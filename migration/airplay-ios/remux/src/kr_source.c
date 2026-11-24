// kr_source: gm_source over FFmpeg's avio (http/https/file). Seeks become HTTP Range requests.
#include "kr_source.h"
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <pthread.h>
#include <libavformat/avio.h>
#include <libavutil/dict.h>
#include <libavutil/error.h>

// One cache per opened movie, shared by independent video/audio/subtitle cursors. Metadata is locked only
// for lookup/copy/publication; a slow Drive read never holds the cache mutex. Block zero stays resident.
#define SOURCE_BLOCK (128 * 1024)
#define SOURCE_SLOTS 1024
// ISSUE-335 (owner logs 87d9a389, 65cca4ce, build 502): AirPlay of a Drive copy froze 30 s on one Drive read that
// sent nothing (video segment 1: source I/O 31.7 s, the others 1-3 s), and a 1080p episode read at ~0.5 MB/s over its
// one connection, slower than it plays.
// Fix 1: a read that receives no bytes for STALL_SECONDS is dropped and retried on a fresh connection.
// Fix 3: when a cursor reads blocks in order, AHEAD_HELPERS extra connections fetch the 1 MiB chunks ahead of it.
#define STALL_SECONDS 4
#ifndef AHEAD_HELPERS
#define AHEAD_HELPERS 2
#endif
#define AHEAD_CHUNK 8    // blocks per helper request (1 MiB)
#define AHEAD_GAP 8      // helpers start this many blocks past the cursor, which streams the ones before
#define AHEAD_QUEUE 64
// Helpers join only a connection measured slower than this (bytes/s, recent reads): on a fast one they cost the
// cursor a reconnect per chunk it skips (host rig: 0.3 s per request, 6 MB in 0.31 s alone, 1.23 s with helpers).
#define AHEAD_BELOW (1536*1024)
typedef struct {
    int64_t at;
    uint8_t *data;
    int len, loading;
    uint64_t used;
} source_block;
typedef struct {
    pthread_mutex_t lock;
    pthread_cond_t changed;
    int refs;
    int64_t size;
    uint64_t clock;
    source_block blocks[SOURCE_SLOTS];
    // ISSUE-335 fix 3: helper connections that fetch the blocks after a sequential reader (owned by the cache).
    pthread_t ahead_thread[AHEAD_HELPERS];
    struct kr_source *ahead_src[AHEAD_HELPERS];
    int ahead_started, ahead_stop;
    int64_t ahead_q[AHEAD_QUEUE];
    int ahead_n;
    pthread_cond_t ahead_cond;
} source_cache;
struct kr_source {
    AVIOContext *io;
    int64_t pos;
    atomic_int aborted;
    atomic_llong io_ns;
    atomic_llong deadline_ns;
    char *url;
    int timeout_s;
    int (*extra_interrupt)(void *);
    void *interrupt_context;
    source_cache *cache;
    // ISSUE-335: no-progress watchdog for the read in flight (only the reading thread touches these).
    int stall_on, stalled, stall_check;
    int64_t progress_ns, last_bytes, last_block;
    int64_t rate_bytes, rate_ns;   // decaying recent throughput of this cursor's own reads
    int helper;
    int request_bytes;   // 0: the defaults below; the preview strip asks for one request that holds a whole keyframe (kr_source_open_tuned)
    atomic_llong cache_wait_ns;
};

static int64_t io_clock(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return (int64_t)t.tv_sec * 1000000000 + t.tv_nsec; }
double kr_source_wait_ms(const kr_source *s) { return s ? atomic_load(&s->cache_wait_ns) / 1e6 : 0; }
double kr_source_io_ms(const kr_source *s) { return s ? atomic_load(&s->io_ns) / 1e6 : 0; }

