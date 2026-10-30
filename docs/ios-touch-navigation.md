# Arctic Fuse iOS Touch-r1 — failure repair candidate

The owner reports the previous customized IPA launches and Fuse displays, but navigation/settings are inaccessible and widgets show No Results. Owner had to select Fuse manually, saw no Keep Skin prompt, and two-finger-right swipe opens no menu. Screenshot and statements are failed device evidence; the raw image remains private. This revision is host-tested, not yet phone-verified.

## Findings and limits

A deterministic setup error is reproduced: Kodi's [iOS settings](https://github.com/xbmc/xbmc/blob/a3a448d26b8d560a65655dab2cd122994dc4e146/system/settings/darwin_ios.xml) hide input.enablemouse, and the [settings API](https://github.com/xbmc/xbmc/blob/a3a448d26b8d560a65655dab2cd122994dc4e146/xbmc/interfaces/json-rpc/SettingsOperations.cpp) rejects invisible settings. Old initialization rolled back before activating Fuse. The failed marker also prevented retry. Both are fixed; the phone journal is still needed to confirm this was its precise path.

Home depends on generated includes and focus IDs 300/400; the old seed disables its submenu and focuses widget content. There was no independent permanent Settings entry. Static menus and safe hub focus now remove that dependency. Preserved local in-progress playlists/videodb widgets can legitimately be empty without a phone library; no media DB or credentials were bundled. The screenshot does not prove network/auth failure or successful menu generation. Definitions/artwork/widgets remain intact; no fake populated rows are added.

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

Elementum stays deferred; no new playback architecture, Phase 5, merge or release. Artifact/checksum will be added after actual hosted build.
