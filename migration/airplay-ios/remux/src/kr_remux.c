// Session + loopback HTTP server for the AirPlay remuxer. POSIX sockets, one thread per connection, bound to
// 127.0.0.1 on a port the system picks (no port conflicts with Elementum 65220 or Kodi's web server).
#include "kr_remux.h"
#include "kr_audio.h"
#include "kr_hls.h"
#include "kr_source.h"
#include <arpa/inet.h>
#include <ctype.h>
#include <errno.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/socket.h>
#include <unistd.h>
#include <libavformat/avformat.h>

#ifndef MSG_NOSIGNAL
#define MSG_NOSIGNAL 0
#endif
#define SEG_SECONDS 6.0
#define MAX_TRACKS 64

typedef struct {
    kr_source *src;
    kr_audio *audio;
    int index;
    pthread_mutex_t lock;
} bridge;

static struct {
    pthread_mutex_t lock;     // session start/stop
    pthread_mutex_t gm_lock;  // gm_stream is single-threaded
    atomic_int state;
    char message[256];
    char url[4096];
    kr_source *src;
    gm_stream *gm;
    bridge bridges[MAX_TRACKS];
    int nbridges;
    int listen_fd, port;
    pthread_t accept_thread;
    atomic_int stopping, active;
    char base[64];
} S = { .lock = PTHREAD_MUTEX_INITIALIZER, .gm_lock = PTHREAD_MUTEX_INITIALIZER, .listen_fd = -1 };

static void set_message(const char *m) { snprintf(S.message, sizeof S.message, "%s", m ? m : ""); }

int kr_remux_kind(const char *url) {
    if (!url) return KR_UNKNOWN;
    const char *end = url + strcspn(url, "?#");
    const char *dot = NULL;
    for (const char *p = url; p < end; p++) { if (*p == '.') dot = p; else if (*p == '/') dot = NULL; }
    if (!dot) return KR_UNKNOWN;
    char ext[8] = "";
    size_t n = (size_t)(end - dot - 1);
    if (n == 0 || n >= sizeof ext) return KR_UNKNOWN;
    for (size_t i = 0; i < n; i++) ext[i] = (char)tolower((unsigned char)dot[1 + i]);
    static const char *remux[] = { "mkv", "mk3d", "avi", "webm", "ts", "m2ts", "mts", NULL };
    static const char *direct[] = { "mp4", "m4v", "mov", "m3u8", NULL };
    for (int i = 0; remux[i]; i++) if (!strcmp(ext, remux[i])) return KR_REMUX;
    for (int i = 0; direct[i]; i++) if (!strcmp(ext, direct[i])) return KR_DIRECT;
    return KR_UNKNOWN;
}

int kr_remux_state(void) { return atomic_load(&S.state); }
const char *kr_remux_message(void) { return S.message; }
int kr_remux_port(void) { return atomic_load(&S.state) == KR_READY ? S.port : 0; }

// ── HTTP ───────────────────────────────────────────────────────────────────────
static int send_all(int fd, const void *p, size_t n) {
    const char *c = p;
    while (n) {
        ssize_t w = send(fd, c, n, MSG_NOSIGNAL);
        if (w < 0 && errno == EINTR) continue;
        if (w <= 0) return -1;
        c += w; n -= (size_t)w;
    }
    return 0;
}

static void respond(int fd, int head, const char *range, const char *type, const uint8_t *body, size_t len) {
    char h[512];
    size_t from = 0, to = len ? len - 1 : 0;
    int partial = 0;
    unsigned long long a = 0, b = 0;
    if (range && len) {
        int got = sscanf(range, "bytes=%llu-%llu", &a, &b);
        if (got >= 1 && a < len) { from = (size_t)a; if (got == 2 && b < len && b >= a) to = (size_t)b; partial = 1; }
        else if (got >= 1) {
            int n = snprintf(h, sizeof h, "HTTP/1.1 416 Range Not Satisfiable\r\nContent-Range: bytes */%zu\r\nContent-Length: 0\r\nConnection: close\r\n\r\n", len);
            send_all(fd, h, (size_t)n); return;
        }
    }
    size_t n_body = len ? to - from + 1 : 0;
    int n = partial
        ? snprintf(h, sizeof h, "HTTP/1.1 206 Partial Content\r\nContent-Type: %s\r\nContent-Length: %zu\r\nContent-Range: bytes %zu-%zu/%zu\r\nAccept-Ranges: bytes\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n", type, n_body, from, to, len)
        : snprintf(h, sizeof h, "HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %zu\r\nAccept-Ranges: bytes\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n", type, n_body);
    if (send_all(fd, h, (size_t)n) == 0 && !head && n_body) send_all(fd, body + from, n_body);
}

