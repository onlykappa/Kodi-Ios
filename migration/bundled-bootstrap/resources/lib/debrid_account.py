"""The app's own AllDebrid account handling (roadmap step 17): PIN sign-in, typed errors, and a "debrid is unavailable" circuit.

Sign-in uses AllDebrid's documented PIN flow (docs.alldebrid.com, read 2026-11-26): `/v4.1/pin/get` returns a short code and a page for the
person to open; `/v4/pin/check` (POST pin + check) returns the api key once they submit it. The key goes only to the app's profile
(`debrid_token.save_own`), never to Git, the IPA or a log. Every AllDebrid error code maps to one source_contract outcome so callers can tell
"debrid is gone" (offline/refused across several calls) from "this title is not cached" (not an error: `ready` is false, outcome empty).
Plain Python over an injectable `request(method, url, data, headers)`; no Kodi imports.
"""
import json
import time
import urllib.parse

import alldebrid
import debrid_token
import source_contract

SOURCE = 'debrid'
UNAVAILABLE_AFTER = 3          # consecutive offline/timeout/refused answers before debrid counts as unavailable
POLL_EVERY = 5
MAX_WAIT = 600

# AllDebrid error code -> outcome. Account problems need the person; refused/blocked are not retried soon; expired means ask again.
CODES = {
    'AUTH_MISSING_APIKEY': source_contract.ACCOUNT_REQUIRED, 'AUTH_BAD_APIKEY': source_contract.ACCOUNT_REQUIRED,
    'MUST_BE_PREMIUM': source_contract.ACCOUNT_REQUIRED, 'MAGNET_MUST_BE_PREMIUM': source_contract.ACCOUNT_REQUIRED,
    'FREE_TRIAL_LIMIT_REACHED': source_contract.ACCOUNT_REQUIRED, 'ACCOUNT_INVALID': source_contract.ACCOUNT_REQUIRED,
    'AUTH_BLOCKED': source_contract.REFUSED, 'AUTH_USER_BANNED': source_contract.REFUSED, 'NO_SERVER': source_contract.REFUSED,
    'MAGNET_TOO_MANY_ACTIVE': source_contract.REFUSED, 'MAGNET_TOO_MANY': source_contract.REFUSED, 'LINK_TOO_MANY_DOWNLOADS': source_contract.REFUSED,
    'LINK_HOST_LIMIT_REACHED': source_contract.REFUSED,
    'MAINTENANCE': source_contract.OFFLINE, 'MAGNET_NO_SERVER': source_contract.OFFLINE, 'MAGNET_INTERNAL_ERROR': source_contract.OFFLINE,
    'LINK_HOST_UNAVAILABLE': source_contract.OFFLINE, 'LINK_HOST_FULL': source_contract.OFFLINE, 'LINK_TEMPORARY_UNAVAILABLE': source_contract.OFFLINE,
    'MAGNET_INVALID_ID': source_contract.EXPIRED, 'MAGNET_LINKS_REMOVED': source_contract.EXPIRED, 'PIN_EXPIRED': source_contract.EXPIRED,
    'LINK_DOWN': source_contract.EXPIRED, 'DELAYED_INVALID_ID': source_contract.EXPIRED,
    'MAGNET_INVALID_URI': source_contract.UNSUPPORTED, 'MAGNET_INVALID_FILE': source_contract.UNSUPPORTED, 'MAGNET_PROCESSING_FAILED': source_contract.UNSUPPORTED,
    'MAGNET_TOO_LARGE': source_contract.UNSUPPORTED, 'MAGNET_MAGNET_TOO_BIG': source_contract.UNSUPPORTED, 'MAGNET_TOOK_TOO_LONG': source_contract.UNSUPPORTED,
    'MAGNET_CANT_BOOTSTRAP': source_contract.EMPTY, 'LINK_HOST_NOT_SUPPORTED': source_contract.UNSUPPORTED, 'BAD_LINK': source_contract.UNSUPPORTED,
    'PIN_INVALID': source_contract.UNSUPPORTED,
}
# Failures that say "the service is not usable", as opposed to "this one request/title/account failed".
SERVICE_DOWN = (source_contract.OFFLINE, source_contract.TIMEOUT, source_contract.REFUSED)


def outcome_for(error):
    """One typed outcome for anything the AllDebrid client can raise. Reads codes and kinds, never the message."""
    if isinstance(error, alldebrid.Problem):
        return CODES.get(getattr(error, 'code', None), source_contract.UNSUPPORTED)
    if isinstance(error, alldebrid.Busy):
        return {'timeout': source_contract.TIMEOUT, 'refused': source_contract.REFUSED}.get(getattr(error, 'kind', ''), source_contract.OFFLINE)
    return source_contract.classify(error)


