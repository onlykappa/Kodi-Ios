# Build 193 mockup measurements

Measured with Playwright from `docs/design/library-status-mockups-r1.html` (approved mockups, evidence class: mockup).
Boxes are in pt relative to the 402 × 874 pt board and in Kodi portrait units (× 2.687). The board's top 62 pt holds
the status bar and the back/title band; Kodi's portrait canvas (1080 × 2090) is the safe area, so subtract the safe-area
top (about 59 pt on an iPhone 16 Pro) to place a control: y_units ≈ (y_pt − 59) × 2.687. Colours are AARRGGBB.

## Board 1 · 1 · Library status (working)

| element | text | x,y pt | w×h pt | x,y units | w×h units | font | colour | background | radius |
|---|---|---|---|---|---|---|---|---|---|
| div |  | 0,0 | 402×874 | 0,-159 | 1080×2348 | 16/400 → 43 u | FFFFFFFF | FF000000 | 0px |
| button |  | 20,62 | 44×44 | 54,8 | 118×118 | 13.3333/400 → 36 u | FFFFFFFF |  | 0px |
| svg |  | 20,73 | 13×22 | 54,38 | 35×59 | 13.3333/400 → 36 u | FFFFFFFF |  | 0px |
| button |  | 338,62 | 44×44 | 908,8 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 360,73 | 22×22 | 967,38 | 59×59 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| h1 | Library status | 20,120 | 362×41 | 54,164 | 973×110 | 34/700 → 91 u | FFFFFFFF |  | 0px |
| div | Kodi Downloads on Google Drive · checked just now | 20,163 | 362×38 | 54,279 | 973×102 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| a |  | 20,215 | 362×148 | 54,419 | 973×398 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div | poster | 34,229 | 52×78 | 91,457 | 140×210 | 11/400 → 30 u | 99EBEBF5 | FF2C2C2E | 8px |
| div | WORKING ON NOW | 98,238 | 204×16 | 263,481 | 548×43 | 13/600 → 35 u | FFBF5AF2 |  | 0px |
| div | Lanterns · S1 E1 | 98,257 | 204×20 | 263,532 | 548×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | Making it start faster | 98,280 | 204×19 | 263,594 | 548×51 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| svg |  | 314,241 | 54×54 | 844,489 | 145×145 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| svg |  | 34,319 | 163×30 | 91,699 | 438×81 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | 4.8 MB/s | 207,325 | 143×19 | 556,715 | 384×51 | 15/600 → 40 u | FFFFFFFF |  | 0px |
| span | · 6 min left | 276,325 | 74×19 | 742,715 | 199×51 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| svg |  | 360,327 | 8×14 | 967,720 | 21×38 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div |  | 20,377 | 362×132 | 54,854 | 973×355 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div | 8 of 12 ready | 34,391 | 106×20 | 91,892 | 285×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | about 1 h 20 min to go | 211,392 | 157×19 | 567,895 | 422×51 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 34,421 | 217×8 | 91,973 | 583×21 | 16/400 → 43 u | FFFFFFFF | FF30D158 | 4px 0px 0px 4px |
| div |  | 254,421 | 27×8 | 682,973 | 73×21 | 16/400 → 43 u | FFFFFFFF | FFBF5AF2 | 0px |
| div |  | 284,421 | 54×8 | 763,973 | 145×21 | 16/400 → 43 u | FFFFFFFF | FF0A84FF | 0px |
| div |  | 341,421 | 27×8 | 916,973 | 73×21 | 16/400 → 43 u | FFFFFFFF | FF636366 | 0px 4px 4px 0px |
| button |  | 34,439 | 79×56 | 91,1021 | 212×150 | 13.3333/400 → 36 u | FFFFFFFF | FF2C2C2E | 10px |
| span | 8 | 67,447 | 13×24 | 180,1043 | 35×64 | 20/700 → 54 u | FF30D158 |  | 0px |
| span | Ready | 56,472 | 36×15 | 150,1110 | 97×40 | 12/400 → 32 u | 99EBEBF5 |  | 0px |
| button |  | 119,439 | 79×56 | 320,1021 | 212×150 | 13.3333/400 → 36 u | FFFFFFFF | FF2C2C2E | 10px |
| span | 1 | 154,447 | 9×24 | 414,1043 | 24×64 | 20/700 → 54 u | FFBF5AF2 |  | 0px |
| span | Working | 135,472 | 47×15 | 363,1110 | 126×40 | 12/400 → 32 u | 99EBEBF5 |  | 0px |
| button |  | 204,439 | 79×56 | 548,1021 | 212×150 | 13.3333/400 → 36 u | FFFFFFFF | FF2C2C2E | 10px |
| span | 2 | 237,447 | 13×24 | 637,1043 | 35×64 | 20/700 → 54 u | FF4FA8FF |  | 0px |
| span | Up next | 221,472 | 44×15 | 594,1110 | 118×40 | 12/400 → 32 u | 99EBEBF5 |  | 0px |
| button |  | 289,439 | 79×56 | 777,1021 | 212×150 | 13.3333/400 → 36 u | FFFFFFFF | FF2C2C2E | 10px |
| span | 1 | 324,447 | 9×24 | 871,1043 | 24×64 | 20/700 → 54 u | 99EBEBF5 |  | 0px |
| span | Kept | 316,472 | 26×15 | 849,1110 | 70×40 | 12/400 → 32 u | 99EBEBF5 |  | 0px |
| div | UP NEXT | 24,529 | 65×19 | 64,1263 | 175×51 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| a | Edit order | 309,529 | 69×19 | 830,1263 | 185×51 | 15/400 → 40 u | FF4FA8FF |  | 0px |
| div |  | 20,562 | 362×121 | 54,1352 | 973×325 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div | 1 | 34,577 | 30×30 | 91,1392 | 81×81 | 14/700 → 38 u | FF4FA8FF | 2E0A84FF | 15px |
| div | Scary Movie (2026) | 76,574 | 292×20 | 204,1384 | 785×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | Convert · 4.3 GB · about 25 min | 76,595 | 292×16 | 204,1440 | 785×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | 2 | 34,638 | 30×30 | 91,1556 | 81×81 | 14/700 → 38 u | FF4FA8FF | 2E0A84FF | 15px |
| div | Fall 2 Deadpoint (2026) | 76,635 | 292×20 | 204,1548 | 785×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | Ready now · faster start next · 16.9 GB | 76,656 | 292×16 | 204,1604 | 785×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | READY FOR KODI AND AIRPLAY | 20,697 | 362×25 | 54,1714 | 973×67 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,736 | 362×105 | 54,1819 | 973×282 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| svg |  | 34,751 | 22×22 | 91,1859 | 59×59 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | Interstellar (2014) | 68,752 | 240×20 | 183,1862 | 645×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | 4K HDR | 320,754 | 48×16 | 860,1867 | 129×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| svg |  | 34,804 | 22×22 | 91,2002 | 59×59 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | Fall 2 Deadpoint (2026) | 68,805 | 271×20 | 183,2005 | 728×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | 4K | 351,807 | 17×16 | 943,2010 | 46×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |

## Board 2 · 2 · Needs you · slower while AirPlay plays

| element | text | x,y pt | w×h pt | x,y units | w×h units | font | colour | background | radius |
|---|---|---|---|---|---|---|---|---|---|
| div |  | 0,0 | 402×874 | 0,-159 | 1080×2348 | 16/400 → 43 u | FFFFFFFF | FF000000 | 0px |
| button |  | 20,62 | 44×44 | 54,8 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 20,73 | 13×22 | 54,38 | 35×59 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| button |  | 338,62 | 44×44 | 908,8 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 360,73 | 22×22 | 967,38 | 59×59 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| h1 | Library status | 20,120 | 362×41 | 54,164 | 973×110 | 34/700 → 91 u | FFFFFFFF |  | 0px |
| div | Kodi Downloads on Google Drive · checked just now | 20,163 | 362×38 | 54,279 | 973×102 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,215 | 362×168 | 54,419 | 973×451 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div |  | 34,229 | 36×36 | 91,457 | 97×97 | 16/400 → 43 u | FFFFFFFF | 2EFF9F0A | 10px |
| svg |  | 42,237 | 20×20 | 113,478 | 54×54 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | Sign in to Google Drive again | 82,229 | 286×20 | 220,457 | 768×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | Google stopped accepting the saved sign-in. Downloads and co | 82,252 | 286×61 | 220,519 | 768×164 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| button | Sign in | 34,325 | 334×44 | 91,715 | 897×118 | 17/600 → 46 u | FF000000 | FFFFFFFF | 22px |
| div |  | 20,397 | 362×134 | 54,908 | 973×360 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div | poster | 34,411 | 52×78 | 91,946 | 140×210 | 11/400 → 30 u | 99EBEBF5 | FF2C2C2E | 8px |
| div | WORKING ON NOW | 98,419 | 204×16 | 263,967 | 548×43 | 13/600 → 35 u | FFBF5AF2 |  | 0px |
| div | Scary Movie (2026) | 98,438 | 204×20 | 263,1018 | 548×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | Converting | 98,461 | 204×19 | 263,1080 | 548×51 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| svg |  | 314,423 | 54×54 | 844,978 | 145×145 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | Slower while AirPlay plays · · 25 min left | 34,501 | 334×16 | 91,1188 | 897×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| svg |  | 34,501 | 16×16 | 91,1188 | 43×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| span | 1.1 MB/s | 234,501 | 50×16 | 629,1188 | 134×43 | 13/600 → 35 u | FFFFFFFF |  | 0px |
| div | DOWNLOADING TO GOOGLE DRIVE | 20,545 | 362×25 | 54,1306 | 973×67 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,584 | 362×86 | 54,1411 | 973×231 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div | Inception (2010) | 34,598 | 130×20 | 91,1448 | 349×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | 38% | 334,599 | 34×19 | 897,1451 | 91×51 | 15/600 → 40 u | FF4FA8FF |  | 0px |
| div |  | 34,626 | 334×6 | 91,1524 | 897×16 | 16/400 → 43 u | FFFFFFFF | FF3A3A3C | 3px |
| div |  | 34,626 | 127×6 | 91,1524 | 341×16 | 16/400 → 43 u | FFFFFFFF | FF0A84FF | 3px |
| div | AllDebrid → Drive · 2.4 MB/s · 9 min left | 34,640 | 334×16 | 91,1561 | 897×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | KEPT AS IT IS | 20,684 | 362×25 | 54,1679 | 973×67 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,723 | 362×60 | 54,1784 | 973×161 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div | Inception (2010) · old copy | 34,734 | 334×20 | 91,1814 | 897×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | Being replaced by the new download above | 34,755 | 334×16 | 91,1870 | 897×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |

## Board 3 · 3 · One movie (sheet)

| element | text | x,y pt | w×h pt | x,y units | w×h units | font | colour | background | radius |
|---|---|---|---|---|---|---|---|---|---|
| div |  | 0,0 | 402×874 | 0,-159 | 1080×2348 | 16/400 → 43 u | FFFFFFFF | FF0B0B0C | 0px |
| div |  | 0,70 | 402×804 | 0,30 | 1080×2160 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 28px 28px 0px 0px |
| div |  | 181,78 | 40×5 | 486,51 | 107×13 | 16/400 → 43 u | FFFFFFFF | FF48484A | 3px |
| div | poster | 20,99 | 64×96 | 54,107 | 172×258 | 11/400 → 30 u | 99EBEBF5 | FF2C2C2E | 10px |
| div | Lanterns · S1 E1 | 98,122 | 226×26 | 263,169 | 607×70 | 22/700 → 59 u | FFFFFFFF |  | 0px |
| div | 4K · HEVC · 2.8 GB | 98,153 | 226×19 | 263,253 | 607×51 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| a |  | 338,99 | 44×44 | 908,107 | 118×118 | 16/400 → 43 u | FF4FA8FF | FF2C2C2E | 22px |
| svg |  | 353,114 | 14×14 | 949,148 | 38×38 | 16/400 → 43 u | FF4FA8FF |  | 0px |
| div |  | 20,211 | 117×4 | 54,408 | 314×11 | 16/400 → 43 u | FFFFFFFF | FF30D158 | 2px |
| div | Downloaded | 20,221 | 117×16 | 54,435 | 314×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div |  | 143,211 | 117×4 | 384,408 | 314×11 | 16/400 → 43 u | FFFFFFFF | FF30D158 | 2px |
| div | On Drive | 143,221 | 117×16 | 384,435 | 314×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div |  | 265,211 | 117×4 | 712,408 | 314×11 | 16/400 → 43 u | FFFFFFFF | FF3A3A3C | 2px |
| div |  | 265,211 | 49×4 | 712,408 | 132×11 | 16/400 → 43 u | FFFFFFFF | FFBF5AF2 | 0px |
| div | Faster start · 42% | 265,221 | 117×16 | 712,435 | 314×43 | 13/600 → 35 u | FFFFFFFF |  | 0px |
| div |  | 20,253 | 362×299 | 54,521 | 973×803 | 16/400 → 43 u | FFFFFFFF | FF2C2C2E | 16px |
| div | Right now | 34,269 | 94×16 | 91,564 | 253×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | 4.8 | 34,287 | 94×34 | 91,613 | 253×91 | 28/700 → 75 u | FFFFFFFF |  | 0px |
| span | MB/s | 85,298 | 43×20 | 228,642 | 116×54 | 17/600 → 46 u | 99EBEBF5 |  | 0px |
| div | 6 min left | 302,267 | 66×19 | 811,559 | 177×51 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| svg |  | 34,331 | 334×150 | 91,731 | 897×403 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | Average | 34,502 | 106×16 | 91,1190 | 285×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | 4.2 MB/s | 34,518 | 106×20 | 91,1233 | 285×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | Done | 148,502 | 106×16 | 398,1190 | 285×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | 1.2 of 2.8 GB | 148,518 | 106×20 | 398,1233 | 285×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | Started | 262,502 | 106×16 | 704,1190 | 285×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | 1:13 PM | 262,518 | 106×20 | 704,1233 | 285×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | It already plays in Kodi and on AirPlay. This rearranges it  | 20,568 | 362×63 | 54,1368 | 973×169 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| button | Play | 20,800 | 176×50 | 54,1991 | 473×134 | 17/600 → 46 u | FF000000 | FFFFFFFF | 25px |
| button | Pause | 206,800 | 176×50 | 554,1991 | 473×134 | 17/600 → 46 u | FFFFFFFF | FF3A3A3C | 25px |

