"""The storage-free preparation queue: Drive → RAM converter → Drive staging → original ID."""
import json
import time
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


class VerifyFailed(RuntimeError):
    """The finished prepared file did not pass its final check. Making it again would end the same way (owner log, build
    368: 30 failed attempts for Naruto Shippuuden, each a full read and write on Drive, then thrown away), so the video
    stops after one failure. Network trouble is never this: it keeps its own waits."""


def native_verify_problem(q, error):
    """The error to raise for a failed native.verify: VerifyFailed for a real mismatch; the original error (network
    trouble: waits and carries on) when the network or the Drive stream had a read problem."""
    import debrid_drive
    try:read_trouble=bool((q.stream.stats() if q.stream and hasattr(q.stream,'stats') else {}).get('read_error'))
    except Exception:read_trouble=False
    if debrid_drive.network_error(error) or read_trouble:return error
    return VerifyFailed(str(error) or 'Prepared Drive file validation failed')


def on_cellular(q, every=5.0):
    """prepare_downloads.cellular_now, looked up at most every few seconds (the converter asks keep_going many times a
    second). A queue with its own link() (tests) is asked every time."""
    if getattr(q, 'link', None) is not None:return prep.cellular_now(q)
    seen = q.__dict__.get('_cellular_seen')
    if not seen or time.monotonic() - seen[0] >= every:
        seen = q.__dict__['_cellular_seen'] = (time.monotonic(), prep.cellular_now(q))
    return seen[1]


def asked_now(job, clock):
    """The owner pressed Start now for this video (prepare_downloads.apply_to sets priority to now + 10**9)."""
    return float(job.get('priority', 0) or 0) > clock() + 5 * 10**8


def known_repack(job):
    """F2: a job known to only re-package (picture copied): it may run in an extra lane beside the main one."""
    return bool(job.get('repack') or (job.get('probe') or {}).get('copy_video')) and not job.get('audit')


def verify_problem(before, after):
    """Why the prepared file's probe is not acceptable (which check failed), or '' when it is."""
    if not after.get('ready'):
        return 'The prepared file is not marked ready (its tracks or index are not what AirPlay needs); original retained'
    was = (before.get('width'), before.get('height')); now = (after.get('width'), after.get('height'))
    if was != now:
        return 'The prepared picture is %sx%s, the original is %sx%s; original retained' % (now + was)
    if before.get('hdr') != after.get('hdr'):
        return 'HDR changed: the original is %s, the prepared video is %s; original retained' % (
            'HDR' if before.get('hdr') else 'not HDR', 'HDR' if after.get('hdr') else 'not HDR')
    return ''


