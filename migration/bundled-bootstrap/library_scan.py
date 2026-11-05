"""Settings › Library › Scan iPhone files. Kodi runs this script outside the GUI thread."""
import os,sys
LIB=os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib')
if LIB not in sys.path:sys.path.insert(0,LIB)
from library_scan import run

if __name__=='__main__':run()
