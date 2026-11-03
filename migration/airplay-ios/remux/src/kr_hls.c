// kr_hls: multivariant + media playlists. Ported from GMPlayer's GMStreamSession.swift masterPlaylist /
// mediaPlaylist (MIT, (c) 2026 Gaston Morixe); the AAC bridge renditions are a Kodi iOS addition.
#include "kr_hls.h"
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>

typedef struct { char *p; size_t len, cap; } sb;

static void sb_add(sb *b, const char *fmt, ...) {
    va_list ap;
    for (;;) {
        size_t room = b->cap - b->len;
        va_start(ap, fmt);
        int n = vsnprintf(b->p ? b->p + b->len : NULL, b->p ? room : 0, fmt, ap);
        va_end(ap);
        if (n < 0) return;
        if (b->p && (size_t)n < room) { b->len += (size_t)n; return; }
        size_t cap = b->cap ? b->cap : 1024;
        while (cap - b->len <= (size_t)n) cap *= 2;
        char *q = realloc(b->p, cap);
        if (!q) return;
        b->p = q; b->cap = cap;
    }
}

int kr_audio_route(const gm_track_info *t) {
    if (!t || t->kind != GM_TRACK_AUDIO) return KR_AUDIO_NONE;
    if (t->avf_compatible) return KR_AUDIO_COPY;
    static const char *bridged[] = { "dts", "truehd", "mlp", "flac", "opus", "vorbis", NULL };
    for (int i = 0; bridged[i]; i++)
        if (!strcmp(t->codec, bridged[i])) return KR_AUDIO_AAC;
    return KR_AUDIO_NONE;
}

const char *kr_audio_token(const gm_track_info *t) {
    if (kr_audio_route(t) == KR_AUDIO_AAC) return "mp4a.40.2";
    if (!strcmp(t->codec, "ac3")) return "ac-3";
    if (!strcmp(t->codec, "eac3")) return "ec-3";
    if (!strcmp(t->codec, "mp3")) return "mp4a.40.34";
    if (!strcmp(t->codec, "alac")) return "alac";
    return "mp4a.40.2";
}

const char *kr_language(const char *c) {
    static const char *map[][2] = {
        {"eng","en"},{"spa","es"},{"fre","fr"},{"fra","fr"},{"ger","de"},{"deu","de"},{"ita","it"},{"jpn","ja"},
        {"por","pt"},{"rus","ru"},{"chi","zh"},{"zho","zh"},{"kor","ko"},{"dut","nl"},{"nld","nl"},{"swe","sv"},
        {"nor","no"},{"dan","da"},{"fin","fi"},{"pol","pl"},{"tur","tr"},{"ara","ar"},{"hin","hi"},{"heb","he"},
        {"gre","el"},{"ell","el"},{"cze","cs"},{"ces","cs"},{"hun","hu"},{"tha","th"},{"vie","vi"},{"ind","id"},
    };
    if (!c || !*c || !strcmp(c, "und") || !strcmp(c, "mis") || !strcmp(c, "zxx")) return "";
    for (size_t i = 0; i < sizeof map / sizeof *map; i++) if (!strcmp(c, map[i][0])) return map[i][1];
    return c;
}

