# Talzin — Exception filter trial v0.2 (pre-registration)

Written 2026-10-25, before any Wikipedia series has been analysed. Test size stays ~5000 marbles
(Foivos's choice, 2026-10-25), so the run happens once downloads finish. It replaces v0.1
(PREREG_FILTER.md, SHA 30abc4bf…, amendments A1–A5 still apply unless changed here).
Why v0.2: a methods review (filter/research/METHODS_RESEARCH.md) found that v0.1 could pass
with no ripple at all (comparators matched to the wrong marble; a trap that was true by
construction; size and count confounds in H2 and H3). Every change below makes the test
harder or more informative. Code: run_filter_v02.py. The 2024–2025 lock still holds.

## Prior knowledge (what we knew before looking)
- We have looked at NO Wikipedia view/edit series for these articles. Only download counts were checked.
- We know from the literature that related articles co-move through hyperlinks and shared news
  (Kummer, ZEW; Gildersleve et al. 2022), that bots inflate views in groups of related titles, and
  that the "user" agent label changed on 2020-04-29. These are the reasons for B4, B5, B6.
- We ran the pipeline on synthetic worlds only (see Checks before the real run).

## Data (changes from v0.1)
- Views: agent = user, as v0.1.
- Edits for check 6: HUMAN edits only = editor type 'user' (registered human editors). Bot editor types
  are excluded; anonymous (IP) edits are also left out to halve the downloads (stricter, not looser). (B6)
- Rival map data: each sampled article's CURRENT outgoing article links (MediaWiki API).
  Current links include links added after 2019, which can only help the rival. (B4)

## Jumps and filter: unchanged from v0.1, except edits = human edits.

## Map ("near"), learned on 2015-07-01..2019-12-31 only
- Same correlation of 3-day-smoothed, clipped zc as v0.1. Top 10 per marble with r >= 0.15 AND
  r above that marble's own 99th percentile of null correlations, where the null comes from three
  non-wrapping time-shifted copies of the learning data (each marble's window starts at its own
  offset of 60–300 or 430–600 days, so annual seasonality cannot realign). (B12, B7)
- Marbles with fewer than 3 neighbours are left out of ripple tests (as v0.1).

## The core statistic (B1 + B2)
For a jump of marble i at day t:
- NJ(j, d) = 1 if neighbour j makes a new jump (zc >= 3) in d+1..d+14 with none in d-7..d.
- Neighbour rate n(d) = mean over neighbours j of NJ(j, d).
- Matched rate m(d) = mean over neighbours j of the mean NJ over 5 random marbles drawn from
  j's OWN language and j's OWN 2015–2019 jump-rate decile (excluding i, i's neighbours and j). (B1)
- excess(d) = n(d) - m(d).
- 20 fake dates per jump: random days of the same period, at least 30 days from any jump of i.
- DiD = excess(real date) - mean excess(fake dates). (B2)
- Lift_adj = [n/m on real dates] / [n/m on fake dates] (reported; used for the SESOI).
- Pooled over jumps (equal weight). CI: two-way bootstrap (calendar month x focal marble),
  2000 resamples; the reported CI is the wider of the month-only and the two-way CI. (B11)

## Hypotheses, tested in fixed order (B9). A later one counts only if the earlier ones pass.
- H1 RIPPLE (2020–2023 filtered jumps): pass if the DiD CI lower bound > 0.
  Smallest effect of interest (SESOI): Lift_adj = 1.10. If the whole Lift_adj CI is below 1.10 we
  report "no ripple of practically relevant size" (an informative fail), not just "failed". (B10)
- H2 FILTER ADDS VALUE: DiD(filtered) - DiD(failing raw jumps), where failing jumps are reweighted
  to the filtered jumps' distribution of jump size (zc at t, 5 bins) x persistence (post-14 mean,
  5 bins). Pass if the CI lower bound > 0. (B8)
- H3 REPEAT: marbles whose 2015–2019 filtered jumps rippled (>= 2 neighbour new-jumps beyond the
  fake-date expectation) vs marbles with filtered jumps that never rippled. Outcome = SHARE of their
  2020–2023 filtered jumps that ripple, compared within quartiles of 2015–2019 filtered-jump count.
  Pass if the ratio's CI (bootstrap over marbles) lower bound > 1. (B8)
- H4 BEATS LINKS (gated on H1): map neighbours that are NOT hyperlinked to i (either direction)
  still have DiD CI lower bound > 0. Also reported: the link map alone and the union, and the share
  of map edges that are links. (B4)

## Traps (each must show no effect)
- T1' SWAPPED LISTS: each marble gets the neighbour list of another marble of the same language and
  decile (100 repetitions). Keeps what kind of marbles neighbours are; breaks the i-specific link. (B3)
- T3 TIME-BROKEN MAP: map learned on non-wrapping time-shifted data (no ~365-day shifts). (B7)
- T4 NEIGHBOUR TIMING SHIFT: each neighbour's (and its matched randoms') jump train is read
  60–300 days earlier or later. Keeps burstiness and seasonality; breaks timing. (B3)
