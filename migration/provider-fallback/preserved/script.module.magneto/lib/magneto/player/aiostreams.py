import json
import requests
from .kore import logger, get_setting, set_property, int_window_prop

public_instance = (
	'https://aiostreams.stremio.ru',
	'https://',
	'https://aiostreams.viren070.me',
	'https://aiostreams.fortheweak.cloud',
	'https://aiostreamsfortheweebsstable.midnightignite.me'
)

def internal_results(provider, sources):
	set_property(int_window_prop % provider, json.dumps(sources))

class Debrid:
	def __init__(self):
		self.username = get_setting('aio.username')
		self.password = get_setting('aio.password')

	def resolve_basic_auth(self): # requests defaults to latin-1
		return tuple(i.strip().encode('utf-8') for i in (self.username, self.password))

	def resolve_aio_instance(self):
		instance_id = int(get_setting('aiostreams_instance', '0'))
		if instance_id == 1: return get_setting('aio.custom_url')
		return public_instance[instance_id]

	def unrestrict_link(self, item):
		from urllib.parse import urlencode
		from magneto.modules.client import randomagent
		logger('aiostreams', f"unrestrict_link\n{json.dumps(item, indent=2)}")
		headers = item.get('requestHeaders')
		try: req_headers = requests.structures.CaseInsensitiveDict(headers)
		except: req_headers = requests.structures.CaseInsensitiveDict()
		if 'User-Agent' not in req_headers: req_headers['User-Agent'] = randomagent()
		try: # some servers do not accept HEAD requests, must use GET + stream
			with requests.get(item.get('url'), headers=req_headers, stream=True, timeout=30) as response:
				response.raise_for_status() # 3xx passes, 4xx/5xx raises
			if headers: return '|'.join((response.url, urlencode(headers)))
			return response.url
		except requests.exceptions.RequestException as e:
			logger('unrestrict_link error', f"{type(e)}: {e}")

class source(Debrid):
	timeout = 30
	scrape_provider = 'aiostreams'
	def results(self, info):
		try:
			self.sources = []
			sources_append = self.sources.append
			if not all((self.username.strip(), self.password.strip())): return internal_results(self.scrape_provider, self.sources)
			self.elapsed, self.errors = None, None
			title, season, episode = info.get('title'), info.get('season'), info.get('episode')
			if 'timeout' in info: self.timeout = info['timeout'] + 1
			media_id = info['imdb_id'] or ('tmdb:%s' % info['tmdb_id'])
			self.scrape_results = self.search(media_id, season, episode)
			if not self.scrape_results: return internal_results(self.scrape_provider, self.sources)
			for item in self.scrape_results:
				if 'p2p' in item['type']: continue
				item.pop('sources', None)
				file = {'scrape_provider': self.scrape_provider, **item.pop('parsedFile', {})}
				try: file.update(item)
				except: pass
				else: sources_append(file)
		except Exception as e: logger(f"Magneto {self.scrape_provider} Exception", f"{e}")
		if self.errors: logger(self.scrape_provider, f"{self.errors}")
		logger(self.scrape_provider, f"{title} : {self.elapsed}s, {len(self.sources)}, {len(self.scrape_results)}")
		internal_results(self.scrape_provider, self.sources)
		return self.sources

	def search(self, media_id, season, episode):
		scrape_results = []
		if episode: params = {'type': 'series', 'id': '%s:%s:%s' % (media_id, season, episode)}
		else: params = {'type': 'movie', 'id': '%s' % media_id}
		params['requiredFields'] = 'parsedFile'
		try:
			auth = self.resolve_basic_auth()
			base_url = self.resolve_aio_instance()
			search_link = '%s/api/v1/search' % base_url.strip().rstrip('/')
			response = requests.get(search_link, params=params, auth=auth, timeout=self.timeout)
			self.elapsed = round(response.elapsed.total_seconds(), 3)
			if not response.ok: response.raise_for_status()
			results = response.json()['data']
			self.errors = [': '.join(i.values()) for i in results['errors']]
			scrape_results.extend(results['results'])
		except requests.exceptions.RequestException as e:
			logger(self.scrape_provider, f"{e}\n{e.request.url}")
		return scrape_results
