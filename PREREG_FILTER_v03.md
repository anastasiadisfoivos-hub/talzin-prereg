# Talzin — Exception filter trial v0.3 (pre-registration)

Written 2026-10-25, before any Wikipedia series has been analysed. Replaces v0.2 (SHA 2ede94a0…).
Why v0.3: an independent code review (filter/review/CODE_REVIEW.md) found 2 blockers and 7
should-fix issues in v0.2 and showed, on a synthetic world, that v0.2's H1 also passes when
neighbours merely share "busy seasons" with no ripple. v0.3 fixes them and adds a direction test.
Code: run_filter_v03.py. Everything in v0.2 stays unless changed here. The 2024–2025 lock holds.

## Prior knowledge
Unchanged from v0.2: no view/edit series of these articles have been looked at. Only file
counts were checked while downloading.

## Data changes
- Check 6 uses registered-user edits only (packer refuses anonymous edits). (SF-6)
- Link map: link data plus each sample article's canonical title and all redirects to it, so a link
  to a redirect counts as a link. (BL-2b)

## Core statistic (changes)
- PRIMARY fake dates are LOCAL: 20 per jump, 30–90 days before or after the jump, inside the same
  period, each at least 30 days from ANY day the marble had z >= 3 (stricter than v0.2). (SF-1, MI-9)
- Global fake dates (v0.2) reported as a secondary H1.
- A neighbour whose matched-random pool is empty is dropped from both rates. (MI-5)
- Absolute size reported as DiD x neighbours = extra neighbour jumps per filtered jump. (MI-6)

## What each hypothesis means, and the order
- H1 CO-DISTURBANCE (the forecast claim): after a filtered jump, map-neighbours jump within 14 days
  more than matched randoms, beyond the local fake-date baseline. Pass: 95% CI lower bound > 0.
  A pass means "a filtered jump tells you which marbles will be disturbed next". It does NOT by
  itself show direction: the review showed shared busy seasons can also pass it.
- H5 DIRECTION (the ripple claim), only if H1 passes: each map edge gets a direction learned in
  2015–2019 (does i's level predict j's next week more than the reverse?). In 2020–2023, DiD for
  neighbours that i is learned to LEAD minus DiD for neighbours that lead i. Pass: CI lower bound > 0.
  Synthetic check: passes in the ripple world, fails in the busy-season world.
- H4 BEYOND LINKS, only if H1 passes: map neighbours not hyperlinked to i, using only edges where both
  articles have link data (edges without link data are dropped and counted). Pass: CI lower bound > 0. (BL-2a)
- H2 FILTER VALUE, only if H1 passes: filtered jumps vs jumps of the SAME size and persistence
  (zc >= 4 and post-14 >= 1, fixed bins zc 4/4.5/5/6/8, post-14 1/1.5/2/3) that failed only the
  human-edit-burst check. Only cells that contain both kinds are used; dropped jumps are counted.
  So H2 tests "does the many-measures check add value", the only part of the filter that is not
  about size. Pass: CI lower bound > 0. (SF-5)
- H3 REPEAT, only if H2 passes: a jump "ripples" if its real-date neighbour-jump count beats the 95th
  percentile of the counts on its own 20 fake dates. Group A = marbles with >= 1 rippling filtered jump
  in 2015–2019 (from day FIRST_OK + 90), group B = marbles with filtered jumps but none rippling.
  Outcome: share of 2020–2023 filtered jumps that ripple, A minus B, within strata of (2015–2019
  filtered-jump count tercile x neighbour-count tercile). Pass: bootstrap CI lower bound > 0 AND
  permutation p (A/B labels shuffled within strata) < 0.0125. (BL-1, MI-3, MI-4)
- Multiplicity: H1 at alpha 0.05. H2–H5 each at alpha 0.05/4 (98.75% CIs), Bonferroni.

## Traps (changes)
- T1': per-jump DiD averaged over 20 swaps of neighbour lists, then the same two-way bootstrap CI. (SF-3)
- T3: time-shift offsets from four groups (0, 120, 240, 520 days, +0–59), so most pairwise shifts are
  >= 60 days and none of the group differences is near 365. Same-group pairs can still be close; this is
  on the safe side. (MI-2)
- T4: unchanged.
- A trap that cannot be computed counts as NOT quiet: the result is then not trustworthy. (SF-4)
- Trap rule otherwise as v0.2 (CI excludes 0 and size >= 25% of the main DiD).

## Positive control P1 (now a real check) (SF-2)
In the same run, a copy with planted neighbour jumps (rate 5% of neighbour slots of evaluated H1
jumps, at day t+3, only where the neighbour had no jump from t-7 to t+14; own random generator) is
evaluated with the same jumps, fake dates and random marbles. Expected rise = mean over jumps of
(planted neighbours / neighbours). Pass if the observed DiD rise is at least 50% of expected (a planted
jump can also count for other focal jumps that share that neighbour, so overshoot is expected; the
synthetic ripple world showed 171%). If P1 fails, the result is marked not trustworthy.

