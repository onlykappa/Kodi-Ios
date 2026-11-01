# Arctic Fuse iOS Touch-r2 — serialized startup repair

The owner reports the previous customized IPA launches and Fuse displays, but navigation/settings are inaccessible and widgets show No Results. Owner had to select Fuse manually, saw no Keep Skin prompt, and two-finger-right swipe opens no menu. Screenshot and statements are failed device evidence; the raw image remains private. Touch-r1 subsequently failed on the phone: the supplied launch log records an early Fuse reload, Estuary reversion and helper failures. Touch-r2 is host-tested, not yet phone-verified.

## Findings and limits

A deterministic setup error is reproduced: Kodi's [iOS settings](https://github.com/xbmc/xbmc/blob/a3a448d26b8d560a65655dab2cd122994dc4e146/system/settings/darwin_ios.xml) hide input.enablemouse, and the [settings API](https://github.com/xbmc/xbmc/blob/a3a448d26b8d560a65655dab2cd122994dc4e146/xbmc/interfaces/json-rpc/SettingsOperations.cpp) rejects invisible settings. Old initialization rolled back before activating Fuse. The failed marker also prevented retry. Both are fixed; the phone journal is still needed to confirm this was its precise path.

Home depends on generated includes and focus IDs 300/400; the old seed disables its submenu and focuses widget content. There was no independent permanent Settings entry. Static menus and safe hub focus now remove that dependency. Preserved local in-progress playlists/videodb widgets can legitimately be empty without a phone library; no media DB or credentials were bundled. The screenshot does not prove network/auth failure or successful menu generation. Definitions/artwork/widgets remain intact; no fake populated rows are added.

## Touch-r2 startup sequencing

The private owner log shows the generated shortcut include is missing before Fuse reloads and reverts to Estuary; queued helpers then read special://skin JSON while the active skin has changed. This supports a reload/confirmation race hypothesis; the exact old RuntimeError was not recorded and is not asserted. Touch-r2 guards helper onloads/reload alarms while activating Fuse. It preserves the native Keep Skin confirmation, then invokes the real pinned view generator and shortcut generator sequentially with no_reload=true. Both must write fresh valid includes; only then is setup marked complete and one controlled reload requested. A skin change, malformed input, stale/partial output, cancellation or timeout fails visibly. Existing completed profiles receive a one-time repair without resetting owner preferences.

Private startup-error.json now includes stage, exception class and stack basename/line/function; no exception message, locals, account path or token is logged by the bootstrap. Do not publish full kodi.log automatically. A host regression cannot prove the original device failure is fixed.

## New navigation

A native Kodi strip is injected inline in 32 major non-dialog windows: **Back, Home, Browse, Settings, Drive, Recovery**. Percentage widths fit supported landscape ratios; large buttons are inset from edges. The strip does not depend on generated shortcuts, item counts or addon content. Hub entry focuses Settings rather than an empty widget. Existing Kodi dialogs and full-screen playback definitions remain unchanged. The intended skin is still Fuse.

Browse/Recovery opens a real Kodi dialog with Settings, Skin settings, TMDb Helper, local videos, Drive, addon browser, focus menu/first row, rebuild views/menus, reload, private diagnostics and explicitly confirmed pre-setup recovery. Routine repair does not switch to Estuary; explicit emergency rollback may return there temporarily.

Tap uses native hit testing, drag uses PanGesture, long press uses Kodi's stock right-click target/context behavior. Two-finger left goes back, right opens the independent menu, up/down page; three-finger tap opens Settings where not overridden by playback bindings. These are configured and statically checked, not demonstrated on the phone yet. Native modal dialogs retain normal Kodi behavior.

## Upgrade and rollback

Install the revised signed IPA as an update if the sideloader supports keeping the app container; do not delete the app to troubleshoot. Repair runs even when the old seed says COMPLETE, backs up changed XML/keymap privately, and preserves source media/widget settings. A recovered failed old seed retries once on the new revision; failure journals/backups are retained in a private history folder. New source files are not blindly copied over owner skin edits. Original IPA remains a separate rollback artifact.

Settings/Recovery are meant to remain usable with zero media results. Private diagnostics records addon enabled flags, generated include presence/sizes/rebuild trigger and bootstrap status, without account values or media names. Use it to distinguish generation/dependency/setup problems during the owner retest. Do not publish raw account logs/screenshots.

## Required owner retest

Verify cold launch, automatic Fuse selection, visible/aligned strip, tap Settings and Back/Home, Browse/Recovery with empty/offline widgets, normal category/menu navigation, drag/page scroll, tap selection and item-specific long press, view/menu rebuilding, relaunch and explicit recovery. Check safe areas/orientation and whether buttons cover content. Record failures with screen IDs and sanitized diagnostics; preserve all 184 existing capture requirements. Compare actual screenshots to the safe-copy Deck baseline; no mockups or fabricated screen evidence.

Simulator: local Apple tooling and a suitable remote simulator are unavailable/unestablished; Kodi 21.3's tagged iOS guide does not support simulator builds. No simulator was run. Physical iPhone testing remains necessary.

Elementum stays deferred; no new playback architecture, Phase 5, merge or release. Touch-r2 build and upload succeeded: [download the revised IPA artifact](https://github.com/onlykappa/Kodi-Ios/actions/runs/41078491846/artifacts/12987708727), expires November 6 UTC. Inside is `Kodi-iOS-Customized-Touch-r2.ipa` (577524657 bytes). SHA-256: `d67b59e286206c5a1b7abaee07d11720de87e2967c28182754c4da3594b7006e`. [Build receipt](../reports/ios-touch-r2-artifact.json). 174 host tests/21 suites pass; actual CI archive/source/seed/dependency/native checks pass (32 windows, 31 seeds, 151 ARM64 images). Actual iPhone retest is required. Sign/install the revised IPA as an update with the existing sideloader, retaining the app container where supported. Extracting the GitHub artifact wrapper is only a download step; no manual Kodi ZIP import is required.

On launch, allow setup to finish and confirm **Keep Skin** if Kodi asks. Do not change skins or request menu rebuild while setup runs. Verify that Settings remains visible with empty widgets, then test Back/Home/Browse/Recovery, normal menus, scrolling and long press, followed by a cold relaunch. Report startup-error.json if setup fails; do not share account credentials. All 184 capture requirements remain pending their actual evidence.

[Touch-r1 failed candidate retained for rollback/history](https://github.com/onlykappa/Kodi-Ios/actions/runs/41068166024/artifacts/12983492116), SHA-256 9c72b195494924fddfa67f24627546ea59f64efe0f04b373647d907e9034db84. [Original customized IPA](https://github.com/onlykappa/Kodi-Ios/actions/runs/41058684326/artifacts/12978745226) remains unchanged with its known navigation failure. The diagnostic IPA is also preserved. Reinstalling an older IPA does not by itself undo changed profile data: use the confirmed Recovery operation for profile rollback; that operation still needs actual iPhone verification. Avoid deleting the app, which can remove its private container.