## Board 4 · 4 · Transfers with the new graph

| element | text | x,y pt | w×h pt | x,y units | w×h units | font | colour | background | radius |
|---|---|---|---|---|---|---|---|---|---|
| div |  | 0,0 | 402×874 | 0,-159 | 1080×2348 | 16/400 → 43 u | FFFFFFFF | FF000000 | 0px |
| button |  | 20,62 | 44×44 | 54,8 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 20,73 | 13×22 | 54,38 | 35×59 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| a | History | 324,74 | 58×20 | 871,40 | 156×54 | 17/400 → 46 u | FF4FA8FF |  | 0px |
| h1 | Transfers | 20,120 | 362×41 | 54,164 | 973×110 | 34/700 → 91 u | FFFFFFFF |  | 0px |
| div | 2 running · 2 up next | 20,163 | 362×19 | 54,279 | 973×51 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| button | Converting | 20,196 | 123×36 | 54,368 | 331×97 | 15/600 → 40 u | FF000000 | FFFFFFFF | 18px |
| span |  | 34,210 | 8×8 | 91,406 | 21×21 | 15/600 → 40 u | FF000000 | FFBF5AF2 | 4px |
| button | Downloading | 151,196 | 137×36 | 406,368 | 368×97 | 15/600 → 40 u | FFFFFFFF | FF2C2C2E | 18px |
| span |  | 165,210 | 8×8 | 443,406 | 21×21 | 15/600 → 40 u | FFFFFFFF | FF0A84FF | 4px |
| div |  | 20,246 | 362×370 | 54,502 | 973×994 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div | Lanterns · S1 E1 | 34,260 | 334×20 | 91,540 | 897×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | Making it start faster · 42% | 34,282 | 334×19 | 91,599 | 897×51 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| div | 4.8 | 34,311 | 62×49 | 91,677 | 167×132 | 40/700 → 107 u | FFFFFFFF |  | 0px |
| div | MB/s · 6 min left | 102,334 | 133×20 | 274,739 | 357×54 | 17/600 → 46 u | 99EBEBF5 |  | 0px |
| svg |  | 34,370 | 334×170 | 91,836 | 897×457 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div |  | 34,550 | 334×6 | 91,1319 | 897×16 | 16/400 → 43 u | FFFFFFFF | FF3A3A3C | 3px |
| div |  | 34,550 | 140×6 | 91,1319 | 376×16 | 16/400 → 43 u | FFFFFFFF | FFBF5AF2 | 3px |
| div | Peak | 34,566 | 106×16 | 91,1362 | 285×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | 5.6 MB/s | 34,582 | 106×20 | 91,1405 | 285×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | Average | 148,566 | 106×16 | 398,1362 | 285×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | 4.2 MB/s | 148,582 | 106×20 | 398,1405 | 285×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | Started | 262,566 | 106×16 | 704,1362 | 285×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | 1:03 PM | 262,582 | 106×20 | 704,1405 | 285×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | UP NEXT | 20,630 | 362×23 | 54,1534 | 973×62 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,667 | 362×105 | 54,1634 | 973×282 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div | Scary Movie (2026) | 34,683 | 159×20 | 91,1677 | 427×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | convert · 4.3 GB | 269,685 | 99×16 | 723,1682 | 266×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | Fall 2 Deadpoint (2026) | 34,736 | 189×20 | 91,1819 | 508×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | faster start · 16.9 GB | 244,738 | 124×16 | 656,1824 | 333×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |

## Board 5 · 5 · Notifications (same card as Library status)