static int hard_interrupted(kr_source *s) {
    int64_t deadline = atomic_load(&s->deadline_ns);
    int extra=s->extra_interrupt && s->extra_interrupt(s->interrupt_context);
    return atomic_load(&s->aborted) || (deadline && io_clock() >= deadline) || extra;
}
// FFmpeg calls this while a read blocks. Besides stop/deadline, a read whose connection has delivered nothing for
// STALL_SECONDS is cut so upstream_read can reconnect (bytes_read grows each time the protocol returns data).
static int interrupted(void *opaque) {
    kr_source *s = opaque;
    if(hard_interrupted(s))return 1;
    if(s->stall_on) {
        int64_t now=io_clock(),bytes=s->io?s->io->bytes_read:-1;
        if(bytes!=s->last_bytes){s->last_bytes=bytes;s->progress_ns=now;}
        else if(now-s->progress_ns>(int64_t)STALL_SECONDS*1000000000LL){s->stalled=1;return 1;}
    }
    return 0;
}

void kr_source_set_interrupt(kr_source *s, int (*callback)(void *), void *context) {
    if(s){s->extra_interrupt=callback;s->interrupt_context=context;}
}

static int open_at(kr_source *s, int64_t offset) {
    AVDictionary *o = NULL;
    char t[32];
    snprintf(t, sizeof t, "%lld", (long long)s->timeout_s * 1000000LL);
    av_dict_set(&o, "rw_timeout", t, 0);
    int http = !strncmp(s->url, "http://", 7) || !strncmp(s->url, "https://", 8);
    if (http) {
        // Bound speculative upstream fetching: the Drive proxy grows open-ended reads to 8 MiB.
        // Keep probing small, then use 1 MiB requests; FFmpeg advances across range boundaries.
        char rs[16];
        snprintf(rs, sizeof rs, "%d", s->request_bytes ? s->request_bytes : 262144);
        av_dict_set(&o, "initial_request_size", rs, 0);
        snprintf(rs, sizeof rs, "%d", s->request_bytes ? s->request_bytes : 1048576);
        av_dict_set(&o, "request_size", rs, 0);
        av_dict_set(&o, "short_seek_size", "65536", 0);
        av_dict_set(&o, "multiple_requests", "1", 0);
        snprintf(t, sizeof t, "%lld", (long long)offset);
        av_dict_set(&o, "offset", t, 0);
        // Retries belong to kr_source_read's shared deadline, not a second HTTP backoff loop.
        av_dict_set(&o, "seekable", "1", 0);  // Elementum and Drive answer Range requests
        av_dict_set(&o, "user_agent", "Kodi-iOS-AirPlay/1", 0);
    }
    AVIOInterruptCB cb = { interrupted, s };
    int r = avio_open2(&s->io, s->url, AVIO_FLAG_READ, &cb, &o);
    av_dict_free(&o);
    // HTTP's offset option already positioned the protocol at this absolute offset, while AVIO's logical
    // origin is still zero. Translate that origin without a buffered seek (which could discard offset bytes
    // a second time). File protocols instead need an actual seek from their initial position.
    if(r>=0 && http)s->io->pos+=offset;
    if (r >= 0 && !http && offset && avio_seek(s->io, offset, SEEK_SET) < 0) r = AVERROR(EIO);
    if (r < 0) { if (s->io) avio_closep(&s->io); }
    else s->pos = offset;
    return r;
}

