# Owner review and roadmap

The owner requested a backup and review baseline before deciding how to dial in the migration. These are open decisions and acceptance criteria, not an implementation commitment.

## Completed baseline

- [x] Locate real Flatpak data paths and inspect without editing the source.
- [x] Create a complete local app-state backup and verify every archived file.
- [x] Inventory installed manifests, enabled states and declared dependencies.
- [x] Export a limited sanitized configuration snapshot and file hashes.
- [x] Preserve existing configuration separately from the future iOS package.
- [x] Record the owner's decision to exclude Umbrella on iOS.
- [x] Prepare automated secret, file-integrity and reference checks.
- [x] Preserve raw keys and login state in a separate verified private account-transfer bundle.

## Decisions for the owner

- Which iPhone and iOS version will be used, and what Kodi build/install method is available?
- Retain Arctic Fuse 3, use Zephyr, or start with a simpler touch layout?
- Which menu categories and widgets should stay?
- Which playback integrations are essential besides personal Google Drive videos?
- Should library metadata/watch state be rebuilt or migrated separately and privately?
- Which existing desktop-only automation should be replaced or omitted?

## Proposed follow-up sequence

1. Establish a supported Kodi installation on the target iPhone and record exact versions.
2. Choose the essential add-on set; investigate native/DRM/platform dependencies with current upstream evidence.
3. Remove Umbrella from a separate target configuration; resolve or omit JetExtractors/The Loop.
4. Rebuild navigation for touch and replace source/path placeholders.
5. Research and choose Google Drive playback; reuse compatible saved account state privately and authenticate on the device only when necessary.
6. Build an iOS package from reviewed target files, with an explicit add-on/version manifest and no credentials.
7. Test launch, navigation, playback, seeking, resume and recovery on the real phone.
8. Update the PR with evidence and ask the owner to review before merging.

Do not install `snapshot/` directly or merge the PR as a completed migration. No installation package has been produced in this baseline change.