def record(health, error=None):
    """Feed one call's result into the shared source health under the name `debrid`. None = success. `empty` (not cached) costs nothing."""
    if health is not None:
        health.record(SOURCE, source_contract.OK if error is None else outcome_for(error))


def unavailable(health, now=None):
    """True only after several consecutive service-level failures that are still cooling down: one bad answer never flips it, a success clears it."""
    entry = (health.data.get(SOURCE) or {}) if health is not None else {}
    return bool(entry and entry.get('fails', 0) >= UNAVAILABLE_AFTER and entry.get('kind') in SERVICE_DOWN and health.state(SOURCE, now) == 'cooldown')


def _json(raw):
    try:
        answer = json.loads(raw)
    except (TypeError, ValueError):
        raise alldebrid.Busy('AllDebrid gave an answer this app cannot read.')
    if not isinstance(answer, dict):
        raise alldebrid.Busy('AllDebrid gave an answer this app cannot read.')
    return answer


def _call(request, method, path, data=None):
    url = alldebrid.API + path + ('?' + urllib.parse.urlencode({'agent': alldebrid.AGENT}) if method == 'GET' else '')
    body = dict(data or {}, agent=alldebrid.AGENT) if method == 'POST' else None
    try:
        answer = _json(request(method, url, body, {}))
    except alldebrid.Busy:
        raise
    except Exception as error:
        busy = alldebrid.Busy('AllDebrid could not be reached (%s).' % type(error).__name__)
        busy.kind = 'timeout' if isinstance(error, TimeoutError) else ('refused' if getattr(error, 'code', None) in (403, 429, 451) else 'offline')
        raise busy
    if answer.get('status') != 'success':
        code = (answer.get('error') or {}).get('code')
        raise alldebrid.Problem('AllDebrid: %s' % ((answer.get('error') or {}).get('message') or 'problem'), code)
    return answer.get('data') or {}


def pin_start(request=alldebrid.default_request):
    """-> {'pin': 'ABCD', 'check': token, 'url': page to open, 'expires': seconds}. Nothing secret yet."""
    data = _call(request, 'GET', '/v4.1/pin/get')
    if not data.get('pin') or not data.get('check'):
        raise alldebrid.Busy('AllDebrid gave an answer this app cannot read.')
    return {'pin': str(data['pin']), 'check': str(data['check']), 'url': str(data.get('user_url') or ''), 'expires': int(data.get('expires_in') or MAX_WAIT)}


def pin_check(started, request=alldebrid.default_request):
    """The api key once the person has submitted the pin, else ''."""
    data = _call(request, 'POST', '/v4/pin/check', {'pin': started['pin'], 'check': started['check']})
    return str(data.get('apikey') or '') if data.get('activated') else ''


def sign_in(show, request=alldebrid.default_request, cancel=None, sleep=time.sleep, clock=time.monotonic, profile=None, health=None):
    """Whole flow. `show(pin, url)` displays the code. Returns True once the key is stored; raises source_contract.Outcome (canceled, expired, ...)."""
    try:
        started = pin_start(request)
        show(started['pin'], started['url'])
        deadline = clock() + min(started['expires'], MAX_WAIT)
        while True:
            if cancel and cancel():
                raise source_contract.Outcome(source_contract.CANCELED)
            if clock() >= deadline:
                raise source_contract.Outcome(source_contract.EXPIRED)
            key = pin_check(started, request)
            if key:
                if not debrid_token.save_own(key, profile):
                    raise source_contract.Outcome(source_contract.OFFLINE)
                record(health)
                return True
            sleep(POLL_EVERY)
    except (alldebrid.Problem, alldebrid.Busy) as error:
        record(health, error)
        raise source_contract.Outcome(outcome_for(error))


def sign_out(profile=None):
    """Forget the app's own key (Umbrella's setting is untouched; if it still holds one, that one is used again)."""
    return debrid_token.clear(profile)


_shared = []


def shared_health():
    """The app's one source-health store (created on first use), so every AllDebrid caller feeds the same record."""
    if not _shared:
        import source_health
        _shared.append(source_health.default())
    return _shared[0]


def observer():
    """For alldebrid.AllDebrid(observe=...): records each call's outcome under `debrid`."""
    return lambda error: record(shared_health(), error)


def is_unavailable():
    return unavailable(shared_health())
