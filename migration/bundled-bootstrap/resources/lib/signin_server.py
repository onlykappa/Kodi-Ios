"""The owner's own Google Drive sign-in server (Cloudflare Worker deployed by .github/workflows/signin-server.yml).
Refresh tokens go only there; the public relay of the Drive add-on's author is never used (owner review, PR 8)."""
SERVER='https://kodi-signin.ballaking1738.workers.dev'
PUBLIC='https://drive.signinserver.com'

def server(setting):
 """The configured server, or the owner's own when the setting is empty or still the public relay."""
 value=(setting or '').strip().rstrip('/')
 return SERVER if not value or value==PUBLIC else value

def migrate(addon):
 """Existing installs: move plugin.googledrive's setting off the public relay. Returns True when changed."""
 if (addon.getSetting('sign-in-server') or '').strip().rstrip('/') in ('',PUBLIC):
  addon.setSetting('sign-in-server',SERVER);return True
 return False
