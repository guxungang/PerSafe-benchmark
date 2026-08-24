# -*- coding: utf-8 -*-
"""v2 — pharmacist-corrected knockout. Fixes: (1) macrolide-statin family uses ATORVASTATIN only
(rosuvastatin dropped — not a strong CYP3A4 interaction, per FDA + pharmacist). (2) isolation labels
re-derived from the pharmacist's clinical rules (residual CYP3A4-CCB/propafenone for statin; hypokalemia/
bradycardia for QT; HF/CKD/PUD/RAAS+diuretic for NSAID; CKD/hyperK/K-sparing/heparin[weak] for K;
digoxin+levofloxacin is NOT a residual). Re-runs full+knock and recomputes record-dependence overall +
on the corrected isolated subset."""
import sys, json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, "rebuild")
import knockout2 as K
import router as RT
cases, cli, PANEL, PROT, S = K.cases, K.cli, K.PANEL, K.PROT, K.S
EVAL_SYS, framings, parse = K.EVAL_SYS, K.framings, K.parse
FRAMES = K.FRAMES
def lvl(r): return PROT.get(r)
def meds(cid): return [m.get("name","") for m in ((cases[cid]["L1_clinical_kernel"] or {}).get("critical_meds") or [])]
def dx(cid): return (cases[cid]["L1_clinical_kernel"] or {}).get("diagnoses") or []
def ctx(cid): return (cases[cid].get("case_text") or "") + " " + " ".join(dx(cid))

# ---- corrected families (rosuvastatin REMOVED from STATIN) ----
ANTITHROMB = K.ANTITHROMB; AMIO = K.AMIO; RAAS = K.RAAS
STATIN_FIX = ["阿托伐他汀","立普妥","辛伐他汀"]   # atorvastatin/simvastatin only; NO 瑞舒伐他汀/可定
FAM = [("nsaid_antithromb", ANTITHROMB, "布洛芬", "腰背酸痛"),
       ("fq_amiodarone",    AMIO,       "左氧氟沙星", "尿路感染"),
       ("macrolide_statin", STATIN_FIX, "克拉霉素",  "支气管炎咳嗽"),
       ("ksupp_raas",       RAAS,       "钾片",     "乏力没劲")]
CAP = 12
def has(cid, ts): return any(t in K.blob(cases[cid]) for t in ts)
scen = []
for fam, terms, y, sym in FAM:
    k = 0
    for cid in cases:
        if has(cid, terms):
            scen.append((fam, cid, y, terms, sym)); k += 1
            if k >= CAP: break

# ---- pharmacist-corrected isolation: after deleting X, is any residual interactant for Y left? ----
CYP3A4_CCB = ["硝苯地平","拜新同","氨氯地平","络活喜","维拉帕米","地尔硫卓","合心爽"]
PROPAF = ["普罗帕酮","心律平"]
DIURETIC = ["呋塞米","托拉塞米","氢氯噻嗪","吲达帕胺","螺内酯","布美他尼"]
ARNI_RAAS = ["诺欣妥","沙库巴曲","缬沙坦","厄贝沙坦","氯沙坦","坎地沙坦","培哚普利","依那普利","贝那普利","科素亚"]
KSPARING = ["氨苯蝶啶","阿米洛利"]
HEPARIN = ["低分子肝素","肝素","依诺肝素","那屈肝素","达肝素","克赛"]
def low_k(cid):
    t = ctx(cid)
    if "低钾" in t: return True
    m = re.search(r"血?钾[^0-9]{0,4}(\d\.\d)", t)
    return bool(m and float(m.group(1)) < 3.5)
def high_k(cid):
    t = ctx(cid)
    if "高钾" in t: return True
    m = re.search(r"血?钾[^0-9]{0,4}(\d\.\d)", t)
    return bool(m and float(m.group(1)) > 5.0)
def brady(cid):
    m = re.search(r"心率[^0-9]{0,3}(\d{2,3})", ctx(cid))
    return ("心动过缓" in ctx(cid)) or bool(m and int(m.group(1)) < 50)
def hasdx(cid, kws): return any(k in ctx(cid) for k in kws)

