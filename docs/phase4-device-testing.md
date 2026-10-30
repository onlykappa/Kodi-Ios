# Owner device testing — pending evidence

Target facts remain owner-reported: iPhone 16 Pro, iOS 27.0.1, non-jailbroken; existing sideloader, initially no Kodi. No actual iPhone or simulator screenshot has been captured. No mock UI substitutes are provided. Phase 4 cannot pass its exit criteria until the real-device and visual evidence exists.

## Safe installation of a diagnostic foundation

Use only the Actions artifact linked in reports/phase4-validation.json once the job has completed successfully. Download through the private repository's Actions page, extract the artifact wrapper ZIP, and verify the **IPA** SHA-256 against reports/unsigned-ipa-candidate.json. The wrapper ZIP checksum is different. This diagnostic IPA contains official Kodi app resources with active embedded signatures removed; it is **not the completed migrated IPA** and contains no added Fuse, Drive, configuration, accounts or media. Do not use it as proof that migration is complete.

1. Preserve any existing target Kodi configuration privately before replacement. The phone was reported to have no Kodi; verify this has not changed. Do not uninstall an existing target with valuable data without its backup. Never restore anything over the working Deck.
2. Import the `.ipa` into the owner's existing sideloader's IPA selection. Let that tool use the owner's own certificate/provisioning and sign **all nested native libraries/plugins**, not just the main app. Keep passwords/certificates outside this repository. No specific UI labels, certificate renewal period or provisioning entitlement availability can be promised because the owner waived tool identity for preparation.
3. Do not copy jailbreak-only privileges or arbitrary original entitlements into a development profile. The unsigned candidate has no valid signature or provisioning profile. Record the actual signer's entitlement choices/errors and renewal expiration privately. Enable iOS Developer Mode or profile trust only if the actual signing/install method requires it and follow that tool/Apple's instructions; do not assume every sideloader uses the same path.
4. Install through the sideloader, launch once, and report the actual OS/app build and launch result. A load-command or permission error is a failure to diagnose; do not switch Kodi major versions silently. Exact iOS 27.0.1 behavior and signer acceptance remain unverified until this step succeeds.
5. Open Kodi's file manager/settings while still using a clean default interface. Discover the real `special://home/` and `special://profile/` paths, file-sharing access and import method. Save a private clean target recovery copy before importing anything. Do not guess an app-container UUID.
6. Follow [the configuration/dependency guide](ios-configuration.md) and [Drive setup](google-drive-setup.md) only after dependencies and source/layout preservation are resolved. The candidate dependency list is not a complete installed add-on bundle. New Drive authorization requires the owner's private consent; other compatible saved accounts transfer separately and privately.

A sideloader that cannot sign nested Mach-O files or handle this unsigned layout is a deployment blocker. Do not claim generic sideloader compatibility from ZIP integrity alone. Keep failed install logs private and supply only reviewed/redacted error text for diagnosis.

## Functional evidence and screenshots

Use reports/device-capture-roster.json, generated from **every** sanitized original/target Fuse menu/widget file slot plus major application/settings/playback routes. For each row, capture each applicable populated/loading/empty/error state and orientation. Tagged 21.3 source declares landscape-left/right only; attempt portrait and record actual rejection/rotation rather than inventing a portrait UI. Add a row for any discovered custom window/setting page missing from the static roster. No row may disappear to conceal a failure.

Capture the baseline from a verified **isolated recovery copy**, with original media unavailable and original profile never launched or modified. Use the same owner-approved synthetic/licensed fixtures on baseline and phone. Do not connect raw private backups to screenshots intended for GitHub. No owner media uploads or live token revocations are authorized by this checklist.

Record: route/slot ID, fixture, Kodi/skin/helper versions and source hashes, actual device/OS, signer/version (privately if preferred), orientation, resolution, timestamp, action, expected/observed result, capture SHA-256, privacy review, issue/fix/retest links. Keep raw screenshots, personal artwork/media frames, account names and QR codes outside GitHub. Share reviewed images privately with the owner; publish only safe metadata unless publication is explicitly approved.

Test every menu/widget navigation and touch target; text clipping/safe areas; missing dependencies/native add-ons; cold and repeated launches; playback startup/codecs, repeated range seeks, subtitle/audio controls, indexed versus unindexed resume, process eviction and background/foreground; Drive consent/cancellation and normal refresh/network failure. Real token revocation requires a separate deliberate owner choice because it may sign out other devices. See the Drive guide for rate/quota recovery and host-test limits.