| element | text | x,y pt | w×h pt | x,y units | w×h units | font | colour | background | radius |
|---|---|---|---|---|---|---|---|---|---|
| div |  | 0,0 | 402×874 | 0,-159 | 1080×2348 | 16/400 → 43 u | FFFFFFFF | FF000000 | 0px |
| button |  | 20,62 | 44×44 | 54,8 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 20,73 | 13×22 | 54,38 | 35×59 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| a | Clear All | 315,74 | 67×20 | 846,40 | 180×54 | 17/400 → 46 u | FF4FA8FF |  | 0px |
| h1 | Notifications | 20,120 | 362×41 | 54,164 | 973×110 | 34/700 → 91 u | FFFFFFFF |  | 0px |
| div |  | 20,175 | 362×36 | 54,312 | 973×97 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 10px |
| button | All | 22,177 | 88×32 | 59,317 | 236×86 | 13/600 → 35 u | FFFFFFFF | FF48484A | 8px |
| button | General | 112,177 | 88×32 | 301,317 | 236×86 | 13/600 → 35 u | 99EBEBF5 |  | 8px |
| button | Downloads | 202,177 | 88×32 | 543,317 | 236×86 | 13/600 → 35 u | 99EBEBF5 |  | 8px |
| button | Problems | 292,177 | 88×32 | 785,317 | 236×86 | 13/600 → 35 u | 99EBEBF5 |  | 8px |
| div | RUNNING NOW | 20,225 | 362×23 | 54,446 | 973×62 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| a |  | 20,262 | 362×84 | 54,545 | 973×226 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div | poster | 34,274 | 40×60 | 91,578 | 107×161 | 9/400 → 24 u | 99EBEBF5 | FF2C2C2E | 6px |
| div | Lanterns · S1 E1 | 86,279 | 262×20 | 231,591 | 704×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | Making it start faster · 4.8 MB/s · 6 min left | 86,302 | 262×16 | 231,653 | 704×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div |  | 86,325 | 262×4 | 231,715 | 704×11 | 16/400 → 43 u | FFFFFFFF | FF3A3A3C | 2px |
| div |  | 86,325 | 110×4 | 231,715 | 296×11 | 16/400 → 43 u | FFFFFFFF | FFBF5AF2 | 2px |
| svg |  | 360,297 | 8×14 | 967,640 | 21×38 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| a |  | 20,360 | 362×84 | 54,809 | 973×226 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div | poster | 34,372 | 40×60 | 91,841 | 107×161 | 9/400 → 24 u | 99EBEBF5 | FF2C2C2E | 6px |
| div | Inception (2010) | 86,377 | 262×20 | 231,854 | 704×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | AllDebrid → Drive · 2.4 MB/s · 9 min left | 86,400 | 262×16 | 231,916 | 704×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div |  | 86,423 | 262×4 | 231,978 | 704×11 | 16/400 → 43 u | FFFFFFFF | FF3A3A3C | 2px |
| div |  | 86,423 | 100×4 | 231,978 | 269×11 | 16/400 → 43 u | FFFFFFFF | FF0A84FF | 2px |
| svg |  | 360,395 | 8×14 | 967,903 | 21×38 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | Up next: Scary Movie, then Fall 2 Deadpoint · | 20,458 | 362×32 | 54,1072 | 973×86 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| a | Library status | 24,458 | 324×32 | 64,1072 | 871×86 | 13/400 → 35 u | FF4FA8FF |  | 0px |
| div | EARLIER | 20,504 | 362×25 | 54,1196 | 973×67 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,543 | 362×123 | 54,1301 | 973×331 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div |  | 34,570 | 8×8 | 91,1373 | 21×21 | 16/400 → 43 u | FFFFFFFF | FF0A84FF | 4px |
| div |  | 54,556 | 36×36 | 145,1335 | 97×97 | 16/400 → 43 u | FFFFFFFF | 2E30D158 | 10px |
| svg |  | 63,565 | 18×18 | 169,1360 | 48×48 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | Ready for Kodi and AirPlay | 102,555 | 193×19 | 274,1333 | 519×51 | 15/600 → 40 u | FFFFFFFF |  | 0px |
| div | 2m | 349,555 | 19×19 | 938,1333 | 51×51 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | Interstellar (2014) opens quickly now | 102,576 | 266×16 | 274,1389 | 715×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div |  | 54,618 | 36×36 | 145,1502 | 97×97 | 16/400 → 43 u | FFFFFFFF | 2E0A84FF | 10px |
| svg |  | 63,627 | 18×18 | 169,1526 | 48×48 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | Queued for Google Drive | 102,617 | 179×19 | 274,1499 | 481×51 | 15/600 → 40 u | FFFFFFFF |  | 0px |
| div | 5m | 349,617 | 19×19 | 938,1499 | 51×51 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | Inception · AllDebrid → Drive → ready | 102,638 | 266×16 | 274,1556 | 715×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |

## Board 6 · 6 · Bell states on Home