static kr_source *open_with(const char *url, int timeout_s, int (*interrupt)(void *), void *context, int request_bytes, char *err, int errlen);
kr_source *kr_source_open_interruptible(const char *url, int timeout_s, int (*interrupt)(void *), void *context, char *err, int errlen) {
    return open_with(url, timeout_s, interrupt, context, 0, err, errlen);
}
// Every HTTP range request is `request_bytes` long (the preview strip: one keyframe per request, read to its end, so the connection is reused for the next jump instead of being
// dropped with most of a 1 MiB answer unread and set up again, which costs a TCP and TLS handshake on every picture over a phone's network).
kr_source *kr_source_open_tuned(const char *url, int timeout_s, int (*interrupt)(void *), void *context, int request_bytes, char *err, int errlen) {
    return open_with(url, timeout_s, interrupt, context, request_bytes, err, errlen);
}
static kr_source *open_with(const char *url, int timeout_s, int (*interrupt)(void *), void *context, int request_bytes, char *err, int errlen) {
    if (!url) return NULL;
    kr_source *s = calloc(1, sizeof *s);
    if (!s) return NULL;
    s->request_bytes = request_bytes;
    s->url = strdup(url);
    s->timeout_s = timeout_s > 0 ? timeout_s : 30;
    s->extra_interrupt=interrupt;s->interrupt_context=context;
    if (!s->url) { free(s); return NULL; }
    // Elementum's server waits for torrent pieces: a quiet connection there is normal, and reconnecting cannot help.
    s->stall_check=(!strncmp(url,"http://",7) || !strncmp(url,"https://",8)) && !strstr(url,":65220/");
    s->last_block=-1;
    s->cache=calloc(1,sizeof *s->cache);
    if(!s->cache){free(s->url);free(s);return NULL;}
    pthread_mutex_init(&s->cache->lock,NULL);pthread_cond_init(&s->cache->changed,NULL);pthread_cond_init(&s->cache->ahead_cond,NULL);
    s->cache->refs=1;s->cache->size=-1;
    atomic_store(&s->deadline_ns, io_clock() + (int64_t)s->timeout_s * 1000000000LL);
    int r = open_at(s, 0);
    if(r>=0)s->cache->size=avio_size(s->io);
    atomic_store(&s->deadline_ns, 0);
    if (r < 0) {
        if (err && errlen > 0) {
            char e[128]; av_strerror(r, e, sizeof e);
            snprintf(err, (size_t)errlen, "cannot open the stream (%s)", e);
        }
        kr_source_close(s);
        return NULL;
    }
    return s;
}

kr_source *kr_source_clone(kr_source *root,int timeout_s,int (*interrupt)(void *),void *context) {
    if(!root)return NULL;
    kr_source *s=calloc(1,sizeof *s);if(!s)return NULL;
    s->url=strdup(root->url);if(!s->url){free(s);return NULL;}
    s->timeout_s=timeout_s>0?timeout_s:root->timeout_s;
    s->extra_interrupt=interrupt;s->interrupt_context=context;s->cache=root->cache;
    s->stall_check=root->stall_check;s->last_block=-1;s->request_bytes=root->request_bytes;
    pthread_mutex_lock(&s->cache->lock);s->cache->refs++;pthread_mutex_unlock(&s->cache->lock);
    return s;
}

kr_source *kr_source_open(const char *url, int timeout_s, char *err, int errlen) {
    return kr_source_open_interruptible(url,timeout_s,NULL,NULL,err,errlen);
}

int64_t kr_source_size(kr_source *s) { return s && s->cache ? s->cache->size : -1; }

static int read_once(kr_source *s, int64_t offset, uint8_t *buf, int n);

// Retry a failed connection using a NEW AVIO context, at the requested offset (no probe at zero).
// All attempts share one timeout budget, so retries cannot turn a 30-second read into 90 seconds.
static int upstream_read(kr_source *s, int64_t offset, uint8_t *buf, int n) {
    if (!s || !buf || offset < 0 || n < 0 || atomic_load(&s->aborted)) return -1;
    if (!n) return 0;
    int64_t start = io_clock();
    int r=-1;
    // Up to three connections share the read's deadline; a connection that went quiet counts as broken.
    for (int k = 0; k < 3 && !hard_interrupted(s); k++) {
        s->stalled=0;s->stall_on=s->stall_check;s->progress_ns=io_clock();s->last_bytes=s->io?s->io->bytes_read:-1;
        if (k && s->io) avio_closep(&s->io);
        r = (s->io || open_at(s,offset)>=0) ? read_once(s, offset, buf, n) : -1;
        s->stall_on=0;
        if(r==0 && offset<s->cache->size)r=-1; // EOF before the advertised end is a broken connection.
        if(s->stalled) {
            if (s->io) avio_closep(&s->io);   // never read again from a connection that went quiet
            if(r>0)break;                       // keep what arrived; the caller asks for the rest anew
            r=-1;continue;
        }
        if(r>=0)break;
    }
    int64_t spent=io_clock()-start;
    atomic_fetch_add(&s->io_ns, spent);
    if(!s->helper){s->rate_bytes=s->rate_bytes*7/8+(r>0?r:0);s->rate_ns=s->rate_ns*7/8+spent;}
    return r;
}

