"""What the person sees when signing in to AllDebrid in the app (step 17 screens). Plain Python: the choice sheet, the closer and the notices are injected,
so every rule is tested without Kodi. The sheet is the app's own choice sheet (no new layout); wording follows the UI policy: plain, short, nothing cut off,
one recovery step.
"""
import threading

import alldebrid
import debrid_account
import debrid_token
import source_contract

HEADING = 'Sign in to AllDebrid'
OUTCOME_TEXT = {
    source_contract.EXPIRED: ('The code expired', 'Open Accounts and try again.'),
    source_contract.OFFLINE: ('AllDebrid could not be reached', 'Check your connection and try again.'),
    source_contract.TIMEOUT: ('AllDebrid did not answer', 'Try again in a moment.'),
    source_contract.REFUSED: ('AllDebrid refused the sign-in', 'Open the e-mail AllDebrid sent you, then try again.'),
    source_contract.UNSUPPORTED: ('Sign-in did not finish', 'Try again, or use Umbrella to sign in.'),
}


def pin_spec(pin, url=''):
    """The sheet for a pending sign-in: the code is the first row; Cancel is the button."""
    page = 'alldebrid.com/pin'
    return {'heading': HEADING, 'sub': 'Waiting for you to enter the code',
            'rows': [{'label': ' '.join(str(pin)), 'detail': 'Enter it at %s on any device. It works for 10 minutes.' % page}],
            'button': 'Cancel'}


def signed_in_spec():
    return {'heading': 'AllDebrid', 'sub': 'Signed in on this phone',
            'rows': [{'label': 'Sign out', 'detail': 'Removes the key from this phone. If Umbrella has a key, that one is used.'}],
            'button': 'Done'}


def run(choose, close, notify, request=alldebrid.default_request, manage=False, profile=None, health=None, sleep=None, clock=None):
    """Sign in (or, when already signed in with `manage`, sign out). Returns 'signed-in', 'signed-out', 'canceled' or the outcome name of a failure."""
    if debrid_token.own(profile) or manage:
        if choose(signed_in_spec()) == 0:
            debrid_account.sign_out(profile)
            notify('info', 'AllDebrid signed out', 'This phone no longer holds a key.')
            return 'signed-out'
        return 'canceled'
    stop, shown, result = threading.Event(), threading.Event(), {}
    spec = {}

    def show(pin, url):
        spec.update(pin_spec(pin, url))
        shown.set()

    def work():
        kwargs = {}
        if sleep:
            kwargs['sleep'] = sleep
        if clock:
            kwargs['clock'] = clock
        try:
            result['ok'] = debrid_account.sign_in(show, request, cancel=stop.is_set, profile=profile, health=health, **kwargs)
        except source_contract.Outcome as outcome:
            result['kind'] = outcome.kind
        finally:
            shown.set()
            close()                                    # the key arrived, or it failed: the sheet goes away by itself
    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    shown.wait(30)
    if spec:
        choose(spec)                                   # blocks until Cancel or until the worker closes it
    stop.set()
    worker.join(10)
    if result.get('ok'):
        notify('info', 'AllDebrid is signed in', 'Downloads and streams can use it now.')
        return 'signed-in'
    kind = result.get('kind')
    if kind in (None, source_contract.CANCELED):
        return 'canceled'
    title, text = OUTCOME_TEXT.get(kind, OUTCOME_TEXT[source_contract.UNSUPPORTED])
    notify('problem', title, text)
    return kind
