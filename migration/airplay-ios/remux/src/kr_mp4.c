#include "kr_mp4.h"
#include <libavutil/intreadwrite.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>

#define HEADER_LIMIT (4u<<20)
#define KEY_LIMIT 2000000
typedef struct {
    kr_source *source;const kr_mp4_fragment *fragments;kr_mp4_keys *result;int count,track;
    atomic_int next,failed,total;int (*interrupt)(void *);void *context;
} scan;

static int stopped(void *opaque) {
    scan *s=opaque;return atomic_load(&s->failed) || (s->interrupt && s->interrupt(s->context));
}
static int read_all(kr_source *s,int64_t offset,uint8_t *data,int len) {
    int done=0;while(done<len){int n=kr_source_read(s,offset+done,data+done,len-done);if(n<=0)return -1;done+=n;}return 0;
}
static int append(kr_mp4_keys *k,int64_t t) {
    if(k->n>=KEY_LIMIT)return -1;
    if(k->n==k->cap){int cap=k->cap?k->cap*2:64;int64_t *p=realloc(k->ticks,(size_t)cap*sizeof *p);if(!p)return -1;k->ticks=p;k->cap=cap;}
    k->ticks[k->n++]=t;return 0;
}
static int box(const uint8_t *p,uint32_t left,uint32_t *len) {
    if(left<8)return -1;
    *len=AV_RB32(p);
    return *len<8 || *len>left?-1:0;
}
// Keyframe presentation times of one track fragment, in the track's own ticks (decode time + composition offset).
static int parse_traf(const uint8_t *p,uint32_t len,int track,kr_mp4_keys *out) {
    uint32_t id=0,defdur=0,defflags=0;int have_flags=0,have_time=0;int64_t dts=0;int first=1;
    for(uint32_t at=8;at<len;) {
        uint32_t n;if(box(p+at,len-at,&n))return -1;const uint8_t *b=p+at;
        if(!memcmp(b+4,"tfhd",4)) {
            if(n<16)return -1;
            uint32_t f=AV_RB24(b+9),q=16;id=AV_RB32(b+12);
            if(f&1)q+=8;
            if(f&2)q+=4;
            if(f&8){if(q+4>n)return -1;defdur=AV_RB32(b+q);q+=4;}
            if(f&16)q+=4;
            if(f&32){if(q+4>n)return -1;defflags=AV_RB32(b+q);have_flags=1;q+=4;}
            if(q>n)return -1;
        } else if(!memcmp(b+4,"tfdt",4)) {
            if(n<16 || b[8]>1 || (b[8] && n<20))return -1;
            dts=b[8]?(int64_t)AV_RB64(b+12):(int64_t)AV_RB32(b+12);have_time=1;
        }
        at+=n;
    }
    if(id!=(uint32_t)track)return 0;
    if(!have_time || dts<0 || dts>INT64_MAX-(KEY_LIMIT+1LL)*UINT32_MAX)return -1;
    for(uint32_t at=8;at<len;) {
        uint32_t n;if(box(p+at,len-at,&n))return -1;const uint8_t *b=p+at;
        if(!memcmp(b+4,"trun",4)) {
            if(n<16 || b[8]>1)return -1;
            uint32_t f=AV_RB24(b+9),count=AV_RB32(b+12),q=16,first_flags=defflags;
            if(f&1)q+=4;
            if(f&4){if(q+4>n)return -1;first_flags=AV_RB32(b+q);q+=4;}
            uint32_t per=((f&0x100)?4:0)+((f&0x200)?4:0)+((f&0x400)?4:0)+((f&0x800)?4:0);
            if(count>KEY_LIMIT || (uint64_t)q+(uint64_t)per*count>n)return -1;
            for(uint32_t i=0;i<count;i++) {
                const uint8_t *e=b+q+i*per;uint32_t k=0,dur=defdur,flags=i?defflags:first_flags;int64_t cts=0;
                if(f&0x100){dur=AV_RB32(e+k);k+=4;}if(f&0x200)k+=4;
                if(f&0x400){flags=AV_RB32(e+k);k+=4;}
                if(f&0x800)cts=b[8]?(int64_t)(int32_t)AV_RB32(e+k):(int64_t)AV_RB32(e+k);
                if(!dur || (!(f&0x400) && !(i==0 && (f&4)) && !have_flags))return -1;
                if(first){if(!out->has_first){out->first=dts+cts;out->has_first=1;}first=0;}
                // ISO sample_is_non_sync_sample / sample_depends_on. Do not promote unknown dependent samples.
                if(!(flags&0x10000) && ((flags>>24)&3)!=1 && append(out,dts+cts))return -1;
                dts+=dur;
            }
        }
        at+=n;
    }
    return first?-1:0;
}
int kr_mp4_moof_keys(const uint8_t *p,uint32_t len,int track,kr_mp4_keys *out) {
    if(!p || len<8 || AV_RB32(p)!=len || memcmp(p+4,"moof",4) || !out)return -1;
    for(uint32_t at=8;at<len;) {
        uint32_t n;if(box(p+at,len-at,&n))return -1;
        if(!memcmp(p+at+4,"traf",4) && parse_traf(p+at,n,track,out))return -1;
        at+=n;
    }
    return 0;
}
// Owner log 0d2dbf1a (build 544): the scan of a 4K movie from Drive took 12-14 s (109 storage fragments, four connections, two round trips
// each: the 8-byte box header, then the moof). One read of FIRST_READ bytes now holds the whole moof in nearly every case (a 70-second
// fragment's index is about 30 KB), and the scan uses SCAN_THREADS connections: about four times fewer waits.
#define FIRST_READ 40960
#define SCAN_THREADS 8
static int inspect(kr_source *source,const kr_mp4_fragment *fr,int track,kr_mp4_keys *out) {
    uint8_t *p=malloc(FIRST_READ);if(!p)return -1;
    int got=kr_source_read(source,fr->offset,p,FIRST_READ),result=-1;
    if(got>=8 && !memcmp(p+4,"moof",4)) {
        uint32_t len=AV_RB32(p);
        if(len>=8 && len<=HEADER_LIMIT) {
            if(len>(uint32_t)FIRST_READ){uint8_t *q=realloc(p,len);if(!q){free(p);return -1;}p=q;}
            // A short first read (the source's own boundary) or a larger moof: read the rest.
            if(got>=(int)len || !read_all(source,fr->offset+got,p+got,(int)len-got))result=kr_mp4_moof_keys(p,len,track,out);
        }
    }
    free(p);return result;
}
static void *worker(void *opaque) {
    scan *s=opaque;kr_source *source=kr_source_clone(s->source,10,stopped,s);
    if(!source){atomic_store(&s->failed,1);return NULL;}
    while(!stopped(s)) {
        int i=atomic_fetch_add(&s->next,1);if(i>=s->count)break;
        if(inspect(source,s->fragments+i,s->track,s->result+i) ||
           atomic_fetch_add(&s->total,s->result[i].n)>KEY_LIMIT-s->result[i].n){atomic_store(&s->failed,1);break;}
    }
    kr_source_close(source);return NULL;
}
void kr_mp4_keys_free(kr_mp4_keys *k) {
    if(k){free(k->ticks);memset(k,0,sizeof *k);}
}
int kr_mp4_keyframe_ticks(kr_source *source,const kr_mp4_fragment *fragments,int count,int track,
                          int (*interrupt)(void *),void *context,kr_mp4_keys *out) {
    if(!source || !fragments || count<1 || count>32768 || track<1 || !out)return -1;
    memset(out,0,sizeof *out);
    kr_mp4_keys *result=calloc((size_t)count,sizeof *result);if(!result)return -1;
    scan s={.source=source,.fragments=fragments,.result=result,.count=count,.track=track,.interrupt=interrupt,.context=context};
    pthread_t th[SCAN_THREADS-1];int n=0;for(int i=0;i<SCAN_THREADS-1 && i<count-1;i++)if(!pthread_create(th+n,NULL,worker,&s))n++;
    worker(&s);for(int i=0;i<n;i++)pthread_join(th[i],NULL);
    int ok=-1;
    // The first fragment must hold a keyframe; its first sample anchors the stream-wide presentation offset.
    if(!stopped(&s) && result[0].n>=1 && result[0].has_first) {
        out->first=result[0].first;out->has_first=1;ok=0;
        for(int i=0;i<count && !ok;i++)for(int j=0;j<result[i].n;j++)if(append(out,result[i].ticks[j])){ok=-1;break;}
        if(ok)kr_mp4_keys_free(out);
    }
    for(int i=0;i<count;i++)free(result[i].ticks);
    free(result);return ok;
}
static int compare(const void *a,const void *b) {double x=*(const double *)a,y=*(const double *)b;return (x>y)-(x<y);}
int kr_mp4_keys_times(const kr_mp4_keys *k,double tb,double first_time,double **times,int *ntimes) {
    if(!k || k->n<1 || !k->has_first || !isfinite(tb) || tb<=0 || !isfinite(first_time) || !times || !ntimes)return -1;
    // One stream-wide presentation offset accounts for its edit list and decoder shift. Re-anchoring
    // every fragment to TFRA loses that offset when different muxers index DTS versus PTS.
    double offset=first_time-(double)k->first*tb;
    double *t=malloc((size_t)k->n*sizeof *t);if(!t)return -1;
    for(int i=0;i<k->n;i++){t[i]=(double)k->ticks[i]*tb+offset;if(!isfinite(t[i])){free(t);return -1;}}
    qsort(t,(size_t)k->n,sizeof *t,compare);
    int used=0;for(int i=0;i<k->n;i++)if(!used || t[i]>t[used-1]+tb*.5)t[used++]=t[i];
    *times=t;*ntimes=used;return 0;
}
int kr_mp4_keyframes(kr_source *source,const kr_mp4_fragment *fragments,int count,int track,double tb,double first_time,
                     int (*interrupt)(void *),void *context,double **times,int *ntimes) {
    if(!isfinite(tb) || tb<=0 || !isfinite(first_time) || !times || !ntimes)return -1;
    kr_mp4_keys k;if(kr_mp4_keyframe_ticks(source,fragments,count,track,interrupt,context,&k))return -1;
    int r=kr_mp4_keys_times(&k,tb,first_time,times,ntimes);kr_mp4_keys_free(&k);return r;
}

