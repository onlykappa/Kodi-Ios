# Elementum cloud routing and storage-free preparation: Elementum without movie files on iPhone storage

The November 5 device log confirms that source selection still reached Elementum `/play`, added a 4K torrent with file storage, and chose `Documents/Elementum Downloads`. The existing delayed adoption cannot prevent this initial local download. The same log includes an unrelated live AirPlay conversion from a debrid URL; that is not a prepared Drive download.

## Behavior

Elementum's Python navigation inspects both initial requests and source-picker redirects before `/play` or `/download` reaches the engine. The dedicated Download action follows the same intercepted redirects. After choosing a torrent, the user chooses **Download only** or **Download and watch after preparation**. Both queue AllDebrid → Drive → preparation. Cancelling, invalid metadata, or missing accounts consumes the request without falling back to a local torrent. A verified prepared copy of the same title/episode at the selected quality opens directly.

Watch requests wait for the Drive checksum/profile marker and an idle player. They open the Drive add-on's playback URL once. New requests cannot be lost when the background service saves a long-running transfer's checkpoint.

## Preparation and storage

KodiAirPlay r16 adds callback output and remote verification. Source bytes are read through the existing authenticated loopback Drive proxy. Audio/video conversion readers hold their current six-second unit in RAM instead of spooling full tracks to disk. Output is a completed fragmented MP4 with its fragment index and finite movie/track durations in the initial header, uploaded in bounded 8 MiB chunks (small subtitle streams use 256 KiB chunks). PGS subtitles use the same callback path and remain small separate subtitle files.

A temporary object in `Kodi Downloads/.Preparation` is validated over HTTP for duration, track count, resolution/HDR and seek index. The app then streams it into a resumable update of the original movie ID, verifies its checksum, marks it ready and permanently deletes the app-owned temporary movie. Moving it to Trash would still consume quota; the follow-up corrects that cleanup from the 164 candidate. A separate cleanup journal survives process exits and library rescans, even when the completed preparation job is removed. One final movie remains. The original stays intact while conversion, validation or an incomplete update fails. Completed staging objects and update sessions survive a restart. Old local preparation checkpoints are removed when the new worker runs.

Phone CPU, RAM and Wi-Fi still do work. Drive does not execute the converter. The staging-to-original update adds network traffic to preserve existing Drive IDs and validate before replacement. There is no permanent second AirPlay movie, resolution downgrade, or movie-sized local input/output.

## Validation

The host native suite covers packet preservation for H.264/HEVC including 4K/HDR metadata, streamed audio/text conversion, PGS preservation, callback failure, remote validation and a 20-minute seek over HTTP. Python tests cover both prompt choices, cancellation, account failures, existing copies, watch sequencing, queue-save races, bounded upload buffers, checksum/range failures, interrupted replacement and restart recovery.

Host tests cannot verify the owner's Roku decoder or iPhone VideoToolbox behavior. The selected codec/resolution remains unchanged for supported H.264/HEVC sources; receiver support still determines playback. The IPA must pin the new framework candidate before distribution. No claim of device validation is made from host tests.
