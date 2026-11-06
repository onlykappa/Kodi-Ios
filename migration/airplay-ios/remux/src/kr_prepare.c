// One-file preparation: preserve H.264/HEVC packets (including 4K/HDR/Dolby metadata),
// bridge other SDR video at its ORIGINAL dimensions, AAC audio, selectable text subtitles,
// and a front-loaded MP4 sample index. No conversion or speculative segment queue at playback.
#include "kr_prepare.h"
#include "kr_video.h"
#include "kr_audio.h"
#include "kr_source.h"
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

#define TRACKS 64
#define SIDECAR TRACKS   // map value of a picture subtitle track written beside the MP4 (r15), not into it

// r15 (owner, build 160: "Interstellar ... needs to be ready for airplay"): MP4 cannot hold Blu-ray picture subtitles
// (PGS). With this on, each PGS track is kept, untouched, in its own .sup file beside the prepared MP4
// (output.sub<track>.<language>[.forced].sup); the setup add-on saves them next to the video on Google Drive, where
// Kodi finds them as external subtitles. Off (the default), such a file is refused as before, so a caller that cannot
// save the .sup files never loses them.
static int keep_image_subs=0;
void kodi_airplay_prepare_keep_image_subs(int on) { keep_image_subs=on!=0; }
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
static int open_source_checked(AVFormatContext **f,const char *input,inspect_wait *wait) {
    AVDictionary *o=NULL;int r;
    *f=avformat_alloc_context();if(!*f)return AVERROR(ENOMEM);
    if(wait)(*f)->interrupt_callback=(AVIOInterruptCB){inspect_interrupt,wait};
    if(!strncmp(input,"http://",7)) {
        av_dict_set(&o,"rw_timeout","30000000",0);
        av_dict_set(&o,"reconnect","1",0);av_dict_set(&o,"reconnect_on_network_error","1",0);
        av_dict_set(&o,"reconnect_delay_max","5",0);av_dict_set(&o,"reconnect_max_retries","3",0);
        av_dict_set(&o,"reconnect_delay_total_max","15",0);av_dict_set(&o,"reconnect_on_http_error","429,500,502,503,504",0);
        av_dict_set(&o,"seekable","1",0);av_dict_set(&o,"multiple_requests","1",0);
        av_dict_set(&o,"user_agent","Kodi-iOS-AirPlay/1",0);
    }
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
static int probe(const char *input,char *json,int size,kr_prepare_progress cb,void *ctx) {
    AVFormatContext *f=NULL;int r=-1;
    if(!local_input(input) || !json || size<2) return -1;
    inspect_wait wait={av_gettime_relative()+120LL*AV_TIME_BASE,cb,ctx,0};
    int opened=open_source_checked(&f,input,&wait);
    if(opened<0){r=opened==AVERROR_EXIT?-2:opened==AVERROR(ETIMEDOUT)?-3:-1;goto end;}
    int v=video_index(f);if(v<0) goto end;
    AVCodecParameters *p=f->streams[v]->codecpar;
    double audio_work=0,duration=f->duration>0?(double)f->duration/AV_TIME_BASE:0;int pgs=0,other_image=0,extra_video=0;
    for(unsigned i=0;i<f->nb_streams;i++) {
        AVCodecParameters *a=f->streams[i]->codecpar;
        if(a->codec_type==AVMEDIA_TYPE_AUDIO && a->codec_id!=AV_CODEC_ID_AAC)
            audio_work+=duration*(a->ch_layout.nb_channels>=6?384000:160000)/8;
        if(a->codec_type==AVMEDIA_TYPE_SUBTITLE && !text_sub(a->codec_id)){if(a->codec_id==AV_CODEC_ID_HDMV_PGS_SUBTITLE)pgs++;else other_image++;}
        if(a->codec_type==AVMEDIA_TYPE_VIDEO && (int)i!=v && !(f->streams[i]->disposition&AV_DISPOSITION_ATTACHED_PIC))extra_video++;
    }
    // r15: the codec and the tracks that decide whether and how a file can be prepared, for the owner's status page.
    snprintf(json,(size_t)size,"{\"ready\":%s,\"width\":%d,\"height\":%d,\"hdr\":%s,\"duration\":%.6f,\"copy_video\":%s,\"audio_work_bytes\":%.0f,"
             "\"codec\":\"%s\",\"bit_depth\":%d,\"pgs_subtitles\":%d,\"other_image_subtitles\":%d,\"extra_video\":%d}",
             kr_prepare_ready(f) && av_dict_get(f->metadata,"kodi_airplay_prepared",NULL,0)?"true":"false",p->width,p->height,hdr(p)?"true":"false",
             duration,copy_video(p)?"true":"false",audio_work,avcodec_get_name(p->codec_id),
             p->bits_per_raw_sample?p->bits_per_raw_sample:(av_pix_fmt_desc_get(p->format)?av_pix_fmt_desc_get(p->format)->comp[0].depth:0),
             pgs,other_image,extra_video);r=0;
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
// A whole track is bounded-memory fMP4; only the current six-second unit is held in RAM.
// Spools checkpoint after every completed segment, so restart/pause does not redo a movie.
static int spool(const char *input,const char *path,int index,int is_video,
                 kr_prepare_progress cb,void *ctx,char *err,int en) {
    kr_source *source=NULL;gm_stream *plan=NULL;kr_video *video=NULL;kr_audio *audio=NULL;
    FILE *file=NULL;gm_buf unit={0};int r=-1,first=0;long long offset=0;
    char state[4096],tmp[4100];snprintf(state,sizeof state,"%s.state",path);snprintf(tmp,sizeof tmp,"%s.tmp",state);
    source=kr_source_open(input,30,err,en);if(!source)goto end;
    plan=gm_stream_open(kr_source_gm(source),6,err,en);if(!plan)goto end;
    if(is_video) {
        video=kr_video_open(kr_source_gm(source),index,err,en);if(!video)goto end;
        kr_video_keep_resolution(video);
    } else {audio=kr_audio_open(kr_source_gm(source),index,err,en);if(!audio)goto end;}
    FILE *saved=fopen(state,"r");if(saved){if(fscanf(saved,"%d %lld",&first,&offset)!=2){first=0;offset=0;}fclose(saved);}
    struct stat st;
    if(first<0 || offset<0 || stat(path,&st) || st.st_size<offset){first=0;offset=0;}
    file=fopen(path,first?"r+b":"w+b");if(!file){fail(err,en,"Cannot create working file",0);goto end;}
    if(ftruncate(fileno(file),(off_t)offset) || fseeko(file,(off_t)offset,SEEK_SET)){fail(err,en,"Cannot resume working file",0);goto end;}
    int count=gm_stream_segment_count(plan);
    if(first>count){fail(err,en,"Invalid conversion checkpoint",0);goto end;}
    for(int i=first;i<count;i++) {
        if(!tick(cb,ctx,is_video?0:1,i,count)){r=-2;goto end;}
        unit.len=0;
        int q=is_video?kr_video_unit(video,plan,i,&unit,err,en):kr_audio_unit(audio,plan,i,&unit,err,en);
        if(q<0)goto end;
        int start=i?kr_first_moof(unit.data,unit.len):0;
        if(start<0 || fwrite(unit.data+start,1,(size_t)(unit.len-start),file)!=(size_t)(unit.len-start) ||
           fflush(file) || fsync(fileno(file))){fail(err,en,"Cannot save converted segment",0);goto end;}
        offset=(long long)ftello(file);
        saved=fopen(tmp,"w");if(!saved){fail(err,en,"Cannot save conversion checkpoint",0);goto end;}
        int ok=fprintf(saved,"%d %lld\n",i+1,offset)>0 && !fflush(saved) && !fsync(fileno(saved));
        if(fclose(saved) || !ok || rename(tmp,state)){fail(err,en,"Cannot commit conversion checkpoint",0);goto end;}
    }
    r=0;
end:if(file)fclose(file);free(unit.data);kr_video_close(video);kr_audio_close(audio);
    gm_stream_close(plan);kr_source_close(source);return r;
}
// Sequential conversion source: only the current six-second unit lives in RAM. Unlike the
// legacy spool this reader never opens a working file. Each track owns its demuxer.
typedef struct {
    kr_source *source;gm_stream *plan;kr_video *video;kr_audio *audio;
    gm_buf unit;int segment,offset,count,is_video;kr_prepare_progress progress;void *context;
    char *error;int error_size;
} generated_reader;
static int generated_read(void *opaque,uint8_t *data,int size) {
    generated_reader *g=opaque;
    if(g->offset>=g->unit.len) {
        if(g->segment>=g->count)return AVERROR_EOF;
        if(!tick(g->progress,g->context,g->is_video?0:1,g->segment,g->count))return AVERROR_EXIT;
        g->unit.len=0;
        int r=g->is_video?kr_video_unit(g->video,g->plan,g->segment,&g->unit,g->error,g->error_size):
                          kr_audio_unit(g->audio,g->plan,g->segment,&g->unit,g->error,g->error_size);
        if(r<0)return AVERROR(EIO);
        g->offset=g->segment?kr_first_moof(g->unit.data,g->unit.len):0;
        if(g->offset<0 || g->offset>=g->unit.len)return AVERROR_INVALIDDATA;
        g->segment++;
    }
    int n=FFMIN(size,g->unit.len-g->offset);memcpy(data,g->unit.data+g->offset,(size_t)n);g->offset+=n;return n;
}
static void generated_close(generated_reader *g) {
    kr_video_close(g->video);kr_audio_close(g->audio);gm_stream_close(g->plan);
    kr_source_close(g->source);free(g->unit.data);memset(g,0,sizeof *g);
}
static int generated_open(generated_reader *g,AVFormatContext **format,AVIOContext **io,
                          const char *input,int index,int video,kr_prepare_progress cb,void *ctx,char *err,int en) {
    g->is_video=video;g->progress=cb;g->context=ctx;g->error=err;g->error_size=en;
    g->source=kr_source_open(input,30,err,en);if(!g->source)return -1;
    g->plan=gm_stream_open(kr_source_gm(g->source),6,err,en);if(!g->plan)return -1;
    g->count=gm_stream_segment_count(g->plan);
    if(video){g->video=kr_video_open(kr_source_gm(g->source),index,err,en);if(!g->video)return -1;kr_video_keep_resolution(g->video);}
    else {g->audio=kr_audio_open(kr_source_gm(g->source),index,err,en);if(!g->audio)return -1;}
    uint8_t *buffer=av_malloc(32768);if(!buffer)return -1;
    *io=avio_alloc_context(buffer,32768,0,g,generated_read,NULL,NULL);
    if(!*io){av_free(buffer);return -1;}
    *format=avformat_alloc_context();if(!*format)return -1;
    (*format)->pb=*io;(*format)->flags|=AVFMT_FLAG_CUSTOM_IO;
    return avformat_open_input(format,NULL,av_find_input_format("mov"),NULL);
}
typedef struct {
    kr_prepare_write write;void *context;int track;char suffix[80];
    uint8_t *init;int init_size,initialized;double duration;
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
static int sink_write(void *opaque,const uint8_t *data,int size) {
    output_sink *s=opaque;
    if(s->track || s->initialized)return s->write(s->track,s->suffix,data,size,s->context)?size:AVERROR_EXIT;
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
            if(!s->write(0,s->suffix,s->init,s->init_size,s->context))return AVERROR_EXIT;
            av_freep(&s->init);s->init_size=0;s->initialized=1;return size;
        }
        at+=(int)n;
    }
    return size;
}
static int sink_open(AVFormatContext *f,output_sink *sink) {
    uint8_t *buffer=av_malloc(32768);if(!buffer)return -1;
    f->pb=avio_alloc_context(buffer,32768,1,sink,NULL,sink_write,NULL);
    if(!f->pb){av_free(buffer);return -1;}f->flags|=AVFMT_FLAG_CUSTOM_IO;return 0;
}
static void sink_close(AVFormatContext *f) {
    if(f && f->pb){av_freep(&f->pb->buffer);avio_context_free(&f->pb);}
}
typedef struct {AVFormatContext *f;AVPacket *packet;int map[TRACKS];int eof;int own;} input_track;
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
    if(avformat_open_input(&f,path,NULL,NULL)<0 || avformat_find_stream_info(f,NULL)<0)goto end;
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
static int prepare(const char *input,const char *output,kr_prepare_progress cb,void *ctx,char *err,int en,
                   kr_prepare_write writer,void *writer_context) {
    generated_reader gens[TRACKS]={0};AVIOContext *readers[TRACKS]={0};
    output_sink sinks[TRACKS+1]={0};
    for(int i=0;i<=TRACKS;i++){sinks[i].write=writer;sinks[i].context=writer_context;sinks[i].track=i;}
    snprintf(sinks[0].suffix,sizeof sinks[0].suffix,".mp4");
    AVFormatContext *original=NULL,*out=NULL,*side[TRACKS]={0};input_track ins[TRACKS]={0};subtitle subs[TRACKS]={0};
    int ninputs=1,r=-1,header=0,mapped=0;char partial[4096],spools[TRACKS][4096]={{0}},sides[TRACKS][4200]={{0}};
    if(err && en>0)*err=0;
    if(!local_input(input) || (!writer && (!output || output[0]!='/' || !strcmp(input,output))))return fail(err,en,"A local or loopback input and a separate local output are required",0);
    snprintf(partial,sizeof partial,"%s.partial",output?output:"stream");
    if(open_source(&original,input)<0){fail(err,en,"Cannot read the source video",0);goto end;}
    int vi=video_index(original);if(vi<0 || original->nb_streams>=TRACKS) {fail(err,en,"Unsupported track layout",0);goto end;}
    sinks[0].duration=(double)original->duration/AV_TIME_BASE;
    if(original->duration<=0){fail(err,en,"Source duration is unknown",0);goto end;}
    if(!copy_video(original->streams[vi]->codecpar)) {
        AVCodecParameters *p=original->streams[vi]->codecpar;
        for(int i=0;i<p->nb_coded_side_data;i++)if(p->coded_side_data[i].type==AV_PKT_DATA_DOVI_CONF) {
            fail(err,en,"This Dolby Vision codec needs RPU remapping; original retained",0);goto end;
        }
    }
    // Never silently discard image subtitles or alternate video tracks during an in-place replacement.
    for(unsigned i=0;i<original->nb_streams;i++) {
        AVCodecParameters *p=original->streams[i]->codecpar;
        if((p->codec_type==AVMEDIA_TYPE_SUBTITLE && !text_sub(p->codec_id) && !sidecar_sub(p)) ||
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
        int generated=((int)i==vi && !copy_video(p)) || (p->codec_type==AVMEDIA_TYPE_AUDIO && p->codec_id!=AV_CODEC_ID_AAC);
        if(generated) {
            int ni=ninputs++;input_track *one=&ins[ni];one->own=1;
            if(writer) {
                if(generated_open(&gens[ni],&one->f,&readers[ni],input,(int)i,(int)i==vi,cb,ctx,err,en)<0)goto end;
                one->f->probesize=2*1024*1024;one->f->max_analyze_duration=AV_TIME_BASE;
                if(avformat_find_stream_info(one->f,NULL)<0){fail(err,en,"Converted track inspection failed",0);goto end;}
            } else {
                snprintf(spools[i],sizeof spools[i],"%s.track%u",output,i);
                int q=spool(input,spools[i],(int)i,(int)i==vi,cb,ctx,err,en);if(q){r=q;goto end;}
                if(avformat_open_input(&one->f,spools[i],NULL,NULL)<0 || avformat_find_stream_info(one->f,NULL)<0)goto end;
            }
            if(one->f->nb_streams!=1)goto end;
            one->map[0]=dst->index;avcodec_parameters_copy(dst->codecpar,one->f->streams[0]->codecpar);
            dst->codecpar->codec_tag=0;dst->time_base=one->f->streams[0]->time_base;
            // Preserve static HDR metadata when another HDR codec is encoded to HEVC Main10.
            if((int)i==vi)for(int m=0;m<p->nb_coded_side_data;m++) {
                AVPacketSideData *from=&p->coded_side_data[m];
                if(from->type!=AV_PKT_DATA_MASTERING_DISPLAY_METADATA && from->type!=AV_PKT_DATA_CONTENT_LIGHT_LEVEL)continue;
                AVPacketSideData *to=av_packet_side_data_new(&dst->codecpar->coded_side_data,&dst->codecpar->nb_coded_side_data,from->type,from->size,0);
                if(!to)goto end;memcpy(to->data,from->data,from->size);
            }
        } else {
            ins[0].map[i]=dst->index;
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
    out->avoid_negative_ts=AVFMT_AVOID_NEG_TS_MAKE_NON_NEGATIVE;
    if((writer?sink_open(out,&sinks[0]):avio_open(&out->pb,partial,AVIO_FLAG_WRITE))<0)goto end;
    AVDictionary *opts=NULL;av_dict_set(&opts,"movflags",writer?"+empty_moov+default_base_moof+frag_keyframe+use_metadata_tags":"+faststart+use_metadata_tags",0);
    if(writer)av_dict_set(&opts,"frag_duration","6000000",0);
    int q=avformat_write_header(out,&opts);av_dict_free(&opts);if(q<0){fail(err,en,"MP4 header",q);goto end;}header=1;
    for(int i=0;i<ninputs;i++){ins[i].packet=av_packet_alloc();if(!ins[i].packet || next(&ins[i])<0)goto end;}
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
            q=av_write_frame(side[si],p);if(q<0){fail(err,en,"Picture subtitle packet",q);goto end;}
            q=next(in);if(q<0){fail(err,en,"Source read",q);goto end;}
            continue;
        }
        AVStream *src=in->f->streams[si],*dst=out->streams[di];
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
                q=av_interleaved_write_frame(out,encoded);av_packet_free(&encoded);
            }
            avsubtitle_free(&sub);
        } else {
            av_packet_rescale_ts(p,src->time_base,dst->time_base);p->stream_index=di;p->pos=-1;
            q=av_interleaved_write_frame(out,p);
        }
        if(q<0){fail(err,en,"MP4 packet",q);goto end;}
        q=next(in);if(q<0){fail(err,en,"Source read",q);goto end;}
    }
    if(!tick(cb,ctx,3,0,1)){r=-2;goto end;}
    q=av_write_trailer(out);header=0;
    if(writer){avio_flush(out->pb);if(out->pb->error<0)q=out->pb->error;}
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
    if(r==-1 && err && en>0 && !*err)fail(err,en,"Preparation failed; original retained",0);
    return r;
}

