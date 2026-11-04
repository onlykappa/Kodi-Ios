// Kodi iOS AirPlay remuxer: plays MKV / AVI / WebM / MPEG-TS through AirPlay by remuxing on demand (video copied;
// r7: converted to H.264 in compat mode) into fragmented-MP4 HLS served from 127.0.0.1, which AVPlayer opens like any HLS stream.
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
// r7: compat=1 converts the picture to H.264 High 8-bit SDR at most 1080p on the phone (kr_video: VideoToolbox decode and
// encode) for receivers that cannot decode the source video (TVs' built-in AirPlay without HEVC). Audio and subtitles
// are served as usual and the segment grid is the same, so a position carries over. A file whose video AirPlay cannot
// carry at all (VP9, MPEG-2...) switches to compat by itself when the converter is available.
int kr_remux_start(const char *url, int lan, int compat, char *out, int outlen);
// r7: 1 when the running session converts the picture (compat), 0 otherwise.
int kr_remux_compat(void);
int kr_remux_state(void);
// A short sentence for the screen when state is KR_FAILED (or the latest serving error), "" otherwise.
const char *kr_remux_message(void);
// Stops the server, aborts network reads and frees everything. Safe to call any time, more than once.
void kr_remux_stop(void);
// r6: the log lines written since the last call ("start: URL", "master: BANDWIDTH=...,CODECS=...", "client: UA",
// "GET /video/seg3.m4s 200 1834567 B 412 ms", "error: ..."), newline-separated, at most len-1 bytes; lines that do
// not fit wait for the next call. Keeps the latest 128. Returns the length written. Any thread.
int kr_remux_log(char *buf, int len);
// r6: media segments sent this session, video (1) or audio (0). A receiver that takes audio segments but never a
// video one is playing sound only (an AirPlay TV that cannot decode the video codec).
int kr_remux_served(int video);
// r8: the same, counting only receivers other than the phone's own player (User-Agent not AppleCoreMedia on an
// iPhone/iPad): what the TV took. 0 video segments while the TV played: it never got a picture.
int kr_remux_served_external(int video);
// r6: the running session's video CODECS value ("avc1.640028", "hvc1.2.4.L120.90"), "" when none.
const char *kr_remux_video_codec(void);
// The port of the running server, 0 when none (tests).
int kr_remux_port(void);
// r8: 1 when a request's User-Agent is a third-party AirPlay receiver (a TV's built-in AirPlay: "MFi_AirPlay_Device").
// When the source video is not H.264, such a receiver gets the compat master (CODECS avc1.640028, at most 1080p, SDR)
// whose video variant is /cvideo/ (the picture converted, kr_video), and its /video/ requests are converted too; every
// other client (AppleCoreMedia on the phone or an Apple TV) keeps the copy. Both paths use the same segment grid.
int kr_remux_third_party_receiver(const char *ua);
// r8: compat masters served to third-party receivers this session (0: none asked).
int kr_remux_compat_clients(void);
// r8: segments made ahead in the background this session (after segment N is served, N+1 and N+2 of that rendition
// are made and cached; inits and recently served segments are cached too).
int kr_remux_prefetched(void);
// r8: 0 turns making segments ahead off (host tests measure with and without it), 1 on (the default).
void kr_remux_set_prefetch(int on);
// r10: the subtitles burned into the converted picture (compat), taken by the next kr_remux_start: ordinal >= 0 is
// Kodi's subtitle stream number (the ordinal-th subtitle stream of the file; at or past the file's count it is
// Kodi's external subtitle, `file`); -1 none; -2 automatic (`file` when given, else the file's forced / default
// text subtitle, else the first in language `lang`, ISO 639-2). Third-party receivers then get the converted picture
// even for H.264 sources. Only text subtitles can be burned (not PGS / DVD images). Changing them is a new session.
void kr_remux_set_subtitles(int ordinal, const char *file, const char *lang);
// r10: the running session's burned subtitles: source stream index, -2 an external file, -1 none.
int kr_remux_burn_track(void);
#ifdef __cplusplus
}
#endif
#endif
