"""Talzin exception filter trial v0.3 — follows PREREG_FILTER_v03.md.
Usage: python run_filter_v03.py <dir with pack_*.json.gz> <out dir> [--fast] [--no-plant]
  --fast     : fewer bootstrap / trap repetitions (synthetic checks only, never the real run)
  --no-plant : skip the planted positive-control copy (synthetic speed only)
"""
import gzip, hashlib, json, os, sys
import numpy as np, pandas as pd
from scipy.stats import poisson

ARGS = sys.argv[1:]
SRC, OUTD = ARGS[0], ARGS[1]
FAST = "--fast" in ARGS
B = 300 if FAST else 2000
K_FAKE, R_PER_NB, PLANT = 20, 5, 0.05
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUTD, exist_ok=True)
LOG = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.append(s)
def sha(p):
    try: return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception: return None

# ---------------- load ----------------
titles, langs, V, EH, LK, ALIAS = [], [], [], [], [], []
start = None
for lang in ["de", "fr", "nl", "pl", "cs"]:
    fn = os.path.join(SRC, f"pack_{lang}.json.gz")
    if not os.path.exists(fn): continue
    d = json.load(gzip.open(fn, "rt")); start = d["start"]
    n = len(d["titles"])
    titles += d["titles"]; langs += [lang] * n
    V.append(np.array(d["views"], dtype=np.float32))
    EH.append(np.array(d["edits_human"], dtype=np.float32))
    LK += d.get("links_now") or [None] * n
    ALIAS += d.get("aliases") or [None] * n
V = np.vstack(V).T; EH = np.vstack(EH).T
langs = np.array(langs); N = V.shape[1]; T = V.shape[0]
dates = pd.date_range(pd.Timestamp(start), periods=T, freq="D")
assert dates.max() < pd.Timestamp("2024-01-01"), "LOCK: 2024+ data present"
LEARN_END = int(np.searchsorted(dates, pd.Timestamp("2020-01-01")))
TEST_START = LEARN_END
SENS_START = int(np.searchsorted(dates, pd.Timestamp("2020-05-01")))
log(f"marbles {N}, days {T}", dict(zip(*np.unique(langs, return_counts=True))))

# ---------------- preprocessing (past-only) ----------------
def prep(Vm, Em):
    y = pd.DataFrame(np.log1p(Vm))
    b = y.rolling(28, min_periods=20).median().shift(1)
    r = y - b
    q75 = r.rolling(365, min_periods=120).quantile(0.75).shift(1)
    q25 = r.rolling(365, min_periods=120).quantile(0.25).shift(1)
    s = ((q75 - q25) / 1.349).clip(lower=0.05)
    alive = (pd.DataFrame(Vm) > 0).rolling(365, min_periods=1).sum().shift(1) >= 60
    z = (r / s).where(alive).to_numpy(np.float32)
    zc = np.full_like(z, np.nan)
    for L in np.unique(langs):
        m = langs == L
        zc[:, m] = z[:, m] - np.nanmedian(z[:, m], axis=1)[:, None]
    return z, zc
z, zc = prep(V, EH)
zcf = np.nan_to_num(zc)
# leak canary (C1): learning-period zc must not change when all 2020+ rows are removed
_zl, _zcl = prep(V[:LEARN_END], EH[:LEARN_END])
assert np.allclose(np.nan_to_num(_zcl), zcf[:LEARN_END], atol=1e-4), "LEAK: learning-period values depend on 2020+ data"
del _zl, _zcl
FIRST_OK = int(np.argmax((np.isfinite(zc).mean(1) > 0.5)))   # first day most marbles have zc
Ed = pd.DataFrame(EH)
e5 = np.nan_to_num(Ed.rolling(5).sum().shift(-3).to_numpy())
expct = np.nan_to_num((5 * Ed.rolling(89, min_periods=30).mean().shift(2)).clip(lower=0.25).to_numpy(), nan=0.25)
burst = (poisson.sf(e5 - 1, expct) < 0.01) & (e5 >= 3)
cs = np.vstack([np.zeros((1, N)), np.cumsum(zcf, axis=0)])
post14 = np.full_like(zc, np.nan); post14[:T - 13] = (cs[14:] - cs[:T - 13]) / 14

