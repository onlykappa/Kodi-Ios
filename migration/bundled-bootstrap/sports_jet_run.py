"""Runs JetExtractors' work on the main thread of a script Kodi started (ISSUE-365): `RunScript(service.kodi.ios.bootstrap,sports_jet_run)` collects games,
`... sports_jet_run play` plays the source the Sports page left in a Home window property. JetExtractors calls xbmcaddon.Addon() with no id, which Kodi
allows only here, not on a page's worker threads."""
import sys

import sports_jet

if __name__ == '__main__':
    sports_jet.run_script(sys.argv[1:])
