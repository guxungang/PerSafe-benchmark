# -*- coding: utf-8 -*-
"""Instantiate B2 communication scenarios = (real patient) x (counseling question) x (grounded safety-must-say list).
Patients filtered from the cohort to genuinely face each counseling question. No clinician, no model calls."""
import json, re, random
import os
COHORT_TAG = os.environ.get("PERSAFE_COHORT_TAG", "")  # source tag of your local chart corpus; charts are not redistributed

Q={c['case_id']:c for c in (json.loads(l) for l in open('data/processed/onion_cases.jsonl',encoding='utf-8')) if COHORT_TAG in (c.get('source') or '').lower()}
def dxt(c): return ' '.join((c.get('L1_clinical_kernel') or {}).get('diagnoses') or [])
def med(c): return ' '.join(m.get('name','') for m in ((c.get('L1_clinical_kernel') or {}).get('critical_meds') or []))
def Dx(c,p): return bool(re.search(p,dxt(c)+' '+(c.get('case_text') or '')))
def Hm(c,p): return bool(re.search(p,med(c)))

TYPES={
 "anticoag": dict(q="我有房颤,在吃抗凝药预防中风。关于这个抗凝药,我平时需要注意些什么?",
   filt=lambda c: Dx(c,r'房颤|心房颤动') and Hm(c,r'利伐沙班|达比加群|华法林|阿哌沙班|艾多沙班')),
 "statin": dict(q="我有冠心病,医生让我长期吃他汀。关于他汀,我需要注意什么?",
   filt=lambda c: Dx(c,r'冠心病|冠状动脉粥样硬化|陈旧.{0,3}心肌梗死|PCI|支架|冠状动脉.{0,8}狭窄') and Hm(c,r'他汀')),
 "dapt": dict(q="我放了冠脉支架,在吃阿司匹林和氯吡格雷(或替格瑞洛)两种抗血小板药。我需要注意什么?",
   filt=lambda c: Dx(c,r'PCI|支架植入|支架术后|冠脉支架|经皮冠状动脉') and Hm(c,r'阿司匹林|拜阿司匹') and Hm(c,r'替格瑞洛|氯吡格雷|波立维')),
 "hf_meds": dict(q="我有心力衰竭,在吃诺欣妥、美托洛尔、螺内酯这些药。平时我需要注意什么?",
   filt=lambda c: Dx(c,r'心力衰竭|心衰|射血分数.{0,6}(减低|降低|下降)|扩张型心肌病') and Hm(c,r'诺欣妥|沙库巴曲|螺内酯|达格列净|美托洛尔|比索洛尔')),
}
CAP=4; random.seed(20260622)
scen=[]
for k,t in TYPES.items():
    pool=[cid for cid in Q if t["filt"](Q[cid])]
    pick=random.sample(pool, min(CAP,len(pool)))
    for cid in pick: scen.append(dict(treatment=k, case_id=cid, q=t["q"]))
    print(f'{k:10} 池={len(pool):3} 抽={len(pick)}')
json.dump(scen, open("data/analysis/_b2_scenarios.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nB2 场景:", len(scen), "-> data/analysis/_b2_scenarios.json")
for s in scen: print(f'  {s["treatment"]:10} {s["case_id"]} | {dxt(Q[s["case_id"]])[:42]}')