# ---------------- jumps ----------------
H3m = np.nan_to_num(z) >= 3
cH = np.vstack([np.zeros((1, N), dtype=np.int32), np.cumsum(H3m, axis=0, dtype=np.int32)])
def any_in(cum, a, bnd, j):
    a = np.clip(a, 0, T); bnd = np.clip(bnd, 0, T); return (cum[bnd, j] - cum[a, j]) > 0
tt, jj = np.nonzero(H3m)
quiet = ~any_in(cH, tt - 14, tt, jj)
raw = pd.DataFrame({"t": tt[quiet], "i": jj[quiet]})
raw["zc"] = zcf[raw.t, raw.i]; raw["p14"] = np.nan_to_num(post14[raw.t, raw.i])
raw["filt"] = (raw.zc >= 4) & (raw.p14 >= 1) & burst[raw.t, raw.i]
log(f"raw jumps {len(raw)}, filtered {int(raw.filt.sum())}")
hotdays = {i: np.nonzero(H3m[:, i])[0] for i in range(N)}    # all z>=3 days, for fake-date spacing (MI-9)

# ---------------- map (learning period only) ----------------
Xl = np.clip(zcf[:LEARN_END], -5, 5)
Xl = pd.DataFrame(Xl).rolling(3, center=True, min_periods=1).mean().to_numpy(np.float32)
def standard(X): return (X - X.mean(0)) / (X.std(0) + 1e-6)
def corr(X):
    X = standard(X); C = (X.T @ X) / X.shape[0]; np.fill_diagonal(C, np.nan); return C
def shifted(X, seed):
    """non-wrapping per-marble time shift; offsets from 4 well-separated groups so most pairwise
    differences are >= 60 days and away from 365 +- 30 (MI-2). Same-group pairs are re-drawn each seed."""
    g = np.random.default_rng(seed); Lw = X.shape[0] - 600
    base = np.array([0, 120, 240, 520])            # pairwise diffs 120,240,520,120,400,280: none near 365
    offs = base[g.integers(0, 4, N)] + g.integers(0, 60, N)
    offs = np.minimum(offs, X.shape[0] - Lw)
    idx = offs[None, :] + np.arange(Lw)[:, None]
    return np.take_along_axis(X, idx, axis=0)
C = corr(Xl)
null99 = np.nanpercentile(np.hstack([corr(shifted(Xl, sd)) for sd in (101, 102, 103)]), 99, axis=1)
def topk(Cm, floor):
    Cm = np.nan_to_num(Cm, nan=-1)
    nb = np.argsort(-Cm, axis=1)[:, :10]
    val = np.take_along_axis(Cm, nb, axis=1)
    ok = (val >= 0.15) & (val > floor[:, None])
    return [nb[k][ok[k]] for k in range(N)]
nbrs = topk(C, null99)
nb_count = np.array([len(n) for n in nbrs])
log(f"map: neighbours after null floor {nb_count.sum()}, marbles with >=3 neighbours {(nb_count >= 3).sum()}")
# learned direction of each map edge (H5): lead(i->j) = corr(x_i[t], mean x_j[t+1..t+7]) - reverse
Xs = standard(Xl)
fwd = pd.DataFrame(Xs).rolling(7, min_periods=7).mean().shift(-7).to_numpy(np.float32)
okr = np.isfinite(fwd).all(1)
LEAD = (Xs[okr].T @ standard(fwd[okr])) / okr.sum()      # LEAD[i, j] = i now vs j next week
DIRN = LEAD - LEAD.T

# hyperlink map (rival): only marbles with link data count (BL-2); titles resolved through aliases
tindex = {}
for k in range(N):
    tindex[(langs[k], titles[k])] = k
    for a in (ALIAS[k] or []): tindex.setdefault((langs[k], a), k)
has_links = np.array([LK[k] is not None for k in range(N)])
Lmap = [set() for _ in range(N)]
for k in range(N):
    for t2 in (LK[k] or []):
        j = tindex.get((langs[k], t2))
        if j is not None and j != k:
            Lmap[k].add(j); Lmap[j].add(k)
log(f"link map: marbles with link data {has_links.sum()}, linked pairs {sum(len(x) for x in Lmap)//2}")

# jump-rate deciles (2015–2019)
learn_raw = raw[raw.t < LEARN_END]
act_years = np.maximum(np.isfinite(z[:LEARN_END]).sum(0) / 365, 0.25)
rate = np.bincount(learn_raw.i, minlength=N) / act_years
dec = np.zeros(N, int)
for L in np.unique(langs):
    m = np.where(langs == L)[0]
    dec[m] = pd.qcut(rate[m], 10, labels=False, duplicates="drop")
