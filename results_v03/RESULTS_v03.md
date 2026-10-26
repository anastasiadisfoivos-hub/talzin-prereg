# Talzin exception filter v0.3: results of the frozen Wikipedia test

Run once on 2026-10-26 (13:33-13:53 UTC), after the plan, the code and the data packer were public in this repo.
- Plan PREREG_FILTER_v03.md: SHA-256 dc5da1fd63186383... (checked against this repo before the run)
- Code run_filter_v03.py: SHA-256 03f11ce906c09124...
- Data: 5,000 Wikipedia articles (1,000 each in de, fr, nl, pl, cs), daily from 2015-07-01 to 2023-12-31.
  Map learned on 2015-2019; test on 2020-2023. 2024-2025 not downloaded (locked for the next version).
- Full run (not --fast), 2,000 bootstrap draws, 20 local fake dates per jump.

## Verdict under the frozen rules: NOT TRUSTWORTHY (trap T3 fired)

| Check | Result | Pass? |
| --- | --- | --- |
| H1 co-disturbance | DiD +0.033 (95% CI +0.016 to +0.049), lift 1.26 (CI 1.12 to 1.39); 1,349 jumps evaluated | numbers pass |
| H5 direction | i-leads 0.031 vs j-leads 0.030, diff +0.001 (CI -0.035 to +0.038) | fail |
| H4 beyond hyperlinks (map-only edges) | DiD +0.030 (98.75% CI +0.007 to +0.053) | numbers pass |
| H2 edit check adds value | diff +0.002 (CI -0.019 to +0.025) | fail |
| H3 ripple-makers repeat | diff +0.001 (CI -0.106 to +0.106), perm p 0.48 | fail |
| Trap T1' swapped lists | DiD +0.002 (CI includes 0) | quiet |
| Trap T3 time-broken map | DiD +0.016 (CI +0.002 to +0.029), 49% of H1 | FIRED |
| Trap T4 neighbour timing shift | DiD -0.009 (CI includes 0) | quiet |
| P1 planted signal | expected rise 0.0326, observed 0.0326 | pass |
| S1 from 2020-05-01 | DiD +0.030 (CI +0.013 to +0.048) | not fragile |

## Reasons (from the failure-diagnosis map fixed in advance, amendment A1)
- T3 fired: a map learned from time-shifted data predicts about half as well as the real map, so roughly half
  of H1 comes from shared seasons and rhythms rather than marble-specific links.
- H5 failed with both arrows strong and equal: pushing is mutual or caused by a shared driver, not one-way.
- The before-window DiD (+0.029) is about as large as H1: neighbours move before as well as after the jump,
  which also points to co-movement rather than a ripple.
- H2 failed with a narrow CI: the human-edit check adds nothing beyond jump size.
- P1 passed exactly, so the pipeline sees a ripple when one is there.

## What this changes
v0.4 will remove shared seasons and group rhythms before learning the map, and look for direction.
It will be frozen and published here before it is run once on data we have never seen (2024-2025),
plus live, timestamped forecasts. Ideas recorded so far: IDEAS_v04.md.

Files: results.json (all numbers), run.log and log.txt (raw output).