def process_one(q, keep_going, lane=None):
    """One preparation job. lane None: the main lane (any job; owns the heartbeat and the 'current' card). lane 'N'
    (F2, PR #24): an extra lane that takes only known re-packages, claims its job so no other lane runs it, and shows its
    card in state['lanes'][N]."""
    runtime = q.runtime if lane is None else None
    running = q.__dict__.setdefault('running_slots', set())
    def set_card(card):
        if lane is None:q.state['current']=card
        else:q.state.setdefault('lanes',{})[lane]=card
    def drop_card():
        if lane is None:q.state.pop('current',None)
        else:q.state.setdefault('lanes',{}).pop(lane,None)
    def card():
        return q.state.get('current') if lane is None else (q.state.get('lanes') or {}).get(lane)
    # Cleanup is independent of jobs: a library rescan can remove completed or superseded jobs.
    # Journal before deleting, and retry 404 safely if a process exited after Drive acknowledged deletion.
    pending=q.state.setdefault('staging_cleanup',[])
    for item_id in list(pending):
        try:drive_prepare.discard(q.drive,item_id)
        except Exception:continue
        pending.remove(item_id);q.commit()
    if pending and lane is None:return False
    for j in q.state['jobs'].values():
        if j.pop('space',None):j['retry_after']=0
    held_changed = False
    with q.lock:   # build 191: a library check may change the list beside a conversion
        candidates = [(slot,j) for slot,j in q.state['jobs'].items() if j.get('status') not in ('done','superseded')
                      and not j.get('blocked') and not j.get('kept') and j.get('retry_after',0) <= q.clock()
                      and slot not in running and (lane is None or known_repack(j))]
        # Owner log (build 368): the phone sat on mobile data 13:31-13:40 while preparation read and wrote whole movies. On
        # mobile data nothing new starts, unless the owner asked for that video now; the Library status says why.
        if candidates and on_cellular(q):
            kept = [pair for pair in candidates if asked_now(pair[1], q.clock)]
            if lane is None:
                if not kept and not q.state.get('wifi_hold'):
                    q.log('preparation: waiting for Wi-Fi (on mobile data)')
                if bool(q.state.get('wifi_hold')) != (not kept):
                    q.state['wifi_hold'] = not kept
                    held_changed = True
            candidates = kept
        elif lane is None and q.state.pop('wifi_hold', None):
            held_changed = True
        candidates.sort(key=lambda pair:prep.order_key(*pair))   # build 182: quick (repack only) before re-encodes
        if candidates:running.add(candidates[0][0])
    if held_changed:q.commit()
    if not candidates:return False
    if lane is None:
        # Old builds' checkpoints are no longer used: their full-sized local media can go.
        for folder in q.work.iterdir():
            if folder.is_dir():shutil.rmtree(folder)
    slot,job = candidates[0];item = job['source'];last = [0]
    plain_keep_going = keep_going
    def keep_going():
        # A job running when the phone moves to mobile data stops cleanly (Stop, like the owner's Pause) and carries on
        # from its mark on Wi-Fi; the owner's Start now overrides.
        return plain_keep_going() and (asked_now(job, q.clock) or not on_cellular(q))
    try:
        return _run(q, keep_going, lane, runtime, set_card, drop_card, card, candidates, slot, job, item, last)
    finally:
        with q.lock:running.discard(slot)
        if hasattr(q.stream,'unwide'):q.stream.unwide(item['id'])


