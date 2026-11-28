"""Add-on install progress for the add-on page (owner-approved docs/design/addon-install-mockups.html, frames 4 and 5).

Kodi reports an add-on install through its background progress box (window 10151, DialogExtendedProgressBar): label 30 reads
"Installing <name>...", label 31 the step ("Downloading add-on...") and progress 32 the percentage. The portrait skin never
draws that box (ISSUE-287), so this copies what it says into Window(Home) properties the add-on page reads:

    Addon.Install.Name     the add-on being installed ('' when nothing is)
    Addon.Install.Stage    0 downloading, 1 checking the download, 2 adding what it needs, 3 installing
    Addon.Install.Percent  0-100

Pure apart from read(), so it is host-tested."""
import re

WINDOW = 10151
HEADER, TEXT, PROGRESS = 30, 31, 32
NAME, STAGE, PERCENT = 'Addon.Install.Name', 'Addon.Install.Stage', 'Addon.Install.Percent'
TAGS = re.compile(r'\[/?[A-Za-z]+[^\]]*\]')
# Kodi's own step lines (English strings 24058, 24078, 24077, 24079 and 24086), most specific first.
STEPS = (('installing add-on dependencies', 2), ('verifying', 1), ('installing add-on', 3), ('downloading', 0), ('checking', 0))


def clean(text):
    return re.sub(r'\s+', ' ', TAGS.sub('', str(text or '')).replace('[CR]', ' ')).strip()


def parse(heading, text):
    """(name, stage) for an add-on install box, else None (another background job)."""
    head = clean(heading)
    found = re.match(r'^Installing (.+?)\.{0,3}$', head)
    if not found:
        return None
    step = clean(text).lower()
    stage = next((n for key, n in STEPS if key in step), 0)
    return found.group(1).rstrip('.').strip(), stage


def read(xbmc, xbmcgui):
    """(heading, text, percent) while Kodi's box is up, else None."""
    if not xbmc.getCondVisibility('Window.IsVisible(%d)' % WINDOW):
        return None
    try:
        window = xbmcgui.Window(WINDOW)
        heading, text = window.getControl(HEADER).getLabel(), window.getControl(TEXT).getLabel()
        try:
            percent = int(window.getControl(PROGRESS).getPercent())
        except Exception:
            percent = 0
    except Exception:
        heading, text, percent = xbmc.getInfoLabel('Control.GetLabel(%d)' % HEADER), xbmc.getInfoLabel('Control.GetLabel(%d)' % TEXT), 0
    return (heading, text, percent) if heading or text else None


def publish(box, set_property, clear_property):
    """Copy one reading into the properties; returns True while an install shows."""
    parsed = parse(box[0], box[1]) if box else None
    if not parsed:
        for key in (NAME, STAGE, PERCENT):
            clear_property(key)
        return False
    set_property(NAME, parsed[0])
    set_property(STAGE, str(parsed[1]))
    set_property(PERCENT, str(max(0, min(100, int(box[2] or 0)))))
    return True


def watch(read_box, set_property, clear_property, wait, busy=0.7, idle=3.0):
    """Poll the box: quickly while an install shows, slowly otherwise. wait(s) -> True to stop."""
    shown = False
    while not wait(busy if shown else idle):
        try:
            shown = publish(read_box(), set_property, clear_property)
        except Exception:
            shown = False
    for key in (NAME, STAGE, PERCENT):
        try:
            clear_property(key)
        except Exception:
            pass