| element | text | x,y pt | w×h pt | x,y units | w×h units | font | colour | background | radius |
|---|---|---|---|---|---|---|---|---|---|
| div |  | 0,0 | 402×874 | 0,-159 | 1080×2348 | 16/400 → 43 u | FFFFFFFF | FF000000 | 0px |
| h1 | The bell on Home | 20,62 | 362×41 | 54,8 | 973×110 | 34/700 → 91 u | FFFFFFFF |  | 0px |
| div | NOTHING RUNNING | 20,125 | 362×19 | 54,177 | 973×51 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,154 | 362×96 | 54,255 | 973×258 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| button |  | 274,180 | 44×44 | 736,325 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 284,190 | 24×24 | 763,352 | 64×64 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| button |  | 324,180 | 44×44 | 871,325 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 334,190 | 24×24 | 897,352 | 64×64 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| div | WORKING · 42% | 20,272 | 362×19 | 54,572 | 973×51 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,301 | 362×96 | 54,650 | 973×258 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| button |  | 274,327 | 44×44 | 736,720 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 274,327 | 44×44 | 736,720 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| span | 2 | 304,325 | 18×18 | 817,715 | 48×48 | 11/700 → 30 u | FF000000 | FF0A84FF | 9px |
| button |  | 324,327 | 44×44 | 871,720 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 334,337 | 24×24 | 897,747 | 64×64 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| div | The ring fills with the job's real progress; the number is h | 20,407 | 362×32 | 54,935 | 973×86 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | SLOWER WHILE AIRPLAY PLAYS | 20,461 | 362×19 | 54,1080 | 973×51 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,490 | 362×96 | 54,1158 | 973×258 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| button |  | 274,516 | 44×44 | 736,1228 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 274,516 | 44×44 | 736,1228 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| button |  | 324,516 | 44×44 | 871,1228 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 334,526 | 24×24 | 897,1255 | 64×64 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| div | Grey ring: still moving, just slower, so the video gets the  | 20,596 | 362×32 | 54,1443 | 973×86 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | NEEDS YOU | 20,650 | 362×19 | 54,1588 | 973×51 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,679 | 362×96 | 54,1666 | 973×258 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| button |  | 274,705 | 44×44 | 736,1736 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 284,715 | 24×24 | 763,1763 | 64×64 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| span | 1 | 300,707 | 18×18 | 806,1741 | 48×48 | 11/700 → 30 u | FF000000 | FFFF453A | 9px |
| button |  | 324,705 | 44×44 | 871,1736 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 334,715 | 24×24 | 897,1763 | 64×64 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| div | Red only when you have to do something, such as sign in to G | 20,785 | 362×32 | 54,1951 | 973×86 | 13/400 → 35 u | 99EBEBF5 |  | 0px |

## Board 7 · 7 · Queue (Edit order)

| element | text | x,y pt | w×h pt | x,y units | w×h units | font | colour | background | radius |
|---|---|---|---|---|---|---|---|---|---|
| div |  | 0,0 | 402×874 | 0,-159 | 1080×2348 | 16/400 → 43 u | FFFFFFFF | FF000000 | 0px |
| button |  | 20,62 | 44×44 | 54,8 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 20,73 | 13×22 | 54,38 | 35×59 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| h1 | Queue | 20,120 | 362×41 | 54,164 | 973×110 | 34/700 → 91 u | FFFFFFFF |  | 0px |
| div | One at a time, top first · about 1 h 20 min | 20,163 | 362×19 | 54,279 | 973×51 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| div | WORKING ON NOW | 20,196 | 362×23 | 54,368 | 973×62 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,233 | 362×80 | 54,468 | 973×215 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div | Lanterns · S1 E1 | 34,245 | 126×20 | 91,500 | 339×54 | 17/600 → 46 u | FFFFFFFF |  | 0px |
| div | 42% | 334,245 | 34×20 | 897,500 | 91×54 | 15/600 → 40 u | FFBF5AF2 |  | 0px |
| div |  | 34,273 | 334×4 | 91,575 | 897×11 | 16/400 → 43 u | FFFFFFFF | FF3A3A3C | 2px |
| div |  | 34,273 | 140×4 | 91,575 | 376×11 | 16/400 → 43 u | FFFFFFFF | FFBF5AF2 | 2px |
| div | Making it start faster · 6 min left · finishes first | 34,285 | 334×16 | 91,607 | 897×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | UP NEXT | 20,327 | 362×25 | 54,720 | 973×67 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,366 | 362×194 | 54,825 | 973×521 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| div | 1 | 34,384 | 28×28 | 91,873 | 75×75 | 13/700 → 35 u | FF4FA8FF | 2E0A84FF | 14px |
| div | Scary Movie (2026) | 72,380 | 194×20 | 193,863 | 521×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | Convert · 4.3 GB · about 25 min | 72,401 | 194×16 | 193,919 | 521×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| button |  | 276,376 | 44×44 | 742,852 | 118×118 | 13.3333/400 → 36 u | 4C101010 |  | 22px |
| svg |  | 290,393 | 16×10 | 779,897 | 43×27 | 13.3333/400 → 36 u | 4C101010 |  | 0px |
| button |  | 330,376 | 44×44 | 887,852 | 118×118 | 13.3333/400 → 36 u | FF000000 | FF2C2C2E | 22px |
| svg |  | 344,393 | 16×10 | 924,897 | 43×27 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| div | 2 | 34,449 | 28×28 | 91,1048 | 75×75 | 13/700 → 35 u | FF4FA8FF | 2E0A84FF | 14px |
| div | Inception (2010) | 72,445 | 194×20 | 193,1037 | 521×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | Convert after download · 22 GB | 72,466 | 194×16 | 193,1094 | 521×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| button |  | 276,441 | 44×44 | 742,1026 | 118×118 | 13.3333/400 → 36 u | FF000000 | FF2C2C2E | 22px |
| svg |  | 290,458 | 16×10 | 779,1072 | 43×27 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| button |  | 330,441 | 44×44 | 887,1026 | 118×118 | 13.3333/400 → 36 u | FF000000 | FF2C2C2E | 22px |
| svg |  | 344,458 | 16×10 | 924,1072 | 43×27 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| div | 3 | 34,514 | 28×28 | 91,1223 | 75×75 | 13/700 → 35 u | 99EBEBF5 | FF2C2C2E | 14px |
| div | Fall 2 Deadpoint (2026) | 72,502 | 194×20 | 193,1190 | 521×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | Ready now · faster start · 16.9 GB | 72,523 | 194×32 | 193,1247 | 521×86 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| button |  | 276,506 | 44×44 | 742,1201 | 118×118 | 13.3333/400 → 36 u | FF000000 | FF2C2C2E | 22px |
| svg |  | 290,523 | 16×10 | 779,1247 | 43×27 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| button |  | 330,506 | 44×44 | 887,1201 | 118×118 | 13.3333/400 → 36 u | 4C101010 |  | 22px |
| svg |  | 344,523 | 16×10 | 924,1247 | 43×27 | 13.3333/400 → 36 u | 4C101010 |  | 0px |
| div | Moving a video to the top makes it next. Faster-start jobs a | 20,574 | 362×55 | 54,1384 | 973×148 | 13/400 → 35 u | 99EBEBF5 |  | 0px |

