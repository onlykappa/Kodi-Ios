# PR 13 verification

## Changes

- Unsupported PQ/HLG HDR sources can be converted to HEVC Main10 at their original dimensions. Compatible H.264/HEVC picture streams remain bit-for-bit copies. HDR transfer/primaries/range and static mastering metadata are preserved; no second permanent AirPlay movie is created. Dolby Vision sources that require RPU remapping are retained with a specific explanation rather than silently changing their picture.
- An independent worker heartbeat keeps background work armed while opening a large file's track/index information. Library and Notifications show the inspection phase without a misleading numeric 0%. Drive media opens retry transient failures; inspection has a cancellation/deadline; upload acknowledgements are reconciled before replay.
- Background transfer settings take effect without restarting. AllDebrid work, pending preparation and cleanup jobs keep the service armed. Native status records when iOS interrupts or fails to start the silent audio session.
- Settings uses the in-place iPhone search field, with matching Kodi and app settings beneath it. Search context preserves movie searches. Notification and Library sheets use a shared clean X. Transfer cards use cached posters with separate bounded artwork lookups; filter labels fit their buttons.
- Build/session diagnostics, detailed exceptions and a redacted Files export are described in [diagnostic-logs.md](diagnostic-logs.md).

## Released artifact

[Build 168](https://github.com/onlykappa/Kodi-Ios/releases/tag/build-168) passed the final 49-suite workflow (813 Python tests). The downloaded IPA was checked against all 63 runtime source files and their Python 3.11 bytecode, both pinned native frameworks, build metadata and Elementum routing hooks. Its SHA256 matches GitHub’s published asset digest. [Machine-readable verification](pr13-build168-verification.json).

## Automated verification

The full host native suite passed **1,890 checks**. It exercises media from files and a real HTTP Range server, output indexes, long seeks, overlapping segment requests, stalled input, receiver routing, video/audio conversion, subtitle paths and bounded streaming output. The targeted preparation/HDR run passed **517 checks**, including AV1 PQ/HLG, H.264 High10 HDR, HEVC 12-bit and 4:2:2 HDR. The HDR reference encoder is test-only libx265; the iPhone build uses VideoToolbox and remains LGPL.

All 46 suites in the initial Python workflow run passed (780 tests). Subsequent focused checks cover the final search changes, wrapped/full log records, artwork, worker heartbeat, network retries, lost intermediate/final upload acknowledgements, diagnostics/redaction and packaging. GitHub independently built the iPhone framework and passed its full host suite in [run 42213336835](https://github.com/onlykappa/Kodi-Ios/actions/runs/42213336835). The archive hash and new exported APIs were verified before pinning KodiAirPlay r17. GlassBar r6 compiled successfully in [run 42213340544](https://github.com/onlykappa/Kodi-Ios/actions/runs/42213340544).

## Rendered Kodi walkthrough

An isolated Debian container runs Kodi 21.2 with the current portrait XML/controllers at 603×1167 under Xvfb. It uses synthetic library/queue/notices and a local cached poster, with no signed-in account or real torrent. Tests inspected Settings, search results/selection, Notifications, message log detail, Library status and item detail, clean close controls, filter labels and log export. Mouse/keyboard input stands in for touch.

[Rendered screenshots](pr13-simulation/) show the synthetic test data, not a real device playback session.

The walkthrough found and corrected truncated filter captions, a missing library-cache poster path, and single-line log rows. Log rows now wrap; selecting a record opens the complete text. Export produced a build-labelled file and success dialog, using the installed build metadata from the rig's base bundle.

The Settings search result renderer was exercised by injecting query text into the same Home property used by the native field. Linux cannot render UIKit's keyboard/search overlay. Existing controller tests cover context changes, keyboard focus/cancel and preservation of the movie search.

## Device checks still needed

A desktop renderer and protocol tests cannot verify an actual iPhone's VideoToolbox HDR encoder, touch/rotation, locked-screen audio/background execution or a Roku's AirPlay decoder. Test the new IPA with the actual Inception/Interstellar sources, a twenty-minute forward/backward seek, changing apps and locking the screen. iOS can interrupt background processing for calls or resources; a powered-off phone or force-quit app cannot continue processing. Unsupported receiver codecs/HDR profiles are not made universally playable merely by using an MP4 container.
