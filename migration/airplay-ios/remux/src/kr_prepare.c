// One-file preparation: preserve H.264/HEVC packets (including 4K/HDR/Dolby metadata),
// bridge other SDR video at its ORIGINAL dimensions, AAC audio, selectable text subtitles,
// and a front-loaded MP4 sample index. No conversion or speculative segment queue at playback.
#include "kr_prepare.h"
#include "kr_remux.h"
#include <time.h>
#include <string.h>
#include <stdatomic.h>
#include <unistd.h>
#include "kr_video.h"
#include "kr_audio.h"
#include "kr_source.h"
#include "kr_upscale.h"
#include <libavcodec/avcodec.h>
#include <libavutil/pixdesc.h>
#include <libavutil/dovi_meta.h>
#include <libavutil/mathematics.h>
#include <libavutil/intreadwrite.h>
#include <libavutil/time.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>
#include <libavutil/bprint.h>
#include "../gmplayer/gm_stream.h"

#define TRACKS 64
// r32: FFmpeg writes a box's size last, by going back in its output buffer; a fragment header (moof) with interleaved
// samples is larger than 32 KB, so the movie's buffer holds 4 MB (picture subtitle files keep 32 KB).
#define SINK_BUFFER (4*1024*1024)
#define PREP_UNIT 30   // seconds per preparation unit (r20; live AirPlay keeps its 6)
#define SIDECAR TRACKS   // map value of a picture subtitle track written beside the MP4 (r15), not into it

