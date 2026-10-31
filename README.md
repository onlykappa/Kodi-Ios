# Kodi iOS Migration

Review baseline for moving a customized Kodi 21.3 Omega setup from Steam Deck to an iPhone, with personal Google Drive media kept separate.

This pull request preserves the sanitized baseline, provisional iOS configuration and validated Phase 3 Drive integration for review. **Owner reports the diagnostic Kodi 21.3 ARM64 IPA installed and launched on iPhone 16 Pro/iOS 27.0.1.** Customized import, visuals, gestures, Google Drive and rollback are not yet device-verified. The owner now requires a single fully bundled unsigned IPA with automatic setup; native Elementum remains deferred, with no substitute or remote service.

## What is here

- `snapshot/userdata/`: 34 sanitized configuration files: both custom skin settings, menu/widget definitions, custom player definitions, two keymaps, 14 smart playlists, source placeholders and four safe GUI preferences.
- `inventory/addons.json`: all 79 user and 161 bundled manifests, dependencies, versions, enabled state where registered, and provisional review categories. Overlapping bundled/user versions are recorded separately.
- `reports/`: full-backup verification metadata, snapshot hashes, reference inventory and local validation results.
- `docs/`: inspection findings, sanitization policy, compatibility review, recovery notes and roadmap questions.
- `scripts/check_project.py`: automated checks using only Python 3's standard library.

The full backup stays offline from this repository. It includes private settings, histories, databases and cached files and must never be pushed. A separate verified private account-state bundle preserves raw saved keys, logins, tokens and account databases for selective transfer. Neither archive is published. The working Steam Deck setup has not been modified.

## Decisions already made

- Umbrella will not be used on iOS. Its references remain in the historical baseline and are excluded from the active iOS target.
- Do not install this baseline over either device's working configuration.
- Do not copy Linux executables to iOS. Transfer compatible saved account state privately, after installing the corresponding add-ons; see [private account transfer](docs/private-account-transfer.md).
- Google Drive media and authentication remain outside this repository.
- Migration work belongs on `feature/ios-migration`; the pull request targets `main` and must not be merged without owner approval.

## Review and check

Read [the inspection report](docs/inspection.md), [compatibility report](docs/compatibility.md) and [roadmap notes](docs/roadmap.md).

```sh
python3 -B scripts/check_project.py
```

On the original Deck, also compare against private source values before a commit or publication:

```sh
python3 -B scripts/check_project.py \
  --source-userdata "$HOME/.var/app/tv.kodi.Kodi/data/userdata"
```

These checks intentionally distinguish documented baseline issues from new missing files or references. Passing them does not mean the snapshot works on iOS.

Master plan: [ROADMAP.md](ROADMAP.md). Resume from [docs/PROGRESS.md](docs/PROGRESS.md); Phase 3 passed independent review; Phase 4 is authorized and has a diagnostic unsigned foundation candidate. Fully bundled IPA is now owner-approved and host-built; customized device acceptance remains blocked pending actual evidence.

Phase 2 static deliverable: [migration/ios](migration/ios) and [configuration review guide](docs/ios-configuration.md). Preferred official foundation is matching 21.3 ARM64; exact iOS 27.0.1 behavior and fully bundled configuration remain unverified. This configuration directory is separate from the diagnostic IPA.

Phase 3: [Drive comparison and approved architecture](docs/google-drive.md). Approved CI resolved the local socket-test blocker (42 upstream tests passed). Credential-free configuration, two reproducible local add-on ZIPs and [setup/recovery instructions](docs/google-drive-setup.md) are ready for Phase 3 review; live authorization/playback and unsigned IPA assembly remain Phase 4. [Visual validation plan](docs/visual-validation-plan.md) adds real source comparison, simulator feasibility, device screenshots and final owner screenshot review for future authorized phases.

Phase 4 partial host evidence: [unsigned diagnostic foundation](reports/unsigned-ipa-candidate.json), [source/skin and simulator findings](docs/phase4-source-findings.md), [owner installation/test procedure](docs/phase4-device-testing.md), and [184-entry capture checklist](reports/device-capture-roster.json). The candidate contains no migrated configuration or added Fuse/Drive add-ons; separate prepared files remain preserved. Device results and screenshots are pending; Phase 5 is unauthorized.

Historical manual-import procedure (superseded): [iPhone import, integrity and rollback](docs/iphone-import.md). Use [automatic IPA instructions](docs/customized-ipa.md) for the current build. Keep the working diagnostic app. The kit is built from reviewed public sources; all private profiles and account transfers stay outside GitHub. [Host evidence](reports/phase4-import-validation.json) and [unchanged Deck verification](reports/phase4-source-immutability.json) are recorded separately from phone acceptance. All 184 screenshot requirements remain. No Phase 5, merge or release authorized.

## Customized IPA ready for device testing

[Download Kodi-iOS-Customized.ipa artifact](https://github.com/onlykappa/Kodi-Ios/actions/runs/41058684326/artifacts/12978745226) and follow [signing, automatic setup and recovery instructions](docs/customized-ipa.md). No manual Kodi ZIP import, file copying or profile transfer is required. This supersedes earlier separate-import instructions. 149 host tests and the actual Linux IPA build pass; no customized iPhone runtime result is claimed. Original diagnostic build remains fallback.

## Current iPhone usability retest

The owner reported Fuse navigation/settings failure in the earlier IPA. Use the revised [Touch-r1 download and retest instructions](docs/ios-touch-navigation.md). Host validation passes; actual iPhone usability has not yet been reverified. Prior IPA is retained for rollback.
