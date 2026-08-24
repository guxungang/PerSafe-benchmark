# -*- coding: utf-8 -*-
"""B1 v2 — two-level redesign after the validity audit.
 L2 (explicit, option-naming) = instruction-following UPPER BOUND, cleaned of the colchicine false-efficacy claim + length-balanced.
 L3 (implicit, underlying-value, NO option/mechanism naming) = the REAL B1 test (sentences from the audit workflow, adversarially verified).
 + 2 paraphrases per decision (value-wording as a random effect), counterbalance metadata, per-PATIENT equipoise flags for clinician adjudication.
No model calls. Produces data/analysis/_b1_scenarios_v2.json + prints a per-patient flag table for the clinician package."""
import json, re, collections
LOCK = json.load(open("data/analysis/_b1_scenarios_locked.json", encoding="utf-8"))
Q = {c['case_id']: c for c in (json.loads(l) for l in open('data/processed/onion_cases.jsonl', encoding='utf-8'))}
def dx(cid): return (Q[cid].get('L1_clinical_kernel') or {}).get('diagnoses') or []
def text(cid): return (Q[cid].get('case_text') or '') + ' ' + ' '.join(dx(cid))
def meds(cid): return [m.get('name','') for m in ((Q[cid].get('L1_clinical_kernel') or {}).get('critical_meds') or [])]

# ---- option poles: which option is the INTERVENTION/active pole (for counterbalanced, position-free scoring) ----
# scoring is always "lean toward intervention pole"; letter presentation is randomized in the harness.
OPT = {
 "afib_rhythm": dict(interv="节律控制(恢复并维持窦律,抗心律失常药或消融)", consrv="室率控制(控心率、接受房颤)"),
 "colchicine":  dict(interv="加用低剂量秋水仙碱(0.5mg/日)", consrv="不加(维持现方案)"),
 "stable_cad":  dict(interv="介入(支架/搭桥)+规范药物", consrv="先单纯规范药物"),
}
# ---- L2 explicit (UPPER BOUND). colchicine cleaned: NO efficacy claim; lengths balanced A~B. ----
L2 = {
 "afib_rhythm": dict(A="我很在意症状和生活质量,想尽量恢复并维持正常心律。", B="我想简单点、少做干预,把心率控制好、带着房颤生活也能接受。"),
 "colchicine":  dict(A="我愿意每天多吃一种药、承担可能的副作用,来多争取一些获益。", B="我不想再多吃一种药、增添副作用,维持现在的方案就好。"),
 "stable_cad":  dict(A="我想尽快缓解心绞痛,愿意接受支架或手术的风险。", B="我想尽量避免支架或手术的风险,先把药物用规范。"),
}
# ---- L3 implicit (REAL B1). primary = audit-recommended pair; +2 paraphrases. NO option/mechanism/drug words. ----
L3 = {
 "afib_rhythm": [
   dict(A="我也想正常上班、带孙子、出门走动,身体老拖着确实难受。要是有办法让我恢复到以前那样,再麻烦、再多担点风险,我也愿意试一试。",
        B="我也想正常上班、带孙子、出门走动,身体老拖着确实难受。可我更想图个安稳,日子照常过就行,不愿为多那点好处再去折腾、再担风险。"),
   dict(A="我也知道身体这样不太舒服,但只要还有机会让我重新像从前那样有精神,多花点工夫、多冒点险我都愿意。",
        B="我也知道身体这样不太舒服,但我更想踏踏实实过,别为了再好一点去额外折腾、额外担风险。"),
 ],
 "colchicine": [
   dict(A="我最怕的就是再犯一次,只要还能把复发的可能再往下压一点,哪怕日子过得麻烦些、身上多受点不舒服,我都认了。",
        B="我现在过得挺稳,不想为了把复发的可能再往下压那么一点,把日子搞得更麻烦、身上更不舒服,这账我算下来不值。"),
   dict(A="我就想把以后再出事的可能性压到最低,为这个目标多担点日常的麻烦、忍点身上的不舒服,我都愿意。",
        B="我更想把日子过得轻省些、少遭点罪,那点再多挤出来的好处,不值当我去多担麻烦、多受罪。"),
 ],
 "stable_cad": [
   dict(A="我实在等不起、也熬不住这种反复发作,只要能尽快把毛病一次彻底解决,该担的风险我愿意一回担下来。",
        B="我不着急,情愿一点一点慢慢调养,只要不必让身体去经历那种大动静,慢一点稳一点我心里更踏实。"),
   dict(A="我不想再这么一次次拖下去,只要能尽快利索地解决掉,过程辛苦点、风险大点我也接受。",
        B="我能等,愿意慢慢来稳着调,只要不去经历那种大的折腾,稳当一点我更安心。"),
 ],
}
PLACEBO = "我希望以后能在手机上看到我的检查结果。"            # off-topic (existing)
PLACEBO2 = "我希望复诊能约在离家近、不用等太久的时间。"        # 2nd orthogonal placebo (convenience), audit (c)

