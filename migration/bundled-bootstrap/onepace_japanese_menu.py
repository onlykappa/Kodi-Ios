"""Context item: Play in Japanese (English subtitles) on a dubbed One Pace episode (the logic is onepace_menu.py)."""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import onepace_menu
onepace_menu.sys.argv=[sys.argv[0],'japanese']
onepace_menu.run()