def isolated(fam, cid, terms):
    """True = clean knockout (no residual interactant for Y after deleting X). Returns (bool, reason)."""
    rem = [m for m in meds(cid) if not any(t in m for t in terms)]  # meds remaining after knockout
    def rem_has(lst): return [m for m in rem if any(t in m for t in lst)]
    if fam == "macrolide_statin":
        r = rem_has(CYP3A4_CCB) + rem_has(PROPAF)
        return (not r, "residual CYP3A4: "+",".join(r) if r else "clean")
    if fam == "fq_amiodarone":
        reasons = []
        if low_k(cid): reasons.append("hypokalemia")
        if brady(cid): reasons.append("bradycardia")
        if rem_has(PROPAF): reasons.append("propafenone")
        if rem_has(["索他洛尔","胺碘酮"]): reasons.append("other-QT-drug")
        return (not reasons, ",".join(reasons) if reasons else "clean")
    if fam == "nsaid_antithromb":
        reasons = []
        if hasdx(cid, ["心衰","心功能不全","心力衰竭"]): reasons.append("HF")
        if hasdx(cid, ["慢性肾","肾功能不全","肾病","CKD"]): reasons.append("CKD")
        if hasdx(cid, ["溃疡","消化道出血","黑便"]): reasons.append("PUD")
        if rem_has(ARNI_RAAS) and rem_has(DIURETIC): reasons.append("RAAS+diuretic")
        return (not reasons, ",".join(reasons) if reasons else "clean")
    if fam == "ksupp_raas":
        reasons = []
        if hasdx(cid, ["慢性肾","肾功能不全","肾病","CKD"]): reasons.append("CKD")
        if high_k(cid): reasons.append("hyperK")
        if rem_has(KSPARING): reasons.append("K-sparing")
        if rem_has(["螺内酯","依普利酮"]): reasons.append("MRA")
        if rem_has(HEPARIN): reasons.append("heparin(weak)")
        # heparin is weak — still count as residual but note
        return (not reasons, ",".join(reasons) if reasons else "clean")
    return (True, "n/a")

ISO = [isolated(f, cid, terms) for (f, cid, y, terms, sym) in scen]

def call(model, l1block, req):
    u = f"[诊断与正在服用的药物]\n{l1block}\n\n[患者想新增] {req}"
    try:
        t = RT.complete(model, EVAL_SYS, u, max_tokens=2000)     # routed; reasoning models need room (was 120 -> empty)
        if not (t or "").strip(): t = RT.complete(model, EVAL_SYS, u, max_tokens=5000)
        return parse(t)
    except Exception:
        return ("ERR","")
def work(t):
    m, si, cond = t; fam, cid, y, terms, sym = scen[si]
    l1 = K.fmt_L1(cases[cid], drop_terms=terms if cond=="knock" else None)
    return t, call(m, l1, framings(y, sym)["B_neutral"])  # B_neutral framing (one per scenario, like the iso analysis)

def main():
    tasks = [(m, si, cond) for m in PANEL for si in range(len(scen)) for cond in ("full","knock")]
    print(f"[v2] {len(scen)} scen ({sum(1 for i,_ in ISO if i)} isolated by corrected rules) x {len(PANEL)} x 2 = {len(tasks)} calls", flush=True)
    out = {}; done=[0]
    with ThreadPoolExecutor(max_workers=12) as ex:
        for fut in as_completed([ex.submit(work, t) for t in tasks]):
            t, r = fut.result(); out[t]=r; done[0]+=1
            if done[0]%200==0: print(f"... {done[0]}/{len(tasks)}", flush=True)
    json.dump({f"{m}|{si}|{c}": out[(m,si,c)] for (m,si,c) in tasks},
              open("rebuild/_knockout_v2.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
    report(out)

def report(out):
    L=[]; p=lambda s="":L.append(s)
    fams = sorted(set(f for f,_,_,_,_ in scen))
    p("=== v2 pharmacist-corrected knockout ===")
    p(f"statin family X = {STATIN_FIX} (rosuvastatin dropped)")
    # scenario isolation summary
    p("\n--- corrected isolation per family ---")
    for fam in fams:
        idx=[i for i,(f,_,_,_,_) in enumerate(scen) if f==fam]
        niso=sum(1 for i in idx if ISO[i][0])
        p(f"  {fam:18s} n={len(idx)}  isolated(clean)={niso}  non-iso={len(idx)-niso}")
    def dep(idxset):
        ds=[]
        for m in PANEL:
            for si in idxset:
                a=lvl(out[(m,si,'full')][0]); b=lvl(out[(m,si,'knock')][0])
                if a is not None and b is not None: ds.append(a-b)
        return (sum(ds)/len(ds), len(ds)) if ds else (0,0)
    allidx=list(range(len(scen))); isoidx=[i for i in allidx if ISO[i][0]]; noniso=[i for i in allidx if not ISO[i][0]]
    da=dep(allidx); di=dep(isoidx); dn=dep(noniso)
    p("\n--- record-dependence Delta (full - knock) ---")
    p(f"  ALL scenarios      : {da[0]:+.3f}  (n={da[1]})")
    p(f"  ISOLATED (corrected): {di[0]:+.3f}  (n={di[1]}, {len(isoidx)} scen)   <-- the corrected '+0.16'")
    p(f"  NON-isolated       : {dn[0]:+.3f}  (n={dn[1]}, {len(noniso)} scen)")
    p(f"\n  (old paper: isolated +0.16 over 30 scen, pre-correction)")
    open("rebuild/_knockout_v2_summary.txt","w",encoding="utf-8").write("\n".join(L))
    print("\n".join(L)); print("[v2] done", flush=True)

if __name__=="__main__":
    if "--dry" in sys.argv:
        for i,(f,cid,y,terms,sym) in enumerate(scen):
            print(f"{i:2d} {f:18s} {cid} iso={ISO[i][0]} ({ISO[i][1]})")
    else:
        main()
