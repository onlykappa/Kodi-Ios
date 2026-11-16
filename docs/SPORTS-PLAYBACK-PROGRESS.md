# Sports playback repair

## Sports playback repair and combined build — 2026-11-16

Owner build 557 log confirms an asynchronous Jet play request returned True and Live Now passed it to Player.play; ResolveURL was installed but absent from the script import path; failed extractor resolution could pass a webpage to Kodi. Load ResolveURL's declared dependency graph, accept only actual playback strings at the page boundary, and reject unresolved links. Forced refresh now joins an active collection, with a process-wide file lock preventing simultaneous interpreter scans. Keep existing results during refresh and avoid rewriting unchanged page properties. Provider outages in the log remain upstream failures; these changes cannot guarantee their availability or phone frame rate.

All 14 sports suites pass (176 tests). Five focused regression cases cover dependency loading, the asynchronous acknowledgement, refresh joining and failed/successful link resolution. Existing mock window failures exposed the need to cache previous properties within each page; corrected and all suites rerun. Owner also approved review/merge of PR #44 and one combined testing IPA. PR #44 merged as 9b276e7 after its 265 Python tests and project check passed. Next: integrate newer sports/subtitle source with main, run native candidate CI, verify/pin its framework, then package and verify the IPA. Actual iPhone playback/scrolling/AirPlay checks remain pending.

