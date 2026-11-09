#include "kr_mp4.h"
#include <libavutil/intreadwrite.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define HEADER_LIMIT (4u<<20)
#define KEY_LIMIT 2000000
typedef struct {double *times;int n,cap;double first;} keys;
typedef struct {
    kr_source *source;const kr_mp4_fragment *fragments;keys *result;int count,track;double tb;
    atomic_int next,failed,total;int (*interrupt)(void *);void *context;
} scan;

static int stopped(void *opaque) {
    scan *s=opaque;return atomic_load(&s->failed) || (s->interrupt && s->interrupt(s->context));
}
static int read_all(kr_source *s,int64_t offset,uint8_t *data,int len) {
    int done=0;while(done<len){int n=kr_source_read(s,offset+done,data+done,len-done);if(n<=0)return -1;done+=n;}return 0;
}
static int append(keys *k,double t) {
    if(!isfinite(t) || k->n>=KEY_LIMIT)return -1;
    if(k->n==k->cap){int cap=k->cap?k->cap*2:64;double *p=realloc(k->times,(size_t)cap*sizeof *p);if(!p)return -1;k->times=p;k->cap=cap;}
    k->times[k->n++]=t;return 0;
}
static int box(const uint8_t *p,uint32_t left,uint32_t *len) {
    if(left<8)return -1;
    *len=AV_RB32(p);
    return *len<8 || *len>left?-1:0;
}
static int parse_traf(const uint8_t *p,uint32_t len,int track,double tb,keys *out) {
    uint32_t id=0,defdur=0,defflags=0;int have_flags=0,have_time=0;int64_t dts=0,first_pts=0;int first=1;
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
                if(first){first_pts=dts+cts;out->first=(double)first_pts*tb;first=0;}
                // ISO sample_is_non_sync_sample / sample_depends_on. Do not promote unknown dependent samples.
                if(!(flags&0x10000) && ((flags>>24)&3)!=1) {
                    double time=(double)(dts+cts)*tb;
                    if(append(out,time))return -1;
                }
                dts+=dur;
            }
        }
        at+=n;
    }
    return first?-1:0;
}
static int inspect(kr_source *source,const kr_mp4_fragment *fr,int track,double tb,keys *out) {
    uint8_t h[8];if(read_all(source,fr->offset,h,8) || memcmp(h+4,"moof",4))return -1;
    uint32_t len=AV_RB32(h);if(len<8 || len>HEADER_LIMIT)return -1;
    uint8_t *p=malloc(len);if(!p)return -1;int result=-1;
    if(read_all(source,fr->offset,p,(int)len))goto end;
    for(uint32_t at=8;at<len;) {
        uint32_t n;if(box(p+at,len-at,&n))goto end;
        if(!memcmp(p+at+4,"traf",4) && parse_traf(p+at,n,track,tb,out))goto end;
        at+=n;
    }
    result=0;
end:free(p);return result;
}
static void *worker(void *opaque) {
    scan *s=opaque;kr_source *source=kr_source_clone(s->source,10,stopped,s);
    if(!source){atomic_store(&s->failed,1);return NULL;}
    while(!stopped(s)) {
        int i=atomic_fetch_add(&s->next,1);if(i>=s->count)break;
        if(inspect(source,s->fragments+i,s->track,s->tb,s->result+i) ||
           atomic_fetch_add(&s->total,s->result[i].n)>KEY_LIMIT-s->result[i].n){atomic_store(&s->failed,1);break;}
    }
    kr_source_close(source);return NULL;
}
static int compare(const void *a,const void *b) {double x=*(const double *)a,y=*(const double *)b;return (x>y)-(x<y);}
int kr_mp4_keyframes(kr_source *source,const kr_mp4_fragment *fragments,int count,int track,double tb,double first_time,
                     int (*interrupt)(void *),void *context,double **times,int *ntimes) {
    if(!source || !fragments || count<1 || count>32768 || track<1 || !isfinite(tb) || tb<=0 || !isfinite(first_time) || !times || !ntimes)return -1;
    keys *result=calloc((size_t)count,sizeof *result);if(!result)return -1;
    scan s={.source=source,.fragments=fragments,.result=result,.count=count,.track=track,.tb=tb,.interrupt=interrupt,.context=context};
    pthread_t th[3];int n=0;for(int i=0;i<3 && i<count-1;i++)if(!pthread_create(th+n,NULL,worker,&s))n++;
    worker(&s);for(int i=0;i<n;i++)pthread_join(th[i],NULL);
    keys all={0};int ok=-1;
    if(!stopped(&s)) {
        // One stream-wide presentation offset accounts for its edit list and decoder shift. Re-anchoring
        // every fragment to TFRA loses that offset when different muxers index DTS versus PTS.
        if(result[0].n<1)goto end;
        double offset=first_time-result[0].first;
        for(int i=0;i<count;i++)for(int j=0;j<result[i].n;j++)if(append(&all,result[i].times[j]+offset))goto end;
        if(all.n<1)goto end;
        qsort(all.times,(size_t)all.n,sizeof *all.times,compare);
        int used=0;for(int i=0;i<all.n;i++)if(!used || all.times[i]>all.times[used-1]+tb*.5)all.times[used++]=all.times[i];
        *times=all.times;*ntimes=used;all.times=NULL;ok=0;
    }
end:
    for(int i=0;i<count;i++)free(result[i].times);
    free(result);free(all.times);return ok;
}
