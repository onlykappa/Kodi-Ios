"""Pages for scripts/measure_backup.py: one valid answer per site so the parallel search has real work to merge."""
import json
H=lambda n:'%040x'%n
PAGES={'apibay.org':json.dumps([{'id':'1','name':'Example.Film.2024.1080p.WEB-DL.x264','info_hash':H(1),'seeders':'50','size':'2000000000'}]),
 'movies-api.accel.li':json.dumps({'status':'ok','data':{'movie_count':0}}),'eztvx.to':json.dumps({'torrents':[]}),
 'api.knaben.org':json.dumps({'hits':[{'title':'Example.Film.2024.1080p.BluRay','hash':H(2),'seeders':70,'bytes':3e9}]})}
