"""Copy failures whose next action is known. No blanket retry for a changed/invalid file or denied Drive access."""
import json
import re


class PermanentCopyError(RuntimeError):
    """The owner must change the source, free space or repair sign-in/access before another attempt can help."""
    terminal = True
    retryable = False

    def __init__(self, message, invalid_drive_id=''):
        super().__init__(message)
        # Identity is private state, never appended to the human-readable reason or log.
        self.invalid_drive_id = invalid_drive_id if isinstance(invalid_drive_id, str) else ''


class RetryableCopyError(RuntimeError):
    """A server/network/session failure; retain confirmed progress and wait before another attempt."""
    terminal = False
    retryable = True


RATE_LIMITS = {'ratelimitexceeded', 'userratelimitexceeded', 'sharingratelimitexceeded', 'downloadquotaexceeded'}
PERMANENT_WORDS = ('different file', 'different size', 'invalid completed upload receipt', 'invalid drive confirmed position',
                   'google drive checksum does not match',
                   'did not preserve resolution/hdr', 'google drive refused this request')
# ISSUE-298 (review of PR #30): the owner can fix these without changing the source (sign in again, grant the folder,
# free space). The copy keeps its place and waits (OWNER_WAIT seconds between tries), as the Sign in notice promises,
# instead of failing for good; before this a sign-out retired the whole queue.
OWNER_WORDS = ('sign in to google drive', 'saved drive sign-in', 'google drive is full', 'google drive refused access')
OWNER_WAIT = 600


def needs_owner(error):
    """True for a Drive sign-in, folder access or full-Drive failure: wait for the owner, never retire the copy."""
    if type(error).__name__ == 'SignedOut':
        return True
    code = getattr(error, 'code', None)
    if isinstance(code, int) and code in (401, 403) and not getattr(error, 'retryable', False):
        return True
    low = str(error or '').lower()
    if any(word in low for word in OWNER_WORDS):
        return True
    http = re.search(r'http\s+(\d{3})', low)
    return bool(http and 'drive' in low and int(http[1]) in (401, 403) and not any(r in low for r in RATE_LIMITS))


def _reasons(body):
    try:
        data = body if isinstance(body, dict) else json.loads(body or b'{}')
        error = data.get('error') or {}
        if not isinstance(error, dict):
            return set()
        return {str(e.get('reason') or '').lower() for e in error.get('errors') or [] if isinstance(e, dict)}
    except (ValueError, TypeError, AttributeError):
        return set()


def http_error(where, status, body=b''):
    """Typed error for an HTTP answer. Body reason codes are read; private body text/URLs are never copied out.

    An expired resumable session can be replaced, unlike a missing source/verification resource. A Drive 403 is
    sometimes a rate limit, not a denied permission: those answers remain retryable.
    """
    status = int(status)
    reasons = _reasons(body)
    transient = status in (408, 409, 425, 429) or status >= 500 or bool(reasons & RATE_LIMITS)
    session_expired = status in (404, 410) and where == 'Drive upload'
    transient = transient or session_expired or 200 <= status < 400
    if session_expired:
        reason = 'The Drive upload session expired; it will start a fresh session.'
    elif transient:
        reason = 'Google Drive is busy or did not confirm the request; it will try again.'
    elif 'storagequotaexceeded' in reasons:
        reason = 'Google Drive is full. Free up space in Drive, then try again.'
    elif status == 401:
        reason = 'Sign in to Google Drive again (Settings › Accounts).'
    elif status == 403:
        reason = 'Google Drive refused access. Check Drive sign-in and folder access, then try again.'
    elif status in (404, 410):
        reason = 'This file or folder is no longer available in Google Drive. Choose another source or folder.'
    else:
        reason = 'Google Drive refused this request. Check Drive access or choose another source.'
    cls = RetryableCopyError if transient else PermanentCopyError
    error = cls('%s: HTTP %d. %s' % (where, status, reason))
    error.code = status
    error.restart_session = session_expired
    return error


def is_retryable(error):
    """Known transient failures only; callers retain their existing network checks for other exceptions."""
    if getattr(error, 'terminal', False):
        return False
    if getattr(error, 'retryable', False):
        return True
    if type(error).__name__ == 'RefreshBusy':
        return True
    low = str(error or '').lower()
    return bool(any(reason in low for reason in RATE_LIMITS) or low.startswith(('retryablecopyerror:', 'refreshbusy:')))


def is_terminal(error):
    """Also recognise old persisted RuntimeError words, so a durable copy does not enter a fresh retry loop."""
    if is_retryable(error) or needs_owner(error):
        return False
    if getattr(error, 'terminal', False):
        return True
    low = str(error or '').lower()
    if low.startswith('permanentcopyerror:') or any(word in low for word in PERMANENT_WORDS):
        return True
    http = re.search(r'http\s+(\d{3})', low)
    # ISSUE-298: only Google Drive's own answers (http_error's 'Drive …' prefixes); a source/AllDebrid text never retires.
    if http and 'drive' in low:
        code = int(http[1])
        if code in (404, 410) and ('drive upload:' in low or 'upload session' in low):
            return False
        # An old raw 401 may predate access-token renewal in Drive.call. Give that new recovery one chance;
        # current, twice-refused 401s are typed PermanentCopyError (or explicitly ask for sign-in) above.
        return 400 <= code < 500 and code not in (401, 408, 409, 425, 429)
    return False