// From the hvcC / avcC configuration record when present (what Apple checks), else the stream's profile and level.
void kr_hls_video_codec(gm_stream *s, char *out, int len) {
    snprintf(out, (size_t)len, "avc1.640028");
    AVFormatContext *f = gm_stream_format_context(s);
    int v = gm_stream_selected_video(s);
    if (!f || v < 0) return;
    AVCodecParameters *p = f->streams[v]->codecpar;
    const uint8_t *x = p->extradata;
    if (p->codec_id == AV_CODEC_ID_HEVC) {
        // ISO/IEC 14496-15 E.3: hvc1.[A-C]<profile>.<compat, bit-reversed hex>.<L|H><level>.<constraint bytes>, the
        // six constraint bytes in hex, trailing zero bytes left out. r6: taken from the hvcC (was always "B0": x265
        // writes 0x90, and a receiver that checks the string against the stream could refuse the video).
        int prof = p->profile > 0 ? p->profile : 1, level = p->level > 0 ? p->level : 120, tier = 0, space = 0;
        unsigned compat = 0;
        char cons[24] = ".B0";
        if (x && p->extradata_size >= 23 && x[0] == 1) {
            space = x[1] >> 6; tier = (x[1] >> 5) & 1; prof = x[1] & 0x1f;
            compat = (unsigned)x[2] << 24 | (unsigned)x[3] << 16 | (unsigned)x[4] << 8 | x[5];
            level = x[12];
            int last = -1;
            for (int i = 0; i < 6; i++) if (x[6 + i]) last = i;
            cons[0] = 0;
            for (int i = 0; i <= last; i++) snprintf(cons + strlen(cons), sizeof cons - strlen(cons), ".%X", x[6 + i]);
        }
        unsigned rev = 0;  // compatibility flags, bit-reversed, as hex (ISO/IEC 14496-15 E.3)
        for (int i = 0; i < 32; i++) if (compat & (1u << i)) rev |= 1u << (31 - i);
        if (!rev) rev = prof == 2 ? 4 : 6;
        const char *sp = space == 1 ? "A" : space == 2 ? "B" : space == 3 ? "C" : "";
        snprintf(out, (size_t)len, "hvc1.%s%d.%X.%c%d%s", sp, prof, rev, tier ? 'H' : 'L', level, cons);
    } else if (p->codec_id == AV_CODEC_ID_H264) {
        if (x && p->extradata_size >= 4 && x[0] == 1) snprintf(out, (size_t)len, "avc1.%02X%02X%02X", x[1], x[2], x[3]);
        else snprintf(out, (size_t)len, "avc1.%02X00%02X", p->profile > 0 ? p->profile & 0xff : 100, p->level > 0 ? p->level : 40);
    }
}

// Names inside a group must be unique: "Surround 5.1", "Surround 5.1 #2"...
static void rendition_name(const gm_track_info *t, int n, char *out, size_t len) {
    const char *lang = kr_language(t->language);
    char base[128];
    if (t->title[0]) snprintf(base, sizeof base, "%s", t->title);
    else if (*lang) snprintf(base, sizeof base, "%s", t->language);
    else if (t->kind == GM_TRACK_AUDIO) snprintf(base, sizeof base, "Audio %d", n);
    else snprintf(base, sizeof base, "Subtitles %d", n);
    for (char *c = base; *c; c++) if (*c == '"' || *c == '\n' || *c == '\r') *c = '\'';
    snprintf(out, len, "%s", base);
}

static int name_taken(char names[][160], int count, const char *name) {
    for (int i = 0; i < count; i++) if (!strcmp(names[i], name)) return 1;
    return 0;
}

