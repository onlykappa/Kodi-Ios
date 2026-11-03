// Kodi iOS AirPlay remuxer: plays MKV / AVI / WebM / MPEG-TS through AirPlay by remuxing on demand (no re-encoding of
// video) into fragmented-MP4 HLS served from 127.0.0.1, which AVPlayer opens like any HLS stream.
#ifndef KR_REMUX_H
#define KR_REMUX_H
#ifdef __cplusplus
extern "C" {
#endif
enum { KR_DIRECT = 0, KR_REMUX = 1, KR_UNKNOWN = -1 };
// From the URL's path: KR_REMUX for .mkv/.mk3d/.avi/.webm/.ts/.m2ts/.mts, KR_DIRECT for .mp4/.m4v/.mov/.m3u8,
// KR_UNKNOWN otherwise (Drive links, Elementum ids: kr_remux_start probes the bytes).
int kr_remux_kind(const char *url);

enum { KR_IDLE = 0, KR_STARTING = 1, KR_READY = 2, KR_FAILED = -1, KR_NOT_NEEDED = 3 };
// Opens `url`, plans the segments and starts the loopback server. On success returns KR_READY and writes the
// playlist URL ("http://127.0.0.1:PORT/master.m3u8") into out. Returns KR_NOT_NEEDED when the bytes are MP4/MOV
// (play the URL directly) and KR_FAILED with a message for the person (kr_remux_message) otherwise.
// lan=0 serves 127.0.0.1 only (playback on the phone). lan=1 is for AirPlay: the Apple TV fetches the playlist and
// segments itself, so the server listens on the phone's Wi-Fi address and every path carries a random token
// ("http://192.168.1.20:PORT/3f9c.../master.m3u8"); requests without it get 404.
// One session at a time: a running one is stopped first. Blocks while the source is probed (call off the main thread).
int kr_remux_start(const char *url, int lan, char *out, int outlen);
int kr_remux_state(void);
// A short sentence for the screen when state is KR_FAILED (or the latest serving error), "" otherwise.
const char *kr_remux_message(void);
// Stops the server, aborts network reads and frees everything. Safe to call any time, more than once.
void kr_remux_stop(void);
// The port of the running server, 0 when none (tests).
int kr_remux_port(void);
#ifdef __cplusplus
}
#endif
#endif
