# TV resume handoff — step1 reproduction, step2 repair

## Result

Native workflow44664113987, source5ccd9585f84b5d12eb4f2bde95d0bfdbf2fa4089:
19 observation checks passed. A second execution of the desired behavior contract
failed exactly four assertions: cold converted target and unnecessary converted
segment0 in each of two fixtures. The wrapper requires those exact four failures
and no others; this is a successful reproduction, not a successful fix or full
regression pass. All33 AirPlay Python checks, shell syntax and project check pass.

## Exercised path

`test_receiver_resume_handoff` in the native host test binary runs the production
remux server, cache, planner and converter against generated HTTP fixtures:

1. Open prepared `coalesced.mp4` or `long-gop.mp4` in segmented-copy mode with
   an explicitly selected external text subtitle, requiring TV subtitle burning.
2. Disable speculative prefetch to isolate what `kr_remux_prime_for(20.0)` actually
   prepares. Observe copied target cached and converted target absent.
3. Fetch the phone master through its normal client identity; it selects `/video/`.
4. Enable prefetch and fetch the MFi receiver master; it selects `/cvideo/`.
5. Observe converted segment0 enter the cache despite the20s resume point.
6. Fetch the real converted target over HTTP and verify nonempty successful media.

The long-GOP case additionally asserts that copy/conversion segment indices at20s
are different. It exercises the window-grid mismatch without requiring private
4K media or expensive hardware encoding.

The read-only plan/cache observers use KR_REMUX_TEST; the host runner defines it,
framework builds do not. They observe actual state and do not change scheduling.
The host uses the existing MPEG-4 test encoder, not iPhone VideoToolbox. A synthetic
MFi User-Agent exercises normal routing; it does not authenticate as another app
or defeat an authorization check.

## Step2 — the repair (source change, native result pending)

Chosen strategy: **receiver-specific readiness at the moment the receiver names itself.** The receiver's identity is known only from
its master-playlist request's User-Agent (nothing earlier in the Python/native handoff carries it), after the phone's copy was
primed. So the copy prime stays as it is (Apple players and the phone keep the copy and nothing is converted for them), and the
master handler for a third-party receiver now calls `receiver_prepare()`:

- it names the converted init and the converted unit that holds the resume position, mapped through the **converted plan's own
  grid** (`resume_segment(R_VCOMPAT)`), instead of queueing converted segment 0;
- with a converted plan and a selected audio track it does the same for converted audio (`R_CAUDIO`, the same plan);
- a repeated master request queues nothing new (queued or cached units are skipped), so retries are safe;
- after an init request the "units after it" are those after the resume segment of that rendition, not after 0;
- a start from the beginning still gets segment 0 (resume position 0 maps to segment 0).

The resume position is stored by `kr_remux_prime_for` (`resume_ms`) and reset with each session. A segment number is never carried from one
rendition to another: each is mapped through `rend_plan(rend)`.

Tradeoffs: no global forced conversion and no extra delay or longer timeout. The converted window is still produced after the receiver's
master, not before, so the receiver may wait for conversion exactly as before; what changes is that the work is for the window it will
ask for, started at the master request, and no longer for a place nobody plays. Preparing before the receiver names itself would need
the sender to pass the receiver model down, which is not available in this path; it is a possible later change.

## Regression gate

`test_receiver_resume_handoff` (also run in the full native suite) is now a normal passing gate, no longer an expected-red wrapper.
For `coalesced.mp4` and `long-gop.mp4` (different copy/conversion grids) it checks: copy video/audio cached by priming; converted
cold after priming and after the phone's master (no unnecessary conversion); after the MFi master the converted resume window (and
converted audio when the plan has one) becomes cached; converted segment 0 is never made; repeated masters answer; the init does not
start the units after 0; the served init plus resume window decode real frames; the log names the resume segment. A zero start
prepares segment 0. Dispatch `airplay-remux.yml` with `receiver_handoff_only=true` (runs `run_host_tests.sh --receiver-handoff`);
it publishes no framework and builds no IPA.

## Evidence limits

Native HTTP host fixture with the existing MPEG-4 test encoder, not iPhone VideoToolbox, AVPlayer or a real TV. It shows the
preparation and scheduling are for the right window; it does not reproduce the owner's timeout, topology, codecs or quality, and
does not prove playback. Native results (run 44667223229: 40 checks, 0 failed on 5a60990) are recorded in ISSUE-393, with the later edge-case tests (`test_receiver_handoff_edges`: subtitles off, backward seek, rewind to zero, stop during preparation).
