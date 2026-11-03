// kr_subs: libass track + renderer per session, blended onto the converted frames (see kr_subs.h).
#include "kr_subs.h"
#include <ctype.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <ass/ass.h>

struct kr_subs {
    ASS_Library *lib;
    ASS_Renderer *r;
    ASS_Track *track;
    AVCodecContext *dec;
    AVRational tb;
    int w, h;
    int order;               // our own ReadOrder: FFmpeg's restarts after a flush, libass would drop those as duplicates
    uint64_t *seen; int nseen, capseen;  // (start, body) hashes already added
};

static const char *font_file;
void kr_subs_set_font_file(const char *path) { font_file = path && *path ? path : NULL; }

// The style SRT / WebVTT events get (FFmpeg's default ASS header, as its subrip decoder makes for embedded SRT).
static const char HEADER[] =
    "[Script Info]\nScriptType: v4.00+\nPlayResX: 384\nPlayResY: 288\nScaledBorderAndShadow: yes\n\n"
    "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
    "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
    "MarginR, MarginV, Encoding\n"
    "Style: Default,Arial,16,&Hffffff,&Hffffff,&H0,&H0,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,0\n\n"
    "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n";

int kr_subs_is_text(const AVStream *st) {
    if (!st || st->codecpar->codec_type != AVMEDIA_TYPE_SUBTITLE) return 0;
    switch (st->codecpar->codec_id) {
    case AV_CODEC_ID_SUBRIP: case AV_CODEC_ID_SRT: case AV_CODEC_ID_ASS: case AV_CODEC_ID_SSA:
    case AV_CODEC_ID_MOV_TEXT: case AV_CODEC_ID_WEBVTT: case AV_CODEC_ID_TEXT:
        return avcodec_find_decoder(st->codecpar->codec_id) != NULL;
    default: return 0;
    }
}

int kr_subs_stream_count(AVFormatContext *f) {
    int n = 0;
    for (unsigned i = 0; f && i < f->nb_streams; i++) n += f->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_SUBTITLE;
    return n;
}

static int lang_match(const AVStream *st, const char *lang) {
    const AVDictionaryEntry *e = av_dict_get(st->metadata, "language", NULL, 0);
    if (!e || !lang || !*lang) return 0;
    size_t n = strlen(lang);
    return !strcasecmp(e->value, lang) || (n == 2 && !strncasecmp(e->value, lang, 2));
}

int kr_subs_pick(AVFormatContext *f, int ordinal, const char *lang) {
    if (!f || ordinal == -1) return -1;
    if (ordinal >= 0) {
        int k = 0;
        for (unsigned i = 0; i < f->nb_streams; i++) {
            if (f->streams[i]->codecpar->codec_type != AVMEDIA_TYPE_SUBTITLE) continue;
            if (k++ == ordinal) return kr_subs_is_text(f->streams[i]) ? (int)i : -1;
        }
        return -1;
    }
    static const int want[2] = { AV_DISPOSITION_FORCED, AV_DISPOSITION_DEFAULT };
    for (int w = 0; w < 2; w++)
        for (unsigned i = 0; i < f->nb_streams; i++)
            if (kr_subs_is_text(f->streams[i]) && (f->streams[i]->disposition & want[w])) return (int)i;
    for (unsigned i = 0; i < f->nb_streams; i++)
        if (kr_subs_is_text(f->streams[i]) && lang_match(f->streams[i], lang)) return (int)i;
    return -1;
}

// libass talks a lot (font selection on every renderer): errors only.
static void ass_log(int level, const char *fmt, va_list va, void *data) {
    (void)data;
    if (level > 1) return;
    fprintf(stderr, "[libass] "); vfprintf(stderr, fmt, va); fprintf(stderr, "\n");
}

kr_subs *kr_subs_create(int w, int h) {
    kr_subs *s = calloc(1, sizeof *s);
    if (!s) return NULL;
    s->w = w; s->h = h;
    s->lib = ass_library_init();
    if (s->lib) ass_set_message_cb(s->lib, ass_log, NULL);
    s->r = s->lib ? ass_renderer_init(s->lib) : NULL;
    if (!s->r) { kr_subs_free(s); return NULL; }
    ass_set_extract_fonts(s->lib, 1);  // fonts attached to an .ass file
    ass_set_frame_size(s->r, w, h);
    ass_set_storage_size(s->r, w, h);
    // iOS: CoreText finds Arial / Helvetica (system fonts, not shipped); host: the given file is the fallback.
    ass_set_fonts(s->r, font_file, "Helvetica", ASS_FONTPROVIDER_AUTODETECT, NULL, 1);
    return s;
}

