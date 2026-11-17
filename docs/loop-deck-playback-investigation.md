# The Loop playback investigation — Deck and iOS

The owner reports a stream playing on the Deck. Kodi's log independently shows HLS demuxing and audio/video stream creation at 19:19 on 2026-11-16.

## Deck versions and locations

Kodi 21.3, The Loop 8.4, JetExtractors 3.3.33, ResolveURL 5.1.213, inputstream.ffmpegdirect 21.3.8, inputstream.adaptive 21.5.22. JetProxy add-on version is unknown; no separate add-on was found. User add-ons live under `special://home/addons` (Flatpak host: `~/.var/app/tv.kodi.Kodi/data/addons`); binary add-ons under `special://xbmcbinaddons` (`/app/lib/kodi/addons` inside Flatpak). Relevant IDs: plugin.video.the-loop, script.module.jetextractors, script.module.resolveurl.

## Observed playback

The Loop's JetExtractors flow identified FawaNews, displayed two nested choices, and invoked Player.play. Kodi VideoPlayer opened a loopback HTTP address, not a web player. inputstream.ffmpegdirect used HLS, is_realtime_stream=true, MIME application/x-mpegURL and FFmpeg AVFormat. It opened H.264 video and AAC audio. Loopback proxy is JetExtractors' StreamProxy, supported by the readable FawaNews source and log; this does not establish a separate JetProxy add-on. The page embeds a Clappr web player, but this playback uses Kodi VideoPlayer.

In `script.module.jetextractors/lib/jetextractors/extractors/fawanews.py`, get_items builds event links; get_links extracts player HLS addresses, calls get_stream_proxy and creates a JetLink with User-Agent/Referer and FFmpegDirect defaults. On proxy creation failure the code falls back to direct adaptive HLS. If no stream is found, iframe links are handed to ResolveURL. This is source behavior; the selected nested link's full provenance is not independently logged.

`util/stream_proxy.py` forwards to `util/proxy_server.py`: StreamProxy binds 127.0.0.1, merges default and per-entry headers for upstream manifests and rewrites playlist URIs, including EXT-X-KEY, to local segment routes. Inspect the segment handler and session handling before asserting exactly which headers/session data reach every request. Actual source-issued cookies or tokens and key requests are unknown from the sanitized log; do not invent or copy them. Proxy logs can contain upstream headers at debug level and must be sanitized.

The Loop's default.py and its jetextractors plugin are obfuscated; they were not decoded. Their exact routes/functions therefore remain unknown beyond runtime messages. No official matching release comparison was completed; local modifications relative to official versions remain unknown. Installed FawaNews source SHA-256: f8c501239f1790d7f4066a3a293e91f1100855d7ff74f5d2cc34e449c98512c0; stream_proxy.py: 94fcb793fe6016e5e2a07775011626fb8fb37a33d1f6dab36fd34e0f42df0926; proxy_server.py: 63cd95c9e567e93ef3cd84320f6bba5a9094649aa874992251aa1beed563400d.

## iOS next steps

1. Identify the actual installed IPA and add-on versions; the repository configuration excludes Loop and JetExtractors but the owner reports the phone lists games, so it may differ from this snapshot.
2. Obtain a sanitized iPhone log from selecting the same provider and source; compare failures in resolver, local server startup, HLS requests and player opening. Preserve host/status while removing URLs, cookies, credentials, identifiers and tokens.
3. Verify an iOS ARM64 ffmpegdirect binary compatible with the installed Kodi version, loopback networking and Python dependencies, including script.module.go where required. Do not transplant Linux binaries. Test playlist, segments and keys with the source's legitimate session data.
4. Package an isolated IPA candidate with the needed compatible components and sign with the owner's existing process. Confirm playback on device. A host build alone does not establish iPhone success.

No source installation was altered. No authorization checks were bypassed. The IPA foundation and prior GitHub Actions artifact were not available locally during this investigation.