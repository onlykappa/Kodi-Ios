# Google Drive integration: requirements to investigate

The owner has an existing Google Drive account with 5 TB capacity and wants to stream personal videos to Kodi on iPhone. No Drive add-on was found in the source setup, and no Drive account was accessed during this baseline work.

Current playback methods have not yet been researched or selected. The roadmap should compare an actively maintained Kodi Drive integration against a separately hosted streaming bridge if required. Verify support for the actual iOS Kodi build, authentication flow, seeking/range requests, token storage, account/API limits and long-term maintenance before choosing a method.

Acceptance criteria:

- Authenticate interactively on the target device or trusted private service.
- Keep OAuth client secrets, access/refresh tokens, account identifiers and private folder links out of GitHub.
- Keep all media in Drive; the configuration repository stores neither videos nor generated private streaming links.
- Test a small representative set for start-up, seeking, resume, subtitles and expired-token recovery.
- Document the selected integration and current upstream instructions once verified.

This file records the scope for the owner's roadmap. It is not a working Drive configuration or a claim of iOS compatibility.
