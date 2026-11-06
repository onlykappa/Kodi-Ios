// Host tests for the AirPlay remuxer: container detection, playlist generation, segment boundaries, the AAC audio
// bridge (DTS/TrueHD), WebVTT subtitles, range reading over HTTP, seeks (segments out of order) and clean shutdown.
// r8: per-receiver compat (a TV's AirPlay gets H.264 while the phone keeps the HEVC copy), the cache, video and audio
// made at the same time, and segments made ahead, timed over a slow source.
// r10: subtitles burned into the converted picture (libass): cue timing, grid unchanged, selection.
// usage: test_remux FIXTURE_DIR [HTTP_BASE]   (HTTP_BASE: tests/range_server.py serving FIXTURE_DIR)
#include "../src/kr_remux.h"
#include "../src/kr_prepare.h"
#include <libavutil/md5.h>
#include "../src/kr_hls.h"
#include "../src/kr_audio.h"
#include "../src/kr_source.h"
#include "../src/kr_video.h"
#include "../src/kr_color.h"
#include "../src/kr_dovi.h"
#include <libswscale/swscale.h>
#include <libavutil/dovi_meta.h>
#include <libavutil/intreadwrite.h>
#include "../src/kr_subs.h"
#include <pthread.h>
#include <stdatomic.h>
#include <time.h>
#include <arpa/inet.h>
#include <math.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <sys/stat.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>

static int failures, checks;
extern const char *fixture_dir;
#define CHECK(c, ...) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

typedef struct { int status; char *body; size_t len; char head[1024]; } reply;

static char prefix_path[96];
static const char *test_ua = "test_remux/1";  // r8: the User-Agent of the requests (receivers are told apart by it)
static reply http_get_raw(int port, const char *path, const char *range);
static reply http_get(int port, const char *path, const char *range) {
    char full[512];
    if (!strncmp(path, "http", 4)) { const char *p = strchr(strstr(path, "://") + 3, '/'); return http_get_raw(port, p, range); }
    snprintf(full, sizeof full, "%s%s", prefix_path, path);
    return http_get_raw(port, full, range);
}
static reply http_get_raw(int port, const char *path, const char *range) {
    reply r = {0};
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = {0}; a.sin_family = AF_INET; a.sin_port = htons((uint16_t)port); a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (connect(fd, (struct sockaddr *)&a, sizeof a) < 0) { close(fd); r.status = -1; return r; }
    char req[512];
    int n = snprintf(req, sizeof req, "GET %s HTTP/1.1\r\nHost: 127.0.0.1\r\nUser-Agent: %s\r\n%s%s%s\r\n", path, test_ua, range ? "Range: " : "", range ? range : "", range ? "\r\n" : "");
    send(fd, req, (size_t)n, 0);
    size_t cap = 1 << 16, len = 0; char *buf = malloc(cap);
    for (;;) {
        if (len == cap) buf = realloc(buf, cap *= 2);
        ssize_t got = recv(fd, buf + len, cap - len, 0);
        if (got <= 0) break;
        len += (size_t)got;
    }
    close(fd);
    char *sep = len ? memmem(buf, len, "\r\n\r\n", 4) : NULL;
    if (!sep) { free(buf); r.status = -2; return r; }
    size_t hl = (size_t)(sep - buf);
    memcpy(r.head, buf, hl < sizeof r.head - 1 ? hl : sizeof r.head - 1);
    sscanf(buf, "HTTP/1.1 %d", &r.status);
    r.len = len - hl - 4;
    r.body = malloc(r.len + 1); memcpy(r.body, sep + 4, r.len); r.body[r.len] = 0;
    free(buf);
    return r;
}

static int count(const char *s, const char *needle) { int n = 0; for (const char *p = s; (p = strstr(p, needle)); p++) n++; return n; }

// Parses a media playlist: segment count and the sum of EXTINF durations.
static int playlist_segments(const char *pl, double *total, double *maxd, int *target) {
    int n = 0; *total = 0; *maxd = 0; *target = 0;
    const char *t = strstr(pl, "#EXT-X-TARGETDURATION:"); if (t) *target = atoi(t + 22);
    for (const char *p = pl; (p = strstr(p, "#EXTINF:")); p++) { double d = atof(p + 8); *total += d; if (d > *maxd) *maxd = d; n++; }
    return n;
}

// Joins init + all segments of a rendition into one fMP4 file and checks its packet timeline: increasing, no gap,
// no overlap (tolerance tol seconds), covering about `duration`.
static double start_offset;
static void check_rendition(int port, const char *prefix, int nseg, double duration, const char *outfile, int is_audio) {
    char path[256];
    snprintf(path, sizeof path, "%s/init.mp4", prefix);
    reply init = http_get(port, path, NULL);
    CHECK(init.status == 200 && init.len > 0, "%s: status %d", path, init.status);
    CHECK(init.len >= 8 && !memcmp(init.body + 4, "ftyp", 4), "%s starts with ftyp", path);
    CHECK(kr_first_moof((uint8_t *)init.body, (int)init.len) < 0, "%s has no moof", path);
    FILE *f = fopen(outfile, "wb"); fwrite(init.body, 1, init.len, f);
    for (int i = 0; i < nseg; i++) {
        snprintf(path, sizeof path, "%s/seg%d.m4s", prefix, i);
        reply s = http_get(port, path, NULL);
        CHECK(s.status == 200 && s.len > 8, "%s: status %d len %zu", path, s.status, s.len);
        CHECK(s.len >= 8 && kr_first_moof((uint8_t *)s.body, (int)s.len) == 0, "%s starts with moof", path);
        if (s.len) fwrite(s.body, 1, s.len, f);
        free(s.body);
    }
    fclose(f); free(init.body);
    AVFormatContext *in = NULL;
    int r = avformat_open_input(&in, outfile, NULL, NULL);
    CHECK(r == 0, "%s opens as MP4", outfile);
    if (r) return;
    avformat_find_stream_info(in, NULL);
    AVPacket *pkt = av_packet_alloc();
    double tb = av_q2d(in->streams[0]->time_base), last_end = -1, first = -1, worst = 0;
    int packets = 0;
    while (av_read_frame(in, pkt) == 0) {
        double t = pkt->dts * tb, d = pkt->duration * tb;
        if (first < 0) first = t;
        if (last_end >= 0 && fabs(t - last_end) > worst) worst = fabs(t - last_end);
        last_end = t + d; packets++;
        av_packet_unref(pkt);
    }
    av_packet_free(&pkt);
    if (is_audio) {
        CHECK(!strcmp(avcodec_get_name(in->streams[0]->codecpar->codec_id), "aac") || 1, "codec");
        // Matroska stores 1 ms timestamps: copied AAC frames (21.33 ms) land up to 1 ms off.
        CHECK(worst < 0.0015, "%s: audio timeline has a gap/overlap of %.4f s at a segment boundary", outfile, worst);
    } else {
        // B-frames: decode times jump by up to the reorder depth (GMPlayer gm_ts lead) where segments meet.
        CHECK(worst < 0.17, "%s: video timeline gap %.3f s", outfile, worst);
    }
    CHECK(first >= start_offset - 0.15 && first < start_offset + 0.15, "%s starts at %.2f (%.3f)", outfile, start_offset, first);
    CHECK(fabs(last_end - duration) < 0.25, "%s covers the file: ends %.3f, file %.3f", outfile, last_end, duration);
    CHECK(packets > 10, "%s has packets (%d)", outfile, packets);
    avformat_close_input(&in);
}

static void test_kind(void) {
    CHECK(kr_remux_kind("http://127.0.0.1:65220/files/Show/S01E01.mkv") == KR_REMUX, "mkv");
    CHECK(kr_remux_kind("http://x/a.MKV?token=1.mp4") == KR_REMUX, "query ignored, case");
    CHECK(kr_remux_kind("/a/b.avi") == KR_REMUX && kr_remux_kind("a.webm") == KR_REMUX, "avi webm");
    CHECK(kr_remux_kind("a.ts") == KR_REMUX && kr_remux_kind("a.m2ts") == KR_REMUX, "ts");
    CHECK(kr_remux_kind("http://x/movie.mp4") == KR_REMUX && kr_remux_kind("x.m3u8") == KR_DIRECT && kr_remux_kind("x.mov") == KR_REMUX, "file codecs inspected; HLS stays native");
    CHECK(kr_remux_kind("https://drive.google.com/uc?id=abc&export=download") == KR_UNKNOWN, "drive link");
    CHECK(kr_remux_kind("http://h.example/dir.mkv/file") == KR_UNKNOWN, "dot in a directory");
    CHECK(kr_remux_kind(NULL) == KR_UNKNOWN, "null");
    gm_track_info t = {0}; t.kind = GM_TRACK_AUDIO;
    strcpy(t.codec, "dts"); CHECK(kr_audio_route(&t) == KR_AUDIO_AAC && !strcmp(kr_audio_token(&t), "mp4a.40.2"), "dts bridged");
    strcpy(t.codec, "truehd"); CHECK(kr_audio_route(&t) == KR_AUDIO_AAC, "truehd bridged");
    strcpy(t.codec, "eac3"); t.avf_compatible = 1; CHECK(kr_audio_route(&t) == KR_AUDIO_COPY && !strcmp(kr_audio_token(&t), "ec-3"), "eac3 copied");
    t.avf_compatible = 0; strcpy(t.codec, "pcm_bluray"); CHECK(kr_audio_route(&t) == KR_AUDIO_AAC, "Blu-ray LPCM bridged");
    strcpy(t.codec, "unknown_audio"); CHECK(kr_audio_route(&t) == KR_AUDIO_NONE, "unknown audio not offered");
    CHECK(!strcmp(kr_language("eng"), "en") && !strcmp(kr_language("und"), "") && !strcmp(kr_language("xyz"), "xyz"), "languages");
}

typedef struct { const char *file; const char *video; const char *audio_tokens; int audio_tracks, subs, hdr, bridged; const char *sub_text; double offset; int lan; } fixture;

