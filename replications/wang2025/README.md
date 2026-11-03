# Replication: Wang et al. 2025 (stigmatizing language in LLMs, and prompt engineering)

**Original:** Wang Y, Hsu K, Brokus C, Huang Y, Ufere N, Wakeman S, Zou J, Zhang W. *Stigmatizing Language in Large
Language Models for Alcohol and Substance Use Disorders: A Multimodel Evaluation and Prompt Engineering Approach.*
J Addict Med 2026;20(3):306–314 (epub 2025-07-24). doi:10.1097/ADM.0000000000001536. PMID 40705021.

**Type: conceptual replication.**
- **Copied exactly:**
  - the design: 60 clinically relevant questions, 20 each on alcohol use disorder (AUD), alcohol-associated liver
    disease (ALD) and substance use disorder (SUD);
  - native vs engineered prompts;
  - the outcome: any stigmatizing language (SL) per response;
  - the analyses: SL rate by condition and topic, logistic model with topic and word count, paired comparison.
- **Not copied (paywalled, no public supplement):**
  - their 60 questions;
  - their engineered prompt;
  - their coding by two physicians.
- **What we used instead:**
  - `questions.csv`: our 60 questions (AI-drafted, neutral wording).
  - `ENGINEERED` in `run.py`: a prompt built from the same NIDA/NIAAA guidance they cite.
  - SL detection: `eval/stigma_terms.py` plus human review of hits.

## What we did
- **Models:** Claude Haiku 5.5, Sonnet 5.5 and Opus 5.5 (current Claude family, Nov 2026). Wang tested 14 LLMs
  available in Sept 2024.
- **Runs:** each question was asked once per model per condition: 360 replies.
  - **Native:** no system prompt.
  - **Engineered:** the system prompt lists the terms to avoid and their preferred alternatives.
- **Cost:** $4.90.

## Results
| | Wang 2025 (14 LLMs) | Claude, raw counter | Claude, adjudicated* |
|---|---|---|---|
| Native: % responses with SL | 35.4% (297/840) | **23.9%** (43/180; 95% CI 18–31%) | **20.6%** |
| Engineered: % with SL | 6.3% (53/840) | **0.6%** (1/180) | 0.6% |
| Effect of engineering | OR 0.15 (adjusted) | 43 replies lost SL, 1 gained; McNemar p < 10⁻¹¹; adjusted OR 0.01 | |
| ALD vs AUD (native) | aOR 2.11 | **55% vs 10%** (adjusted OR 11) | 55% vs 7% |
| SUD vs AUD | aOR 1.17 (ns) | 7% vs 10% | 0% vs 7% |
| Per model (native) | all 14 had SL | Haiku 23%, Sonnet 22%, Opus 27% | 20–22% |
| Longer replies → more SL | yes | **no** (r = −0.14) | |

\*Adjudicated applies Shubham's main-study rulings by analogy (pending his confirmation): "users" describing a group
and "habit" in its behavioral sense are not counted.

**What drives it:** outdated liver-disease names.
- The main term is "alcoholic hepatitis" (41 uses in native replies). Others: "alcoholic fatty liver / steatosis /
  liver disease" and "alcoholic hallucinosis".
- Liver societies have renamed these "alcohol-associated…", and NIAAA advises against "alcoholic". Wang named the
  same category ("alcoholic cirrhosis").
- Outside the ALD questions, Claude almost never used stigmatizing terms: SUD 0% after adjudication.

## What it means
1. **The core finding replicates in today's Claude models, at a lower level.**
   - Without instructions, about 1 in 5 answers about alcohol-related conditions contain a stigmatizing term.
   - Most of these are disease names that still circulate in medical literature, which is probably why the model
     reproduces them.
2. **Prompt engineering works even better than in Wang:** one system prompt took SL to 0.6%. The single remaining
   hit was Opus saying "alcoholic" in a liver-disease answer.
3. **The topic effect replicates strongly:** liver-disease questions are where the stigma lives.
4. **The length effect did not replicate.** Engineered replies were longer *and* cleaner, which breaks the
   length–stigma link.
5. **Contrast with our main study.** First-person messages from people who use drugs produced almost no stigma
   (0–2%). Clinical-style liver questions did.
   - So the type of question matters more than the speaker.
   - Clinical framing pulls in clinical, and sometimes outdated, terminology.

## Limitations
- The questions are ours, not Wang's. An automated counter plus human review replaced physician coding.
- One sample per question per condition; no temperature control.
- Whether "alcoholic hepatitis" counts as stigma is debatable: it is still a common diagnosis name. We follow
  NIAAA, the liver-society renaming, and Wang's own coding.
- **Mention vs use:** replies that *explain* the renaming (e.g. *"alcohol-associated" is now preferred over
  "alcoholic"*) are not counted (`eval/stigma_terms.py`).

## Files
- `questions.csv`: the 60 questions.
- `run.py`: generation and analysis.
- `cache.jsonl`: all 360 replies.
- `results/scored.csv`: per-reply SL and terms.
- `results/table_*.csv` and `results/summary.json`: the tables and model output.
