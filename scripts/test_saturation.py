"""DEC-039 V2: Saturation from the Picture menu changes the picture (Kodi r32: SetVideoSaturation(n) built-in, a
luma-preserving saturation folded into the GLES YUV-to-RGB matrix) and each video starts with its own value."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap'
sys.dont_write_bytecode=True
sys.path.insert(0,str(BOOT/'resources/lib'))
import picture
PATCH=(ROOT/'migration/ios-portrait/kodi-21.3-portrait.patch').read_text()

class Builtin(unittest.TestCase):
 def test_value_is_clamped(self):
  self.assertEqual(picture.builtin(12),'SetVideoSaturation(12)')
  self.assertEqual(picture.builtin(90),'SetVideoSaturation(50)')
  self.assertEqual(picture.builtin(-90),'SetVideoSaturation(-50)')

class Sync(unittest.TestCase):
 def test_each_video_gets_its_own_and_nothing_is_resent(self):
  data={'default':{'upscale':'off','saturation':0},'shows':{},'videos':{}}
  naruto={'type':'tv','show':'Naruto','title':'Homecoming','drive_id':'d1'}
  data=picture.apply(data,'show',naruto,saturation=20)
  film={'type':'movie','show':'Fall','title':'Fall','drive_id':'d2'}
  sync=picture.SaturationSync()
  self.assertEqual(sync.step(True,naruto,data),'SetVideoSaturation(20)')
  self.assertIsNone(sync.step(True,naruto,data))                       # the same video: nothing new
  self.assertEqual(sync.step(True,film,data),'SetVideoSaturation(0)')  # a show's +20 never stays on the next film
  self.assertIsNone(sync.step(False,{},{}))
  self.assertEqual(sync.step(True,film,data),'SetVideoSaturation(0)')  # a new start sends it again
  data=picture.apply(data,'default',film,saturation=-10)
  self.assertEqual(sync.step(True,film,data),'SetVideoSaturation(-10)')  # changed while playing

class Patch(unittest.TestCase):
 def test_builtin_and_matrix(self):
  self.assertIn('{"setvideosaturation",  {"Kodi iOS: set the video saturation (-50..50)", 1, SetVideoSaturation}},',PATCH)
  self.assertIn('+std::atomic<int> g_videoSaturation{0};',PATCH)
  self.assertIn('+extern std::atomic<int> g_videoSaturation;',PATCH)
  for needle in ('const float w[3] = {0.2126f, 0.7152f, 0.0722f};','yuvMat[c][0] = k * r + luma;','KODI_IOS::g_videoSaturation.load(std::memory_order_relaxed)'):
   self.assertIn(needle,PATCH)
 def test_the_add_on_sends_it(self):
  self.assertIn("xbmc.executebuiltin(picture.builtin(picture.resolve(settings, media)[1]['saturation']))",(BOOT/'picture_page.py').read_text())
  self.assertIn('sync=picture.SaturationSync()',(BOOT/'service.py').read_text())

class Matrix(unittest.TestCase):
 """The C++ arithmetic, in Python: grey stays grey and keeps its luma; colour moves away from (or toward) grey."""
 def saturate(self,mat,saturation):
  k=1+saturation/100;w=(0.2126,0.7152,0.0722);out=[list(c) for c in mat]
  for c in range(4):
   r,g,b=out[c][0],out[c][1],out[c][2];luma=(1-k)*(w[0]*r+w[1]*g+w[2]*b)
   out[c][0],out[c][1],out[c][2]=k*r+luma,k*g+luma,k*b+luma
  return out
 def apply(self,mat,v):return [sum(mat[c][row]*v[c] for c in range(4)) for row in range(3)]
 def test_grey_kept_colour_scaled(self):
  # A BT.709 full-range YUV->RGB matrix, column-major (mat[column][row]), input (y, u-0.5, v-0.5, 1).
  mat=[[1,1,1,0],[0,-0.1873,1.8556,0],[1.5748,-0.4681,0,0],[0,0,0,1]]
  for s in (-50,30):
   m=self.saturate(mat,s)
   grey=self.apply(m,(0.5,0,0,1));self.assertTrue(all(abs(x-0.5)<1e-6 for x in grey))
   red=self.apply(mat,(0.3,-0.1,0.4,1));red2=self.apply(m,(0.3,-0.1,0.4,1))
   luma=lambda p:0.2126*p[0]+0.7152*p[1]+0.0722*p[2]
   self.assertAlmostEqual(luma(red),luma(red2),places=6)
   self.assertAlmostEqual(red2[0]-luma(red2),(1+s/100)*(red[0]-luma(red)),places=6)

if __name__=='__main__':unittest.main()
