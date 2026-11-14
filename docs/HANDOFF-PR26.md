# Handoff: PR #26 (branch `claude/preparation-repair`), 2026-11-14

Read first: AGENTS.md, docs/design/APPLE-UI-POLICY.md (for any UI work), docs/ISSUES.md ISSUE-226 to ISSUE-249,
docs/DECISIONS.md DEC-047 and DEC-048, ROADMAP.md. Rules: never merge, release or build an IPA without the owner's OK in
the current request; `python3 -B scripts/check_project.py` before every commit (run Python with `-B`, or __pycache__
fails it); new tests go in `.github/workflows/import-review.yml`; log every fix in docs/ISSUES.md; never offer AI Upscale in
quality messages; owner approves mockups before UI is coded. Native converter changes: read the airplay-remux host-tests
job as well as the framework build before pinning a KodiAirPlay release.

## State

- Owner's last IPA: **build-393** (8aa612d): everything through ISSUE-245.
- Committed and pushed after build-393, **not built**: ISSUE-246 (Refresh inspection waits while downloads are made ready;
  upload pieces grow on a steady line), ISSUE-247 / DEC-048 (smart Refresh; hold Refresh = Check Every Video), ISSUE-248
  (preparation carries on after a rename; version picker opens on Back), ISSUE-249 (rig render fixes).
- The owner asked for these recommendations and then an IPA. **Next step: finish the open items below, then build the IPA
  (`import-review.yml` workflow_dispatch on this branch; the release is `build-<run number>`) and send the link.** The
  owner said "push the ipa", so building is approved for this batch.
- All 96+ scripts in the import-review test list pass on the host (one known environment-only error in
  test_build193_pages `test_landscape_airplay_sheet_unchanged`: `git show` in a shallow clone).

## Open (do these)

1. ~~Done 2026-11-14: rig shows both glyph tiles.~~ **Re-render the Download problems choice sheet in the desktop Kodi rig** after the `choice_sheet.glyph_path` fix
   (ISSUE-249): tiles must show the eye-slash and trash glyphs, no bare squares. How: `python3 -B scripts/kodi_rig.py start`,
   `sync`, write fake data with the script below, `open copy_problems`, `click 9201`, `shot NAME` (screenshots stay out of
   Git; they are in ~/.cache/kodi-rig/shots). The fake Library data script used this session was in the scratchpad
   (not in Git): it writes drive-library.json (`tv:` with one show, `tv:<id>` with episodes), drive-library-art.json
   (`tv:<title lower>:<year>` → tmdb_id, `season:<tmdb>:<n>` → titles/thumbs), a preparation state (prepare_downloads.save)
   and two failed debrid jobs (debrid_drive.save) into ~/.cache/kodi-rig/home/.kodi/userdata/addon_data/service.kodi.ios.bootstrap.
   A Trakt 401 dialog may cover the rig: `builtin "Dialog.Close(all,true)"`.
2. ~~Done 2026-11-14: no square highlight.~~ Re-render the show page's ••• capsule after its focus change (no square highlight).
3. Optional (owner dislikes "…"): Download problems row titles truncate ("Naruto Shippuuden · S…"); would need the
   row to wrap or shorten (approved page; small change, mention to the owner).
4. Build the IPA, send the link, update the PR #26 description (ISSUE-246 to ISSUE-249 are not in it yet).

## Needs the owner's phone

Smart Refresh and Check Every Video; uploads while a season is made ready; AI Upscale only on request; Repair skipping
dead/low versions and its live "Looking for 1080p…" ✕; show page ••• menu, Select toolbar and Better Version (old file to
Trash after the new one is saved); Don't Show Again; no "Window id does not exist"; DVD subtitles shown; AI Upscale hold menu
and Cancel All; waiting for Wi-Fi on mobile data; deleting while converting.
