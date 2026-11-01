"""Accounts page (Settings › profile card): which provider add-ons are signed in, and what tapping each one does.

Setting ids come from each add-on's own settings.xml (checked 2026-11-01 against Elementum master, Umbrella 6.7.99,
script.trakt 3.9.0 and TMDb Helper 6.18.1). A login counts when its token (or user name) setting is not empty.
Google Drive keeps its sign-ins in its own account store (clouddrive.common), so accounts_page.py passes those in.
Sign-ins never leave the phone: this only reads whether they exist.
"""

DRIVE='ActivateWindow(Videos,plugin://plugin.googledrive/,return)'
SECTIONS=('Streaming & Sources','Cloud & Tracking')

# logins: (label, user-name setting, token setting); either may be '' when the add-on has no such setting.
SERVICES=[
 {'key':'elementum','name':'Elementum','addon':'plugin.video.elementum','section':0,'icon':'magnet.png','tint':'FF1F6FEB',
  'logins':[('Trakt','trakt_username','trakt_token')],'none':'Trakt not linked',
  'sign_in':'RunPlugin(plugin://plugin.video.elementum/tracker/authorize?tracker=trakt)',
  'manage':'Addon.OpenSettings(plugin.video.elementum)'},
 {'key':'umbrella','name':'Umbrella','addon':'plugin.video.umbrella','section':0,'icon':'umbrella.png','tint':'FF7D3CFF',
  'logins':[('Trakt','trakt.user.name','trakt.user.token'),('AllDebrid','alldebridusername','alldebridtoken'),
            ('Real-Debrid','realdebridusername','realdebridtoken'),('Premiumize','premiumizeusername','premiumizetoken'),
            ('TorBox','','torboxtoken')],
  'sign_in':'Addon.OpenSettings(plugin.video.umbrella)','manage':'Addon.OpenSettings(plugin.video.umbrella)'},
 {'key':'drive','name':'Google Drive','addon':'plugin.googledrive','section':1,'icon':'cloud.png','tint':'FF1A9E5C',
  'drive':True,'sign_in':DRIVE,'manage':DRIVE},
 {'key':'trakt','name':'Trakt','addon':'script.trakt','section':1,'icon':'circle-check.png','tint':'FFED1C24',
  'logins':[('Trakt','user','authorization')],
  'sign_in':'RunScript(script.trakt,action=auth_info)','manage':'Addon.OpenSettings(script.trakt)'},
 {'key':'tmdb','name':'TMDb Helper','addon':'plugin.video.themoviedb.helper','section':1,'icon':'film.png','tint':'FF01B4E4',
  'logins':[('Trakt','','trakt_token')],'prefix':'Home rows · ',
  'sign_in':'RunScript(plugin.video.themoviedb.helper,authenticate_trakt)',
  'manage':'Addon.OpenSettings(plugin.video.themoviedb.helper)'},
]
# Extra rows under the services (ids 9611...).
LINKS=[('Profiles & Login Screen','user.png','FF0A84FF','ActivateWindow(profiles)')]

def status(service,installed,get_setting,drive_accounts=()):
 """{'signed','text','button','action'} for one service. get_setting(id) reads the add-on's setting ('' if unset);
 drive_accounts: Google Drive's saved accounts (dicts with a 'name')."""
 prefix=service.get('prefix','')
 if not installed:
  return {'signed':False,'text':'Not installed','button':'Install','action':'InstallAddon(%s)'%service['addon']}
 if service.get('drive'):
  names=[str(a.get('name') or '').strip() for a in drive_accounts]
  if drive_accounts:
   shown=', '.join(n for n in names if n) or 'Signed in'
   return {'signed':True,'text':shown,'button':'','action':service['manage']}
  return {'signed':False,'text':'Not signed in','button':'Sign In','action':service['sign_in']}
 linked=[]
 for label,user_id,token_id in service['logins']:
  user=(get_setting(user_id) or '').strip() if user_id else ''
  token=(get_setting(token_id) or '').strip() if token_id else ''
  if user or token:linked.append((label,user))
 if not linked:
  return {'signed':False,'text':prefix+service.get('none','Not signed in'),'button':'Sign In','action':service['sign_in']}
 if len(service['logins'])==1:
  user=linked[0][1];text='Signed in as %s'%user if user else 'Signed in'
 else:text='Signed in · '+', '.join(label for label,_ in linked)
 return {'signed':True,'text':prefix+text,'button':'','action':service['manage']}

def initials(name):
 words=[w for w in str(name or '').replace('_',' ').split() if w[:1].isalnum()]
 return ''.join(w[0] for w in words[:2]).upper() or '?'

def summary(states):
 """'3 of 5 services signed in' (services that are not installed do not count)."""
 present=[s for s in states if s['button']!='Install'];signed=sum(1 for s in present if s['signed'])
 if not present:return 'No account add-ons installed'
 return '%d of %d service%s signed in'%(signed,len(present),'' if len(present)==1 else 's')

def properties(states,profile_name,thumb=''):
 """Window properties for portrait/IOSAccounts.xml: acct.<n>.* for service n (1-based, SERVICES order)."""
 # Kodi's stock profile picture (DefaultUser.png) is not a picture of anyone: show the initials instead.
 thumb='' if not thumb or 'DefaultUser' in thumb else thumb
 props={'name':profile_name or 'Master user','initials':initials(profile_name or 'Master user'),'thumb':thumb,
        'summary':summary(states)}
 for n,(service,state) in enumerate(zip(SERVICES,states),1):
  props.update({'acct.%d.name'%n:service['name'],'acct.%d.icon'%n:service['icon'],'acct.%d.tint'%n:service['tint'],
                'acct.%d.text'%n:state['text'],'acct.%d.signed'%n:'true' if state['signed'] else '',
                'acct.%d.button'%n:state['button']})
 return props