int kr_source_cached_read(kr_source *s,int64_t offset,uint8_t *buf,int n) {
    if(!s || !buf || offset<0 || n<=0 || interrupted(s))return 0;
    source_cache *c=s->cache;int got=0;int64_t base=offset/SOURCE_BLOCK*SOURCE_BLOCK;
    pthread_mutex_lock(&c->lock);
    for(int i=0;i<SOURCE_SLOTS;i++) {
        source_block *b=&c->blocks[i];
        if(b->data && b->at==base && offset-base<b->len) {
            got=b->len-(int)(offset-base);if(got>n)got=n;
            memcpy(buf,b->data+(offset-base),(size_t)got);b->used=++c->clock;break;
        }
    }
    pthread_mutex_unlock(&c->lock);return got;
}

// ---- ISSUE-335 fix 3: read-ahead helpers ---------------------------------------------------------------------
// The reading cursor keeps streaming on its own connection. Helpers each take a whole chunk (AHEAD_CHUNK blocks,
// one continuous request) that starts AHEAD_GAP blocks past it, and publish each block as it arrives, so a slow
// connection is joined by others instead of the cursor waiting on a fresh request per block.
static int ahead_stopping(void *context) { return ((source_cache *)context)->ahead_stop; }
// c->lock held. The slot for base claimed for loading, or -1 when the block is present/loading or no slot is free.
static int claim_locked(source_cache *c,int64_t base) {
    int evict=-1;
    for(int i=0;i<SOURCE_SLOTS;i++) {
        source_block *b=&c->blocks[i];
        if(b->data && b->at==base && (b->len>0 || b->loading))return -1;
        if(!b->loading && (!b->data || b->at!=0) && (evict<0 || !b->data || b->used<c->blocks[evict].used))evict=i;
    }
    if(evict<0)return -1;
    source_block *b=&c->blocks[evict];
    if(!b->data && !(b->data=malloc(SOURCE_BLOCK)))return -1;
    b->at=base;b->len=0;b->loading=1;b->used=++c->clock;
    return evict;
}
static void *ahead_worker(void *arg) {
    kr_source *s=arg;source_cache *c=s->cache;
    pthread_mutex_lock(&c->lock);
    while(!c->ahead_stop) {
        if(!c->ahead_n){pthread_cond_wait(&c->ahead_cond,&c->lock);continue;}
        int64_t chunk=c->ahead_q[0];
        memmove(c->ahead_q,c->ahead_q+1,(size_t)(--c->ahead_n)*sizeof *c->ahead_q);
        for(int k=0;k<AHEAD_CHUNK && !c->ahead_stop;k++) {
            int64_t base=chunk+(int64_t)k*SOURCE_BLOCK;
            if(c->size>=0 && base>=c->size)break;
            int slot=claim_locked(c,base);
            if(slot<0)continue;   // the cursor or another helper has it
            source_block *b=&c->blocks[slot];
            int need=SOURCE_BLOCK;if(c->size>=0 && base+need>c->size)need=(int)(c->size-base);
            pthread_mutex_unlock(&c->lock);
            atomic_store(&s->deadline_ns,io_clock()+(int64_t)s->timeout_s*1000000000LL);
            int got=upstream_read(s,base,b->data,need);
            atomic_store(&s->deadline_ns,0);
            pthread_mutex_lock(&c->lock);
            b->len=got>0?got:0;b->loading=0;pthread_cond_broadcast(&c->changed);
            if(got<need)break;
        }
    }
    pthread_mutex_unlock(&c->lock);
    return NULL;
}
static void read_ahead(kr_source *s,int64_t base) {
    if(!s->stall_check || s->helper)return;
    int sequential=s->last_block>=0 && base==s->last_block+SOURCE_BLOCK;
    s->last_block=base;
    // Judged over the last few hundred kilobytes of reads, so one slow connection set-up does not count as a slow source.
    int slow=s->rate_bytes>=(int64_t)AHEAD_CHUNK*SOURCE_BLOCK/4 && s->rate_ns>0 &&
             (double)s->rate_bytes*1e9/(double)s->rate_ns<AHEAD_BELOW;
    if(!sequential || !slow || AHEAD_HELPERS<1)return;
    source_cache *c=s->cache;
    pthread_mutex_lock(&c->lock);
    if(!c->ahead_started && !c->ahead_stop) {
        c->ahead_started=1;
        for(int h=0;h<AHEAD_HELPERS;h++) {
            kr_source *k=calloc(1,sizeof *k);
            if(!k || !(k->url=strdup(s->url))){free(k);break;}
            k->timeout_s=s->timeout_s;k->request_bytes=s->request_bytes;k->cache=c;k->helper=1;k->stall_check=1;k->last_block=-1;
            k->extra_interrupt=ahead_stopping;k->interrupt_context=c;
            if(pthread_create(&c->ahead_thread[h],NULL,ahead_worker,k)){free(k->url);free(k);break;}
            c->ahead_src[h]=k;
        }
    }
    int64_t span=(int64_t)AHEAD_CHUNK*SOURCE_BLOCK;
    int64_t first=(base/SOURCE_BLOCK+AHEAD_GAP)*SOURCE_BLOCK/span*span;
    if(first<=base)first+=span;
    for(int k=0;k<AHEAD_HELPERS;k++) {
        int64_t at=first+k*span;
        if(c->size>=0 && at>=c->size)break;
        int known=0;
        for(int i=0;i<c->ahead_n && !known;i++)known=c->ahead_q[i]==at;
        for(int i=0;i<SOURCE_SLOTS && !known;i++)known=c->blocks[i].data && c->blocks[i].at==at && (c->blocks[i].len>0 || c->blocks[i].loading);
        if(!known && c->ahead_n<AHEAD_QUEUE)c->ahead_q[c->ahead_n++]=at;
    }
    pthread_cond_broadcast(&c->ahead_cond);
    pthread_mutex_unlock(&c->lock);
}

