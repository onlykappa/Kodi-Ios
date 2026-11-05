# Settings Redesign Mockups

Open `settings-mockups.html` in a browser (or on iPhone) to see the owner-approved mockups. The code is in `migration/bundled-bootstrap/resources/lib/settings_page.py`, `accounts.py` and `accounts_page.py`.

The new Settings UI copies the native iOS 27 Settings app: inset grouped lists, black icon tiles with coloured glyphs, a glass back button, the floating search bar and iOS 26 toggles. It replaces Fuse's landscape Settings window letterboxed into the portrait screen.

Screens:
1. Settings Home (root)
1b. Accounts (provider sign-ins: Elementum, Umbrella, Google Drive, Trakt, TMDb Helper), built
2. System (category page with a hero card)
3. System › Display (detail page with an inline pick-one list)
4. Customisation (styled like Appearance)
5. Player (sections and a subtitle preview)
6. Add-ons hub (styled like Apple Account)
7. Add-on Updates (styled like Software Update)
8. Information (styled like About and Storage)

Built so far: Settings Home, Customisation and Accounts. The other screens are still Kodi's own windows (shrunk).
The design specs (colours, spacing, type) are at the bottom of `settings-mockups.html`.

## Round 2: remaining Fuse pages (`fuse-pages-mockups.html`)

Mockups only, for owner review: Play on TV over video (landscape AirPlay-style sheet), Umbrella's "getting ready to play" screen (its `source_progress.xml`, which the portrait skin folder can override), Add-ons and My Add-ons, File Manager, Event Log, System Information, Hubs & Widgets, Skin Settings, and the shared alert / progress / action-sheet dialogs. The page ends with the full list of the 89 windows that are still Fuse's shrunk landscape box, grouped as own page, shared template, or later.

Built from round 2 (`resources/lib/pages.py`): Play on TV, Umbrella getting ready, Add-ons, File Manager (two stacked panes: Kodi copies between them), Event Log, System Information and the alert/progress/text/settings dialogs. Not built yet: Skin Settings, Hubs & Widgets, My Add-ons filter pills, add-on info, and the action sheet for pick-one lists outside Choose a version.

## Round 3: activity indicator (`activity-indicator-mockups.html`)

Mockups only, for owner review. The loader is Kodi's background progress box (DialogExtendedProgressBar / DialogProgressBG), shared by Kodi (update checks, add-on installs, library scans, file operations, Live TV guide), Elementum (downloads, magnet resolving), Elementum Burst (searches), Umbrella (background scraping, resolving, Trakt sync, debrid cloud), TMDb Helper (library) and Skin Variables. Kodi rotates its jobs every 2 s; Fuse draws it as a small landscape strip. The mockups replace it with one activity pill (app tile, plain wording, real progress), an Activity sheet for several jobs, a Running now group in Notifications and per-source switches, placed the same way on every page.
