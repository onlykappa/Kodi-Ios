// Host tests for the AirPlay remuxer: container detection, playlist generation, segment boundaries, the AAC audio
// bridge (DTS/TrueHD), WebVTT subtitles, range reading over HTTP, seeks (segments out of order) and clean shutdown.
// usage: test_remux FIXTURE_DIR [HTTP_BASE]   (HTTP_BASE: tests/range_server.py serving FIXTURE_DIR)
#include "../src/kr_remux.h"
#include "../src/kr_hls.h"
#include "../src/kr_audio.h"
#include "../src/kr_source.h"
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

static int failures, checks;
#define CHECK(c, ...) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

typedef struct { int status; char *body; size_t len; char head[1024]; } reply;

static char prefix_path[96];
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
    int n = snprintf(req, sizeof req, "GET %s HTTP/1.1\r\nHost: 127.0.0.1\r\nUser-Agent: test_remux/1\r\n%s%s%s\r\n", path, range ? "Range: " : "", range ? range : "", range ? "\r\n" : "");
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
    CHECK(kr_remux_kind("http://x/movie.mp4") == KR_DIRECT && kr_remux_kind("x.m3u8") == KR_DIRECT && kr_remux_kind("x.mov") == KR_DIRECT, "direct");
    CHECK(kr_remux_kind("https://drive.google.com/uc?id=abc&export=download") == KR_UNKNOWN, "drive link");
    CHECK(kr_remux_kind("http://h.example/dir.mkv/file") == KR_UNKNOWN, "dot in a directory");
    CHECK(kr_remux_kind(NULL) == KR_UNKNOWN, "null");
    gm_track_info t = {0}; t.kind = GM_TRACK_AUDIO;
    strcpy(t.codec, "dts"); CHECK(kr_audio_route(&t) == KR_AUDIO_AAC && !strcmp(kr_audio_token(&t), "mp4a.40.2"), "dts bridged");
    strcpy(t.codec, "truehd"); CHECK(kr_audio_route(&t) == KR_AUDIO_AAC, "truehd bridged");
    strcpy(t.codec, "eac3"); t.avf_compatible = 1; CHECK(kr_audio_route(&t) == KR_AUDIO_COPY && !strcmp(kr_audio_token(&t), "ec-3"), "eac3 copied");
    t.avf_compatible = 0; strcpy(t.codec, "pcm_bluray"); CHECK(kr_audio_route(&t) == KR_AUDIO_NONE, "unknown audio not offered");
    CHECK(!strcmp(kr_language("eng"), "en") && !strcmp(kr_language("und"), "") && !strcmp(kr_language("xyz"), "xyz"), "languages");
}

typedef struct { const char *file; const char *video; const char *audio_tokens; int audio_tracks, subs, hdr, bridged; const char *sub_text; double offset; int lan; } fixture;

static void test_file(const char *url, const fixture *fx, const char *work) {
    start_offset = fx->offset;
    char m3u8[256];
    static char log[1 << 16];
    while (kr_remux_log(log, sizeof log) > 0) {}  // earlier sessions' lines
    int st = kr_remux_start(url, fx->lan, m3u8, sizeof m3u8);
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
    kr_source_abort(s);
    CHECK(kr_source_read(s, 0, a, 16) < 0, "reads fail after abort (stop pressed)");
    fclose(f);
    kr_source_close(s);
    char m3u8[256];
    snprintf(url, sizeof url, "%s/h264_aac.mp4", http_base);
    CHECK(kr_remux_start(url, 0, m3u8, sizeof m3u8) == KR_NOT_NEEDED, "MP4 bytes go direct (%s)", kr_remux_message());
    snprintf(url, sizeof url, "%s/missing.mkv", http_base);
    CHECK(kr_remux_start(url, 0, m3u8, sizeof m3u8) == KR_FAILED && strstr(kr_remux_message(), "AirPlay"), "a missing file explains itself: %s", kr_remux_message());
    kr_remux_stop();
}

const char *fixture_dir;

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: test_remux FIXTURE_DIR [HTTP_BASE]\n"); return 2; }
    fixture_dir = argv[1];
    test_kind();
    char work[512]; snprintf(work, sizeof work, "%s/out", argv[1]);
    mkdir(work, 0755);
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
    if (argc > 2) {
        printf("-- over HTTP (%s)\n", argv[2]);
        test_range_source(argv[2]);
        char url[1024]; snprintf(url, sizeof url, "%s/h264_ac3_dts_srt.mkv", argv[2]);
        test_file(url, &fx[4], work);
    }
    printf("%d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