static int cached_read_one(kr_source *s,int64_t offset,uint8_t *buf,int n) {
    if(!s || !buf || offset<0 || n<0 || interrupted(s))return -1;
    if(!n || (s->cache->size>=0 && offset>=s->cache->size))return 0;
    source_cache *c=s->cache;int result=-1;
    for(;;) {
        if(interrupted(s))break;
        int64_t base=offset/SOURCE_BLOCK*SOURCE_BLOCK;
        if(base!=s->last_block)read_ahead(s,base);
        int got=kr_source_cached_read(s,offset,buf,n);
        if(got>0){result=got;break;}
        pthread_mutex_lock(&c->lock);
        int slot=-1,evict=-1;
        for(int i=0;i<SOURCE_SLOTS;i++) {
            source_block *b=&c->blocks[i];
            if(b->data && b->at==base){slot=i;break;}
            if(!b->loading && (!b->data || b->at!=0) &&
               (evict<0 || !b->data || b->used<c->blocks[evict].used))evict=i;
        }
        if(slot<0)slot=evict;
        if(slot<0 || c->blocks[slot].loading) {
            struct timespec t;clock_gettime(CLOCK_REALTIME,&t);t.tv_nsec+=50000000;
            if(t.tv_nsec>=1000000000){t.tv_sec++;t.tv_nsec-=1000000000;}
            int64_t waiting=io_clock();
            pthread_cond_timedwait(&c->changed,&c->lock,&t);
            atomic_fetch_add(&s->cache_wait_ns,io_clock()-waiting);
            pthread_mutex_unlock(&c->lock);continue;
        }
        source_block *b=&c->blocks[slot];
        if(!b->data){b->data=malloc(SOURCE_BLOCK);if(!b->data){pthread_mutex_unlock(&c->lock);break;}}
        if(b->at!=base){b->at=base;b->len=0;}
        // Recheck after locking: another cursor may have published the requested bytes.
        if(offset-base<b->len){pthread_mutex_unlock(&c->lock);continue;}
        int filled=b->len;
        int need=(int)(offset-base)+(n<SOURCE_BLOCK?n:SOURCE_BLOCK);
        if(need>SOURCE_BLOCK)need=SOURCE_BLOCK;
        if(c->size>=0 && base+need>c->size)need=(int)(c->size-base);
        b->loading=1;b->used=++c->clock;pthread_mutex_unlock(&c->lock);
        // Only this loader writes the unpublished suffix. Cached prefixes remain readable meanwhile.
        got=upstream_read(s,base+filled,b->data+filled,need-filled);
        pthread_mutex_lock(&c->lock);
        if(got>0)b->len=filled+got;
        b->loading=0;pthread_cond_broadcast(&c->changed);pthread_mutex_unlock(&c->lock);
        if(got<=0){result=got;break;}
    }
    return result;
}

