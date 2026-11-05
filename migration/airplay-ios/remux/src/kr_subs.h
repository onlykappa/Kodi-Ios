// kr_subs (r10): burned-in subtitles for the picture bridge (kr_video). Third-party AirPlay receivers (TVs' built-in
// AirPlay, "MFi_AirPlay_Device") ignore the master's WebVTT rendition, so in compat mode the chosen text subtitle is
// drawn into the converted picture: events from the source's text subtitle stream (SRT / ASS / SSA / mov_text /
// WebVTT, decoded by FFmpeg) or from an external .srt / .vtt / .ass / .ssa file go into one libass track per session,
// and each output frame gets ass_render_frame at its own timestamp, alpha-blended onto the 8-bit 4:2:0 frame (NV12 or
// planar). libass (ISC) with FreeType (FTL), FriBidi (LGPL-2.1+) and HarfBuzz (MIT), linked statically; no
// fontconfig: on iOS libass takes the system fonts through CoreText, the host tests give a font file. Kodi iOS code.
#ifndef KR_SUBS_H
#define KR_SUBS_H
#include <stdint.h>
struct AVFormatContext;
struct AVStream;
struct AVPacket;
typedef struct kr_subs kr_subs;

// Font file used when no system font provider finds one (host tests; NULL on iOS: CoreText). Set before use.
void kr_subs_set_font_file(const char *path);
// 1 when FFmpeg can turn this stream into text events (subrip, srt, ass, ssa, mov_text, webvtt, text).
int kr_subs_is_text(const struct AVStream *st);
// Text or a supported embedded palette-bitmap subtitle (PGS/DVD/DVB/XSUB).
int kr_subs_supported(const struct AVStream *st);
// The source stream to burn. ordinal >= 0: Kodi's subtitle stream number, the ordinal-th subtitle stream of the
// file in stream order (image subtitles count too, as in Kodi's list; unsupported codecs give -1); -2: automatic,
// the first supported stream marked forced, else default, else the first in language `lang` (ISO 639-2 like "eng", or
// 639-1 "en"); -1 or nothing suitable: -1.
int kr_subs_pick(struct AVFormatContext *f, int ordinal, const char *lang);
// Number of subtitle streams in the file (Kodi's embedded subtitle count; ordinals at or above it are external).
int kr_subs_stream_count(struct AVFormatContext *f);

// A renderer for w x h output frames.
kr_subs *kr_subs_create(int w, int h);
// Preferred external subtitle language aliases (e.g. ger|deu|de), normalized by Kodi; set before loading a file.
void kr_subs_set_language(kr_subs *s, const char *lang);
// Local file: .ass / .ssa through libass, .srt / .vtt parsed here (UTF-8, else Latin-1), .sup / .idx + companion
// .sub decoded lazily with a bounded bitmap cache. Backward requests replay the subtitle input. 0 on success.
int kr_subs_load_file(kr_subs *s, const char *path);
// Events from a source stream: opens its decoder (FFmpeg's ASS header goes to libass). 0 on success.
int kr_subs_open_stream(kr_subs *s, struct AVStream *st);
// One packet of that stream: decoded, its events added once (a packet seen again after a seek is skipped).
int kr_subs_feed(kr_subs *s, struct AVPacket *pkt);
// Restart embedded decoding before an independent seek/preroll (clear bitmap state, preserve text deduplication).
void kr_subs_reset_stream(kr_subs *s);
// One event: an ASS dialogue body ("Layer,Style,Name,MarginL,MarginR,MarginV,Effect,Text") at [start, start+dur) ms.
// Duplicates (same start and body) are ignored.
void kr_subs_add(kr_subs *s, const char *body, int64_t start_ms, int64_t dur_ms);
int kr_subs_events(const kr_subs *s);
// r11: frames kr_subs_blend has drawn something on so far.
long kr_subs_drawn(const kr_subs *s);
// Draws what shows at t_ms onto an 8-bit 4:2:0 frame: data[0] Y, then data[1] interleaved CbCr (nv12=1) or data[1]
// Cb and data[2] Cr (nv12=0), limited range BT.709. Returns 1 when drawn, 0 when absent, -1 on external input error.
int kr_subs_blend(kr_subs *s, int64_t t_ms, uint8_t *const data[3], const int linesize[3], int w, int h, int nv12);
void kr_subs_free(kr_subs *s);
#endif
