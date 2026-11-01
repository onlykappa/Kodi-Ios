# Read-only inspection

Inspection date: 2026-10-29. Source: SteamOS 3.9.5, Kodi 21.3 Omega, per-user Flatpak `tv.kodi.Kodi` from Flathub, x86_64/stable. Runtime: `org.freedesktop.Platform/x86_64/24.08`.

The deployed application is under `${HOME}/.local/share/flatpak/app/tv.kodi.Kodi/x86_64/stable/active/`. Kodi's own startup logs establish `${HOME}/.var/app/tv.kodi.Kodi/data/` as `special://home/`, and its `userdata/` subdirectory as `special://masterprofile/`. This deployment does not use a `.kodi` subdirectory inside `data/`.

Kodi was stopped for inspection and the complete backup. No source files were edited, add-ons executed, settings changed or application started.

## Inventory

| Item | Finding |
| --- | --- |
| User manifests | 79: 77 parse successfully, two are empty |
| Bundled manifests | 161; includes API interfaces and bundled copies overridden by some user add-ons |
| Add-on database | 230 registered entries: 201 enabled, 29 disabled |
| User repositories | Six; `repository.gsports` is disabled |
| Selected skin | Arctic Fuse 3, version 3.4.8 |
| Other skins | Arctic Zephyr Mod 3.0.3 and bundled Estuary |
| Skin preferences | 320 Fuse settings and 325 Zephyr settings in the source |
| Custom keymaps | Two Steam Deck navigation/D-pad XML files |
| Smart playlists | 14, including mounted-media path rules |
| Sources and favourites | Six sources, one favourite; favourite content is not exported |
| Google Drive | No installed add-on identified by Drive/Google identifiers |

Relevant components include TMDb Helper 6.18.1, YouTube 7.4.4a, Trakt 3.9.0, Elementum 0.1.114, The Loop 8.3, Skin Variables 2.2.10, Skin Shortcuts 2.0.3 and custom `service.deck.keeper` 1.0.0. See the JSON inventory for every installed manifest and declared dependency.

## Existing issues

- Umbrella and JetExtractors each have a zero-byte `addon.xml`.
- The Loop declares JetExtractors as a required dependency. This is unresolved in the source baseline.
- Menu and TMDb Helper player definitions still refer to Umbrella. The owner excludes it from the future iOS build; source cleanup is deferred.
- Custom configuration contains mounted-storage paths and desktop-specific actions. Private paths are replaced or normalized in the snapshot.
- Elementum ships native binaries for several desktop platforms; the custom Deck Keeper invokes subprocesses. Static discovery does not establish iOS compatibility.

## Backup

The complete Flatpak per-user state contains 22,463 files totaling 2,669,419,647 bytes before compression. The verified archive is 2,127,468,973 bytes. Every archived regular file was checked against SHA-256 hashes; a second inventory verified that the source did not change during backup.

The archive includes all Flatpak app-state directories, caches, databases, installed user add-ons, previous backup fragments and settings. It records the Flatpak installation/version separately. It does not copy the installed application/runtime or external media and is not a SteamOS disk image. Archive ACLs and extended attributes were requested; verification covers content, directory/symlink coverage and symlink targets, not a cross-filesystem restore test.

No standalone per-user Flatpak override file was found. Existing older backup folders were not relied on or altered.
