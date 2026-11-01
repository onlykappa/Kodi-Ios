# Settings rework and notification center (planned, not built yet)

Requested by the owner on 2026-11-01, to be done together with the settings page rework.

## Notification center

A bell button at the top of the portrait pages, beside the profile button, opening a list of recent
messages instead of Kodi's toasts popping over the page (for example the "Elementum · SCARY MOVIE (2026)
[2160p] … 3.5 MB/s · 4%" download status in the top right corner).

What it should show:

- **Downloads**: Elementum downloads in progress (title, percent, speed), finished, and uploaded to Google
  Drive (driveupload already knows when a file reached Drive and the phone copy was removed).
- **Problems**: Elementum engine skipped or failed to start, Drive upload paused (with the reason), portrait
  layout refresh failed, Umbrella source page could not attach, Play on TV refused (with the Roku's answer).
- **Updates**: a newer build available (updates.py already checks).
- A badge with the number of unread messages on the bell; tapping a message opens what it is about
  (Elementum's torrents list, the Drive folder, the log uploader for problems).

Open questions to settle before coding:

1. Where Elementum's own toasts come from (engine notifications through JSON-RPC GUI.ShowNotification) and
   whether they can be redirected, or only hidden and mirrored (the engine's /torrents/list gives progress).
2. Whether Kodi's own notification toasts should be hidden everywhere or only on the portrait pages.
3. How long to keep messages (suggestion: the last 50, cleared on demand).

## Settings rework

The Settings pages are Fuse's landscape windows shrunk into the middle of the portrait screen and look
cramped (owner's screenshots, 2026-11-01). Plan: portrait settings pages in the same iOS style as the rest
(grouped lists, large title, back button), starting with the pages the owner uses: Elementum, Umbrella,
Google Drive, Trakt, subtitles, player.

## Not in this plan

Anything already shipped: Download button and episode picker, Choose a version page for Elementum and
Umbrella, Apple TV-style video controls, Elementum folders following a reinstall.
