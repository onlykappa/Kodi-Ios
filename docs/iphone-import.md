# Customized iPhone import — review/testing procedure

Owner has confirmed diagnostic Kodi 21.3 installation/launch on iPhone 16 Pro/iOS 27.0.1 and explicitly approved a separate import. This procedure/package has **not been tested on the phone**. Elementum's phone-local engine is not built; it is not replaced by another primary. The source-choice UI reports that limitation. Google Drive remains a separate source. YouTube/Fusion are excluded by owner instruction; the original Deck and backups remain intact.

## What this package does

The public review ZIP contains sanitized menus/widgets, retained skin settings, playlists, portable paths, view choices, reviewed add-on source ZIPs, source provenance/checksums, and offline Python tools. Patched TMDb Helper requests explicit movie/episode watch choices; TV shows expose episode options. Long press maps to normal Kodi ContextMenu. Host tests are not touch/playback evidence. The custom first-run helper only requests Kodi add-on enable/skin-change operations on iOS; it refuses other platforms. It installs no native engine or background server.

The original generated view expressions are derived from saved view choices. Actual helper generation reproduces all 68 baseline expressions from the original 76 choices. Target YouTube-only view overrides are removed deliberately. Do not copy the old generated shortcut XML cache: the pinned skin startup/rebuild path should generate it from sanitized inputs after activation. This first-run behavior and visual parity remain device tests. Keep all 184 original capture requirements, including explicit owner-approved absence checks for YouTube.

## First phone-side checkpoint — requires owner verification

1. Keep the already working diagnostic app. In Kodi's file manager, establish the **actual** mappings for `special://home/` and `special://profile/`. Tagged iOS source intends sandbox Documents/Kodi and declares file sharing; no container UUID or actual Files-app access has been measured here.
2. Force-quit Kodi before copying its profile. Using the iOS Files app, verify whether **On My iPhone → Kodi** exposes the Documents container and its Kodi folder. If that view is unavailable or the mapping differs, stop and report the access limitation; do not use jailbreak paths or uninstall Kodi to solve it. Apple's desktop file-sharing path is an alternative only if the owner has appropriate existing tools/access.
3. Make a private copy/ZIP of the complete target Kodi data folder. Preserve it untouched outside the app before any replacement. Transfer this owner-exported copy privately to the Deck staging area. Never put this copy, account databases, private keys, logs or screenshots in GitHub. A private configuration transfer is not a media upload or an always-on server.

## Integrity and private offline staging on the Deck

Download the review artifact through the private PR/Actions link and verify the inner `Kodi-iOS-Customized-Import.zip` SHA-256 against the published report/PR. The wrapper ZIP has a different checksum. Extract the inner ZIP into a **new private working folder**, keeping the original ZIP for the apply command. The bundled tools use only Python 3; they do not run Kodi, touch the working Deck profile, copy Linux executables or send data anywhere.

Example paths below are new private staging locations. The owner-exported phone folder must be placed at `phone-export/Kodi`; it is **not** the Deck's `.var/app/tv.kodi.Kodi` folder. Replace `PUBLISHED_IMPORT_SHA256` only with the actual report value; it is intentionally not a fake digest.

```sh
python3 -B tools/import_profile.py prepare \
  --from-export /home/deck/Projects/Kodi-iOS-private/phone-export/Kodi \
  --output /home/deck/Projects/Kodi-iOS-private/phone-work/Kodi
python3 -B tools/import_profile.py apply \
  --bundle /home/deck/Projects/Kodi-iOS-private/Kodi-iOS-Customized-Import.zip \
  --expected-sha256 PUBLISHED_IMPORT_SHA256 \
  --target /home/deck/Projects/Kodi-iOS-private/phone-work/Kodi \
  --backups /home/deck/Projects/Kodi-iOS-private/phone-clean-backups
python3 -B tools/import_profile.py export \
  --target /home/deck/Projects/Kodi-iOS-private/phone-work/Kodi \
  --output /home/deck/Projects/Kodi-iOS-private/Kodi-customized-private.zip
```

