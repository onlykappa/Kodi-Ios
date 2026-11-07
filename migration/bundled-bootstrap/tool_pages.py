"""RunScript(service.kodi.ios.bootstrap,tool_pages,<queue|history|airplay>): one of the library tools' pages
(resources/lib/tool_windows.py runs them; Library status, Transfers, Play on TV and Notifications open them directly)."""
import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import tool_windows

def run(args=()):tool_windows.run(args)

if __name__=='__main__':run(sys.argv[1:])