def pool(L, d):
    p = np.where((langs == L) & (dec == d))[0]; lo, hi = d, d
    while len(p) < 10 and (lo > 0 or hi < 9):
        lo, hi = max(0, lo - 1), min(9, hi + 1)
        p = np.where((langs == L) & (dec >= lo) & (dec <= hi))[0]
    return p
POOLS = {(L, d): pool(L, d) for L in np.unique(langs) for d in range(10)}

# ---------------- evaluation machinery ----------------
Hc0 = zcf >= 3
STATE = {}
def set_hc(Hc):
    STATE["cum"] = np.vstack([np.zeros((1, N), dtype=np.int32), np.cumsum(Hc, axis=0, dtype=np.int32)])
def NJ(dts, js, before=False):
    """after: j new-jumps in d+1..d+14, none in d-7..d.  before (mirror): j new-jumps in d-14..d-1, none in d-21..d-15."""
    cum = STATE["cum"]; dts = np.asarray(dts); js = np.asarray(js)
    if not before:
        ok = (dts - 7 >= 0) & (dts + 15 <= T)
        out = any_in(cum, dts + 1, dts + 15, js) & ~any_in(cum, dts - 7, dts + 1, js)
    else:
        ok = (dts - 21 >= 0) & (dts + 1 <= T)
        out = any_in(cum, dts - 14, dts, js) & ~any_in(cum, dts - 21, dts - 14, js)
    return np.where(ok, out.astype(float), np.nan)

def fake_dates(rg, i, t, lo, hi, k, local):
    """local=True (primary, B-L): 30-90 days before or after t. local=False: anywhere in lo..hi.
    Always >= 30 days from ANY z>=3 day of i (MI-9)."""
    hd = hotdays[i]; out = []
    for _ in range(k * 40):
        f = int(t + rg.choice([-1, 1]) * rg.integers(30, 91)) if local else int(rg.integers(lo, hi))
        if f < lo or f >= hi: continue
        if hd.size == 0 or np.min(np.abs(hd - f)) >= 30: out.append(f)
        if len(out) == k: break
    return out

def draw_randoms(rg, i, nb):
    excl = set(nb.tolist()) | {i}; rr = []
    for j in nb:
        p = POOLS[(langs[j], dec[j])]; p = p[~np.isin(p, list(excl | {j}))]
        rr.append(rg.choice(p, size=min(R_PER_NB, len(p)), replace=False))
    return rr

def evaluate(J, nb_list, lo, hi, shift_nb=None, local=True, before=False, seed=1, keep_fakes=False):
    rg = np.random.default_rng(seed)
    rows = []
    for t, i in zip(J.t.to_numpy(), J.i.to_numpy()):
        nb = np.asarray(nb_list[i], dtype=int)
        if len(nb) < 3: continue
        fk = fake_dates(rg, i, t, lo, hi, K_FAKE, local)
        if len(fk) < 5: continue
        rr = draw_randoms(rg, i, nb)
        keep = np.array([len(x) > 0 for x in rr])             # MI-5: drop neighbours with empty pools from both
        nb2 = nb[keep]; rr2 = [x for x, k_ in zip(rr, keep) if k_]
        if len(nb2) < 3: continue
        sh = np.zeros(len(nb2), int) if shift_nb is None else shift_nb[nb2]
        def exc(d):
            dn = d + sh
            a = NJ(dn, nb2, before)
            m = np.array([np.nanmean(NJ(np.full(len(rx), dn[q]), rx, before)) for q, rx in enumerate(rr2)])
            return np.nanmean(a), np.nanmean(m), np.nansum(a)
        n0, m0, h0 = exc(t)
        fx = [exc(f) for f in fk]
        nf = np.nanmean([x[0] for x in fx]); mf = np.nanmean([x[1] for x in fx])
        hf = np.array([x[2] for x in fx])
        rows.append((t, i, dates[t].year * 12 + dates[t].month, n0, m0, nf, mf, len(nb2), h0,
                     float(np.nanpercentile(hf, 95)) if np.isfinite(hf).any() else np.nan,
                     float(np.nanmean(hf >= h0)) if np.isfinite(hf).any() else np.nan))
    df = pd.DataFrame(rows, columns=["t", "i", "mon", "n0", "m0", "nf", "mf", "k", "h0", "hf95", "pfake"])
    df["did"] = (df.n0 - df.m0) - (df.nf - df.mf)
    return df

