"""CA roots for every Python add-on on the phone (owner, build 623: "we cant have failed sources"; log 8c570737).

Crew's embedsports streamer failed twice with `SSLError ... (_ssl.c:1006)` ("[SSL] unknown error"), the same text the app met before for Drive sign-in
(ISSUES: "Drive sign-in failed with `[SSL] unknown error (_ssl.c:1006)` while TMDb Helper (certifi CA bundle) works"): on this phone Python's default
SSL context has no CA roots, so any add-on that builds its own context (instead of letting requests use certifi) cannot verify any site. Kodi's Python
runs every add-on in one process, so pointing OpenSSL's SSL_CERT_FILE at certifi's bundle once, before the add-ons build contexts, gives all of them
roots. Add-ons that already use certifi are unaffected. If SSL_CERT_FILE already names a file it is left alone."""
import os


def apply(environ=None, where=None, isfile=os.path.isfile):
    """Set SSL_CERT_FILE to certifi's bundle unless it already names a file. Returns the path set, or '' (nothing to do or certifi missing). Never raises."""
    environ = os.environ if environ is None else environ
    try:
        current = environ.get('SSL_CERT_FILE', '')
        if current and isfile(current):
            return ''
        if where is None:
            import certifi
            where = certifi.where
        path = where()
        if not path or not isfile(path):
            return ''
        environ['SSL_CERT_FILE'] = path
        return path
    except Exception:
        return ''
