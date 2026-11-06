"""Script entry of service.kodi.ios.bootstrap: RunScript(service.kodi.ios.bootstrap[,page[,arguments...]]).

The phone's buttons (bell, Play on TV, speed, Accounts, gear menu...) used to run their scripts by file path, so Kodi
could not tell which add-on they belong to: it logged "Script invoked without an addon" and put every installed
add-on's modules on the Python path before each one started (owner's logs, ISSUE-071). By add-on id it sets up only
this add-on. Without a page this is the recovery script, as the add-on's script entry always was.
"""
import os,runpy,sys
HERE=os.path.dirname(os.path.abspath(__file__))
PAGES=('notifications','cast','speed','accounts_page','settings_search','navigation_menu','check_updates','download','activity_page','library_scan','prepare_check','library_status','recover')

def target(argv):
 """(script path, its argv) for RunScript's arguments."""
 page=argv[1] if len(argv)>1 and argv[1] in PAGES else 'recover'
 rest=argv[2:] if len(argv)>1 and argv[1] in PAGES else argv[1:]
 path=os.path.join(HERE,page+'.py')
 return path,[path]+list(rest)

if __name__=='__main__':
 path,sys.argv=target(sys.argv)
 runpy.run_path(path,run_name='__main__')
