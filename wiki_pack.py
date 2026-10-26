"""Pack downloaded wiki marbles into one gzipped JSON per language (stdlib only). v0.2:
views (user agent), edits_all (all editor types, optional), edits_human (registered users only),
links_now and aliases (if present). Only articles with views and human edits present are packed; a sample article missing any file is listed in 'missing'.
Usage: python3 wiki_pack.py [root]   (root defaults to raw/wiki_marbles)
"""
import datetime as dt, gzip, json, os, sys, urllib.parse
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join("raw", "wiki_marbles")
d0, d1 = dt.date(2015, 7, 1), dt.date(2023, 12, 31)
days = [(d0 + dt.timedelta(i)).strftime("%Y%m%d") for i in range((d1 - d0).days + 1)]
def load(f):
    try:
        return json.load(open(f))
    except Exception:
        return None
for lang in ["de", "fr", "nl", "pl", "cs"]:
    p = os.path.join(OUT, lang)
    if not os.path.exists(os.path.join(p, "sample.json")):
        continue
    links = load(os.path.join(p, "links_now.json")) or {}
    aliases = load(os.path.join(p, "aliases.json")) or {}
    titles, V, E, EH, L, A, missing = [], [], [], [], [], [], []
    for t in json.load(open(os.path.join(p, "sample.json"))):
        q = urllib.parse.quote(t, safe="")[:180] + ".json"
        v, e, eu = load(os.path.join(p, "views", q)), load(os.path.join(p, "edits", q)), load(os.path.join(p, "edits_ua", q))
        if v is None or eu is None:
            missing.append(t); continue
        titles.append(t)
        V.append([v.get(x, 0) for x in days])
        E.append([e.get(x, 0) for x in days] if e else None)
        # plan v0.3 + A4: human edits = registered users only; an "anonymous" key, if present, is ignored
        EH.append([eu.get("user", {}).get(x, 0) for x in days])
        L.append(links.get(t)); A.append(aliases.get(t))
    with gzip.open(os.path.join(OUT, f"pack_{lang}.json.gz"), "wt") as f:
        json.dump({"lang": lang, "start": days[0], "titles": titles, "views": V, "edits_all": E,
                   "edits_human": EH, "links_now": L, "aliases": A, "missing": missing}, f)
    print(lang, "packed", len(titles), "missing", len(missing), "with links", sum(x is not None for x in L))