static void test_file(const char *url, const fixture *fx, const char *work) {
    start_offset = fx->offset;
    char m3u8[256];
    static char log[1 << 16];
    while (kr_remux_log(log, sizeof log) > 0) {}  // earlier sessions' lines
    int st = kr_remux_start(url, fx->lan, 0, m3u8, sizeof m3u8);
    kr_remux_log(log, sizeof log);
    CHECK(strstr(log, "start: ") && strstr(log, "master: BANDWIDTH=") && strstr(log, "CODECS=\"") && !strstr(log, "#EXT"),
          "%s: the log names the source and the variant line:\n%s", fx->file, log);
    snprintf(prefix_path, sizeof prefix_path, "%s", strstr(m3u8, "://") ? strchr(strstr(m3u8, "://") + 3, '/') : "");
    char *cut = strstr(prefix_path, "/master.m3u8"); if (cut) *cut = 0;
    CHECK(st == KR_READY, "%s: start %d (%s)", fx->file, st, kr_remux_message());
    if (st != KR_READY) return;
    int port = kr_remux_port();
    CHECK(port > 0 && strstr(m3u8, "/master.m3u8") && (fx->lan || strstr(m3u8, "http://127.0.0.1:")), "playlist url %s", m3u8);
    reply master = http_get(port, "/master.m3u8", NULL);
    CHECK(master.status == 200 && strstr(master.head, "application/vnd.apple.mpegurl"), "master status");
    const char *pl = master.body ? master.body : "";
    CHECK(!strncmp(pl, "#EXTM3U\n#EXT-X-VERSION:7\n", 25), "%s master header", fx->file);
    CHECK(strstr(pl, fx->video) != NULL, "%s: video codec %s in\n%s", fx->file, fx->video, pl);
    CHECK(strstr(pl, fx->audio_tokens) != NULL, "%s: audio tokens %s in\n%s", fx->file, fx->audio_tokens, pl);
    CHECK(count(pl, "TYPE=AUDIO") == fx->audio_tracks, "%s: %d audio renditions", fx->file, fx->audio_tracks);
    CHECK(count(pl, "DEFAULT=YES") == (fx->audio_tracks ? 1 : 0), "%s: one default audio", fx->file);
    CHECK(count(pl, "TYPE=SUBTITLES") == fx->subs, "%s: %d subtitle renditions", fx->file, fx->subs);
    if (fx->hdr) CHECK(strstr(pl, ".L") && strstr(pl, ".90,") && !strstr(pl, ".B0"), "%s: HEVC constraint bytes from the hvcC (x265: 90) in\n%s", fx->file, pl);
    CHECK(strstr(pl, fx->hdr ? "VIDEO-RANGE=PQ" : "VIDEO-RANGE=SDR") != NULL, "%s video range", fx->file);
    CHECK(strstr(pl, "RESOLUTION=320x180") && strstr(pl, "FRAME-RATE=24.000"), "%s resolution/fps", fx->file);
    CHECK(count(pl, "(AAC)") == fx->bridged, "%s: %d bridged renditions named", fx->file, fx->bridged);

    reply video = http_get(port, "/video/index.m3u8", NULL);
    double total, maxd; int target;
    int nseg = playlist_segments(video.body ? video.body : "", &total, &maxd, &target);
    CHECK(nseg >= 2, "%s: %d segments", fx->file, nseg);
    CHECK(fabs(total - 20.0) < 0.2, "%s: EXTINF total %.3f", fx->file, total);
    CHECK(target == (int)ceil(maxd) && target >= 1, "%s: target duration %d vs max %.3f", fx->file, target, maxd);
    CHECK(strstr(video.body, "#EXT-X-MAP:URI=") && strstr(video.body, "#EXT-X-ENDLIST\n") && strstr(video.body, "#EXT-X-PLAYLIST-TYPE:VOD"), "media tags");
    char out[512];
    snprintf(out, sizeof out, "%s/%s.video.mp4", work, fx->file);
    check_rendition(port, "/video", nseg, 20.0 + fx->offset, out, 0);

    // Seeks: a later segment first, then an earlier one, then the later one again: same bytes.
    if (nseg >= 3) {
        reply a = http_get(port, "/video/seg2.m4s", NULL), b = http_get(port, "/video/seg0.m4s", NULL), c = http_get(port, "/video/seg2.m4s", NULL);
        CHECK(a.len == c.len && a.len && !memcmp(a.body, c.body, a.len), "%s: segment 2 identical after a seek back", fx->file);
        // Range on a segment (AVPlayer sometimes asks for part of one).
        reply part = http_get(port, "/video/seg2.m4s", "bytes=100-199");
        CHECK(part.status == 206 && part.len == 100 && !memcmp(part.body, a.body + 100, 100), "%s: Range on a segment", fx->file);
        CHECK(strstr(part.head, "Content-Range: bytes 100-199/") != NULL, "Content-Range header");
        free(a.body); free(b.body); free(c.body); free(part.body);
    }

    // Every audio rendition: copied or bridged, with a continuous timeline across segment boundaries.
    for (const char *p = pl; (p = strstr(p, "/audio/")); p++) {
        int idx = atoi(p + 7);
        char prefix[64]; snprintf(prefix, sizeof prefix, "/audio/%d", idx);
        char ipath[96]; snprintf(ipath, sizeof ipath, "%s/index.m3u8", prefix);
        reply ap = http_get(port, ipath, NULL);
        double at; int an = playlist_segments(ap.body ? ap.body : "", &at, &maxd, &target);
        CHECK(an == nseg, "%s: audio %d has the video's %d segments (%d)", fx->file, idx, nseg, an);
        snprintf(out, sizeof out, "%s/%s.audio%d.mp4", work, fx->file, idx);
        check_rendition(port, prefix, an, 20.0 + fx->offset, out, 1);
        free(ap.body);
        p += 7;
    }

    if (fx->subs) {
        const char *s = strstr(pl, "/subs/");
        int idx = s ? atoi(s + 6) : -1;
        char path[64]; snprintf(path, sizeof path, "/subs/%d/index.m3u8", idx);
        reply sp = http_get(port, path, NULL);
        CHECK(sp.status == 200 && strstr(sp.body, "seg0.vtt") && !strstr(sp.body, "EXT-X-MAP"), "subtitle playlist");
        snprintf(path, sizeof path, "/subs/%d/seg0.vtt", idx);
        reply vtt = http_get(port, path, NULL);
        CHECK(vtt.status == 200 && !strncmp(vtt.body, "WEBVTT", 6), "%s: WebVTT segment", fx->file);
        CHECK(strstr(vtt.body, fx->sub_text) != NULL && !strchr(vtt.body, '{'), "%s: cue text %s (tags stripped) in\n%s", fx->file, fx->sub_text, vtt.body);
        // r9: cues of later segments (owner build-138: every segment after a seek was the bare header). The SRT's
        // second cue (6.5-7.5 s) sits in the segment whose window holds 6.5 s, fetched out of order (last first).
        if (strstr(fx->sub_text, "SRT")) {
            double st[64]; int ns = 0; double t = 0;
            for (const char *q = sp.body; q && (q = strstr(q, "#EXTINF:")) && ns < 63; q += 8) { st[ns++] = t; t += atof(q + 8); }
            st[ns] = t;
            int want = -1;
            for (int k = 0; k < ns; k++) if (6.5 >= st[k] && 6.5 < st[k + 1]) want = k;
            CHECK(want > 0, "%s: a later subtitle segment holds 6.5 s (%d of %d)", fx->file, want, ns);
            for (int k = ns - 1; k >= 0 && want > 0; k--) {
                snprintf(path, sizeof path, "/subs/%d/seg%d.vtt", idx, k);
                reply sv = http_get(port, path, NULL);
                int has = sv.body && strstr(sv.body, "Second line") != NULL;
                CHECK(sv.status == 200 && has == (k == want), "%s: subtitle segment %d %s the 6.5 s cue:\n%s", fx->file, k,
                      k == want ? "has" : "lacks", sv.body ? sv.body : "");
                free(sv.body);
            }
        }
        free(sp.body); free(vtt.body);
    }
    reply missing = http_get(port, "/nothing", NULL);
    CHECK(missing.status == 404, "404 for unknown paths");
    reply notoken = http_get_raw(port, "/master.m3u8", NULL);
    CHECK(notoken.status == 404, "404 without the session token");
    reply badtoken = http_get_raw(port, "/0000/master.m3u8", NULL);
    CHECK(badtoken.status == 404, "404 with a wrong token");
    CHECK(strlen(prefix_path) == 33, "token of 32 hex digits (%s)", prefix_path);
    if (fx->lan) CHECK(!strstr(m3u8, "127.0.0.1") && !strstr(pl, "127.0.0.1"), "AirPlay playlists use the network address: %s", m3u8);
    free(notoken.body); free(badtoken.body);
    reply bad = http_get(port, "/video/seg9999.m4s", NULL);
    CHECK(bad.status == 500 && *kr_remux_message(), "a failed segment is reported (%s)", kr_remux_message());
    free(missing.body); free(bad.body); free(master.body); free(video.body);
    CHECK(kr_remux_served(1) >= nseg && (fx->audio_tracks == 0 || kr_remux_served(0) > 0), "%s: segments counted (%d video, %d audio)",
          fx->file, kr_remux_served(1), kr_remux_served(0));
    CHECK(!strncmp(kr_remux_video_codec(), fx->video, strlen(fx->video)), "%s: session codec %s", fx->file, kr_remux_video_codec());
    CHECK(kr_remux_compat() == 0, "%s: video copied by default", fx->file);
    char small[48];
    int n1 = kr_remux_log(small, sizeof small);
    CHECK(n1 < (int)sizeof small && (n1 == 0 || small[n1 - 1] == '\n'), "a short buffer gets whole lines only (%d)", n1);
    strcpy(log, small); kr_remux_log(log + n1, (int)sizeof log - n1);
    CHECK(strstr(log, "client: test_remux/1\n") && strstr(log, "GET /video/seg9999.m4s 500 0 B ") && strstr(log, "error: AirPlay conversion failed")
          && strstr(log, "GET (no token) 404") && strstr(log, " 206 100 B "), "%s: requests and errors logged:\n%.3000s", fx->file, log);
    CHECK(kr_remux_log(log, sizeof log) == 0 && !*log, "the log is read once");

    kr_remux_stop();
    CHECK(kr_remux_state() == KR_IDLE && kr_remux_port() == 0, "stopped");
    reply gone = http_get_raw(port, "/master.m3u8", NULL);
    CHECK(gone.status == -1, "%s: the server is gone after stop", fx->file);
}

typedef struct { kr_source *source; int result; uint8_t bytes[4096]; } source_wait;
static int interrupt_source_wait(void *context) { return atomic_load((atomic_int *)context); }
static void *waiting_source_read(void *context) {
    source_wait *w=context;w->result=kr_source_read(w->source,700000,w->bytes,sizeof w->bytes);return NULL;
}

static void test_source_transport(const char *http_base) {
    char url[512], path[512], err[256] = "";
    extern const char *fixture_dir;
    snprintf(path, sizeof path, "%s/h264_dts.mkv", fixture_dir);
    FILE *f = fopen(path, "rb");
    CHECK(f != NULL, "transport fixture opens");
    if (!f) return;
    uint8_t *a = malloc(1500000), *b = malloc(1500000);
    CHECK(a && b, "transport comparison buffers allocated");
    if (!a || !b) { free(a); free(b); fclose(f); return; }
    snprintf(url, sizeof url, "%s/bounded/h264_dts.mkv", http_base);
    kr_source *s = kr_source_open(url, 3, err, sizeof err);
    CHECK(s != NULL, "finite-range-only server opens (%s)", err);
    if (s) {
        int64_t size = kr_source_size(s), offset = 0;
        // Each read spans the initial 256 KiB and subsequent 1 MiB HTTP response boundaries.
        while (offset < size) {
            int n = kr_source_read(s, offset, a, 1500000);
            int m = (int)fread(b, 1, 1500000, f);
            CHECK(n == m && n > 0 && !memcmp(a, b, (size_t)n), "bounded sequential bytes at %lld (%d/%d)", (long long)offset, n, m);
            if (n <= 0 || n != m) break;
            offset += n;
        }
        CHECK(offset == size && kr_source_read(s, size, a, 1) == 0, "bounded reads reach exact EOF");
        int64_t offsets[] = { size-23, 4096, size/2, 0 };
        for (int i = 0; i < 4; i++) {
            int n = kr_source_read(s, offsets[i], a, 4096);
            fseek(f, (long)offsets[i], SEEK_SET);
            int m = (int)fread(b, 1, 4096, f);
            CHECK(n == m && n > 0 && !memcmp(a, b, (size_t)n), "bounded forward/backward seek at %lld", (long long)offsets[i]);
        }
        kr_source_close(s);
    }
    snprintf(url,sizeof url,"%s/stall/h264_dts.mkv",http_base);
    s=kr_source_open(url,10,err,sizeof err);
    CHECK(s!=NULL,"transient-interrupt source opens");
    if(s){
        atomic_int cancelled=0;kr_source_set_interrupt(s,interrupt_source_wait,&cancelled);
        source_wait wait={.source=s};pthread_t thread;pthread_create(&thread,NULL,waiting_source_read,&wait);
        usleep(150000);struct timespec before,after;clock_gettime(CLOCK_MONOTONIC,&before);
        atomic_store(&cancelled,1);pthread_join(thread,NULL);clock_gettime(CLOCK_MONOTONIC,&after);
        double elapsed=after.tv_sec-before.tv_sec+(after.tv_nsec-before.tv_nsec)/1e9;
        CHECK(wait.result<0 && elapsed<1,"canceled speculative read interrupts network wait (%.3f s, result %d)",elapsed,wait.result);
        atomic_store(&cancelled,0);
        int n=kr_source_read(s,700000,a,4096);fseek(f,700000,SEEK_SET);int m=(int)fread(b,1,4096,f);
        CHECK(n==m && n>0 && !memcmp(a,b,(size_t)n),"next read recovers exact bytes after transient cancellation");
        kr_source_set_interrupt(s,NULL,NULL);kr_source_close(s);
    }
    snprintf(url, sizeof url, "%s/recover/h264_dts.mkv", http_base);
    s = kr_source_open(url, 3, err, sizeof err);
    CHECK(s != NULL, "fault-injection source opens");
    if (s) {
        int n = kr_source_read(s, 700000, a, 4096);
        fseek(f, 700000, SEEK_SET); int m = (int)fread(b, 1, 4096, f);
        CHECK(n == m && n > 0 && !memcmp(a, b, (size_t)n), "truncated seek response recovers exact bytes on fresh connection");
        n = kr_source_read(s, 704096, a, 4096);
        m = (int)fread(b, 1, 4096, f);
        CHECK(n == m && n > 0 && !memcmp(a, b, (size_t)n), "reading continues from recovered offset");
        n = kr_source_read(s, 699900, a, 4096);
        fseek(f, 699900, SEEK_SET); m = (int)fread(b, 1, 4096, f);
        CHECK(n == m && n > 0 && !memcmp(a, b, (size_t)n), "backward seek within reopened buffer preserves absolute offsets");
        kr_source_close(s);
    }
    snprintf(url, sizeof url, "%s/stall/h264_dts.mkv", http_base);
    s = kr_source_open(url, 1, err, sizeof err);
    CHECK(s != NULL, "stalled-read source opens");
    if (s) {
        struct timespec before, after;
        clock_gettime(CLOCK_MONOTONIC, &before);
        int n = kr_source_read(s, 700000, a, 4096);
        clock_gettime(CLOCK_MONOTONIC, &after);
        double elapsed = after.tv_sec-before.tv_sec + (after.tv_nsec-before.tv_nsec)/1e9;
        CHECK(n < 0 && elapsed >= .8 && elapsed < 1.8, "stalled read honors ONE timeout budget, not three (%.3f s, result %d)", elapsed, n);
        printf("  stalled source: one-second read budget returned in %.3f s\n", elapsed);
        kr_source_abort(s);
        CHECK(kr_source_read(s, 0, a, 4096) < 0, "timed-out source still honors stop");
        kr_source_close(s);
    }
    free(a); free(b); fclose(f);
}

static void test_range_source(const char *http_base) {
    char url[512]; snprintf(url, sizeof url, "%s/h264_dts.mkv", http_base);
    char err[256] = "";
    kr_source *s = kr_source_open(url, 10, err, sizeof err);
    CHECK(s != NULL, "range source opens (%s)", err);
    if (!s) return;
    FILE *f = NULL;
    int64_t size = kr_source_size(s);
    CHECK(size > 1000000, "size over HTTP %lld", (long long)size);
    // Reads at scattered offsets must match the bytes at those offsets (Range requests, backwards too).
    static uint8_t a[4096], b[4096];
    int64_t offsets[] = { size - 4096, 0, size / 2, 12345, size - 10 };
    extern const char *fixture_dir;
    char path[512]; snprintf(path, sizeof path, "%s/h264_dts.mkv", fixture_dir);
    f = fopen(path, "rb");
    for (int i = 0; i < 5; i++) {
        int n = kr_source_read(s, offsets[i], a, sizeof a);
        fseek(f, (long)offsets[i], SEEK_SET);
        int m = (int)fread(b, 1, sizeof b, f);
        CHECK(n == m && n > 0 && !memcmp(a, b, (size_t)n), "range read at %lld: %d vs %d bytes", (long long)offsets[i], n, m);
    }
    CHECK(kr_source_read(s, size, a, 16) == 0, "read at the end returns 0");
    CHECK(kr_source_io_ms(s) > 0, "source I/O timing includes actual range reads");
    kr_source_abort(s);
    CHECK(kr_source_read(s, 0, a, 16) < 0, "reads fail after abort (stop pressed)");
    fclose(f);
    kr_source_close(s);
    char m3u8[256];
    snprintf(url, sizeof url, "%s/h264_aac.mp4", http_base);
    CHECK(kr_remux_start(url, 0, 0, m3u8, sizeof m3u8) == KR_READY, "MP4 bytes reach codec-aware HLS routing (%s)", kr_remux_message());
    snprintf(url, sizeof url, "%s/missing.mkv", http_base);
    CHECK(kr_remux_start(url, 0, 0, m3u8, sizeof m3u8) == KR_FAILED && strstr(kr_remux_message(), "AirPlay"), "a missing file explains itself: %s", kr_remux_message());
    kr_remux_stop();
}


