# Recovery and testing

## Full local backup

The backup is under `${HOME}/Kodi-iOS-Backups/20261029T180632Z/` on the source Deck. The directory is private and outside the repository. It contains a compressed app-state archive, SHA-256 checksum, private per-file manifest, Flatpak version information, verification report and private redaction reverse map.

To verify the archive without changing Kodi:

```sh
cd "$HOME/Kodi-iOS-Backups/20261029T180632Z"
sha256sum -c SHA256SUMS
```

The SHA-256 recorded in `reports/backup-verification.json` is an additional cross-check. Close Kodi before any recovery. Extract first into an empty private directory, inspect the result, and plan a separate recovery operation before replacing anything. Never extract over a running or working installation. The archive is a Steam Deck recovery backup, not an iOS package.

## Automated baseline validation

From the project root:

```sh
python3 -B scripts/check_project.py
```

On the source Deck, add the private-value comparison:

```sh
python3 -B scripts/check_project.py \
  --source-userdata "$HOME/.var/app/tv.kodi.Kodi/data/userdata"
```

Expected baseline issues are the empty Umbrella and JetExtractors manifests and preserved Umbrella menu references. All referenced exported smart playlists must exist. Configuration placeholders are intentional. Any new integrity, secret or reference failure must be fixed before committing or publishing.

## Checks needed later on iPhone

Record the phone model, iOS version, Kodi build and installation method. Start with a clean profile and retain a recovery copy. Test skin installation and dependencies, touch navigation, all retained menu actions, media access, representative video codecs, seeking, resume, subtitles and foreground/background behavior. Restore compatible saved account state through the private transfer procedure and test it before requesting new logins. Keep tokens outside GitHub. Capture sanitized results and failure details in the PR.

No iPhone is connected to this session, and no runtime or playback tests have been performed. Installation instructions must be finalized against the chosen, current iOS installation method rather than assumed from desktop paths.
