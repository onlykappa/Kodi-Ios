"""Shared tab identities and actions. Deliberately independent of layout generation and add-on/network work."""
TAB_PROPERTY='Portrait.Tab'
HUB_TABS=('home','movies','tv')
HUB_OFFSET={'home':0,'movies':10000,'tv':20000}
# Preloader (owner, build-135: "bring back the preloader, it was game changing"). The three hubs share Home.xml and
# every row of Home, Movies and TV loads as soon as Home opens, then keeps its titles: switching tabs finds them
# filled. Home's hero and rows come first in the window, so Kodi queues them first. The performance pass had made
# Movies/TV wait for their first visit (and Home's lower rows two seconds), which the owner felt as every menu
# saying "Loading...". Fuse's startup scripts stay off and there is still one tab bar.
def tab_actions(key):
 """[(condition, builtin)] for one tab: hubs set the property (and come back to Home), the others open their window."""
 if key in HUB_TABS:
  return [('','ClearProperty(%s,home)'%TAB_PROPERTY if key=='home' else 'SetProperty(%s,%s,home)'%(TAB_PROPERTY,key)),
          ('!Window.IsActive(home)','ReplaceWindow(Home)'),('','SetFocus(%d)'%(4000+HUB_OFFSET[key]))]
 return [('','ReplaceWindow(%s)'%{'library':1103,'search':1105}[key])]
TABS=[('home','Home','house.png'),('movies','Movies','film.png'),('tv','TV','tv.png'),('library','Library','layer-group.png'),
      ('search','Search','magnifying-glass.png')]
