# Isolated AirPlay candidate validation

Source PR: https://github.com/onlykappa/Kodi-Ios/pull/8
Source commit: 532db69035f33650d925a555bfa1657d5efbc1ea
Source tree: e13e66cfd41f9351c9f49f0db0605a20d0553f29

Only this marker differs from the source tree above. Push validates host tests and iPhoneOS compilation, with no IPA or framework release trigger. Includes transient background-read cancellation and the cross-version first-frame RPU fixture correction.