def _run(q, keep_going, lane, runtime, set_card, drop_card, card, candidates, slot, job, item, last):
    job.pop('space',None)
    # Build 177: time left and pace come from this attempt only. The old job['eta_mark'] outlived stopped attempts,
    # so a restart measured from hours earlier ("about 46 h 28 min", owner screenshot).
    job.pop('eta_mark',None);job['started_at']=q.clock()   # Library status › a ready movie: "took 41 min"
    attempt={'mark':None,'sink':None,'fraction':0.0,'convert_start':None}
    original_stats=runtime.stats if runtime else None
    def progress(stage,pct):
        if runtime:runtime.phase(stage,pct is not None,item['name'])
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
        current=dict(title=item['name'],watch_next=prep.watch_next(job),stage='Step 3 of 3 · '+stage,kind='repack' if job.get('repack') else 'conv',progress=max(0,min(100,pct or 0)),indeterminate=pct is None,
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
        set_card(current)
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
    if lane is None:q.native.keep_going=keep_going
    outputs = job.setdefault('cloud_output',{})
    temp_id = None
    def finished(new):
        # Build 181: the prepared movie is a new Drive file (same folder and name, .mp4); the original is in the bin.
        main=dict(outputs.get('0') or {},moved=True)
        job['cloud_output']={'0':main};job['status']='done';job['completed']=q.clock();job['prepared_id']=new['id']
        job.pop('stream_only',None);job.pop('audit',None)
        q.commit();clear_temps()
        try:
            import debrid_drive;debrid_drive.renamed(q.profile,item['id'],new['id'])   # "download and watch" plays the new one
        except Exception as error:q.log('preparation: watch list not updated: %s'%error)
        driveupload.invalidate_library(str(prep.location(q.profile).parent));prep.request_check(q.profile)
        drop_card();q.commit()
        q.notify('info','Ready for Kodi and AirPlay',drivelibrary.display_title(item['name']));return True
    try:
        q.log('preparation: %s — opening Drive file'%drivelibrary.display_title(item['name']))
        progress('Checking compatibility',None)
        if job.get('promoted'):
            # Stopped after the prepared file took the original's place: send the original to the bin and finish.
            drive_prepare.bin(q.drive,item['id'])
            return finished(prep.metadata(q.drive,job['promoted']))
        current = prep.metadata(q.drive,item['id'])
        if prep.ready(current) and not job.get('repack') and not job.get('audit'):
            job['status']='done';clear_temps();q.commit();return True
        if q.skip_compatible(slot,job,current,job.get('probe')):
            drop_card();q.commit();return True
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
                    before=q.inspect_source(item,keep_going);job['probe']=before
                    # Keep a contradictory old prepared marker from bypassing this repair after a pause/failure.
                    if prep.streamable_video(before):job.pop('audit',None)
                    else:job['audit']=True
                    q.commit()
                # ISSUE-231 (owner: "I selected 1080p ... 480p is ass"): an automatic pick that turns out lower than the
                # quality chosen is not kept: its copy ends 'failed' (Download problems, and the next search leaves that
                # version out), the file goes to Drive's Trash (30 days), and it is not prepared.
                try:
                    import debrid_drive
                    _,wanted=debrid_drive.wanted_quality(debrid_drive.load(q.profile),item['id'])
                except Exception:
                    wanted=''
                if wanted and prep.below_wanted(before,wanted):
                    why='Not the quality you picked: %sx%s, you chose %s'%(before.get('width'),before.get('height'),wanted)
                    debrid_drive.refuse_low_quality(q.profile,item['id'],why)
                    try:drive_prepare.bin(q.drive,item['id'])
                    except Exception as error:q.log('preparation: %s could not go to the Trash: %s'%(drivelibrary.display_title(item['name']),error))
                    job.update(status='superseded',error=why);q.state['last_scan']=0
                    driveupload.invalidate_library(str(prep.location(q.profile).parent))
                    q.log('preparation: %s — %s; moved to Google Drive\'s Trash, another version will be looked for'%(drivelibrary.display_title(item['name']),why))
                    q.notify('problem','Not the quality you picked','%s is %sx%s, not %s. It went to Google Drive\'s Trash; another version will be looked for.'%(
                        drivelibrary.display_title(item['name']),before.get('width'),before.get('height'),wanted))
                    drop_card();q.commit();return True
                if q.skip_compatible(slot,job,item,before):
                    drop_card();q.commit();return True
                q.log('preparation: %s — codec %s, %sx%s, %s-bit, HDR=%s, copy=%s, audio work=%s'%(drivelibrary.display_title(item['name']),before.get('codec'),before.get('width'),before.get('height'),before.get('bit_depth'),before.get('hdr'),before.get('copy_video'),before.get('audio_work_bytes')))
                # F3 (ISSUE-211): a re-package (picture copied) reads Drive with more blocks in flight; a real conversion
                # keeps the usual few. This is the path the phone runs (native outputs), not prepare_downloads' local one.
                if before.get('copy_video') and hasattr(q.stream,'widen'):q.stream.widen(item['id'])
                progress('Opening conversion tracks',None)
                parent=q.drive.folder([driveupload.TOP,'.Preparation'])
                def on_file(track,result):outputs[track]=result;q.commit()
                # Owner (2026-11-13): preparation goes on while a video plays (slowed); it waits only while Kodi buffers.
                paused=getattr(q,'paused',None) or (lambda:False)
                identity=prep.identity(item)
                sink=drive_prepare.Sink(q.drive,parent,slot,lambda:keep_going() or paused(),on_file,hold=lambda:paused() or __import__('slowdown').preparation_holding(),
                    spool=str(resume_store.folder(q.profile)) if resumes else None,checkpoint=checkpoint,
                    keep_pieces=resumes and not (job.get('probe') or {}).get('copy_video'),
                    on_checkpoint=lambda cp:resume_store.save(q.profile,slot,identity,cp))
                # ISSUE-232 (owner log 47e2276a: "Making it start faster · 78.7%" for 6 minutes while the made movie went up
                # at ~1.3 MB/s): once every unit is made, each confirmed piece updates the card with the upload's share.
                ticks={'at':0.0}
                def upload_tick():
                    if not getattr(sink,'made_all',False) or q.clock()-ticks['at']<2:return
                    ticks['at']=q.clock();c=card()
                    if not c or not sink.made:return
                    done=min(1.0,float(sink.sent)/sink.made);left=max(0,sink.made-sink.sent)/1048576.0
                    c.update(stage='Step 3 of 3 · Uploading to Google Drive · %d%%'%int(100*done),updated=q.clock(),
                             detail='%s left to upload'%('%.1f GB'%(left/1024) if left>=1024 else '%.0f MB'%left))
                    q.commit()
                sink.on_confirmed=upload_tick
                attempt['sink']=sink
                if runtime:
                    runtime.stats=lambda:dict(original_stats() or {},**sink.stats())
                def waiting():
                    # Build 193: only the owner's Pause holds a conversion now (a video or AirPlay slows it instead),
                    # so the words say so; the reason is stored, never guessed (build-192 log: "Paused while a video
                    # plays" with nothing playing).
                    if runtime:runtime.phase('Paused by you',False,item['name'])
                    current=card() or {}
                    if q.clock()-float(current.get('updated') or 0)>=2:
                        current.update(stage='Step 3 of 3 · Paused by you',running=True,paused=True,updated=q.clock(),rate=0,detail='')
                        set_card(current);q.commit()
                # Build 192: a resumed movie shows where it got to (the mark's place in the film), not 0%, while it lines up.
                duration=float((job.get('probe') or {}).get('duration') or 0)
                converted=[min(80,80*resume_store.mark_seconds(checkpoint['mark'])/duration) if checkpoint and duration else 0]
                def converted_progress(stage,n,t):
                    if stage==4:   # r32: lining up after Kodi was closed
                        progress('Finding where it left off',converted[0]);return
                    doing='Making it start faster' if job.get('repack') else 'Converting'
                    if attempt['convert_start'] is None:attempt['convert_start']=q.clock()
                    if stage in (0,2) and t:attempt['fraction']=max(attempt['fraction'],min(1.0,float(n)/t))
                    if stage==3 or (stage in (0,2) and t and n>=t):sink.made_all=True   # ISSUE-202: the rest is the upload
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
                    raise VerifyFailed('Prepared Drive file checksum differs; original retained')
                # Build 188: reading a 50 GB movie's index back over a slow line can take longer than one probe's
                # 120 s; the Drive blocks it read stay cached, so another try gets further.
                for tries in range(3):
                    try:after=q.native.probe(target);break
                    except RuntimeError as error:
                        if 'timed out' not in str(error) or tries==2:raise
                        q.log('preparation: checking the Drive file timed out (try %d of 3); trying again'%(tries+1))
                before=job.get('probe') or q.native.probe(source)
                reason = verify_problem(before, after)
                if reason:raise VerifyFailed(reason)
                try:q.native.verify(source,target)  # duration, all tracks, middle/end index seeks over HTTP
                except RuntimeError as error:
                    # ISSUE-238 (handoff, ISSUE-230 open item): the converter's own check failing is a bad file, and making
                    # it again ends the same way; it stops after this one. Network trouble during the check is not.
                    raise native_verify_problem(q,error)
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
        job['cloud_output']={'0':main};job['status']='done';job['completed']=q.clock();job.pop('audit',None);job.pop('stream_only',None)
        pending=q.state.setdefault('staging_cleanup',[])
        if main['id'] not in pending:pending.append(main['id'])
        q.commit();clear_temps()
        driveupload.invalidate_library(str(prep.location(q.profile).parent));prep.request_check(q.profile)
        drop_card();q.commit()
        q.notify('info','Ready for Kodi and AirPlay',drivelibrary.display_title(item['name']));return True
    except driveupload.Stop:
        if job.get('status')!='committing':job['status']='paused'
        job['retry_after']=0;return False
    except prep.SourceGone as error:
        # ISSUE-233 (owner log 1ae21097: 32 "Drive video is unavailable or incomplete" failures, retried every minute, after
        # Naruto was deleted mid-conversion): a deleted video leaves the queue quietly.
        job.update(status='superseded',forgotten=q.clock());job.pop('error',None)
        clear_temps();resume_store.clear(q.profile,slot);drop_card();q.commit()
        q.log('preparation: %s — %s; left out of the queue'%(drivelibrary.display_title(item['name']),error))
        return True
    except Exception as error:
        import debrid_drive
        # ISSUE-232 (owner log 47e2276a, build 374: E10's final read-back failed while Drive dropped the connection 7 times,
        # and read "Prepared Drive file validation failed", its 6th try): a read-back that failed while the Drive stream
        # had a read problem is network trouble, not a bad file.
        read_trouble=False
        try:read_trouble='validation failed' in str(error).lower() and bool((q.stream.stats() if q.stream else {}).get('read_error'))
        except Exception:pass
        if not isinstance(error,VerifyFailed) and (debrid_drive.network_error(error) or read_trouble) and 'source changed' not in str(error).lower():
            # ISSUE-198 (owner log b3c5d6eb, build 350: Drive reads stopped for 5 minutes, then "Source read:
            # Input/output error"): network trouble is not the video's fault. It waits (15 s up to 5 min), carries on
            # from its last mark (resume_store) and never counts toward the long back-off.
            job['net_attempts']=job.get('net_attempts',0)+1
            job['retry_after']=q.clock()+debrid_drive.net_wait(job['net_attempts'])
            if job.get('status')!='committing':job['status']='waiting'
            q.log('preparation: %s — network trouble (%s); carrying on in %d s'%(drivelibrary.display_title(item['name']),
                  str(error)[:100],debrid_drive.net_wait(job['net_attempts'])))
            drop_card();q.commit()
            return False
        verify_failed=isinstance(error,VerifyFailed)
        job['attempts']=job.get('attempts',0)+1
        job['retry_after']=q.clock()+min(3600,60*2**min(job['attempts']-1,6))
        if job.get('status')!='committing':job['status']='failed'
        diagnostics.exception(q.log,'preparation',error,phase=(card() or {}).get('stage','opening'),attempt=job['attempts'],video=job.get('probe') or {})
        text=preparation_runtime.problem(error)
        if 'could not be inspected' in text and q.stream and hasattr(q.stream,'stats'):
            underlying=q.stream.stats().get('read_error')
            if underlying:text+=': '+underlying
        q.log('preparation: failed for %s: %s; phase=%s; video=%s'%(drivelibrary.display_title(item['name']),text,(card() or {}).get('stage','opening'),json.dumps(job.get('probe') or {},sort_keys=True)))
        if 'source changed' in text:job['status']='superseded';q.state['last_scan']=0;clear_temps();resume_store.clear(q.profile,slot)
        elif 'tracks MP4 cannot preserve' in text or 'without changing HDR' in text or 'needs RPU remapping' in text:
            # Owner screenshot (2026-11-13, Naruto Shippuuden S1 E16): this read "Video preparation paused" with the
            # converter's words, but nothing is paused: the file is kept as it is (blocked, not tried again). Say so plainly,
            # once, and name what stops it.
            job['blocked']=True
            why=('it has DVD picture subtitles or a second video track an MP4 can\'t keep' if 'tracks MP4' in text else
                 'its Dolby Vision or HDR picture can\'t be copied as it is')
            if not job.get('kept_told'):   # once per video: retry_image_subtitles gives one more try and clears the error
                job['kept_told']=True
                q.notify('info','Kept as it is',drivelibrary.display_title(item['name'])+' still plays in Kodi as it is; '+why+
                         ', so it isn\'t made ready for AirPlay.')
                import transfer_history;transfer_history.failed(q.profile,'conv',item['name'],'kept as it is: '+why,q.clock())
            job['error']=text;return False
        elif verify_failed:
            # Build 368 log: the same final check failed 30 times for Naruto Shippuuden episodes. One failure stops the video;
            # the original is kept. A re-package that already plays reads as Ready (repack_failed), anything else stays a
            # preparation problem (Download problems lists it). Repair / Start now (prepare_downloads.forgive) clear it.
            job['blocked']=True;job['verify_failed']=True;clear_temps();resume_store.clear(q.profile,slot)
            if job.get('repack'):job['repack_failed']=True
            if not job.get('verify_told'):
                job['verify_told']=True
                plain=drivelibrary.display_title(item['name'])
                q.notify('info','Kept as it is',plain+(" still plays in Kodi and on AirPlay; it couldn't be made to start faster. " if job.get('repack') else
                         " still plays in Kodi as it is; the prepared copy failed its final check, so it wasn't used. ")+text[:160])
                import transfer_history;transfer_history.failed(q.profile,'conv',item['name'],'kept as it is: '+text[:160],q.clock())
            job['error']=text;return False
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
        if runtime and original_stats is not None:runtime.stats=original_stats
        q.stream.forget(item['id'])
        if temp_id:q.stream.forget(temp_id)
        # Build 193 (build-192 log: a stopped Inception kept "Paused while a video plays"): a stopped job says it stopped.
        if card():card().update(running=False,paused=False,updated=q.clock(),rate=0,detail='',
                                                            stage='Stopped' if job.get('status')!='failed' else 'Will try again')
        q.commit()
