# Changelog

## 2026-10-29T18:27:38.692486+00:00 — roadmap planning

Created five-phase roadmap and persistent trackers, reviewed historical backup/inventory evidence, retained existing documentation and known failures, and added planning consistency validation. No migration implementation started.

## Historical baseline

Commits 3bf0e63 and c5aecaf introduced the sanitized snapshot, verified backup metadata, private account preservation instructions and scanner/tests. Those reports describe prior results, not new device or recovery tests.

## Phase 1 — security, baseline and isolated recovery

Replaced fixed roadmap totals/status lists with task-derived progress; added four regression tests and mandatory review gates. Verified both archives, original source immutability, publication exclusions, snapshot/history/private-value checks and isolated recovery. Logged parser and report-name failures with fixes/retests. Retained private recovery copy and documented rollback; no source or media changes. Phase 1 READY FOR REVIEW; Phase 2 requires authorization.

## Phase 2 authorization — P2-002 blocked

Recorded owner approval of Phase 1 and authorization of Phase 2. Requested missing target and signing details. No task completion added; progress remains 7/32. Phase 2 dependency order prevents compatibility implementation before target constraints are established.

Deployment requirement update: prioritize an unsigned IPA and existing owner sideloader; Phase 2 now includes bundling/import feasibility and Phase 4 explicitly covers artifact structure, provenance, entitlements, integrity and real-device signing/install tests. Credentials remain external. No IPA assembled or device compatibility asserted.

## Phase 2 — static target and compatibility review

Recorded confirmed non-jailbroken iPhone 16 Pro/iOS 27.0.1 target; owner waived sideloader identity and approved sports deferral. Researched official matching 21.3 ARM64 DEB foundation and conversion; exact OS support remains unverified. Classified all 240 baseline manifest records, produced a deterministic 32-file provisional import configuration with a 48-entry candidate dependency closure, portable paths, menu-slot adaptation mapping and upstream-syntax touch adapter. Removed active Umbrella/native/backend references from target only. Documented private account mappings and separate-import packaging tradeoff. Six new target regressions pass; source/baseline unchanged. No IPA assembled, no device success claimed, no Phase 3 started.

## Phase 3 authorization and visual requirements

Phase 2 static review passed. Added seven future tasks (39 total), preserving completed history and dynamic counts. Added real-code comparison, simulator investigation, actual-device screen captures, visual regression fixes/retests and mandatory final owner screenshot approval. Phase 4 work has not begun.

## Phase 3 research, owner choice and test-executor blocker

Compared maintained direct add-on/public or private relay, rclone bridge and older alternative using primary sources. Owner selected direct add-on/public relay. Recorded read-only OAuth trust/lifecycle design, current endpoint and imminent legacy endpoint retirement, cost/quota caveats and source pins. Verified 74 upstream text files outside Git. Preflight ran 42 upstream tests: 34 pass, eight error on denied local sockets. Preserved failure evidence and blocked P3-004; no integration-ready claim or Phase 4 work. No Google account or media accessed.
