"""Exercise the actual saved helper's pure view generator with vetted layout input.
No Kodi runtime, original writes, network or add-on entry point is executed.
"""
import argparse,ast,functools,hashlib,json,types,xml.etree.ElementTree as ET
from pathlib import Path

def semantic(elements):return [(x.tag,sorted(x.attrib.items()),(x.text or '').strip()) for x in elements]
def validate(data_root,inputs):
 skin=data_root/'addons/skin.arctic.fuse.3';helper=data_root/'addons/script.skinvariables/resources/lib/viewtypes.py'
 meta=json.loads((skin/'shortcuts/skinviewtypes.json').read_text());choices=json.loads(inputs.read_text())
 assert set(choices)<={'library','plugins','plugin.video.youtube'}
 for group,rules in choices.items():
  for content,view in rules.items():assert content in meta['rules'] and view in meta['rules'][content]['viewtypes'],'Unknown view choice'
 tree=ast.parse(helper.read_text());selected=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in {'join_conditions','ViewTypes'}]
 assert len(selected)==2
 class Progress:
  def create(self,*a,**kw):pass
  def update(self,*a,**kw):pass
  def close(self):pass
 scope={'cached_property':functools.cached_property,'xbmcgui':types.SimpleNamespace(DialogProgressBG=Progress),'ADDON':types.SimpleNamespace(getLocalizedString=lambda x:str(x))}
 exec(compile(ast.Module(body=selected,type_ignores=[]),str(helper),'exec'),scope)
 obj=object.__new__(scope['ViewTypes']);obj.__dict__.update(meta=meta,addon_meta=choices)
 generated=obj.make_xmltree();elements=[]
 for entry in generated:
  el=ET.Element(entry['tag'],entry['attrib']);el.text=entry['content'];elements.append(el)
 original=ET.parse(skin/'1080i/script-skinviewtypes-includes.xml').getroot()
 assert semantic(elements)==semantic(original),'Saved view input does not reproduce baseline generated expressions'
 return {'passed':True,'actual_helper_source_sha256':hashlib.sha256(helper.read_bytes()).hexdigest(),'skin_metadata_sha256':hashlib.sha256((skin/'shortcuts/skinviewtypes.json').read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(inputs.read_bytes()).hexdigest(),'generated_expressions':len(elements),'baseline_semantics_equal':True,'view_choices':sum(map(len,choices.values())),'source_written':False,'kodi_or_phone_runtime_tested':False,'shortcut_cache_resolution':'Do not import stale generated shortcut cache; retain sanitized nodes/settings and upstream pending-rebuild trigger. Actual first-run generation still needs phone validation.'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private-data',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=validate(a.private_data,a.inputs);a.report.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