static void fail(int fd, int code, const char *why) {
    char h[256];
    int n = snprintf(h, sizeof h, "HTTP/1.1 %d %s\r\nContent-Length: 0\r\nConnection: close\r\n\r\n", code, why);
    send_all(fd, h, (size_t)n);
}

static int ends_with(const char *s, const char *tail) {
    size_t a = strlen(s), b = strlen(tail);
    return a >= b && !strcmp(s + a - b, tail);
}

static bridge *find_bridge(int index) {
    for (int i = 0; i < S.nbridges; i++) if (S.bridges[i].index == index) return &S.bridges[i];
    return NULL;
}

static int track_route(int index) {
    gm_track_info t;
    for (int i = 0; i < gm_stream_track_count(S.gm); i++)
        if (gm_stream_track_info(S.gm, i, &t) == 0 && t.src_index == index) return kr_audio_route(&t);
    return KR_AUDIO_NONE;
}

// Opens the bridge for an audio track the first time AVPlayer asks for it (a second connection to the source).
static kr_audio *bridge_audio(bridge *b, char *err, int errlen) {
    if (b->audio) return b->audio;
    b->src = kr_source_open(S.url, 30, err, errlen);
    if (!b->src) return NULL;
    b->audio = kr_audio_open(kr_source_gm(b->src), b->index, err, errlen);
    if (!b->audio) { kr_source_close(b->src); b->src = NULL; }
    return b->audio;
}

static void serve(int fd, const char *method, const char *path, const char *range) {
    int head = !strcmp(method, "HEAD");
    char err[256] = "";
    gm_buf buf = {0};
    int idx = -1, seg = -1, r = -1;
    char *text = NULL;
    const char *m3u8 = "application/vnd.apple.mpegurl";
    if (!strcmp(path, "/master.m3u8")) {
        pthread_mutex_lock(&S.gm_lock); text = kr_hls_master(S.gm, S.base); pthread_mutex_unlock(&S.gm_lock);
    } else if (!strcmp(path, "/video/index.m3u8")) {
        char prefix[96]; snprintf(prefix, sizeof prefix, "%s/video", S.base);
        pthread_mutex_lock(&S.gm_lock); text = kr_hls_media(S.gm, prefix, "m4s", 1); pthread_mutex_unlock(&S.gm_lock);
    } else if (ends_with(path, "/index.m3u8") && (sscanf(path, "/audio/%d/", &idx) == 1 || sscanf(path, "/subs/%d/", &idx) == 1)) {
        int subs = path[1] == 's';
        char prefix[96]; snprintf(prefix, sizeof prefix, "%s/%s/%d", S.base, subs ? "subs" : "audio", idx);
        pthread_mutex_lock(&S.gm_lock); text = kr_hls_media(S.gm, prefix, subs ? "vtt" : "m4s", !subs); pthread_mutex_unlock(&S.gm_lock);
    }
    if (text) { respond(fd, head, NULL, m3u8, (uint8_t *)text, strlen(text)); free(text); return; }

    if (!strcmp(path, "/video/init.mp4")) {
        pthread_mutex_lock(&S.gm_lock); r = gm_stream_video_init(S.gm, &buf, err, sizeof err); pthread_mutex_unlock(&S.gm_lock);
    } else if (sscanf(path, "/video/seg%d.m4s", &seg) == 1) {
        pthread_mutex_lock(&S.gm_lock); r = gm_stream_video_segment(S.gm, seg, &buf, err, sizeof err); pthread_mutex_unlock(&S.gm_lock);
    } else if (sscanf(path, "/subs/%d/seg%d.vtt", &idx, &seg) == 2) {
        pthread_mutex_lock(&S.gm_lock); r = gm_stream_subtitle_segment(S.gm, idx, seg, &buf, err, sizeof err); pthread_mutex_unlock(&S.gm_lock);
        if (r == 0) { respond(fd, head, range, "text/vtt", buf.data, (size_t)buf.len); free(buf.data); return; }
    } else if (sscanf(path, "/audio/%d/", &idx) == 1) {
        int init = strstr(path, "/init.mp4") != NULL;
        if (!init && sscanf(path, "/audio/%*d/seg%d.m4s", &seg) != 1) { fail(fd, 404, "Not Found"); return; }
        int route = track_route(idx);
        if (route == KR_AUDIO_COPY) {
            pthread_mutex_lock(&S.gm_lock);
            r = init ? gm_stream_audio_init(S.gm, idx, &buf, err, sizeof err) : gm_stream_audio_segment(S.gm, idx, seg, &buf, err, sizeof err);
            pthread_mutex_unlock(&S.gm_lock);
        } else if (route == KR_AUDIO_AAC) {
            bridge *b = find_bridge(idx);
            if (b) {
                pthread_mutex_lock(&b->lock);
                kr_audio *a = bridge_audio(b, err, sizeof err);
                if (a) r = init ? kr_audio_init(a, S.gm, &buf, err, sizeof err) : kr_audio_segment(a, S.gm, seg, &buf, err, sizeof err);
                pthread_mutex_unlock(&b->lock);
            }
        } else { fail(fd, 404, "Not Found"); return; }
    } else { fail(fd, 404, "Not Found"); return; }

    if (r == 0) respond(fd, head, range, "video/mp4", buf.data, (size_t)buf.len);
    else {
        if (!atomic_load(&S.stopping)) {
            char m[300]; snprintf(m, sizeof m, "AirPlay conversion failed on %.60s: %s", path, *err ? err : "unknown error");
            set_message(m);
            fprintf(stderr, "kodi-airplay-remux: %s\n", m);
        }
        fail(fd, 500, "Remux Failed");
    }
    free(buf.data);
}

