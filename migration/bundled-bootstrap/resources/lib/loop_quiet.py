"""Keep The Loop's background work off (owner, 2026-11-20: "ensure it stops doing all that work", the Loop integration comes later).

Build 615's log: the Loop add-on logged "Analytics poll: playback detected but no session synced yet" 56 times in 7 minutes, and its JetExtractors
scrapers failed to import (`cannot import name 'config'`) and retried in the background. Nothing in the app uses the Loop (Sports sources come from The Crew),
so while the setting "Pause The Loop's background work" is on (default) the add-on is disabled; switching the setting off enables it again, but only if
this app disabled it (an add-on the owner disabled themselves is left alone).
"""
import json

LOOP = 'plugin.video.the-loop'


def apply(wanted, rpc, state_file, log=lambda text: None):
    """Make the Loop add-on match the setting. rpc(method, params) -> result dict; state_file is a path in the profile. Returns 'disabled', 'enabled' or ''."""
    try:
        details = (rpc('Addons.GetAddonDetails', {'addonid': LOOP, 'properties': ['enabled']}) or {}).get('addon') or {}
    except Exception:
        return ''
    if not details:   # not installed
        return ''
    enabled = bool(details.get('enabled'))
    ours = _load(state_file).get('disabled')
    if wanted and enabled:
        rpc('Addons.SetAddonEnabled', {'addonid': LOOP, 'enabled': False})
        _save(state_file, {'disabled': True})
        log('loop: paused (its analytics poll and scraper retries were running in the background)')
        return 'disabled'
    if not wanted and ours and not enabled:
        rpc('Addons.SetAddonEnabled', {'addonid': LOOP, 'enabled': True})
        _save(state_file, {})
        log('loop: switched back on')
        return 'enabled'
    return ''


def _load(path):
    try:
        with open(path) as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(path, data):
    try:
        with open(path, 'w') as handle:
            json.dump(data, handle)
    except OSError:
        pass
