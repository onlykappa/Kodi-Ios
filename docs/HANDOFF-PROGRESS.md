# Kodi iOS — live progress (updated 2026-11-06 ~12:55 UTC)

## Branches
- **`fix/elementum-cloud-164` (PR #13): current work.** Codex continued here from `feature/library-status` (`2b3cbb6`) and produced builds 164–168. KodiAirPlay r17, GlassBar r6, portrait r23. Its notes are in `docs/pr13-verification.md`, `docs/elementum-cloud-downloads.md` and `docs/diagnostic-logs.md`.
- `feature/library-status` (PR #12): older; everything on it is included in PR #13.
- PR #11 (Apple UI guidance): stays open and untouched. PR #9 and #10 are merged.
- Always commit with `[skip ci]`; builds are started by hand (import-review.yml).

## Builds
| Build | Branch | State |
|---|---|---|
| 163 | feature/library-status | AllDebrid→Drive, folders, r15. Verified |
| 164–168 | fix/elementum-cloud-164 | Codex: r16/r17 storage-free preparation, HDR re-encode, native Settings search, diagnostics/export. 168 tested by owner (log `Kodi-build-168-…log`) |
| 169 | fix/elementum-cloud-164 | This session: fixes from the build-168 log (below). Building |

## Build-168 log findings (owner, 04:31–04:42 local)
- Inception (2010): AV1 10-bit HDR 3840×1600, copy=False, so it needs a full re-encode. It stayed at "0%" with about 79 MB read in 3 min. Kodi restarted at 04:39 and the conversion restarted.
- Fall 2 (AllDebrid → Drive, 18.1 GB): 52 MB copied. Codex measured 76–86 s for Drive to acknowledge each 16 MB (~0.2 MB/s), while the conversion was using Drive at the same time.
- Settings search: "Control 9160 in window 13000 has been asked to focus, but it can't". The search page was hidden while the field was empty, but its modal dialog stayed on top, so taps went nowhere and Back was hidden.

## Build 169 changes (this session)
- Settings search page always visible: before typing it lists Settings' own rows; list focus is set; Back always works (`settings_page.search_window`, `settings_search.py`).
- Each Drive copy chunk logs its source-read and Drive-send times and MB/s (`driveupload.upload_stream`), so the next log shows which side is slow.
- While an AllDebrid file is being copied into Drive, preparation waits its turn; it resumes afterwards (`debrid_drive.copying`, service loop).

## Lost from the Codex session (hit its usage limit before pushing). Redo if still wanted
- RAM range cache for Drive reads during conversion ("96 repeated reads → 2 upstream fetches").
- Remove the foreground CPU pacing in `Native.convert` (keep it only in the background). Needs a reliable foreground/background signal.
- Show conversion progress without a rounded "0%".

## Open questions
- Is Drive upload really ~0.2 MB/s from the owner's network? Build 169's chunk timing will show.
- Inception's AV1 4K HDR re-encode on the phone may take many hours. An alternative is to download a different (HEVC) version.
- The TCL Roku TV may play only the sound of HEVC.