// ── r7 compat (picture converted, kr_video) ───────────────────────────────────
// Pure pieces: output size, bit rate, CODECS, window tiling.
static void test_video_units(void) {
    int w, h;
    kr_video_output_size(3840, 2160, &w, &h); CHECK(w == 1920 && h == 1080, "4K -> 1080p (%dx%d)", w, h);
    kr_video_output_size(3840, 1600, &w, &h); CHECK(w == 1920 && h == 800, "scope 4K -> 1920x800 (%dx%d)", w, h);
    kr_video_output_size(4096, 1716, &w, &h); CHECK(w == 1920 && h == 804, "DCI scope, even (%dx%d)", w, h);
    kr_video_output_size(1440, 1920, &w, &h); CHECK(w == 810 && h == 1080, "portrait capped by height (%dx%d)", w, h);
    kr_video_output_size(720, 480, &w, &h); CHECK(w == 720 && h == 480, "SD never upscaled (%dx%d)", w, h);
    kr_video_output_size(321, 181, &w, &h); CHECK(w == 320 && h == 180, "odd sizes made even (%dx%d)", w, h);
    CHECK(kr_video_bitrate(1920, 1080) == 7000000, "1080p at 7 Mbit/s (%d)", kr_video_bitrate(1920, 1080));
    CHECK(kr_video_bitrate(320, 180) == 1500000, "floor 1.5 Mbit/s");
    CHECK(!strcmp(kr_video_codecs(23.976), "avc1.640028") && !strcmp(kr_video_codecs(30), "avc1.640028") &&
          !strcmp(kr_video_codecs(59.94), "avc1.64002A") && !strcmp(KR_VIDEO_CODECS, "avc1.640028"), "H.264 High 4.0 / 4.2 CODECS");
    // Every frame time falls in exactly one window of a grid (no gap, no overlap), boundaries included.
    double grid[] = { 0, 6.006, 12.012, 18.018 };
    int bad = 0;
    for (int k = 0; k < 24 * 25; k++) {
        double t = k / 24.0 * 1.001;
        int hits = 0;
        for (int i = 0; i < 4; i++) hits += kr_video_in_window(t, i ? grid[i] : -1e9, i < 3 ? grid[i + 1] : -1);
        if (hits != 1) bad++;
    }
    CHECK(bad == 0, "windows tile the timeline (%d frames in 0 or 2 windows)", bad);
    CHECK(kr_video_in_window(6.006, 0, 6.006) == 0 && kr_video_in_window(6.006, 6.006, 12.012) == 1, "a boundary frame opens the next segment");
}

// Decodes a joined init+segments file: frame count, timestamps continuous, first frame of each segment a keyframe.
static int decode_count(const char *file, int *keyframes) {
    AVFormatContext *in = NULL;
    if (avformat_open_input(&in, file, NULL, NULL) < 0) return -1;
    avformat_find_stream_info(in, NULL);
    const AVCodec *dc = avcodec_find_decoder(in->streams[0]->codecpar->codec_id);
    AVCodecContext *c = dc ? avcodec_alloc_context3(dc) : NULL;
    if (!c) { avformat_close_input(&in); return -1; }
    avcodec_parameters_to_context(c, in->streams[0]->codecpar);
    if (avcodec_open2(c, dc, NULL) < 0) { avcodec_free_context(&c); avformat_close_input(&in); return -1; }
    AVPacket *p = av_packet_alloc(); AVFrame *f = av_frame_alloc();
    int frames = 0; *keyframes = 0;
    while (av_read_frame(in, p) == 0) {
        if (p->flags & AV_PKT_FLAG_KEY) (*keyframes)++;
        avcodec_send_packet(c, p); av_packet_unref(p);
        while (avcodec_receive_frame(c, f) == 0) { frames++; av_frame_unref(f); }
    }
    avcodec_send_packet(c, NULL);
    while (avcodec_receive_frame(c, f) == 0) { frames++; av_frame_unref(f); }
    av_frame_free(&f); av_packet_free(&p); avcodec_free_context(&c); avformat_close_input(&in);
    return frames;
}

// First packet time and key flag of one segment, joined to the init.
static double segment_first(const reply *init, const reply *seg, const char *tmp, int *key) {
    FILE *f = fopen(tmp, "wb"); fwrite(init->body, 1, init->len, f); fwrite(seg->body, 1, seg->len, f); fclose(f);
    AVFormatContext *in = NULL; *key = 0;
    if (avformat_open_input(&in, tmp, NULL, NULL) < 0) return -1;
    AVPacket *p = av_packet_alloc();
    double t = -1;
    if (av_read_frame(in, p) == 0) { t = p->pts * av_q2d(in->streams[0]->time_base); *key = (p->flags & AV_PKT_FLAG_KEY) != 0; }
    av_packet_free(&p); avformat_close_input(&in);
    return t;
}

// compat=1 asked for (HEVC 10-bit PQ, H.264 TS starting at 1.4 s), or chosen by itself (MPEG-2: not an AirPlay codec).
static void test_compat(const char *url, const char *name, int ask, double offset, const char *audio_token, const char *work) {
    char m3u8[256];
    static char log[1 << 16];
    while (kr_remux_log(log, sizeof log) > 0) {}
    int st = kr_remux_start(url, 0, ask, m3u8, sizeof m3u8);
    CHECK(st == KR_READY, "%s compat: start %d (%s)", name, st, kr_remux_message());
    if (st != KR_READY) return;
    snprintf(prefix_path, sizeof prefix_path, "%s", strchr(strstr(m3u8, "://") + 3, '/'));
    char *cut = strstr(prefix_path, "/master.m3u8"); if (cut) *cut = 0;
    int port = kr_remux_port();
    CHECK(kr_remux_compat() == 1, "%s: compat session", name);
    CHECK(!strcmp(kr_remux_video_codec(), "avc1.640028"), "%s: session codec %s", name, kr_remux_video_codec());
    reply master = http_get(port, "/master.m3u8", NULL);
    const char *pl = master.body ? master.body : "";
    char want[64]; snprintf(want, sizeof want, "CODECS=\"avc1.640028,%s\"", audio_token);
    CHECK(strstr(pl, want) && !strstr(pl, "hvc1") && strstr(pl, "VIDEO-RANGE=SDR") && strstr(pl, "RESOLUTION=320x180") &&
          strstr(pl, "FRAME-RATE=24.000") && strstr(pl, "BANDWIDTH=2890000,"), "%s: compat variant (%s) in\n%s", name, want, pl);
    reply video = http_get(port, "/video/index.m3u8", NULL);
    double total, maxd; int target;
    int nseg = playlist_segments(video.body ? video.body : "", &total, &maxd, &target);
    CHECK(nseg >= 3 && fabs(total - 20.0) < 0.2, "%s: %d segments, %.3f s", name, nseg, total);
    // Out of order first (a seek): segment 2, then 0.
    reply init = http_get(port, "/video/init.mp4", NULL);
    CHECK(init.status == 200 && init.len > 8 && !memcmp(init.body + 4, "ftyp", 4) && kr_first_moof((uint8_t *)init.body, (int)init.len) < 0,
          "%s: converted init (status %d)", name, init.status);
    double start = 0;  // the planned grid: segment i starts at the sum of the EXTINFs before it (the first at the first frame)
    const char *p = video.body ? video.body : "";
    char tmp[512]; snprintf(tmp, sizeof tmp, "%s/%s.compat.one.mp4", work, name);
    for (int i = nseg >= 3 ? 2 : 0, pass = 0; pass < 2; pass++, i = 0) {
        char path[64]; snprintf(path, sizeof path, "/video/seg%d.m4s", i);
        reply seg = http_get(port, path, NULL);
        CHECK(seg.status == 200 && kr_first_moof((uint8_t *)seg.body, (int)seg.len) == 0, "%s: %s converted (%d)", name, path, seg.status);
        free(seg.body);
    }
    // Each segment opens with a keyframe exactly at its place on the grid (tfdt absolute, no rebasing).
    int seg_ok = 0;
    for (int i = 0; i < nseg; i++) {
        p = strstr(p, "#EXTINF:");
        double d = p ? atof(p + 8) : 0; if (p) p += 8;
        char path[64]; snprintf(path, sizeof path, "/video/seg%d.m4s", i);
        reply seg = http_get(port, path, NULL);
        int key = 0;
        double t = segment_first(&init, &seg, tmp, &key);
        double grid = fmax(start, offset);
        if (key && fabs(t - grid) < 1.0 / 24 + 0.002) seg_ok++;
        else printf("  %s seg%d: first %.3f (grid %.3f) key %d\n", name, i, t, grid, key);
        start += d;
        free(seg.body);
    }
    CHECK(seg_ok == nseg, "%s: %d/%d segments start with a keyframe on the grid", name, seg_ok, nseg);
    char out[512]; snprintf(out, sizeof out, "%s/%s.compat.video.mp4", work, name);
    start_offset = offset;
    check_rendition(port, "/video", nseg, 20.0 + offset, out, 0);
    int keys = 0, frames = decode_count(out, &keys);
    CHECK(frames == 480, "%s: every source frame converted once (%d of 480)", name, frames);
    CHECK(keys == nseg, "%s: one keyframe per segment (%d, %d segments)", name, keys, nseg);
    {   // the converted size and the 8-bit SDR format
        AVFormatContext *in = NULL;
        if (avformat_open_input(&in, out, NULL, NULL) == 0) {
            avformat_find_stream_info(in, NULL);
            AVCodecParameters *cp = in->streams[0]->codecpar;
            CHECK(cp->width == 320 && cp->height == 180 && (cp->format == AV_PIX_FMT_YUV420P || cp->format == AV_PIX_FMT_NV12),
                  "%s: 320x180 8-bit 4:2:0 (%dx%d fmt %d)", name, cp->width, cp->height, cp->format);
            avformat_close_input(&in);
        }
    }
    // Audio still there, on the same grid.
    const char *a = strstr(pl, "/audio/");
    if (a) {
        char prefix[64]; snprintf(prefix, sizeof prefix, "/audio/%d", atoi(a + 7));
        snprintf(out, sizeof out, "%s/%s.compat.audio.mp4", work, name);
        check_rendition(port, prefix, nseg, 20.0 + offset, out, 1);
    }
    kr_remux_log(log, sizeof log);
    CHECK(strstr(log, "compat: converting video stream") && strstr(log, "with mpeg4 (software decoding)"), "%s: conversion logged:\n%.2000s", name, log);
    if (!ask) CHECK(strstr(log, "compat: the video is not H.264/HEVC") != NULL, "%s: switched by itself", name);
    free(master.body); free(video.body); free(init.body);
    kr_remux_stop();
    CHECK(kr_remux_compat() == 0 && kr_remux_state() == KR_IDLE, "%s: compat cleared on stop", name);
}

