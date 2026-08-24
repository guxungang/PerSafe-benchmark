# -*- coding: utf-8 -*-
"""Phase 1a — full-口径 corrected content-axis recompute: v2's pharmacist-corrected scenarios + isolation,
now over all 3 framings, with per-model breakdown and scenario-bootstrap CI for the isolated subset.
Gives the definitive corrected '+0.16' for the B benchmark content axis."""
import sys, json, random, os
from concurrent.futures import ThreadPoolExecutor, as_completed
WORKERS = int(os.environ.get("CC_WORKERS", "10"))
sys.path.insert(0, "rebuild")
import knockout_v2 as V2
import router as RT
K = V2.K
cases, scen, ISO, FRAMES = V2.cases, V2.scen, V2.ISO, V2.FRAMES
PANEL = RT.ALL                       # 12-model panel (routed), consistent with B1/B2
framings, lvl, call = V2.framings, V2.lvl, V2.call

def work(t):
    m, si, fr, cond = t
    fam, cid, y, terms, sym = scen[si]
    l1 = K.fmt_L1(cases[cid], drop_terms=terms if cond == "knock" else None)
    return t, call(m, l1, framings(y, sym)[fr])

def main(models=None):
    global PANEL
    models = models or PANEL
    tasks = [(m, si, fr, cond) for m in models for si in range(len(scen)) for fr in FRAMES for cond in ("full", "knock")]
    try: prev = json.load(open("rebuild/_knockout_panel.json", encoding="utf-8"))
    except FileNotFoundError: prev = {}
    todo = [t for t in tasks if f"{t[0]}|{t[1]}|{t[2]}|{t[3]}" not in prev]
    print(f"[v3] {len(scen)} scen x {len(models)} models x {len(FRAMES)} framings x 2 = {len(tasks)} cells; {len(todo)} to run", flush=True)
    out = {}; done = [0]
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for fut in as_completed([ex.submit(work, t) for t in todo]):
            t, r = fut.result(); out[t] = r; done[0] += 1
            if done[0] % 200 == 0: print(f"... {done[0]}/{len(todo)}", flush=True)
    for t in todo: prev[f"{t[0]}|{t[1]}|{t[2]}|{t[3]}"] = out[t]
    json.dump(prev, open("rebuild/_knockout_panel.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    full = {t: prev[f"{t[0]}|{t[1]}|{t[2]}|{t[3]}"] for t in tasks if f"{t[0]}|{t[1]}|{t[2]}|{t[3]}" in prev}
    PANEL = models                                    # report iterates PANEL (declared global at top of main)
    report(full)

def report(out):
    L = []; p = lambda s="": L.append(s)
    isoidx = [i for i in range(len(scen)) if ISO[i][0]]
    nonidx = [i for i in range(len(scen)) if not ISO[i][0]]
    def pair_deltas(idxset):  # all (model,framing) deltas over scenarios in idxset
        ds = []
        for m in PANEL:
            for si in idxset:
                for fr in FRAMES:
                    a = lvl(out[(m, si, fr, 'full')][0]); b = lvl(out[(m, si, fr, 'knock')][0])
                    if a is not None and b is not None: ds.append(a - b)
        return ds
    def mean(xs): return sum(xs) / len(xs) if xs else 0.0
    def scen_mean(si):  # mean delta for one scenario over models x framings
        ds = []
        for m in PANEL:
            for fr in FRAMES:
                a = lvl(out[(m, si, fr, 'full')][0]); b = lvl(out[(m, si, fr, 'knock')][0])
                if a is not None and b is not None: ds.append(a - b)
        return mean(ds) if ds else None
    p("=== v3 FULL corrected content-axis (3 framings, per-model, bootstrap CI) ===")
    p(f"statin = atorvastatin; isolated={len(isoidx)} non-iso={len(nonidx)} scenarios")
    allD = mean(pair_deltas(list(range(len(scen)))))
    isoD = mean(pair_deltas(isoidx)); nonD = mean(pair_deltas(nonidx))
    # scenario-bootstrap CI for isolated
    sm = [scen_mean(i) for i in isoidx]; sm = [x for x in sm if x is not None]
    random.seed(7); boots = []
    for _ in range(2000):
        samp = [sm[random.randrange(len(sm))] for _ in range(len(sm))]
        boots.append(mean(samp))
    boots.sort(); lo, hi = boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]
    p(f"\n  ALL         Δ = {allD:+.3f}")
    p(f"  ISOLATED    Δ = {isoD:+.3f}   95% CI [{lo:+.3f}, {hi:+.3f}]   ({len(isoidx)} scen)   <-- corrected headline")
    p(f"  NON-ISOLATED Δ = {nonD:+.3f}   ({len(nonidx)} scen)")
    p(f"  isolation gap (iso - non) = {isoD - nonD:+.3f}   (old paper: +0.16 vs +0.02 = +0.14 gap)")
    # per-model (isolated)
    p("\n  --- per-model Δ on ISOLATED subset ---")
    npos = 0
    for m in PANEL:
        ds = []
        for si in isoidx:
            for fr in FRAMES:
                a = lvl(out[(m, si, fr, 'full')][0]); b = lvl(out[(m, si, fr, 'knock')][0])
                if a is not None and b is not None: ds.append(a - b)
        md = mean(ds); npos += (md > 0)
        p(f"    {m:18s} {md:+.3f}")
    p(f"  models with Δ>0 (isolated): {npos}/{len(PANEL)}")
    # per-family (isolated)
    p("\n  --- per-family Δ (isolated only) ---")
    for fam in sorted(set(f for f, *_ in scen)):
        idx = [i for i in isoidx if scen[i][0] == fam]
        p(f"    {fam:18s} Δ={mean(pair_deltas(idx)):+.3f}  (n_scen={len(idx)})")
    open("rebuild/_knockout_v3_summary.txt", "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L)); print("[v3] done", flush=True)

if __name__ == "__main__":
    mv=[a.split('=')[1] for a in sys.argv if a.startswith('--models=')]
    main(models=(mv[0].split(',') if mv else None))
