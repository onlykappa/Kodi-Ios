# Handoff: state at 2026-11-07 (after build 182 started)

Branch `claude/trusting-euler-kgug98` = draft PR #14. `main` = same commit (b65cf2e). Every change below is
committed and pushed; nothing is only local. Builds are started by hand; commit with `[skip ci]`.

## Builds since r24 (details per build in docs/HANDOFF-PROGRESS.md)
| Build | What | State |
|---|---|---|
| 176 | r24: HEVC prio_speed, 2 hardware video lanes | verified, owner tested (~1.8x real time, upload-bound) |
| 178 | background 32 MB Drive upload thread, Transfers + movie sheet redesign, Play / Play on TV | verified, owner tested |
| 179 | r25 only | not given to the owner |
| 180 | r26: stuck unit remade after 90 s, off-screen CPU decode, Start converting now, audio = original + English | verified, owner tested |
| 181 | r27: upload once (promote + bin), English subtitles only, subtitle uploads on own threads, AllDebrid read-ahead | verified, owner testing (Interstellar ~40 min, works) |
| 182 | r28 keep-awake re-armed on background/foreground, Drive read 4 blocks ahead in parallel, Home hero copy compared without page, quick movies first | **import-review run 42327383714 (#182) running at handoff: verify the IPA** |

r28: pinned in `migration/airplay-ios/source-lock.json` (sha 34b0d61b…, CI run 42326849053) and published
(release kodi-airplay-r28, digest matches).

## Next steps, in order
1. **Build 182**: when run 42327383714 ends, download release build-182, check build.json commit = b65cf2e, airplay
   tag r28, binary sha = candidate of run 42326849053; record in HANDOFF-PROGRESS; give the owner the link.
2. **Transfers says "Nothing is moving right now" at random while converting** (owner screenshot, build 181). Two
   causes, NOT fixed yet:
   - `transfer_history.running(fresh=10)` while `watch()` saves every 10 s: the page reads a record up to ~10+ s old.
     Fix: fresh=30 (and/or save every 4 s).
   - `transfer_history.activity`: conversion counted only if prep `current.updated` < 15 s old; the muxer's progress
     callback stalls while a 32 MB piece uploads. Fix: 60 s, and `prepare_downloads.cards` (line ~846, `<15`) too.
   Add tests in scripts/test_transfers.py. Ship in build 183 (Python only).
3. **Resume after Kodi is closed** (owner asked: "nice for app updates"). Not started beyond reading the code.
   Plan (kr_prepare.c `prepare()` with a writer): fMP4 with `+empty_moov+default_base_moof+frag_keyframe`,
   `frag_duration` 6 s. Record per confirmed Drive offset of the main track the last complete fragment (unit index,
   end time, fragment sequence, byte offset); on restart: skip units before it, open the muxer with `fragment_index`
   continuing, drop the new init, continue the Drive resumable session (drive_prepare.Sink keeps url + offset) at the
   confirmed offset. The trailing `mfra` must list every fragment: either write our own mfra from the recorded list
   or rebuild it; `kodi_airplay_verify` must pass. Host test: stop mid-file, resume, verify. Sidecars (.sup) and the
   audio tracks need the same treatment. Big change: its own native release (r29) and build.
4. Elementum download settings checked (rate limits 0, connections auto, DHT on): left as they are.

## Owner decisions in this session
- Prepare everything ahead of time once; only Umbrella streams play live.
- Upload once (new Drive file id; watched/resume may reset once: accepted).
- Keep only the original audio + English, and only English subtitles (untagged ones kept). No lower picture quality.
- Quick (repack-only) movies before re-encodes; Start converting now overrides; Prepare next waits its turn.
- Conversion must keep going in the background (keep-awake) and never freeze.

## Known numbers (owner's iPhone 16 Pro, his line)
- AV1 4K HDR re-encode: ~2.5x real time with 2 hardware lanes (chip-bound); Inception ~1 h.
- Drive upload: 32 MB pieces 3-4 s on a good line (8-10 MB/s), 6-17 s when the line is busy.
- Copy-only 4K (Interstellar 8.4 GB): ~40 min in build 181; 182 should be faster (parallel reads).
