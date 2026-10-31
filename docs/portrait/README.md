# r11 portrait mode — feasibility and design (draft, awaiting owner approval)

Status: RESEARCH + MOCKUPS ONLY. Nothing is wired into the IPA yet.

## 1. Native rotation (Kodi 21.3-Omega source, checked)

Kodi iOS is locked to landscape in three places, and it has no code path for the screen changing shape:

- `Info.plist` `UISupportedInterfaceOrientations` lists only LandscapeLeft/Right. This can be edited when repackaging.
- `xbmc/platform/darwin/ios/XBMCController.mm` `supportedInterfaceOrientations` returns `UIInterfaceOrientationMaskLandscape` (24). This is compiled code. `XBMCApplication` forwards the window's mask to it.
- `xbmc/windowing/ios/WinSystemIOS.mm` `GetScreenResolution` caches the internal screen size in `m_internalTouchscreenResolutionWidth/Height` the first time it is read, and never resets it.
- There is no `viewWillTransitionToSize:` handler. The GL view (`IOSEAGLView`) has no autoresizing, and its framebuffer is only resized by `setScreen:withFrameBufferResize:` (external-screen switches). `guiInsets` (safe areas) are read once in `onXbmcAlive`.

**A binary patch of the mask (24 -> 26) alone is not viable.** UIKit would rotate the root view, but Kodi would keep a
landscape framebuffer and a cached landscape resolution. The picture would be clipped or misplaced, touch
coordinates would no longer match, and the safe-area insets would stay landscape. The cached size is a C++ member, so
neither an Info.plist edit nor an injected Objective-C dylib can reset it cleanly.

**Recommended: rebuild only the Kodi 21.3 main executable on a macOS runner with a small source patch (~60 lines):**
1. `supportedInterfaceOrientations` -> `UIInterfaceOrientationMaskAllButUpsideDown`. Add Portrait to Info.plist.
2. `viewWillTransitionToSize:withTransitionCoordinator:`. When the rotation completes: set the GL view frame to the new bounds, resize the framebuffer,
   clear the cached touchscreen size, call `UpdateResolutions()`, re-apply `RES_DESKTOP` on Kodi's thread
   (`SetVideoResolution` -> `GUI_MSG_WINDOW_RESIZE`), and call `setGUIInsetsFromMainThread:YES`.
3. Lock rotation during fullscreen video (keep landscape), and while a modal keyboard is up.

The rest of the official, hash-pinned app bundle (add-ons, frameworks) stays as it is. We would swap in only the executable, built from the same
tag. Cost: Kodi `tools/depends` + Xcode build on `macos-14/15`, roughly 1.5–3 h per cold CI run (cacheable). This needs owner approval.

## 2. Skin side (Kodi source, checked)

- `CSkinInfo` reads every `<res>` in the skin's addon.xml. `GetSkinPath()` picks the folder whose aspect ratio is
  closest to the current resolution, each time a window XML loads.
- Includes, fonts and timers are loaded once per skin load, though. After rotation a `ReloadSkin()` is required. It restores the
  active window. The bootstrap service will watch `System.ScreenWidth/Height` and call it after a short debounce.
- Plan: add `<res width="1080" height="1920" aspect="9:16" default="false" folder="portrait"/>` to Fuse at IPA build
  time. A new `portrait/` folder holds Home, the hub windows, the show/info page and the chooser, plus a portrait `Includes.xml`
  that `<include file="../1080i/...">`s the Fuse includes it reuses (widgets, fonts, colours, expressions).
  On the iPhone 16 Pro (1206x2622 px) the portrait canvas is 1080 wide x ~2347 tall. Bottom-anchored controls use
  `<bottom>`, never a fixed `<top>`; safe areas still come from Kodi's `guiInsets`.
- Landscape keeps using `1080i` unchanged.

## 3. Layout A mockups (603x1311, iPhone 16 Pro portrait)

`home.png` and `show.png` (HTML sources beside them, colours are placeholders for artwork):
- Home: small header with only Search; a hero card with art, title, rating/year/genre, white Play and grey Info; Fuse widget
  rows as horizontal poster strips; bottom tab bar Home/TV/Movies/Downloads/Drive/More (More = gear menu).
- Show page: hero art, title/meta/plot, season chips, episode list. A movie or episode opens the existing
  `plugin.video.kodi.ios.watch` chooser as a bottom sheet.

## Touch behaviour in portrait

Rows return PAN_HORIZONTAL, so a sideways drag scrolls a row. For vertical page scrolling, the ISSUE-043/048 swipe-to-Up/Down
mapping already applies to Home and the hubs. In portrait the page will be a vertical list/grouplist with real drag
scrolling where Kodi allows it.