Pair every baseline/phone screen side by side with matching fixtures. Preserve original captures; record crop/scale only on comparison copies. Log every inaccessible control, missing widget, unexpected color/layout/font deviation and expected aspect-ratio difference. Fix only target copies, recapture affected and neighboring routes, preserve failure evidence, and retest. Final owner screenshot approval remains a Phase 5 release prerequisite; Phase 5 is not authorized now.

## Rollback evidence required

With target Kodi closed, restore the privately saved clean target profile and verify clean launch. Reinstalling may erase target data; back up first and confirm its actual importer/signing implications. Record the restore procedure, hashes and observed recovery. The source Deck and SSD remain untouched. Installation, selective account restoration, screenshots, side-by-side fixes and actual rollback remain blocked until owner evidence arrives.

## Rebuild the diagnostic IPA without the original installation

Use an isolated Linux environment with Python 3, curl and dpkg-deb (the GitHub job provides these). No original Deck profile, private backup or Google credentials are required. From this repository, select a **new empty** staging/output directory outside Git:

```sh
mkdir -p /tmp/kodi-foundation-rebuild
curl --fail --location --proto '=https' --proto-redir '=https' \
  --output /tmp/kodi-foundation-rebuild/foundation.deb \
  https://mirrors.kodi.tv/releases/darwin/ios-arm64/org.xbmc.kodi-ios_21.3_iphoneos-arm64.deb
printf '%s  %s\n' \
  c80e2e4eded0b3be9f9c8cd19a73e3f3ac7171575dd6f08cfddf14312ca81eb8 \
  /tmp/kodi-foundation-rebuild/foundation.deb | sha256sum --check
dpkg-deb --extract /tmp/kodi-foundation-rebuild/foundation.deb \
  /tmp/kodi-foundation-rebuild/unpacked
python3 -B scripts/build_unsigned_ipa.py \
  /tmp/kodi-foundation-rebuild/unpacked/Applications/Kodi.app \
  --deb /tmp/kodi-foundation-rebuild/foundation.deb \
  --output /tmp/kodi-foundation-rebuild/candidate
```

The builder requires a fresh output directory, preserves modes/symlinks, uses fixed ZIP timestamps and rejects a changed foundation hash. It rejects unsupported native formats and unresolved required bundled dylib paths rather than silently shipping them. System library availability, actual entitlement support and the signer's rebuilding of signature/LINKEDIT data still require the actual phone. The artifact is retained for seven days; download it privately before expiry or reproduce it with the pinned script/source. No stable public release/download is created.

## Actual original entitlement findings

The successful follow-up inspection (reports/ios-foundation-entitlements.json) decoded the original main executable XML entitlement slot. It includes `platform-application`, `com.apple.private.security.no-container`, `com.apple.private.skip-library-validation`, Apple keychain groups and other private privileges. These are public foundation metadata, not owner credentials, and must **not** be copied into an ordinary non-jailbroken provisioning profile. The unsigned candidate removed all active embedded signatures and their original entitlement regions. Its signer must derive permitted entitlements from the actual provisioning method and sign every native image; this has not been tested. Original XML inspection does not audit every DER/provisioning capability or establish that Kodi needs those privileges when sandboxed. The source includes a sandboxed Documents path; actual target access must still be measured.

Two independent hosted downloads/builds produced the identical IPA SHA-256 (reports/ipa-reproducibility.json). Latest retained artifact: https://github.com/onlykappa/Kodi-Ios/actions/runs/40970445429/artifacts/12940141859 . This confirms byte reproducibility in those runs, not signer/device compatibility.

## Current owner evidence and import test update

Owner reports successful diagnostic installation/launch on the stated phone/OS (reports/owner-device-evidence.json); this supersedes earlier pending diagnostic-launch wording only. Separate sanitized import is approved. Use docs/iphone-import.md for the private profile export/stage/transfer/enable/rollback procedure; actual Files access and custom runtime remain unverified. All 184 capture IDs remain, including a YouTube expected-absence check. Engine work is deferred by owner: record the unavailable Elementum choice honestly; no substitute or remote server. Test normal long press, explicit movie/episode choices, TV episode navigation, separate Drive source, empty/error states, relaunch and real rollback. Screenshots must be actual application captures, kept private with sanitized hashes/evidence metadata in GitHub.
