"""The storage-free preparation queue: Drive → RAM converter → Drive staging → original ID."""
import json
import shutil
import urllib.parse
import urllib.request
import drive_prepare
import driveupload
import drivelibrary
import prepare_downloads as prep
import preparation_runtime
import diagnostics


def process_one(q, keep_going):
    # Cleanup is independent of jobs: a library rescan can remove completed or superseded jobs.
    # Journal before deleting, and retry 404 safely if a process exited after Drive acknowledged deletion.
    pending=q.state.setdefault('staging_cleanup',[])
    for item_id in list(pending):
        try:drive_prepare.discard(q.drive,item_id)
        except Exception:continue
        pending.remove(item_id);q.commit()
    if pending:return False
    for j in q.state['jobs'].values():
        if j.pop('space',None):j['retry_after']=0
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
        if q.runtime:q.runtime.phase(stage,pct is not None,item['name'])
        if not keep_going():raise driveupload.Stop('Preparation paused')
        now = q.clock()
        if now-last[0] < .5 and (pct or 0) < 100:return
        last[0] = now
        # Owner (build 170): speed and time left, not a bare "Converting and saving to Drive".
        speed=q.read_speed(now)
        mark=job.setdefault('eta_mark',[now,pct or 0]) if pct is not None else None
        eta=''
        if mark and (pct or 0)-mark[1]>=0.2 and now>mark[0]:
            eta=prep.eta_text((now-mark[0])*(100-(pct or 0))/((pct or 0)-mark[1]))
        q.state['current'] = dict(title=item['name'],stage='Step 3 of 3 · '+stage,progress=max(0,min(100,pct or 0)),indeterminate=pct is None,
                                  queued=len(candidates),running=True,updated=now,read=speed[0],rate=speed[1],
                                  detail=prep.speed_text(*speed),eta=eta)
        q.commit()
    def clear_temps():
        discard=[o['id'] for o in (job.get('cloud_output') or {}).values() if not o.get('moved')]
        pending=q.state.setdefault('staging_cleanup',[])
        pending.extend(item_id for item_id in discard if item_id not in pending)
        job.pop('cloud_output',None);job.pop('cloud_replace',None);q.commit()
        success=True
        for item_id in discard:
            try:drive_prepare.discard(q.drive,item_id)
            except Exception:success=False;continue
            if item_id in pending:pending.remove(item_id)
            q.commit()
        return success
    q.native.keep_going=keep_going
    outputs = job.setdefault('cloud_output',{})
    temp_id = None
    try:
        q.log('preparation: %s — opening Drive file'%drivelibrary.display_title(item['name']))
        progress('Reading from Google Drive',None)
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
                progress('Inspecting video and track index',None)
                before=q.native.probe(source);job['probe']=before;q.commit()
                q.log('preparation: %s — codec %s, %sx%s, %s-bit, HDR=%s, copy=%s, audio work=%s'%(drivelibrary.display_title(item['name']),before.get('codec'),before.get('width'),before.get('height'),before.get('bit_depth'),before.get('hdr'),before.get('copy_video'),before.get('audio_work_bytes')))
                progress('Opening conversion tracks',None)
                parent=q.drive.folder([driveupload.TOP,'.Preparation'])
                def on_file(track,result):outputs[track]=result;q.commit()
                sink=drive_prepare.Sink(q.drive,parent,slot,keep_going,on_file)
                converted=[0]
                def converted_progress(stage,n,t):
                    value=80 if stage==3 else (min(80,80*n/t) if t else converted[0])
                    converted[0]=max(converted[0],value)
                    progress('Converting and saving to Drive',converted[0])
                try:
                    q.native.convert_to(source,sink,keep_going,
                        converted_progress)
                    sink.finish()
                except Exception:
                    # Drop RAM buffers immediately. Complete staging objects are recorded for cleanup next time.
                    sink.tracks.clear();raise
                main=outputs['0']
            temp_id=main['id'];target=q.stream.url(temp_id)
            progress('Verifying the Drive file and seek index',82)
            try:
                fresh=prep.metadata(q.drive,temp_id)
                if (fresh['md5Checksum'].lower(),int(fresh['size'])) != (main['md5Checksum'].lower(),int(main['size'])):
                    raise RuntimeError('Prepared Drive file checksum differs; original retained')
                after=q.native.probe(target);before=job.get('probe') or q.native.probe(source)
                if not after.get('ready') or (before['width'],before['height'],before['hdr']) != (after['width'],after['height'],after['hdr']):
                    raise RuntimeError('Prepared video did not preserve resolution/HDR; original retained')
                q.native.verify(source,target)  # duration, all tracks, middle/end index seeks over HTTP
            except driveupload.Stop:raise
            except Exception as error:
                # Network interruptions can retry a valid completed object; invalid output must be regenerated.
                if isinstance(error,RuntimeError) and any(word in str(error).lower() for word in ('validation','preserve','checksum')):clear_temps()
                raise
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
        job['cloud_output']={'0':main};job['status']='done';job['completed']=q.clock()
        pending=q.state.setdefault('staging_cleanup',[])
        if main['id'] not in pending:pending.append(main['id'])
        q.commit();clear_temps()
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
        diagnostics.exception(q.log,'preparation',error,phase=(q.state.get('current') or {}).get('stage','opening'),attempt=job['attempts'],video=job.get('probe') or {})
        text=preparation_runtime.problem(error)
        if 'could not be inspected' in text and q.stream and hasattr(q.stream,'stats'):
            underlying=q.stream.stats().get('read_error')
            if underlying:text+=': '+underlying
        q.log('preparation: failed for %s: %s; phase=%s; video=%s'%(drivelibrary.display_title(item['name']),text,(q.state.get('current') or {}).get('stage','opening'),json.dumps(job.get('probe') or {},sort_keys=True)))
        if 'source changed' in text:job['status']='superseded';q.state['last_scan']=0;clear_temps()
        elif 'tracks MP4 cannot preserve' in text or 'without changing HDR' in text or 'needs RPU remapping' in text:job['blocked']=True
        if job.get('error')!=text:
            q.notify('problem','Video preparation paused',drivelibrary.display_title(item['name'])+': '+text[:200])
            # Transfers › History: once per video and reason, like the notification (not a source changed meanwhile).
            if job.get('status')!='superseded':
                import transfer_history;transfer_history.failed(q.profile,'conv',item['name'],prep.plain(text),q.clock())
        job['error']=text;return False
    finally:
        q.stream.forget(item['id'])
        if temp_id:q.stream.forget(temp_id)
        if q.state.get('current'):q.state['current'].update(running=False,updated=q.clock())
        q.commit()
