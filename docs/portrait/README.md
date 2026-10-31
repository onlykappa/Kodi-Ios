# r11 portrait mode (owner design "layout A")

Status: implemented on host and checked in the Kodi 21.3 rig; native executable built by CI; awaiting iPhone test.

## How it works
1. **Native** (`migration/ios-portrait/kodi-21.3-portrait.patch`, Kodi 21.3-Omega `a3a448d`):
   - `supportedInterfaceOrientations` allows all but upside down; landscape only while video plays or on an external screen.
   - `viewWillTransitionToSize:` → resize the GL view and framebuffer, then on Kodi's thread reset `WinSystemIOS`'s cached
     touchscreen size, `UpdateResolutions()`, recompute safe-area insets, `SetVideoResolution(RES_DESKTOP, true)`.
   - Playback start/stop (`AnnounceReceiver`) asks iOS to re-check the mask, so video turns landscape.
   - Grouplists pass taps to rows that are only partly on screen (Kodi only did this for fully visible rows).
   - `Info.plist.in` lists portrait; `scripts/ios_portrait.py` also edits the shipped Info.plist.
   Why not a binary patch of the mask (24 -> 26): Kodi never resizes its framebuffer or its cached resolution, so the
   picture would be clipped and taps misplaced.
2. **Build**: `.github/workflows/kodi-ios-portrait.yml` (macOS) builds the patched executable from the pinned tag
   (`build-kodi-ios.sh`; depends cached). `build_customized_ipa.py --portrait-executable Kodi --portrait-executable-sha256 …`
   swaps only the main executable, after checking it links the same libraries as the official one. Without it the IPA keeps
   the official landscape-only executable (the portrait folder is then simply unused).
3. **Skin** (`migration/bundled-bootstrap/resources/lib/portrait.py`): adds `<res aspect="9:19.5" width="1080" height="2090"
   folder="portrait">` (and 9:16) to Fuse and generates the folder. 1080x2090 is the 16 Pro's portrait safe area
   (402x778 pt) with square pixels; Kodi stretches the canvas into the safe area.
   - Home / TV / Movies / Downloads: header with Search, hero card (hub spotlight list, swipe sideways), Play (movie → watch
     chooser, show → show page) and Info, then the hub's Fuse widget rows as poster rows, and the bottom tab bar
     Home · TV · Movies · Downloads · Drive · More.
   - Show page (`MyVideoNav`, seasons content): art, title, rating/year/seasons, plot, season chips, episode list of the
     selected chip. Episodes content and other folders get a plain list.
   - Info page, the select dialog as a centred card sized to its rows (this is "How would you like to watch?"), and More
     (Settings, Google Drive, Check for updates, iPhone navigation / recovery, Favourites, File manager).
   - Every other window: the landscape Fuse window shrunk into the middle (taps verified), so nothing is unreachable.
   - Fuse's landscape header overlay (1182) is empty in portrait.
4. **On the phone** (bootstrap service, after setup): regenerate the portrait windows when widget lists or 1080i files
   change, once turn off ".." parent rows (so a show opens on Season 1), then reload the skin whenever the phone settles
   in the other orientation.

## Testing
- `scripts/test_portrait.py` (layout generation, resolutions, fallback, select-dialog ids, rotation debounce, Info.plist).
- Rig: `scripts/portrait_rig.py` runs Kodi 21.3 (built from source, with the patch's GUI part) under Xvfb at 603x1167
  (the safe area at 1.5x) with the IPA's Fuse patches, real TMDb data, iOS conditions forced on. Screenshots were sent
  to the owner with the safe-area bars added back (603x1311). No touch gestures, rotation or safe areas in the rig.