int kr_source_read(kr_source *s,int64_t offset,uint8_t *buf,int n) {
    if(!s || !buf || offset<0 || n<0 || interrupted(s))return -1;
    atomic_store(&s->deadline_ns,io_clock()+(int64_t)s->timeout_s*1000000000LL);
    int got=0,r=0;
    while(got<n && (r=cached_read_one(s,offset+got,buf+got,n-got))>0)got+=r;
    atomic_store(&s->deadline_ns,0);return got?got:r;
}

static int read_once(kr_source *s, int64_t offset, uint8_t *buf, int n) {
    if (!s || !s->io || atomic_load(&s->aborted)) return -1;
    if (offset != s->pos) {
        int64_t r = avio_seek(s->io, offset, SEEK_SET);
        if (r < 0) return -1;
        s->pos = offset;
    }
    int got = 0;
    while (got < n) {
        int r = avio_read(s->io, buf + got, n - got);
        if (r == AVERROR_EOF || r == 0) break;
        if (r < 0) { if (!got) return -1; break; }
        got += r;
    }
    s->pos += got;
    return got;
}

static int64_t gm_size(void *ctx) { return kr_source_size(ctx); }
static int gm_read(void *ctx, int64_t off, uint8_t *buf, int n) { return kr_source_read(ctx, off, buf, n); }

gm_source kr_source_gm(kr_source *s) { gm_source g = { s, gm_size, gm_read }; return g; }

void kr_source_abort(kr_source *s) { if (s) atomic_store(&s->aborted, 1); }

void kr_source_close(kr_source *s) {
    if (!s) return;
    s->extra_interrupt=NULL;s->interrupt_context=NULL;
    if (s->io) avio_closep(&s->io);
    source_cache *c=s->cache;
    if(c) {
        pthread_mutex_lock(&c->lock);int last=!--c->refs;pthread_mutex_unlock(&c->lock);
        if(last) {
            pthread_mutex_lock(&c->lock);c->ahead_stop=1;pthread_cond_broadcast(&c->ahead_cond);pthread_mutex_unlock(&c->lock);
            for(int h=0;h<AHEAD_HELPERS;h++)if(c->ahead_src[h]) {
                pthread_join(c->ahead_thread[h],NULL);
                kr_source *k=c->ahead_src[h];if(k->io)avio_closep(&k->io);free(k->url);free(k);
            }
            for(int i=0;i<SOURCE_SLOTS;i++)free(c->blocks[i].data);
            pthread_cond_destroy(&c->ahead_cond);pthread_cond_destroy(&c->changed);pthread_mutex_destroy(&c->lock);free(c);
        }
    }
    free(s->url);
    free(s);
}