static void *connection(void *arg) {
    int fd = (int)(intptr_t)arg;
    char req[8192]; size_t got = 0;
    while (got < sizeof req - 1) {
        ssize_t n = recv(fd, req + got, sizeof req - 1 - got, 0);
        if (n <= 0) break;
        got += (size_t)n; req[got] = 0;
        if (strstr(req, "\r\n\r\n")) break;
    }
    req[got] = 0;
    char method[8] = "", path[1024] = "";
    if (sscanf(req, "%7s %1023s", method, path) == 2 && (!strcmp(method, "GET") || !strcmp(method, "HEAD"))) {
        char range[128] = "", *h = req;
        while ((h = strstr(h, "\r\n")) != NULL) {
            h += 2;
            if (!strncasecmp(h, "Range:", 6)) { sscanf(h + 6, " %127[^\r\n]", range); break; }
        }
        char *q = strchr(path, '?'); if (q) *q = 0;
        serve(fd, method, path, *range ? range : NULL);
    } else fail(fd, 405, "Method Not Allowed");
    close(fd);
    atomic_fetch_sub(&S.active, 1);
    return NULL;
}

static void *accept_loop(void *unused) {
    (void)unused;
    while (!atomic_load(&S.stopping)) {
        int fd = accept(S.listen_fd, NULL, NULL);
        if (fd < 0) { if (errno == EINTR) continue; break; }
        if (atomic_load(&S.stopping)) { close(fd); break; }
#ifdef SO_NOSIGPIPE
        int one = 1; setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof one);
#endif
        struct timeval tv = { 60, 0 };
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof tv);
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
        atomic_fetch_add(&S.active, 1);
        pthread_t t;
        pthread_attr_t at; pthread_attr_init(&at); pthread_attr_setdetachstate(&at, PTHREAD_CREATE_DETACHED);
        if (pthread_create(&t, &at, connection, (void *)(intptr_t)fd) != 0) { close(fd); atomic_fetch_sub(&S.active, 1); }
        pthread_attr_destroy(&at);
    }
    return NULL;
}

// Binds 127.0.0.1 on a port the system picks; tries again a few times if that fails.
static int listen_loopback(int *port) {
    for (int attempt = 0; attempt < 5; attempt++) {
        int fd = socket(AF_INET, SOCK_STREAM, 0);
        if (fd < 0) continue;
        int one = 1; setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
        struct sockaddr_in a = { 0 };
        a.sin_family = AF_INET; a.sin_addr.s_addr = htonl(INADDR_LOOPBACK); a.sin_port = 0;
        socklen_t len = sizeof a;
        if (bind(fd, (struct sockaddr *)&a, sizeof a) == 0 && listen(fd, 32) == 0 &&
            getsockname(fd, (struct sockaddr *)&a, &len) == 0) { *port = ntohs(a.sin_port); return fd; }
        close(fd);
    }
    return -1;
}

