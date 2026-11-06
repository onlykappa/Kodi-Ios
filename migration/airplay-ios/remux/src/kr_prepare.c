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
#include <sys/stat.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define TRACKS 64
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
static int open_source(AVFormatContext **f,const char *input) {
    AVDictionary *o=NULL;int r;
    if(!strncmp(input,"http://",7)) {
        // Long reads over the phone's loopback to Drive: bounded waits, reconnect at the same offset, Range seeks.
        av_dict_set(&o,"rw_timeout","60000000",0);
        av_dict_set(&o,"reconnect","1",0);
        av_dict_set(&o,"reconnect_on_network_error","1",0);
        av_dict_set(&o,"reconnect_delay_max","30",0);
        av_dict_set(&o,"seekable","1",0);
        av_dict_set(&o,"multiple_requests","1",0);
        av_dict_set(&o,"user_agent","Kodi-iOS-AirPlay/1",0);
    }
    r=avformat_open_input(f,input,NULL,&o);av_dict_free(&o);
    if(r<0)return r;
    return avformat_find_stream_info(*f,NULL);
}
// The setup add-on asks this before streaming a Drive file to preparation instead of downloading it first.
int kodi_airplay_prepare_streams(void) { return 1; }
int kodi_airplay_probe(const char *input,char *json,int size) {
    AVFormatContext *f=NULL;int r=-1;
    if(!local_input(input) || !json || size<2) return -1;
    if(open_source(&f,input)<0) goto end;
    int v=video_index(f);if(v<0) goto end;
    AVCodecParameters *p=f->streams[v]->codecpar;
    double audio_work=0,duration=f->duration>0?(double)f->duration/AV_TIME_BASE:0;
    for(unsigned i=0;i<f->nb_streams;i++) {
        AVCodecParameters *a=f->streams[i]->codecpar;
        if(a->codec_type==AVMEDIA_TYPE_AUDIO && a->codec_id!=AV_CODEC_ID_AAC)
            audio_work+=duration*(a->ch_layout.nb_channels>=6?384000:160000)/8;
    }
    snprintf(json,(size_t)size,"{\"ready\":%s,\"width\":%d,\"height\":%d,\"hdr\":%s,\"duration\":%.6f,\"copy_video\":%s,\"audio_work_bytes\":%.0f}",
             kr_prepare_ready(f) && av_dict_get(f->metadata,"kodi_airplay_prepared",NULL,0)?"true":"false",p->width,p->height,hdr(p)?"true":"false",
             duration,copy_video(p)?"true":"false",audio_work);r=0;
end:avformat_close_input(&f);return r;
}
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
        int64_t t=(int64_t)((double)f->duration*(k==1?.5:.95));
        if(av_seek_frame(f,-1,t,AVSEEK_FLAG_BACKWARD)<0){av_packet_free(&p);goto end;}
        int q=av_read_frame(f,p);av_packet_unref(p);if(q<0){av_packet_free(&p);goto end;}
    }
    av_packet_free(&p);r=0;