int kodi_airplay_prepare(const char *input,const char *output,kr_prepare_progress cb,void *ctx,char *err,int en) {
    return prepare(input,output,cb,ctx,err,en,NULL,NULL);
}
// Non-seekable output with a completed fragment index (mfra). The caller must remotely
// validate the completed file before replacing the original; successful generation alone is insufficient.
int kodi_airplay_prepare_to(const char *input,kr_prepare_write write,void *write_context,
                            kr_prepare_progress cb,void *ctx,char *err,int en) {
    if(!write)return fail(err,en,"Output callback is required",0);
    return prepare(input,NULL,cb,ctx,err,en,write,write_context);
}

int kodi_airplay_verify(const char *input,const char *output,char *err,int en) {
    AVFormatContext *original=NULL;int r=-1,mapped=0;
    if(!local_input(input) || !local_input(output))return -1;
    if(open_source(&original,input)<0)goto end;
    int vi=video_index(original);
    for(unsigned i=0;i<original->nb_streams;i++){
        AVCodecParameters *p=original->streams[i]->codecpar;
        if((int)i==vi || p->codec_type==AVMEDIA_TYPE_AUDIO ||
           (p->codec_type==AVMEDIA_TYPE_SUBTITLE && text_sub(p->codec_id)))mapped++;
    }
    r=validate(output,original,mapped,err,en);
end:avformat_close_input(&original);return r;
}