static void teardown_locked(void) {
    atomic_store(&S.stopping, 1);
    if (S.src) kr_source_abort(S.src);
    for (int i = 0; i < S.nbridges; i++) if (S.bridges[i].src) kr_source_abort(S.bridges[i].src);
    if (S.listen_fd >= 0) {
        shutdown(S.listen_fd, SHUT_RDWR); close(S.listen_fd); S.listen_fd = -1;
        pthread_join(S.accept_thread, NULL);
    }
    for (int i = 0; i < 400 && atomic_load(&S.active) > 0; i++) usleep(10000);  // up to 4 s for open requests
    if (S.gm) { gm_stream_close(S.gm); S.gm = NULL; }
    if (S.src) { kr_source_close(S.src); S.src = NULL; }
    for (int i = 0; i < S.nbridges; i++) {
        kr_audio_close(S.bridges[i].audio); kr_source_close(S.bridges[i].src);
        pthread_mutex_destroy(&S.bridges[i].lock);
    }
    S.nbridges = 0; S.port = 0;
}

void kr_remux_stop(void) {
    pthread_mutex_lock(&S.lock);
    teardown_locked();
    atomic_store(&S.state, KR_IDLE);
    set_message("");
    pthread_mutex_unlock(&S.lock);
}

static int is_direct_format(const char *name) {
    return name && (strstr(name, "mp4") || strstr(name, "mov") || !strcmp(name, "hls"));
}

int kr_remux_start(const char *url, char *out, int outlen) {
    pthread_mutex_lock(&S.lock);
    teardown_locked();
    atomic_store(&S.stopping, 0);
    atomic_store(&S.state, KR_STARTING);
    set_message("");
    if (out && outlen > 0) *out = 0;
    char err[256] = "";
    int result = KR_FAILED;
    snprintf(S.url, sizeof S.url, "%s", url ? url : "");
    S.src = kr_source_open(S.url, 30, err, sizeof err);
    if (!S.src) { char m[300]; snprintf(m, sizeof m, "AirPlay: %s.", err); set_message(m); goto done; }
    {   // MP4/MOV bytes behind a URL without an extension (a Drive link): Apple's player takes the URL itself
        uint8_t pad[4096 + AVPROBE_PADDING_SIZE] = {0};
        int n = kr_source_read(S.src, 0, pad, 4096);
        AVProbeData pd = { "", pad, n > 0 ? n : 0, NULL };
        const AVInputFormat *fmt = n > 0 ? av_probe_input_format(&pd, 1) : NULL;
        if (fmt && is_direct_format(fmt->name)) { result = KR_NOT_NEEDED; goto done; }
    }
    S.gm = gm_stream_open(kr_source_gm(S.src), SEG_SECONDS, err, sizeof err);
    if (!S.gm) {
        char m[300];
        snprintf(m, sizeof m, "AirPlay cannot play this file: %s.", *err ? err : "the video is not H.264 or HEVC");
        set_message(m);
        goto done;
    }
    // Every audio track Apple cannot carry but we can decode gets a bridge (opened on first use).
    gm_track_info t;
    int playable_audio = 0, audio_tracks = 0;
    for (int i = 0; i < gm_stream_track_count(S.gm) && S.nbridges < MAX_TRACKS; i++) {
        if (gm_stream_track_info(S.gm, i, &t) != 0 || t.kind != GM_TRACK_AUDIO) continue;
        audio_tracks++;
        int route = kr_audio_route(&t);
        if (route) playable_audio++;
        if (route == KR_AUDIO_AAC) {
            bridge *b = &S.bridges[S.nbridges++];
            memset(b, 0, sizeof *b); b->index = t.src_index; pthread_mutex_init(&b->lock, NULL);
        }
    }
    if (audio_tracks && !playable_audio) {
        set_message("AirPlay: this file's audio format cannot be converted, so it would play silent. Use Play on TV instead.");
        goto done;
    }
    S.listen_fd = listen_loopback(&S.port);
    if (S.listen_fd < 0) { set_message("AirPlay: could not start the local streaming server."); goto done; }
    snprintf(S.base, sizeof S.base, "http://127.0.0.1:%d", S.port);
    if (pthread_create(&S.accept_thread, NULL, accept_loop, NULL) != 0) {
        close(S.listen_fd); S.listen_fd = -1;
        set_message("AirPlay: could not start the local streaming server."); goto done;
    }
    if (out && outlen > 0) snprintf(out, (size_t)outlen, "%s/master.m3u8", S.base);
    result = KR_READY;
done:
    if (result != KR_READY) teardown_locked();
    atomic_store(&S.state, result);
    pthread_mutex_unlock(&S.lock);
    return result;
}
