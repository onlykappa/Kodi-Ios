// kr_source: a GMPlayer byte source (gm_source) over a URL: http(s) with Range requests (Elementum's
// 127.0.0.1:65220 server, Google Drive links) or a local file. Kodi iOS AirPlay remuxer.
#ifndef KR_SOURCE_H
#define KR_SOURCE_H
#include "../gmplayer/gm_stream.h"
typedef struct kr_source kr_source;
// Opens `url`; NULL with `err` filled when it cannot be opened. timeout_s bounds opening and each complete
// read (including retries). HTTP uses bounded ranges; file reads retain normal byte-offset behavior.
kr_source *kr_source_open(const char *url, int timeout_s, char *err, int errlen);
gm_source kr_source_gm(kr_source *s);
int64_t kr_source_size(kr_source *s);
// Reads up to n bytes at offset: bytes read, 0 at the end, negative on error.
int kr_source_read(kr_source *s, int64_t offset, uint8_t *buf, int n);
// Cumulative seek/read time, including reconnect attempts; no URLs or byte contents.
double kr_source_io_ms(const kr_source *s);
// Interrupts waits (stop pressed): reads return errors from now on.
void kr_source_abort(kr_source *s);
// Additional transient interrupt predicate (e.g. canceled speculative conversion). Bind with no active read;
// context must outlive reads. Resetting its condition lets subsequent reads recover through fresh connections.
void kr_source_set_interrupt(kr_source *s, int (*callback)(void *), void *context);
void kr_source_close(kr_source *s);
#endif