These commands must run from the extracted review kit so `tools/` exists. They reject known original Deck/backup paths, symlinks, nested project repositories and unmarked targets. Apply checks archive SHA/CRC/coverage, every nested add-on manifest and required dependency, then stages a new copy with a verified private clean snapshot. Existing target-only GUI/audio settings and account files remain; imported safe settings merge without copying credentials from the Deck. Selecting Fuse is deferred to the owner/helper to preserve a usable default interface. Never copy or edit Kodi's add-on SQLite records to force activation.

Same-bundle repeat imports make zero writes if managed files are unchanged. Changed managed files cause a conflict rather than silent overwrite. Corrupt/missing add-ons or dependency/version failures stop before target changes. Host tests cover partial staging/commit failures and restoring a clean private profile. The final `Kodi-customized-private.zip` contains target-private state and must **never** be uploaded to GitHub or treated as the public import ZIP.

## Transfer and enable — actual phone tests pending

1. Keep Kodi force-quit. Transfer the private customized ZIP back using the owner's trusted private transfer method, extract it separately, and verify its content/ZIP checksum before replacement. Rename/preserve the current target Kodi folder as a private rollback copy, then place the prepared Kodi folder at the measured Documents location. Avoid an ambiguous partial folder merge. If Files cannot perform the required copy/rename safely, stop; do not improvise a live import.
2. Launch Kodi. Newly copied non-system add-ons are discovered **disabled** by Kodi's source-defined database sync; copying files is not an installation/enable success. Keep Estuary until dependencies have been enabled. Verify actual behavior rather than treating this source expectation as a passed phone test.
3. In Add-ons → Install from ZIP, choose the reviewed `script.kodi.ios.first_run` ZIP from the extracted kit's `addons` folder. If Kodi requires the normal unknown-source setting, authorize only this reviewed package and restore the previous setting afterward. Run **Kodi iOS First Run Review** from program add-ons. It validates copied code against the private receipt, requests dependency-first enable operations through Kodi's API, and requests undo of new enables if one fails. Host mocks do not establish actual rollback success.
4. Only after enable requests succeed, accept the helper's explicit offer to select Arctic Fuse 3 and any Kodi skin-confirmation dialog. Preserve an accessible Estuary/settings recovery route. Review the two patched helper components' auto-update behavior so an unreviewed update cannot silently remove the source-choice integration.
5. Test every menu/widget, movie/show/episode source-selection path and normal long-press context actions. The Elementum option remains unavailable until a real iOS engine and player integration exist. Do not enable its native-test route merely to suppress the warning. Do not configure a remote engine or Deck service without a new owner decision.
6. Follow the separate Google Drive guide for private first authorization, subtitles, seeking, resume and refresh tests. No account or folder IDs are preconfigured. Restore other compatible saved account state separately/private only after schema/version checks. Expired/device-bound tokens may still require consent; no universal login-reuse promise is made.

## Rollback

For the host staging copy, use the exact private clean snapshot path returned by apply:

```sh
python3 -B tools/import_profile.py restore \
  --snapshot /home/deck/Projects/Kodi-iOS-private/phone-clean-backups/ACTUAL_CLEAN_SNAPSHOT \
  --target /home/deck/Projects/Kodi-iOS-private/phone-work/Kodi
```

For the iPhone, force-quit Kodi, preserve the failed target copy privately, restore the untouched pre-import phone folder at its measured location, and relaunch. Verify actual recovery and signing continuity; host hash equality is not phone rollback evidence. Never restore over the Steam Deck profile, delete original media, revoke accounts to troubleshoot, or remove failed evidence.

Record actual device/build versions, source/add-on hashes, test IDs, failures/fixes/retests and sanitized metadata under the existing capture plan. Keep raw screenshots/accounts/media private. Phase 4 remains incomplete until required owner-device evidence passes. Phase 5, merge and release are not authorized.
