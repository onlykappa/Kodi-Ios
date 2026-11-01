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