// ISSUE-335 fix 2 / ISSUE-346: the keyframe timeline of a prepared file depends only on its bytes, so it is kept on
// the phone, keyed by the file size, the track and a hash of the file's own fragment index (mfra). Preparation saves
// it as it writes the file; a cast that finds none scans the file once and saves it. KR_KEYFRAME_CACHE overrides the
// folder (host tests); otherwise Library/Caches/KodiAirPlay under the app's home. KRKF1 files (times in seconds)
// are not read; the file is scanned again once.
#define KF_MAGIC "KRKF2"
static void cache_path(char *out,size_t len,uint64_t key) {
    const char *dir=getenv("KR_KEYFRAME_CACHE");char made[1024]="";
    if(!dir || !*dir) {
        const char *home=getenv("HOME");if(!home || !*home){*out=0;return;}
        snprintf(made,sizeof made,"%s/Library/Caches/KodiAirPlay",home);
        char parent[1024];snprintf(parent,sizeof parent,"%s/Library/Caches",home);
        mkdir(parent,0755);mkdir(made,0755);dir=made;
    } else mkdir(dir,0755);
    snprintf(out,len,"%s/keyframes-%016llx.bin",dir,(unsigned long long)key);
}
uint64_t kr_mp4_cache_key(const uint8_t *mfra,uint32_t len,int64_t size,int track) {
    uint64_t h=1469598103934665603ULL;   // FNV-1a 64
    for(uint32_t i=0;i<len;i++){h^=mfra[i];h*=1099511628211ULL;}
    h^=(uint64_t)size;h*=1099511628211ULL;h^=(uint64_t)(uint32_t)track;h*=1099511628211ULL;
    return h;
}
int kr_mp4_cache_load(uint64_t key,kr_mp4_keys *out,int *origin) {
    char path[1100];cache_path(path,sizeof path,key);if(!*path || !out)return -1;
    memset(out,0,sizeof *out);
    FILE *f=fopen(path,"rb");if(!f)return -1;
    char magic[6]={0};int32_t count=0,from=0;int64_t first=0;int64_t *t=NULL;int ok=-1;
    if(fread(magic,1,6,f)==6 && !memcmp(magic,KF_MAGIC,6) && fread(&from,sizeof from,1,f)==1 && fread(&first,sizeof first,1,f)==1 &&
       fread(&count,sizeof count,1,f)==1 && count>0 && count<=KEY_LIMIT &&
       (t=malloc((size_t)count*sizeof *t)) && fread(t,sizeof *t,(size_t)count,f)==(size_t)count && fgetc(f)==EOF)ok=0;
    fclose(f);
    if(ok){free(t);return -1;}   // a damaged file is ignored
    out->ticks=t;out->n=out->cap=count;out->first=first;out->has_first=1;if(origin)*origin=from;
    return 0;
}
void kr_mp4_cache_save(uint64_t key,const kr_mp4_keys *k,int origin) {
    char path[1100],tmp[1120];cache_path(path,sizeof path,key);
    if(!*path || !k || k->n<=0 || !k->has_first)return;
    snprintf(tmp,sizeof tmp,"%s.%d.%p.tmp",path,(int)getpid(),(const void *)k);
    FILE *f=fopen(tmp,"wb");if(!f)return;
    int32_t count=k->n,from=origin;
    int ok=fwrite(KF_MAGIC,1,6,f)==6 && fwrite(&from,sizeof from,1,f)==1 && fwrite(&k->first,sizeof k->first,1,f)==1 &&
           fwrite(&count,sizeof count,1,f)==1 && fwrite(k->ticks,sizeof *k->ticks,(size_t)k->n,f)==(size_t)k->n;
    if(fclose(f)!=0)ok=0;
    if(ok)rename(tmp,path);else unlink(tmp);
}