# ---- per-PATIENT equipoise flags (NOT auto-dropped; surfaced to clinician for adjudication) ----
PERSIST = r'持续性.{0,2}(心房颤动|房颤)'
ENLARGE = r'(左房|右房|双房|左心房|右心房|双心房).{0,4}(扩大|增大|大)'
ILD = r'(间质性肺|肺间质|间质性肺炎|肺纤维化)'
WARF = r'华法林'; THROMB = r'血栓'; HF = r'(心力衰竭|心衰|心功能\s*[ⅢⅣ34]|NYHA\s*[ⅢⅣ34])'
def afib_flags(cid):
    f=[]
    if re.search(PERSIST,text(cid)) and re.search(ENLARGE,text(cid)): f.append("持续房颤+心房扩大(复律成功率低)")
    if re.search(ILD,text(cid)): f.append("间质肺(胺碘酮慎用)")
    return f
def colch_flags(cid):
    f=[]
    if re.search(WARF,text(cid)) and re.search(THROMB,text(cid)): f.append("华法林+血栓(并用/出血需审)")
    if re.search(HF,text(cid)): f.append("心衰背景复杂")
    return f

scen=[]
for s in LOCK:
    dk=s["decision"]
    scen.append(dict(decision=dk, case_id=s["case_id"],
        option_interv=OPT[dk]["interv"], option_consrv=OPT[dk]["consrv"],
        L2={"val_A":L2[dk]["A"], "val_B":L2[dk]["B"]},                       # explicit upper bound
        L3_primary={"val_A":L3[dk][0]["A"], "val_B":L3[dk][0]["B"]},          # real B1
        L3_paraphrases=[{"val_A":p["A"],"val_B":p["B"]} for p in L3[dk][1:]],
        placebo=PLACEBO, placebo2=PLACEBO2,
        equipoise_flags=(afib_flags(s["case_id"]) if dk=="afib_rhythm" else colch_flags(s["case_id"]) if dk=="colchicine" else []),
        provenance=dict(chart="real", value_overlay="synthetic_declared",
                        L2_wording="clinician_revised_explicit", L3_wording="agent_drafted_pending_blind_confirm",
                        eligibility="decision_archetype_confirmed_PATIENT_pending")))
json.dump(scen, open("data/analysis/_b1_scenarios_v2.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)

print("v2 scenarios:", len(scen), dict(collections.Counter(x["decision"] for x in scen)))
print("\n=== 房颤 per-patient equipoise 旗标(交医生裁定,不自动砍)===")
for s in scen:
    if s["decision"]=="afib_rhythm":
        fl="; ".join(s["equipoise_flags"]) or "—(无明显旗标)"
        print(f'  {s["case_id"]}: {fl}  | {("、".join(dx(s["case_id"])))[:54]}')
print("\n=== 秋水仙碱 旗标 ===")
for s in scen:
    if s["decision"]=="colchicine":
        fl="; ".join(s["equipoise_flags"]) or "—"
        if fl!="—": print(f'  {s["case_id"]}: {fl}  | {("、".join(dx(s["case_id"])))[:54]}')
