# Add-on and skin compatibility review

This is a source inspection report, not an assertion of iOS support. No add-on has been tested on an iPhone. Each manifest's provisional category and dependency list are in `inventory/addons.json`.

| Component | Evidence from this installation | Next review |
| --- | --- | --- |
| Arctic Fuse 3 3.4.8 | Selected skin; depends on Skin Variables, Texture Maker, TMDb Helper and resource packs | Verify versions, touch navigation and performance on the intended iPhone |
| Arctic Zephyr Mod 3.0.3 | Alternate skin; depends on Skin Shortcuts and Embuary helpers | Decide whether to retain as an alternative; test touch input |
| TMDb Helper 6.18.1 | Custom Elementum and Umbrella player definitions | Remove Umbrella from the future build; choose supported playback routes |
| Elementum 0.1.114 and Burst | Native executable payloads and process-launch code | Review iOS support and platform execution requirements before including |
| Deck Keeper 1.0.0 | Custom Python service invokes subprocesses | Review or replace desktop-specific behavior |
| Custom delete context menu | Contains a Deck-specific filesystem path | Review destination and filesystem behavior before enabling |
| YouTube 7.4.4a / Fusion 0.1.4 | Python add-ons; YouTube declares InputStream Adaptive | Verify iOS build, authentication and playback routes |
| Trakt 3.9.0 | Python service with account settings preserved in the private bundle | Try compatible saved account state first; keep tokens outside GitHub |
| The Loop 8.3 and related modules | Required JetExtractors manifest is empty | Resolve source dependency before judging iOS compatibility |
| Umbrella | Empty manifest and existing menu/player references | Excluded from iOS by owner; baseline cleanup deferred |
| InputStream, PVR, VFS, decoders, visualizations | Bundled with the Linux Flatpak | Inventory against actual iOS distributions; do not copy Linux libraries |
| Python modules / resource packs | Dependency declarations found locally | Resolve matching versions and test; `platform=all` is insufficient evidence |
| Keymaps / playlists / sources | Desktop input mappings and private mounted-media paths | Select touch controls and replace path placeholders |

The inventory records API interface manifests as well as user-facing add-ons. Their presence in the Flatpak is not a requirement to install all of them on iOS. Repositories should be reviewed for necessary components and platform availability rather than copied indiscriminately.
