# Google Drive setup, recovery and device-test procedure

Phase 3 delivers a credential-free configuration, reproducible add-on packages and host/mocked tests. These instructions are for a future **authorized Phase 4** target installation. They have not been executed on the iPhone. No Google account was connected during development.

## Preparation and provenance

The target remains iPhone 16 Pro, owner-reported iOS 27.0.1, non-jailbroken, using the owner's sideloader. The intended deployment artifact is an unsigned ARM64 Kodi IPA. Foundation conversion, entitlements, signing, profile import and exact OS compatibility are unresolved Phase 4 work; these add-on ZIPs are not an IPA. Read [foundation research](ios-foundation.md), [configuration import](ios-configuration.md) and [OAuth trust design](google-drive-oauth-design.md).

Use pinned Google Drive **1.6.8** (`f8229d0fbf2f6546536780c1e551caac6e7f8281`) and Cloud Drive Common **1.5.11** (`7d22102557bb95b89abcd2f055597db6f54da05c`). The older Omega catalogue entry is not equivalent. Provenance/file identities are in [source-lock](../migration/google-drive/source-lock.json); archive results are in [package evidence](../reports/drive-addon-packages.json).

The verified source cache and archives stay outside Git. To reproduce from that cache, run from the repository:

```sh
python3 -B scripts/package_drive_addons.py \
  --source-cache /home/deck/Projects/Kodi-iOS-private/drive-source-cache \
  --output /home/deck/Projects/Kodi-iOS-private/drive-addon-packages \
  --private-source-userdata /home/deck/.var/app/tv.kodi.Kodi/data/userdata
```

This reads the source profile only to compare sensitive values; it writes no source files. All 97 pinned inputs are hash-checked. Production ZIPs include licenses, exclude upstream tests/editor files, and are deterministic. No account database, personal STRM, media or original add-on settings are bundled.

| Archive | SHA-256 |
| --- | --- |
| plugin.googledrive-1.6.8.zip | `2ec3cf757e782dcfea86cb4c796a4ab889e44d71e07bbc2ff41a9c3f6011a727` |
| script.module.clouddrive.common-1.5.11.zip | `d54b274fab576d5337f542472a9f166a64fdf2001de0899c4809beadeeb0ab2e` |

## Target installation procedure — pending Phase 4

1. Validate/sign/install the trusted ARM64 foundation using the owner's sideloader. Launch a clean target once; discover its actual writable Kodi profile and save a private clean recovery copy. Never guess the iOS app-container path or overwrite the Steam Deck profile.
2. Acquire and verify Kodi Python 3, dateutil and pyqrcode for the target. The candidate dependency plan is not a downloaded installation; confirm manifest versions and iOS behavior. Stop and record a blocker if dependencies are unavailable. Install common first, then Google Drive, verifying the above versions/hashes. If enabling ZIP installation is required, use it only for these reviewed packages and restore the previous setting afterward.
3. Import the reviewed sanitized configuration using the separate profile-import procedure after skins/helpers are installed. The new home submenu entry opens `plugin://plugin.googledrive/` without account or folder identifiers. Preserve an Estuary/settings recovery route if Arctic Fuse controls fail.
4. Confirm `sign-in-server=https://drive.signinserver.com`, subtitles and resume prompts enabled, directory listing disabled, and folder cleanup disabled. Do not copy legacy Heroku configuration. No automatic media export, deletion or Google login is configured.
5. Add the owner's account privately through the add-on's current pairing/Google consent flow. Keep Safari and Kodi on a consistent network/IP context. Verify the consent is **Drive read-only**, which grants account-wide reads/downloads; a media-folder UI filter does not narrow OAuth authority. Stop for unexpected permissions/endpoints. Never paste passwords, pickup codes, QR captures, account/folder IDs or tokens into GitHub.
6. Browse existing personal videos without uploading media. For library widgets and durable library-indexed resume, investigate the add-on's optional **private** STRM/library export on the target. Review destinations before enabling it; keep cleanup disabled and all personal STRM paths outside the repository and IPA. Raw unindexed browsing resume across restarts is not verified. Do not represent a plain Drive shortcut as already populated Fuse library widgets.
7. Execute the device matrix below and record actual build/device/results before claiming compatibility. Keep any raw account/media captures private; publish only reviewed/redacted evidence.