- (v0.1's fake dates are now inside the core statistic.)
- Trap rule (B9): a trap invalidates the result only if its CI excludes 0 AND its size is at least
  25% of the main DiD. All trap numbers are reported regardless. With 3 traps there is about a 14%
  chance one fires by luck; that is accepted and stated.

## Checks before the real run (done on synthetic worlds, no real data)
- Ripple world (true ripples): must pass H1, traps quiet.
- Confound world (same-day shared news + jumpier cluster members, no ripple): H1 must NOT pass.
- Power: worlds with weak ripples, to know what size the test can see (minimum detectable effect).
- Positive control (P1): in the real run, a second copy with planted neighbour jumps in 5% of
  real-jump windows must raise the DiD by about the planted amount. If it does not, the pipeline
  is broken and the main result is not reported as a result. (B10)

## Sensitivity and extra reports
- S1: test period from 2020-05-01 (after the bot-label change). If H1 passes only with Jan–Apr 2020,
  it is reported as fragile. (B5a)
- Lag profile of neighbour hits by day 1..14 (a day-1 peak suggests shared news / link spillover).
- Absolute excess (extra neighbour jumps per filtered jump), distinct neighbours, top-10 hub share.
- Mean decile of neighbours vs focal marbles.

## Negative-control marbles (NC), only if their data is downloaded before this plan is frozen
Daily nature series (sunspots, earthquake counts, city weather) added as extra marbles to the map.
Report: how many get map neighbours; DiD for jumps of NC marbles (expected about 0). If NC data is
not available at freeze time this section is skipped and that is reported.

## Contingencies
- Fewer than 100 filtered test jumps: H1 reported as "underpowered", with the synthetic power numbers.
- A decile pool with fewer than 10 marbles: merge with neighbouring deciles.
- Link data missing for more than half the marbles: H4 not run, reported as missing.

## What this trial still cannot show
- "A pushes B" vs "the same news reaches B a few days later" (pass = predicts WHERE next
  disturbances appear, not causation). Attention only. Languages, not countries. 5000 of millions.

## Not done in v0.2 (logged with reason)
- Bot flag from desktop/mobile share on jump days (B5b): needs ~10,000 more downloads through a
  rate-limited connection. Partly covered by S1 and human-only edits.
- Specification curve over thresholds (B14): run afterwards, labelled exploratory.
- Independent public timestamp of this file's hash (B13): to be posted by Foivos (OSF or a public
  commit) before the run.


## Synthetic check results (2026-10-25, no real data; small worlds of 600 marbles)
- Ripple world (true ripples, 60% of followers): H1 DiD 0.148, CI 0.126 to 0.170, pass. Traps quiet.
- Confound world (same-day shared news + jumpier clusters, NO ripple): H1 DiD -0.002, CI -0.018 to
  0.013, correctly NOT passed. (v0.1's statistic gave a biased lift of 0.87 with its fake-date trap
  also off 1, confirming the review.)
- Positive control: 5% planted neighbour jumps -> DiD 0.040 (CI 0.023 to 0.056), close to the
  ~0.045 planted. Recovered.
- Power at this small size: weak ripples (5–15% of followers) were NOT detected (two-way CIs
  include 0). Minimum detectable DiD here is about 0.03. The real run has ~8x more marbles, so
  the CI should be roughly 2–3x narrower (estimate, not measured).

## Exploratory (anything not listed above is exploratory and will be labelled as such)

## AMENDMENTS to v0.2
(none yet)
