# Phase 4 customized test package

Status: READY FOR OWNER DEVICE TESTING. Phase 4 remains BLOCKED and is not complete.

[Download the fixed kit](https://github.com/onlykappa/Kodi-Ios/actions/runs/40981957027/artifacts/12945112472) (GitHub private Actions artifact, expires 2026-11-06 UTC). Extract the wrapper ZIP; it contains the actual import ZIP, public source/integrity report and full synthetic import smoke receipt. **Do not use run 40981565041's superseded kit.**

Inner file: `Kodi-iOS-Customized-Import.zip`, 366643141 bytes. SHA-256:

```text
cc5d7eb7efa62f1f389f67451b3b94ab8d6a0deda15b94d6e66b48f3ea06669e
```

The wrapper digest is different (recorded in reports/phase4-import-artifact.json). The kit contains 38 reviewed add-on packages, 30 configuration files, watch-choice and iOS-only activation helpers, and offline private staging tools. Arctic Fuse 3 3.4.8, helper 6.18.1+ios.1, skinvariables 2.2.10 and approved Drive 1.6.8/common 1.5.11 are included. Other dependencies/versions and upstream provenance are recorded in its import-review-report.json. Foundation-supplied native APIs/Pillow are audited separately; no Linux executables/native engine, owner credentials or personal media are included.

Keep the existing owner-tested Kodi 21.3 app. No new IPA, app overwrite, signing entitlement or native component is required by this profile kit. The previous diagnostic IPA SHA-256 remains 8d20fcc260aebcd11dee8e5c7f2807ec7c0ef24f528fd58ab43e58ba7ea8f212.

Follow [the actual import procedure](iphone-import.md): discover/verify the target profile's Files access, stop Kodi and privately export/back up that folder, use the extracted tools on an isolated copy, privately return the prepared profile, enable copied add-ons through the reviewed helper/Kodi API and select Fuse. Stop if the required device file access is unavailable; no guessed container UUID or live import. Preserve the original target folder for actual rollback. Saved Deck accounts are a separate [private transfer](private-account-transfer.md), never part of this public kit.

Validated: 133 host tests, actual ZIP/dependency closure, 7324 full-bundle add-on files identical after staging, same-kit zero-write repeat, full synthetic clean restore and unchanged source Deck (22463 hashes). These do not certify iPhone behavior.

Remaining device checks: import/activation, Fuse regeneration and appearance, menus/widgets/artwork, single-tap watch selection and long-press context menus, episodes, Drive private consent/playback/seek/subtitles/resume/refresh, relaunch and rollback. Preserve all 184 capture IDs; compare real screenshots against safe-copy Deck fixtures. No fabricated screens or simulator substitution. Final owner screenshot review remains mandatory.

Elementum's phone-local engine is explicitly deferred and unavailable; no primary replacement or external server. YouTube/Fusion are excluded, so YouTube-backed trailers are unsupported (do not install them to resolve a retained trailer button). Umbrella and broken sports integration remain deferred.

[PR #1](https://github.com/onlykappa/Kodi-Ios/pull/1), [task tracker](PROGRESS.md), [issues/failure history](ISSUES.md), [artifact receipt](../reports/phase4-import-artifact.json). Phase 4 is 4/11 complete (36.36%); overall 25/39 (64.10%). Do not start Phase 5, merge or release.
