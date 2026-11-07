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
import resume_store


# A re-pack (faster start) that fails on one of these converter errors would fail the same way every time.
REPACK_STOPS=('MP4 packet','Picture subtitle packet','Subtitle decode','Subtitle encode')


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
    with q.lock:   # build 191: a library check may change the list beside a conversion
        candidates = [(slot,j) for slot,j in q.state['jobs'].items() if j.get('status') not in ('done','superseded')
                      and not j.get('blocked') and not j.get('kept') and j.get('retry_after',0) <= q.clock()]
    # Old builds' checkpoints are no longer used: their full-sized local media can go.
    for folder in q.work.iterdir():
        if folder.is_dir():shutil.rmtree(folder)
    if not candidates:return False
    candidates.sort(key=lambda pair:prep.order_key(*pair))   # build 182: quick (repack only) before re-encodes
    slot,job = candidates[0];item = job['source'];last = [0]
    job.pop('space',None)
    # Build 177: time left and pace come from this attempt only. The old job['eta_mark'] outlived stopped attempts,
    # so a restart measured from hours earlier ("about 46 h 28 min", owner screenshot).
    job.pop('eta_mark',None);job['started_at']=q.clock()   # Library status › a ready movie: "took 41 min"
    attempt={'mark':None,'sink':None,'fraction':0.0,'convert_start':None}
    def progress(stage,pct):
        if q.runtime:q.runtime.phase(stage,pct is not None,item['name'])
        if not keep_going():raise driveupload.Stop('Preparation paused')
        now = q.clock()
        if now-last[0] < .5 and (pct or 0) < 100:return
        last[0] = now
        # Owner (build 170): speed and time left, not a bare "Converting and saving to Drive".
        speed=q.read_speed(now)
        if pct is not None and attempt['mark'] is None:attempt['mark']=[now,pct]
        mark=attempt['mark'];eta=''
        eta_s=0
        if mark and (pct or 0)-mark[1]>=0.2 and now>mark[0]:
            eta_s=(now-mark[0])*(100-(pct or 0))/((pct or 0)-mark[1]);eta=prep.eta_text(eta_s)
        current=dict(title=item['name'],stage='Step 3 of 3 · '+stage,kind='repack' if job.get('repack') else 'conv',progress=max(0,min(100,pct or 0)),indeterminate=pct is None,
                     queued=len(candidates),running=True,updated=now,read=speed[0],rate=speed[1],
                     detail=prep.speed_text(*speed),eta=eta,eta_s=eta_s)
        # Build 177 (owner-approved movie sheet): upload speed, film done, pace and the expected size.
        sink=attempt['sink'];duration=float((job.get('probe') or {}).get('duration') or 0)
        if sink is not None:
            f=attempt['fraction'];up=sink.rate()
            current.update(up_rate=up,out_bytes=sink.sent,film_total=duration,film_done=f*duration)
            if f>0.01 and attempt['convert_start'] and now>attempt['convert_start']:
                current['pace']=f*duration/(now-attempt['convert_start'])
                current['out_total']=int(sink.sent/f) if sink.sent else 0
            # What the graphs show while converting: the movie going up to Drive, or, before the first piece is up
            # (build-178: Transfers said 0.0 MB/s in the first minute), how fast the converter makes it.
            current['rate']=up or sink.made_rate()
        q.state['current']=current
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
    def finished(new):
        # Build 181: the prepared movie is a new Drive file (same folder and name, .mp4); the original is in the bin.
        main=dict(outputs.get('0') or {},moved=True)
        job['cloud_output']={'0':main};job['status']='done';job['completed']=q.clock();job['prepared_id']=new['id']
        q.commit();clear_temps()
        try:
            import debrid_drive;debrid_drive.renamed(q.profile,item['id'],new['id'])   # "download and watch" plays the new one
        except Exception as error:q.log('preparation: watch list not updated: %s'%error)
        driveupload.invalidate_library(str(prep.location(q.profile).parent));prep.request_check(q.profile)
        q.state.pop('current',None);q.commit()
        q.notify('info','Ready for Kodi and AirPlay',drivelibrary.display_title(item['name']));return True
    try:
        q.log('preparation: %s — opening Drive file'%drivelibrary.display_title(item['name']))
        progress('Reading from Google Drive',None)
        if job.get('promoted'):
            # Stopped after the prepared file took the original's place: send the original to the bin and finish.
            drive_prepare.bin(q.drive,item['id'])
            return finished(prep.metadata(q.drive,job['promoted']))
        current = prep.metadata(q.drive,item['id'])
        if prep.ready(current) and not prep.repack_due(current):
            job['status']='done';clear_temps();q.commit();return True
        main = outputs.get('0')
        completed = bool(main and int(current['size']) == int(main['size']) and current['md5Checksum'].lower() == main['md5Checksum'].lower())
        if not completed:
            if prep.identity(current) != prep.identity(item):raise RuntimeError('Drive source changed; preparation will rescan')
            source = q.stream.url(item['id'])
            if not main:
                # r30: carry on from where the last run got to (Kodi closed, the app updated), if Drive still has it.
                resumes=bool(getattr(q.native,'resumes',False))
                checkpoint=resume_store.load(q.profile,slot,prep.identity(item)) if resumes else None
                if checkpoint:
                    held=resume_store.confirmed(q.drive,checkpoint) if job.get('probe') else None
                    checkpoint=resume_store.fit(checkpoint,held,bool((job.get('probe') or {}).get('copy_video')))
                if not checkpoint:resume_store.clear(q.profile,slot)
                # Remove completed sidecars from an interrupted generation before retrying.
                if not clear_temps():raise RuntimeError('Preparation temporary files could not be cleaned up')
                outputs=job.setdefault('cloud_output',{})
                if checkpoint:
                    before=job['probe']
                    q.log('preparation: %s — carrying on from byte %d (Drive kept it; %d bytes past the mark already on Drive)'%(
                        drivelibrary.display_title(item['name']),checkpoint['offset']+len(checkpoint['tail'])-checkpoint.get('skip',0),checkpoint.get('skip',0)))
                else:
                    progress('Inspecting video and track index',None)
                    before=q.native.probe(source);job['probe']=before;q.commit()
                q.log('preparation: %s — codec %s, %sx%s, %s-bit, HDR=%s, copy=%s, audio work=%s'%(drivelibrary.display_title(item['name']),before.get('codec'),before.get('width'),before.get('height'),before.get('bit_depth'),before.get('hdr'),before.get('copy_video'),before.get('audio_work_bytes')))
                progress('Opening conversion tracks',None)
                parent=q.drive.folder([driveupload.TOP,'.Preparation'])
                def on_file(track,result):outputs[track]=result;q.commit()
                # A video playing pauses the conversion where it is (owner, build 175): the upload session waits too.
                paused=getattr(q,'paused',None) or (lambda:False)
                identity=prep.identity(item)
                sink=drive_prepare.Sink(q.drive,parent,slot,lambda:keep_going() or paused(),on_file,hold=paused,
                    spool=str(resume_store.folder(q.profile)) if resumes else None,checkpoint=checkpoint,
                    keep_pieces=resumes and not (job.get('probe') or {}).get('copy_video'),
                    on_checkpoint=lambda cp:resume_store.save(q.profile,slot,identity,cp))
                attempt['sink']=sink
                def waiting():
                    # Build 193: only the owner's Pause holds a conversion now (a video or AirPlay slows it instead),
                    # so the words say so; the reason is stored, never guessed (build-192 log: "Paused while a video
                    # plays" with nothing playing).
                    if q.runtime:q.runtime.phase('Paused by you',False,item['name'])
                    current=q.state.get('current') or {}
                    if q.clock()-float(current.get('updated') or 0)>=2:
                        current.update(stage='Step 3 of 3 · Paused by you',running=True,paused=True,updated=q.clock(),rate=0,detail='')
                        q.state['current']=current;q.commit()
                # Build 192: a resumed movie shows where it got to (the mark's place in the film), not 0%, while it lines up.
                duration=float((job.get('probe') or {}).get('duration') or 0)
                converted=[min(80,80*resume_store.mark_seconds(checkpoint['mark'])/duration) if checkpoint and duration else 0]
                def converted_progress(stage,n,t):
                    if stage==4:   # r32: lining up after Kodi was closed
                        progress('Finding where it left off',converted[0]);return
                    doing='Making it start faster' if job.get('repack') else 'Converting'
                    if attempt['convert_start'] is None:attempt['convert_start']=q.clock()
                    if stage in (0,2) and t:attempt['fraction']=max(attempt['fraction'],min(1.0,float(n)/t))
                    value=80 if stage==3 else (min(80,80*n/t) if t else converted[0])
                    converted[0]=max(converted[0],value)
                    progress(doing,converted[0])   # build 192 (owner): shorter, more fits on the page
                try:
                    try:
                        q.native.convert_to(source,sink,keep_going,
                            converted_progress,paused,waiting,resume=checkpoint['mark'] if checkpoint else None)
                    except prep.ResumeFailed as error:
                        # The saved place no longer fits: start this movie again at once.
                        q.log('preparation: cannot carry on (%s); starting again'%error)
                        sink.close();sink.tracks.clear();resume_store.clear(q.profile,slot)
                        raise driveupload.Stop('Starting the conversion again')
                    sink.finish()
                    resume_store.clear(q.profile,slot)
                except Exception:
                    # Drop RAM buffers immediately. Complete staging objects are recorded for cleanup next time.
                    sink.close();sink.tracks.clear();raise
                main=outputs['0']
            temp_id=main['id'];target=q.stream.url(temp_id)
            progress('Verifying the Drive file and seek index',82)
            try:
                fresh=prep.metadata(q.drive,temp_id)
                if (fresh['md5Checksum'].lower(),int(fresh['size'])) != (main['md5Checksum'].lower(),int(main['size'])):
                    raise RuntimeError('Prepared Drive file checksum differs; original retained')
                # Build 188: reading a 50 GB movie's index back over a slow line can take longer than one probe's
                # 120 s; the Drive blocks it read stay cached, so another try gets further.
                for tries in range(3):
                    try:after=q.native.probe(target);break
                    except RuntimeError as error:
                        if 'timed out' not in str(error) or tries==2:raise
                        q.log('preparation: checking the Drive file timed out (try %d of 3); trying again'%(tries+1))
                before=job.get('probe') or q.native.probe(source)
                if not after.get('ready') or (before['width'],before['height'],before['hdr']) != (after['width'],after['height'],after['hdr']):
                    raise RuntimeError('Prepared video did not preserve resolution/HDR; original retained')
                q.native.verify(source,target)  # duration, all tracks, middle/end index seeks over HTTP
            except driveupload.Stop:raise
            except Exception as error:
                # Network interruptions can retry a valid completed object; invalid output must be regenerated.
                if isinstance(error,RuntimeError) and any(word in str(error).lower() for word in ('validation','preserve','checksum')):
                    clear_temps();resume_store.clear(q.profile,slot)
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
            if not (job.get('cloud_replace') or {}).get('url'):
                # Build 181 (owner: "upload once not twice"): the prepared file takes the original's place; no copy.
                if not parents:raise RuntimeError('Drive did not describe the video folder')
                progress('Putting it in place on Google Drive',95)
                new=drive_prepare.promote(q.drive,item,main,parents[0],q.drive.folder([driveupload.TOP,'.Preparation']))
                job['promoted']=new['id'];q.commit()
                drive_prepare.bin(q.drive,item['id'])
                return finished(new)
            # A replacement started by an older build: finish it the old way.
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
        if 'source changed' in text:job['status']='superseded';q.state['last_scan']=0;clear_temps();resume_store.clear(q.profile,slot)
        elif 'tracks MP4 cannot preserve' in text or 'without changing HDR' in text or 'needs RPU remapping' in text:job['blocked']=True
        elif job.get('repack') and any(word in text for word in REPACK_STOPS):
            # Build 193 (build-192 log 13:55:08: Fall 2's faster start failed at 22 % on "MP4 packet: Invalid argument" after
            # 26 min): the converter refuses the same piece of an older file every time, so each retry would start from
            # 0 % and fail there again, for ever. The movie is Ready and plays; it stays as it is.
            job['blocked']=True;job['repack_failed']=True;clear_temps();resume_store.clear(q.profile,slot)
            q.notify('info','Kept as it is',drivelibrary.display_title(item['name'])+" still plays in Kodi and on AirPlay; it couldn't be made to start faster.")
            import transfer_history;transfer_history.failed(q.profile,'conv',item['name'],"couldn't be made to start faster; it still plays",q.clock())
            job['error']=text;return False
        if job.get('error')!=text:
            q.notify('problem','Video preparation paused',drivelibrary.display_title(item['name'])+': '+text[:200])
            # Transfers › History: once per video and reason, like the notification (not a source changed meanwhile).
            if job.get('status')!='superseded':
                import transfer_history;transfer_history.failed(q.profile,'conv',item['name'],prep.plain(text),q.clock())
        job['error']=text;return False
    finally:
        q.stream.forget(item['id'])
        if temp_id:q.stream.forget(temp_id)
        # Build 193 (build-192 log: a stopped Inception kept "Paused while a video plays"): a stopped job says it stopped.
        if q.state.get('current'):q.state['current'].update(running=False,paused=False,updated=q.clock(),rate=0,detail='',
                                                            stage='Stopped' if job.get('status')!='failed' else 'Will try again')
        q.commit()