def lift_adj(df):
    if "m0" not in df: return np.nan
    l0 = df.n0.mean() / df.m0.mean() if df.m0.mean() > 0 else np.nan
    lf = df.nf.mean() / df.mf.mean() if df.mf.mean() > 0 else np.nan
    return l0 / lf if lf and np.isfinite(lf) and lf > 0 else np.nan
def boot2(df, f, Bn=None, seed=11, q=(2.5, 97.5)):
    Bn = Bn or B; rg = np.random.default_rng(seed)
    if len(df) < 10: return [np.nan, np.nan], [np.nan, np.nan]
    mons = df.mon.unique(); mars = df.i.unique()
    mi = pd.Index(mons).get_indexer(df.mon); ai = pd.Index(mars).get_indexer(df.i)
    o1, o2 = [], []
    for _ in range(Bn):
        wm = np.bincount(rg.integers(0, len(mons), len(mons)), minlength=len(mons))[mi]
        wa = np.bincount(rg.integers(0, len(mars), len(mars)), minlength=len(mars))[ai]
        for w, o in ((wm, o1), (wm * wa, o2)):
            sel = df.loc[df.index.repeat(w)]
            o.append(f(sel) if len(sel) else np.nan)
    return np.nanpercentile(o1, list(q)).tolist(), np.nanpercentile(o2, list(q)).tolist()
