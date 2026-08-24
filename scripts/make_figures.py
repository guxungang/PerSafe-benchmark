# -*- coding: utf-8 -*-
"""Generate Figure 2 (model picture scatter) and Figure 3 (failure heatmap) from the locked run data.
Vector PDF for the paper + PNG for inspection. Colorblind-safe, grayscale-readable (values annotated)."""
import os, json, collections, sys
sys.path.insert(0, "rebuild")
import b1_experiment2 as B
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = "paper_bench/figures"; os.makedirs(OUT, exist_ok=True)
PANEL = ["gpt-5.5","gpt-5.4-mini","grok-4.3","qwen3.5-plus","glm-5","qwen3-235b-a22b",
         "deepseek-v3.2","deepseek-r1","kimi-k2.6","deepseek-v4-pro","gpt-oss-120b","gpt-oss-20b",
         "gemma-4-31b","Baichuan-M2"]
def mean(xs): xs=[x for x in xs if x is not None]; return sum(xs)/len(xs) if xs else None

# ---- aggregate from raw _b1v2.json (same logic as panel_summary) ----
d=json.load(open("rebuild/_b1v2.json",encoding="utf-8"))
agg=collections.defaultdict(list)
for ks,v in d.items():
    k=ks.split("|")
    if k[0] in PANEL: agg[(k[0],int(k[3]),k[4],k[5])].append(v)
A={k:mean(v) for k,v in agg.items()}
pool=B.SCEN+B.EDGES
decs=sorted(set(s["decision"] for s in pool if "L2" in s))
edges=[(i,s) for i,s in enumerate(pool) if "push_value" in s]
def ul(m,i,cond):
    v=A.get((m,i,"edge",cond)); return None if v is None else (v if pool[i]["unsafe_pole"]=="interv" else 100-v)
follow={}; danger={}
for m in PANEL:
    fol=[]
    for dk in decs:
        idx=[i for i,s in enumerate(pool) if "L2" in s and s["decision"]==dk]
        va=mean([A.get((m,i,"L3","val_A")) for i in idx]); vb=mean([A.get((m,i,"L3","val_B")) for i in idx])
        if va is not None and vb is not None: fol.append(va-vb)
    follow[m]=mean(fol)
    danger[m]=mean([ul(m,i,"push") for i,_ in edges if ul(m,i,"push") is not None])

# trap matrix (ordered by mean pushed lean, desc)
traps=sorted(set(s["edge_of"] for _,s in edges),
             key=lambda g:-mean([ul(m,i,"push") for i,s in edges if s["edge_of"]==g for m in PANEL if ul(m,i,"push") is not None]))
SHORT={t:s for t,s in zip(traps,[None]*len(traps))}
LABEL={"病窦+简单控率(停搏)":"SSS\nrate-ctrl","左室收缩功能减低(LVEF<50)+非DHP-CCB(负性肌力)":"redEF\n+CCB",
       "ARNI在用+加普利(血管性水肿)":"ARNI\n+ACEi","结构性心脏病+IC类复律(CAST类效应)":"struct\n+IC",
       "β阻滞剂+已有缓慢/传导阻滞→加非DHP-CCB(高度阻滞)":"BB-brady\n+CCB","急性心梗血运重建":"acute-MI\nrevasc",
       "确诊ASCVD维持他汀":"keep\nstatin","高卒中风险房颤维持抗凝":"keep\nanticoag","机械瓣围术期自停华法林(瓣膜血栓)":"mech-valve\nwarfarin"}
mat=np.array([[ (mean([ul(m,i,"push") for i,s in edges if s["edge_of"]==t if ul(m,i,"push") is not None]) or np.nan) for t in traps] for m in PANEL])

plt.rcParams.update({"font.size":9,"font.family":"serif","axes.linewidth":0.8,"savefig.bbox":"tight"})

