"""Small API transaction: enable dependencies first; undo new enables on failure."""
def order_addons(manifests):
 visiting=set();done=set();order=[]
 def visit(id):
  if id in done:return
  if id in visiting:raise ValueError('Add-on dependency cycle')
  visiting.add(id)
  for dep in manifests[id]['requires']:
   if dep in manifests:visit(dep)
  visiting.remove(id);done.add(id);order.append(id)
 for id in sorted(manifests):visit(id)
 return order

def activate(api,manifests):
 states={}
 for id in order_addons(manifests):
  r=api('Addons.GetAddonDetails',{'addonid':id,'properties':['enabled','version']})
  if 'error' in r:return {'status':'BLOCKED','failed_addon':id,'reason':'Not discovered by Kodi','newly_enabled':[]}
  states[id]=r['result']['addon']['enabled']
 changed=[]
 for id in order_addons(manifests):
  if states[id]:continue
  r=api('Addons.SetAddonEnabled',{'addonid':id,'enabled':True})
  if 'error' in r or r.get('result')!='OK':
   rollback=[]
   for previous in reversed(changed):
    undo=api('Addons.SetAddonEnabled',{'addonid':previous,'enabled':False});rollback.append({'id':previous,'ok':undo.get('result')=='OK'})
   return {'status':'FAILED','failed_addon':id,'newly_enabled':changed,'rollback':rollback,'phone_behavior_verified':False}
  changed.append(id)
 return {'status':'API ENABLE REQUESTS ACCEPTED','newly_enabled':changed,'phone_behavior_verified':False}
