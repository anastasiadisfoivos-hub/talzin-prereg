# Talzin — Exception filter trial v0.1 (pre-registration)

Written 2026-10-25, before any Wikipedia data is downloaded or looked at.
Frozen by SHA-256 (see PREREG_FILTER.sha256). Any change after freezing goes in the
AMENDMENTS section at the bottom, with a date and a reason. The 2024–2025 lock still holds:
no data on or after 2024-01-01 is downloaded or used.

## Idea being tested (Foivos's words, simplified)
Marbles are every separate data group on the web. When wind hits, most marbles do not move.
A really affected marble (1) changes on many measures at once, not only one, and (2) ripples:
marbles NEAR it in the data get disturbed at about the same time, soon after.
"Near" = near in the data: marbles that moved together in the past, after removing shared wind.

## Data
- Marbles = Wikipedia articles in 5 language editions: de (DE+AT), fr (FR+BE-fr), nl (NL+BE-nl),
  pl (PL), cs (CZ). Languages are not countries; this is a known limit of v0.1.
- Universe: union of the monthly top-1000 article lists, 2015-07 to 2023-12, per language.
  Drop the main page and any title containing ':' . Keep titles that appear in >= 3 monthly lists.
  Random sample of up to 1500 per language (seed 42). Target ~7500 marbles.
- Measures per marble, daily, 2015-07-01 to 2023-12-31:
  views (agent=user) and edits (all editor types).

## Preprocessing (all causal: day t only uses days <= t, except the post-jump persistence window,
which is part of the outcome definition and never used as a predictor)
- y = log(1 + views).
- Baseline b_t = median of y over days t-28..t-1. Residual r_t = y_t - b_t.
- Scale s_t = 1.4826 * MAD of r over days t-365..t-1 (minimum 0.05). z_t = r_t / s_t.
- Web-wide removal (check 5): zc_t = z_t - median over all marbles of the same language of z_t.
- Edits: e5_t = edits over t-1..t+3; expected = 5 * mean daily edits over t-90..t-2.
  Edit burst if Poisson upper-tail p(e5 | expected) < 0.01 and e5 >= 3.

## Jumps
- Raw jump (no filter): z_t >= 3, first such day after >= 14 quiet days for that marble.
- Filtered jump = raw jump that also passes:
  - Check 1 SIZE + POSITION: zc_t >= 4 and mean of zc over t..t+13 >= 1 (a lasting move, not a one-day spike).
  - Check 5 NOT JUST NOISE: uses zc (web-wide move removed), as above.
  - Check 6 MANY MEASURES: edit burst at t.
- Checks 2 (timing vs a named event) and 4 (fake dates) are not filter steps in v0.1, because we
  have no event list for millions of marbles. Check 4 is used as a trap instead (see Traps).
- Check 3 REPEAT is tested as hypothesis H3, not used as a filter step.
- "Neighbour new jump": neighbour j has zc >= 3 on some day in t+1..t+14 and had no zc >= 3 on t-7..t.

## The map ("near"), learned on 2015-07-01 .. 2019-12-31 ONLY
- Series used: zc clipped to [-5, 5], then 3-day centred mean.
- Similarity = Pearson correlation over the learning period, all pairs, across all languages.
- Neighbours of i = top 10 marbles by similarity, keeping only those with correlation >= 0.15.
  Marbles with fewer than 3 such neighbours are excluded from ripple tests.
- Leak canary: the map-building code asserts that its max date < 2020-01-01.

## Test period: 2020-01-01 .. 2023-12-31

## Matched random comparison
For each jump of marble i at day t, draw 10 random marbles that are not neighbours of i and not i,
from the same language and the same decile of 2015–2019 raw-jump rate. Their "new jump" rate in the
same window t+1..t+14 is the expected rate.
Lift = (neighbour new-jump rate) / (matched random new-jump rate), pooled over all jumps.
Confidence intervals: block bootstrap by calendar month, 2000 resamples, 95%.

## Hypotheses (decided now)
- H1 RIPPLE: for filtered jumps in 2020–2023, lift > 1. Pass if the 95% CI lower bound > 1.
- H2 FILTER ADDS VALUE: lift(filtered jumps) - lift(raw jumps that fail the filter) > 0.
  Pass if the 95% CI lower bound > 0.
- H3 REPEAT: marbles that had >= 1 rippling filtered jump in 2015–2019 (rippling = at least 2
  neighbours make new jumps in t+1..t+14) have a higher rate of rippling filtered jumps per year in
  2020–2023 than marbles that had filtered jumps in 2015–2019 but none rippling.
  Pass if rate ratio 95% CI (bootstrap over marbles) lower bound > 1.
  (For H3 the 2015–2019 ripple label uses the map, which was learned on 2015–2019. That label is
  only used to SPLIT marbles; the outcome is measured on 2020–2023 only.)

## Traps (each must FAIL to show an effect)
- T1 SHUFFLED MAP: neighbours replaced by random marbles matched on language and jump-rate decile
  (200 shuffles). Expected lift ~ 1.
- T2 FAKE DATES (check 4): each filtered jump moved to a random day in 2020–2023 for the same marble
  (keeping >= 30 days from any real jump). Expected lift ~ 1.
- T3 TIME-BROKEN MAP: map learned after shifting each marble's series by a random 60–600 days
  (circular, within the learning period). Expected lift ~ 1.
If a trap shows a lift whose CI excludes 1, the main result is reported as untrustworthy.

## What this trial can NOT show (stated in advance)
- It cannot tell "A pushes B" from "the same news reaches B a few days later".
  A pass means: filtered exceptions predict WHERE the next disturbances appear. Not causation.
- Wikipedia attention is only one kind of marble (attention). No opinion, no sales.
- Languages stand in for countries.
- One sample of 7500 articles out of millions. Not the whole web.

## Report
All numbers for H1–H3 and T1–T3, whether they pass or fail, plus the number of jumps in each group.

## AMENDMENTS
- A1 (2026-10-25, before any data downloaded): scale s_t uses the rolling interquartile range / 1.349
  over t-365..t-1 instead of a rolling MAD. Reason: same robust scale, but a rolling MAD cannot be
  computed for 7500 x 3100 cells in reasonable time.
- A2 (2026-10-25, before any data downloaded): z is left empty until the article has >= 60 days with
  views in the prior 365 days. Reason: articles that did not exist yet would give fake jumps.
- A3 (2026-10-25, before any data downloaded): baseline median needs >= 20 of its 28 days and the
  scale needs >= 120 of its 365 days; edit expectation uses days t-90..t-2 with >= 30 days.
- A4 (2026-10-25, during download, before any series is analysed): the Wikimedia API has no monthly
  top list for some months (e.g. 2015-12 returns 404). Those months are skipped when building the
  universe; this only changes which articles are eligible, not any test.
- A5 (2026-10-25, during download, before any series is analysed): sample cut from 1500 to 1000 per
  language (the first 1000 of the same seed-42 shuffle), because Wikimedia rate limits make 1500 take
  most of a day. Target becomes ~5000 marbles.
