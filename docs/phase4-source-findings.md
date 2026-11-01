# Phase 4 source and platform findings

This is static evidence, not runtime or visual parity. Source originals and media were never altered. Full Phase 4 acceptance remains blocked by deployment choice and actual owner-device evidence; the prepared investigations do not waive roadmap dependencies.

## Kodi foundation and installed source

The installed Flatpak manifest pins Kodi to `a3a448d26b8d560a65655dab2cd122994dc4e146`, the official `21.3-Omega` tag. The acquired official iOS main executable's Info.plist build revision is `20251031-a3a448d26b`, consistent with that source revision. See reports/kodi-source-provenance.json and reports/ios-foundation-inspection.json. This establishes source/build-label provenance, not an independent reproducible compilation or binary equivalence.

The actual installed manifest records Linux GL, ALSA/PulseAudio, DBus, UDev, VAAPI/VDPAU and other Linux integrations. It also applies a Linux launcher patch and an application-metadata patch; its shell step patches add-on manifests. The [launcher patch](https://github.com/flathub/tv.kodi.Kodi/blob/30f8c953d763/patches/kodi.sh.in.patch) sets XDG data paths and `/app/share/kodi`; [metadata patch](https://github.com/flathub/tv.kodi.Kodi/blob/30f8c953d763/patches/kodi.metainfo.xml.in.patch) is separate. None is an iOS startup hook. Full dependency/toolchain rebuild parity is unverified. Linux binaries and system-service behavior are not copied.

Actual pinned source reviewed:

| File | Git blob | Finding |
| --- | --- | --- |
| xbmc/settings/SettingsComponent.cpp | 0f5f7ae8da75fd73cbaf950cf87ad69847783298 | InitDirectoriesOSX separates packaged system resources from writable user home/profile. CreateUserDirs creates user directories; it is not a recursive migration importer. |
| xbmc/platform/darwin/ios-common/DarwinEmbedUtils.mm | f2fa674e22ca5c041ff6f25f418a29fddc8666b5 | Sandbox detection chooses Documents for iOS and Library/Preferences otherwise; the executable's container location affects this detection. Verify actual signed target paths. |
| xbmc/filesystem/SpecialProtocol.cpp | 189ddfa5dcac9c98bf38a4aa3f8b71988a539363 | Runtime special-path registration/translation is separate from bundle storage. |
| xbmc/platform/darwin/ios/Info.plist.in | e29411aa80b82e185633e244f7d431efd8d4c15f | Template enables file sharing/document access and landscape orientations; this is source intent, not proof of target import accessibility. |

Sources: [tagged settings initialization](https://github.com/xbmc/xbmc/blob/a3a448d26b8d560a65655dab2cd122994dc4e146/xbmc/settings/SettingsComponent.cpp), [sandbox root](https://github.com/xbmc/xbmc/blob/a3a448d26b8d560a65655dab2cd122994dc4e146/xbmc/platform/darwin/ios-common/DarwinEmbedUtils.mm), [special paths](https://github.com/xbmc/xbmc/blob/a3a448d26b8d560a65655dab2cd122994dc4e146/xbmc/filesystem/SpecialProtocol.cpp), [Info.plist](https://github.com/xbmc/xbmc/blob/a3a448d26b8d560a65655dab2cd122994dc4e146/xbmc/platform/darwin/ios/Info.plist.in).

Engineering conclusion: a separate reviewed first-run import is the conservative initial option. Merely embedding arbitrary userdata in an IPA is not evidence that Kodi loads it. No complete recursive/import-idempotency path has been established by this bounded source review; that is not a claim that every possible source hook was exhaustively disproved. Automatic initialization would require a proven bootstrap and safe no-overwrite behavior, then device tests. The owner deployment choice is pending. No unreviewed executable/bootstrap or entitlement changes are injected.

## Real Arctic Fuse 3 file comparison

Official `v3.4.8` resolves to `aa54dca0fbc01c4b5574fb2819007611a0db6040`. Compared **all 3,344** upstream blob identities against the verified private recovery copy (3,338 installed files). **3,336 match exactly**. Seven upstream-only missing files are repository administration/ignore files, not skin rendering assets. One source file differs and one extra generated file exists:

- `1080i/script-skinviewtypes-includes.xml`: installed generated form has 68 children/10,098 bytes versus the small upstream rebuild-trigger template. Private SHA-256 `c432a33f640c21e71e2c3d349a893829a654caa98ecb197473e55f054f3131c2`.
- `1080i/script-skinvariables-generator-includes-.xml`: additional generated form, 90 children/275,584 bytes; private SHA-256 `571af6b46003a37c9b19df093c0b45719d0d52e8bd11d235e20b1ef4851a05f6`.

These are real source/layout differences, not matching-version assumptions. Both private generated files remain preserved; they are **not silently replaced, deleted or certified portable**. Decide their target regeneration/retention after helper/dependency and first-run import checks, then compare resulting controls visually. No owner-custom file content has been uploaded for this analysis. Upstream source/assets carry Creative Commons Attribution Non-Commercial Share-Alike 4.0 metadata; preserve notices and review redistribution conditions before any release. Kodi license notices also remain with its original resources.

Evidence: reports/fuse-source-comparison.json; reproducible command:

```sh
python3 -B scripts/compare_skin_source.py \
  --private-root /home/deck/Kodi-iOS-Backups/20261029T180632Z/phase1-isolated-recovery/tv.kodi.Kodi/data/addons/skin.arctic.fuse.3 \
  --upstream-tree /home/deck/Projects/Kodi-iOS-private/fuse-3.4.8-upstream-tree.json \
  --report reports/fuse-source-comparison.json
```

The public tree metadata cache was retrieved from the exact upstream commit, is untruncated and is hashed in the report. Tests reject truncated trees/path traversal and distinguish matching/changed/missing/additional files. This comparison does not validate helper Python/native runtime or visual behavior.

## Simulator feasibility outcome

**Infeasible with the available local environment; no simulator executed.** Linux x86_64 has no xcodebuild, xcrun, simulator runtime or Mac access configured. The [actual tagged Kodi iOS build guide](https://github.com/xbmc/xbmc/blob/a3a448d26b8d560a65655dab2cd122994dc4e146/docs/README.iOS.md) explicitly says simulator building is unsupported. The acquired app declares iPhoneOS, not iPhoneSimulator. ARM64 alone does not make it a simulator build.

This is a bounded finding for the current environment and trusted Kodi 21.3 recipe, not proof that no future experimental simulator port could exist. No Mac rental, simulator service, Xcode purchase or new hosting was provisioned. A different simulator-specific build/toolchain would need its own provenance, dependencies and validation. It could never replace the required actual iPhone 16 Pro/iOS 27.0.1 tests or application screenshots. See docs/phase4-device-testing.md and reports/device-capture-roster.json (184 checklist entries; zero captures).
