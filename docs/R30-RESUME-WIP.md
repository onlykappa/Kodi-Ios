# r30 resume work in progress (not built)

Apply: `sed -n "/^\`\`\`diff$/,/^\`\`\`$/p" docs/R30-RESUME-WIP.md | sed "1d;\$d" | git apply`

```diff
diff --git a/migration/airplay-ios/remux/src/kr_prepare.c b/migration/airplay-ios/remux/src/kr_prepare.c
index 84638ba..cba721a 100644
--- a/migration/airplay-ios/remux/src/kr_prepare.c
+++ b/migration/airplay-ios/remux/src/kr_prepare.c
@@ -23,6 +23,8 @@
 #include <string.h>
 #include <math.h>
 #include <pthread.h>
+#include <libavutil/bprint.h>
+#include "../gmplayer/gm_stream.h"
 
 #define TRACKS 64
 #define PREP_UNIT 30   // seconds per preparation unit (r20; live AirPlay keeps its 6)
@@ -252,7 +254,7 @@ typedef struct {
 } generated_lane;
 typedef struct {
     generated_lane *lanes[MAX_LANES];int nlanes;generated_hub *hub;
-    gm_buf unit;int segment,offset,count,is_video,index;kr_prepare_progress progress;void *context;
+    gm_buf unit;int segment,offset,count,is_video,index,served,start;kr_prepare_progress progress;void *context;
     char *error;int error_size;char *input;   // the reader array lives on the converter's stack: keep it small
     long seen_frames[MAX_LANES];double seen_at[MAX_LANES];
 } generated_reader;
@@ -324,7 +326,7 @@ static int generated_read(void *opaque,uint8_t *data,int size) {
         for(int i=0;i<g->nlanes;i++) if(!g->lanes[i]->started && lane_start(g->lanes[i])) {
             if(g->error && g->error_size>0)snprintf(g->error,(size_t)g->error_size,"Conversion thread");return AVERROR(EIO);
         }
-        int li=g->segment%g->nlanes;generated_lane *l=g->lanes[li];
+        int li=(g->segment-g->start)%g->nlanes;generated_lane *l=g->lanes[li];
         g->seen_at[li]=now_s();g->seen_frames[li]=g->is_video?kr_video_frames(l->video):0;
         pthread_mutex_lock(&h->lock);
         while(!l->has_next) {
@@ -357,7 +359,7 @@ static int generated_read(void *opaque,uint8_t *data,int size) {
         pthread_cond_broadcast(&h->cond);   // that lane makes its next unit meanwhile
         pthread_mutex_unlock(&h->lock);
         if(r<0)return AVERROR(EIO);
-        g->offset=g->segment?kr_first_moof(g->unit.data,g->unit.len):0;
+        g->offset=g->served++?kr_first_moof(g->unit.data,g->unit.len):0;   // r30: the first unit served keeps its init
         if(g->offset<0 || g->offset>=g->unit.len)return AVERROR_INVALIDDATA;
         g->segment++;
     }
@@ -379,8 +381,18 @@ static void generated_close(generated_reader *g) {
     }
     free(g->unit.data);free(g->input);memset(g,0,sizeof *g);
 }
+// r30: resume_t >= 0 starts at the unit holding that time (a picture: the unit that starts there); -1 at the start.
+static int resume_unit(gm_stream *plan,double t,int video) {
+    if(t<0)return 0;
+    int count=gm_stream_segment_count(plan);
+    for(int u=0;u<count;u++){double start=gm_stream_segment_start(plan,u);if(video && fabs(start-t)<0.02)return u;}
+    if(video)return -1;
+    int u=gm_stream_time_to_segment(plan,t);if(u<0)return -1;
+    if(u>0 && t-gm_stream_segment_start(plan,u)<1.0)u--;   // near a boundary the packet may still be in the unit before
+    return u;
+}
 static int generated_open(generated_reader *g,AVFormatContext **format,AVIOContext **io,
-                          const char *input,int index,int video,kr_prepare_progress cb,void *ctx,char *err,int en) {
+                          const char *input,int index,int video,kr_prepare_progress cb,void *ctx,char *err,int en,double resume_t) {
     g->is_video=video;g->index=index;g->progress=cb;g->context=ctx;g->error=err;g->error_size=en;
     g->input=strdup(input);if(!g->input)return -1;
     g->hub=calloc(1,sizeof *g->hub);if(!g->hub)return -1;
@@ -392,6 +404,9 @@ static int generated_open(generated_reader *g,AVFormatContext **format,AVIOConte
     first->source=kr_source_open(input,30,err,en);if(!first->source)return -1;
     first->plan=gm_stream_open(kr_source_gm(first->source),PREP_UNIT,err,en);if(!first->plan)return -1;   // r21: was 6 s
     g->count=gm_stream_segment_count(first->plan);
+    int start=resume_unit(first->plan,resume_t,video);
+    if(start<0 || (start>=g->count && g->count>0))return fail(err,en,"Resume position not found",0);
+    g->segment=start;g->start=start;
     if(video) {
         first->video=kr_video_open(kr_source_gm(first->source),index,err,en);if(!first->video)return -1;kr_video_keep_resolution(first->video);
         // A picture copied by hardware HDR / GPU work in lanes; one lane for anything else (CPU work is already
@@ -401,8 +416,8 @@ static int generated_open(generated_reader *g,AVFormatContext **format,AVIOConte
         const char *forced=getenv("KR_PREP_LANES");
         if(forced && atoi(forced)>=1 && atoi(forced)<=MAX_LANES)g->nlanes=atoi(forced);
     } else {first->audio=kr_audio_open(kr_source_gm(first->source),index,err,en);if(!first->audio)return -1;}
-    first->first=0;first->stride=g->nlanes;first->count=g->count;first->is_video=video;first->index=index;
-    for(int i=1;i<g->nlanes;i++){g->lanes[i]=lane_open(g,i,err,en);if(!g->lanes[i])return -1;}
+    first->first=start;first->stride=g->nlanes;first->count=g->count;first->is_video=video;first->index=index;
+    for(int i=1;i<g->nlanes;i++){g->lanes[i]=lane_open(g,start+i,err,en);if(!g->lanes[i])return -1;}
     uint8_t *buffer=av_malloc(32768);if(!buffer)return -1;
     *io=avio_alloc_context(buffer,32768,0,g,generated_read,NULL,NULL);
     if(!*io){av_free(buffer);return -1;}
@@ -412,9 +427,12 @@ static int generated_open(generated_reader *g,AVFormatContext **format,AVIOConte
 }
 // r26: the add-on says when Kodi is off screen (VideoToolbox may stop there): units then decode on the CPU.
 void kodi_airplay_prepare_background(int on) { kr_video_set_background(on); }
+typedef struct {AVFormatContext *f;AVPacket *packet;int map[TRACKS];int eof;int own;} input_track;
+struct resume_ctx;
 typedef struct {
     kr_prepare_write write;void *context;int track;char suffix[80];
     uint8_t *init;int init_size,initialized;double duration;
+    struct resume_ctx *rc;   // r30, the movie (track 0) of a streamed conversion: parsed on its way out
 } output_sink;
 // A finite standalone fragmented movie must advertise its full duration in the init,
 // before any packets have been muxed. FFmpeg's empty_moov otherwise writes zero.
@@ -445,9 +463,195 @@ static int init_duration(uint8_t *p,int size,double seconds,uint32_t *movie_scal
     }
     return 0;
 }
+// r30 (owner, build 185: "lets fix restarting when its closed and have it keep progress"): a streamed conversion can
+// carry on after Kodi is closed instead of starting the movie again at 0%.
+// - The movie's boxes are parsed on their way out. Packets go to the muxer one at a time (av_write_frame) and the
+//   output is flushed after each, so every fragment holds exactly the packets written between two fragment starts.
+// - A *mark* is a fragment that starts with a video keyframe (for a re-encoded picture: where a unit, and so a fresh
+//   encoder, starts). With kodi_airplay_prepare_marks(1) the caller gets each mark as text through write(-1, "mark"):
+//   its byte offset, its fragment number, where every input stood (the next packet of each), every track's decode time
+//   there, the picture subtitle files' lengths and the fragment index entries before it. Everything before the mark is
+//   complete fragments; the caller keeps Drive's upload at or before a mark and saves the latest one.
+// - kodi_airplay_prepare_resume(input, mark text, ...) writes the same movie from that mark on: the inputs start at
+//   their recorded packets, the new init is dropped, fragment numbers continue and each fragment's decode time (tfdt,
+//   which FFmpeg counts from the first packet it was given) is moved onto the first run's timeline.
+// - FFmpeg's fragment index (mfra) only knows its own run, so it is turned off and built here from every fragment,
+//   the way FFmpeg builds it, in both runs.
+#define MARK_TRACK (-1)
+static int marks_on=0;
+void kodi_airplay_prepare_marks(int on) { marks_on=on!=0; }
+typedef struct {int64_t pos,dts;double t;int si,eof;} in_mark;
+typedef struct {int markable;in_mark in[TRACKS];int64_t side[TRACKS];} prep_state;
+typedef struct {int64_t end,start,shift;int has_start;} out_track;   // by MP4 track_ID - 1 (= output stream index)
+typedef struct {uint32_t id;int64_t time,offset;} tfra_entry;
+typedef struct resume_ctx {
+    int resume;int64_t resume_at;uint32_t resume_seq;int64_t at;
+    uint8_t head[16];int head_len;uint64_t left;int in_moof;int64_t box_start;
+    uint8_t *moof;int moof_size,moof_len;
+    out_track tracks[TRACKS];int nstreams,ninputs,shift_known,moofs,marks;
+    int64_t base[TRACKS];
+    tfra_entry *tfra;int ntfra,cap,emitted;
+    prep_state frag_start,pending,resumed;
+    char layout[600];
+    AVFormatContext **side;
+} resume_ctx;
+static int rc_forward(output_sink *s,const uint8_t *d,int n) {
+    if(n<=0)return 1;
+    if(!s->write(0,s->suffix,d,n,s->context))return 0;
+    s->rc->at+=n;return 1;
+}
+static int tfra_add(resume_ctx *rc,uint32_t id,int64_t time,int64_t offset) {
+    if(rc->ntfra==rc->cap){int c=rc->cap?rc->cap*2:1024;tfra_entry *g=realloc(rc->tfra,sizeof *g*(size_t)c);if(!g)return -1;rc->tfra=g;rc->cap=c;}
+    rc->tfra[rc->ntfra++]=(tfra_entry){id,time,offset};return 0;
+}
+// One moof: each traf's tfdt moves onto the first run's timeline (base, 0 without a resume), its end and its index
+// entry (FFmpeg: time = first dts + first cts, at least 0; offset = the moof) are noted.
+static int moof_parse(resume_ctx *rc,uint8_t *m,int size,int64_t offset) {
+    for(int at=8;at+8<=size;) {
+        uint32_t n=AV_RB32(m+at),type=AV_RB32(m+at+4);if(n<8 || n>(uint32_t)(size-at))return -1;
+        uint8_t *b=m+at;
+        if(type==MKBETAG('t','r','a','f')) {
+            uint32_t id=0,defdur=0;int have=0,v1=0,samples=0;uint8_t *tfdt=NULL;int64_t dur=0,cts=0;
+            for(uint32_t t=8;t+8<=n;) {
+                uint32_t cn=AV_RB32(b+t),ct=AV_RB32(b+t+4);if(cn<8 || cn>n-t)return -1;uint8_t *c=b+t;
+                if(ct==MKBETAG('t','f','h','d') && cn>=16) {
+                    uint32_t fl=AV_RB24(c+9),q=16;id=AV_RB32(c+12);have=1;
+                    if(fl&1)q+=8;if(fl&2)q+=4;
+                    if(fl&8){if(q+4>cn)return -1;defdur=AV_RB32(c+q);}
+                } else if(ct==MKBETAG('t','f','d','t') && cn>=16) {
+                    v1=c[8]==1;if(v1 && cn<20)return -1;tfdt=c+12;
+                } else if(ct==MKBETAG('t','r','u','n') && cn>=16) {
+                    int version=c[8];uint32_t fl=AV_RB24(c+9),count=AV_RB32(c+12),q=16;
+                    if(fl&1)q+=4;if(fl&4)q+=4;
+                    uint32_t per=((fl&0x100)?4:0)+((fl&0x200)?4:0)+((fl&0x400)?4:0)+((fl&0x800)?4:0);
+                    if((uint64_t)q+(uint64_t)per*count>cn)return -1;
+                    for(uint32_t i=0;i<count;i++) {
+                        uint8_t *e=c+q+per*i;uint32_t k=0;
+                        dur+=(fl&0x100)?AV_RB32(e):defdur;if(fl&0x100)k+=4;if(fl&0x200)k+=4;if(fl&0x400)k+=4;
+                        if(!samples && (fl&0x800))cts=version?(int64_t)(int32_t)AV_RB32(e+k):(int64_t)AV_RB32(e+k);
+                        samples++;
+                    }
+                }
+                t+=cn;
+            }
+            if(!have || !tfdt || id<1 || id>TRACKS)return -1;
+            int64_t value=(v1?(int64_t)AV_RB64(tfdt):(int64_t)AV_RB32(tfdt))+rc->base[id-1];
+            if(v1)AV_WB64(tfdt,(uint64_t)value);
+            else {if(value<0 || value>UINT32_MAX)return -1;AV_WB32(tfdt,(uint32_t)value);}
+            out_track *tr=&rc->tracks[id-1];
+            if(samples) {
+                int64_t time=value+(tr->has_start?tr->start:0)+cts;
+                if(tfra_add(rc,id,time<0?0:time,offset)<0)return -1;
+            }
+            tr->end=value+dur;
+        }
+        at+=(int)n;
+    }
+    return 0;
+}
+static uint32_t moof_seq(const uint8_t *m,int size) {
+    for(int at=8;at+16<=size;){uint32_t n=AV_RB32(m+at);if(n<8 || n>(uint32_t)(size-at))return 0;
+        if(AV_RB32(m+at+4)==MKBETAG('m','f','h','d'))return AV_RB32(m+at+12);at+=(int)n;}
+    return 0;
+}
+static int rc_mark(output_sink *s,int64_t offset,uint32_t seq) {
+    resume_ctx *rc=s->rc;prep_state *st=&rc->frag_start;
+    // The subtitle files' bytes up to here reach the caller first, so the lengths in the mark are all with it.
+    for(int i=0;i<TRACKS;i++)if(rc->side && rc->side[i] && rc->side[i]->pb){avio_flush(rc->side[i]->pb);if(rc->side[i]->pb->error<0)return 0;}
+    AVBPrint b;av_bprint_init(&b,0,AV_BPRINT_SIZE_UNLIMITED);
+    av_bprintf(&b,"kr-resume 1\noffset %lld\nseq %u\nlayout %s\n",(long long)offset,seq,rc->layout);
+    for(int i=0;i<rc->ninputs;i++){in_mark *m=&st->in[i];
+        av_bprintf(&b,"in %d %d %lld %d %lld %.6f\n",i,m->eof,(long long)m->pos,m->si,(long long)m->dts,m->t);}
+    for(int k=0;k<rc->nstreams;k++){out_track *t=&rc->tracks[k];
+        av_bprintf(&b,"track %d %lld %d %lld %lld\n",k+1,(long long)t->end,t->has_start,(long long)t->start,(long long)t->shift);}
+    for(int i=0;i<TRACKS;i++)if(rc->side && rc->side[i])av_bprintf(&b,"side %d %lld\n",i,(long long)st->side[i]);
+    for(;rc->emitted<rc->ntfra && rc->tfra[rc->emitted].offset<offset;rc->emitted++){tfra_entry *e=&rc->tfra[rc->emitted];
+        av_bprintf(&b,"tfra %u %lld %lld\n",e->id,(long long)e->time,(long long)e->offset);}
+    int ok=av_bprint_is_complete(&b) && s->write(MARK_TRACK,"mark",(const uint8_t*)b.str,(int)b.len,s->context);
+    av_bprint_finalize(&b,NULL);rc->marks++;
+    return ok;
+}
+static int moof_done(output_sink *s) {
+    resume_ctx *rc=s->rc;int64_t offset=rc->box_start;
+    // A fragment that starts on a picture keyframe, after the first of this run, is a place to carry on from.
+    if(marks_on && rc->frag_start.markable && rc->moofs>0 && !rc_mark(s,offset,moof_seq(rc->moof,rc->moof_size)))return -1;
+    if(moof_parse(rc,rc->moof,rc->moof_size,offset)<0)return -1;
+    if(!rc_forward(s,rc->moof,rc->moof_size))return -1;
+    rc->moofs++;rc->frag_start=rc->pending;   // the packet being written now starts the next fragment
+    return 0;
+}
+static int out_feed(output_sink *s,const uint8_t *d,int n) {
+    resume_ctx *rc=s->rc;
+    while(n>0) {
+        if(rc->in_moof) {
+            int take=FFMIN(n,rc->moof_size-rc->moof_len);memcpy(rc->moof+rc->moof_len,d,(size_t)take);rc->moof_len+=take;d+=take;n-=take;
+            if(rc->moof_len==rc->moof_size){int q=moof_done(s);av_freep(&rc->moof);rc->in_moof=0;if(q<0)return 0;}
+            continue;
+        }
+        if(rc->left>0) {
+            int take=(int)FFMIN((uint64_t)n,rc->left);if(!rc_forward(s,d,take))return 0;
+            if(rc->left!=UINT64_MAX)rc->left-=(uint64_t)take;d+=take;n-=take;continue;
+        }
+        rc->head[rc->head_len++]=*d++;n--;
+        if(rc->head_len<8)continue;
+        uint64_t size=AV_RB32(rc->head);
+        if(size==1){if(rc->head_len<16)continue;size=AV_RB64(rc->head+8);}
+        int hl=rc->head_len;uint32_t type=AV_RB32(rc->head+4);rc->box_start=rc->at;rc->head_len=0;
+        if(size && size<(uint64_t)hl)return 0;
+        if(type==MKBETAG('m','o','o','f')) {
+            if(size>64*1024*1024)return 0;
+            rc->moof=av_malloc((size_t)size);if(!rc->moof)return 0;
+            memcpy(rc->moof,rc->head,(size_t)hl);rc->moof_len=hl;rc->moof_size=(int)size;rc->in_moof=1;
+        } else {
+            if(!rc_forward(s,rc->head,hl))return 0;
+            rc->left=size?size-(uint64_t)hl:UINT64_MAX;
+        }
+    }
+    return 1;
+}
+// FFmpeg's mfra, from every fragment of both runs: one tfra per track (track order), then mfro with the mfra size.
+static int write_mfra(output_sink *s) {
+    resume_ctx *rc=s->rc;AVBPrint b;av_bprint_init(&b,0,AV_BPRINT_SIZE_UNLIMITED);
+    uint8_t w[19];
+    av_bprint_append_data(&b,"\0\0\0\0mfra",8);
+    for(int k=1;k<=rc->nstreams;k++) {
+        int count=0;for(int i=0;i<rc->ntfra;i++)count+=rc->tfra[i].id==(uint32_t)k;
+        if(!count)continue;
+        uint8_t h[24];AV_WB32(h,(uint32_t)(24+19*count));memcpy(h+4,"tfra",4);AV_WB32(h+8,0x01000000);AV_WB32(h+12,(uint32_t)k);AV_WB32(h+16,0);AV_WB32(h+20,(uint32_t)count);
+        av_bprint_append_data(&b,(const char*)h,24);
+        for(int i=0;i<rc->ntfra;i++)if(rc->tfra[i].id==(uint32_t)k){
+            AV_WB64(w,(uint64_t)rc->tfra[i].time);AV_WB64(w+8,(uint64_t)rc->tfra[i].offset);w[16]=w[17]=w[18]=1;
+            av_bprint_append_data(&b,(const char*)w,19);}
+    }
+    uint8_t f[16];AV_WB32(f,16);memcpy(f+4,"mfro",4);AV_WB32(f+8,0);AV_WB32(f+12,(uint32_t)(b.len+16));
+    av_bprint_append_data(&b,(const char*)f,16);
+    int ok=av_bprint_is_complete(&b);
+    if(ok){AV_WB32((uint8_t*)b.str,(uint32_t)b.len);ok=rc_forward(s,(const uint8_t*)b.str,(int)b.len);}
+    av_bprint_finalize(&b,NULL);return ok?0:-1;
+}
+// Parse a mark (the text rc_mark wrote, with the tfra lines of every earlier mark) into a fresh context.
+static int rc_load(resume_ctx *rc,const char *text,int *ninputs) {
+    const char *at=text;int version=0;*ninputs=0;
+    if(sscanf(at,"kr-resume %d",&version)!=1 || version!=1)return -1;
+    while((at=strchr(at,'\n'))) {
+        at++;long long a,b2,c;int i,e,si,h;double t;unsigned id;
+        if(sscanf(at,"offset %lld",&a)==1)rc->resume_at=a;
+        else if(sscanf(at,"seq %u",&id)==1)rc->resume_seq=id;
+        else if(!strncmp(at,"layout ",7)){const char *end=strchr(at,'\n');size_t n=end?(size_t)(end-at-7):strlen(at+7);if(n>=sizeof rc->layout)return -1;memcpy(rc->layout,at+7,n);rc->layout[n]=0;}
+        else if(sscanf(at,"in %d %d %lld %d %lld %lf",&i,&e,&a,&si,&b2,&t)==6){if(i<0 || i>=TRACKS)return -1;
+            rc->resumed.in[i]=(in_mark){a,b2,t,si,e};if(i+1>*ninputs)*ninputs=i+1;}
+        else if(sscanf(at,"track %d %lld %d %lld %lld",&i,&a,&h,&b2,&c)==5){if(i<1 || i>TRACKS)return -1;
+            rc->base[i-1]=a;rc->tracks[i-1].end=a;rc->tracks[i-1].has_start=h;rc->tracks[i-1].start=b2;rc->tracks[i-1].shift=c;}
+        else if(sscanf(at,"side %d %lld",&i,&a)==2){if(i<0 || i>=TRACKS)return -1;rc->resumed.side[i]=a;}
+        else if(sscanf(at,"tfra %u %lld %lld",&id,&a,&b2)==3){if(b2>=rc->resume_at)continue;if(tfra_add(rc,id,a,b2)<0)return -1;}
+    }
+    if(rc->resume_at<=0 || !rc->resume_seq || !rc->layout[0] || !*ninputs)return -1;
+    rc->resume=1;rc->shift_known=1;rc->emitted=rc->ntfra;return 0;
+}
 static int sink_write(void *opaque,const uint8_t *data,int size) {
     output_sink *s=opaque;
-    if(s->track || s->initialized)return s->write(s->track,s->suffix,data,size,s->context)?size:AVERROR_EXIT;
+    if(s->track || (s->initialized && !s->rc))return s->write(s->track,s->suffix,data,size,s->context)?size:AVERROR_EXIT;
+    if(s->initialized)return out_feed(s,data,size)?size:AVERROR_EXIT;
     // Only the init boxes are buffered, capped independently of movie duration/size.
     if(size<0 || s->init_size>4*1024*1024-size)return AVERROR(ENOMEM);
     uint8_t *grown=av_realloc(s->init,(size_t)(s->init_size+size));if(!grown)return AVERROR(ENOMEM);
@@ -460,8 +664,13 @@ static int sink_write(void *opaque,const uint8_t *data,int size) {
         if(AV_RB32(s->init+at+4)==MKBETAG('m','o','o','v')) {
             uint32_t scale=0;
             if(init_duration(s->init+at,(int)n,s->duration,&scale)<0)return AVERROR_INVALIDDATA;
-            if(!s->write(0,s->suffix,s->init,s->init_size,s->context))return AVERROR_EXIT;
-            av_freep(&s->init);s->init_size=0;s->initialized=1;return size;
+            int end=s->rc?at+(int)n:s->init_size;   // r30: what follows the moov goes through the parser
+            if(!(s->rc && s->rc->resume) && !s->write(0,s->suffix,s->init,end,s->context))return AVERROR_EXIT;   // a resumed run's init is already on Drive
+            if(s->rc)s->rc->at=s->rc->resume?s->rc->resume_at:end;
+            s->initialized=1;
+            int rest=s->init_size-end;uint8_t *init=s->init;s->init=NULL;s->init_size=0;
+            int ok=rest<=0 || out_feed(s,init+end,rest);av_free(init);
+            return ok?size:AVERROR_EXIT;
         }
         at+=(int)n;
     }
@@ -475,7 +684,6 @@ static int sink_open(AVFormatContext *f,output_sink *sink) {
 static void sink_close(AVFormatContext *f) {
     if(f && f->pb){av_freep(&f->pb->buffer);avio_context_free(&f->pb);}
 }
-typedef struct {AVFormatContext *f;AVPacket *packet;int map[TRACKS];int eof;int own;} input_track;
 typedef struct {AVCodecContext *dec,*enc;} subtitle;
 static int next(input_track *in) {
     av_packet_unref(in->packet);
@@ -519,14 +727,81 @@ static int validate(const char *path,AVFormatContext *original,int expected_trac
     av_packet_free(&p);r=0;
 end:avformat_close_input(&f);if(r<0)fail(err,en,"Output validation failed; original retained",0);return r;
 }
+static int put(AVFormatContext *out,resume_ctx *rc,AVPacket *p) {
+    if(!rc)return av_interleaved_write_frame(out,p);
+    if(!rc->shift_known && p->dts!=AV_NOPTS_VALUE) {   // FFmpeg's make-non-negative shift, from the first packet
+        AVRational tb=out->streams[p->stream_index]->time_base;
+        for(unsigned k=0;k<out->nb_streams;k++)rc->tracks[k].shift=p->dts<0?av_rescale_q_rnd(-p->dts,tb,out->streams[k]->time_base,AV_ROUND_UP):0;
+        rc->shift_known=1;
+    }
+    out_track *t=&rc->tracks[p->stream_index];
+    if(!t->has_start && p->dts!=AV_NOPTS_VALUE){t->start=p->dts+t->shift;t->has_start=1;}
+    int q=av_write_frame(out,p);
+    if(q>=0){avio_flush(out->pb);if(out->pb->error<0)q=out->pb->error;}
+    return q;
+}
+// Where every input stands before a packet is written (its next packet), and whether a fragment may start there.
+static int unit_start(generated_reader *g,AVFormatContext *f,AVPacket *p) {
+    gm_stream *plan=NULL;for(int i=0;i<g->nlanes && !plan;i++)if(g->lanes[i])plan=g->lanes[i]->plan;
+    int64_t ts=p->pts!=AV_NOPTS_VALUE?p->pts:p->dts;if(!plan || ts==AV_NOPTS_VALUE)return 0;
+    return resume_unit(plan,ts*av_q2d(f->streams[p->stream_index]->time_base),1)>=0;
+}
+static void snapshot(resume_ctx *rc,input_track *ins,int ninputs,generated_reader *gens,AVFormatContext **side,int pick,int video_out) {
+    prep_state *st=&rc->pending;st->markable=0;
+    for(int i=0;i<ninputs;i++){in_mark *m=&st->in[i];m->eof=ins[i].eof;
+        if(!m->eof){AVPacket *p=ins[i].packet;int64_t ts=p->pts!=AV_NOPTS_VALUE?p->pts:p->dts;
+            m->pos=p->pos;m->si=p->stream_index;m->dts=p->dts;m->t=ts==AV_NOPTS_VALUE?0:ts*av_q2d(ins[i].f->streams[p->stream_index]->time_base);}}
+    for(int i=0;i<TRACKS;i++)st->side[i]=side[i] && side[i]->pb?avio_tell(side[i]->pb):0;
+    AVPacket *p=ins[pick].packet;
+    if(ins[pick].map[p->stream_index]!=video_out || !(p->flags&AV_PKT_FLAG_KEY) || p->dts==AV_NOPTS_VALUE)return;
+    if(pick>0 && !unit_start(&gens[pick],ins[pick].f,p))return;   // a re-encoded picture: only where a unit starts
+    if(!ins[0].eof && (ins[0].packet->pos<0 || ins[0].packet->dts==AV_NOPTS_VALUE))return;
+    for(int i=1;i<ninputs;i++)if(!ins[i].eof && ins[i].packet->dts==AV_NOPTS_VALUE)return;
+    st->markable=1;
+}
+// Bring an input to the packet a mark recorded as its next one; everything before it is already in the movie.
+static int resume_input(input_track *in,const in_mark *m,int original) {
+    if(m->eof){in->eof=1;return 0;}
+    if(!original) {
+        for(int guard=0;guard<10000000;guard++) {
+            if(in->eof)return -1;
+            AVPacket *p=in->packet;
+            if(p->stream_index==m->si && p->dts==m->dts)return 0;
+            if(p->dts!=AV_NOPTS_VALUE && p->dts>m->dts && p->stream_index==m->si)return -1;
+            if(next(in)<0)return -1;
+        }
+        return -1;
+    }
+    for(int back=10;back<=1000;back*=10) {
+        int64_t ts=(int64_t)((m->t-back)*AV_TIME_BASE);if(ts<0)ts=0;
+        if(av_seek_frame(in->f,-1,ts,AVSEEK_FLAG_BACKWARD)<0)return -1;
+        in->eof=0;if(next(in)<0)return -1;
+        int passed=0;
+        while(!in->eof) {
+            AVPacket *p=in->packet;
+            if(p->pos==m->pos && p->stream_index==m->si && p->dts==m->dts)return 0;
+            if(p->pos>m->pos){passed=1;break;}
+            if(next(in)<0)return -1;
+        }
+        if(!passed)return -1;
+        if(ts==0)return -1;
+    }
+    return -1;
+}
 static int prepare(const char *input,const char *output,kr_prepare_progress cb,void *ctx,char *err,int en,
-                   kr_prepare_write writer,void *writer_context) {
+                   kr_prepare_write writer,void *writer_context,const char *resume_text) {
     generated_reader gens[TRACKS]={0};AVIOContext *readers[TRACKS]={0};
     output_sink sinks[TRACKS+1]={0};
     for(int i=0;i<=TRACKS;i++){sinks[i].write=writer;sinks[i].context=writer_context;sinks[i].track=i;}
     snprintf(sinks[0].suffix,sizeof sinks[0].suffix,".mp4");
     AVFormatContext *original=NULL,*out=NULL,*side[TRACKS]={0};input_track ins[TRACKS]={0};subtitle subs[TRACKS]={0};
-    int ninputs=1,r=-1,header=0,mapped=0,skipped_subs=0;char partial[4096],spools[TRACKS][4096]={{0}},sides[TRACKS][4200]={{0}};
+    int ninputs=1,r=-1,header=0,mapped=0,skipped_subs=0,video_out=-1,resumed_inputs=0;
+    resume_ctx *rc=NULL;
+    if(writer) {
+        rc=calloc(1,sizeof *rc);if(!rc)return fail(err,en,"out of memory",0);
+        sinks[0].rc=rc;rc->side=side;
+        if(resume_text && rc_load(rc,resume_text,&resumed_inputs)<0){free(rc->tfra);free(rc);return fail(err,en,"Resume record is not valid",0);}
+    }char partial[4096],spools[TRACKS][4096]={{0}},sides[TRACKS][4200]={{0}};
     if(err && en>0)*err=0;
     if(!local_input(input) || (!writer && (!output || output[0]!='/' || !strcmp(input,output))))return fail(err,en,"A local or loopback input and a separate local output are required",0);
     snprintf(partial,sizeof partial,"%s.partial",output?output:"stream");
@@ -577,7 +852,8 @@ static int prepare(const char *input,const char *output,kr_prepare_progress cb,v
         if(generated) {
             int ni=ninputs++;input_track *one=&ins[ni];one->own=1;
             if(writer) {
-                if(generated_open(&gens[ni],&one->f,&readers[ni],input,(int)i,(int)i==vi,cb,ctx,err,en)<0)goto end;
+                double at=rc && rc->resume && ni<resumed_inputs && !rc->resumed.in[ni].eof?rc->resumed.in[ni].t:-1;
+                if(generated_open(&gens[ni],&one->f,&readers[ni],input,(int)i,(int)i==vi,cb,ctx,err,en,at)<0)goto end;
                 one->f->probesize=2*1024*1024;one->f->max_analyze_duration=AV_TIME_BASE;
                 if(avformat_find_stream_info(one->f,NULL)<0){fail(err,en,"Converted track inspection failed",0);goto end;}
             } else {
@@ -586,7 +862,7 @@ static int prepare(const char *input,const char *output,kr_prepare_progress cb,v
                 if(avformat_open_input(&one->f,spools[i],NULL,NULL)<0 || avformat_find_stream_info(one->f,NULL)<0)goto end;
             }
             if(one->f->nb_streams!=1)goto end;
-            one->map[0]=dst->index;avcodec_parameters_copy(dst->codecpar,one->f->streams[0]->codecpar);
+            one->map[0]=dst->index;if((int)i==vi)video_out=dst->index;avcodec_parameters_copy(dst->codecpar,one->f->streams[0]->codecpar);
             dst->codecpar->codec_tag=0;dst->time_base=one->f->streams[0]->time_base;
             // Preserve static HDR metadata when another HDR codec is encoded to HEVC Main10.
             if((int)i==vi)for(int m=0;m<p->nb_coded_side_data;m++) {
@@ -596,7 +872,7 @@ static int prepare(const char *input,const char *output,kr_prepare_progress cb,v
                 if(!to)goto end;memcpy(to->data,from->data,from->size);
             }
         } else {
-            ins[0].map[i]=dst->index;
+            ins[0].map[i]=dst->index;if((int)i==vi)video_out=dst->index;
             if(p->codec_type==AVMEDIA_TYPE_SUBTITLE && p->codec_id!=AV_CODEC_ID_MOV_TEXT) {
                 subtitle *s=&subs[i];const AVCodec *dc=avcodec_find_decoder(p->codec_id),*ec=avcodec_find_encoder(AV_CODEC_ID_MOV_TEXT);
                 if(!dc || !ec){fail(err,en,"Subtitle encoder unavailable",0);goto end;}
@@ -620,10 +896,23 @@ static int prepare(const char *input,const char *output,kr_prepare_progress cb,v
     av_dict_set(&out->metadata,"kodi_airplay_prepared","source-resolution-v1",0);
     out->avoid_negative_ts=AVFMT_AVOID_NEG_TS_MAKE_NON_NEGATIVE;
     if((writer?sink_open(out,&sinks[0]):avio_open(&out->pb,partial,AVIO_FLAG_WRITE))<0)goto end;
-    AVDictionary *opts=NULL;av_dict_set(&opts,"movflags",writer?"+empty_moov+default_base_moof+frag_keyframe+use_metadata_tags":"+faststart+use_metadata_tags",0);
+    if(rc) {
+        // The same source, settings and framework give the same tracks; a mark from anything else starts over.
+        char layout[sizeof rc->layout];int n=snprintf(layout,sizeof layout,"%u/%d",out->nb_streams,ninputs);
+        for(unsigned k=0;k<out->nb_streams && n<(int)sizeof layout-16;k++)n+=snprintf(layout+n,sizeof layout-(size_t)n,"/%d",(int)out->streams[k]->codecpar->codec_id);
+        for(int k=0;k<TRACKS && n<(int)sizeof layout-16;k++)if(side[k])n+=snprintf(layout+n,sizeof layout-(size_t)n,"/s%d",k);
+        if(rc->resume && (strcmp(layout,rc->layout) || resumed_inputs!=ninputs)){fail(err,en,"Resume record does not match this video",0);goto end;}
+        snprintf(rc->layout,sizeof rc->layout,"%s",layout);rc->nstreams=(int)out->nb_streams;rc->ninputs=ninputs;
+    }
+    AVDictionary *opts=NULL;av_dict_set(&opts,"movflags",writer?"+empty_moov+default_base_moof+frag_keyframe+use_metadata_tags+skip_trailer":"+faststart+use_metadata_tags",0);
     if(writer)av_dict_set(&opts,"frag_duration","6000000",0);
+    if(rc && rc->resume)av_dict_set_int(&opts,"fragment_index",rc->resume_seq,0);
     int q=avformat_write_header(out,&opts);av_dict_free(&opts);if(q<0){fail(err,en,"MP4 header",q);goto end;}header=1;
     for(int i=0;i<ninputs;i++){ins[i].packet=av_packet_alloc();if(!ins[i].packet || next(&ins[i])<0)goto end;}
+    if(rc && rc->resume) {
+        for(int i=0;i<ninputs;i++)if(resume_input(&ins[i],&rc->resumed.in[i],i==0)<0){fail(err,en,"Resume position not found",0);goto end;}
+        kr_remux_note("prepare: carrying on from %.0f s (byte %lld, fragment %u)",rc->resumed.in[0].eof?rc->resumed.in[ninputs>1?1:0].t:rc->resumed.in[0].t,(long long)rc->resume_at,rc->resume_seq);
+    }
     unsigned packets=0;
     for(;;) {
         int pick=-1;double earliest=0;
@@ -643,6 +932,7 @@ static int prepare(const char *input,const char *output,kr_prepare_progress cb,v
             continue;
         }
         AVStream *src=in->f->streams[si],*dst=out->streams[di];
+        if(rc)snapshot(rc,ins,ninputs,gens,side,pick,video_out);
         if(pick==0 && subs[si].dec) {
             AVSubtitle sub={0};int got=0;
             q=avcodec_decode_subtitle2(subs[si].dec,&sub,&got,p);
@@ -656,12 +946,12 @@ static int prepare(const char *input,const char *output,kr_prepare_progress cb,v
                 int64_t base=p->pts==AV_NOPTS_VALUE?0:av_rescale_q(p->pts,src->time_base,dst->time_base);
                 encoded->pts=encoded->dts=base+av_rescale_q(sub.start_display_time,(AVRational){1,1000},dst->time_base);
                 encoded->duration=av_rescale_q(sub.end_display_time-sub.start_display_time,(AVRational){1,1000},dst->time_base);
-                q=av_interleaved_write_frame(out,encoded);av_packet_free(&encoded);
+                q=put(out,rc,encoded);av_packet_free(&encoded);
             }
             avsubtitle_free(&sub);
         } else {
             av_packet_rescale_ts(p,src->time_base,dst->time_base);p->stream_index=di;p->pos=-1;
-            q=av_interleaved_write_frame(out,p);
+            q=put(out,rc,p);
         }
         if(q<0){fail(err,en,"MP4 packet",q);goto end;}
         q=next(in);if(q<0){fail(err,en,"Source read",q);goto end;}
@@ -669,6 +959,7 @@ static int prepare(const char *input,const char *output,kr_prepare_progress cb,v
     if(!tick(cb,ctx,3,0,1)){r=-2;goto end;}
     q=av_write_trailer(out);header=0;
     if(writer){avio_flush(out->pb);if(out->pb->error<0)q=out->pb->error;}
+    if(rc && q>=0 && (rc->in_moof || write_mfra(&sinks[0])<0))q=AVERROR_EXIT;
     if(q<0 || (!writer && avio_closep(&out->pb)<0)){fail(err,en,"MP4 finalization",q);goto end;}
     for(int i=0;i<TRACKS;i++) if(side[i]) {
         q=av_write_trailer(side[i]);
@@ -696,19 +987,25 @@ end:
     if(out){if(writer)sink_close(out);else if(out->pb)avio_closep(&out->pb);avformat_free_context(out);}
     avformat_close_input(&original);if(r && !writer)unlink(partial);
     for(int i=0;i<=TRACKS;i++)av_free(sinks[i].init);
+    if(rc){av_free(rc->moof);free(rc->tfra);free(rc);}
     if(r==-1 && err && en>0 && !*err)fail(err,en,"Preparation failed; original retained",0);
     return r;
 }
 
 int kodi_airplay_prepare(const char *input,const char *output,kr_prepare_progress cb,void *ctx,char *err,int en) {
-    return prepare(input,output,cb,ctx,err,en,NULL,NULL);
+    return prepare(input,output,cb,ctx,err,en,NULL,NULL,NULL);
 }
 // Non-seekable output with a completed fragment index (mfra). The caller must remotely
 // validate the completed file before replacing the original; successful generation alone is insufficient.
 int kodi_airplay_prepare_to(const char *input,kr_prepare_write write,void *write_context,
                             kr_prepare_progress cb,void *ctx,char *err,int en) {
     if(!write)return fail(err,en,"Output callback is required",0);
-    return prepare(input,NULL,cb,ctx,err,en,write,write_context);
+    return prepare(input,NULL,cb,ctx,err,en,write,write_context,NULL);
+}
+int kodi_airplay_prepare_resume(const char *input,const char *resume,kr_prepare_write write,void *write_context,
+                                kr_prepare_progress cb,void *ctx,char *err,int en) {
+    if(!write || !resume)return fail(err,en,"Output callback and resume record are required",0);
+    return prepare(input,NULL,cb,ctx,err,en,write,write_context,resume);
 }
 
 int kodi_airplay_verify(const char *input,const char *output,char *err,int en) {
diff --git a/migration/airplay-ios/remux/src/kr_prepare.h b/migration/airplay-ios/remux/src/kr_prepare.h
index 71b39b8..d6b46a8 100644
--- a/migration/airplay-ios/remux/src/kr_prepare.h
+++ b/migration/airplay-ios/remux/src/kr_prepare.h
@@ -27,5 +27,10 @@ int kodi_airplay_prepare(const char *input, const char *output, kr_prepare_progr
 typedef int (*kr_prepare_write)(int track,const char *suffix,const uint8_t *data,int size,void *context);
 int kodi_airplay_prepare_to(const char *input,kr_prepare_write write,void *write_context,
                            kr_prepare_progress progress,void *context,char *error,int error_size);
+// r30: marks (write(-1, "mark", text)) where a conversion can carry on, and carrying on from one (the text of the
+// latest mark plus the tfra lines of all earlier ones). The resumed output starts at the mark's byte offset.
+void kodi_airplay_prepare_marks(int on);
+int kodi_airplay_prepare_resume(const char *input,const char *resume,kr_prepare_write write,void *write_context,
+                                kr_prepare_progress progress,void *context,char *error,int error_size);
 int kodi_airplay_verify(const char *input,const char *output,char *error,int error_size);
 #endif
diff --git a/migration/airplay-ios/remux/tests/run_host_tests.sh b/migration/airplay-ios/remux/tests/run_host_tests.sh
index 1baf7d2..ee183d5 100755
--- a/migration/airplay-ios/remux/tests/run_host_tests.sh
+++ b/migration/airplay-ios/remux/tests/run_host_tests.sh
@@ -26,6 +26,11 @@ if [[ ! -f "$WORK/fixtures/long_pgs.mkv" ]]; then
   ffmpeg -hide_banner -loglevel error -y -copyts -stream_loop 3 -i "$WORK/fixtures/h264_aac_srt.mkv" -i "$WORK/fixtures/long.sup" \
     -map 0:v -map 0:a -map 1:s -c copy -t 65 -disposition:s:0 default "$WORK/fixtures/long_pgs.mkv"
 fi
+# r30: a re-encoded picture (MPEG-2) and audio (AC-3) longer than two 30-second units, for carrying on from a mark.
+if [[ ! -f "$WORK/fixtures/resume_mpeg2.mkv" ]]; then
+  ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=128x72:rate=24:duration=75' -f lavfi -i 'sine=frequency=440:duration=75' \
+    -c:v mpeg2video -g 12 -c:a ac3 -b:a 96k "$WORK/fixtures/resume_mpeg2.mkv"
+fi
 # Long sparse fixture proves an actual twenty-minute MP4 seek without a large test download.
 if [[ ! -f "$WORK/fixtures/long_seek.mkv" ]]; then
   ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=64x36:rate=1:duration=1300' \
diff --git a/migration/airplay-ios/remux/tests/test_remux.c b/migration/airplay-ios/remux/tests/test_remux.c
index 763195c..6befbb7 100644
--- a/migration/airplay-ios/remux/tests/test_remux.c
+++ b/migration/airplay-ios/remux/tests/test_remux.c
@@ -1459,6 +1459,85 @@ static void test_hdr_preparation(const char *work,const char *http_base) {
     kr_video_set_hdr_encoder(NULL);
 }
 
+// r30: a conversion carries on from a mark after the app is closed. A straight run collects the marks; a run from a
+// middle mark, after the first run's bytes up to it, gives the same movie (byte for byte when nothing is re-encoded).
+typedef struct {uint8_t *data[65];size_t len[65],cap[65];char *marks[4096];int nmarks;int stop_after_marks;} resume_sink;
+static int resume_write(int track,const char *suffix,const uint8_t *data,int size,void *context) {
+    resume_sink *r=context;(void)suffix;
+    if(track==-1){if(r->nmarks>=4096)return 0;char *m=malloc((size_t)size+1);if(!m)return 0;memcpy(m,data,(size_t)size);m[size]=0;r->marks[r->nmarks++]=m;
+        return !(r->stop_after_marks && r->nmarks>=r->stop_after_marks);}
+    if(track<0 || track>=65)return 0;
+    if(r->len[track]+(size_t)size>r->cap[track]){size_t c=(r->len[track]+(size_t)size)*2;uint8_t *g=realloc(r->data[track],c);if(!g)return 0;r->data[track]=g;r->cap[track]=c;}
+    memcpy(r->data[track]+r->len[track],data,(size_t)size);r->len[track]+=(size_t)size;return 1;
+}
+static void resume_free(resume_sink *r){for(int i=0;i<65;i++)free(r->data[i]);for(int i=0;i<r->nmarks;i++)free(r->marks[i]);memset(r,0,sizeof *r);}
+static long long mark_value(const char *mark,const char *key) {
+    char k[64];snprintf(k,sizeof k,"\n%s ",key);const char *at=strstr(mark,k);return at?atoll(at+strlen(k)):-1;
+}
+static long long side_length(const char *mark,int track) {
+    char k[64];snprintf(k,sizeof k,"\nside %d ",track);const char *at=strstr(mark,k);return at?atoll(at+strlen(k)):-1;
+}
+// What the add-on saves: the chosen mark without its tfra lines, then every tfra line up to and including it.
+static char *resume_record(resume_sink *r,int chosen) {
+    size_t cap=1<<20,len=0;char *out=malloc(cap);if(!out)return NULL;out[0]=0;
+    const char *m=r->marks[chosen];
+    for(const char *line=m;line && *line;) {const char *end=strchr(line,'\n');size_t n=end?(size_t)(end-line+1):strlen(line);
+        if(strncmp(line,"tfra ",5)){if(len+n+1>cap)break;memcpy(out+len,line,n);len+=n;out[len]=0;}line=end?end+1:NULL;}
+    for(int i=0;i<=chosen;i++)for(const char *line=strstr(r->marks[i],"\ntfra ");line;line=strstr(line+1,"\ntfra ")) {
+        const char *end=strchr(line+1,'\n');size_t n=end?(size_t)(end-line):strlen(line);
+        if(len+n+2>cap){cap*=2;char *g=realloc(out,cap);if(!g){free(out);return NULL;}out=g;}
+        memcpy(out+len,line+1,n);len+=n;if(!end){out[len++]='\n';}out[len]=0;
+    }
+    return out;
+}
+static int save_bytes(const char *path,const uint8_t *a,size_t na,const uint8_t *b,size_t nb) {
+    FILE *f=fopen(path,"wb");if(!f)return -1;int ok=fwrite(a,1,na,f)==na && (!nb || fwrite(b,1,nb,f)==nb);return fclose(f)||!ok?-1:0;
+}
+static void test_preparation_resume(const char *work,const char *http_base) {
+    struct {const char *file;int same;} cases[]={{"long_seek.mkv",1},{"long_pgs.mkv",1},{"h264_ac3_dts_srt.mkv",0},{"resume_mpeg2.mkv",0}};
+    kodi_airplay_prepare_keep_image_subs(1);kr_video_set_encoder("mpeg4");kodi_airplay_prepare_marks(1);
+    for(unsigned c=0;c<sizeof cases/sizeof cases[0];c++) {
+        char input[1024],err[512]="",path[1200],remote[1300];int calls=0;
+        snprintf(input,sizeof input,"%s/%s",http_base,cases[c].file);
+        resume_sink full={0},more={0};
+        int r=kodi_airplay_prepare_to(input,resume_write,&full,preparation_progress,&calls,err,sizeof err);
+        CHECK(r==0,"resume %s: straight run: %s",cases[c].file,err);
+        CHECK(full.nmarks>=1,"resume %s: the straight run gives marks (%d)",cases[c].file,full.nmarks);
+        snprintf(path,sizeof path,"%s/resume-full-%u.mp4",fixture_dir,c);snprintf(remote,sizeof remote,"%s/resume-full-%u.mp4",http_base,c);
+        if(r || !full.nmarks || save_bytes(path,full.data[0],full.len[0],NULL,0)){resume_free(&full);continue;}
+        CHECK(kodi_airplay_verify(input,remote,err,sizeof err)==0,"resume %s: the straight run with its own index validates: %s",cases[c].file,err);
+        int chosen=full.nmarks/2;long long at=mark_value(full.marks[chosen],"offset");
+        CHECK(at>0 && at<(long long)full.len[0],"resume %s: mark %d at byte %lld of %zu",cases[c].file,chosen,at,full.len[0]);
+        char *record=resume_record(&full,chosen);
+        r=record?kodi_airplay_prepare_resume(input,record,resume_write,&more,preparation_progress,&calls,err,sizeof err):-1;
+        CHECK(r==0,"resume %s: carrying on from mark %d: %s",cases[c].file,chosen,err);
+        if(!r) {
+            snprintf(path,sizeof path,"%s/resume-joined-%u.mp4",fixture_dir,c);snprintf(remote,sizeof remote,"%s/resume-joined-%u.mp4",http_base,c);
+            save_bytes(path,full.data[0],(size_t)at,more.data[0],more.len[0]);
+            CHECK(kodi_airplay_verify(input,remote,err,sizeof err)==0,"resume %s: the joined movie validates: %s",cases[c].file,err);
+            size_t joined=(size_t)at+more.len[0];
+            if(cases[c].same)CHECK(joined==full.len[0] && !memcmp(full.data[0]+at,more.data[0],more.len[0]),"resume %s: the joined movie is the straight one (%zu / %zu bytes)",cases[c].file,joined,full.len[0]);
+            uint8_t a[16],b[16];int w,h,n,w2,h2,n2;char straight[1300];snprintf(straight,sizeof straight,"%s/resume-full-%u.mp4",fixture_dir,c);
+            CHECK(video_digest(straight,a,&w,&h,&n)==0 && video_digest(path,b,&w2,&h2,&n2)==0 && n==n2 && (!cases[c].same || !memcmp(a,b,16)),"resume %s: same tracks and picture",cases[c].file);
+            for(int t=1;t<65;t++)if(full.len[t]) {
+                long long keep=side_length(full.marks[chosen],t-1);
+                CHECK(keep>=0 && keep<=(long long)full.len[t] && keep+(long long)more.len[t]==(long long)full.len[t] && !memcmp(full.data[t]+keep,more.data[t],more.len[t]),
+                      "resume %s: picture subtitles carry on (%lld + %zu of %zu)",cases[c].file,keep,more.len[t],full.len[t]);
+            }
+        }
+        // A mark from another video (other tracks) is refused before anything is written.
+        if(record && c==0) {
+            resume_sink other={0};char wrong[1024];snprintf(wrong,sizeof wrong,"%s/h264_aac_srt.mkv",http_base);
+            CHECK(kodi_airplay_prepare_resume(wrong,record,resume_write,&other,preparation_progress,&calls,err,sizeof err)<0 && !other.len[0],"resume: a mark from another video is refused: %s",err);
+            resume_free(&other);
+            CHECK(kodi_airplay_prepare_resume(input,"kr-resume 9\n",resume_write,&other,preparation_progress,&calls,err,sizeof err)<0,"resume: a bad record is refused");
+            resume_free(&other);
+        }
+        free(record);resume_free(&full);resume_free(&more);
+    }
+    kodi_airplay_prepare_marks(0);
+}
+
 // r25: only the original (first) audio track and the chosen languages are kept; verification uses the same rule.
 static int audio_tracks(const char *path) {
     AVFormatContext *f=NULL;int n=-1;
@@ -1634,7 +1713,10 @@ int main(int argc, char **argv) {
     char work[512]; snprintf(work, sizeof work, "%s/out", argv[1]);
     mkdir(work, 0755);
     if (argc > 3 && !strcmp(argv[3], "--prepare-only")) {
-        test_preparation(work);test_audio_languages(work);test_preparation_http(argv[2],work);test_preparation_stream(work,argv[2]);test_hdr_preparation(work,argv[2]);printf("%d checks, %d failed\n",checks,failures);return failures?1:0;
+        test_preparation(work);test_audio_languages(work);test_preparation_http(argv[2],work);test_preparation_stream(work,argv[2]);test_hdr_preparation(work,argv[2]);test_preparation_resume(work,argv[2]);printf("%d checks, %d failed\n",checks,failures);return failures?1:0;
+    }
+    if (argc > 3 && !strcmp(argv[3], "--resume-only")) {
+        test_preparation_resume(work,argv[2]);printf("%d checks, %d failed\n",checks,failures);return failures?1:0;
     }
     if (argc > 3 && !strcmp(argv[3], "--dovi-only")) {
         kr_video_set_encoder("mpeg4");test_dovi_render(work);
@@ -1649,7 +1731,7 @@ int main(int argc, char **argv) {
         return failures ? 1 : 0;
     }
     test_preparation(work);test_audio_languages(work);
-    if (argc > 2){test_preparation_http(argv[2], work);test_preparation_stream(work,argv[2]);test_hdr_preparation(work,argv[2]);}
+    if (argc > 2){test_preparation_http(argv[2], work);test_preparation_stream(work,argv[2]);test_hdr_preparation(work,argv[2]);test_preparation_resume(work,argv[2]);}
     fixture fx[] = {
         { "h264_aac_srt.mkv", "avc1.42C0", "mp4a.40.2", 1, 1, 0, 0, "Hello from SRT" },
         { "hevc_ac3_ass.mkv", "hvc1.2.4.L", "ac-3", 1, 1, 1, 0, "Hello from ASS" },
```