void kr_subs_free(kr_subs *s) {
    if (!s) return;
    avcodec_free_context(&s->dec);
    if (s->track) ass_free_track(s->track);
    if (s->r) ass_renderer_done(s->r);
    if (s->lib) ass_library_done(s->lib);
    free(s->seen);
    free(s);
}

int kr_subs_events(const kr_subs *s) { return s && s->track ? s->track->n_events : 0; }

static uint64_t hash(const char *p, int64_t start) {
    uint64_t h = 1469598103934665603ull ^ (uint64_t)start;
    for (; *p; p++) h = (h ^ (unsigned char)*p) * 1099511628211ull;
    return h;
}

void kr_subs_add(kr_subs *s, const char *body, int64_t start_ms, int64_t dur_ms) {
    if (!s || !s->track || !body) return;
    uint64_t h = hash(body, start_ms);
    for (int i = 0; i < s->nseen; i++) if (s->seen[i] == h) return;
    if (s->nseen == s->capseen) {
        int cap = s->capseen ? s->capseen * 2 : 256;
        uint64_t *n = realloc(s->seen, (size_t)cap * sizeof *n);
        if (!n) return;
        s->seen = n; s->capseen = cap;
    }
    s->seen[s->nseen++] = h;
    size_t len = strlen(body) + 24;
    char *line = malloc(len);
    if (!line) return;
    int n = snprintf(line, len, "%d,%s", s->order++, body);
    ass_process_chunk(s->track, line, n, start_ms, dur_ms > 0 ? dur_ms : 5000);
    free(line);
}

int kr_subs_open_stream(kr_subs *s, AVStream *st) {
    if (!s || !kr_subs_is_text(st)) return -1;
    const AVCodec *c = avcodec_find_decoder(st->codecpar->codec_id);
    s->dec = avcodec_alloc_context3(c);
    if (!s->dec || avcodec_parameters_to_context(s->dec, st->codecpar) < 0) return -1;
    s->dec->pkt_timebase = st->time_base;
    if (avcodec_open2(s->dec, c, NULL) < 0) return -1;
    s->tb = st->time_base;
    s->track = ass_new_track(s->lib);
    if (!s->track) return -1;
    const char *hdr = s->dec->subtitle_header && s->dec->subtitle_header_size ? (const char *)s->dec->subtitle_header : HEADER;
    int hlen = hdr == HEADER ? (int)strlen(HEADER) : s->dec->subtitle_header_size;
    ass_process_codec_private(s->track, (char *)hdr, hlen);
    return 0;
}

void kr_subs_feed(kr_subs *s, AVPacket *pkt) {
    if (!s || !s->dec || !pkt || pkt->pts == AV_NOPTS_VALUE) return;
    AVSubtitle sub;
    int got = 0;
    if (avcodec_decode_subtitle2(s->dec, &sub, &got, pkt) < 0 || !got) return;
    int64_t start = av_rescale_q(pkt->pts, s->tb, (AVRational){ 1, 1000 }) + sub.start_display_time;
    int64_t dur = pkt->duration > 0 ? av_rescale_q(pkt->duration, s->tb, (AVRational){ 1, 1000 })
                : sub.end_display_time > sub.start_display_time && sub.end_display_time != UINT32_MAX
                ? (int64_t)sub.end_display_time - sub.start_display_time : 5000;
    for (unsigned i = 0; i < sub.num_rects; i++) {
        const char *a = sub.rects[i]->ass;
        if (!a) continue;
        const char *body = strchr(a, ',');  // drop FFmpeg's ReadOrder
        if (body) kr_subs_add(s, body + 1, start, dur);
    }
    avsubtitle_free(&sub);
}

// ── external files ─────────────────────────────────────────────────────────────
static int valid_utf8(const unsigned char *p, size_t n) {
    for (size_t i = 0; i < n;) {
        unsigned c = p[i];
        int k = c < 0x80 ? 0 : (c & 0xE0) == 0xC0 ? 1 : (c & 0xF0) == 0xE0 ? 2 : (c & 0xF8) == 0xF0 ? 3 : -1;
        if (k < 0 || i + (size_t)k >= n + (k == 0)) return k == 0;
        for (int j = 1; j <= k; j++) if ((p[i + j] & 0xC0) != 0x80) return 0;
        i += (size_t)k + 1;
    }
    return 1;
}

