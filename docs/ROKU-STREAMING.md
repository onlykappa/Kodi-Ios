# Roku streaming from the existing Drive library

Use Play on TV → the Roku / Media Assistant route first for a 4K movie. Kodi fetches the same Drive file and serves
separate video/audio HLS renditions to the TV. Compatible H.264/HEVC video keeps its resolution and encoded picture;
there is no required local download, separate media server, or Apple TV box.

The first segment is buffered before launching Media Assistant. Older prepared movies can have longer keyframe
windows; those are advertised with their real durations, so opening one can take longer. New preparations aim at
six-second fragments with frequent keyframes. A slow first read can therefore keep Kodi opening
the movie for a while; the TV is launched once video and audio are available. After launch, playlist access alone
is not success: Kodi waits for video delivery before stopping its own player. Keep Kodi open on the iPhone while
using Media Assistant; it is the streaming server. Existing background work slows during casting.

Roku's built-in AirPlay remains an alternative. The prepared-file path uses progressive byte ranges; a rejected
stream can restart once as H.264 with separate audio. That compatibility conversion is limited to 1080p SDR, so
use Media Assistant to test retained 4K first. A successful framework build cannot establish either receiver's
actual decoding behavior.

For testing the repaired build:

1. Install it as an update, preserving the current Drive/account setup. Open the same prepared 4K movie.
2. Choose Media Assistant. Allow the opening/buffering step to complete; verify picture, sound and advancing time.
3. Play for at least five minutes, seek forward several minutes, then back. Repeat with the second movie.
4. Try native AirPlay separately. Record whether it uses the original picture or the compatibility restart.
5. If either fails, retain the new Kodi log. It now separates initialization, lane waits, measured source I/O,
   first video delivery, and cancellation. Note the Roku's message and the time of the attempt.

Practical recommendations:

- Use a 4K-capable Roku for 4K HEVC. Roku documents Main/Main10 through level 5.1 and up to 40 Mbit/s for 4K models;
  a model without that support requires a compatible video conversion.
- For sustained high-bitrate playback, keep the phone and TV on a strong local connection (5 GHz or Ethernet for
  the TV when available). This is a throughput recommendation, not a diagnosis from the old warning.
- Judge the next attempt by actual video delivery and measured source read times. A movie stored in Drive still
  travels from Drive to the phone and then across the local network to Roku; “downloaded” in the Drive workflow
  does not by itself mean those bytes are already on the iPhone. No workflow change is required for this repair.

References reviewed: [Roku media documentation](https://developer.roku.com/dev/docs/media) and
[Apple AirPlay guidance](https://developer.apple.com/design/human-interface-guidelines/airplay).


Wi-Fi is the local iPhone-to-Roku link; it can work without an internet connection when the complete movie is
available to Kodi offline. The installed Drive playback helper caches resolved URLs, then requests authenticated
Google media byte ranges. Its URL cache is not a complete offline movie. A Google Drive app's offline storage is
also separate from Kodi's sandbox. If playback with Wi-Fi off uses mobile data, it still has internet access.
A direct Roku download requires a TV-readable URL and compatible media/authentication. Private Drive URLs need the
Google credentials handled by the phone's bridge; account permissions and file visibility are unchanged.
