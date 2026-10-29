# iPhone foundation and packaging evidence

Checked 2026-10-29. Target facts are owner-reported, not measured on a connected phone: iPhone 16 Pro, iOS 27.0.1, ARM64, not jailbroken, Kodi not installed. Owner already has a sideloader and explicitly waived tool-specific details for unsigned artifact preparation. Installation is not required during Phase 2.

## Official foundation

[Official iOS download page](https://kodi.tv/download/ios/) lists Kodi 21.3 Omega, 64-bit, and a generic minimum iOS 11. [Official install guide](https://kodi.wiki/view/HOW-TO:Install_Kodi_for_iOS) lists 21.3 stable but says iOS 9+, conflicting with the download page; use the more conservative download-page floor. Neither statement certifies this precise iOS release. The [official ARM64 directory](https://mirrors.kodi.tv/releases/darwin/ios-arm64/) contains `org.xbmc.kodi-ios_21.3_iphoneos-arm64.deb`, alongside 22.0 prereleases. Prefer the matching stable 21.3 candidate over an untested major-version upgrade. This is an official DEB foundation, not a verified ready-made official IPA release.

The install guide documents converting the application into a ZIP containing `Payload/Kodi.app` and naming it `.ipa`. Preserve executable modes, symlinks, resources and frameworks; do not use a third-party repack as provenance. Binary download, checksums, Mach-O/Info.plist inspection, code-signature handling and entitlements verification remain Phase 4 work, not completed checks here. A locally computed checksum will establish reproducibility, not by itself authenticate a third-party download.

Searches of Kodi official downloads/wiki and upstream issues/forum for iOS 27 did not identify explicit iOS 27.0.1 certification. This is a limited negative search result, not proof of incompatibility or absence of any report. Runtime and sideloader compatibility remain UNVERIFIED until the exact signed build is installed and tested on the phone. Never infer success from ARM64 or minimum OS alone.

## Configuration placement decision

Preferred initial approach: prepare an unsigned foundation IPA plus a separate sanitized configuration import. [Kodi data-folder documentation](https://kodi.wiki/view/Kodi_data_folder) describes installed skins/add-ons and user changes in the writable data folder; [userdata documentation](https://kodi.wiki/view/Userdata) separates settings and addon_data. Therefore copying a Linux userdata directory into the application bundle is not sufficient evidence of automatic loading. This is an engineering inference from the documented separation, not a tested bootstrap feature.

Do not invent a fixed container UUID or apply jailbreak filesystem paths to this non-jailbroken phone. Resolve `special://profile/` and `special://home/` from actual target logs/file manager. Confirm available file import/transfer access on-device before promising a one-step installer. Retain the requested bundled experience as a Phase 4 investigation: a first-run resource-to-profile import must be proven, idempotent and avoid overwriting existing settings; otherwise use the documented separate import. The owner must review this deployment tradeoff before calling a separate import equivalent to a fully preconfigured IPA.

Pure data skins/resources may be candidates for bundling before signing, but writable/generated skin data and account state require separate handling. No custom executable, first-run installer or changed entitlements are silently introduced. Native add-ons require iOS-compatible binaries included/signed appropriately, not Linux `.so` files. Include no passwords, tokens, account state or personal media in either public configuration or IPA. Private account restoration remains a separate selective operation.

## Compatibility sources and limits

- [Arctic Fuse 3 upstream](https://github.com/jurialmunkey/skin.arctic.fuse.3): preserve source skin preference/configuration and helper dependencies; no iPhone support promise found.
- [Touchscreen feature requests](https://github.com/jurialmunkey/skin.arctic.fuse.3/discussions/categories/feature-requests): October 2026 report of unusable touchscreen. A user report is risk evidence, not a reproduced failure or a maintainer compatibility verdict.
- [Kodi 21.3 touch keymap](https://github.com/xbmc/xbmc/blob/21.3-Omega/system/keymaps/touchscreen.xml): authoritative gesture syntax; coordinate tap and pan do not establish that every Fuse control supports touch.
- [Elementum upstream](https://github.com/elgatito/plugin.video.elementum): published native platform table omits iOS, distinguishes macOS ARM64, and suggests a remote client/server mode for unsupported systems. Native executable payload is not suitable to copy; remote-server compatibility/hosting is unverified and requires later owner choice. No source Deck server is enabled.
- [InputStream Adaptive upstream](https://github.com/xbmc/inputstream.adaptive): segmented-stream and DRM support are platform-specific. No Linux CDM or InputStream binary is copied; exact iOS build availability and each playback path need target tests.

Failed retrieval evidence: three guessed raw source paths returned cache misses; the tagged official GitHub contents API worked. No inferred source behavior was asserted from those failed reads. Signing entitlements must be derived from the actual foundation and provisioning capabilities, not fabricated from a generic entitlement list.