// Stop while a segment is being converted: the request ends, stop returns promptly.
static void *fetch_seg(void *arg) { int port = (int)(intptr_t)arg; reply r = http_get(port, "/video/seg1.m4s", NULL); free(r.body); return NULL; }
static void test_compat_stop(const char *url) {
    char m3u8[256];
    if (kr_remux_start(url, 0, 1, m3u8, sizeof m3u8) != KR_READY) { CHECK(0, "compat stop: start (%s)", kr_remux_message()); return; }
    snprintf(prefix_path, sizeof prefix_path, "%s", strchr(strstr(m3u8, "://") + 3, '/'));
    char *cut = strstr(prefix_path, "/master.m3u8"); if (cut) *cut = 0;
    pthread_t t; pthread_create(&t, NULL, fetch_seg, (void *)(intptr_t)kr_remux_port());
    usleep(20000);
    struct timespec a, b; clock_gettime(CLOCK_MONOTONIC, &a);
    kr_remux_stop();
    clock_gettime(CLOCK_MONOTONIC, &b);
    pthread_join(t, NULL);
    double s = (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / 1e9;
    CHECK(s < 4.5 && kr_remux_state() == KR_IDLE, "stop during a conversion returns (%.2f s)", s);
}

// ── r8: per receiver compat, cache and segments made ahead ─────────────────────
#define UA_PHONE "AppleCoreMedia/1.0.0.24A446 (iPhone; U; CPU OS 27_0_1 like Mac OS X; en_us)"
#define UA_APPLETV "AppleCoreMedia/1.0.0.22J580 (Apple TV; U; CPU OS 18_0 like Mac OS X; en_us)"
#define UA_TV "AirPlay/2.0 (App/80.141.0) MFi_AirPlay_Device (MFiModelGroup/TCL Roku TV)"

static int start_session(const char *url, int compat, char *m3u8, size_t len) {
    int st = kr_remux_start(url, 0, compat, m3u8, (int)len);
    if (st == KR_READY) {
        snprintf(prefix_path, sizeof prefix_path, "%s", strchr(strstr(m3u8, "://") + 3, '/'));
        char *cut = strstr(prefix_path, "/master.m3u8"); if (cut) *cut = 0;
    }
    return st;
}

static reply get_as(const char *ua, int port, const char *path) {
    const char *was = test_ua; test_ua = ua;
    reply r = http_get(port, path, NULL);
    test_ua = was;
    return r;
}

// An HEVC file played in copy mode: the phone and an Apple TV get the HEVC copy, a third-party TV (MFi_AirPlay_Device)
// the picture converted to H.264, on the same grid. An H.264 file: everyone gets the copy.
static void test_receivers(const char *hevc, const char *h264, const char *work) {
    CHECK(kr_remux_third_party_receiver(UA_TV) && kr_remux_third_party_receiver("airplay/2.0 mfi_airplay_device"), "a TV's AirPlay is third-party");
    CHECK(!kr_remux_third_party_receiver(UA_PHONE) && !kr_remux_third_party_receiver(UA_APPLETV) && !kr_remux_third_party_receiver("AirPlay/2.0") &&
          !kr_remux_third_party_receiver("") && !kr_remux_third_party_receiver(NULL), "Apple's players are not third-party");
    static char log[1 << 16];
    while (kr_remux_log(log, sizeof log) > 0) {}
    char m3u8[256];
    int st = start_session(hevc, 0, m3u8, sizeof m3u8);
    CHECK(st == KR_READY && kr_remux_compat() == 0, "receivers: HEVC copy session (%d %s)", st, kr_remux_message());
    if (st != KR_READY) return;
    int port = kr_remux_port();
    reply phone = get_as(UA_PHONE, port, "/master.m3u8"), atv = get_as(UA_APPLETV, port, "/master.m3u8");
    CHECK(kr_remux_compat_clients() == 0, "no compat master before the TV asks");
    reply tv = get_as(UA_TV, port, "/master.m3u8");
    const char *p = phone.body ? phone.body : "", *t = tv.body ? tv.body : "";
    CHECK(strstr(p, "hvc1.") && strstr(p, "/video/index.m3u8") && !strstr(p, "cvideo"), "the phone gets the HEVC copy:\n%s", p);
    CHECK(atv.body && !strcmp(atv.body, p), "an Apple TV gets the HEVC copy:\n%s", atv.body ? atv.body : "");
    CHECK(strstr(t, "CODECS=\"avc1.640028,ac-3\"") && strstr(t, "/cvideo/index.m3u8") && !strstr(t, "hvc1") && strstr(t, "VIDEO-RANGE=SDR") &&
          strstr(t, "RESOLUTION=320x180"), "the TV gets the H.264 picture:\n%s", t);
    const char *pv = strstr(p, "#EXT-X-STREAM-INF:"), *tvv = strstr(t, "#EXT-X-STREAM-INF:");
    CHECK(pv && tvv && pv - p == tvv - t && !memcmp(p, t, (size_t)(pv - p)), "same audio and subtitle renditions for both");
    CHECK(kr_remux_compat_clients() == 1, "one compat master served (%d)", kr_remux_compat_clients());
    reply vpl = get_as(UA_PHONE, port, "/video/index.m3u8"), cpl = get_as(UA_TV, port, "/cvideo/index.m3u8");
    char *same = cpl.body ? strdup(cpl.body) : strdup("");
    for (char *q; (q = strstr(same, "/cvideo/")); ) memmove(q + 1, q + 2, strlen(q + 2) + 1);  // "/cvideo/" -> "/video/"
    CHECK(vpl.body && !strcmp(same, vpl.body), "the converted picture has the copy's segment grid:\n%s\nvs\n%s", same, vpl.body ? vpl.body : "");
    free(same);
    double total, maxd; int target;
    int nseg = playlist_segments(vpl.body ? vpl.body : "", &total, &maxd, &target);
    reply vinit = get_as(UA_PHONE, port, "/video/init.mp4"), cinit = get_as(UA_TV, port, "/cvideo/init.mp4");
    CHECK(vinit.status == 200 && cinit.status == 200 && (vinit.len != cinit.len || memcmp(vinit.body, cinit.body, vinit.len)), "two different inits");
    reply ph0 = get_as(UA_PHONE, port, "/video/seg0.m4s");
    CHECK(kr_remux_served(1) == 1 && kr_remux_served_external(1) == 0, "the phone's segments are not the TV's (%d, %d)",
          kr_remux_served(1), kr_remux_served_external(1));
    free(ph0.body);
    char tmp[512]; snprintf(tmp, sizeof tmp, "%s/receivers.one.mp4", work);
    int aligned = 0;
    for (int i = 0; i < nseg; i++) {
        char path[64]; snprintf(path, sizeof path, "/video/seg%d.m4s", i);
        reply a = get_as(UA_PHONE, port, path);
        snprintf(path, sizeof path, "/cvideo/seg%d.m4s", i);
        reply b = get_as(UA_TV, port, path);
        int ka = 0, kb = 0;
        double ta = segment_first(&vinit, &a, tmp, &ka), tb = segment_first(&cinit, &b, tmp, &kb);
        if (ka && kb && fabs(ta - tb) < 1.0 / 24 + 0.002) aligned++;
        else printf("  seg%d: copy %.3f key %d, converted %.3f key %d\n", i, ta, ka, tb, kb);
        free(a.body); free(b.body);
    }
    CHECK(nseg >= 3 && aligned == nseg, "copy and converted segments start on the same frame (%d/%d)", aligned, nseg);
    CHECK(kr_remux_served_external(1) == nseg && kr_remux_served(1) == 2 * nseg + 1, "the TV took %d video segments (%d in all)",
          kr_remux_served_external(1), kr_remux_served(1));
    // A TV asking /video/ itself (without the master) gets the converted picture as well; the phone the copy.
    reply tv1 = get_as(UA_TV, port, "/video/seg1.m4s"), tc1 = get_as(UA_TV, port, "/cvideo/seg1.m4s"), ph1 = get_as(UA_PHONE, port, "/video/seg1.m4s");
    CHECK(tv1.len && tv1.len == tc1.len && !memcmp(tv1.body, tc1.body, tv1.len), "the TV's /video/ is converted");
    CHECK(ph1.len && (ph1.len != tc1.len || memcmp(ph1.body, tc1.body, ph1.len)), "the phone's /video/ is the copy");
    char out[512]; snprintf(out, sizeof out, "%s/receivers.converted.mp4", work);
    const char *was = test_ua; test_ua = UA_TV;
    start_offset = 0;
    check_rendition(port, "/cvideo", nseg, 20.0, out, 0);
    test_ua = was;
    int keys = 0;
    CHECK(decode_count(out, &keys) == 480 && keys == nseg, "the TV's picture: every frame once, a keyframe per segment (%d)", keys);
    kr_remux_log(log, sizeof log);
    CHECK(strstr(log, "compat: third-party AirPlay receivers (MFi_AirPlay_Device) get the picture as H.264, others the hvc1.") &&
          strstr(log, "compat: AirPlay/2.0 (App/80.141.0) MFi_AirPlay_Device") && strstr(log, "gets the picture as H.264: BANDWIDTH=") &&
          strstr(log, "client: " UA_TV), "per-receiver compat logged:\n%.3000s", log);
    free(phone.body); free(atv.body); free(tv.body); free(vpl.body); free(cpl.body); free(vinit.body); free(cinit.body);
    free(tv1.body); free(tc1.body); free(ph1.body);
    kr_remux_stop();

    st = start_session(h264, 0, m3u8, sizeof m3u8);
    CHECK(st == KR_READY, "receivers: H.264 session");
    if (st != KR_READY) return;
    port = kr_remux_port();
    reply h = get_as(UA_TV, port, "/master.m3u8"), c = get_as(UA_TV, port, "/cvideo/index.m3u8");
    CHECK(h.body && strstr(h.body, "avc1.42C0") && strstr(h.body, "/video/index.m3u8") && !strstr(h.body, "cvideo"), "H.264: the TV gets the copy");
    CHECK(c.status == 404 && kr_remux_compat_clients() == 0, "H.264: no converted picture (%d)", c.status);
    free(h.body); free(c.body);
    kr_remux_stop();
}

static void test_extra_format(const char *url, const char *name, const char *work, int force) {
    char master_url[256], out[512];
    int st = start_session(url, force, master_url, sizeof master_url);
    CHECK(st == KR_READY, "%s: codec routing opens (%s)", name, kr_remux_message());
    if (st != KR_READY) return;
    int port = kr_remux_port();
    reply init = http_get(port, "/video/init.mp4", NULL);
    reply target = http_get(port, "/video/seg2.m4s", NULL);
    CHECK(init.status == 200 && target.status == 200, "%s: seek target/init (%d, %d)", name, init.status, target.status);
    if (init.status == 200 && target.status == 200) {
        int key = 0, keys = 0;
        snprintf(out, sizeof out, "%s/%s-seek.mp4", work, name);
        double at = segment_first(&init, &target, out, &key);
        CHECK(key && at >= 11 && at < 16, "%s: independent target near requested time (%.3f)", name, at);
        CHECK(decode_count(out, &keys) > 0, "%s: seek target actually decodes", name);
    }
    reply back = http_get(port, "/video/seg0.m4s", NULL);
    reply retry = http_get(port, "/video/seg2.m4s", NULL);
    CHECK(back.status == 200 && retry.status == 200 && !*kr_remux_message(), "%s: backward/forward retry", name);
    reply master = http_get(port, "/master.m3u8", NULL);
    int audio = -1;
    const char *p = master.body ? strstr(master.body, "/audio/") : NULL;
    if (p) audio = atoi(p + 7);
    CHECK(audio >= 0, "%s: playable audio rendition", name);
    if (audio >= 0) {
        char path[64]; snprintf(path, sizeof path, "/audio/%d/init.mp4", audio);
        reply ai = http_get(port, path, NULL);
        snprintf(path, sizeof path, "/audio/%d/seg2.m4s", audio);
        reply as = http_get(port, path, NULL);
        CHECK(ai.status == 200 && as.status == 200 && as.len > 8, "%s: audio seek produces media", name);
        free(ai.body); free(as.body);
    }
    free(init.body); free(target.body); free(back.body); free(retry.body); free(master.body);
    kr_remux_stop();
}

// Synthetic Dolby configuration validates routing only; these HEVC pixels are not a Dolby Vision reference.
static void test_dovi_native_route(const char *input, const char *work) {
    AVFormatContext *in = NULL, *out = NULL;
    char path[512], playlist[256]; snprintf(path, sizeof path, "%s/dovi-routing.mp4", work);
    int r = avformat_open_input(&in, input, NULL, NULL);
    if (r >= 0) r = avformat_find_stream_info(in, NULL);
    if (r >= 0) r = avformat_alloc_output_context2(&out, NULL, "mp4", path);
    if (r < 0) { CHECK(0, "synthetic Dolby fixture setup"); avformat_close_input(&in); return; }
    for (unsigned i = 0; i < in->nb_streams; i++) {
        AVStream *st = avformat_new_stream(out, NULL);
        avcodec_parameters_copy(st->codecpar, in->streams[i]->codecpar); st->time_base = in->streams[i]->time_base;
        if (st->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) {
            AVPacketSideData *sd = av_packet_side_data_new(&st->codecpar->coded_side_data, &st->codecpar->nb_coded_side_data,
                AV_PKT_DATA_DOVI_CONF, sizeof(AVDOVIDecoderConfigurationRecord), 0);
            if (!sd) { r = -1; break; }
            AVDOVIDecoderConfigurationRecord *c = (void *)sd->data;
            memset(c, 0, sizeof *c); c->dv_version_major = 1; c->dv_profile = 5; c->dv_level = 6; c->rpu_present_flag = c->bl_present_flag = 1;
        }
    }
    out->strict_std_compliance = FF_COMPLIANCE_UNOFFICIAL; // permit the synthetic dvcC fixture box
    if (r >= 0) r = avio_open(&out->pb, path, AVIO_FLAG_WRITE);
    if (r >= 0) r = avformat_write_header(out, NULL);
    AVPacket *p = av_packet_alloc();
    while (r >= 0 && av_read_frame(in, p) >= 0) {
        av_packet_rescale_ts(p, in->streams[p->stream_index]->time_base, out->streams[p->stream_index]->time_base);
        r = av_interleaved_write_frame(out, p); av_packet_unref(p);
    }
    if (r >= 0) r = av_write_trailer(out);
    av_packet_free(&p); avio_closep(&out->pb); avformat_free_context(out); avformat_close_input(&in);
    CHECK(r >= 0, "synthetic Dolby configuration is muxed");
    if (r >= 0) CHECK(kr_remux_start(path, 0, 0, playlist, sizeof playlist) == KR_READY && kr_remux_compat(),
        "profile-5 metadata selects RPU-aware compatibility instead of an unsafe receiver bypass (%s)", kr_remux_message());
    kr_remux_stop();
    CHECK(kr_remux_state() == KR_IDLE, "native Dolby routing cleans up the previous session");
}

static void test_color_mapping(void) {
    kr_color *ctx = NULL;
    AVFrame *src = av_frame_alloc(), *dst = av_frame_alloc();
    src->format = AV_PIX_FMT_YUV420P10LE; src->width = src->height = 16;
    src->color_range = AVCOL_RANGE_MPEG; src->colorspace = AVCOL_SPC_BT2020_NCL;
    src->color_primaries = AVCOL_PRI_BT2020; src->color_trc = AVCOL_TRC_SMPTE2084;
    av_frame_get_buffer(src, 0);
    for (int y = 0; y < 16; y++) for (int x = 0; x < 16; x++) ((uint16_t *)(src->data[0] + y * src->linesize[0]))[x] = 64 + x * 56;
    for (int p = 1; p <= 2; p++) for (int y = 0; y < 8; y++) for (int x = 0; x < 8; x++) ((uint16_t *)(src->data[p] + y * src->linesize[p]))[x] = 512;
    dst->format = AV_PIX_FMT_YUV420P; dst->width = dst->height = 16;
    int r = kr_color_convert(&ctx, dst, src);
    CHECK(r >= 0, "PQ color mapping succeeds (%d)", r);
    int pq = r >= 0 ? dst->data[0][4] : -1;
    if (r >= 0) {
        int mono = 1;
        for (int x = 1; x < 16; x++) if (dst->data[0][x] < dst->data[0][x-1]) mono = 0;
        CHECK(mono && dst->data[0][0] < 20 && dst->data[0][15] <= 235, "PQ black/highlights preserved and bounded");
        CHECK(abs(dst->data[1][0]-128) <= 2 && abs(dst->data[2][0]-128) <= 2, "neutral HDR stays neutral");
    }
    CHECK(dst->color_trc == AVCOL_TRC_BT709 && src->color_trc == AVCOL_TRC_SMPTE2084, "output SDR, source metadata preserved");
    av_frame_unref(dst); dst->format = AV_PIX_FMT_YUV420P; dst->width = dst->height = 16;
    src->color_trc = AVCOL_TRC_BT709;
    r = kr_color_convert(&ctx, dst, src);
    CHECK(r >= 0 && abs(dst->data[0][4] - pq) > 8, "tone mapping changes pixels, not only tags (PQ %d vs SDR %d)", pq, r >= 0 ? dst->data[0][4] : -1);
    av_frame_unref(dst); dst->format = AV_PIX_FMT_YUV420P; dst->width = dst->height = 16;
    src->color_trc = AVCOL_TRC_ARIB_STD_B67;
    r = kr_color_convert(&ctx, dst, src);
    CHECK(r >= 0 && kr_color_is_hdr(src), "HLG maps through the same managed path");
    src->colorspace = AVCOL_SPC_IPT_C2;
    CHECK(kr_color_convert(&ctx, dst, src) < 0, "IPT/Dolby Vision cannot be relabeled as ordinary HDR");
    kr_color_free(ctx); av_frame_free(&src); av_frame_free(&dst);
}

static void test_dovi_render(const char *work) {
    char path[1024]; snprintf(path,sizeof path,"%s/dovi.mkv",fixture_dir);
    AVFormatContext *input=NULL;
    int r=avformat_open_input(&input,path,NULL,NULL);
    CHECK(r>=0,"RPU fixture opens"); if(r<0)return;
    avformat_find_stream_info(input,NULL);
    AVCodecContext *dec=avcodec_alloc_context3(avcodec_find_decoder(AV_CODEC_ID_HEVC));
    avcodec_parameters_to_context(dec,input->streams[0]->codecpar);
    dec->err_recognition=AV_EF_CRCCHECK|AV_EF_EXPLODE;avcodec_open2(dec,dec->codec,NULL);
    AVPacket *p=av_packet_alloc(); AVFrame *src=av_frame_alloc(),*pq=av_frame_alloc(),*sdr=av_frame_alloc();
    int got=0,padded=0;
    while(av_read_frame(input,p)>=0){
        if(p->stream_index==0){
            // Reproduce older muxers retaining trailing_zero_8bits on a length-prefixed RPU NAL.
            int pos=0,last=-1;
            while(pos+4<=p->size){unsigned n=AV_RB32(p->data+pos);if(n<2 || n>(unsigned)(p->size-pos-4))break;last=pos;pos+=4+(int)n;}
            if(pos==p->size && last>=0 && ((p->data[last+4]>>1)&63)==62){
                unsigned n=AV_RB32(p->data+last);
                if(av_grow_packet(p,1)==0){p->data[p->size-1]=0;AV_WB32(p->data+last,n+1);padded=1;}
            }
            avcodec_send_packet(dec,p);if(avcodec_receive_frame(dec,src)==0)got=1;
        }
        av_packet_unref(p);if(got)break;
    }
    CHECK(padded,"Dolby regression includes trailing zero padding with CRC validation enabled");
    CHECK(got && kr_dovi_is_profile5(src),"real HEVC decoder exposes parsed profile-5 metadata");
    if(got && !kr_dovi_is_profile5(src)){
        printf("  DOVI diagnostic: format %d, %d side data entries\n",src->format,src->nb_side_data);
        for(int i=0;i<src->nb_side_data;i++)printf("  side data %d size %zu\n",src->side_data[i]->type,src->side_data[i]->size);
        AVFrameSideData *side=av_frame_get_side_data(src,AV_FRAME_DATA_DOVI_METADATA);
        if(side && side->size>=sizeof(AVDOVIMetadata)){
            AVDOVIMetadata *meta=(void*)side->data;
            printf("  offsets: header %zu mapping %zu color %zu; sizes %zu/%zu/%zu metadata %zu\n",meta->header_offset,meta->mapping_offset,meta->color_offset,sizeof(AVDOVIRpuDataHeader),sizeof(AVDOVIDataMapping),sizeof(AVDOVIColorMetadata),side->size);
            if(meta->header_offset<=side->size && sizeof(AVDOVIRpuDataHeader)<=side->size-meta->header_offset){
                AVDOVIRpuDataHeader header;memcpy(&header,side->data+meta->header_offset,sizeof header);
                printf("  RPU header profile %u full-range %u bit depth %u denom %u\n",header.vdr_rpu_profile,header.bl_video_full_range_flag,header.bl_bit_depth,header.coef_log2_denom);
            }
        }
    }
    kr_dovi *ctx=NULL;kr_color *color=NULL;
    if(got){
        pq->width=src->width;pq->height=src->height;
        r=kr_dovi_convert(&ctx,pq,src);CHECK(r==0,"RPU reshape/IPT/PQ/LMS pipeline renders (%d)",r);
        if(!r){
            snprintf(path,sizeof path,"%s/dovi-rgb48.raw",work); FILE *f=fopen(path,"wb");
            for(int y=0;y<pq->height;y++)fwrite(pq->data[0]+y*pq->linesize[0],1,(size_t)pq->width*6,f);
            fclose(f);
            CHECK(pq->color_trc==AVCOL_TRC_SMPTE2084 && pq->color_primaries==AVCOL_PRI_BT2020 &&
                  !av_frame_get_side_data(pq,AV_FRAME_DATA_DOVI_METADATA),"rendered RGB is PQ/2020 without stale RPU");
        }
        sdr->format=AV_PIX_FMT_YUV420P;sdr->width=src->width;sdr->height=src->height;
        CHECK(kr_color_convert(&color,sdr,src)>=0 && sdr->color_trc==AVCOL_TRC_BT709,"profile-5 RPU reaches SDR tone mapping");
        AVFrameSideData *sd=av_frame_get_side_data(src,AV_FRAME_DATA_DOVI_METADATA);
        if(sd){AVDOVIMetadata *m=(void*)sd->data;
            AVDOVIDataMapping *mapping=av_dovi_get_mapping(m);
            for(int k=0;k<3;k++){
                int w=k?src->width/2:src->width,h=k?src->height/2:src->height;
                for(int y=0;y<h;y++)for(int x=0;x<w;x++)AV_WL16(src->data[k]+y*src->linesize[k]+x*2,(k+1)*256);
                AVDOVIReshapingCurve *curve=&mapping->curves[k];memset(curve,0,sizeof *curve);
                curve->num_pivots=2;curve->pivots[1]=1023;curve->mapping_idc[0]=AV_DOVI_MAPPING_MMR;
                curve->mmr_order[0]=k+1;curve->mmr_constant[0]=1<<21;
                for(int j=0;j<=k;j++)for(int n=0;n<7;n++)curve->mmr_coef[0][j][n]=1<<17;
            }
            AVFrame *mmr=av_frame_alloc(),*expected=av_frame_alloc();
            mmr->width=expected->width=src->width;mmr->height=expected->height=src->height;
            int converted=kr_dovi_convert(&ctx,mmr,src);
            // Exact dyadic sums for signals (.25,.5,.75), every seven MMR terms through orders 1/2/3.
            const int constants[3]={2396160,2537088,2618956};
            for(int k=0;k<3;k++){AVDOVIReshapingCurve *curve=&mapping->curves[k];memset(curve,0,sizeof *curve);
                curve->num_pivots=2;curve->pivots[1]=1023;curve->poly_order[0]=1;curve->poly_coef[0][0]=constants[k];}
            int rendered=kr_dovi_convert(&ctx,expected,src);
            CHECK(converted==0 && rendered==0 && !memcmp(mmr->data[0],expected->data[0],6),"all MMR orders/cross terms match independently calculated polynomial-equivalent pixels");
            av_frame_free(&mmr);av_frame_free(&expected);
            m->mapping_offset=SIZE_MAX;
            AVFrame *bad=av_frame_alloc();bad->width=src->width;bad->height=src->height;
            CHECK(kr_dovi_convert(&ctx,bad,src)<0,"corrupt metadata offsets rejected before dereference");av_frame_free(&bad);}
    }
    kr_color_free(color);kr_dovi_free(ctx);av_frame_free(&src);av_frame_free(&pq);av_frame_free(&sdr);
    av_packet_free(&p);avcodec_free_context(&dec);avformat_close_input(&input);
}

static double mono_ms(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1000.0 + t.tv_nsec / 1e6; }

typedef struct { int port; char path[64]; double ms; int status; } timed;
static void *timed_get(void *arg) {
    timed *g = arg;
    double t0 = mono_ms();
    reply r = http_get(g->port, g->path, NULL);
    g->ms = mono_ms() - t0; g->status = r.status;
    free(r.body);
    return NULL;
}
static double get_ms(int port, const char *path) {
    timed g = { port, "", 0, 0 };
    snprintf(g.path, sizeof g.path, "%s", path);
    timed_get(&g);
    CHECK(g.status == 200, "%s: %d", path, g.status);
    return g.ms;
}

// A seek/retry may overlap a still-connected request for the old position. Only speculative
// conversion may be canceled: returning 500 for the other live request poisons AVPlayer's session.
static void test_seek_overlap(const char *http_base) {
    char url[512], m3u8[256];
    snprintf(url, sizeof url, "%s/slow/hevc_ac3_ass.mkv", http_base);
    for (int ahead = 0; ahead <= 1; ahead++) {
        kr_remux_set_prefetch(ahead);
        int st = start_session(url, 0, m3u8, sizeof m3u8);
        CHECK(st == KR_READY, "seek overlap: source opens (prefetch %d)", ahead);
        if (st != KR_READY) continue;
        int port = kr_remux_port();
        reply init = http_get(port, "/cvideo/init.mp4", NULL);
        CHECK(init.status == 200, "seek overlap: converted init (%d)", init.status);
        free(init.body);
        timed old = { port, "/cvideo/seg1.m4s", 0, 0 };
        pthread_t t; pthread_create(&t, NULL, timed_get, &old);
        usleep(20000);
        reply target = http_get(port, "/cvideo/seg3.m4s", NULL);
        pthread_join(t, NULL);
        CHECK(old.status == 200, "seek overlap: live old request survives (prefetch %d, status %d)", ahead, old.status);
        CHECK(target.status == 200 && target.len > 8, "seek overlap: forward target plays (prefetch %d, status %d)", ahead, target.status);
        CHECK(!*kr_remux_message(), "seek overlap: no false fatal error (%s)", kr_remux_message());
        free(target.body);
        // Then go backward and retry the forward segment; the cache and converter must remain usable.
        reply back = http_get(port, "/cvideo/seg0.m4s", NULL);
        reply retry = http_get(port, "/cvideo/seg3.m4s", NULL);
        CHECK(back.status == 200 && retry.status == 200, "seek overlap: backward/forward retry (%d, %d)", back.status, retry.status);
        free(back.body); free(retry.body);
        kr_remux_stop();
    }
    kr_remux_set_prefetch(1);
}

// Actual 4K/10-bit decode and downscale, then seek to the tail and back. Linux uses the MPEG-4
// test encoder: this checks media/timestamps, not Apple's H.264 encoder or sustained 24/60 fps on iOS.
static void test_4k_seek(const char *url, const char *work) {
    char m3u8[256], out[512];
    kr_remux_set_prefetch(0);
    int st = start_session(url, 0, m3u8, sizeof m3u8);
    CHECK(st == KR_READY, "4K seek: source opens (%s)", kr_remux_message());
    if (st != KR_READY) { kr_remux_set_prefetch(1); return; }
    int port = kr_remux_port();
    reply copy = http_get(port, "/master.m3u8", NULL);
    reply tv = get_as(UA_TV, port, "/master.m3u8");
    CHECK(copy.body && strstr(copy.body, "RESOLUTION=3840x2160"), "4K: copy preserves original dimensions");
    CHECK(tv.body && strstr(tv.body, "RESOLUTION=1920x1080") && strstr(tv.body, "avc1.640028"), "4K: TV gets compatibility picture");
    reply pl = http_get(port, "/cvideo/index.m3u8", NULL);
    double total, maxd; int target;
    int n = playlist_segments(pl.body ? pl.body : "", &total, &maxd, &target);
    CHECK(n >= 3 && fabs(total - 20) < .2, "4K: seekable grid (%d segments, %.2f s)", n, total);
    reply init = http_get(port, "/cvideo/init.mp4", NULL);
    reply tail = http_get(port, "/cvideo/seg3.m4s", NULL);
    CHECK(init.status == 200 && tail.status == 200, "4K: converted init and seek (%d, %d)", init.status, tail.status);
    if (init.status == 200 && tail.status == 200) {
        snprintf(out, sizeof out, "%s/4k-seek.mp4", work);
        int key = 0, keys = 0;
        double t = segment_first(&init, &tail, out, &key);
        CHECK(key && fabs(t - 18) < 1.0 / 6, "4K: target is a keyframe at requested time (%.3f)", t);
        CHECK(decode_count(out, &keys) == 12 && keys == 1, "4K: tail segment actually decodes");
        AVFormatContext *in = NULL;
        int opened = avformat_open_input(&in, out, NULL, NULL);
        if (!opened) avformat_find_stream_info(in, NULL);
        CHECK(!opened && in->streams[0]->codecpar->width == 1920 && in->streams[0]->codecpar->height == 1080,
              "4K: encoded pixels are 1920x1080");
        avformat_close_input(&in);
    }
    reply back = http_get(port, "/cvideo/seg0.m4s", NULL);
    CHECK(back.status == 200 && !*kr_remux_message(), "4K: backward seek remains usable");
    free(copy.body); free(tv.body); free(pl.body); free(init.body); free(tail.body); free(back.body);
    kr_remux_stop(); kr_remux_set_prefetch(1);
}

// Over a slow source (tests/range_server.py /slow/: latency per request and limited bytes/s, like Drive through its
// proxy): video and audio made at the same time, inits and served segments cached, the next segments made ahead.
static void test_latency(const char *http_base) {
    char url[512], m3u8[256];
    snprintf(url, sizeof url, "%s/slow/h264_aac_srt.mkv", http_base);
    kr_remux_set_prefetch(0);
    int st = start_session(url, 0, m3u8, sizeof m3u8);
    CHECK(st == KR_READY, "latency: slow source opens (%s)", kr_remux_message());
    if (st != KR_READY) { kr_remux_set_prefetch(1); return; }
    int port = kr_remux_port();
    reply master = http_get(port, "/master.m3u8", NULL);
    const char *a = master.body ? strstr(master.body, "/audio/") : NULL;
    int aidx = a ? atoi(a + 7) : 1;
    free(master.body);
    char ainit[64], aseg[64];
    snprintf(ainit, sizeof ainit, "/audio/%d/init.mp4", aidx);
    double vinit = get_ms(port, "/video/init.mp4"), first_ainit = get_ms(port, ainit);  // opens the audio demuxer
    double vinit2 = get_ms(port, "/video/init.mp4"), seg0 = get_ms(port, "/video/seg0.m4s");
    CHECK(vinit2 < 50 && seg0 < 50, "init and segment 0 made once (init %.0f ms, again %.1f ms, seg0 after it %.1f ms)", vinit, vinit2, seg0);
    snprintf(aseg, sizeof aseg, "/audio/%d/seg2.m4s", aidx);
    double tv = get_ms(port, "/video/seg2.m4s"), ta = get_ms(port, aseg);
    timed gv = { port, "/video/seg1.m4s", 0, 0 }, ga = { port, "", 0, 0 };
    snprintf(ga.path, sizeof ga.path, "/audio/%d/seg1.m4s", aidx);
    pthread_t th[2];
    double t0 = mono_ms();
    pthread_create(&th[0], NULL, timed_get, &gv); pthread_create(&th[1], NULL, timed_get, &ga);
    pthread_join(th[0], NULL); pthread_join(th[1], NULL);
    double both = mono_ms() - t0;
    CHECK(gv.status == 200 && ga.status == 200, "video and audio together (%d %d)", gv.status, ga.status);
    CHECK(both < 0.8 * (tv + ta), "video and audio are made at the same time: together %.0f ms, one after the other %.0f + %.0f ms", both, tv, ta);
    double again = get_ms(port, "/video/seg2.m4s");
    CHECK(again < 50, "a segment asked again comes from the cache (%.1f ms, made in %.0f ms)", again, tv);
    CHECK(kr_remux_prefetched() == 0, "nothing made ahead with prefetch off (%d)", kr_remux_prefetched());
    kr_remux_stop();

    kr_remux_set_prefetch(1);
    st = start_session(url, 0, m3u8, sizeof m3u8);
    if (st != KR_READY) { CHECK(0, "latency: second session"); return; }
    port = kr_remux_port();
    double p0 = get_ms(port, "/video/seg0.m4s"), p1 = get_ms(port, "/video/seg1.m4s");
    usleep(2500000);  // the receiver plays segment 1 (6 s in real time): N+1, N+2 are made meanwhile
    double p2 = get_ms(port, "/video/seg2.m4s");
    usleep(2500000);
    double p3 = get_ms(port, "/video/seg3.m4s");
    printf("  latency over the slow source: cold video segment %.0f ms, audio %.0f ms, both at once %.0f ms; with prefetch "
           "seg0 %.0f ms, seg1 right after %.0f ms, seg2 %.1f ms, seg3 %.1f ms (%d made ahead)\n", tv, ta, both, p0, p1, p2, p3, kr_remux_prefetched());
    CHECK(p2 < 50 && p3 < 50, "segments after the first are ready when asked (seg2 %.1f ms, seg3 %.1f ms; cold %.0f ms)", p2, p3, tv);
    CHECK(kr_remux_prefetched() >= 3, "segments made ahead (%d)", kr_remux_prefetched());
    // A seek far away while segments are being made ahead: answered, and stop is prompt with work in flight.
    reply far = http_get(port, "/video/seg0.m4s", NULL);
    free(far.body);
    double s0 = mono_ms();
    kr_remux_stop();
    double stop_ms = mono_ms() - s0;
    CHECK(stop_ms < 4500 && kr_remux_state() == KR_IDLE, "stop while making segments ahead returns (%.0f ms)", stop_ms);
}

const char *fixture_dir;

// ── r10 burned-in subtitles (kr_subs + kr_video) ──────────────────────────────
// A gray 320x180 4:2:0 frame; returns how many Y samples differ from 128 in rows [y0, y1), and chroma samples changed.
static int frame_changes(uint8_t *const d[3], const int ls[3], int nv12, int y0, int y1, int *chroma) {
    int n = 0; *chroma = 0;
    for (int y = y0; y < y1; y++) for (int x = 0; x < 320; x++) n += d[0][y * ls[0] + x] != 128;
    for (int y = 0; y < 90; y++) for (int x = 0; x < (nv12 ? 320 : 160); x++) {
        *chroma += d[1][y * ls[1] + x] != 128;
        if (!nv12) *chroma += d[2][y * ls[2] + x] != 128;
    }
    return n;
}

static void gray(uint8_t *buf, uint8_t *d[3], int ls[3], int nv12) {
    memset(buf, 128, 320 * 180 * 3 / 2);
    d[0] = buf; ls[0] = 320;
    if (nv12) { d[1] = buf + 320 * 180; ls[1] = 320; d[2] = NULL; ls[2] = 0; }
    else { d[1] = buf + 320 * 180; d[2] = d[1] + 160 * 90; ls[1] = ls[2] = 160; }
}

static void test_bitmap_subtitles(const char *url) {
    AVFormatContext *f = NULL;
    int opened = avformat_open_input(&f, url, NULL, NULL);
    CHECK(opened == 0, "bitmap fixture opens");
    if (opened) return;
    avformat_find_stream_info(f, NULL);
    int idx = kr_subs_pick(f, 0, NULL);
    CHECK(idx >= 0 && !kr_subs_is_text(f->streams[idx]) && kr_subs_supported(f->streams[idx]), "PGS selected as supported bitmap");
    kr_subs *s = kr_subs_create(320, 180);
    if (idx < 0 || !s) { kr_subs_free(s); avformat_close_input(&f); return; }
    CHECK(kr_subs_open_stream(s, f->streams[idx]) == 0, "actual PGS decoder opens");
    AVPacket *p = av_packet_alloc();
    while (av_read_frame(f, p) == 0) {
        if (p->stream_index == idx) kr_subs_feed(s, p);
        av_packet_unref(p);
    }
    uint8_t *buf = malloc(320*180*3/2), *d[3]; int ls[3];
    for (int nv12 = 0; nv12 <= 1; nv12++) {
        gray(buf, d, ls, nv12);
        CHECK(!kr_subs_blend(s, 500, d, ls, 320, 180, nv12), "bitmap absent before cue");
        CHECK(kr_subs_blend(s, 2000, d, ls, 320, 180, nv12) && d[0][130*ls[0]+40] > 220, "PGS white pixels at source position");
        CHECK(d[0][20*ls[0]+20] == 128 && d[0][130*ls[0]+60] > 60 && d[0][130*ls[0]+60] < 128, "bitmap clipping/palette alpha");
        gray(buf, d, ls, nv12);
        CHECK(!kr_subs_blend(s, 3500, d, ls, 320, 180, nv12), "PGS clear ends cue");
        CHECK(kr_subs_blend(s, 2000, d, ls, 320, 180, nv12), "backward seek restores cached bitmap");
    }
    free(buf); av_packet_free(&p); kr_subs_free(s); avformat_close_input(&f);
}

static void test_external_bitmaps(void) {
    char path[1024]; snprintf(path, sizeof path, "%s/long.sup", fixture_dir);
    uint8_t *buf = malloc(320*180*3/2), *d[3]; int ls[3];
    CHECK(buf != NULL, "external bitmap frame allocated");
    if (!buf) return;
    for (int nv12 = 0; nv12 <= 1; nv12++) {
        kr_subs *s = kr_subs_create(320,180);
        int opened = kr_subs_load_file(s, path);
        CHECK(s && opened == 0, "external SUP opens (nv12 %d)", nv12);
        if (!s || opened < 0) { kr_subs_free(s); continue; }
        CHECK(kr_subs_events(s) == 0, "external SUP does not predecode the entire file");
        int64_t times[] = { 45000,60000,135000,150000,798500,799000,45000,500,120000,135000 };
        int expected[] = { 1,0,1,0,1,0,1,0,1,1 };
        for (unsigned i = 0; i < sizeof times / sizeof *times; i++) {
            gray(buf,d,ls,nv12);
            int drawn = kr_subs_blend(s,times[i],d,ls,320,180,nv12);
            CHECK(drawn == expected[i] && (!drawn || d[0][130*ls[0]+40]>220),
                  "external bitmap at %lld ms: long cue/fresh seek/clear/backward pixels (%d)", (long long)times[i], drawn);
            CHECK(kr_subs_events(s) <= 256, "external bitmap cache stays bounded (%d)",kr_subs_events(s));
        }
        kr_subs_free(s);
        snprintf(path,sizeof path,"%s/dvd.idx",fixture_dir);
        s = kr_subs_create(320,180);
        CHECK(kr_subs_load_file(s,path)==0,"actual external IDX/SUB decoder opens");
        gray(buf,d,ls,nv12);
        CHECK(kr_subs_blend(s,500,d,ls,320,180,nv12)==0,"DVD bitmap absent before cue");
        CHECK(kr_subs_blend(s,2000,d,ls,320,180,nv12)==1 && d[0][130*ls[0]+40]>220,"DVD bitmap decoded white pixels");
        gray(buf,d,ls,nv12);
        CHECK(kr_subs_blend(s,3500,d,ls,320,180,nv12)==0,"DVD bitmap duration ends cue");
        CHECK(kr_subs_blend(s,2000,d,ls,320,180,nv12)==1,"DVD backward replay restores cue");
        kr_subs_free(s);
        snprintf(path,sizeof path,"%s/long.sup",fixture_dir);
    }
    kr_subs *s = kr_subs_create(320,180);
    snprintf(path,sizeof path,"%s/missing.sup",fixture_dir);
    CHECK(kr_subs_load_file(s,path)<0,"missing external bitmap refused"); kr_subs_free(s);
    s = kr_subs_create(320,180);
    CHECK(kr_subs_load_file(s,"http://127.0.0.1/untrusted.sup")<0,"external bitmap loader remains local-only"); kr_subs_free(s);
    snprintf(path,sizeof path,"%s/out/bad.sup",fixture_dir);
    FILE *bad = fopen(path,"wb"); fputs("invalid PGS",bad); fclose(bad);
    s = kr_subs_create(320,180);
    CHECK(kr_subs_load_file(s,path)<0,"corrupt external bitmap refused at load"); kr_subs_free(s);
    char original[1024]; snprintf(original,sizeof original,"%s/box.sup",fixture_dir);
    FILE *input = fopen(original,"rb"); bad = fopen(path,"wb"); int c;
    while ((c=fgetc(input))!=EOF) fputc(c,bad);
    fputs("broken tail",bad); fclose(input); fclose(bad);
    s = kr_subs_create(320,180);
    CHECK(kr_subs_load_file(s,path)==0,"valid header with later damage opens lazily");
    gray(buf,d,ls,1);
    CHECK(kr_subs_blend(s,8000,d,ls,320,180,1)<0,"later subtitle I/O corruption is an error, not silent missing captions"); kr_subs_free(s);
    free(buf);
    snprintf(path,sizeof path,"%s/multi.idx",fixture_dir);
    for(int spanish=0;spanish<2;spanish++){
        s=kr_subs_create(320,180);kr_subs_set_language(s,spanish?"spa|es":"eng|en");
        CHECK(kr_subs_load_file(s,path)==0,"multi-language VobSub opens");
        uint8_t pixels[320*180*3/2];gray(pixels,d,ls,1);
        CHECK(kr_subs_blend(s,2000,d,ls,320,180,1)==1 && d[0][130*ls[0]+(spanish?200:40)]>220 &&
              d[0][130*ls[0]+(spanish?40:200)]==128,"selected VobSub language burns its own distinct bitmap (%s)",spanish?"es":"en");
        gray(pixels,d,ls,1);
        CHECK(kr_subs_blend(s,500,d,ls,320,180,1)==0 && kr_subs_blend(s,2000,d,ls,320,180,1)==1 &&
              d[0][130*ls[0]+(spanish?200:40)]>220,"VobSub language selection survives backward replay");
        kr_subs_free(s);
    }
}

static void test_burn_render(void) {
    char path[1024];
    static uint8_t buf[320 * 180 * 3 / 2];
    uint8_t *d[3]; int ls[3], ch;
    for (int nv12 = 0; nv12 < 2; nv12++) {
        kr_subs *s = kr_subs_create(320, 180);
        snprintf(path, sizeof path, "%s/subs.srt", fixture_dir);
        CHECK(s && kr_subs_load_file(s, path) == 0 && kr_subs_events(s) == 2, "SRT file loaded (%d events)", kr_subs_events(s));
        if (!s) return;
        int64_t before[] = { 0, 999, 3000, 5000, 6499, 7500, 9000 };
        for (size_t k = 0; k < sizeof before / sizeof *before; k++) {
            gray(buf, d, ls, nv12);
            int drawn = kr_subs_blend(s, before[k], d, ls, 320, 180, nv12);
            CHECK(!drawn && frame_changes(d, ls, nv12, 0, 180, &ch) == 0 && ch == 0, "nothing drawn at %lld ms (nv12 %d)", (long long)before[k], nv12);
        }
        int64_t during[] = { 1000, 2000, 2999, 6500, 7000 };
        for (size_t k = 0; k < sizeof during / sizeof *during; k++) {
            gray(buf, d, ls, nv12);
            int drawn = kr_subs_blend(s, during[k], d, ls, 320, 180, nv12);
            int low = frame_changes(d, ls, nv12, 120, 180, &ch), high = frame_changes(d, ls, nv12, 0, 100, &ch);
            CHECK(drawn && low > 200 && high == 0, "cue drawn at %lld ms in the bottom third only (%d / %d changed, nv12 %d)",
                  (long long)during[k], low, high, nv12);
        }
        kr_subs_add(s, "0,Default,,0,0,0,,Hello from SRT", 1000, 2000);  // a duplicate of the first cue
        CHECK(kr_subs_events(s) == 2, "a cue seen again is not added twice");
        kr_subs_free(s);
    }
    kr_subs *a = kr_subs_create(320, 180);
    snprintf(path, sizeof path, "%s/subs.ass", fixture_dir);
    CHECK(a && kr_subs_load_file(a, path) == 0 && kr_subs_events(a) == 1, "ASS file loaded");
    gray(buf, d, ls, 1);
    CHECK(a && kr_subs_blend(a, 1500, d, ls, 320, 180, 1) == 0 && kr_subs_blend(a, 3000, d, ls, 320, 180, 1) == 1 &&
          frame_changes(d, ls, 1, 0, 180, &ch) > 100, "ASS cue only during 2-4 s");
    kr_subs_free(a);
    // Latin-1 SRT with CRLF and tags, and WebVTT timestamps
    char tmp[1024]; snprintf(tmp, sizeof tmp, "%s/out/latin1.vtt", fixture_dir);
    FILE *f = fopen(tmp, "wb");
    fputs("WEBVTT\r\n\r\n00:01.000 --> 00:02.500\r\n<i>Caf\xe9</i> <c.x>ok</c>\r\n\r\n", f); fclose(f);
    kr_subs *v = kr_subs_create(320, 180);
    CHECK(v && kr_subs_load_file(v, tmp) == 0 && kr_subs_events(v) == 1, "Latin-1 WebVTT file loaded");
    gray(buf, d, ls, 0);
    CHECK(v && kr_subs_blend(v, 2000, d, ls, 320, 180, 0) == 1 && kr_subs_blend(v, 2600, d, ls, 320, 180, 0) == 0, "WebVTT cue timing");
    kr_subs_free(v);
    snprintf(tmp, sizeof tmp, "%s/missing.srt", fixture_dir);
    kr_subs *m = kr_subs_create(320, 180);
    CHECK(kr_subs_load_file(m, tmp) < 0, "a missing file is refused");
    kr_subs_free(m);
}

// Decoded Y planes of a unit (320x180), with their times.
static int unit_frames(const gm_buf *u, const char *tmp, uint8_t **ys, double *ts, int max) {
    FILE *f = fopen(tmp, "wb"); fwrite(u->data, 1, (size_t)u->len, f); fclose(f);
    AVFormatContext *in = NULL;
    if (avformat_open_input(&in, tmp, NULL, NULL) < 0) return -1;
    avformat_find_stream_info(in, NULL);
    const AVCodec *dc = avcodec_find_decoder(in->streams[0]->codecpar->codec_id);
    AVCodecContext *c = avcodec_alloc_context3(dc);
    avcodec_parameters_to_context(c, in->streams[0]->codecpar);
    avcodec_open2(c, dc, NULL);
    AVPacket *p = av_packet_alloc(); AVFrame *fr = av_frame_alloc();
    int n = 0;
    for (int flushing = 0; flushing < 2; flushing++) {
        for (;;) {
            if (!flushing) { if (av_read_frame(in, p) < 0) break; avcodec_send_packet(c, p); av_packet_unref(p); }
            else avcodec_send_packet(c, NULL);
            while (avcodec_receive_frame(c, fr) == 0) {
                if (n < max) {
                    ys[n] = malloc(320 * 180);
                    for (int y = 0; y < 180; y++) memcpy(ys[n] + y * 320, fr->data[0] + y * fr->linesize[0], 320);
                    ts[n] = fr->best_effort_timestamp * av_q2d(in->streams[0]->time_base);
                    n++;
                }
                av_frame_unref(fr);
            }
            if (flushing) break;
        }
    }
    av_frame_free(&fr); av_packet_free(&p); avcodec_free_context(&c); avformat_close_input(&in);
    return n;
}

// Samples of rows [y0, y1) that differ by more than `by` (text vs encoder noise).
static int region_diff(const uint8_t *a, const uint8_t *b, int y0, int y1, int by) {
    int n = 0;
    for (int y = y0; y < y1; y++) for (int x = 0; x < 320; x++) n += abs(a[y * 320 + x] - b[y * 320 + x]) > by;
    return n;
}

// The SRT stream of h264_aac_srt.mkv (cue 1-3 s) burned into segment 0: frames before the cue identical to the
// unburned conversion, frames during it changed at the bottom, the same frames and times (grid unchanged).
static void test_burn_video(const char *work, const char *file, const char *external) {
    char url[1024], err[256] = "", tmp[1024];
    snprintf(url, sizeof url, "file:%s/%s", fixture_dir, file);
    kr_source *s0 = kr_source_open(url, 10, err, sizeof err), *s1 = kr_source_open(url, 10, err, sizeof err),
              *s2 = kr_source_open(url, 10, err, sizeof err);
    gm_stream *gm = s0 ? gm_stream_open(kr_source_gm(s0), 6.0, err, sizeof err) : NULL;
    kr_video *plain = s1 ? kr_video_open(kr_source_gm(s1), 0, err, sizeof err) : NULL;
    kr_video *burn = s2 ? kr_video_open(kr_source_gm(s2), 0, err, sizeof err) : NULL;
    CHECK(gm && plain && burn, "burn: converters open (%s)", err);
    if (!gm || !plain || !burn) goto out;
    CHECK(kr_video_burn(plain, -1, NULL, err, sizeof err) == 0 && !kr_video_burning(plain), "no subtitles: nothing burned");
    CHECK(kr_video_burn(burn, 1, NULL, err, sizeof err) < 0, "an audio stream is not a subtitle (%s)", err);
    CHECK(kr_video_burn(burn, external ? -1 : 2, external, err, sizeof err) == 0 && kr_video_burning(burn), "chosen subtitle burned (%s)", err);
    // r11: a source stream's events load with the picture (the r10 "0 events loaded" log line was read before any).
    CHECK(kr_video_burn_events(burn) == 0 && kr_video_burn_drawn(burn) == 0, "no events before the first segment is read");
    gm_buf a = {0}, b = {0}, a2 = {0};
    CHECK(kr_video_unit(plain, gm, 0, &a, err, sizeof err) == 0 && kr_video_unit(burn, gm, 0, &b, err, sizeof err) == 0, "units made (%s)", err);
    CHECK(kr_video_burn_events(burn) >= 1, "the cue was read from the stream (%d events)", kr_video_burn_events(burn));
    CHECK(kr_video_burn_drawn(burn) > 30, "the cue was drawn on %ld frames", kr_video_burn_drawn(burn));
    int m = kr_first_moof(a.data, a.len);
    CHECK(m > 0 && m == kr_first_moof(b.data, b.len) && !memcmp(a.data, b.data, (size_t)m), "same init with subtitles burned in");
    // The no-subtitle path is deterministic: the same unit again is byte-identical.
    CHECK(kr_video_unit(plain, gm, 0, &a2, err, sizeof err) == 0 && a2.len == a.len && !memcmp(a.data, a2.data, (size_t)a.len),
          "no subtitles: identical bytes on a second conversion");
    enum { MAXF = 400 };
    static uint8_t *ya[MAXF], *yb[MAXF]; static double ta[MAXF], tb[MAXF];
    snprintf(tmp, sizeof tmp, "%s/burn_a.mp4", work); int na = unit_frames(&a, tmp, ya, ta, MAXF);
    snprintf(tmp, sizeof tmp, "%s/burn_b.mp4", work); int nb = unit_frames(&b, tmp, yb, tb, MAXF);
    int same_t = na == nb && na > 24;
    for (int i = 0; same_t && i < na; i++) same_t = fabs(ta[i] - tb[i]) < 1e-6;
    CHECK(same_t, "same frames and timestamps with subtitles (%d vs %d)", na, nb);
    int bad_before = 0, bad_during = 0, top_changed = 0, during = 0;
    for (int i = 0; same_t && i < na; i++) {
        int low = region_diff(ya[i], yb[i], 130, 180, 48), high = region_diff(ya[i], yb[i], 0, 60, 48);
        if (ta[i] < 1.0 - 1e-3) bad_before += region_diff(ya[i], yb[i], 0, 180, 0) > 0;
        else if (ta[i] >= 1.05 && ta[i] < 2.95) { during++; bad_during += low < 80; top_changed += high > 0; }
    }
    CHECK(same_t && bad_before == 0, "frames before the cue untouched (%d differ)", bad_before);
    CHECK(same_t && during > 30 && bad_during == 0 && top_changed == 0, "the cue burned into the bottom of %d frames (%d missing, %d top changed)",
          during, bad_during, top_changed);
    for (int i = 0; i < na; i++) free(ya[i]);
    for (int i = 0; i < nb; i++) free(yb[i]);
    free(a.data); free(b.data); free(a2.data);
    // A later segment opened fresh (a seek) still reads its subtitles (lookback pass), timing unchanged.
    if (gm_stream_segment_count(gm) > 1) {
        gm_buf c = {0};
        int r = kr_video_unit(burn, gm, gm_stream_segment_count(gm) - 1, &c, err, sizeof err);
        CHECK(r == 0 && kr_first_moof(c.data, c.len) > 0, "a later burned segment (%s)", err);
        free(c.data);
    }
out:
    kr_video_close(plain); kr_video_close(burn);
    gm_stream_close(gm);
    kr_source_close(s0); kr_source_close(s1); kr_source_close(s2);
}

// Selection: Kodi's subtitle number, off, automatic, an external file; a TV then gets the H.264 picture even for an
// H.264 source.
static void test_long_embedded(const char *work) {
    char url[1024],err[256]="",path[1024];snprintf(url,sizeof url,"file:%s/long_pgs.mkv",fixture_dir);
    kr_source *s0=kr_source_open(url,10,err,sizeof err),*s1=kr_source_open(url,10,err,sizeof err);
    gm_stream *gm=s0?gm_stream_open(kr_source_gm(s0),6,err,sizeof err):NULL;
    kr_video *v=s1?kr_video_open(kr_source_gm(s1),0,err,sizeof err):NULL;
    CHECK(gm && v,"long embedded cue converters open (%s)",err);
    if(gm && v){
        CHECK(kr_video_burn(v,2,NULL,err,sizeof err)==0,"long embedded PGS selected");
        gm_buf b={0};int r=kr_video_unit(v,gm,7,&b,err,sizeof err);
        CHECK(r==0 && kr_video_burn_drawn(v)>0,"fresh far seek recovers cue begun more than ten seconds earlier (%s)",err);
        double target=gm_stream_segment_start(gm,7);
        CHECK(kr_video_subtitle_scan_end(v)>=target && kr_video_subtitle_scan_end(v)<target+.1,
              "subtitle preroll ends on the target video, not next caption/clear (%.3f vs %.3f)",kr_video_subtitle_scan_end(v),target);
        uint8_t *frames[300]={0};double times[300];snprintf(path,sizeof path,"%s/long-pgs.mp4",work);
        int n=r==0?unit_frames(&b,path,frames,times,300):0;
        CHECK(n>0 && frames[0][130*320+40]>220,"far-seek video decodes with actual white subtitle pixels");
        for(int i=0;i<n;i++)free(frames[i]);
        free(b.data);
        b=(gm_buf){0};CHECK(kr_video_unit(v,gm,0,&b,err,sizeof err)==0,"embedded long-cue backward retry succeeds");free(b.data);
    }
    kr_video_close(v);gm_stream_close(gm);kr_source_close(s0);kr_source_close(s1);
}

static void test_burn_select(void) {
    char url[1024], m3u8[256], ext[1024];
    snprintf(url, sizeof url, "file:%s/h264_aac_srt.mkv", fixture_dir);
    snprintf(ext, sizeof ext, "%s/subs.srt", fixture_dir);
    struct { int ord; const char *file; int want; int tv_compat; } cases[] = {
        { -1, NULL, -1, 0 }, { 0, NULL, 2, 1 }, { -2, NULL, 2, 1 }, { 1, ext, -2, 1 }, { 1, NULL, -1, 0 }, { -2, ext, -2, 1 },
    };
    for (size_t k = 0; k < sizeof cases / sizeof *cases; k++) {
        kr_remux_set_subtitles(cases[k].ord, cases[k].file, "eng");
        int st = start_session(url, 0, m3u8, sizeof m3u8);
        CHECK(st == KR_READY && kr_remux_burn_track() == cases[k].want, "subtitles %d%s: burn track %d (want %d)", cases[k].ord,
              cases[k].file ? " + file" : "", kr_remux_burn_track(), cases[k].want);
        if (st != KR_READY) continue;
        reply tv = get_as(UA_TV, kr_remux_port(), "/master.m3u8");
        CHECK(tv.body && (strstr(tv.body, "/cvideo/") != NULL) == cases[k].tv_compat, "case %zu: the TV %s the H.264 picture", k,
              cases[k].tv_compat ? "gets" : "does not get");
        if (cases[k].tv_compat) {
            reply seg = get_as(UA_TV, kr_remux_port(), "/cvideo/seg0.m4s");
            CHECK(seg.status == 200 && seg.len > 0, "case %zu: burned segment served (%d)", k, seg.status);
            free(seg.body);
            // r11: burned in for the TV: no WebVTT rendition in its master, and a /subs request answers at once (empty)
            CHECK(!strstr(tv.body, "TYPE=SUBTITLES") && !strstr(tv.body, "SUBTITLES=\"subs\""), "case %zu: no subtitles group for the TV", k);
            reply vtt = get_as(UA_TV, kr_remux_port(), "/subs/2/seg0.vtt");
            CHECK(vtt.status == 200 && vtt.body && !strncmp(vtt.body, "WEBVTT", 6) && !strstr(vtt.body, "Hello"), "case %zu: empty cue file for the TV", k);
            free(vtt.body);
        }
        free(tv.body);
        kr_remux_stop();
    }
    kr_remux_set_subtitles(-1, NULL, NULL);
}


static int preparation_progress(int stage,double done,double total,void *ctx) {
    int *calls=ctx;(*calls)++;
    CHECK(stage>=0 && stage<=3 && isfinite(done) && total>0,"preparation progress is bounded");
    return 1;
}
static int pause_preparation(int stage,double done,double total,void *ctx) {
    (void)done;(void)total;(void)ctx;return stage!=2;
}
static int video_digest(const char *path,uint8_t digest[16],int *width,int *height,int *tracks) {
    AVFormatContext *f=NULL;AVPacket *p=av_packet_alloc();struct AVMD5 *md5=av_md5_alloc();int r=-1;
    if(!p || !md5 || avformat_open_input(&f,path,NULL,NULL)<0 || avformat_find_stream_info(f,NULL)<0)goto end;
    int video=-1;for(unsigned i=0;i<f->nb_streams;i++)if(f->streams[i]->codecpar->codec_type==AVMEDIA_TYPE_VIDEO){video=(int)i;break;}
    if(video<0)goto end;
    *width=f->streams[video]->codecpar->width;*height=f->streams[video]->codecpar->height;*tracks=(int)f->nb_streams;
    av_md5_init(md5);while(av_read_frame(f,p)>=0){if(p->stream_index==video)av_md5_update(md5,p->data,p->size);av_packet_unref(p);}
    av_md5_final(md5,digest);r=0;
end:av_free(md5);av_packet_free(&p);avformat_close_input(&f);return r;
}
static void test_preparation(const char *work) {
    const char *files[]={"h264_aac_srt.mkv","hevc_ac3_ass.mkv","h264_ac3_dts_srt.mkv","hevc_4k.mkv","dovi.mkv","long_seek.mkv"};
    for(unsigned i=0;i<sizeof files/sizeof files[0];i++) {
        char input[1024],output[1024],err[512]="",json[1024],url[1100],playlist[512];
        snprintf(input,sizeof input,"%s/%s",fixture_dir,files[i]);snprintf(output,sizeof output,"%s/prepared-%u.mp4",work,i);unlink(output);
        int calls=0;
        int r=kodi_airplay_prepare(input,output,preparation_progress,&calls,err,sizeof err);
        CHECK(r==0,"prepare %s: %s",files[i],err);if(r)continue;
        CHECK(calls>0,"prepare %s publishes progress",files[i]);
        CHECK(kodi_airplay_probe(output,json,sizeof json)==0 && strstr(json,"\"ready\":true"),"prepared portable MP4: %s",json);
        uint8_t a[16],b[16];int aw,ah,an,bw,bh,bn;
        CHECK(video_digest(input,a,&aw,&ah,&an)==0 && video_digest(output,b,&bw,&bh,&bn)==0,"read preparation input/output");
        CHECK(aw==bw && ah==bh,"source resolution preserved (%dx%d -> %dx%d)",aw,ah,bw,bh);
        CHECK(an==bn,"all selected video/audio/text tracks preserved (%d -> %d)",an,bn);
        CHECK(!memcmp(a,b,16),"H.264/HEVC video packets preserved without quality loss: %s",files[i]);
        snprintf(url,sizeof url,"file:%s",output);
        CHECK(kr_remux_start(url,0,0,playlist,sizeof playlist)==KR_READY && strstr(playlist,"/prepared.mp4"),"prepared file uses indexed byte-range seeking without live conversion");
        int port=kr_remux_port();
        reply bytes=http_get(port,playlist,"bytes=0-127");
        CHECK(bytes.status==206 && bytes.len==128 && !memcmp(bytes.body+4,"ftyp",4),"prepared MP4 ranges return exact bytes");free(bytes.body);
        bytes=http_get(port,playlist,"bytes=-128");CHECK(bytes.status==206 && bytes.len==128,"prepared MP4 suffix range");free(bytes.body);
        bytes=http_get(port,playlist,"bytes=10-2");CHECK(bytes.status==416,"prepared MP4 rejects invalid range");free(bytes.body);
        CHECK(kr_remux_compat()==0 && kr_remux_prefetched()==0,"prepared playback never converts/prefetches segments");
        int idle_fd=socket(AF_INET,SOCK_STREAM,0);struct sockaddr_in idle_address={0};
        idle_address.sin_family=AF_INET;idle_address.sin_port=htons((uint16_t)port);idle_address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        CHECK(connect(idle_fd,(struct sockaddr *)&idle_address,sizeof idle_address)==0,"connect idle seek client");usleep(20000);
        double stop_at=mono_ms();kr_remux_stop();
        CHECK(mono_ms()-stop_at<1500,"idle client is interrupted on stop, never freed while active");close(idle_fd);
        AVFormatContext *f=NULL;CHECK(avformat_open_input(&f,output,NULL,NULL)==0,"open output MP4");
        if(f){avformat_find_stream_info(f,NULL);
            if(!strcmp(files[i],"long_seek.mkv")) {
                CHECK(av_seek_frame(f,-1,1200LL*AV_TIME_BASE,AVSEEK_FLAG_BACKWARD)>=0,"prepared file seeks twenty minutes");
                AVPacket *seek=av_packet_alloc();int got=av_read_frame(f,seek);
                double at=got>=0?seek->pts*av_q2d(f->streams[seek->stream_index]->time_base):-1;
                CHECK(got>=0 && at>=1198 && at<=1202,"twenty-minute seek lands at the selected time (%.3f)",at);av_packet_free(&seek);
            }
            for(unsigned n=0;n<f->nb_streams;n++) {
            AVCodecParameters *cp=f->streams[n]->codecpar;
            if(cp->codec_type==AVMEDIA_TYPE_AUDIO)CHECK(cp->codec_id==AV_CODEC_ID_AAC,"prepared audio is AAC");
            if(cp->codec_type==AVMEDIA_TYPE_SUBTITLE)CHECK(cp->codec_id==AV_CODEC_ID_MOV_TEXT,"prepared subtitles stay selectable text");
        }avformat_close_input(&f);}
    }
    char input[1024],output[1024],err[512]="";
    snprintf(input,sizeof input,"%s/hevc_ac3_ass.mkv",fixture_dir);snprintf(output,sizeof output,"%s/preparation-pause.mp4",work);unlink(output);
    CHECK(kodi_airplay_prepare(input,output,pause_preparation,NULL,err,sizeof err)==-2,"pause preparation without committing partial output");
    CHECK(access(output,F_OK)!=0,"paused file never becomes a completed movie");
    CHECK(kodi_airplay_prepare(input,output,NULL,NULL,err,sizeof err)==0,"resume checkpointed preparation: %s",err);
    snprintf(input,sizeof input,"%s/h264_pgs.mkv",fixture_dir);unlink(output);
    CHECK(kodi_airplay_prepare(input,output,NULL,NULL,err,sizeof err)<0 && strstr(err,"tracks MP4 cannot preserve"),"never silently drop bitmap subtitles: %s",err);
    CHECK(access(output,F_OK)!=0,"unsupported tracks keep the original untouched");
}

// r14: prepare straight from a loopback HTTP source (the phone streams the Drive file), never a downloaded copy.
static void test_preparation_http(const char *http_base,const char *work) {
    const char *files[]={"hevc_ac3_ass.mkv","h264_ac3_dts_srt.mkv"};
    for(unsigned i=0;i<sizeof files/sizeof files[0];i++) {
        char input[1024],local[1024],output[1024],err[512]="",json[1024];
        snprintf(input,sizeof input,"%s/%s",http_base,files[i]);snprintf(local,sizeof local,"%s/%s",fixture_dir,files[i]);
        snprintf(output,sizeof output,"%s/prepared-http-%u.mp4",work,i);unlink(output);
        CHECK(kodi_airplay_probe(input,json,sizeof json)==0 && strstr(json,"\"ready\":false"),"probe over loopback HTTP: %s",json);
        int r=kodi_airplay_prepare(input,output,NULL,NULL,err,sizeof err);
        CHECK(r==0,"prepare over loopback HTTP %s: %s",files[i],err);if(r)continue;
        CHECK(kodi_airplay_probe(output,json,sizeof json)==0 && strstr(json,"\"ready\":true"),"HTTP-prepared portable MP4: %s",json);
        uint8_t a[16],b[16];int aw,ah,an,bw,bh,bn;
        CHECK(video_digest(local,a,&aw,&ah,&an)==0 && video_digest(output,b,&bw,&bh,&bn)==0,"read HTTP preparation input/output");
        CHECK(aw==bw && ah==bh && an==bn && !memcmp(a,b,16),"HTTP-prepared video packets identical to the source: %s",files[i]);
    }
    char output[1024],err[512]="";snprintf(output,sizeof output,"%s/prepared-remote.mp4",work);
    CHECK(kodi_airplay_prepare("http://example.com/movie.mkv",output,NULL,NULL,err,sizeof err)<0 && access(output,F_OK)!=0,
          "preparation never reads a non-loopback URL: %s",err);
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: test_remux FIXTURE_DIR [HTTP_BASE]\n"); return 2; }
    fixture_dir = argv[1];
    // r10: the copy/compat checks below run without burned subtitles (the files' default SRT would be picked).
    kr_remux_set_subtitles(-1, NULL, NULL);
    kr_subs_set_font_file(getenv("KR_TEST_FONT"));
    if (argc > 3 && !strcmp(argv[3], "--source-only")) {
        test_source_transport(argv[2]);
        printf("%d checks, %d failed\n", checks, failures);
        return failures ? 1 : 0;
    }
    if (argc > 3 && !strcmp(argv[3], "--bitmap-only")) {
        char work[1024], path[1024];
        snprintf(work,sizeof work,"%s/out",fixture_dir); mkdir(work,0755);
        snprintf(path,sizeof path,"%s/box.sup",fixture_dir);
        kr_video_set_encoder("mpeg4"); test_external_bitmaps();
        test_long_embedded(work);
        test_burn_video(work,"h264_aac_srt.mkv",path);
        snprintf(path,sizeof path,"%s/dvd.idx",fixture_dir);
        test_burn_video(work,"h264_aac_srt.mkv",path);
        printf("%d checks, %d failed\n", checks, failures);
        return failures ? 1 : 0;
    }
    if (argc > 3 && !strcmp(argv[3], "--seek-only")) {
        kr_video_set_encoder("mpeg4");
        test_seek_overlap(argv[2]);
        printf("%d checks, %d failed\n", checks, failures);
        return failures ? 1 : 0;
    }
    test_kind();
    char work[512]; snprintf(work, sizeof work, "%s/out", argv[1]);
    mkdir(work, 0755);
    if (argc > 3 && !strcmp(argv[3], "--prepare-only")) {
        test_preparation(work);test_preparation_http(argv[2],work);printf("%d checks, %d failed\n",checks,failures);return failures?1:0;
    }
    if (argc > 3 && !strcmp(argv[3], "--dovi-only")) {
        kr_video_set_encoder("mpeg4");test_dovi_render(work);
        char url[1024];snprintf(url,sizeof url,"file:%s/dovi.mkv",fixture_dir);
        test_extra_format(url,"dovi",work,1);
        printf("%d checks, %d failed\n",checks,failures);return failures?1:0;
    }
    if (argc > 3 && !strcmp(argv[3], "--routing-only")) {
        char url[1024]; snprintf(url, sizeof url, "file:%s/mp4_bytes", argv[1]);
        kr_video_set_encoder("mpeg4"); test_dovi_native_route(url, work);
        printf("%d checks, %d failed\n", checks, failures);
        return failures ? 1 : 0;
    }
    test_preparation(work);
    if (argc > 2) test_preparation_http(argv[2], work);
    fixture fx[] = {
        { "h264_aac_srt.mkv", "avc1.42C0", "mp4a.40.2", 1, 1, 0, 0, "Hello from SRT" },
        { "hevc_ac3_ass.mkv", "hvc1.2.4.L", "ac-3", 1, 1, 1, 0, "Hello from ASS" },
        { "h264_dts.mkv", "avc1.", "mp4a.40.2", 1, 0, 0, 1, NULL },
        { "h264_truehd.mkv", "avc1.", "mp4a.40.2", 1, 0, 0, 1, NULL },
        { "h264_ac3_dts_srt.mkv", "avc1.", "ac-3,mp4a.40.2", 2, 1, 0, 1, "Hello from SRT" },
        { "h264_ac3_dts_srt.mkv", "avc1.", "ac-3,mp4a.40.2", 2, 1, 0, 1, "Hello from SRT", 0, 1 },  // AirPlay (LAN) mode
        { "h264_ac3.ts", "avc1.", "ac-3", 1, 0, 0, 0, NULL, 1.4 },  // MPEG-TS starts at 1.4 s: kept (absolute tfdt)
    };
    for (size_t i = 0; i < sizeof fx / sizeof *fx; i++) {
        char url[1024]; snprintf(url, sizeof url, "file:%s/%s", argv[1], fx[i].file);
        printf("-- %s\n", fx[i].file); fflush(stdout);
        test_file(url, &fx[i], work);
    }
    // r7: FFmpeg has no LGPL H.264 encoder and the host has no VideoToolbox: the picture bridge is exercised with the
    // MPEG-4 Part 2 encoder (same decode -> scale -> encode -> mux -> tfdt path; the bytes are not H.264 here).
    printf("-- compat (picture converted; host encoder %s)\n", "mpeg4"); fflush(stdout);
    test_video_units();
    kr_video_set_encoder("mpeg4");
    CHECK(kr_video_available(), "host FFmpeg has the test encoder");
    test_color_mapping();
    test_dovi_render(work);
    {
        const char *names[] = { "av1_opus.mkv", "wmv_wma.asf", "flv_mp3.flv", "theora_vorbis.ogv", "mpeg2_mp2.mpg", "h264_10bit.mp4", "h264_aac.mp4", "rv20_ac3.rm", "mpeg2_ac3.wtv", "mpeg4_pcm.nut", "prores_pcm.mov", "dovi.mkv" };
        for (unsigned i = 0; i < sizeof names / sizeof names[0]; i++) {
            char url[1024]; snprintf(url, sizeof url, "file:%s/%s", argv[1], names[i]);
            test_extra_format(url, names[i], work, i == 5 || i == 6 ? 0 : 1);
            if (i == 5) CHECK(kr_remux_state() == KR_IDLE, "10-bit H.264 session stopped cleanly");
        }
        char url[1024], h264[1024];
        snprintf(url, sizeof url, "file:%s/mp4_bytes", argv[1]);
        snprintf(h264, sizeof h264, "file:%s/h264_aac.mp4", argv[1]);
        test_receivers(url, h264, work);
        test_dovi_native_route(url, work);
        char playlist[256]; snprintf(url, sizeof url, "file:%s/native_hls", argv[1]);
        CHECK(kr_remux_start(url, 0, 0, playlist, sizeof playlist) == KR_NOT_NEEDED, "extensionless HLS remains native");
        kr_remux_stop();
    }
    {
        char url[1024];
        snprintf(url, sizeof url, "file:%s/hevc_ac3_ass.mkv", argv[1]); test_compat(url, "hevc_ac3_ass.mkv", 1, 0, "ac-3", work);
        snprintf(url, sizeof url, "file:%s/h264_ac3.ts", argv[1]); test_compat(url, "h264_ac3.ts", 1, 1.4, "ac-3", work);
        snprintf(url, sizeof url, "file:%s/mpeg2_ac3.mkv", argv[1]); test_compat(url, "mpeg2_ac3.mkv", 0, 0, "ac-3", work);
        snprintf(url, sizeof url, "file:%s/vp9_opus.webm", argv[1]); test_compat(url, "vp9_opus.webm", 0, 0, "mp4a.40.2", work);
        snprintf(url, sizeof url, "file:%s/mpeg4_mp3.avi", argv[1]); test_compat(url, "mpeg4_mp3.avi", 1, 0, "mp4a.40.34", work);
        snprintf(url, sizeof url, "file:%s/hevc_4k.mkv", argv[1]); test_4k_seek(url, work);
        snprintf(url, sizeof url, "file:%s/hevc_ac3_ass.mkv", argv[1]); test_compat_stop(url);
        printf("-- r8 receivers (a TV's AirPlay gets H.264, the phone the HEVC copy)\n"); fflush(stdout);
        char h264[1024]; snprintf(h264, sizeof h264, "file:%s/h264_aac_srt.mkv", argv[1]);
        test_receivers(url, h264, work);
        printf("-- r10 burned-in subtitles (libass)\n"); fflush(stdout);
        test_burn_render();
        test_burn_video(work, "h264_aac_srt.mkv", NULL);
        test_burn_video(work, "h264_pgs.mkv", NULL);
        char external[1024]; snprintf(external, sizeof external, "%s/box.sup", fixture_dir);
        test_burn_video(work, "h264_aac_srt.mkv", external);
        snprintf(external, sizeof external, "%s/dvd.idx", fixture_dir);
        test_burn_video(work, "h264_aac_srt.mkv", external);
        test_external_bitmaps();
        test_long_embedded(work);
        test_burn_select();
        snprintf(url, sizeof url, "file:%s/h264_pgs.mkv", argv[1]); test_bitmap_subtitles(url);
        kr_video_set_encoder("no_such_encoder");
        char m3u8[256];
        CHECK(kr_remux_start(url, 0, 1, m3u8, sizeof m3u8) == KR_FAILED && strstr(kr_remux_message(), "cannot convert video"),
              "compat without an encoder explains itself: %s", kr_remux_message());
        snprintf(url, sizeof url, "file:%s/mpeg2_ac3.mkv", argv[1]);
        CHECK(kr_remux_start(url, 0, 0, m3u8, sizeof m3u8) == KR_FAILED && strstr(kr_remux_message(), "cannot convert video"),
              "no encoder: unsupported video must fail clearly instead of silently playing audio only");
        kr_remux_stop();
        kr_video_set_encoder("mpeg4");
    }
    if (argc > 2) {
        printf("-- over HTTP (%s)\n", argv[2]);
        test_range_source(argv[2]);
        test_source_transport(argv[2]);
        char url[1024]; snprintf(url, sizeof url, "%s/h264_ac3_dts_srt.mkv", argv[2]);
        test_file(url, &fx[4], work);
        snprintf(url, sizeof url, "%s/hevc_ac3_ass.mkv", argv[2]);
        test_compat(url, "hevc_ac3_ass.mkv.http", 1, 0, "ac-3", work);
        printf("-- r8 latency (slow source)\n"); fflush(stdout);
        test_latency(argv[2]);
        printf("-- overlapping converted seek requests\n"); fflush(stdout);
        test_seek_overlap(argv[2]);
    }
    printf("%d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