end:avformat_close_input(&f);if(r<0)fail(err,en,"Output validation failed; original retained",0);return r;
}
int kodi_airplay_prepare(const char *input,const char *output,kr_prepare_progress cb,void *ctx,char *err,int en) {
    AVFormatContext *original=NULL,*out=NULL;input_track ins[TRACKS]={0};subtitle subs[TRACKS]={0};
    int ninputs=1,r=-1,header=0,mapped=0;char partial[4096],spools[TRACKS][4096]={{0}};
    if(err && en>0)*err=0;
    if(!local_input(input) || !output || output[0]!='/' || !strcmp(input,output))return fail(err,en,"A local or loopback input and a separate local output are required",0);
    snprintf(partial,sizeof partial,"%s.partial",output);
    if(open_source(&original,input)<0){fail(err,en,"Cannot read the source video",0);goto end;}
    int vi=video_index(original);if(vi<0 || original->nb_streams>=TRACKS) {fail(err,en,"Unsupported track layout",0);goto end;}
    if(original->duration<=0){fail(err,en,"Source duration is unknown",0);goto end;}
    if(!copy_video(original->streams[vi]->codecpar) && hdr(original->streams[vi]->codecpar)) {
        fail(err,en,"This HDR codec cannot be prepared without changing HDR; original retained",0);goto end;
    }
    // Never silently discard image subtitles or alternate video tracks during an in-place replacement.
    for(unsigned i=0;i<original->nb_streams;i++) {
        AVCodecParameters *p=original->streams[i]->codecpar;
        if((p->codec_type==AVMEDIA_TYPE_SUBTITLE && !text_sub(p->codec_id)) ||
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
        AVStream *dst=avformat_new_stream(out,NULL);if(!dst)goto end;mapped++;
        av_dict_copy(&dst->metadata,src->metadata,0);dst->disposition=src->disposition;dst->time_base=src->time_base;
        avcodec_parameters_copy(dst->codecpar,p);dst->codecpar->codec_tag=0;
        int generated=((int)i==vi && !copy_video(p)) || (p->codec_type==AVMEDIA_TYPE_AUDIO && p->codec_id!=AV_CODEC_ID_AAC);
        if(generated) {
            snprintf(spools[i],sizeof spools[i],"%s.track%u",output,i);
            int q=spool(input,spools[i],(int)i,(int)i==vi,cb,ctx,err,en);if(q){r=q;goto end;}
            input_track *one=&ins[ninputs++];one->own=1;
            if(avformat_open_input(&one->f,spools[i],NULL,NULL)<0 || avformat_find_stream_info(one->f,NULL)<0)goto end;
            if(one->f->nb_streams!=1)goto end;
            one->map[0]=dst->index;avcodec_parameters_copy(dst->codecpar,one->f->streams[0]->codecpar);
            dst->codecpar->codec_tag=0;dst->time_base=one->f->streams[0]->time_base;
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
    if(avio_open(&out->pb,partial,AVIO_FLAG_WRITE)<0)goto end;
    AVDictionary *opts=NULL;av_dict_set(&opts,"movflags","+faststart+use_metadata_tags",0);
    int q=avformat_write_header(out,&opts);av_dict_free(&opts);if(q<0){fail(err,en,"MP4 header",q);goto end;}header=1;
    for(int i=0;i<ninputs;i++){ins[i].packet=av_packet_alloc();if(!ins[i].packet || next(&ins[i])<0)goto end;}
    unsigned packets=0;
    for(;;) {
        int pick=-1;double earliest=0;
        for(int i=0;i<ninputs;i++)if(!ins[i].eof && (pick<0 || packet_time(&ins[i])<earliest)){pick=i;earliest=packet_time(&ins[i]);}
        if(pick<0)break;
        if((packets++%128)==0 && !tick(cb,ctx,2,earliest,(double)original->duration/AV_TIME_BASE)){r=-2;goto end;}
        input_track *in=&ins[pick];AVPacket *p=in->packet;int si=p->stream_index,di=in->map[si];
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
    if(q<0 || avio_closep(&out->pb)<0){fail(err,en,"MP4 finalization",q);goto end;}
    if(validate(partial,original,mapped,err,en)<0)goto end;
    if(!tick(cb,ctx,3,1,1)){r=-2;goto end;}
    if(rename(partial,output)){fail(err,en,"Cannot commit prepared file",0);goto end;}
    r=0;
end:
    (void)header;
    for(int i=0;i<TRACKS;i++) {
        avcodec_free_context(&subs[i].dec);avcodec_free_context(&subs[i].enc);
        av_packet_free(&ins[i].packet);if(ins[i].own)avformat_close_input(&ins[i].f);
        if(r==0 && spools[i][0]){unlink(spools[i]);char state[4110];snprintf(state,sizeof state,"%s.state",spools[i]);unlink(state);}
    }
    if(out){if(out->pb)avio_closep(&out->pb);avformat_free_context(out);}
    avformat_close_input(&original);if(r)unlink(partial);
    if(r==-1 && err && en>0 && !*err)fail(err,en,"Preparation failed; original retained",0);
    return r;
}
