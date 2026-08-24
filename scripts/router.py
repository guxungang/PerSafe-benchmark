# -*- coding: utf-8 -*-
"""Unified model router: complete(model, system, user, max_tokens) -> text, across 4 providers
(DashScope/Bailian, Azure-OpenAI-Responses, Azure-Grok-inference, SiliconFlow). Used by all 3 axis harnesses."""
import os
from dotenv import load_dotenv; load_dotenv(override=True)
from openai import OpenAI, AzureOpenAI

# canonical panel name -> (provider, api_model_id)
PANEL = {
 "gpt-5.5":           ("azure_gpt55", "gpt-5.5"),
 "gpt-5.4-mini":      ("azure_mini",  "gpt-5.4-mini"),
 "grok-4.3":          ("azure_grok",  "grok-4.3"),
 "qwen3.5-plus":      ("dashscope",   "qwen3.5-plus"),
 "glm-5":             ("dashscope",   "glm-5"),
 "qwen3-235b-a22b":   ("dashscope",   "qwen3-235b-a22b"),
 "deepseek-v3.2":     ("dashscope",   "deepseek-v3.2"),
 "deepseek-r1":       ("dashscope",   "deepseek-r1"),
 "kimi-k2.6":         ("dashscope",   "kimi-k2.6"),
 "deepseek-v4-pro":   ("siliconflow", "deepseek-ai/DeepSeek-V4-Pro"),
 "gpt-oss-120b":      ("siliconflow", "openai/gpt-oss-120b"),
 "gpt-oss-20b":       ("siliconflow", "openai/gpt-oss-20b"),
 "Baichuan-M2":       ("baichuan",    "Baichuan-M2"),   # medical-specialist arm
 "gemma-4-31b":       ("siliconflow", "google/gemma-4-31B-it"),   # Google open, Western-open second lineage
}
_cli = {}
def _client(prov):
    if prov in _cli: return _cli[prov]
    if prov=="dashscope":   c=OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"], base_url=os.environ["DASHSCOPE_ENDPOINT"], timeout=120, max_retries=2)
    elif prov=="siliconflow": c=OpenAI(api_key=os.environ["SILICONFLOW_API_KEY"], base_url=os.environ["SILICONFLOW_ENDPOINT"], timeout=240, max_retries=6)  # heavier retry: rate-limits under load
    elif prov=="baichuan":    c=OpenAI(api_key=os.environ["BAICHUAN_API_KEY"], base_url=os.environ["BAICHUAN_ENDPOINT"], timeout=180, max_retries=8)  # low rate limit -> heavy retry
    elif prov=="azure_grok":  c=OpenAI(api_key=os.environ["AZURE_GROK_API_KEY"], base_url=os.environ["AZURE_GROK_ENDPOINT"], default_query={"api-version":os.environ["AZURE_GROK_API_VERSION"]}, timeout=180, max_retries=2)
    elif prov=="azure_gpt55": c=AzureOpenAI(azure_endpoint=os.environ["AZURE_GPT55_ENDPOINT"], api_key=os.environ["AZURE_GPT55_API_KEY"], api_version=os.environ["AZURE_GPT55_API_VERSION"], timeout=180, max_retries=2)
    elif prov=="azure_mini":  c=AzureOpenAI(azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"], api_version=os.environ["AZURE_OPENAI_API_VERSION"], timeout=180, max_retries=2)
    else: raise ValueError(prov)
    _cli[prov]=c; return c

def _think_off(api_id):  # Qwen/GLM hybrids: disable thinking for short tasks (else thinking exhausts budget -> empty)
    ml=api_id.lower(); return (ml.startswith("qwen") or ml.startswith("glm")) and not any(t in ml for t in ("r1","reasoner","thinking"))

def complete(model, system, user, max_tokens=2000):
    prov, api = PANEL[model]
    msgs=[{"role":"system","content":system},{"role":"user","content":user}] if system else [{"role":"user","content":user}]
    if prov in ("azure_gpt55","azure_mini"):                 # Responses API
        r=_client(prov).responses.create(model=api, input=msgs, max_output_tokens=max(max_tokens,2000))
        return r.output_text or ""
    eb={"extra_body":{"enable_thinking":False}} if (prov=="dashscope" and _think_off(api)) else {}
    r=_client(prov).chat.completions.create(model=api, messages=msgs, max_tokens=max_tokens, temperature=0, **eb)
    return r.choices[0].message.content or ""

def _warmup():
    # Force OpenAI SDK's lazy submodule imports (chat.completions / responses) SINGLE-THREADED at load,
    # else concurrent threads race the import lock -> "deadlock detected by _ModuleLock".
    for prov in ("dashscope","siliconflow","azure_grok","azure_gpt55","azure_mini","baichuan"):
        try:
            c=_client(prov); _=c.chat.completions; _=c.responses
        except Exception: pass
_warmup()

ALL = list(PANEL.keys())
if __name__=="__main__":
    import concurrent.futures as cf
    SYS=("你是医疗助手。请回答你更推荐哪个方案、把握多大。choice=1更推荐方案一,choice=2更推荐方案二;confidence=0-100。"
         '只输出一行JSON:{"choice":1或2,"confidence":整数}')
    U="[病人] 阵发性房颤。[选择] 方案一:节律控制 ;方案二:室率控制。[病人说] 我想恢复正常生活,愿意多担点风险。"
    import re
    def t(m):
        try:
            c=complete(m,SYS,U,2500); j=re.search(r'"choice"\s*:\s*([12])',c)
            return m, ('✅ '+ (j.group(0) if j else repr(c[:40])))
        except Exception as e: return m, '❌ '+str(e)[:80]
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for m,s in ex.map(t, ALL): print(f'  {m:18} {s}')
