"""Add-on search with the phone's native search field (owner, 2026-11-27: "it should look like the search for TV shows").

Kodi's add-on search asks for the name with a keyboard dialog before it lists anything (CAddonsDirectory::GetSearchResults),
which on the phone was a grey "Enter search string" over a blank page. Kodi lists a search from its address alone, though:
addons://search/<name> needs no keyboard. So the add-ons page stays where it is, the native iOS search field (the one Settings
search uses, searchbar.py's "settings" context: Window(Home) properties Settings.Search.Active / Query / Close) sits above it,
and each time typing pauses the page is pointed at addons://search/<what is typed>. This module holds the address and the
follow-the-field logic; bootstrap/addon_search.py runs it."""
import urllib.parse

BASE = 'addons://search/'
BLANK = BASE + '%E2%80%8B'   # a zero-width space: a search that lists nothing, so no keyboard dialog opens


def normal(text):
    return ' '.join(str(text or '').split())


def path(query):
    query = normal(query)
    return BASE + urllib.parse.quote(query) if query else BLANK


class Follower:
    """tick() until it returns False: points the add-ons page at what is typed and ends when the page leaves the search or
    the field is closed (X). Everything it touches is passed in, so it is tested without Kodi."""

    def __init__(self, query, folder, closed, go, back, clock, grace=5.0):
        self.query, self.folder, self.closed, self.go, self.back, self.clock = query, folder, closed, go, back, clock
        self.grace, self.began, self.seen, self.last = grace, clock(), False, ''

    def tick(self):
        if self.closed():
            self.back()
            return False
        if str(self.folder() or '').startswith(BASE):
            self.seen = True
        elif self.seen or self.clock() - self.began > self.grace:
            return False
        typed = normal(self.query())
        if typed != self.last:
            self.last = typed
            self.go(path(typed))
        return True
