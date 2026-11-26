# Preserved third-party sources (reference copies)

Source of two add-ons the Kodi iOS provider fallback uses, kept here because their upstream repository (`kodifitzwell/repo` on GitHub) began answering 404 on
2026-11-24 (ISSUE-470). They are **for reading** (an agent that needs to see how POV works); the build does not read this folder. The build's copy is the archive in
the release `provider-sources-1` (`plugin.video.pov-6.11.03.zip`, `script.module.magneto-6.11.01.zip`), checked against the sha256 in
`migration/provider-fallback/source-lock.json`.

- `plugin.video.pov/` POV 6.11.03, `script.module.magneto/` 6.11.01. Both are GNU GPL v3 (`<license>` in each `addon.xml`); their authors keep their copyright.
- Where they come from: the reviewed trees that shipped in build 679's IPA (`Payload/Kodi.app/AppData/AppHome/addons/`), because the upstream archives could no longer be
  fetched. Bytecode is left out, and POV's background service is already disabled in `plugin.video.pov/addon.xml` (`remove_services`), as the build does it.
- Left out of this folder, because the repository only keeps text of types `.py .xml .json .po .md`: the add-on artwork (`*.png`), a text file or two and one `.pdi` data
  file. The release archive has everything.
- One value is replaced: the default of `tmdb_read_token` in `plugin.video.pov/resources/settings.xml` is an access token its author embedded; it reads
  `REDACTED-UPSTREAM-DEFAULT-TOKEN` here (a token never goes into Git). The archive in the release is byte-exact.