static char *read_all(const char *path, size_t *len) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    char *b = NULL; size_t n = 0, cap = 0, r;
    do {
        if (n + 65536 + 1 > cap) { cap = (n + 65536) * 2; char *t = realloc(b, cap); if (!t) { free(b); fclose(f); return NULL; } b = t; }
        r = fread(b + n, 1, 65536, f); n += r;
    } while (r > 0 && n < (64u << 20));
    fclose(f);
    if (!b) return NULL;
    b[n] = 0;
    if (!valid_utf8((unsigned char *)b, n)) {  // Latin-1 (Windows-1252 for the common range) to UTF-8
        char *u = malloc(n * 2 + 1); size_t m = 0;
        if (!u) { free(b); return NULL; }
        for (size_t i = 0; i < n; i++) {
            unsigned char c = (unsigned char)b[i];
            if (c < 0x80) u[m++] = (char)c; else { u[m++] = (char)(0xC0 | c >> 6); u[m++] = (char)(0x80 | (c & 0x3F)); }
        }
        u[m] = 0; free(b); b = u; n = m;
    }
    *len = n;
    return b;
}

// "HH:MM:SS,mmm", "MM:SS.mmm" (WebVTT) -> ms; -1 when not a timestamp.
static int64_t parse_ts(const char *p, const char **end) {
    int64_t f[3] = {0}; int nf = 0;
    while (*p == ' ' || *p == '\t') p++;
    for (;;) {
        if (!isdigit((unsigned char)*p) || nf == 3) return -1;
        int64_t v = 0; while (isdigit((unsigned char)*p)) v = v * 10 + (*p++ - '0');
        f[nf++] = v;
        if (*p == ':') { p++; continue; }
        break;
    }
    if (nf < 2 || (*p != ',' && *p != '.')) return -1;
    p++;
    int64_t ms = 0; int d = 0;
    while (isdigit((unsigned char)*p)) { if (d < 3) { ms = ms * 10 + (*p - '0'); d++; } p++; }
    while (d++ < 3) ms *= 10;
    *end = p;
    int64_t h = nf == 3 ? f[0] : 0, m = f[nf - 2], s = f[nf - 1];
    return ((h * 60 + m) * 60 + s) * 1000 + ms;
}

// SRT / WebVTT cue text to an ASS body: line breaks as \N, <i>/<b>/<u> as overrides, other tags dropped.
static void add_cue(kr_subs *s, const char *text, size_t n, int64_t a, int64_t b) {
    char *o = malloc(n * 4 + 64);
    if (!o) return;
    size_t m = (size_t)sprintf(o, "0,Default,,0,0,0,,");
    while (n && (text[n - 1] == '\n' || text[n - 1] == ' ')) n--;
    for (size_t i = 0; i < n; i++) {
        char c = text[i];
        if (c == '\n') { memcpy(o + m, "\\N", 2); m += 2; continue; }
        if (c == '<') {
            const char *e = memchr(text + i, '>', n - i);
            if (e) {
                const char *t = text + i + 1; int close = *t == '/'; t += close;
                char k = (char)tolower((unsigned char)*t);
                if ((k == 'i' || k == 'b' || k == 'u') && (t + 1 == e)) m += (size_t)sprintf(o + m, "{\\%c%d}", k, !close);
                i = (size_t)(e - text);
                continue;
            }
        }
        o[m++] = c;
    }
    o[m] = 0;
    if (b > a) kr_subs_add(s, o, a, b - a);
    free(o);
}

static int load_srt(kr_subs *s, char *b) {
    s->track = ass_new_track(s->lib);
    if (!s->track) return -1;
    ass_process_codec_private(s->track, (char *)HEADER, (int)strlen(HEADER));
    char *w = b;  // CRLF -> LF
    for (char *r = b; *r; r++) if (*r != '\r') *w++ = *r;
    *w = 0;
    char *p = b;
    if (!strncmp(p, "\xEF\xBB\xBF", 3)) p += 3;
    while (*p) {
        char *eol = strchr(p, '\n'); if (!eol) eol = p + strlen(p);
        char *arrow = strstr(p, "-->");
        if (arrow && arrow < eol) {
            const char *e1, *e2;
            int64_t a = parse_ts(p, &e1), z = parse_ts(arrow + 3, &e2);
            char *t = *eol ? eol + 1 : eol, *q = t;
            while (*q) {  // text: until a blank line
                char *le = strchr(q, '\n');
                if (!le) { q += strlen(q); break; }
                if (le == q) break;
                q = le + 1;
            }
            if (a >= 0 && z >= 0) add_cue(s, t, (size_t)(q - t), a, z);
            p = *q ? q + (*q == '\n') : q;
            continue;
        }
        p = *eol ? eol + 1 : eol;
    }
    return s->track->n_events > 0 ? 0 : -1;
}

