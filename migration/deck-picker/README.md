# Deck "Choose a version" page for Elementum

Copied from the owner's Steam Deck (Deck Keeper snapshot, Elementum 0.1.114). One change on the phone: the quality
list shows only the quality and how many versions it has (no "top pick" size or seeds).


- `deck_picker.py` → `plugin.video.elementum/resources/site-packages/elementum/deck_picker.py`
- `DeckSourceSelect.xml` → `plugin.video.elementum/resources/skins/Default/720p/DeckSourceSelect.xml`
- `media.json` → `plugin.video.elementum/resources/skins/Default/media/deck/*.png` (base64; the repository holds text only)

On the Deck, Elementum's `rpc.py` `Dialog_Select_Large` hands the link list to `deck_picker.run()`: first a quality
choice (only qualities that exist, or "Show all"), then the five best different links in that quality on a page with
the title's poster, background, year/runtime and plot. `scripts/build_customized_ipa.py` installs these files into the
bundled Elementum and applies the same `rpc.py` edit. iPhone change: the two full-screen background layers reach the
right edge (`<right>0</right>`), since the phone's canvas is wider than 1280 at 720 high. The poster and details come
from the watch menu (`ios_watch_dialog.py`), which leaves them on the Home window as the Deck's Sources chooser did.

Kodi-iOS source check: every link is checked against the title being played by
`migration/bundled-bootstrap/resources/lib/source_match.py` (installed beside `deck_picker.py` as
`site-packages/elementum/source_match.py`). Links of another title or year are never offered as versions: short lists
get this page too, "Show all" lists only verified links when some were hidden, and a "N hidden (wrong title/year)" row
reveals the others with the reason. Burst runs the same check on every provider's results (`BURST_PATCHES` in
`scripts/build_customized_ipa.py`), so Elementum's auto-pick and downloads are verified too, and hands the identity it
checked to this page through the Home window (`KodiIOS.SourceMatch`).