// r15 (owner, build 160: "Interstellar ... needs to be ready for airplay"): MP4 cannot hold Blu-ray picture subtitles
// (PGS). With this on, each PGS track is kept, untouched, in its own .sup file beside the prepared MP4
// (output.sub<track>.<language>[.forced].sup); the setup add-on saves them next to the video on Google Drive, where
// Kodi finds them as external subtitles. Off (the default), such a file is refused as before, so a caller that cannot
// save the .sup files never loses them.
static int keep_image_subs=0;
void kodi_airplay_prepare_keep_image_subs(int on) { keep_image_subs=on!=0; }
// r25 (owner, build 178: "keep our audio only and original if different"): a comma list of language tags
// ("en,eng"). With it, an audio track is kept when it is the file's first audio track (the original) or its language
// tag is in the list; empty (the default) keeps every track. Preparation and verification use the same rule.
static char audio_languages[256]="";
void kodi_airplay_prepare_audio_languages(const char *list) {
    snprintf(audio_languages,sizeof audio_languages,",%s,",list && *list?list:"");
    for(char *c=audio_languages;*c;c++)if(*c>='A' && *c<='Z')*c=(char)(*c|32);
    if(!strcmp(audio_languages,",,"))audio_languages[0]=0;
}
// r27 (owner, build 180: "only keep english subtitles"; Interstellar's Blu-ray picture subtitles in many languages
// held its conversion up): the same kind of list for subtitles. A subtitle track is kept when its language tag is in
// the list or it has none; empty keeps them all.
static char subtitle_languages[256]="";
void kodi_airplay_prepare_subtitle_languages(const char *list) {
    snprintf(subtitle_languages,sizeof subtitle_languages,",%s,",list && *list?list:"");
    for(char *c=subtitle_languages;*c;c++)if(*c>='A' && *c<='Z')*c=(char)(*c|32);
    if(!strcmp(subtitle_languages,",,"))subtitle_languages[0]=0;
}
// r48 (DEC-039/DEC-040): the next conversion makes an upscaled copy in a box_w x box_h box (0 x 0: an ordinary
// preparation). The setter is the add-on's; prepare() hands it to kr_video for the length of one conversion.
static int up_box_w=0,up_box_h=0,up_engine=KR_UP_AUTO,up_kbps=0;
void kodi_airplay_prepare_upscale(int box_w,int box_h,int engine,int kbps) {
    up_box_w=box_w>0?box_w:0;up_box_h=box_h>0?box_h:0;up_engine=engine;up_kbps=kbps>0?kbps:0;
}
int kodi_airplay_upscale_support(int w,int h,int box_w,int box_h,int engine,char *json,int size) {
    int ow=0,oh=0;
    if(!json || size<64)return -1;
    if(!kr_video_upscale_size(w,h,(AVRational){1,1},box_w,box_h,&ow,&oh)) {
        int n=snprintf(json,(size_t)size,"{\"engine\":\"none\",\"engine_id\":-1,\"model\":\"none\",\"why\":\"already this size\"}");
        return n<size?n:-1;
    }
    return kr_upscale_support(w,h,ow,oh,engine,json,size);
}
int kodi_airplay_upscale_model(int w,int h,int box_w,int box_h,int engine,int start) {
    int ow=0,oh=0;
    if(!kr_video_upscale_size(w,h,(AVRational){1,1},box_w,box_h,&ow,&oh))return -1;
    return kr_upscale_model(w,h,ow,oh,engine,start,NULL);
}
int kodi_device_state(char *json,int size){return json && size>0?kr_device_state(json,size):-1;}
static int keep_subtitle(AVFormatContext *f,unsigned i) {
    if(!subtitle_languages[0])return 1;
    AVDictionaryEntry *l=av_dict_get(f->streams[i]->metadata,"language",NULL,0);
    if(!l || !l->value[0] || !strcmp(l->value,"und"))return 1;
    char tag[40];snprintf(tag,sizeof tag,",%s,",l->value);
    for(char *c=tag;*c;c++)if(*c>='A' && *c<='Z')*c=(char)(*c|32);
    return strstr(subtitle_languages,tag)!=NULL;
}
static int first_audio(AVFormatContext *f) {
    for(unsigned i=0;i<f->nb_streams;i++)if(f->streams[i]->codecpar->codec_type==AVMEDIA_TYPE_AUDIO)return (int)i;
    return -1;
}
static int keep_audio(AVFormatContext *f,unsigned i) {
    if(!audio_languages[0] || (int)i==first_audio(f))return 1;
    AVDictionaryEntry *l=av_dict_get(f->streams[i]->metadata,"language",NULL,0);
    if(!l || !l->value[0])return 0;
    char tag[40];snprintf(tag,sizeof tag,",%s,",l->value);
    for(char *c=tag;*c;c++)if(*c>='A' && *c<='Z')*c=(char)(*c|32);
    return strstr(audio_languages,tag)!=NULL;
}
static int video_index(AVFormatContext *f) {
    for (unsigned i=0;i<f->nb_streams;i++)
        if(f->streams[i]->codecpar->codec_type==AVMEDIA_TYPE_VIDEO &&
           !(f->streams[i]->disposition&AV_DISPOSITION_ATTACHED_PIC)) return (int)i;
    return -1;
}
static int hdr(const AVCodecParameters *p) {
    if(p->color_trc==AVCOL_TRC_SMPTE2084 || p->color_trc==AVCOL_TRC_ARIB_STD_B67) return 1;
    for(int i=0;i<p->nb_coded_side_data;i++) if(p->coded_side_data[i].type==AV_PKT_DATA_DOVI_CONF) return 1;
    return 0;
}
static int copy_video(const AVCodecParameters *p) {
    if(p->codec_id!=AV_CODEC_ID_H264 && p->codec_id!=AV_CODEC_ID_HEVC) return 0;
    const AVPixFmtDescriptor *d=av_pix_fmt_desc_get(p->format);
    int depth=p->codec_id==AV_CODEC_ID_HEVC?10:8;
    return p->bits_per_raw_sample<=depth && (!d || (d->comp[0].depth<=depth &&
           d->log2_chroma_w==1 && d->log2_chroma_h==1));
}
static int sidecar_sub(const AVCodecParameters *p) {
    return keep_image_subs && p->codec_type==AVMEDIA_TYPE_SUBTITLE && p->codec_id==AV_CODEC_ID_HDMV_PGS_SUBTITLE;
}
static int text_sub(enum AVCodecID id) {
    return id==AV_CODEC_ID_MOV_TEXT || id==AV_CODEC_ID_SUBRIP || id==AV_CODEC_ID_ASS ||
           id==AV_CODEC_ID_SSA || id==AV_CODEC_ID_WEBVTT || id==AV_CODEC_ID_TEXT;
}
int kr_prepare_ready(AVFormatContext *f) {
    if(!f || !f->iformat || !strstr(f->iformat->name,"mov")) return 0;
    int v=video_index(f);if(v<0 || !copy_video(f->streams[v]->codecpar)) return 0;
    for(unsigned i=0;i<f->nb_streams;i++) {
        AVCodecParameters *p=f->streams[i]->codecpar;
        if(p->codec_type==AVMEDIA_TYPE_AUDIO && p->codec_id!=AV_CODEC_ID_AAC) return 0;
        if(p->codec_type==AVMEDIA_TYPE_SUBTITLE && p->codec_id!=AV_CODEC_ID_MOV_TEXT) return 0;
    }
    return 1;
}
// r14 (owner, build 157: "my storage can't handle large scale downloads"): the source may be read straight from the
// phone's own loopback server (the setup add-on streams the Drive file through it) instead of a downloaded copy.
// Only a local path or http://127.0.0.1 is accepted: preparation never reaches out to the network by itself.
static int local_input(const char *input) {
    return input && (input[0]=='/' || !strncmp(input,"http://127.0.0.1:",17));
}
typedef struct {int64_t deadline;kr_prepare_progress progress;void *context;int cancelled;} inspect_wait;
static int inspect_interrupt(void *opaque) {
    inspect_wait *w=opaque;
    if(w->progress && !w->progress(0,0,0,w->context)){w->cancelled=1;return 1;}
    return av_gettime_relative()>=w->deadline;
}
// The options every reader of a Drive (loopback) file uses; r31: also the read-back check (validate), which opened
// without them: no reconnect, and FFmpeg then walked every fragment of a prepared movie (655 reads of a 100 MB test).
static void reading_options(AVDictionary **o,const char *input) {
    if(!strncmp(input,"http://",7)) {
        av_dict_set(o,"rw_timeout","30000000",0);
        av_dict_set(o,"reconnect","1",0);av_dict_set(o,"reconnect_on_network_error","1",0);
        av_dict_set(o,"reconnect_delay_max","5",0);av_dict_set(o,"reconnect_max_retries","3",0);
        av_dict_set(o,"reconnect_delay_total_max","15",0);av_dict_set(o,"reconnect_on_http_error","429,500,502,503,504",0);
        av_dict_set(o,"seekable","1",0);av_dict_set(o,"multiple_requests","1",0);
        av_dict_set(o,"user_agent","Kodi-iOS-AirPlay/1",0);
    }
    av_dict_set(o,"use_mfra_for","pts",0);
}
static int open_source_checked(AVFormatContext **f,const char *input,inspect_wait *wait) {
    AVDictionary *o=NULL;int r;
    *f=avformat_alloc_context();if(!*f)return AVERROR(ENOMEM);
    if(wait)(*f)->interrupt_callback=(AVIOInterruptCB){inspect_interrupt,wait};
    // r31 (owner, build-189 log: Interstellar's last check timed out three times): a prepared movie is fragmented, and
    // without its index (mfra) FFmpeg opens it by reading every fragment header in turn: ~1,700 Drive reads for a
    // 2 h 49 min movie. With the index it reads the start and the end.
    reading_options(&o,input);
    r=avformat_open_input(f,input,NULL,&o);av_dict_free(&o);
    if(r>=0)r=avformat_find_stream_info(*f,NULL);
    // AVIO copies the callback: its context must survive until avformat_close_input.
    if(wait && wait->cancelled)return AVERROR_EXIT;
    if(wait && av_gettime_relative()>=wait->deadline)return AVERROR(ETIMEDOUT);
    return r;
}
static int open_source(AVFormatContext **f,const char *input){return open_source_checked(f,input,NULL);}
// The setup add-on asks this before streaming a Drive file to preparation instead of downloading it first.
int kodi_airplay_prepare_streams(void) { return 1; }
int kodi_airplay_prepare_hdr(void) { return 1; }
// r48: the copy's "WxH engine=N" tag, only when it is plain text (it goes into JSON as it is).
static const char *upscaled_tag(AVFormatContext *f) {
    AVDictionaryEntry *e=av_dict_get(f->metadata,"kodi_airplay_upscaled",NULL,0);
    if(!e || !e->value || strlen(e->value)>48)return "";
    for(const char *c=e->value;*c;c++)if(!((*c>='0'&&*c<='9')||(*c>='a'&&*c<='z')||*c=='x'||*c==' '||*c=='='||*c=='-'))return "";
    return e->value;
}
static int probe(const char *input,char *json,int size,kr_prepare_progress cb,void *ctx) {
    AVFormatContext *f=NULL;int r=-1;
    if(!local_input(input) || !json || size<2) return -1;
    inspect_wait wait={av_gettime_relative()+120LL*AV_TIME_BASE,cb,ctx,0};
    int opened=open_source_checked(&f,input,&wait);
    if(opened<0){r=opened==AVERROR_EXIT?-2:opened==AVERROR(ETIMEDOUT)?-3:-1;goto end;}
    int v=video_index(f);if(v<0) goto end;
    AVCodecParameters *p=f->streams[v]->codecpar;
    double audio_work=0,duration=f->duration>0?(double)f->duration/AV_TIME_BASE:0;int pgs=0,other_image=0,extra_video=0,audio_tracks=0,subtitle_tracks=0;
    for(unsigned i=0;i<f->nb_streams;i++) {
        AVCodecParameters *a=f->streams[i]->codecpar;
        audio_tracks+=a->codec_type==AVMEDIA_TYPE_AUDIO;subtitle_tracks+=a->codec_type==AVMEDIA_TYPE_SUBTITLE;
        if(a->codec_type==AVMEDIA_TYPE_AUDIO && a->codec_id!=AV_CODEC_ID_AAC && keep_audio(f,i))
            audio_work+=duration*(a->ch_layout.nb_channels>=6?384000:160000)/8;
        if(a->codec_type==AVMEDIA_TYPE_SUBTITLE && !text_sub(a->codec_id) && keep_subtitle(f,i)){if(a->codec_id==AV_CODEC_ID_HDMV_PGS_SUBTITLE)pgs++;else other_image++;}
        if(a->codec_type==AVMEDIA_TYPE_VIDEO && (int)i!=v && !(f->streams[i]->disposition&AV_DISPOSITION_ATTACHED_PIC))extra_video++;
    }
    // r15: the codec and the tracks that decide whether and how a file can be prepared, for the owner's status page.
    snprintf(json,(size_t)size,"{\"ready\":%s,\"width\":%d,\"height\":%d,\"hdr\":%s,\"duration\":%.6f,\"copy_video\":%s,\"audio_work_bytes\":%.0f,"
             "\"codec\":\"%s\",\"bit_depth\":%d,\"pgs_subtitles\":%d,\"other_image_subtitles\":%d,\"extra_video\":%d,"
             "\"fps\":%.3f,\"audio_tracks\":%d,\"subtitle_tracks\":%d,\"upscaled\":\"%s\"}",
             kr_prepare_ready(f) && av_dict_get(f->metadata,"kodi_airplay_prepared",NULL,0)?"true":"false",p->width,p->height,hdr(p)?"true":"false",
             duration,copy_video(p)?"true":"false",audio_work,avcodec_get_name(p->codec_id),
             p->bits_per_raw_sample?p->bits_per_raw_sample:(av_pix_fmt_desc_get(p->format)?av_pix_fmt_desc_get(p->format)->comp[0].depth:0),
             pgs,other_image,extra_video,
             // r48: frame rate (measurement), track counts (an upscaled copy keeps them all) and the copy's tag.
             f->streams[v]->avg_frame_rate.den?av_q2d(f->streams[v]->avg_frame_rate):0,audio_tracks,subtitle_tracks,
             upscaled_tag(f));r=0;
end:avformat_close_input(&f);return r;
}
int kodi_airplay_probe(const char *input,char *json,int size){return probe(input,json,size,NULL,NULL);}
int kodi_airplay_probe_ex(const char *input,char *json,int size,kr_prepare_progress cb,void *ctx){return probe(input,json,size,cb,ctx);}
static int tick(kr_prepare_progress cb,void *ctx,int stage,double done,double total) {
    return !cb || cb(stage,done,total,ctx);
}
static int fail(char *err,int n,const char *what,int code) {
    char detail[100]="";if(code<0)av_strerror(code,detail,sizeof detail);
    if(err && n>0)snprintf(err,(size_t)n,"%s%s%s",what,*detail?": ":"",detail);
    return -1;
}
// A whole track is bounded-memory fMP4; only the current PREP_UNIT-second unit is held in RAM.
// Spools checkpoint after every completed segment, so restart/pause does not redo a movie.
static int spool(const char *input,const char *path,int index,int is_video,
                 kr_prepare_progress cb,void *ctx,char *err,int en) {
    kr_source *source=NULL;gm_stream *plan=NULL;kr_video *video=NULL;kr_audio *audio=NULL;
    FILE *file=NULL;gm_buf unit={0};int r=-1,first=0;long long offset=0;
    char state[4096],tmp[4100];snprintf(state,sizeof state,"%s.state",path);snprintf(tmp,sizeof tmp,"%s.tmp",state);
    source=kr_source_open(input,30,err,en);if(!source)goto end;
    // r20 (owner, build 170: Inception converted at about a quarter of real time): 6-second units were made for live
    // AirPlay; for a whole file each one re-seeks to its keyframe, re-decodes from there and starts a new encoder.
    // Preparation uses PREP_UNIT-second units (one ~100 MB unit in RAM at 4K); checkpoints carry the length.
    plan=gm_stream_open(kr_source_gm(source),PREP_UNIT,err,en);if(!plan)goto end;
    if(is_video) {
        video=kr_video_open(kr_source_gm(source),index,err,en);if(!video)goto end;
        kr_video_keep_resolution(video);
    } else {audio=kr_audio_open(kr_source_gm(source),index,err,en);if(!audio)goto end;}
    int unit_s=0;
    FILE *saved=fopen(state,"r");if(saved){if(fscanf(saved,"%d %lld %d",&first,&offset,&unit_s)<2){first=0;offset=0;}fclose(saved);}
    if(unit_s!=PREP_UNIT){first=0;offset=0;}   // a checkpoint from other-sized units (r19 and earlier) starts over
    struct stat st;
    if(first<0 || offset<0 || stat(path,&st) || st.st_size<offset){first=0;offset=0;}
    file=fopen(path,first?"r+b":"w+b");if(!file){fail(err,en,"Cannot create working file",0);goto end;}
    if(ftruncate(fileno(file),(off_t)offset) || fseeko(file,(off_t)offset,SEEK_SET)){fail(err,en,"Cannot resume working file",0);goto end;}
    int count=gm_stream_segment_count(plan);
    if(first>count){fail(err,en,"Invalid conversion checkpoint",0);goto end;}
    for(int i=first;i<count;i++) {
        if(!tick(cb,ctx,is_video?0:1,i,count)){r=-2;goto end;}
        unit.len=0;
        struct timespec t0,t1;clock_gettime(CLOCK_MONOTONIC,&t0);
        int q=is_video?kr_video_unit(video,plan,i,&unit,err,en):kr_audio_unit(audio,plan,i,&unit,err,en);
        if(q<0)goto end;
        clock_gettime(CLOCK_MONOTONIC,&t1);
        double took=(double)(t1.tv_sec-t0.tv_sec)+(double)(t1.tv_nsec-t0.tv_nsec)/1e9;
        if(is_video || i%10==0)
            kr_remux_note("prepare: %s %d/%d made in %.1f s for %d s of film (%.2fx real time)%s%s",is_video?"video":"audio",i+1,count,
                          took,PREP_UNIT,took>0?PREP_UNIT/took:0,is_video?" via ":"",is_video?kr_video_route(video):"");
        int start=i?kr_first_moof(unit.data,unit.len):0;
        if(start<0 || fwrite(unit.data+start,1,(size_t)(unit.len-start),file)!=(size_t)(unit.len-start) ||
           fflush(file) || fsync(fileno(file))){fail(err,en,"Cannot save converted segment",0);goto end;}
        offset=(long long)ftello(file);
        saved=fopen(tmp,"w");if(!saved){fail(err,en,"Cannot save conversion checkpoint",0);goto end;}
        int ok=fprintf(saved,"%d %lld %d\n",i+1,offset,PREP_UNIT)>0 && !fflush(saved) && !fsync(fileno(saved));
        if(fclose(saved) || !ok || rename(tmp,state)){fail(err,en,"Cannot commit conversion checkpoint",0);goto end;}
    }
    r=0;
end:if(file)fclose(file);free(unit.data);kr_video_close(video);kr_audio_close(audio);
    gm_stream_close(plan);kr_source_close(source);return r;
}
// Sequential conversion source: only the current PREP_UNIT-second unit lives in RAM. Unlike the
// legacy spool this reader never opens a working file. Each track owns its demuxer.
// r23 (owner, build 175 log: per 30 s of Inception the video took 37 s and each of two audio tracks 23 s more, one
// after another): each track's next unit is made on its own thread while the muxer takes the current one, so the
// picture and the audio tracks are converted at the same time (and read the same Drive blocks together). One unit is
// made ahead per track, so memory stays at two units per track.
// r24 (owner: "we need a way to really boost speed for av1"): a re-encoded picture is made in VIDEO_LANES lanes, each
// with its own source, decoder and encoder: lane l makes units l, l+n, l+2n... and the muxer takes them in order. Each
// unit already had a fresh encoder (closed GOP), so a unit is the same whichever lane makes it. Audio keeps one lane.
#define VIDEO_LANES 2
#define MAX_LANES 4
// r26 (build-178 log: Kodi left the screen while a VideoToolbox unit was being made; that unit never finished and the
// muxer, which takes units in order, waited for it for 20 minutes, even after Kodi came back): a unit whose decoder
// shows no new picture for STALL_S seconds is made again by a fresh lane (CPU decoder for that unit), and the stuck
// lane is abandoned. Lanes live on the heap and share a small hub (lock, condition, stop) that outlives the reader
// while an abandoned lane may still wake up: such a lane then frees itself and, if it is the last, the hub.
#define STALL_S 90
typedef struct {pthread_mutex_t lock;pthread_cond_t cond;int stop,abandoned,orphan;} generated_hub;
typedef struct {
    generated_hub *hub;
    kr_source *source;gm_stream *plan;kr_video *video;kr_audio *audio;
    pthread_t thread;int started,has_next,next_result,next_segment,dead;gm_buf next;char work_error[512];
    int first,stride,count,is_video,index;
} generated_lane;
typedef struct {
    generated_lane *lanes[MAX_LANES];int nlanes;generated_hub *hub;
    gm_buf unit;int segment,offset,count,is_video,index,served,start,resuming;kr_prepare_progress progress;void *context;
    char *error;int error_size;char *input;   // the reader array lives on the converter's stack: keep it small
    long seen_frames[MAX_LANES];double seen_at[MAX_LANES];
} generated_reader;
static double now_s(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (double)t.tv_sec+(double)t.tv_nsec/1e9;}
static int stall_seconds(void){const char *e=getenv("KR_PREP_STALL_S");int n=e?atoi(e):0;return n>0?n:STALL_S;}
static void lane_free(generated_lane *l) {
    if(!l)return;
    free(l->next.data);kr_video_close(l->video);kr_audio_close(l->audio);gm_stream_close(l->plan);kr_source_close(l->source);free(l);
}
static void hub_release(generated_hub *h) {   // an abandoned lane is done: the last one out frees an orphaned hub
    pthread_mutex_lock(&h->lock);h->abandoned--;int last=h->orphan && h->abandoned<=0;pthread_mutex_unlock(&h->lock);
    if(last){pthread_mutex_destroy(&h->lock);pthread_cond_destroy(&h->cond);free(h);}
}
static void generated_note(generated_lane *l,int segment,double took) {
    if(l->is_video || segment%10==0)
        kr_remux_note("prepare: %s %d/%d made in %.1f s for %d s of film (%.2fx real time)%s%s%s",l->is_video?"video":"audio",
                      segment+1,l->count,took,PREP_UNIT,took>0?PREP_UNIT/took:0,l->is_video?" via ":"",
                      l->is_video?kr_video_route(l->video):"",l->is_video && l->stride>1?(segment%l->stride?", lane 2":", lane 1"):"");
}
static void *generated_work(void *opaque) {
    generated_lane *l=opaque;generated_hub *h=l->hub;
    for(int segment=l->first;;segment+=l->stride) {
        pthread_mutex_lock(&h->lock);
        while(!h->stop && !l->dead && l->has_next)pthread_cond_wait(&h->cond,&h->lock);   // the muxer has not taken our last one yet
        int dead=l->dead;
        if(h->stop || dead || segment>=l->count){pthread_mutex_unlock(&h->lock);if(dead){lane_free(l);hub_release(h);}return NULL;}
        pthread_mutex_unlock(&h->lock);
        gm_buf unit={0};char error[512]="";
        // Host tests: KR_PREP_STALL_UNIT=n makes the first attempt at unit n hang for 20 s (a stuck VideoToolbox unit).
        static atomic_int stalled;const char *st=getenv("KR_PREP_STALL_UNIT");
        if(st && l->is_video && atoi(st)==segment && !atomic_exchange(&stalled,1))sleep(20);
        struct timespec t0,t1;clock_gettime(CLOCK_MONOTONIC,&t0);
        int r=l->is_video?kr_video_unit(l->video,l->plan,segment,&unit,error,sizeof error):
                          kr_audio_unit(l->audio,l->plan,segment,&unit,error,sizeof error);
        clock_gettime(CLOCK_MONOTONIC,&t1);
        pthread_mutex_lock(&h->lock);
        if(l->dead || h->stop) {   // abandoned while it was stuck, or the conversion is over: this unit is not wanted
            dead=l->dead;pthread_mutex_unlock(&h->lock);free(unit.data);
            if(dead){lane_free(l);hub_release(h);}
            return NULL;
        }
        if(r>=0)generated_note(l,segment,(double)(t1.tv_sec-t0.tv_sec)+(double)(t1.tv_nsec-t0.tv_nsec)/1e9);
        free(l->next.data);l->next=unit;l->next_result=r;l->next_segment=segment;l->has_next=1;
        if(r<0)snprintf(l->work_error,sizeof l->work_error,"%s",error);
        pthread_cond_broadcast(&h->cond);
        pthread_mutex_unlock(&h->lock);
        if(r<0)return NULL;
    }
}
static generated_lane *lane_open(generated_reader *g,int first,char *err,int en) {
    generated_lane *l=calloc(1,sizeof *l);if(!l){fail(err,en,"out of memory",0);return NULL;}
    l->hub=g->hub;l->first=first;l->stride=g->nlanes;l->count=g->count;l->is_video=g->is_video;l->index=g->index;
    l->source=kr_source_open(g->input,30,err,en);if(!l->source)goto bad;
    l->plan=gm_stream_open(kr_source_gm(l->source),PREP_UNIT,err,en);if(!l->plan)goto bad;   // r21: was 6 s
    if(g->is_video){l->video=kr_video_open(kr_source_gm(l->source),g->index,err,en);if(!l->video)goto bad;kr_video_keep_resolution(l->video);}
    else {l->audio=kr_audio_open(kr_source_gm(l->source),g->index,err,en);if(!l->audio)goto bad;}
    return l;
bad:lane_free(l);return NULL;
}
static int lane_start(generated_lane *l) {
    if(pthread_create(&l->thread,NULL,generated_work,l))return -1;
    l->started=1;return 0;
}
static int generated_read(void *opaque,uint8_t *data,int size) {
    generated_reader *g=opaque;generated_hub *h=g->hub;
    if(g->offset>=g->unit.len) {
        if(g->segment>=g->count)return AVERROR_EOF;
        // r32: while a resumed run lines up, the unit it waits for is part of "finding where it left off" (stage 4).
        if(!tick(g->progress,g->context,g->resuming?4:g->is_video?0:1,g->segment,g->count))return AVERROR_EXIT;
        for(int i=0;i<g->nlanes;i++) if(!g->lanes[i]->started && lane_start(g->lanes[i])) {
            if(g->error && g->error_size>0)snprintf(g->error,(size_t)g->error_size,"Conversion thread");return AVERROR(EIO);
        }
        int li=(g->segment-g->start)%g->nlanes;generated_lane *l=g->lanes[li];
        g->seen_at[li]=now_s();g->seen_frames[li]=g->is_video?kr_video_frames(l->video):0;
        pthread_mutex_lock(&h->lock);
        while(!l->has_next) {
            struct timespec until;clock_gettime(CLOCK_REALTIME,&until);until.tv_sec+=2;
            pthread_cond_timedwait(&h->cond,&h->lock,&until);
            if(l->has_next || !g->is_video)continue;
            long frames=kr_video_frames(l->video);double t=now_s();
            if(frames!=g->seen_frames[li]){g->seen_frames[li]=frames;g->seen_at[li]=t;continue;}
            if(t-g->seen_at[li]<stall_seconds())continue;
            // Stuck: abandon this lane and make the unit again from a fresh one (CPU decoder for this unit).
            pthread_mutex_unlock(&h->lock);
            char e2[256]="";generated_lane *fresh=lane_open(g,g->segment,e2,sizeof e2);
            if(fresh)kr_video_software_next(fresh->video);
            pthread_mutex_lock(&h->lock);
            if(!fresh){g->seen_at[li]=now_s();continue;}   // could not open one now: keep waiting, try again later
            l->dead=1;h->abandoned++;pthread_cond_broadcast(&h->cond);
            if(l->started)pthread_detach(l->thread);   // never joined: it frees itself if it ever wakes
            g->lanes[li]=fresh;l=fresh;
            pthread_mutex_unlock(&h->lock);
            kr_remux_note("prepare: video %d/%d made no progress for %d s; making it again",g->segment+1,g->count,stall_seconds());
            int started=lane_start(fresh);
            pthread_mutex_lock(&h->lock);
            if(started){pthread_mutex_unlock(&h->lock);if(g->error && g->error_size>0)snprintf(g->error,(size_t)g->error_size,"Conversion thread");return AVERROR(EIO);}
            g->seen_at[li]=now_s();g->seen_frames[li]=kr_video_frames(fresh->video);
        }
        int r=l->next_result;
        if(r>=0 && l->next_segment!=g->segment)r=-1;   // never out of order
        free(g->unit.data);g->unit=l->next;memset(&l->next,0,sizeof l->next);l->has_next=0;
        if(r<0 && g->error && g->error_size>0)snprintf(g->error,(size_t)g->error_size,"%s",l->work_error[0]?l->work_error:"Conversion unit order");
        pthread_cond_broadcast(&h->cond);   // that lane makes its next unit meanwhile
        pthread_mutex_unlock(&h->lock);
        if(r<0)return AVERROR(EIO);
        g->offset=g->served++?kr_first_moof(g->unit.data,g->unit.len):0;   // r30: the first unit served keeps its init
        if(g->offset<0 || g->offset>=g->unit.len)return AVERROR_INVALIDDATA;
        g->segment++;
    }
    int n=FFMIN(size,g->unit.len-g->offset);memcpy(data,g->unit.data+g->offset,(size_t)n);g->offset+=n;return n;
}
static void generated_close(generated_reader *g) {
    generated_hub *h=g->hub;
    if(h) {   // each live lane finishes the unit it is making (none touches the reader after stop)
        pthread_mutex_lock(&h->lock);h->stop=1;pthread_cond_broadcast(&h->cond);pthread_mutex_unlock(&h->lock);
    }
    for(int i=0;i<MAX_LANES;i++) {
        generated_lane *l=g->lanes[i];if(!l)continue;
        if(l->started)pthread_join(l->thread,NULL);
        lane_free(l);g->lanes[i]=NULL;
    }
    if(h) {   // abandoned lanes may still be stuck: then the last of them frees the hub when it wakes
        pthread_mutex_lock(&h->lock);int keep=h->abandoned>0;h->orphan=1;pthread_mutex_unlock(&h->lock);
        if(!keep){pthread_mutex_destroy(&h->lock);pthread_cond_destroy(&h->cond);free(h);}
    }
    free(g->unit.data);free(g->input);memset(g,0,sizeof *g);
}
// r30: resume_t >= 0 starts at the unit holding that time (a picture: the unit that starts there); -1 at the start.
static int resume_unit(gm_stream *plan,double t,int video) {
    if(t<0)return 0;
    int count=gm_stream_segment_count(plan);
    for(int u=0;u<count;u++){double start=gm_stream_segment_start(plan,u);if(video && fabs(start-t)<0.02)return u;}
    if(video)return -1;
    int u=gm_stream_time_to_segment(plan,t);if(u<0)return -1;
    if(u>0 && t-gm_stream_segment_start(plan,u)<1.0)u--;   // near a boundary the packet may still be in the unit before
    return u;
}
static int generated_open(generated_reader *g,AVFormatContext **format,AVIOContext **io,
                          const char *input,int index,int video,kr_prepare_progress cb,void *ctx,char *err,int en,double resume_t) {
    g->is_video=video;g->index=index;g->progress=cb;g->context=ctx;g->error=err;g->error_size=en;
    g->input=strdup(input);if(!g->input)return -1;
    g->hub=calloc(1,sizeof *g->hub);if(!g->hub)return -1;
    pthread_mutex_init(&g->hub->lock,NULL);pthread_cond_init(&g->hub->cond,NULL);
    g->nlanes=1;g->count=0;
    // Lane 0 first: its plan gives the unit count and its decoder says whether lanes pay (hardware decoding).
    generated_lane *first=calloc(1,sizeof *first);if(!first)return -1;
    first->hub=g->hub;g->lanes[0]=first;
    first->source=kr_source_open(input,30,err,en);if(!first->source)return -1;
    first->plan=gm_stream_open(kr_source_gm(first->source),PREP_UNIT,err,en);if(!first->plan)return -1;   // r21: was 6 s
    g->count=gm_stream_segment_count(first->plan);
    int start=resume_unit(first->plan,resume_t,video);
    if(start<0 || (start>=g->count && g->count>0))return fail(err,en,"Resume position not found",0);
    g->segment=start;g->start=start;g->resuming=resume_t>=0;
    if(video) {
        first->video=kr_video_open(kr_source_gm(first->source),index,err,en);if(!first->video)return -1;kr_video_keep_resolution(first->video);
        // A picture copied by hardware HDR / GPU work in lanes; one lane for anything else (CPU work is already
        // spread over the cores inside one lane).
        // r48: an upscaled copy keeps one lane: each lane holds its own AI engine and 4K buffers.
        if(kr_video_hw_decode(first->video) && !kr_video_upscaling(first->video))g->nlanes=VIDEO_LANES;
        // Host tests have no VideoToolbox: KR_PREP_LANES forces the lanes so the in-order hand-over is tested.
        const char *forced=getenv("KR_PREP_LANES");
        if(forced && atoi(forced)>=1 && atoi(forced)<=MAX_LANES)g->nlanes=atoi(forced);
    } else {first->audio=kr_audio_open(kr_source_gm(first->source),index,err,en);if(!first->audio)return -1;}
    first->first=start;first->stride=g->nlanes;first->count=g->count;first->is_video=video;first->index=index;
    for(int i=1;i<g->nlanes;i++){g->lanes[i]=lane_open(g,start+i,err,en);if(!g->lanes[i])return -1;}
    uint8_t *buffer=av_malloc(32768);if(!buffer)return -1;
    *io=avio_alloc_context(buffer,32768,0,g,generated_read,NULL,NULL);
    if(!*io){av_free(buffer);return -1;}
    *format=avformat_alloc_context();if(!*format)return -1;
    (*format)->pb=*io;(*format)->flags|=AVFMT_FLAG_CUSTOM_IO;
    return avformat_open_input(format,NULL,av_find_input_format("mov"),NULL);
}
// r26: the add-on says when Kodi is off screen (VideoToolbox may stop there): units then decode on the CPU.
void kodi_airplay_prepare_background(int on) { kr_video_set_background(on); }
typedef struct {AVFormatContext *f;AVPacket *packet;int map[TRACKS];int eof;int own;} input_track;
struct resume_ctx;
typedef struct {
    kr_prepare_write write;void *context;int track;char suffix[80];
    uint8_t *init;int init_size,initialized;double duration;
    struct resume_ctx *rc;   // r30, the movie (track 0) of a streamed conversion: parsed on its way out
} output_sink;
// A finite standalone fragmented movie must advertise its full duration in the init,
// before any packets have been muxed. FFmpeg's empty_moov otherwise writes zero.
// Update fixed-size fields only: every moof/mfra byte offset remains unchanged.
static int init_duration(uint8_t *p,int size,double seconds,uint32_t *movie_scale) {
    for(int at=0;at+8<=size;) {
        uint64_t n=AV_RB32(p+at);int header=8;
        if(n==1){if(at+16>size)return -1;n=AV_RB64(p+at+8);header=16;}
        if(n<(uint64_t)header || n>(uint64_t)(size-at))return -1;
        uint8_t *box=p+at;uint32_t type=AV_RB32(box+4);
        if(type==MKBETAG('m','o','o','v') || type==MKBETAG('t','r','a','k') || type==MKBETAG('m','d','i','a')) {
            if(init_duration(box+header,(int)n-header,seconds,movie_scale)<0)return -1;
        } else if(type==MKBETAG('m','v','h','d') || type==MKBETAG('m','d','h','d') || type==MKBETAG('t','k','h','d')) {
            if(n<(uint64_t)(header+4))return -1;
            int version=box[header];if(version>1)return -1;
            int track=type==MKBETAG('t','k','h','d');
            int offset=header+(track?(version?28:20):(version?24:16));
            int bytes=version?8:4;
            if(offset+bytes>(int)n)return -1;
            uint32_t scale=track?*movie_scale:AV_RB32(box+offset-4);
            if(type==MKBETAG('m','v','h','d'))*movie_scale=scale;
            if(!scale)return -1;
            uint64_t duration=(uint64_t)llround(seconds*scale);
            if(!version && duration>UINT32_MAX)return -1;
            if(version)AV_WB64(box+offset,duration);else AV_WB32(box+offset,(uint32_t)duration);
        }
        at+=(int)n;
    }
    return 0;
}
// r30 (owner, build 185: "lets fix restarting when its closed and have it keep progress"): a streamed conversion can
// carry on after Kodi is closed instead of starting the movie again at 0%.
// - The movie's boxes are parsed on their way out. Packets go to the muxer one at a time (av_write_frame) and the
//   output is flushed after each, so every fragment holds exactly the packets written between two fragment starts.
// - A *mark* is a fragment that starts with a video keyframe (for a re-encoded picture: where a unit, and so a fresh
//   encoder, starts). With kodi_airplay_prepare_marks(1) the caller gets each mark as text through write(-1, "mark"):
//   its byte offset, its fragment number, where every input stood (the next packet of each), every track's decode time
//   there, the picture subtitle files' lengths and the fragment index entries before it. Everything before the mark is
//   complete fragments; the caller keeps Drive's upload at or before a mark and saves the latest one.
// - kodi_airplay_prepare_resume(input, mark text, ...) writes the same movie from that mark on: the inputs start at
//   their recorded packets, the new init is dropped, fragment numbers continue and each fragment's decode time (tfdt,
//   which FFmpeg counts from the first packet it was given) is moved onto the first run's timeline.
// - FFmpeg's fragment index (mfra) only knows its own run, so it is turned off and built here from every fragment,
//   the way FFmpeg builds it, in both runs.
#define MARK_TRACK (-1)
static int marks_on=0;
void kodi_airplay_prepare_marks(int on) { marks_on=on!=0; }
typedef struct {int64_t pos,dts;double t;int si,eof;} in_mark;
typedef struct {int markable;in_mark in[TRACKS];int64_t side[TRACKS];} prep_state;
typedef struct {int64_t end,start,shift;int has_start,from_mark,carried;} out_track;   // by MP4 track_ID - 1 (= output stream index)
typedef struct {uint32_t id;int64_t time,offset;} tfra_entry;
typedef struct resume_ctx {
    int resume;int64_t resume_at;uint32_t resume_seq;int64_t at;
    uint8_t head[16];int head_len;uint64_t left;int in_moof;int64_t box_start;
    uint8_t *moof;int moof_size,moof_len;
    out_track tracks[TRACKS];int nstreams,ninputs,shift_known,moofs,marks;
    int64_t base[TRACKS];
    tfra_entry *tfra;int ntfra,cap,emitted;
    prep_state frag_start,pending,resumed;
    char layout[600];
    AVFormatContext **side;
} resume_ctx;
static int rc_forward(output_sink *s,const uint8_t *d,int n) {
    if(n<=0)return 1;
    if(!s->write(0,s->suffix,d,n,s->context))return 0;
    s->rc->at+=n;return 1;
}
static int tfra_add(resume_ctx *rc,uint32_t id,int64_t time,int64_t offset) {
    if(rc->ntfra==rc->cap){int c=rc->cap?rc->cap*2:1024;tfra_entry *g=realloc(rc->tfra,sizeof *g*(size_t)c);if(!g)return -1;rc->tfra=g;rc->cap=c;}
    rc->tfra[rc->ntfra++]=(tfra_entry){id,time,offset};return 0;
}
// One moof: each traf's tfdt moves onto the first run's timeline (base, 0 without a resume), its end and its index
// entry (FFmpeg: time = first dts + first cts, at least 0; offset = the moof) are noted.
static int moof_parse(resume_ctx *rc,uint8_t *m,int size,int64_t offset) {
    for(int at=8;at+8<=size;) {
        uint32_t n=AV_RB32(m+at),type=AV_RB32(m+at+4);if(n<8 || n>(uint32_t)(size-at))return -1;
        uint8_t *b=m+at;
        if(type==MKBETAG('t','r','a','f')) {
            uint32_t id=0,defdur=0;int have=0,v1=0,samples=0;uint8_t *tfdt=NULL;int64_t dur=0,cts=0;
            for(uint32_t t=8;t+8<=n;) {
                uint32_t cn=AV_RB32(b+t),ct=AV_RB32(b+t+4);if(cn<8 || cn>n-t)return -1;uint8_t *c=b+t;
                if(ct==MKBETAG('t','f','h','d') && cn>=16) {
                    uint32_t fl=AV_RB24(c+9),q=16;id=AV_RB32(c+12);have=1;
                    if(fl&1)q+=8;if(fl&2)q+=4;
                    if(fl&8){if(q+4>cn)return -1;defdur=AV_RB32(c+q);}
                } else if(ct==MKBETAG('t','f','d','t') && cn>=16) {
                    v1=c[8]==1;if(v1 && cn<20)return -1;tfdt=c+12;
                } else if(ct==MKBETAG('t','r','u','n') && cn>=16) {
                    int version=c[8];uint32_t fl=AV_RB24(c+9),count=AV_RB32(c+12),q=16;
                    if(fl&1)q+=4;if(fl&4)q+=4;
                    uint32_t per=((fl&0x100)?4:0)+((fl&0x200)?4:0)+((fl&0x400)?4:0)+((fl&0x800)?4:0);
                    if((uint64_t)q+(uint64_t)per*count>cn)return -1;
                    for(uint32_t i=0;i<count;i++) {
                        uint8_t *e=c+q+per*i;uint32_t k=0;
                        dur+=(fl&0x100)?AV_RB32(e):defdur;if(fl&0x100)k+=4;if(fl&0x200)k+=4;if(fl&0x400)k+=4;
                        if(!samples && (fl&0x800))cts=version?(int64_t)(int32_t)AV_RB32(e+k):(int64_t)AV_RB32(e+k);
                        samples++;
                    }
                }
                t+=cn;
            }
            if(!have || !tfdt || id<1 || id>TRACKS)return -1;
            int64_t value=(v1?(int64_t)AV_RB64(tfdt):(int64_t)AV_RB32(tfdt))+rc->base[id-1];
            if(v1)AV_WB64(tfdt,(uint64_t)value);
            else {if(value<0 || value>UINT32_MAX)return -1;AV_WB32(tfdt,(uint32_t)value);}
            out_track *tr=&rc->tracks[id-1];
            if(samples) {
                int64_t time=value+(tr->has_start?tr->start:0)+cts;
                if(tfra_add(rc,id,time<0?0:time,offset)<0)return -1;
            }
            tr->end=value+dur;
        }
        at+=(int)n;
    }
    return 0;
}
static uint32_t moof_seq(const uint8_t *m,int size) {
    for(int at=8;at+16<=size;){uint32_t n=AV_RB32(m+at);if(n<8 || n>(uint32_t)(size-at))return 0;
        if(AV_RB32(m+at+4)==MKBETAG('m','f','h','d'))return AV_RB32(m+at+12);at+=(int)n;}
    return 0;
}
static int rc_mark(output_sink *s,int64_t offset,uint32_t seq) {
    resume_ctx *rc=s->rc;prep_state *st=&rc->frag_start;
    // The subtitle files' bytes up to here reach the caller first, so the lengths in the mark are all with it.
    for(int i=0;i<TRACKS;i++)if(rc->side && rc->side[i] && rc->side[i]->pb){avio_flush(rc->side[i]->pb);if(rc->side[i]->pb->error<0)return 0;}
    AVBPrint b;av_bprint_init(&b,0,AV_BPRINT_SIZE_UNLIMITED);
    av_bprintf(&b,"kr-resume 1\noffset %lld\nseq %u\nlayout %s\n",(long long)offset,seq,rc->layout);
    for(int i=0;i<rc->ninputs;i++){in_mark *m=&st->in[i];
        av_bprintf(&b,"in %d %d %lld %d %lld %.6f\n",i,m->eof,(long long)m->pos,m->si,(long long)m->dts,m->t);}
    for(int k=0;k<rc->nstreams;k++){out_track *t=&rc->tracks[k];
        av_bprintf(&b,"track %d %lld %d %lld %lld\n",k+1,(long long)t->end,t->has_start,(long long)t->start,(long long)t->shift);}
    for(int i=0;i<TRACKS;i++)if(rc->side && rc->side[i])av_bprintf(&b,"side %d %lld\n",i,(long long)st->side[i]);
    for(;rc->emitted<rc->ntfra && rc->tfra[rc->emitted].offset<offset;rc->emitted++){tfra_entry *e=&rc->tfra[rc->emitted];
        av_bprintf(&b,"tfra %u %lld %lld\n",e->id,(long long)e->time,(long long)e->offset);}
    int ok=av_bprint_is_complete(&b) && s->write(MARK_TRACK,"mark",(const uint8_t*)b.str,(int)b.len,s->context);
    av_bprint_finalize(&b,NULL);rc->marks++;
    return ok;
}
static int moof_done(output_sink *s) {
    resume_ctx *rc=s->rc;int64_t offset=rc->box_start;
    // A fragment that starts on a picture keyframe, after the first of this run, is a place to carry on from.
    if(marks_on && rc->frag_start.markable && rc->moofs>0 && !rc_mark(s,offset,moof_seq(rc->moof,rc->moof_size)))return -1;
    if(moof_parse(rc,rc->moof,rc->moof_size,offset)<0)return -1;
    if(!rc_forward(s,rc->moof,rc->moof_size))return -1;
    rc->moofs++;rc->frag_start=rc->pending;   // the packet being written now starts the next fragment
    return 0;
}
static int out_feed(output_sink *s,const uint8_t *d,int n) {
    resume_ctx *rc=s->rc;
    while(n>0) {
        if(rc->in_moof) {
            int take=FFMIN(n,rc->moof_size-rc->moof_len);memcpy(rc->moof+rc->moof_len,d,(size_t)take);rc->moof_len+=take;d+=take;n-=take;
            if(rc->moof_len==rc->moof_size){int q=moof_done(s);av_freep(&rc->moof);rc->in_moof=0;if(q<0)return 0;}
            continue;
        }
        if(rc->left>0) {
            int take=(int)FFMIN((uint64_t)n,rc->left);if(!rc_forward(s,d,take))return 0;
            if(rc->left!=UINT64_MAX)rc->left-=(uint64_t)take;d+=take;n-=take;continue;
        }
        rc->head[rc->head_len++]=*d++;n--;
        if(rc->head_len<8)continue;
        uint64_t size=AV_RB32(rc->head);
        if(size==1){if(rc->head_len<16)continue;size=AV_RB64(rc->head+8);}
        int hl=rc->head_len;uint32_t type=AV_RB32(rc->head+4);rc->box_start=rc->at;rc->head_len=0;
        if(size && size<(uint64_t)hl)return 0;
        if(type==MKBETAG('m','o','o','f')) {
            if(!size || size>(uint64_t)SINK_BUFFER)return 0;   // a fragment header larger than the buffer could not be finished
            rc->moof=av_malloc((size_t)size);if(!rc->moof)return 0;
            memcpy(rc->moof,rc->head,(size_t)hl);rc->moof_len=hl;rc->moof_size=(int)size;rc->in_moof=1;
        } else {
            if(!rc_forward(s,rc->head,hl))return 0;
            rc->left=size?size-(uint64_t)hl:UINT64_MAX;
        }
    }
    return 1;
}
// FFmpeg's mfra, from every fragment of both runs: one tfra per track (track order), then mfro with the mfra size.
static int write_mfra(output_sink *s) {
    resume_ctx *rc=s->rc;AVBPrint b;av_bprint_init(&b,0,AV_BPRINT_SIZE_UNLIMITED);
    uint8_t w[19];
    av_bprint_append_data(&b,"\0\0\0\0mfra",8);
    for(int k=1;k<=rc->nstreams;k++) {
        int count=0;for(int i=0;i<rc->ntfra;i++)count+=rc->tfra[i].id==(uint32_t)k;
        if(!count)continue;
        uint8_t h[24];AV_WB32(h,(uint32_t)(24+19*count));memcpy(h+4,"tfra",4);AV_WB32(h+8,0x01000000);AV_WB32(h+12,(uint32_t)k);AV_WB32(h+16,0);AV_WB32(h+20,(uint32_t)count);
        av_bprint_append_data(&b,(const char*)h,24);
        for(int i=0;i<rc->ntfra;i++)if(rc->tfra[i].id==(uint32_t)k){
            AV_WB64(w,(uint64_t)rc->tfra[i].time);AV_WB64(w+8,(uint64_t)rc->tfra[i].offset);w[16]=w[17]=w[18]=1;
            av_bprint_append_data(&b,(const char*)w,19);}
    }
    uint8_t f[16];AV_WB32(f,16);memcpy(f+4,"mfro",4);AV_WB32(f+8,0);AV_WB32(f+12,(uint32_t)(b.len+16));
    av_bprint_append_data(&b,(const char*)f,16);
    int ok=av_bprint_is_complete(&b);
    if(ok){AV_WB32((uint8_t*)b.str,(uint32_t)b.len);ok=rc_forward(s,(const uint8_t*)b.str,(int)b.len);}
    av_bprint_finalize(&b,NULL);return ok?0:-1;
}
// Parse a mark (the text rc_mark wrote, with the tfra lines of every earlier mark) into a fresh context.
static int rc_load(resume_ctx *rc,const char *text,int *ninputs) {
    const char *at=text;int version=0;*ninputs=0;
    if(sscanf(at,"kr-resume %d",&version)!=1 || version!=1)return -1;
    while((at=strchr(at,'\n'))) {
        at++;long long a,b2,c;int i,e,si,h;double t;unsigned id;
        if(sscanf(at,"offset %lld",&a)==1)rc->resume_at=a;
        else if(sscanf(at,"seq %u",&id)==1)rc->resume_seq=id;
        else if(!strncmp(at,"layout ",7)){const char *end=strchr(at,'\n');size_t n=end?(size_t)(end-at-7):strlen(at+7);if(n>=sizeof rc->layout)return -1;memcpy(rc->layout,at+7,n);rc->layout[n]=0;}
        else if(sscanf(at,"in %d %d %lld %d %lld %lf",&i,&e,&a,&si,&b2,&t)==6){if(i<0 || i>=TRACKS)return -1;
            rc->resumed.in[i]=(in_mark){a,b2,t,si,e};if(i+1>*ninputs)*ninputs=i+1;}
        else if(sscanf(at,"track %d %lld %d %lld %lld",&i,&a,&h,&b2,&c)==5){if(i<1 || i>TRACKS)return -1;
            rc->base[i-1]=a;rc->tracks[i-1].end=a;rc->tracks[i-1].has_start=h;rc->tracks[i-1].start=b2;rc->tracks[i-1].shift=c;rc->tracks[i-1].from_mark=h;}
        else if(sscanf(at,"side %d %lld",&i,&a)==2){if(i<0 || i>=TRACKS)return -1;rc->resumed.side[i]=a;}
        else if(sscanf(at,"tfra %u %lld %lld",&id,&a,&b2)==3){if(b2>=rc->resume_at)continue;if(tfra_add(rc,id,a,b2)<0)return -1;}
    }
    if(rc->resume_at<=0 || !rc->resume_seq || !rc->layout[0] || !*ninputs)return -1;
    rc->resume=1;rc->shift_known=1;rc->emitted=rc->ntfra;return 0;
}
static int sink_write(void *opaque,const uint8_t *data,int size) {
    output_sink *s=opaque;
    if(s->track || (s->initialized && !s->rc))return s->write(s->track,s->suffix,data,size,s->context)?size:AVERROR_EXIT;
    if(s->initialized)return out_feed(s,data,size)?size:AVERROR_EXIT;
    // Only the init boxes are buffered, capped independently of movie duration/size.
    if(size<0 || s->init_size>4*1024*1024-size)return AVERROR(ENOMEM);
    uint8_t *grown=av_realloc(s->init,(size_t)(s->init_size+size));if(!grown)return AVERROR(ENOMEM);
    s->init=grown;memcpy(s->init+s->init_size,data,(size_t)size);s->init_size+=size;
    for(int at=0;at+8<=s->init_size;) {
        uint64_t n=AV_RB32(s->init+at);int header=8;
        if(n==1){if(at+16>s->init_size)return size;n=AV_RB64(s->init+at+8);header=16;}
        if(n<(uint64_t)header)return AVERROR_INVALIDDATA;
        if(n>(uint64_t)(s->init_size-at))return size;
        if(AV_RB32(s->init+at+4)==MKBETAG('m','o','o','v')) {
            uint32_t scale=0;
            if(init_duration(s->init+at,(int)n,s->duration,&scale)<0)return AVERROR_INVALIDDATA;
            int end=s->rc?at+(int)n:s->init_size;   // r30: what follows the moov goes through the parser
            if(!(s->rc && s->rc->resume) && !s->write(0,s->suffix,s->init,end,s->context))return AVERROR_EXIT;   // a resumed run's init is already on Drive
            if(s->rc)s->rc->at=s->rc->resume?s->rc->resume_at:end;
            s->initialized=1;
            int rest=s->init_size-end;uint8_t *init=s->init;s->init=NULL;s->init_size=0;
            int ok=rest<=0 || out_feed(s,init+end,rest);av_free(init);
            return ok?size:AVERROR_EXIT;
        }
        at+=(int)n;
    }
    return size;
}
static int sink_open(AVFormatContext *f,output_sink *sink) {
    int size=sink->track?32768:SINK_BUFFER;
    uint8_t *buffer=av_malloc((size_t)size);if(!buffer)return -1;
    f->pb=avio_alloc_context(buffer,size,1,sink,NULL,sink_write,NULL);
    if(!f->pb){av_free(buffer);return -1;}f->flags|=AVFMT_FLAG_CUSTOM_IO;return 0;
}
static void sink_close(AVFormatContext *f) {
    if(f && f->pb){av_freep(&f->pb->buffer);avio_context_free(&f->pb);}
}
typedef struct {AVCodecContext *dec,*enc;} subtitle;
static int next(input_track *in) {
    av_packet_unref(in->packet);
    int r;
    while((r=av_read_frame(in->f,in->packet))>=0) {
        int n=in->packet->stream_index;
        if(n>=0 && n<TRACKS && in->map[n]>=0)return 0;
        av_packet_unref(in->packet);
    }
    if(r!=AVERROR_EOF)return r;
    in->eof=1;return 0;
}
static double packet_time(input_track *in) {
    AVPacket *p=in->packet;int64_t t=p->dts!=AV_NOPTS_VALUE?p->dts:p->pts;
    return t==AV_NOPTS_VALUE?0:t*av_q2d(in->f->streams[p->stream_index]->time_base);
}
static int validate(const char *path,AVFormatContext *original,int expected_tracks,char *err,int en) {
    AVFormatContext *f=NULL;int r=-1;
    {AVDictionary *o=NULL;reading_options(&o,path);   // r31: same reader as everywhere, opened by the index
     int q=avformat_open_input(&f,path,NULL,&o);av_dict_free(&o);if(q<0 || avformat_find_stream_info(f,NULL)<0)goto end;}
    int a=video_index(original),b=video_index(f);
    if(a<0 || b<0 || (int)f->nb_streams!=expected_tracks || !kr_prepare_ready(f))goto end;
    AVCodecParameters *src=original->streams[a]->codecpar,*dst=f->streams[b]->codecpar;
    if(src->width!=dst->width || src->height!=dst->height || hdr(src)!=hdr(dst))goto end;
    if(original->duration<=0 || f->duration<=0 || llabs(original->duration-f->duration)>2*AV_TIME_BASE)goto end;
    // Exercise the index at a long seek and near the end; do not accept a truncated, unseekable result.
    AVPacket *p=av_packet_alloc();if(!p)goto end;
    for(int k=1;k<=2;k++) {
        double target=(double)f->duration/AV_TIME_BASE*(k==1?.5:.95);
        int64_t t=(int64_t)(target/av_q2d(f->streams[b]->time_base));
        if(av_seek_frame(f,b,t,AVSEEK_FLAG_BACKWARD)<0){av_packet_free(&p);goto end;}
        int found=0;
        for(int count=0;count<4096 && av_read_frame(f,p)>=0;count++) {
            if(p->stream_index==b && p->pts!=AV_NOPTS_VALUE) {
                double at=p->pts*av_q2d(f->streams[b]->time_base);
                if(at>=target-2){found=at<=target+2;av_packet_unref(p);break;}
            }
            av_packet_unref(p);
        }
        if(!found){av_packet_free(&p);goto end;}
    }
    av_packet_free(&p);r=0;
end:avformat_close_input(&f);if(r<0)fail(err,en,"Output validation failed; original retained",0);return r;
}
static int put(AVFormatContext *out,resume_ctx *rc,AVPacket *p) {
    if(!rc)return av_interleaved_write_frame(out,p);
    if(!rc->shift_known && p->dts!=AV_NOPTS_VALUE) {   // FFmpeg's make-non-negative shift, from the first packet
        AVRational tb=out->streams[p->stream_index]->time_base;
        for(unsigned k=0;k<out->nb_streams;k++)rc->tracks[k].shift=p->dts<0?av_rescale_q_rnd(-p->dts,tb,out->streams[k]->time_base,AV_ROUND_UP):0;
        rc->shift_known=1;
    }
    out_track *t=&rc->tracks[p->stream_index];
    // r31 (end-to-end test: a run carried on from a mark differed from a straight run by one tick in one duration): in
    // the first run FFmpeg moved this packet's dts to where the track's earlier durations ended (it starts a fragment);
    // a resumed run starts the track here. Moving dts and pts by the same amount gives the same durations and the same
    // composition offsets, so a copied movie comes out byte for byte the same and Drive's bytes past a mark can be kept.
    // Moving it earlier is always allowed (nothing of this track comes before it here). When the first run had moved it
    // later (a source whose packet durations overshoot), moving it here could pass the next packet: it keeps its time,
    // and only this first fragment's first duration differs from the first run (the fragments after it match).
    if(rc->resume && t->from_mark && !t->carried && p->dts!=AV_NOPTS_VALUE) {
        int64_t moved=t->start-t->shift+rc->base[p->stream_index]-p->dts;
        if(moved<=0){p->dts+=moved;if(p->pts!=AV_NOPTS_VALUE)p->pts+=moved;}
    }
    t->carried=1;
    if(!t->has_start && p->dts!=AV_NOPTS_VALUE){t->start=p->dts+t->shift;t->has_start=1;}
    int q=av_write_frame(out,p);
    if(q>=0){avio_flush(out->pb);if(out->pb->error<0)q=out->pb->error;}
    return q;
}
// Where every input stands before a packet is written (its next packet), and whether a fragment may start there.
static int unit_start(generated_reader *g,AVFormatContext *f,AVPacket *p) {
    gm_stream *plan=NULL;for(int i=0;i<g->nlanes && !plan;i++)if(g->lanes[i])plan=g->lanes[i]->plan;
    int64_t ts=p->pts!=AV_NOPTS_VALUE?p->pts:p->dts;if(!plan || ts==AV_NOPTS_VALUE)return 0;
    return resume_unit(plan,ts*av_q2d(f->streams[p->stream_index]->time_base),1)>=0;
}
static void snapshot(resume_ctx *rc,input_track *ins,int ninputs,generated_reader *gens,AVFormatContext **side,int pick,int video_out) {
    prep_state *st=&rc->pending;st->markable=0;
    for(int i=0;i<ninputs;i++){in_mark *m=&st->in[i];m->eof=ins[i].eof;
        if(!m->eof){AVPacket *p=ins[i].packet;int64_t ts=p->pts!=AV_NOPTS_VALUE?p->pts:p->dts;
            m->pos=p->pos;m->si=p->stream_index;m->dts=p->dts;m->t=ts==AV_NOPTS_VALUE?0:ts*av_q2d(ins[i].f->streams[p->stream_index]->time_base);}}
    for(int i=0;i<TRACKS;i++)st->side[i]=side[i] && side[i]->pb?avio_tell(side[i]->pb):0;
    AVPacket *p=ins[pick].packet;
    if(ins[pick].map[p->stream_index]!=video_out || !(p->flags&AV_PKT_FLAG_KEY) || p->dts==AV_NOPTS_VALUE)return;
    if(pick>0 && !unit_start(&gens[pick],ins[pick].f,p))return;   // a re-encoded picture: only where a unit starts
    if(!ins[0].eof && (ins[0].packet->pos<0 || ins[0].packet->dts==AV_NOPTS_VALUE))return;
    for(int i=1;i<ninputs;i++)if(!ins[i].eof && ins[i].packet->dts==AV_NOPTS_VALUE)return;
    st->markable=1;
}
// Bring an input to the packet a mark recorded as its next one; everything before it is already in the movie.
// r32 (owner, build 190: Fall 2 "seems to be frozen" after carrying on): lining up after a restart reads the source
// from a little before the mark, which says nothing for a while over a slow line; it now reports stage 4 ("finding where
// it left off"), which also lets the add-on pause or stop it.
static int resume_input(input_track *in,const in_mark *m,int original,kr_prepare_progress cb,void *ctx) {
    if(m->eof){in->eof=1;return 0;}
    if(!original) {
        for(int guard=0;guard<10000000;guard++) {
            if(in->eof)return -1;
            AVPacket *p=in->packet;
            if(p->stream_index==m->si && p->dts==m->dts)return 0;
            if(p->dts!=AV_NOPTS_VALUE && p->dts>m->dts && p->stream_index==m->si)return -1;
            if(!(guard&63) && !tick(cb,ctx,4,(double)guard,(double)guard+1))return -2;
            if(next(in)<0)return -1;
        }
        return -1;
    }
    for(int back=10;back<=1000;back*=10) {
        int64_t ts=(int64_t)((m->t-back)*AV_TIME_BASE);if(ts<0)ts=0;
        if(av_seek_frame(in->f,-1,ts,AVSEEK_FLAG_BACKWARD)<0)return -1;
        in->eof=0;if(next(in)<0)return -1;
        int passed=0;
        while(!in->eof) {
            AVPacket *p=in->packet;
            if(p->pos==m->pos && p->stream_index==m->si && p->dts==m->dts)return 0;
            if(p->pos>m->pos){passed=1;break;}
            if(!tick(cb,ctx,4,p->pos>0?(double)p->pos:0,m->pos>0?(double)m->pos:1))return -2;
            if(next(in)<0)return -1;
        }
        if(!passed)return -1;
        if(ts==0)return -1;
    }
    return -1;
}
static int prepare(const char *input,const char *output,kr_prepare_progress cb,void *ctx,char *err,int en,
                   kr_prepare_write writer,void *writer_context,const char *resume_text) {
    generated_reader gens[TRACKS]={0};AVIOContext *readers[TRACKS]={0};
    output_sink sinks[TRACKS+1]={0};
    for(int i=0;i<=TRACKS;i++){sinks[i].write=writer;sinks[i].context=writer_context;sinks[i].track=i;}
    snprintf(sinks[0].suffix,sizeof sinks[0].suffix,".mp4");
    AVFormatContext *original=NULL,*out=NULL,*side[TRACKS]={0};input_track ins[TRACKS]={0};subtitle subs[TRACKS]={0};
    int ninputs=1,r=-1,header=0,mapped=0,skipped_subs=0,video_out=-1,resumed_inputs=0;
    resume_ctx *rc=NULL;
    if(writer) {
        rc=calloc(1,sizeof *rc);if(!rc)return fail(err,en,"out of memory",0);
        sinks[0].rc=rc;rc->side=side;
        if(resume_text && rc_load(rc,resume_text,&resumed_inputs)<0){free(rc->tfra);free(rc);return fail(err,en,"Resume record is not valid",0);}
    }char partial[4096],spools[TRACKS][4096]={{0}},sides[TRACKS][4200]={{0}};
    if(err && en>0)*err=0;
    if(!local_input(input) || (!writer && (!output || output[0]!='/' || !strcmp(input,output))))return fail(err,en,"A local or loopback input and a separate local output are required",0);
    snprintf(partial,sizeof partial,"%s.partial",output?output:"stream");
    if(open_source(&original,input)<0){fail(err,en,"Cannot read the source video",0);goto end;}
    int vi=video_index(original);if(vi<0 || original->nb_streams>=TRACKS) {fail(err,en,"Unsupported track layout",0);goto end;}
    sinks[0].duration=(double)original->duration/AV_TIME_BASE;
    if(original->duration<=0){fail(err,en,"Source duration is unknown",0);goto end;}
    // r48: an upscaled copy. Only when the picture is smaller than the box; never HDR (the AI models take SDR), never
    // a resize dressed up: the caller asked for this box, so a picture that already fills it is refused, not copied.
    int up=0;
    if(up_box_w>0 && up_box_h>0) {
        AVCodecParameters *p=original->streams[vi]->codecpar;int ow=0,oh=0;
        if(hdr(p)){fail(err,en,"HDR video is kept as it is (not upscaled)",0);goto end;}
        if(!kr_video_upscale_size(p->width,p->height,p->sample_aspect_ratio,up_box_w,up_box_h,&ow,&oh)){fail(err,en,"The video is already this size; no upscaled copy needed",0);goto end;}
        up=1;kr_video_set_upscale(up_box_w,up_box_h,up_engine,up_kbps);
        kr_remux_note("prepare: upscaled copy %dx%d -> %dx%d (engine %d)",p->width,p->height,ow,oh,up_engine);
    }
    if(!copy_video(original->streams[vi]->codecpar)) {
        AVCodecParameters *p=original->streams[vi]->codecpar;
        for(int i=0;i<p->nb_coded_side_data;i++)if(p->coded_side_data[i].type==AV_PKT_DATA_DOVI_CONF) {
            fail(err,en,"This Dolby Vision codec needs RPU remapping; original retained",0);goto end;
        }
    }
    // Never silently discard image subtitles or alternate video tracks during an in-place replacement.
    for(unsigned i=0;i<original->nb_streams;i++) {
        AVCodecParameters *p=original->streams[i]->codecpar;
        if((p->codec_type==AVMEDIA_TYPE_SUBTITLE && keep_subtitle(original,i) && !text_sub(p->codec_id) && !sidecar_sub(p)) ||
           (p->codec_type==AVMEDIA_TYPE_VIDEO && i!=(unsigned)vi && !(original->streams[i]->disposition&AV_DISPOSITION_ATTACHED_PIC))) {
            fail(err,en,"This file has tracks MP4 cannot preserve; original retained",0);goto end;
        }
    }
    if(avformat_alloc_output_context2(&out,NULL,"mp4",partial)<0 || !out)goto end;
    ins[0].f=original;
    for(int i=0;i<TRACKS;i++){for(int j=0;j<TRACKS;j++)ins[i].map[j]=-1;}
    for(unsigned i=0;i<original->nb_streams;i++) {
        AVStream *src=original->streams[i];AVCodecParameters *p=src->codecpar;
        if((int)i!=vi && p->codec_type!=AVMEDIA_TYPE_AUDIO && p->codec_type!=AVMEDIA_TYPE_SUBTITLE)continue;
        if(p->codec_type==AVMEDIA_TYPE_AUDIO && !keep_audio(original,i))continue;   // r25: other languages left out
        if(p->codec_type==AVMEDIA_TYPE_SUBTITLE && !keep_subtitle(original,i))continue;   // r27: other languages left out
        if(sidecar_sub(p)) {
            // Its own .sup file, packets copied as they are (written as .partial, renamed with the MP4).
            char lang[9]="und";AVDictionaryEntry *l=av_dict_get(src->metadata,"language",NULL,0);
            if(l && l->value[0]){int k=0;for(const char *c=l->value;*c && k<8;c++)if((*c>='a'&&*c<='z')||(*c>='A'&&*c<='Z'))lang[k++]=(char)(*c|32);if(k)lang[k]=0;}
            snprintf(sides[i],sizeof sides[i],"%s.sub%u.%s%s.sup",output?output:"stream",i,lang,(src->disposition&AV_DISPOSITION_FORCED)?".forced":"");
            snprintf(sinks[i+1].suffix,sizeof sinks[i+1].suffix,".%s%s.%u.sup",lang,(src->disposition&AV_DISPOSITION_FORCED)?".forced":"",i);
            char part[4300];snprintf(part,sizeof part,"%s.partial",sides[i]);
            AVStream *s=NULL;
            if(avformat_alloc_output_context2(&side[i],NULL,"sup",part)<0 || !side[i] || !(s=avformat_new_stream(side[i],NULL)) ||
               avcodec_parameters_copy(s->codecpar,p)<0){fail(err,en,"Picture subtitle file",0);goto end;}
            s->time_base=src->time_base;s->codecpar->codec_tag=0;
            if((writer?sink_open(side[i],&sinks[i+1]):avio_open(&side[i]->pb,part,AVIO_FLAG_WRITE))<0 || avformat_write_header(side[i],NULL)<0){fail(err,en,"Picture subtitle file",0);goto end;}
            ins[0].map[i]=SIDECAR;continue;
        }
        AVStream *dst=avformat_new_stream(out,NULL);if(!dst)goto end;mapped++;
        av_dict_copy(&dst->metadata,src->metadata,0);dst->disposition=src->disposition;dst->time_base=src->time_base;
        avcodec_parameters_copy(dst->codecpar,p);dst->codecpar->codec_tag=0;
        int generated=((int)i==vi && (!copy_video(p) || up)) || (p->codec_type==AVMEDIA_TYPE_AUDIO && p->codec_id!=AV_CODEC_ID_AAC);
        if(generated) {
            int ni=ninputs++;input_track *one=&ins[ni];one->own=1;
            if(writer) {
                double at=rc && rc->resume && ni<resumed_inputs && !rc->resumed.in[ni].eof?rc->resumed.in[ni].t:-1;
                if(generated_open(&gens[ni],&one->f,&readers[ni],input,(int)i,(int)i==vi,cb,ctx,err,en,at)<0)goto end;
                one->f->probesize=2*1024*1024;one->f->max_analyze_duration=AV_TIME_BASE;
                if(avformat_find_stream_info(one->f,NULL)<0){fail(err,en,"Converted track inspection failed",0);goto end;}
            } else {
                snprintf(spools[i],sizeof spools[i],"%s.track%u",output,i);
                int q=spool(input,spools[i],(int)i,(int)i==vi,cb,ctx,err,en);if(q){r=q;goto end;}
                if(avformat_open_input(&one->f,spools[i],NULL,NULL)<0 || avformat_find_stream_info(one->f,NULL)<0)goto end;
            }
            if(one->f->nb_streams!=1)goto end;
            one->map[0]=dst->index;if((int)i==vi)video_out=dst->index;avcodec_parameters_copy(dst->codecpar,one->f->streams[0]->codecpar);
            dst->codecpar->codec_tag=0;dst->time_base=one->f->streams[0]->time_base;
            // Preserve static HDR metadata when another HDR codec is encoded to HEVC Main10.
            if((int)i==vi)for(int m=0;m<p->nb_coded_side_data;m++) {
                AVPacketSideData *from=&p->coded_side_data[m];
                if(from->type!=AV_PKT_DATA_MASTERING_DISPLAY_METADATA && from->type!=AV_PKT_DATA_CONTENT_LIGHT_LEVEL)continue;
                AVPacketSideData *to=av_packet_side_data_new(&dst->codecpar->coded_side_data,&dst->codecpar->nb_coded_side_data,from->type,from->size,0);
                if(!to)goto end;memcpy(to->data,from->data,from->size);
            }
        } else {
            ins[0].map[i]=dst->index;if((int)i==vi)video_out=dst->index;
            if(p->codec_type==AVMEDIA_TYPE_SUBTITLE && p->codec_id!=AV_CODEC_ID_MOV_TEXT) {
                subtitle *s=&subs[i];const AVCodec *dc=avcodec_find_decoder(p->codec_id),*ec=avcodec_find_encoder(AV_CODEC_ID_MOV_TEXT);
                if(!dc || !ec){fail(err,en,"Subtitle encoder unavailable",0);goto end;}
                s->dec=avcodec_alloc_context3(dc);s->enc=avcodec_alloc_context3(ec);if(!s->dec || !s->enc)goto end;
                avcodec_parameters_to_context(s->dec,p);
                if(avcodec_open2(s->dec,dc,NULL)<0)goto end;
                s->enc->time_base=(AVRational){1,1000};s->enc->flags|=AV_CODEC_FLAG_GLOBAL_HEADER;
                if(s->dec->subtitle_header_size>0) {
                    s->enc->subtitle_header=av_mallocz(s->dec->subtitle_header_size+AV_INPUT_BUFFER_PADDING_SIZE);
                    if(!s->enc->subtitle_header)goto end;
                    memcpy(s->enc->subtitle_header,s->dec->subtitle_header,s->dec->subtitle_header_size);
                    s->enc->subtitle_header_size=s->dec->subtitle_header_size;
                }
                if(avcodec_open2(s->enc,ec,NULL)<0 || avcodec_parameters_from_context(dst->codecpar,s->enc)<0)goto end;
                dst->time_base=(AVRational){1,1000};
            }
        }
        if(dst->codecpar->codec_id==AV_CODEC_ID_HEVC)dst->codecpar->codec_tag=MKTAG('h','v','c','1');
    }
    av_dict_copy(&out->metadata,original->metadata,0);
    av_dict_set(&out->metadata,"kodi_airplay_prepared","source-resolution-v1",0);
    if(up && video_out>=0) {
        char tag[64];snprintf(tag,sizeof tag,"%dx%d engine=%d",out->streams[video_out]->codecpar->width,out->streams[video_out]->codecpar->height,up_engine);
        av_dict_set(&out->metadata,"kodi_airplay_upscaled",tag,0);
    }
    out->avoid_negative_ts=AVFMT_AVOID_NEG_TS_MAKE_NON_NEGATIVE;
    if((writer?sink_open(out,&sinks[0]):avio_open(&out->pb,partial,AVIO_FLAG_WRITE))<0)goto end;
    if(rc) {
        // The same source, settings and framework give the same tracks; a mark from anything else starts over.
        char layout[sizeof rc->layout];int n=snprintf(layout,sizeof layout,"%u/%d",out->nb_streams,ninputs);
        for(unsigned k=0;k<out->nb_streams && n<(int)sizeof layout-16;k++)n+=snprintf(layout+n,sizeof layout-(size_t)n,"/%d",(int)out->streams[k]->codecpar->codec_id);
        for(int k=0;k<TRACKS && n<(int)sizeof layout-16;k++)if(side[k])n+=snprintf(layout+n,sizeof layout-(size_t)n,"/s%d",k);
        if(rc->resume && (strcmp(layout,rc->layout) || resumed_inputs!=ninputs)){fail(err,en,"Resume record does not match this video",0);goto end;}
        snprintf(rc->layout,sizeof rc->layout,"%s",layout);rc->nstreams=(int)out->nb_streams;rc->ninputs=ninputs;
    }
    AVDictionary *opts=NULL;av_dict_set(&opts,"movflags",writer?"+empty_moov+default_base_moof+frag_keyframe+use_metadata_tags+skip_trailer":"+faststart+use_metadata_tags",0);
    if(writer) {
        // r32 (owner, build 190: a prepared Interstellar took 30 s to start in Kodi and the picture broke up, while the
        // original MKV started at once): each fragment held all its picture, then all its sound, so Kodi's player
        // jumped back and forth inside every fragment, each jump a new Drive request; and it opens a file by reading
        // every fragment header (~1,700 for Interstellar). Samples are now interleaved inside fragments (12 at a time,
        // like an MKV), and fragments hold about FRAG_BYTES of the movie (6-60 s, from its bitrate) instead of starting
        // at every keyframe, at most FRAG_MAX bytes in memory.
        const int64_t FRAG_BYTES=64LL*1024*1024,FRAG_MAX=96LL*1024*1024;
        int64_t rate=original->bit_rate>0?original->bit_rate:0;
        if(!rate && original->pb && original->duration>0){int64_t size=avio_size(original->pb);if(size>0)rate=(int64_t)(size*8.0/((double)original->duration/AV_TIME_BASE));}
        double seconds=rate>0?FRAG_BYTES*8.0/(double)rate:6.0;
        if(seconds<6)seconds=6;if(seconds>60)seconds=60;
        const char *forced=getenv("KR_PREP_FRAG_S");   // host tests: short test films keep several marks
        if(forced && atof(forced)>0)seconds=atof(forced);
        av_dict_set_int(&opts,"min_frag_duration",(int64_t)(seconds*1e6),0);
        av_dict_set_int(&opts,"frag_duration",(int64_t)(seconds*2e6),0);
        av_dict_set_int(&opts,"frag_size",FRAG_MAX,0);
        av_dict_set(&opts,"frag_interleave","12",0);
        kr_remux_note("prepare: fragments of about %.0f s (source %.1f Mbit/s), samples interleaved",seconds,rate/1e6);
    }
    if(rc && rc->resume)av_dict_set_int(&opts,"fragment_index",rc->resume_seq,0);
    int q=avformat_write_header(out,&opts);av_dict_free(&opts);if(q<0){fail(err,en,"MP4 header",q);goto end;}header=1;
    for(int i=0;i<ninputs;i++){ins[i].packet=av_packet_alloc();if(!ins[i].packet || next(&ins[i])<0)goto end;}
    if(rc && rc->resume) {
        for(int i=0;i<ninputs;i++) {
            int q=resume_input(&ins[i],&rc->resumed.in[i],i==0,cb,ctx);
            if(q==-2){r=-2;goto end;}
            if(q<0){fail(err,en,"Resume position not found",0);goto end;}
        }
        for(int i=0;i<TRACKS;i++)gens[i].resuming=0;
        kr_remux_note("prepare: carrying on from %.0f s (byte %lld, fragment %u)",rc->resumed.in[0].eof?rc->resumed.in[ninputs>1?1:0].t:rc->resumed.in[0].t,(long long)rc->resume_at,rc->resume_seq);
    }
    unsigned packets=0;
    for(;;) {
        int pick=-1;double earliest=0;
        for(int i=0;i<ninputs;i++)if(!ins[i].eof && (pick<0 || packet_time(&ins[i])<earliest)){pick=i;earliest=packet_time(&ins[i]);}
        if(pick<0)break;
        if((packets++%128)==0 && !tick(cb,ctx,2,earliest,(double)original->duration/AV_TIME_BASE)){r=-2;goto end;}
        input_track *in=&ins[pick];AVPacket *p=in->packet;int si=p->stream_index,di=in->map[si];
        if(pick==0 && di==SIDECAR) {
            AVStream *from=in->f->streams[si],*to=side[si]->streams[0];
            av_packet_rescale_ts(p,from->time_base,to->time_base);p->stream_index=0;p->pos=-1;
            // r19 (owner, build 168: Inception failed after 30 min on "Picture subtitle packet: Invalid data"): a
            // malformed or empty PGS packet is skipped; the rest of the subtitles and the movie carry on.
            q=p->size>0?av_write_frame(side[si],p):0;
            if(q==AVERROR_INVALIDDATA || q==AVERROR(EINVAL)){skipped_subs++;(void)skipped_subs;q=0;}
            if(q<0){fail(err,en,"Picture subtitle packet",q);goto end;}
            q=next(in);if(q<0){fail(err,en,"Source read",q);goto end;}
            continue;
        }
        AVStream *src=in->f->streams[si],*dst=out->streams[di];
        if(rc)snapshot(rc,ins,ninputs,gens,side,pick,video_out);
        if(pick==0 && subs[si].dec) {
            AVSubtitle sub={0};int got=0;
            q=avcodec_decode_subtitle2(subs[si].dec,&sub,&got,p);
            if(q<0){avsubtitle_free(&sub);fail(err,en,"Subtitle decode",q);goto end;}
            if(got) {
                AVPacket *encoded=av_packet_alloc();if(!encoded){avsubtitle_free(&sub);goto end;}
                if(av_new_packet(encoded,262144)<0){av_packet_free(&encoded);avsubtitle_free(&sub);goto end;}
                q=avcodec_encode_subtitle(subs[si].enc,encoded->data,encoded->size,&sub);
                if(q<0){av_packet_free(&encoded);avsubtitle_free(&sub);fail(err,en,"Subtitle encode",q);goto end;}
                encoded->size=q;encoded->stream_index=di;
                int64_t base=p->pts==AV_NOPTS_VALUE?0:av_rescale_q(p->pts,src->time_base,dst->time_base);
                encoded->pts=encoded->dts=base+av_rescale_q(sub.start_display_time,(AVRational){1,1000},dst->time_base);
                encoded->duration=av_rescale_q(sub.end_display_time-sub.start_display_time,(AVRational){1,1000},dst->time_base);
                q=put(out,rc,encoded);av_packet_free(&encoded);
            }
            avsubtitle_free(&sub);
        } else {
            av_packet_rescale_ts(p,src->time_base,dst->time_base);p->stream_index=di;p->pos=-1;
            q=put(out,rc,p);
        }
        if(q<0){fail(err,en,"MP4 packet",q);goto end;}
        q=next(in);if(q<0){fail(err,en,"Source read",q);goto end;}
    }
    if(!tick(cb,ctx,3,0,1)){r=-2;goto end;}
    q=av_write_trailer(out);header=0;
    if(writer){avio_flush(out->pb);if(out->pb->error<0)q=out->pb->error;}
    if(rc && q>=0 && (rc->in_moof || write_mfra(&sinks[0])<0))q=AVERROR_EXIT;
    if(q<0 || (!writer && avio_closep(&out->pb)<0)){fail(err,en,"MP4 finalization",q);goto end;}
    for(int i=0;i<TRACKS;i++) if(side[i]) {
        q=av_write_trailer(side[i]);
        if(writer){avio_flush(side[i]->pb);if(side[i]->pb->error<0)q=side[i]->pb->error;}
        if(q<0 || (!writer && avio_closep(&side[i]->pb)<0)){fail(err,en,"Picture subtitle file",q);goto end;}
    }
    if(!writer && validate(partial,original,mapped,err,en)<0)goto end;
    if(!tick(cb,ctx,3,1,1)){r=-2;goto end;}
    for(int i=0;i<TRACKS;i++) if(side[i]) {
        char part[4300];snprintf(part,sizeof part,"%s.partial",sides[i]);
        if(!writer && rename(part,sides[i])){fail(err,en,"Cannot commit picture subtitle file",0);goto end;}
    }
    if(!writer && rename(partial,output)){fail(err,en,"Cannot commit prepared file",0);goto end;}
    r=0;
end:
    (void)header;
    for(int i=0;i<TRACKS;i++) {
        avcodec_free_context(&subs[i].dec);avcodec_free_context(&subs[i].enc);
        av_packet_free(&ins[i].packet);if(ins[i].own)avformat_close_input(&ins[i].f);
        if(readers[i]){av_freep(&readers[i]->buffer);avio_context_free(&readers[i]);}generated_close(&gens[i]);
        if(r==0 && spools[i][0]){unlink(spools[i]);char state[4110];snprintf(state,sizeof state,"%s.state",spools[i]);unlink(state);}
        if(side[i]){if(writer)sink_close(side[i]);else if(side[i]->pb)avio_closep(&side[i]->pb);avformat_free_context(side[i]);side[i]=NULL;}
        if(!writer && r && sides[i][0]){char part[4300];snprintf(part,sizeof part,"%s.partial",sides[i]);unlink(part);unlink(sides[i]);}
    }
    if(out){if(writer)sink_close(out);else if(out->pb)avio_closep(&out->pb);avformat_free_context(out);}
    avformat_close_input(&original);if(r && !writer)unlink(partial);
    for(int i=0;i<=TRACKS;i++)av_free(sinks[i].init);
    if(rc){av_free(rc->moof);free(rc->tfra);free(rc);}
    // r48: the upscale asked for was for this conversion only; the next one is an ordinary preparation unless the
    // add-on asks again (a stopped copy that carries on sets it again before resuming).
    if(up_box_w || up_box_h){kr_video_set_upscale(0,0,-1,0);up_box_w=up_box_h=0;up_engine=KR_UP_AUTO;up_kbps=0;}
    if(r==-1 && err && en>0 && !*err)fail(err,en,"Preparation failed; original retained",0);
    return r;
}

