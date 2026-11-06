# Kodi iOS diagnostic logs

Each launch writes an INFO record headed `Kodi iOS diagnostic` to `kodi.log`. It identifies the installed IPA build, complete source commit, source branch, workflow run/attempt, build timestamp, and pinned AirPlay/GlassBar/Kodi executable releases. A launch session ID connects UI actions, transfers, preparation and background status. Missing build metadata is reported as `unknown`; the available update number is never substituted.

Detailed records are available without enabling Kodi's verbose debug mode:

- Startup reports Kodi, operating-system and Python versions.
- One summary per minute reports queue counts, states, phases, progress/byte counts, worker heartbeat age, retry/cleanup state and free phone space. It does not dump accounts or queue source objects.
- Preparation failures include phase, attempt, inspected codec/resolution/HDR information, underlying exception chain, HTTP status/errno when present, and file/function/line locations. Local variables and source lines are excluded.
- Drive network failures report method, hostname, attempt, elapsed time and retry decision. Upload chunk records include transferred bytes and response timing; slow requests are recorded too. Request headers, bodies, source paths and resumable session URLs are excluded.
- Menu actions record the page opened/closed, elapsed time and script failures without action arguments.
- AirPlay records route/format, elapsed connection time, player outcome and native receiver/conversion events. UI scripts attach to the service's existing session identity.

Settings → Export diagnostic log saves `Kodi-build-N-YYYYMMDDTHHMMSSZ.log` under Files → On My iPhone → Kodi → Kodi Logs. The export contains a build header, the preceding and current launch logs, and a current queue summary. Each source log is bounded to its most recent 32 MiB. The original logs remain unchanged. Exporting does not upload or send a file.

Generated diagnostics exclude credentials and signed URLs. Export additionally removes URLs (including Kodi pipe headers), magnets, bearer/basic credentials and common token/password/cookie fields from third-party log lines. Third-party add-ons can log arbitrary text, so this redaction cannot identify every possible secret; review a log before sharing it publicly. Existing logs from older builds cannot gain diagnostic detail retroactively.
