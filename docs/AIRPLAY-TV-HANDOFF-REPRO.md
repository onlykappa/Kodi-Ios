# TV resume handoff reproduction — step1

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

## Execution and regression contract

Dispatch `airplay-remux.yml` on the draft branch with `receiver_handoff_only=true`.
This runs `run_host_tests.sh` with `--receiver-handoff-repro`, followed by
`--receiver-handoff-contract` against the same synthetic HTTP server. It publishes
no framework, builds no IPA and does not execute the full regression suite.
Import-review registers the native invocation and validates the host runner's
shell syntax alongside the existing AirPlay Python suite.

For step2, make the desired contract pass: when this TV handoff is declared ready,
the target converted window must already be available, and the resumed master
must not cause obsolete segment0 work. Change the expected-red wrapper into a
normal passing regression gate when the implementation is repaired. Keep source
and receiver-specific route selection; do not globally force unnecessary video
conversion merely to satisfy a test.

## Evidence limits

This is a native HTTP host fixture, not a desktop Kodi screenshot, AVPlayer test,
or real TV. It establishes the preparation mismatch and obsolete work independently
of receiver timing. It does not reproduce the owner's timeout, network topology,
exact codecs/quality, or prove either issue is sufficient to cause every failure.
The first build608 attempt's absent direct TV requests, slow High10 MKV preparation,
and earlier empty-audio failure remain separate investigation targets.