int kodi_airplay_prepare(const char *input,const char *output,kr_prepare_progress cb,void *ctx,char *err,int en) {
    return prepare(input,output,cb,ctx,err,en,NULL,NULL,NULL);
}
// Non-seekable output with a completed fragment index (mfra). The caller must remotely
// validate the completed file before replacing the original; successful generation alone is insufficient.
int kodi_airplay_prepare_to(const char *input,kr_prepare_write write,void *write_context,
                            kr_prepare_progress cb,void *ctx,char *err,int en) {
    if(!write)return fail(err,en,"Output callback is required",0);
    return prepare(input,NULL,cb,ctx,err,en,write,write_context,NULL);
}
int kodi_airplay_prepare_resume(const char *input,const char *resume,kr_prepare_write write,void *write_context,
                                kr_prepare_progress cb,void *ctx,char *err,int en) {
    if(!write || !resume)return fail(err,en,"Output callback and resume record are required",0);
    return prepare(input,NULL,cb,ctx,err,en,write,write_context,resume);
}

int kodi_airplay_verify(const char *input,const char *output,char *err,int en) {
    AVFormatContext *original=NULL;int r=-1,mapped=0;
    if(!local_input(input) || !local_input(output))return -1;
    if(open_source(&original,input)<0)goto end;
    int vi=video_index(original);
    for(unsigned i=0;i<original->nb_streams;i++){
        AVCodecParameters *p=original->streams[i]->codecpar;
        if((int)i==vi || (p->codec_type==AVMEDIA_TYPE_AUDIO && keep_audio(original,i)) ||
           (p->codec_type==AVMEDIA_TYPE_SUBTITLE && text_sub(p->codec_id) && keep_subtitle(original,i)))mapped++;
    }
    r=validate(output,original,mapped,err,en);
end:avformat_close_input(&original);return r;
}
