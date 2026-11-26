# Packaging that survives upstream shutdown (roadmap step 12)

Code: `scripts/provider_addons.py` (`preserved_store`, `source(..., preserved)`, `run(..., preserved)`, CLI `--preserved DIR`, environment `KODI_IOS_PRESERVED_INPUTS`). Tests: `scripts/test_packaging_offline.py` (11 tests, host only; the staged-bundle test runs inside a network-less Linux namespace when `unshare` is available).

**Build time vs runtime.**
* *Build time* (a build machine or CI, may use the network): fetch the pinned inputs, verify every SHA-256, stage them into the IPA. A folder of preserved inputs (the owner's private release downloads, `migration/source-baseline`, the Elementum offline stage from step 3) is now looked up first, **by digest only**: a renamed, damaged or tampered file is not found, never trusted by name, and a wrong download is still rejected with a digest error. Only inputs missing from the folder are downloaded, so a build with every input preserved touches no upstream host (tested with the socket layer blocked and with a failing downloader).
* *Runtime* (the phone): the bundled last-known-working add-ons and Python modules ship inside the IPA (`build_customized_ipa` copies the whole bootstrap tree, so every module from steps 4–12 is in it) and need no update service. The in-app update check (`updates.py`) only lists GitHub releases and saves a newer IPA to the Files app's "Kodi Updates" folder for the sideloader; a test confirms it contains no `exec`, `eval`, `importlib`, `subprocess` or similar, so downloaded code is never run or swapped in by the app. Executable changes therefore only arrive through a signed IPA you install.

**Staged install and restart.** The test copies the bootstrap tree the way the build does into a clean folder, starts a separate Python process that can see only that folder (`-I`, no repository path), blocks the network, and runs the ten-site search against a fixture: it returns the expected hash. This proves the bundled modules import and run on their own, not that Kodi starts them (the rig and the phone do that).

**Unavoidable external dependencies (recorded, not removed).**
* Build tools: Python 3.11 for the bytecode step, `gh` (private release download), Xcode and the iPhone SDK for native frameworks, Go and the toolchain for the Elementum engine (step 3 lists their inputs and what is not mirrored).
* Metadata APIs at run time: TMDb (title matching), ESPN (Sports); step 20 covers an outage snapshot.
* Content services: the source sites, trackers and peers, the debrid service (steps 17–19), Google Drive, and Crew's own remote modules, which the Crew add-on itself downloads at run time (`control.cdnImport`): that is third-party add-on behaviour this project does not control, so the independent searches, not Crew, are the outage path.

**Elementum inputs.** `scripts/fetch_elementum_inputs.py` now takes the same `--preserved DIR` / `KODI_IOS_PRESERVED_INPUTS`: the client, the engine framework, Burst, the extras and the AirPlay framework are found by digest in the folder before any download (tests: no network, a tampered file is never used, unchanged behaviour without a folder). The five pinned Git module trees still come from `git` or the step 3 stager (`source_elementum_offline.py`).

**Not done.** A full IPA build with all hosts blocked was not run (needs the macOS toolchain and the preserved Apple inputs). No device evidence.
