import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
import updates
updates.run(check_only=len(sys.argv)>1 and sys.argv[1]=='--check')
