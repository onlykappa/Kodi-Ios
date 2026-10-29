# Kodi iOS Migration

Review baseline for moving a customized Kodi 21.3 Omega setup from Steam Deck to an iPhone, with personal Google Drive media kept separate.

This first pull request preserves a sanitized configuration snapshot and an inventory so the owner can review the starting point and decide the roadmap. **It is not an installable iOS configuration.** No iPhone runtime testing has happened.

## What is here

- `snapshot/userdata/`: 34 sanitized configuration files: both custom skin settings, menu/widget definitions, custom player definitions, two keymaps, 14 smart playlists, source placeholders and four safe GUI preferences.
- `inventory/addons.json`: all 79 user and 161 bundled manifests, dependencies, versions, enabled state where registered, and provisional review categories. Overlapping bundled/user versions are recorded separately.
- `reports/`: full-backup verification metadata, snapshot hashes, reference inventory and local validation results.
- `docs/`: inspection findings, sanitization policy, compatibility review, recovery notes and roadmap questions.
- `scripts/check_project.py`: automated checks using only Python 3's standard library.

The full backup stays offline from this repository. It includes private settings, histories, databases and cached files and must never be pushed. A separate verified private account-state bundle preserves raw saved keys, logins, tokens and account databases for selective transfer. Neither archive is published. The working Steam Deck setup has not been modified.

## Decisions already made

- Umbrella will not be used on iOS. Its references are preserved only as historical baseline evidence; cleaning them up belongs to a later migration change.
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

Master plan: [ROADMAP.md](ROADMAP.md). Resume from [docs/PROGRESS.md](docs/PROGRESS.md); implementation awaits owner approval.

Phase 2 static deliverable: [migration/ios](migration/ios) and [configuration review guide](docs/ios-configuration.md). Preferred official foundation is matching 21.3 ARM64; exact iOS 27.0.1 behavior and fully bundled configuration remain unverified. This is not a built IPA.

Phase 3: [Drive comparison and approved architecture](docs/google-drive.md). Host streaming preflight is blocked by local socket permissions; the integration is not ready. [Visual validation plan](docs/visual-validation-plan.md) adds real source comparison, simulator feasibility, device screenshots and final owner screenshot review for future authorized phases.