## Board 8 · 8 · History

| element | text | x,y pt | w×h pt | x,y units | w×h units | font | colour | background | radius |
|---|---|---|---|---|---|---|---|---|---|
| div |  | 0,0 | 402×874 | 0,-159 | 1080×2348 | 16/400 → 43 u | FFFFFFFF | FF000000 | 0px |
| button |  | 20,62 | 44×44 | 54,8 | 118×118 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| svg |  | 20,73 | 13×22 | 54,38 | 35×59 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| h1 | History | 20,120 | 362×41 | 54,164 | 973×110 | 34/700 → 91 u | FFFFFFFF |  | 0px |
| div |  | 20,175 | 362×36 | 54,312 | 973×97 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 10px |
| button | Today | 22,177 | 118×32 | 59,317 | 317×86 | 13/600 → 35 u | FFFFFFFF | FF48484A | 8px |
| button | Yesterday | 142,177 | 118×32 | 382,317 | 317×86 | 13/600 → 35 u | 99EBEBF5 |  | 8px |
| button | 7 days | 262,177 | 118×32 | 704,317 | 317×86 | 13/600 → 35 u | 99EBEBF5 |  | 8px |
| div | DIDN'T FINISH | 20,225 | 362×23 | 54,446 | 973×62 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,262 | 362×108 | 54,545 | 973×290 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| svg |  | 34,276 | 22×22 | 91,583 | 59×59 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | Inception (2010) | 68,274 | 130×20 | 183,578 | 349×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | 12:23 PM | 311,274 | 57×20 | 836,578 | 153×54 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | AllDebrid was busy and didn't answer properly | 68,296 | 300×16 | 183,637 | 806×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| button | Try again | 68,322 | 100×36 | 183,707 | 269×97 | 15/600 → 40 u | FF4FA8FF | FF2C2C2E | 18px |
| div | FINISHED | 20,384 | 362×25 | 54,873 | 973×67 | 15/600 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,423 | 362×121 | 54,978 | 973×325 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 16px |
| svg |  | 34,442 | 22×22 | 91,1029 | 59×59 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | Interstellar (2014) | 68,435 | 141×20 | 183,1010 | 379×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | 1:02 PM | 319,435 | 49×20 | 857,1010 | 132×54 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | Faster start · 52 GB in 41 min | 68,456 | 300×16 | 183,1067 | 806×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| svg |  | 34,503 | 22×22 | 91,1193 | 59×59 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | Lanterns · S1 E2 | 68,496 | 128×20 | 183,1174 | 344×54 | 17/400 → 46 u | FFFFFFFF |  | 0px |
| div | 11:40 AM | 313,496 | 55×20 | 841,1174 | 148×54 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div | Downloaded and ready · 2.6 GB | 68,517 | 300×16 | 183,1231 | 806×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |

## Board 9 · 9 · Movie sheet: ready

| element | text | x,y pt | w×h pt | x,y units | w×h units | font | colour | background | radius |
|---|---|---|---|---|---|---|---|---|---|
| div |  | 0,0 | 402×874 | 0,-159 | 1080×2348 | 16/400 → 43 u | FFFFFFFF | FF0B0B0C | 0px |
| div |  | 0,70 | 402×804 | 0,30 | 1080×2160 | 16/400 → 43 u | FFFFFFFF | FF1C1C1E | 28px 28px 0px 0px |
| div |  | 181,78 | 40×5 | 486,51 | 107×13 | 16/400 → 43 u | FFFFFFFF | FF48484A | 3px |
| div | poster | 20,99 | 64×96 | 54,107 | 172×258 | 11/400 → 30 u | 99EBEBF5 | FF2C2C2E | 10px |
| div | Interstellar (2014) | 98,122 | 226×26 | 263,169 | 607×70 | 22/700 → 59 u | FFFFFFFF |  | 0px |
| div | 4K HDR · 2 h 49 min · 52 GB | 98,153 | 226×19 | 263,253 | 607×51 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| button |  | 338,99 | 44×44 | 908,107 | 118×118 | 13.3333/400 → 36 u | FF000000 | FF2C2C2E | 22px |
| svg |  | 353,114 | 14×14 | 949,148 | 38×38 | 13.3333/400 → 36 u | FF000000 |  | 0px |
| div |  | 20,211 | 117×4 | 54,408 | 314×11 | 16/400 → 43 u | FFFFFFFF | FF30D158 | 2px |
| div | Downloaded | 20,221 | 117×16 | 54,435 | 314×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div |  | 143,211 | 117×4 | 384,408 | 314×11 | 16/400 → 43 u | FFFFFFFF | FF30D158 | 2px |
| div | On Drive | 143,221 | 117×16 | 384,435 | 314×43 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| div |  | 265,211 | 117×4 | 712,408 | 314×11 | 16/400 → 43 u | FFFFFFFF | FF30D158 | 2px |
| div | Ready | 265,221 | 117×16 | 712,435 | 314×43 | 13/600 → 35 u | FFFFFFFF |  | 0px |
| div |  | 20,253 | 362×195 | 54,521 | 973×524 | 16/400 → 43 u | FFFFFFFF | FF2C2C2E | 16px |
| div | Kodi | 34,268 | 31×19 | 91,562 | 83×51 | 15/400 → 40 u | FFFFFFFF |  | 0px |
| div | Opens in about 1 s | 236,268 | 132×19 | 634,562 | 355×51 | 15/600 → 40 u | FF30D158 |  | 0px |
| div | AirPlay | 34,317 | 50×19 | 91,693 | 134×51 | 15/400 → 40 u | FFFFFFFF |  | 0px |
| div | Ready, seeks instantly | 206,317 | 162×19 | 554,693 | 435×51 | 15/600 → 40 u | FF30D158 |  | 0px |
| div | Picture | 34,366 | 50×19 | 91,825 | 134×51 | 15/400 → 40 u | FFFFFFFF |  | 0px |
| div | HEVC 4K HDR10 · copied | 191,366 | 177×19 | 513,825 | 476×51 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| div | Sound and subtitles | 34,415 | 140×19 | 91,957 | 376×51 | 15/400 → 40 u | FFFFFFFF |  | 0px |
| div | English · 5.1 | 286,415 | 82×19 | 768,957 | 220×51 | 15/400 → 40 u | 99EBEBF5 |  | 0px |
| div |  | 20,464 | 362×100 | 54,1088 | 973×269 | 16/400 → 43 u | FFFFFFFF | FF2C2C2E | 16px |
| div |  | 34,476 | 30×30 | 91,1120 | 81×81 | 16/400 → 43 u | FFFFFFFF | 2EFF9F0A | 9px |
| svg |  | 41,483 | 16×16 | 110,1139 | 43×43 | 16/400 → 43 u | FFFFFFFF |  | 0px |
| div | When something needs you | 76,476 | 292×19 | 204,1120 | 785×51 | 15/600 → 40 u | FFFFFFFF |  | 0px |
| div | This card appears only then, with one button, e.g. "Sign in  | 76,497 | 292×55 | 204,1177 | 785×148 | 13/400 → 35 u | 99EBEBF5 |  | 0px |
| button | Play | 20,800 | 176×50 | 54,1991 | 473×134 | 17/600 → 46 u | FF000000 | FFFFFFFF | 25px |
| button | Play on TV | 206,800 | 176×50 | 554,1991 | 473×134 | 17/600 → 46 u | FFFFFFFF | FF3A3A3C | 25px |

