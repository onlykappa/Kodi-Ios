"""The storage-free preparation queue: Drive → RAM converter → Drive staging → original ID."""
import json
import shutil
import urllib.parse
import urllib.request
import drive_prepare
import driveupload
import drivelibrary
import prepare_downloads as prep


def process_one(q, keep_going):
    for j in q.state['jobs'].values():
        if j.pop('space',None):j['retry_after']=0
        if j.get('status')=='done' and j.get('cloud_output'):
            left={}
            for track,output in j['cloud_output'].items():
                if output.get('moved'):continue
                try:drivelibrary.trash(q.drive,output['id'])
                except Exception:left[track]=output
            j['cloud_output']=left;q.commit()
    candidates = [(slot,j) for slot,j in q.state['jobs'].items() if j.get('status') not in ('done','superseded')
                  and not j.get('blocked') and not j.get('kept') and j.get('retry_after',0) <= q.clock()]
    # Old builds' checkpoints are no longer used: their full-sized local media can go.
    for folder in q.work.iterdir():
        if folder.is_dir():shutil.rmtree(folder)
    if not candidates:return False
    candidates.sort(key=lambda pair:(-pair[1].get('priority',0),pair[0]))
    slot,job = candidates[0];item = job['source'];last = [0]
    job.pop('space',None)
    def progress(stage,pct):
        if not keep_going():raise driveupload.Stop('Preparation paused')
        now = q.clock()
        if now-last[0] < .5 and pct < 100:return
        last[0] = now
        q.state['current'] = dict(title=item['name'],stage='Step 3 of 3 · '+stage,progress=max(0,min(100,pct)),
                                  queued=len(candidates),running=True,updated=now)
        q.commit()
    def clear_temps():
        for output in (job.get('cloud_output') or {}).values():
            if output.get('moved'):continue
            try:drivelibrary.trash(q.drive,output['id'])
            except Exception:return False
        job.pop('cloud_output',None);q.commit();return True
    outputs = job.setdefault('cloud_output',{})
    temp_id = None
    try:
        progress('Reading from Google Drive',0)
        current = prep.metadata(q.drive,item['id'])
        if prep.ready(current):
            job['status']='done';clear_temps();q.commit();return True
        main = outputs.get('0')
        completed = bool(main and int(current['size']) == int(main['size']) and current['md5Checksum'].lower() == main['md5Checksum'].lower())
        if not completed:
            if prep.identity(current) != prep.identity(item):raise RuntimeError('Drive source changed; preparation will rescan')
            source = q.stream.url(item['id'])
            if not main:
                # Remove completed sidecars from an interrupted generation before retrying.
                if not clear_temps():raise RuntimeError('Preparation temporary files could not be cleaned up')
                outputs=job.setdefault('cloud_output',{})
                before=q.native.probe(source);job['probe']=before;q.commit()
                parent=q.drive.folder([driveupload.TOP,'.Preparation'])
                def on_file(track,result):outputs[track]=result;q.commit()
                sink=drive_prepare.Sink(q.drive,parent,slot,keep_going,on_file)
                try:
                    q.native.convert_to(source,sink,keep_going,
                        lambda stage,n,t:progress('Converting and saving to Drive',min(80,80*n/t) if t else 0))
                    sink.finish()
                except Exception:
                    # Drop RAM buffers immediately. Complete staging objects are recorded for cleanup next time.
                    sink.tracks.clear();raise
                main=outputs['0']
            temp_id=main['id'];target=q.stream.url(temp_id)
            progress('Verifying the Drive file and seek index',82)
            after=q.native.probe(target);before=job.get('probe') or q.native.probe(source)
            if not after.get('ready') or (before['width'],before['height'],before['hdr']) != (after['width'],after['height'],after['hdr']):
                raise RuntimeError('Prepared video did not preserve resolution/HDR; original retained')
            q.native.verify(source,target)  # duration, all tracks, middle/end index seeks over HTTP
            # Move tiny subtitle sidecars beside the movie before replacing its source.
            parents=current.get('parents') or []
            if any(k!='0' for k in outputs) and not parents:raise RuntimeError('Drive did not describe the video folder')
            for track,side in outputs.items():
                if track=='0' or side.get('moved'):continue
                suffix=side['name'][len(slot):]
                name=item['name'].rsplit('.',1)[0]+suffix
                status,_,_=q.drive.call('PATCH',driveupload.API+'/'+urllib.parse.quote(side['id'],safe='')+
                    '?addParents='+urllib.parse.quote(parents[0],safe='')+'&removeParents='+urllib.parse.quote(q.drive.folder([driveupload.TOP,'.Preparation']),safe=''),
                    json.dumps({'name':name}).encode(),{'Content-Type':'application/json'})
                if status!=200:raise RuntimeError('Subtitle save: HTTP %d'%status)
                side['moved']=True;q.commit()
            job['status']='committing';q.commit()
            def open_at(offset):
                return urllib.request.urlopen(urllib.request.Request(target,headers={'Range':'bytes=%d-'%offset}),timeout=60)
            current=drive_prepare.replace(q.drive,item,main,job.setdefault('cloud_replace',{}),q.commit,keep_going,open_at,
                lambda n,t:progress('Finalizing on Google Drive',85+14*n/t))
        digest=main['md5Checksum'].lower()
        if not driveupload.confirmed(q.drive,item['id'],int(main['size']),digest):raise RuntimeError('Prepared Drive file checksum differs')
        props=dict(current.get('appProperties') or {});props.update({prep.PROPERTY:prep.PROFILE,prep.CHECKSUM_PROPERTY:digest})
        status,_,_=q.drive.call('PATCH',driveupload.API+'/'+urllib.parse.quote(item['id'],safe=''),json.dumps({'appProperties':props}).encode(),{'Content-Type':'application/json'})
        if status!=200:raise RuntimeError('Preparation verification marker: HTTP %d'%status)
        # Sidecars now belong to the library; only the temporary main movie is removed.
        job['cloud_output']={'0':main};job['status']='done';job['completed']=q.clock();q.commit();clear_temps()
        driveupload.invalidate_library(str(prep.location(q.profile).parent));prep.request_check(q.profile)
        q.state.pop('current',None);q.commit()
        q.notify('info','Ready for Kodi and AirPlay',drivelibrary.display_title(item['name']));return True
    except driveupload.Stop:
        if job.get('status')!='committing':job['status']='paused'
        job['retry_after']=0;return False
    except Exception as error:
        job['attempts']=job.get('attempts',0)+1
        job['retry_after']=q.clock()+min(3600,60*2**min(job['attempts']-1,6))
        if job.get('status')!='committing':job['status']='failed'
        text=str(error) if isinstance(error,RuntimeError) else 'Preparation paused (%s)'%type(error).__name__
        if 'http://' in text or 'https://' in text:text='Preparation paused; connection needs a retry'
        if 'source changed' in text:job['status']='superseded';q.state['last_scan']=0;clear_temps()
        elif 'tracks MP4 cannot preserve' in text or 'without changing HDR' in text:job['blocked']=True
        if job.get('error')!=text:q.notify('problem','Video preparation paused',drivelibrary.display_title(item['name'])+': '+text[:200])
        job['error']=text;return False
    finally:
        q.stream.forget(item['id'])
        if temp_id:q.stream.forget(temp_id)
        if q.state.get('current'):q.state['current'].update(running=False,updated=q.clock())
        q.commit()