Accounts live in the add-on's private writable profile/account database. This is not a promise of OS-keychain encryption. Drive was absent from the baseline, so its first grant is new; saved accounts for other compatible add-ons remain separate private migration work. Expired, revoked or device-bound sessions may require reauthentication. Never embed account state in IPA resources.

## Recovery and rollback

| Failure | Diagnosis and bounded recovery |
| --- | --- |
| Legacy sign-in URL | Confirm pinned versions and current HTTPS relay. Upstream announces retirement of the old Heroku endpoint on October 30, 2026. Do not send new grants there. |
| Pairing timeout/403 | Confirm Safari/Kodi network/IP consistency, including VPN/privacy relay effects; generate a fresh short-lived pairing request. Upstream describes a three-minute transient pickup window; this is not an audit of deployed retention. Do not publish pairing details. |
| Expired access token | Allow normal refresh through the approved relay. Host tests cover successful refresh and persistence; confirm actual target behavior privately. |
| `invalid_grant`, revoked token or repeated consent | Preserve a private recovery copy, diagnose provider/OAuth-project state, then request new consent if required. Testing-status OAuth apps may have short-lived refresh grants. Do not repeatedly erase account databases or revoke other devices. |
| Offline/network/relay outage | Keep saved account state, restore connectivity and retry a bounded operation. Source mocks verify failed refresh does not destroy saved state. No guarantee of public relay uptime. |
| HTTP 503 | The pinned OAuth wrapper retains its bounded request retry budget. Capture redacted failure if exhausted; do not add an endless loop. |
| HTTP 429 or quota/download 403 | The current OAuth wrapper stops its call on 429; it does not universally schedule Retry-After. Wait/back off and inspect actual quota/download availability; do not assume 5 TB storage grants unlimited bandwidth, enable billing, or create public shares to bypass limits. |
| Playback/subtitle/resume failure | Capture redacted Kodi/build/version and case details privately, compare a known supported test clip, and log the issue. Library-indexed resume and arbitrary browsed-video resume must be distinguished. Do not edit the original media to make tests pass. |
| Account removal/revocation | Provider revocation can sign out other Kodi devices. Require an explicit owner decision; it is not routine troubleshooting. |

Before any authorized target import, save its clean profile privately. To roll back the new integration, close **target** Kodi, restore that target recovery copy, and verify clean launch. For offline engineering comparison, reconstruct the previously reviewed Phase 2 configuration from its recorded commit into a separate safe copy; do not reset history or restore over the working Steam Deck. Keep private account-state backups encrypted/access-controlled using the owner's chosen private transfer method. Never publish recovery archives or unredacted logs.

## Real-device matrix — all pending Phase 4

Use owner-approved existing clips or privately staged licensed/synthetic fixtures. Creating/uploading media or revoking grants is not implicitly authorized by this plan.

| Case | Required evidence |
| --- | --- |
| First launch, account pairing, browsing and start | Actual signed build/OS, dependency versions, consent scope and redacted result; no credentials/screenshots of codes. |
| Range seeking and restart | Startup latency, forward/backward and near-end seeks, full/open-ended ranges where observable, interrupted connection recovery. Host tests do not establish device codec/network performance. |
| Subtitles | Adjacent supported subtitle selection, sync and on/off behavior on actual playback. |
| Resume | Indexed library prompt, beginning/cancel choices, app exit/restart persistence; separately test unindexed browsing and record unsupported behavior. |
| Authentication recovery | Normal expiry/refresh, offline relay/network recovery and deliberate failed grant using safe fixtures. Any live grant revocation requires separate owner choice. |
| iOS lifecycle | Background/foreground, screen lock, process eviction/relaunch, local-service availability and safe failure handling. |
| Fuse presentation | Every affected menu/widget/settings/playback view and side-by-side source comparison under the Phase 4 visual plan; owner screenshot review before release. |

## Reproducible host evidence

Run the project checks listed in [Phase 3 validation](../reports/phase3-validation.json). The approved [CI run](https://github.com/onlykappa/Kodi-Ios/actions/runs/40940315803) passed all 42 pinned common-module tests. Twelve pinned provider tests and nine pinned-source mocked refresh/resume tests passed locally. The original eight local socket errors remain in their historical report. Cleanup/destructor warnings are retained in ISSUE-016 for lifecycle investigation. These results prove neither live Google authorization nor iOS playback.
