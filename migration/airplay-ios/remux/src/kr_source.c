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
#define SOURCE_SLOTS 512
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
};

static int64_t io_clock(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return (int64_t)t.tv_sec * 1000000000 + t.tv_nsec; }
double kr_source_io_ms(const kr_source *s) { return s ? atomic_load(&s->io_ns) / 1e6 : 0; }

static int interrupted(void *opaque) {
    kr_source *s = opaque;
    int64_t deadline = atomic_load(&s->deadline_ns);
    int extra=s->extra_interrupt && s->extra_interrupt(s->interrupt_context);
    return atomic_load(&s->aborted) || (deadline && io_clock() >= deadline) || extra;
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
        av_dict_set(&o, "initial_request_size", "262144", 0);
        av_dict_set(&o, "request_size", "1048576", 0);
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

kr_source *kr_source_open_interruptible(const char *url, int timeout_s, int (*interrupt)(void *), void *context, char *err, int errlen) {
    if (!url) return NULL;
    kr_source *s = calloc(1, sizeof *s);
    if (!s) return NULL;
    s->url = strdup(url);
    s->timeout_s = timeout_s > 0 ? timeout_s : 30;
    s->extra_interrupt=interrupt;s->interrupt_context=context;
    if (!s->url) { free(s); return NULL; }
    s->cache=calloc(1,sizeof *s->cache);
    if(!s->cache){free(s->url);free(s);return NULL;}
    pthread_mutex_init(&s->cache->lock,NULL);pthread_cond_init(&s->cache->changed,NULL);
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
    int r = (s->io || open_at(s,offset)>=0) ? read_once(s, offset, buf, n) : -1;
    if(r==0 && offset<s->cache->size)r=-1; // EOF before the advertised end is a broken connection.
    for (int k = 0; r < 0 && k < 2 && !interrupted(s); k++) {
        if (s->io) avio_closep(&s->io);
        if (open_at(s, offset) >= 0) r = read_once(s, offset, buf, n);
        if(r==0 && offset<s->cache->size)r=-1;
    }
    atomic_fetch_add(&s->io_ns, io_clock() - start);
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

static int cached_read_one(kr_source *s,int64_t offset,uint8_t *buf,int n) {
    if(!s || !buf || offset<0 || n<0 || interrupted(s))return -1;
    if(!n || (s->cache->size>=0 && offset>=s->cache->size))return 0;
    source_cache *c=s->cache;int result=-1;
    for(;;) {
        if(interrupted(s))break;
        int got=kr_source_cached_read(s,offset,buf,n);
        if(got>0){result=got;break;}
        int64_t base=offset/SOURCE_BLOCK*SOURCE_BLOCK;
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
            pthread_cond_timedwait(&c->changed,&c->lock,&t);pthread_mutex_unlock(&c->lock);continue;
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
        if(last){for(int i=0;i<SOURCE_SLOTS;i++)free(c->blocks[i].data);pthread_cond_destroy(&c->changed);pthread_mutex_destroy(&c->lock);free(c);}
    }
    free(s->url);
    free(s);
}
