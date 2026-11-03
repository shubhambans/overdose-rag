# Replications of published studies, run on Claude

Each folder re-runs a published study's design on current Claude models (Nov 2026), so our results can be compared
with the literature. Every folder has its own README covering: what was copied exactly, what could not be copied
and why, the results next to the paper's numbers, and limitations.

| Folder | Study | Type | Headline |
|---|---|---|---|
| `hripbench/` | Wang K. et al. 2025, *HRIPBench* (arXiv 2507.21815): harm-reduction facts, 2,160 questions | **Direct** (public data, verbatim prompts). The paper had no Claude model. | Accuracy equals the paper's best models (Sonnet 87.3% vs 81.7–88.8%). Errors lean strongly toward caution: "not safe" when the source says safe 48–64% of the time, the reverse 1–3%. 0 refusals. |
| `wang2025/` | Wang Y. et al. 2025, *J Addict Med*: stigmatizing language in 14 LLMs, plus prompt engineering | **Conceptual** (questions and prompt not public; design and analysis copied) | Stigma in 20–24% of native replies (Wang: 35%), 0.6% with an anti-stigma prompt (Wang: 6.3%). Driven by outdated liver-disease names ("alcoholic hepatitis"). |
| `campos2025/` | Campos et al. 2025, *Am J Addict*: ChatGPT vs official opioid FAQs (readability, stigma) | **Conceptual** (their 50 FAQs not public; 50 real official FAQs rebuilt; all measures and tests copied) | Claude is about 3× longer than the FAQs. Reading level depends on how bullets are scored (−1.8 or +2.7 grades). A plain-language prompt brings it to about 5th grade. Stigma is rare. |

**Shared tools:** `eval/stigma_terms.py` (stigma counter), `src/costs.py` (budget guard), `src/llm.py` (API calls).
**Figures:** `make_figures.py` draws `figures/fig9_hripbench_safety` and `figures/fig10_wang_replication`.

**Why "conceptual" for two of them:** both papers are paywalled, and neither published its question set. We copied
their design, measures and statistics exactly, and rebuilt the inputs from the same kinds of sources. If the
original question lists become available (supplements, or by emailing the authors), `questions.csv` / `faqs.csv`
can be swapped in and the scripts re-run unchanged.