char *kr_hls_master(gm_stream *s, const char *base) {
    sb b = {0};
    sb_add(&b, "#EXTM3U\n#EXT-X-VERSION:7\n#EXT-X-INDEPENDENT-SEGMENTS\n");
    int n = gm_stream_track_count(s), sel = gm_stream_selected_audio(s), nau = 0, nsub = 0, deflt = -1;
    char tokens[64] = "";
    static char names[64][160];
    gm_track_info t;
    for (int i = 0; i < n; i++)  // the default: the engine's choice, else the first track that can be served
        if (gm_stream_track_info(s, i, &t) == 0 && kr_audio_route(&t) && (deflt < 0 || t.src_index == sel)) deflt = t.src_index;
    for (int i = 0; i < n && nau < 64; i++) {
        if (gm_stream_track_info(s, i, &t) != 0 || !kr_audio_route(&t)) continue;
        const char *tok = kr_audio_token(&t);
        if (!strstr(tokens, tok)) { if (*tokens) strcat(tokens, ","); strncat(tokens, tok, sizeof tokens - strlen(tokens) - 1); }
        char name[160]; rendition_name(&t, nau + 1, name, sizeof name);
        if (kr_audio_route(&t) == KR_AUDIO_AAC) { char tmp[160]; snprintf(tmp, sizeof tmp, "%.120s (AAC)", name); strcpy(name, tmp); }
        for (int k = 2; name_taken(names, nau, name); k++) {
            char tmp[160]; rendition_name(&t, nau + 1, tmp, sizeof tmp);
            snprintf(name, sizeof name, "%.140s #%d", tmp, k);
        }
        strcpy(names[nau++], name);
        sb_add(&b, "#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID=\"aud\",NAME=\"%s\"", name);
        if (*kr_language(t.language)) sb_add(&b, ",LANGUAGE=\"%s\"", kr_language(t.language));
        // CHANNELS left out on purpose (GMPlayer: container counts can disagree with the stream; AVPlayer rejects).
        sb_add(&b, ",DEFAULT=%s,AUTOSELECT=YES,URI=\"%s/audio/%d/index.m3u8\"\n", t.src_index == deflt ? "YES" : "NO", base, t.src_index);
    }
    for (int i = 0; i < n && nsub < 64; i++) {
        if (gm_stream_track_info(s, i, &t) != 0 || t.kind != GM_TRACK_SUBTITLE || !t.is_text_sub) continue;
        char name[160]; rendition_name(&t, nsub + 1, name, sizeof name);
        for (int k = 2; name_taken(names + nau, nsub, name); k++) {
            char tmp[160]; rendition_name(&t, nsub + 1, tmp, sizeof tmp);
            snprintf(name, sizeof name, "%.140s #%d", tmp, k);
        }
        strcpy(names[nau + nsub++], name);
        sb_add(&b, "#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID=\"subs\",NAME=\"%s\"", name);
        if (*kr_language(t.language)) sb_add(&b, ",LANGUAGE=\"%s\"", kr_language(t.language));
        sb_add(&b, ",DEFAULT=NO,AUTOSELECT=NO,FORCED=NO,URI=\"%s/subs/%d/index.m3u8\"\n", base, t.src_index);
    }
    char vcodec[64]; kr_hls_video_codec(s, vcodec, sizeof vcodec);
    AVFormatContext *f = gm_stream_format_context(s);
    double dur = gm_stream_duration(s);
    int64_t size = (f && f->pb) ? avio_size(f->pb) : -1;
    double avg = (size > 0 && dur > 0) ? (double)size * 8.0 / dur : 30e6;
    long bw = (long)fmax(8e6, avg * 2.5);  // over-declared: remux peaks run 1.5-2x the average
    sb_add(&b, "#EXT-X-STREAM-INF:BANDWIDTH=%ld,CODECS=\"%s%s%s\"", bw, vcodec, *tokens ? "," : "", tokens);
    int v = gm_stream_selected_video(s);
    for (int i = 0; i < n; i++) {
        if (gm_stream_track_info(s, i, &t) != 0 || t.src_index != v) continue;
        if (t.width > 0 && t.height > 0) sb_add(&b, ",RESOLUTION=%dx%d", t.width, t.height);
        if (t.fps_num > 0 && t.fps_den > 0) sb_add(&b, ",FRAME-RATE=%.3f", (double)t.fps_num / t.fps_den);
    }
    gm_color_info c;
    const char *range = "SDR";
    if (gm_stream_color_info(s, &c) == 0 && gm_stream_is_hdr(s)) range = c.transfer == 18 ? "HLG" : "PQ";
    sb_add(&b, ",VIDEO-RANGE=%s", range);
    if (nau) sb_add(&b, ",AUDIO=\"aud\"");
    if (nsub) sb_add(&b, ",SUBTITLES=\"subs\"");
    sb_add(&b, "\n%s/video/index.m3u8\n", base);
    return b.p;
}

char *kr_hls_media(gm_stream *s, const char *prefix, const char *seg_ext, int with_map) {
    sb b = {0};
    int n = gm_stream_segment_count(s);
    double maxd = 0;
    for (int i = 0; i < n; i++) maxd = fmax(maxd, gm_stream_segment_duration(s, i));
    sb_add(&b, "#EXTM3U\n#EXT-X-VERSION:7\n#EXT-X-TARGETDURATION:%d\n", (int)ceil(maxd));
    sb_add(&b, "#EXT-X-MEDIA-SEQUENCE:0\n#EXT-X-PLAYLIST-TYPE:VOD\n#EXT-X-INDEPENDENT-SEGMENTS\n");
    if (with_map) sb_add(&b, "#EXT-X-MAP:URI=\"%s/init.mp4\"\n", prefix);
    for (int i = 0; i < n; i++) sb_add(&b, "#EXTINF:%.5f,\n%s/seg%d.%s\n", gm_stream_segment_duration(s, i), prefix, i, seg_ext);
    sb_add(&b, "#EXT-X-ENDLIST\n");
    return b.p;
}
