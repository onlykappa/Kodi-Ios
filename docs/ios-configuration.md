# Phase 2 static configuration and review limits

Target: iPhone 16 Pro / iOS 27.0.1 / ARM64 / non-jailbroken. Kodi is absent; installation is a Phase 4 task. See [upstream research](ios-foundation.md) and [target facts](../reports/ios-target.json).

## Deliverable

`migration/ios/` is a reproducible **provisional static import configuration**, not an IPA or a working iOS installation. The Phase 2 review contained 32 text files/48 dependency candidates. The Phase 3 extension now contains 33 text files including the integrity manifest and 51 dependency candidates. Historical Phase 2 reports retain their original counts. Build with `python3 -B scripts/build_ios_config.py`, validate with `python3 -B scripts/check_ios.py`, and run regression checks with `python3 -B scripts/test_ios.py`. The builder reads only the sanitized baseline, never original Kodi state or private credentials. It writes only its dedicated generated project directory; do not place unrelated files there.

The 240 manifest records are classified in `reports/ios-compatibility.json` with source metadata, reasons and evidence. No add-on is certified on this precise OS. Categories distinguish owner exclusions, broken/deferred integration, incompatible existing native implementation, iOS native-build requirements and unverified data/Python candidates. The current selected 51-entry dependency closure records source-version candidates and required numeric minimums, including Kodi API interfaces. These are candidate entries, not 51 downloaded or installed add-ons. Exact iOS repository availability/signability must be checked before activation; do not substitute Linux libraries or silently upgrade dependencies.

## Preservation and intentional changes

All exported skin preferences and menu/widget slots that survive explicit backend exclusions are carried forward. `adaptations.json` maps retained menu labels/locations, changed fields, omitted desktop files and declared empty media folders. It preserves Fuse 3 as the selected skin and Zephyr as an optional candidate. Upstream skin code and resource packs are acquired separately; the original private backup preserves the installed custom skin code/assets. Full parity between local skin modifications and a fresh upstream skin is not certified by these static files and must be reconciled before claiming an equivalent device experience.

- Umbrella player definitions and runtime preferences are removed only from the generated target. Historical snapshot and private backup remain unchanged. Names in the excluded-component inventory are metadata, not enabled references.
- Broken sports integration is deferred with explicit owner approval; no empty JetExtractors manifest is copied. The target dependency graph has no selected missing manifest. The Loop is not claimed repaired.
- Elementum native payload/Burst and Deck Keeper/delete automation are not copied. Former unsupported action paths point to local-library browsing, with each replacement recorded; that is not an equivalent streaming backend. TMDb discovery remains available as an unverified candidate; actual playback providers are not configured. Phase 3 adds a credential-free Google Drive menu entry and preferences; see [setup and limitations](google-drive-setup.md).
- Mounted-media/network placeholders become portable `special://profile/media/.../` folders declared in adaptations. These folders contain no media; create them during target import. Original external SSD paths are never mounted or altered.
- Desktop keymaps are replaced with an adapter using Kodi 21.3 upstream touch syntax: tap, long press, pan, two-finger back/menu and playback gestures. It does not establish that every Fuse control is touch-accessible. Upstream touchscreen problems remain a device-test risk; do not call this a proven skin-level touchscreen fix.
- One opaque/redacted baseline setting identifier is omitted instead of importing an unknown setting; this is recorded in adaptations. Source baseline is retained.

## Non-jailbroken import procedure to validate in Phase 4

1. Validate the official foundation binary/IPA and sign/install using the owner-managed sideloader. Record exact device/build results before making any runtime claims.
2. Launch a clean Kodi once, establish its actual writable profile/data paths through Kodi, and save a clean target recovery copy. Do not use a guessed filesystem container path.
3. Install the reviewed iOS-compatible skin/helper/resource dependencies from official Kodi or Jurialmunkey sources. Validate the selected versions and native PIL/InputStream requirements. Stop if a required compatible dependency is unavailable.
4. Stage sanitized configuration separately. Create declared empty folders, import playlists/menu data and skin preferences into actual target locations; merge the four exported safe GUI preferences only after dependencies are installed. Preserve the target-generated display/audio/network settings.
5. Keep an accessible route to default Estuary settings/file manager as recovery. Test each retained label, widget and touch action against adaptations, plus source-specific skin customizations. If Fuse cannot be operated by touch, record the failure; do not switch skins or drop requested behavior without owner review.
6. Restore saved account state separately and privately only after compatibility checks described below. No state goes into the IPA or public package.
7. Run device tests for launch, layout, all navigation paths, context menus, video OSD, seeking, resume, subtitles and background/foreground. Google Drive live playback is a later integration/device test, not a Phase 2 success.

## Private account-state mapping

For retained add-ons, the private source directory is `userdata/addon_data/<addon-id>/` within the private recovery/account archive. Target destination is the actual target `special://profile/addon_data/<addon-id>/`. Keep settings and account databases together, compare source/target add-on versions and schemas, and review paths privately before importing. Start with TMDb Helper, YouTube and Trakt only if actually installed/compatible; skip Umbrella and deferred sports/Elementum state. Resource/API interfaces have no account-state migration requirement. Do not bulk-copy the entire private archive or Linux guisettings into the phone. Device-bound/revoked/expired sessions may still require reauthentication. No credentials, account identifiers or secret values appear in these mappings.

## Packaging and entitlements

Preferred initial packaging is unsigned official-foundation IPA plus separately imported sanitized settings. A fully preconfigured IPA requires a verified first-run import mechanism that is not implemented here. This tradeoff needs owner review before Phase 4 packaging. Do not infer writable profile import from arbitrary files inside Payload/Kodi.app. Native add-ons, nested frameworks, signature removal/resigning and entitlement capabilities must be inspected on the actual candidate binary. No entitlement profile is invented and no sideloading success is asserted.

Static checks cannot prove iOS 27.0.1 support, sideloader acceptance, dependency binary availability, exact skin-code parity or touch operation. These limitations remain explicit rather than silently certified.