# ================= FIGURE 2: scatter =================
fig,ax=plt.subplots(figsize=(5.8,4.4))
xs=[follow[m] for m in PANEL]; ys=[100-danger[m] for m in PANEL]
ax.axhspan(80,103,color="0.93",zorder=0)                       # safe zone
ax.text(45.5,101.5,"safer",color="0.45",fontsize=8,style="italic",va="top")
hi={"gpt-5.5":"#0072B2","qwen3-235b-a22b":"#D55E00","Baichuan-M2":"#009E73"}  # Okabe-Ito blue / vermillion / green=medical specialist
for m,x,y in zip(PANEL,xs,ys):
    c=hi.get(m,"#333333"); s=72 if m in hi else 34
    ax.scatter(x,y,s=s,color=c,edgecolor="white",linewidth=0.6,zorder=4)
# explicit label anchors (data coords) + thin leader lines -> no overlap
LP={"gpt-5.5":(68.5,99.5),"grok-4.3":(53,92),"gpt-oss-20b":(46.8,75.5),
    "deepseek-v4-pro":(88,95.5),"glm-5":(90.5,90.5),"deepseek-r1":(74.5,83.3),
    "gpt-5.4-mini":(89.5,86),"qwen3.5-plus":(90.5,79),"gpt-oss-120b":(72,74.6),
    "kimi-k2.6":(63,74.6),"deepseek-v3.2":(66.5,60.5),"qwen3-235b-a22b":(88,45),
    "gemma-4-31b":(78,93),"Baichuan-M2":(58,95)}
P=dict(zip(PANEL,zip(xs,ys)))
for m,(lx,ly) in LP.items():
    px,py=P[m]; ha="left" if lx>=px else "right"
    ax.annotate(m,xy=(px,py),xytext=(lx,ly),fontsize=6.3,ha=ha,va="center",
                color=hi.get(m,"0.15"),fontweight="bold" if m in hi else "normal",
                arrowprops=dict(arrowstyle="-",color="0.6",lw=0.5,shrinkA=0,shrinkB=2))
ax.set_xlabel("follows the stated preference  (0–100,  higher = follows)")
ax.set_ylabel("safety under pressure  (100 − danger-endorsement)")
ax.set_xlim(44,97); ax.set_ylim(38,103)
ax.grid(True,color="0.9",linewidth=0.6); ax.set_axisbelow(True)
fig.savefig(f"{OUT}/fig2_model_picture.pdf"); fig.savefig(f"{OUT}/fig2_model_picture.png",dpi=150); plt.close(fig)

# ================= FIGURE 3: heatmap =================
fig,ax=plt.subplots(figsize=(6.6,4.4))
cmap=plt.cm.YlOrRd.copy(); cmap.set_bad("0.88")               # missing cells -> light gray
im=ax.imshow(np.ma.masked_invalid(mat),cmap=cmap,vmin=0,vmax=100,aspect="auto")
ax.set_xticks(range(len(traps))); ax.set_xticklabels([LABEL[t] for t in traps],fontsize=6.6)
ax.set_yticks(range(len(PANEL))); ax.set_yticklabels(PANEL,fontsize=7.5)
for i in range(len(PANEL)):
    for j in range(len(traps)):
        v=mat[i,j]
        if not np.isnan(v):
            ax.text(j,i,f"{v:.0f}",ha="center",va="center",fontsize=6,
                    color="white" if v>55 else "0.2")
cb=fig.colorbar(im,ax=ax,fraction=0.025,pad=0.02); cb.set_label("lean toward danger when pushed (0–100)",fontsize=7.5)
cb.ax.tick_params(labelsize=7)
ax.set_xticks(np.arange(-.5,len(traps),1),minor=True); ax.set_yticks(np.arange(-.5,len(PANEL),1),minor=True)
ax.grid(which="minor",color="white",linewidth=1.0); ax.tick_params(which="minor",length=0)
fig.savefig(f"{OUT}/fig3_failure_heatmap.pdf"); fig.savefig(f"{OUT}/fig3_failure_heatmap.png",dpi=150); plt.close(fig)

print("wrote:", os.listdir(OUT))
print("follow/danger sanity:", {m:(round(follow[m]),round(danger[m])) for m in PANEL[:3]})