## Leak canary (MI-1)
The code recomputes the learning-period values with all 2020+ rows deleted and stops if anything changes.

## Reports written to results.json (SF-7, MI-7, MI-8)
fast flag, bootstrap count, SHA-256 of this plan and the code, number of jumps actually evaluated
("underpowered" if < 100), the before-window (mirror) DiD, S1 (from 2020-05-01) and an S1 "fragile"
flag, NC skipped note, lag profile, hubs, examples.

## Synthetic results for v0.3 (no real data; --fast)
Small worlds of 600 marbles, final code, 2026-10-25:

| World | Truth | H1 | H5 direction | H4 beyond links | Traps | P1 |
| --- | --- | --- | --- | --- | --- | --- |
| Ripple | real directed ripples | pass (DiD 0.163) | pass (0.145) | pass (0.067) | quiet | pass |
| Busy seasons (reviewer's world) | shared seasons, no ripple | pass (0.030) | fail (-0.009) | fail | quiet | pass |
| Confound | same-day shared news, no ripple | fail (0.006) | fail | fail | quiet | pass |
| Weak ripples (15% of followers) | weak ripples | fail (0.008) | fail | fail | quiet | pass |

Reading: H1 alone cannot tell busy seasons from ripples; H1 + H5 can. Weak ripples are below what
a 600-marble world can see. H2 and H3 never pass here (these worlds have no edit-check value and
no marble-specific repeat), which is the correct answer for them.

## AMENDMENTS to v0.3
- A1 (2026-10-25, before any real series is analysed): FAILURE DIAGNOSIS MAP (Foivos: "every failure
  should have a reason"). Pass/fail rules are unchanged; this only fixes in advance which reported
  numbers will be used to explain a failure, so the explanation cannot be invented afterwards.

| If this fails | Possible reason | Number that tells them apart |
| --- | --- | --- |
| H1 | no co-disturbance at all | H1 DiD and Lift_adj CI below SESOI 1.10 |
| H1 | real but too weak to see | "underpowered" flag, CI straddling 0 but wide; P1 passes |
| H1 | pipeline broken | P1 fails |
| H1 | map is noise | few marbles with >= 3 neighbours; T1' about equal to H1 |
| H1 | effect only before the bot-label change | S1 vs H1 |
| H1 | neighbours move BEFORE, not after | before-window DiD vs H1 DiD |
| H5 | no pushing | H1 fails too, or both arrows' DiD near 0 |
| H5 | pushing is MUTUAL (two-way, similar strength) | did_i_leads and did_j_leads both > 0 and similar |
| H5 | direction learned in 2015–2019 changed later | exploratory: re-learn direction on 2020–2021, test 2022–2023 |
| H4 | the map is mostly hyperlinks | share_map_edges_linked high; link-map DiD > map-only DiD |
| H2 | edit check adds nothing beyond size | H2 diff near 0 with narrow CI |
| H2 | too few comparison jumps | n_fail small, wide CI |
| H3 | rippling is not a lasting trait | share_diff near 0, perm p large |
| traps | a trap fires | which trap: T1' = neighbour-kind effect, T3 = map from seasonality, T4 = timing not needed |

- A2 (2026-10-25): idea for the NEXT version, recorded before results (Foivos, whiteboard): links are
  two-way with different strengths, so measure i->j and j->i as two separate arrows (each with its
  own DiD), not one net direction. Not part of this test.
- A3 (2026-10-26, before any real series is analysed): correction to v0.1 amendment A4. Its premise was
  wrong: the 404 replies for monthly top lists were temporary, not months without data (2015-12 for de
  later returned data). As a result one month was left out of the universe for fr (2015-12), nl (2018-03)
  and pl (2019-04). The samples are still random draws (seed 42) from the eligible articles, decided before
  any analysis, so the tests are unaffected; the samples are kept as drawn rather than re-downloaded.
  The cloud-built sample.json files are the canonical samples (the Mac built a slightly different pl
  sample; its extra articles are not used).
- A4 (2026-10-26, before any real series is analysed): some early human-edit files hold both a "user" and an
  "anonymous" count (downloaded before anonymous edits were dropped). The packer now IGNORES the anonymous
  count instead of refusing the file, so check 6 still uses registered-user edits only, as planned.
  Also: the Dutch sample is the one built on the Mac (universe 16,294 / eligible 6,046, seed-42 draw,
  verified to reproduce exactly from its saved universe.json), because all its articles were downloaded;
  the cloud-built Dutch sample was not used.