QB = (0.625, 99.375)   # Bonferroni over the four follow-up hypotheses H2-H5 (alpha 0.05/4)
def wide(a, b): return [min(a[0], b[0]), max(a[1], b[1])]
meandid = lambda df: df.did.mean()
def summary(df, name, q=(2.5, 97.5)):
    if len(df) < 10:
        out = {"n": int(len(df)), "not_run": True}; log(name, out); return out
    c1, c2 = boot2(df, meandid, q=q)
    l1, l2 = boot2(df, lift_adj, Bn=max(200, B // 4)) if "m0" in df else ([np.nan] * 2, [np.nan] * 2)
    out = dict(n=int(len(df)), did=float(df.did.mean()), ci=wide(c1, c2), ci_month=c1, ci_twoway=c2,
               lift_adj=float(lift_adj(df)), lift_adj_ci=wide(l1, l2),
               extra_neighbour_jumps_per_jump=float((df.did * df.k).mean()) if "k" in df else None)
    log(name, json.dumps(out, default=float))
    return out
def in_window(J, lo): return J[(J.t >= lo) & (J.t + 14 < T)]

# ---------------- main run ----------------
set_hc(Hc0)
R = {"prereg": "PREREG_FILTER_v03.md", "fast": FAST, "B": B, "K_FAKE": K_FAKE,
     "sha_plan": sha(os.path.join(HERE, "PREREG_FILTER_v03.md")), "sha_code": sha(os.path.abspath(__file__))}
filt_T = in_window(raw[raw.filt], TEST_START); fail_T = in_window(raw[~raw.filt], TEST_START)
TLO, THI = TEST_START, T - 15

# H1 (primary: local fake dates)
ef = evaluate(filt_T, nbrs, TLO, THI, local=True)
R["H1"] = summary(ef, "H1 (local fake dates)")
R["counts"] = dict(filtered_test=len(filt_T), evaluated=len(ef), failing_test=len(fail_T), underpowered=len(ef) < 100)
R["H1"]["pass"] = bool(not R["H1"].get("not_run") and R["H1"]["ci"][0] > 0)
if R["H1"].get("lift_adj_ci") and np.isfinite(R["H1"]["lift_adj_ci"][1]) and R["H1"]["lift_adj_ci"][1] < 1.10:
    R["H1"]["equivalence"] = "no ripple of practically relevant size (CI below SESOI 1.10)"
if R["counts"]["underpowered"]: R["H1"]["label"] = "underpowered"
R["H1"]["mean_decile_neighbours"] = float(np.mean([dec[j] for i in ef.i for j in nbrs[i]])) if len(ef) else None
R["H1"]["mean_decile_focal"] = float(dec[ef.i].mean()) if len(ef) else None
R["H1_global_fake_dates"] = summary(evaluate(filt_T, nbrs, TLO, THI, local=False, seed=2), "H1 secondary (global fake dates)")
R["before_window"] = summary(evaluate(filt_T, nbrs, TLO, THI, local=True, before=True, seed=1), "before-window (mirror)")

# H2 (fixed order): edit-burst check adds value, on common support of size x persistence (SF-5)
zb = [4, 4.5, 5, 6, 8, np.inf]; pb = [1, 1.5, 2, 3, np.inf]
fail_big = fail_T[(raw.loc[fail_T.index, "zc"] >= 4) & (raw.loc[fail_T.index, "p14"] >= 1)]
eu = evaluate(fail_big, nbrs, TLO, THI, local=True, seed=3)
def cells(df):
    s = raw.set_index(["t", "i"]).loc[list(zip(df.t, df.i)), ["zc", "p14"]].to_numpy()
    return np.digitize(s[:, 0], zb[1:-1]) * 10 + np.digitize(s[:, 1], pb[1:-1])
if len(ef) >= 10 and len(eu) >= 10:
    ef["cell"] = cells(ef); eu["cell"] = cells(eu)
    common = set(ef.cell) & set(eu.cell)
    a = ef[ef.cell.isin(common)].copy(); c = eu[eu.cell.isin(common)].copy()
    tf = a.cell.value_counts(normalize=True); tu = c.cell.value_counts(normalize=True)
    c["w"] = [tf[x] / tu[x] for x in c.cell]; a["w"] = 1.0
    both = pd.concat([a.assign(g=1), c.assign(g=0)], ignore_index=True)
    def dd(df):
        x = df[df.g == 1]; y_ = df[df.g == 0]
        if len(x) == 0 or y_.w.sum() == 0: return np.nan
        return x.did.mean() - np.average(y_.did, weights=y_.w)
    c1, c2 = boot2(both, dd, q=QB)
    R["H2"] = dict(what="filtered jumps vs same-size jumps that failed only the edit-burst check",
                   n_filtered_common=len(a), n_filtered_dropped=int(len(ef) - len(a)), n_fail=len(c),
                   diff=float(dd(both)), ci=wide(c1, c2))
    R["H2"]["pass"] = bool(R["H1"]["pass"] and R["H2"]["ci"][0] > 0)
else:
    R["H2"] = {"not_run": True, "n_fail": int(len(eu))}
log("H2", json.dumps(R["H2"], default=float))

# H3 (fixed order): repeat, judged per jump against its OWN fake dates (BL-1), permutation-calibrated
learn_f = in_window(raw[raw.filt & (raw.t < LEARN_END - 15) & (raw.t >= FIRST_OK + 90)], 0)
el = evaluate(learn_f, nbrs, FIRST_OK, LEARN_END - 15, local=True, seed=4)
if len(el) >= 10 and len(ef) >= 10:
    rip = lambda df: (df.h0 > df.hf95)                       # beats 95th pct of own fake-date counts
    lg = el.assign(rp=rip(el)).groupby("i").agg(n=("rp", "size"), r=("rp", "sum"), k=("k", "mean"))
    tg = ef.assign(rp=rip(ef)).groupby("i").agg(n_t=("rp", "size"), r_t=("rp", "sum"))
    lg = lg.join(tg, how="inner")
    lg["grp"] = (lg.r >= 1).astype(int)
    lg["stratum"] = pd.qcut(lg.n.rank(method="first"), 3, labels=False) * 10 + pd.qcut(lg.k.rank(method="first"), 3, labels=False)
    lg["share_t"] = lg.r_t / lg.n_t
    def diff(d):
        rs = []
        for _, g in d.groupby("stratum"):
            x, y_ = g[g.grp == 1].share_t, g[g.grp == 0].share_t
            if len(x) and len(y_): rs.append((x.mean() - y_.mean(), len(g)))
        return np.average([r_[0] for r_ in rs], weights=[r_[1] for r_ in rs]) if rs else np.nan
    obs = diff(lg); rg = np.random.default_rng(5)
    perm = []
    for _ in range(B):
        p = lg.copy(); p["grp"] = p.groupby("stratum").grp.transform(lambda s: rg.permutation(s.values)); perm.append(diff(p))
    bs = [diff(lg.sample(len(lg), replace=True, random_state=int(rg.integers(1e9)))) for _ in range(B)]
    R["H3"] = dict(nA=int(lg.grp.sum()), nB=int((lg.grp == 0).sum()), share_diff=float(obs),
                   ci=np.nanpercentile(bs, list(QB)).tolist(),
                   perm_p=float((1 + np.sum(np.array(perm) >= obs)) / (1 + len(perm))))
    R["H3"]["pass"] = bool(R["H2"].get("pass", False) and R["H3"]["ci"][0] > 0 and R["H3"]["perm_p"] < 0.0125)
else:
    R["H3"] = {"not_run": True}
log("H3", json.dumps(R["H3"], default=float))

# H4 (gated on H1): map-only neighbours, both ends with link data (BL-2)
if has_links.mean() > 0.5:
    maponly = [np.array([j for j in nbrs[k] if has_links[k] and has_links[j] and j not in Lmap[k]], dtype=int) for k in range(N)]
    dropped = int(sum(1 for k in range(N) for j in nbrs[k] if not (has_links[k] and has_links[j])))
    lmap = [np.array(sorted(Lmap[k]), dtype=int) if has_links[k] else np.array([], int) for k in range(N)]
    R["H4_maponly"] = summary(evaluate(filt_T, maponly, TLO, THI, seed=6), "H4 map-only", q=QB)
    R["H4_maponly"]["edges_dropped_no_link_data"] = dropped
    R["H4_maponly"]["pass"] = bool(R["H1"]["pass"] and not R["H4_maponly"].get("not_run") and R["H4_maponly"]["ci"][0] > 0)
    R["linkmap"] = summary(evaluate(filt_T, lmap, TLO, THI, seed=7), "link map")
    chk = [(k, j) for k in range(N) for j in nbrs[k] if has_links[k] and has_links[j]]
    R["share_map_edges_linked"] = float(np.mean([j in Lmap[k] for k, j in chk])) if chk else None
else:
    R["H4_maponly"] = {"not_run": True, "note": "link data missing for most marbles"}

# H5 (gated on H1): direction. Neighbours the map says i LEADS vs neighbours that lead i
if R["H1"]["pass"] or FAST:
    lead_nb = [np.array([j for j in nbrs[k] if DIRN[k, j] > 0], dtype=int) for k in range(N)]
    lag_nb = [np.array([j for j in nbrs[k] if DIRN[k, j] < 0], dtype=int) for k in range(N)]
    eA = evaluate(filt_T, lead_nb, TLO, THI, seed=8); eB = evaluate(filt_T, lag_nb, TLO, THI, seed=9)
    if len(eA) >= 10 and len(eB) >= 10:
        both5 = pd.concat([eA.assign(g=1), eB.assign(g=0)], ignore_index=True)
        d5 = lambda df: df[df.g == 1].did.mean() - df[df.g == 0].did.mean()
        c1, c2 = boot2(both5, d5, q=QB)
        R["H5"] = dict(did_i_leads=float(eA.did.mean()), did_j_leads=float(eB.did.mean()), diff=float(d5(both5)), ci=wide(c1, c2),
                       nA=len(eA), nB=len(eB))
        R["H5"]["pass"] = bool(R["H1"]["pass"] and R["H5"]["ci"][0] > 0)
    else:
        R["H5"] = {"not_run": True}
    log("H5", json.dumps(R["H5"], default=float))

# ---------------- traps ----------------
traps = {}
rg = np.random.default_rng(21)
reps = 5 if FAST else 20
per_jump = []
for rep in range(reps):      # T1': swapped neighbour lists; per-jump DiD averaged over reps, then one bootstrap (SF-3)
    sw = []
    for k in range(N):
        p = POOLS[(langs[k], dec[k])]; p = p[p != k]
        cand = [c for c in p if k not in set(nbrs[c].tolist())]
        sw.append(nbrs[rg.choice(cand)] if cand else np.array([], int))
    e = evaluate(filt_T, sw, TLO, THI, seed=100 + rep)
    per_jump.append(e.set_index(["t", "i"])[["did", "mon"]])
if per_jump:
    pj = pd.concat(per_jump).groupby(level=[0, 1]).agg(did=("did", "mean"), mon=("mon", "first")).reset_index()
    traps["T1p"] = summary(pj, "T1' swapped lists")
traps["T3"] = summary(evaluate(filt_T, topk(corr(shifted(Xl, 999)), null99), TLO, THI, seed=31), "T3 time-broken map")
shift_nb = rg.integers(60, 301, N) * rg.choice([-1, 1], N)
traps["T4"] = summary(evaluate(filt_T, nbrs, TLO, THI, shift_nb=shift_nb, seed=32), "T4 neighbour timing shift")
main = R["H1"].get("did", 0) or 0
def fires(tr):
    if tr.get("not_run") or not tr.get("ci") or not np.all(np.isfinite(tr["ci"])): return "not_run"
    return bool((tr["ci"][0] > 0 or tr["ci"][1] < 0) and abs(tr["did"]) >= 0.25 * abs(main))
R["traps"] = traps; R["trap_fired"] = {k: fires(v) for k, v in traps.items()}
R["result_trustworthy"] = all(v is False for v in R["trap_fired"].values())   # SF-4: not_run => not trustworthy
log("traps", json.dumps(R["trap_fired"]))

# ---------------- positive control P1 (SF-2): planted copy, own generator, explicit pass rule ----------------
if "--no-plant" not in ARGS and len(ef) >= 10:
    gp = np.random.default_rng(7); Hp = Hc0.copy(); planted = {}
    for t, i in zip(ef.t, ef.i):
        for j in nbrs[i]:
            if t + 3 < T and gp.random() < PLANT and not Hp[max(0, t - 7):t + 15, j].any():
                Hp[t + 3, j] = True; planted[(t, i)] = planted.get((t, i), 0) + 1
    set_hc(Hp)
    ep = evaluate(filt_T, nbrs, TLO, THI, local=True)     # same J and seed as main H1 -> same fakes/randoms
    set_hc(Hc0)
    m = ef.merge(ep[["t", "i", "did"]], on=["t", "i"], suffixes=("", "_p"))
    expected = float(np.mean([planted.get((t, i), 0) / k for t, i, k in zip(m.t, m.i, m.k)]))
    rise = float((m.did_p - m.did).mean())
    R["P1"] = dict(planted=int(sum(planted.values())), expected_rise=expected, observed_rise=rise,
                   note="a planted jump can count for several focal jumps that share the neighbour, so the rise may exceed the expected value",
                   pass_=bool(expected > 0 and rise >= 0.5 * expected))
    log("P1", json.dumps(R["P1"]))
    if not R["P1"]["pass_"]: R["result_trustworthy"] = False

# ---------------- sensitivity + descriptives ----------------
R["S1_from_2020_05"] = summary(evaluate(in_window(raw[raw.filt], SENS_START), nbrs, SENS_START, THI, seed=41), "S1 from 2020-05-01")
R["S1_fragile"] = bool(R["H1"]["pass"] and not (not R["S1_from_2020_05"].get("not_run") and R["S1_from_2020_05"]["ci"][0] > 0))
R["NC"] = {"skipped": True, "note": "no negative-control marbles in the packs"} if not any(t.startswith("NC:") for t in titles) else {}
Hc = Hc0; lagp = np.zeros(14); cnt = 0
for t, i in zip(ef.t, ef.i):
    nb = nbrs[i]
    if t + 15 > T or t - 7 < 0: continue
    prior = Hc[t - 7:t + 1, nb].any(0); win = Hc[t + 1:t + 15, nb]
    hit = win.any(0) & ~prior
    for f in np.argmax(win, axis=0)[hit]: lagp[f] += 1
    cnt += len(nb)
R["lag_profile_hits_per_1000_neighbours"] = (lagp / max(cnt, 1) * 1000).round(2).tolist()
hubs = pd.Series([j for i in ef.i for j in nbrs[i]]).value_counts() if len(ef) else pd.Series(dtype=int)
R["distinct_neighbours"] = int(hubs.size); R["top10_hub_share"] = float(hubs.head(10).sum() / max(hubs.sum(), 1))
ex = ef.assign(h=ef.did * ef.k).sort_values("h", ascending=False).head(15)
R["examples"] = [dict(marble=f"{langs[i]}:{titles[i]}", date=str(dates[t].date()), neighbours=[f"{langs[j]}:{titles[j]}" for j in nbrs[i][:5]])
                 for t, i in zip(ex.t, ex.i)]
json.dump(R, open(os.path.join(OUTD, "results.json"), "w"), indent=1, default=float)
open(os.path.join(OUTD, "log.txt"), "w").write("\n".join(LOG))
log("DONE")
