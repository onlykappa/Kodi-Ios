import importlib.util,sys,types,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('deck_picker',ROOT/'migration/deck-picker/deck_picker.py')
dp=importlib.util.module_from_spec(spec);spec.loader.exec_module(dp)
# The streams Elementum listed on the phone for Orange Is the New Black S01E01 (owner's screenshot), in its format.
ITEMS=['[B][COLOR FF5AB3FF]1080p[/COLOR][/B] (75 / 0) [B][1.71 GB][/B] Blu-Ray H.265 AC3 - [B]Torrentio[/B]\nIs the New Black (2013) Season 1-7 S01-S07 (1080p BluRay x265 HEVC 10bit AAC 5.1 Silence) [QxR] Season 1/Orange Is the New Black (2013) - S01E01.mkv\nicon.png',
 '1080p (39 / 0) [347.48 MB] WebDL H.265 AC3 - Torrentio\n[RE-UP] Orange Is The New Black (2013) Season 01 S01 (1080p WEBRip x265 HEVC AAC 5.1 Joy) [UTR] Orange Is The New Black S01E01.mkv\nicon.png',
 '1080p (22 / 0) [1.3 GB] Blu-Ray H.265 - Torrentio\nOrange.Is.The.New.Black.S01-S07.Complete.Series.1080p.Bluray.x265-HiQVE/Orange.Is.The.New.Black.S01E01.mkv\nicon.png',
 '1080p (17 / 0) [3.97 GB] Blu-Ray H.264 - Torrentio\nOrange.is.the.New.Black.S01.1080p.BluRay.x264-ROVERS[rartv] orange.is.the.new.black.s01e01.1080p.bluray.x264-rovers.mkv\nicon.png',
 '1080p (9 / 0) [1.59 GB] Blu-Ray H.265 - Torrentio\nOrange.Is.the.New.Black.S01.1080p.BluRay.x265-YAWNiX Orange.Is.the.New.Black.S01E01.1080p.BluRay.x265-YAWNiX.mkv\nicon.png',
 '1080p (6 / 0) [995.3 MB] WebDL H.264 AC3 - Torrentio\n[moon] Orange is the New Black - Season 1 1080p WEBRip x264 AC3 MultiSubs E01 I Wasn\'t Ready.mp4\nicon.png',
 '1080p (6 / 0) [1.82 GB] Blu-Ray H.264 - Torrentio\nOrange.is.the.New.Black.S01.Season.1.Complete.1080p.BluRay.x264-maximersk [mrsktv] Orange.Is.The.New.Black.S01E01.1080p.BluRa.mkv\nicon.png',
 '1080p (7 / 0) [1.49 GB] H.264 AC3 - Torrentio\nOrange Is The New Black - Season 1 to 6 - Mp4 x264 AC3 1080p Season 1/Orange Is The New Black S01E01.mp4\nicon.png',
 '720p (7 / 0) [278.58 MB] Blu-Ray H.265 AC3 - Torrentio\nOrange Is the New Black S01 Complete 720p HEVC [Hindi 5.1 English] BluRay Dual-Audio x265 - KatmovieHD Orange.is.the.New.Black.S0.mkv\nicon.png']

class DeckPicker(unittest.TestCase):
 def test_reads_every_stream_from_the_phone(self):
  parsed=dp.parse_all(ITEMS);self.assertEqual(len(parsed),len(ITEMS))
  self.assertEqual((parsed[0]['quality'],parsed[0]['seeds'],round(parsed[0]['size'],2),parsed[0]['providers']),('1080p',75,1.71,['Torrentio']))
 def test_quality_first_then_five_best_and_the_choice_maps_back(self):
  seen={}
  def quality(labels):seen['qualities']=labels;return 0
  def source(title,rows,quality,count):seen['rows']=rows;seen['quality']=quality;return 1
  with mock.patch.object(dp,'choose_quality',quality),mock.patch.object(dp,'choose_source',source):
   choice=dp.run('Orange Is the New Black S01E01',ITEMS)
  self.assertIn('1080p Full HD',seen['qualities'][0]);self.assertTrue(seen['qualities'][-1].startswith('Show all 9'))
  self.assertEqual(len(seen['rows']),dp.TOP_N+1)
  shown=dp.pick(dp.group_by_quality(dp.parse_all(ITEMS))[1]['1080p'],dp.TOP_N)
  self.assertEqual(choice,shown[1]['idx']);self.assertTrue(0<=choice<len(ITEMS))
 def test_cancel_and_show_all_fall_back_safely(self):
  with mock.patch.object(dp,'choose_quality',lambda labels:-1):self.assertEqual(dp.run('t',ITEMS),-1)
  with mock.patch.object(dp,'choose_quality',lambda labels:len(labels)-1):self.assertIsNone(dp.run('t',ITEMS))
  self.assertIsNone(dp.run('t',['not a torrent line']*10));self.assertIsNone(dp.run('t',ITEMS[:3]))

class WatchMenuDetails(unittest.TestCase):
 def test_details_left_for_the_picker(self):
  spec=importlib.util.spec_from_file_location('watch',ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_watch_dialog.py')
  watch=importlib.util.module_from_spec(spec);spec.loader.exec_module(watch)
  props={};window=types.SimpleNamespace(setProperty=props.__setitem__)
  player=types.SimpleNamespace(tmdb_type='tv',details=types.SimpleNamespace(
   infolabels={'tvshowtitle':'Orange Is the New Black','season':1,'episode':1,'year':2013,'duration':3540,'plot':'Piper goes to prison.'},
   art={'tvshow.poster':'poster.jpg','fanart':'fan.jpg'}))
  watch.share_details(player,window)
  self.assertEqual(props['Deck.Picker.Title'],'Orange Is the New Black');self.assertEqual(props['Deck.Picker.Meta'],'S01E01  |  2013  |  59 min')
  self.assertEqual((props['Deck.Picker.Poster'],props['Deck.Picker.Fanart'],props['Deck.Picker.Plot']),('poster.jpg','fan.jpg','Piper goes to prison.'))
if __name__=='__main__':unittest.main()
