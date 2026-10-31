# Elementum on the iPhone — source investigation and proposed build probe

Owner selects Elementum as primary and wants the engine on the phone. A remote engine/hosting/Deck server is **not approved**. Nothing has been provisioned. Native engine creation is a new port/integration requirement, not satisfied by the working diagnostic Kodi app or by a client ZIP.

## Evidence

The current plugin release is 0.1.114. Its [release assets](https://github.com/elgatito/plugin.video.elementum/releases/tag/v0.1.114) include Android, Linux, Windows, macOS Intel, and a client-only ZIP; no iOS engine is listed. Current upstream README also distinguishes macOS Apple Silicon from iOS and suggests client/server mode for unsupported systems. Native iOS support is **not available from those assets**; this does not prove a port impossible.

Pinned compatible release sources: plugin `8ea802e705c28fef692aef7908e8a7cfce9a55f0`; engine `cdab7e2ed69122e048be158e2ebea70dbda789ee`; that engine's go.mod selects libtorrent-go `d8763f5e17831acd4ec0a2841074113ae571157f`. Newer master revisions were reviewed separately and are not silently substituted. The stable engine declares Go 1.21/toolchain 1.21.1; current master declares 1.27.2, so mixing their recipes would be incorrect.

The [real shared-engine source](https://github.com/elgatito/elementum/blob/cdab7e2ed69122e048be158e2ebea70dbda789ee/build_shared.go) exposes C-callable startWithArgs/startWithLogAndArgs under the shared build tag. This offers a possible integration seam. It is not proof of an iOS library build or safe host lifecycle. The pinned [libtorrent Go binding](https://github.com/ElementumOrg/libtorrent-go/blob/d8763f5e17831acd4ec0a2841074113ae571157f/libtorrent_cgo.go) uses pkg-config for static libtorrent-rasterbar/OpenSSL and Darwin linker settings, including an old C++ runtime flag that may need an iOS-specific patch. Mac binaries/libraries must not be relabeled as iOS ARM64.

The [Go build-mode documentation](https://pkg.go.dev/cmd/go#hdr-Build_modes) describes C archive/export behavior. Proposed route: compile the **real** engine and its C++ dependencies for iPhoneOS, then prove a signed in-process bridge/library or source-level Kodi integration. Do not spawn a Linux/macOS daemon, download an executable at runtime, add jailbreak privileges, or call a Python substitute a native engine. A C archive alone is not a working Kodi engine; the actual linking strategy remains to be proven.

## Required work and current blockers

1. Acquire an authorized Mac/Xcode/iPhoneOS SDK build executor and compatible Go/C++ tools. This Linux session has none of go, cc, clang, cmake, Docker, xcodebuild or xcrun. No local native build was attempted or claimed successful.
2. Compile matching ARM64 **iOS** libtorrent, OpenSSL and required C++/Boost dependencies with recorded versions/licenses/checksums. Existing Darwin target recipes are not iOS recipes. Prevent accidental linking to macOS Homebrew libraries.
3. Build the real pinned engine as a candidate C archive, diagnose unsupported APIs/build tags/linker/runtime problems, then design/review its actual in-process Kodi bridge. Preserve upstream failures and add focused tests; no placeholder engine.
4. Establish start/stop ownership, paths inside the target sandbox, loopback RPC/provider callbacks, port conflicts, cancellation and safe shutdown. A functioning screen or HTTP stub cannot establish torrent-engine functionality.
5. Bundle every native component into a new unsigned IPA before signing; audit all architectures/load commands/dependencies/entitlements. Existing diagnostic IPA remains unchanged and has **no Elementum engine**.
6. Owner signs/tests the rebuilt app on iPhone 16 Pro/iOS 27.0.1 with authorized synthetic/owned fixtures: real transfer, buffering, seeking, subtitles, episode selection, cancellation, storage and foreground/lifecycle behavior. No broad background/always-on promise follows from the phone being powered on. No personal media upload or live provider authentication is performed here.

## Owner-approved capped Mac probe — failed before compilation

`migration/elementum-ios/probe-build.sh` performs a real source-pinned C-archive compile attempt. It creates only isolated temporary build output, requests no owner signing keys or accounts, and deliberately isolates pkg-config from host macOS libraries. With missing iOS native dependencies it must fail and preserve that blocker, not report an engine. Shell syntax and the missing-tool guard are host-testable; no iOS compiler/linker validation has happened.

Proposed executor: one GitHub Actions `macos-14` job, timeout **8 minutes**, permissions `contents: read`, SHA-pinned checkout, the existing Go toolchain on that runner, and `bash migration/elementum-ios/probe-build.sh`. Logs retained; no media, credentials, target execution or always-on service. GitHub macOS minutes can consume the owner's Actions allowance; this proposal is not an approval to enable billing or rent a Mac. Owner explicitly approved one eight-minute macOS Actions probe. The workflow accepts only a temporary exact PR-body marker on an edited event; pushes do not trigger it. Remove the marker immediately after the single trigger so subsequent PR edits/publications cannot rerun it. No second attempt is authorized automatically. A successful probe would still require actual iOS-native dependencies, integration, signing and device evidence before functionality is claimed.

## Remote alternative — researched, not selected

The released client ZIP SHA-256 is `ab095bd39fbeacb1dcfeb38e61bda5b047e897feb5dafbb6cf906d3102801f93` according to its GitHub release digest. Client configuration uses local_only_client, remote_host/remote_port (default HTTP port 65220) and a local callback port (65221); Kodi JSON-RPC connectivity is also involved. This is not an iOS certification. The pinned monitor source logs remote username/password in debug output; it would require redaction before any credential use. Its HTTP/basic-auth and callback/network lifecycle also require review. Do not expose it publicly or provision any remote service without a new owner decision. The owner's current preference remains phone-local engine creation.

Failed retrievals retained: guessed Kodi iOS binary-addon directories were inaccessible; official Omega index lists other OS variants but no iOS InputStream Adaptive entry. No universal incompatibility is inferred solely from failed URLs. Apple security-page retrieval returned HTTP 429, so no Apple quotation or unsupported platform-policy conclusion is attributed to that failed fetch.


## Recorded probe outcome and next build gate

The sole approved Mac attempt [40975489124](https://github.com/onlykappa/Kodi-Ios/actions/runs/40975489124/job/123802357346) failed at `BLOCKED: missing go` (exit 2), **before** source checkout, SDK discovery or engine compilation. The proposal incorrectly assumed Go was on the runner PATH. This is an executor failure, not evidence that Elementum cannot compile for iOS. The trigger marker is absent. The one-attempt allowance is consumed; no new Mac run is authorized by this result.

[Sanitized probe receipt](../reports/elementum-ios-probe.json) records the failure without publishing raw runner logs or private data. A corrected build needs an explicit Go installation plus genuine iPhoneOS libtorrent/OpenSSL/Boost dependencies; merely installing Go does not resolve the dependency blocker.

Owner update: native engine work is explicitly deferred while available Phase 4 import preparation is finished. This is not cancellation or compatibility acceptance. No remote replacement or additional Mac run is approved.
