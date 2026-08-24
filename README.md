# PerSafe

Benchmark and evaluation code for *Reading the Patient, Holding the Line: PerSafe, a Gold-Light Contingency
Benchmark for Safe Personalization in Medical LLMs* (PRICAI 2026).

PerSafe evaluates whether a medical LLM's answer is **contingent on the patient**: one input is changed and the
output is checked to change only when it should. Because every check compares a model with itself, no per-case
answer key is needed; the scenarios are still built from published guidelines and drug labels, so the method is
*gold-light*.

## Contents

| Path | What it holds |
|---|---|
| `oracles/preference_equipoise_scenarios.json` | The three genuine-equipoise decisions: neutralized options, explicit and implicit value sentences, paraphrases, placebo wishes, per-patient eligibility flags, provenance |
| `oracles/safety_edge_traps.json` | The nine hidden-danger traps: the push utterance, the neutralized options, which pole is unsafe, and the guideline or label the hazard rests on |
| `oracles/must_say_lists.json` | The four external must-say lists, tiered, taken from drug labels and guidelines (no model output) |
| `oracles/communication_scenarios.json` | The communication scenarios and the four style dimensions |
| `oracles/trap_citation_verification.md` | The independent citation re-check, including the four candidate traps that were dropped and why |
| `oracles/equipoise_clinician_adjudication.md` | The cardiologist's adjudication of the candidate equipoise decisions |
| `scripts/` | The multi-provider router and the three axis harnesses, plus the aggregation and figure scripts |
| `scores/` | Per-cell numeric results for all 14 models, and the aggregated panel tables |

## What is not released

The underlying patient charts are governed by a data-use agreement and are not redistributed. The
communication scores carry the must-say verdicts and answer lengths but not the raw model answers, since those
quote chart content. Case identifiers are pseudonymous.

## Reproducing the tables

The `scores/` files are the cached per-cell outputs, so every table in the paper can be regenerated without
calling any model:

```bash
python scripts/a_axis_analysis.py scores/content_knockout_cells.json   # content: record-dependence + the three rates
python scripts/panel_summary.py                                       # the master panel table
```

Re-running the panel from scratch requires provider credentials; see `scripts/router.py` for the five
providers and the environment variables each expects.

## Citation

To be added on publication.

## Licence

Code under MIT. Scenario specifications and oracles under CC BY 4.0. The clinical facts they encode are drawn
from published guidelines and drug labels, cited in each file.