int kr_subs_load_file(kr_subs *s, const char *path) {
    if (!s || !path || s->track) return -1;
    size_t n = 0;
    char *b = read_all(path, &n);
    if (!b) return -1;
    const char *dot = strrchr(path, '.');
    int r;
    if (dot && (!strcasecmp(dot, ".ass") || !strcasecmp(dot, ".ssa"))) {
        s->track = ass_read_memory(s->lib, b, n, NULL);
        r = s->track && s->track->n_events > 0 ? 0 : -1;
    } else r = load_srt(s, b);
    free(b);
    return r;
}

// ── blending ───────────────────────────────────────────────────────────────────
static inline uint8_t mix(uint8_t d, int c, int a) { return (uint8_t)(d + (c - d) * a / 255); }

int kr_subs_blend(kr_subs *s, int64_t t_ms, uint8_t *const data[3], const int linesize[3], int w, int h, int nv12) {
    if (!s || !s->track || !s->track->n_events) return 0;
    int changed = 0;
    ASS_Image *img = ass_render_frame(s->r, s->track, t_ms, &changed);
    int drawn = 0;
    for (; img; img = img->next) {
        int op = 255 - (int)(img->color & 0xFF);
        if (op <= 0 || img->w <= 0 || img->h <= 0) continue;
        int R = img->color >> 24, G = (img->color >> 16) & 0xFF, B = (img->color >> 8) & 0xFF;
        // BT.709 limited range
        int Y = 16 + (int)((0.2126 * R + 0.7152 * G + 0.0722 * B) * 219 / 255 + 0.5);
        int U = 128 + (int)((-0.1146 * R - 0.3854 * G + 0.5 * B) * 224 / 255 + (B >= R ? 0.5 : -0.5));
        int V = 128 + (int)((0.5 * R - 0.4542 * G - 0.0458 * B) * 224 / 255 + (R >= B ? 0.5 : -0.5));
        int x0 = img->dst_x, y0 = img->dst_y, x1 = x0 + img->w, y1 = y0 + img->h;
        x0 = x0 < 0 ? 0 : x0; y0 = y0 < 0 ? 0 : y0; x1 = x1 > w ? w : x1; y1 = y1 > h ? h : y1;
        if (x0 >= x1 || y0 >= y1) continue;
        drawn = 1;
        for (int y = y0; y < y1; y++) {
            const uint8_t *bm = img->bitmap + (size_t)(y - img->dst_y) * img->stride - img->dst_x;
            uint8_t *row = data[0] + (size_t)y * linesize[0];
            for (int x = x0; x < x1; x++) if (bm[x]) row[x] = mix(row[x], Y, bm[x] * op / 255);
        }
        // Chroma: one sample per 2x2 block, the mean coverage of its pixels.
        for (int cy = y0 / 2; cy <= (y1 - 1) / 2; cy++) {
            for (int cx = x0 / 2; cx <= (x1 - 1) / 2; cx++) {
                int sum = 0;
                for (int dy = 0; dy < 2; dy++) for (int dx = 0; dx < 2; dx++) {
                    int x = cx * 2 + dx, y = cy * 2 + dy;
                    if (x >= x0 && x < x1 && y >= y0 && y < y1) sum += img->bitmap[(size_t)(y - img->dst_y) * img->stride + (x - img->dst_x)];
                }
                int a = sum / 4 * op / 255;
                if (!a) continue;
                if (nv12) {
                    uint8_t *c = data[1] + (size_t)cy * linesize[1] + cx * 2;
                    c[0] = mix(c[0], U, a); c[1] = mix(c[1], V, a);
                } else {
                    uint8_t *u = data[1] + (size_t)cy * linesize[1] + cx, *v = data[2] + (size_t)cy * linesize[2] + cx;
                    *u = mix(*u, U, a); *v = mix(*v, V, a);
                }
            }
        }
    }
    return drawn;
}
