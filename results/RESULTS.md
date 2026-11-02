# Results: how Claude responds to people who use drugs and their families

**Status: first full run, 2026-11-02.**
- **Test messages:** 60, AI-written (`author = AI-draft-v0`), not yet reviewed by Shubham.
- **Hand-score validation:** pending (`eval/hand_scoring_sheet.csv`).
- Treat every number below as **preliminary**.

## Setup in one paragraph
- **Messages:** 60 first-person messages, made from 10 scenarios × 6 substances. 6 scenarios come from a person
  who uses drugs, 4 from family or friends.
- **Model and conditions:** Claude Sonnet 5.5 answered each message under three conditions:
  - **Default:** the system prompt is just "You are a helpful assistant."
  - **RAG:** the 5 most relevant excerpts from our guidance, research and communication corpus are added to
    the system prompt.
  - **MI prompt:** a system prompt asking for a motivational-interviewing, harm-reduction style.
- **Judge:** Claude Opus 5.5 scored all 180 replies on our MITI-based rubric (`eval/tone_rubric.md`). It never
  saw which condition wrote the reply, and replies were shuffled with citation tags stripped.
- **Stigma counter:** a script, with no AI involved, counted stigmatizing words (NIDA *Words Matter* plus your
  rules).
- **Statistics:** each message is compared with itself across conditions. Scores use the Wilcoxon signed-rank
  test; yes/no outcomes use McNemar's exact test. Holm correction is applied over the 5 rubric dimensions;
  95% CIs are bootstrapped over messages.

## Total API spend: **$9.27 of the $18 hard stop**
| Phase | Calls | Cost |
|---|---|---|
| Responses (Sonnet 5.5) | 180 | $2.45 |
| Judge (Opus 5.5) | 180 | $5.83 |
| Judge validation on AnnoMI (Opus 5.5) | 42 | $0.97 |
| Study 2A zero-shot (Haiku 5.5) | 56 | $0.01 |

Pilot runs that were reused from cache are counted once. Source: `results/api_usage.csv`, which is git-ignored.

---

## Finding 1: The MI-style system prompt improved every dimension, most of all autonomy
- **Question:** does a one-paragraph MI/harm-reduction system prompt change how Claude talks to people who use
  drugs?
- **Result:** mean score, MI prompt minus default (95% CI), with Holm-corrected p. "Better/worse" counts the
  messages where the MI reply scored higher or lower than the default reply.

  | Dimension | Default | MI prompt | Difference (95% CI) | Better / worse | p (Holm) |
  |---|---|---|---|---|---|
  | Autonomy | 4.17 | 4.77 | **+0.60** (0.45 to 0.75) | 37 / 2 | <0.001 |
  | Empathy | 4.15 | 4.47 | +0.32 (0.20 to 0.43) | 19 / 0 | <0.001 |
  | Harm reduction | 4.53 | 4.82 | +0.28 (0.13 to 0.43) | 19 / 3 | 0.002 |
  | Non-judgment | 4.80 | 5.00 | +0.20 (0.10 to 0.30) | 12 / 0 | 0.002 |
  | Helpfulness | 4.80 | 4.92 | +0.12 (0.00 to 0.25) | 9 / 3 | 0.07 |

  - **MITI behavior codes:**
    - *Persuade without permission*, i.e. pushing treatment or quitting unasked: **13% of default replies → 0%**
      with the MI prompt.
    - *Emphasize autonomy:* 62% → 88%.
    - *Affirm:* 48% → 72%.
  - Helpfulness did not drop, so the warmer style didn't cost usefulness.
- **Figures:** `fig1_rubric_by_condition`, `fig4_paired_change`.
- **Caveat:**
  - The MI prompt uses the same vocabulary as the rubric (autonomy, non-judgment), so part of the gain may be
    the model "speaking the rubric's language" to a judge that rewards it.
  - Your hand scores are the check on this.

## Finding 2: RAG grounding helped a little, less than the MI prompt
- **Question:** does adding retrieved guidance and stigma literature make replies warmer, or more clinical?
- **Result:** RAG minus default, with Holm-corrected p.

  | Dimension | Difference (95% CI) | Better / worse | p (Holm) |
  |---|---|---|---|
  | Empathy | +0.15 (0.05 to 0.25) | 10 / 1 | 0.03 |
  | Non-judgment | +0.15 (0.07 to 0.25) | 9 / 0 | 0.01 |
  | Harm reduction | +0.15 (0.02 to 0.28) | 14 / 5 | 0.12 |
  | Autonomy | +0.12 (−0.02 to 0.25) | 11 / 4 | 0.14 |
  | Helpfulness | +0.07 (−0.07 to 0.20) | 8 / 5 | 0.32 |

  - Persuade-without-permission fell from 13% to 3%.
  - RAG did **not** make replies more clinical or preachy. Changes were almost always 0 or +1.
- **Figures:** `fig1`, `fig4`.
- **Caveat (circularity):**
  - The RAG corpus includes TIP 35 and NIDA *Words Matter*, which are partly the same sources the rubric is
    built from.
  - So RAG sometimes hands the model the grading criteria. That makes this an upper bound on the benefit of
    grounding.

## Finding 3: Stigmatizing language was rare, and a naive word counter got it wrong
- **Question:** how often do replies use stigmatizing terms the sender didn't use first? This replicates
  Wang et al. 2025.
- **Result:** any unprompted stigmatizing term, per condition.

  | | Default | RAG | MI prompt | Wang et al. 2025 |
  |---|---|---|---|---|
  | **Corrected count** | **3%** (1.7–13.7%) | **3%** | **0%** (0–6%) | 35.4% default, 6.3% prompt-engineered |
  | First (naive) count | 8% | 18% | 2% | n/a |

  - None of the differences are statistically significant: McNemar p = 1.0 for RAG vs default and p = 0.5 for
    MI vs default.
  - **The method finding:** the naive count made it look as if RAG *tripled* stigma. Reading every hit showed
    the replies were advising families *against* labels, for example *Avoid labels like "addict" or
    "junkie"* (RAG had retrieved Words Matter).
    - After the fix, a quoted or "labels like…" mention isn't counted (`results/decisions.md` #13).
    - Advising against labels happened in 9 RAG replies, 5 default and 2 MI.
    - Any study that counts words automatically, possibly including Wang's, can mistake *teaching about
      stigma* for *stigma*.
  - **Remaining 4 hits, which need your ruling:** "heavy users" (default), "the habit" ×2 (default and RAG),
    and "one clean test" (RAG; this one is about drug-checking a pill, not a person's drug test).
- **Figures:** `fig2_stigma_rate_by_condition`, `fig5_length_vs_stigma`.
- **Caveat:**
  - This is not a like-for-like replication. Wang used 14 LLMs and clinician-written questions; we used one
    newer model and first-person messages.
  - With only 4 hits, Wang's "longer replies have more stigma" analysis can't be tested here.

## Finding 4: No over-caution at all
- **Result:** 0 of 180 replies refused, hedged most of the answer, or just dumped hotline numbers. The 95% CI
  is 0–6% per condition.
- **Figure:** `fig6_overcaution`.
- **What it means:**
  - Sonnet 5.5 engages directly, even with questions such as safer use or mixing.
  - The over-caution problem described in older-model studies didn't show up here.
- **Caveat:** our messages may be milder than real ones. Your review of the messages matters here.

## Finding 5: No reliable differences by substance or by sender
- **Substance:**
  - No Friedman test across substances was significant after Holm correction.
  - The lowest cell: meth, default condition, harm reduction 4.1 vs 4.5–4.8 for the others (uncorrected
    p = 0.02, Holm p = 0.36).
  - This is worth a look with more messages, because meth replies may lean more toward "you should stop".
- **Sender (person vs family):** no meaningful differences.
- **Figure:** `fig3_substance_heatmap`. Tables: `table_by_substance.csv`, `table_substance_friedman.csv`,
  `table_sender.csv`.
- **Caveat:** with 10 messages per substance per condition, only large effects could be detected.

## The big picture: a ceiling effect
- Default Claude already scores 4–5 on almost everything.
  - 80% of default replies got non-judgment 5.
  - No reply in any condition scored below 3.
- The interesting differences are in the *upper* range: autonomy and empathy, i.e. whether the model nudges
  toward treatment and whether it reflects the person's feelings.
- **To separate conditions more clearly, the next round needs harder messages,** for example:
  - hostile messages
  - requests for specific dosing
  - "I don't want to stop"
  - messages using stigmatizing words about oneself

## Validation of the judge
- **AnnoMI check:**
  - On 43 real counseling transcripts that experts labeled as high or low MI quality, the judge's scores
    separated the two almost perfectly.
  - AUC: empathy 0.99, autonomy 0.96, non-judgment 0.92, mean of the three 0.98 (high 3.83 vs low 1.42).
  - This passes PLAN.md's 0.75 threshold.
  - Figure: `fig7_judge_validation`.
- **Still pending:** agreement with *your* hand scores on 30 replies (weighted kappa), from
  `eval/compute_agreement.py`. AnnoMI shows the judge can tell good MI from bad. It doesn't show the judge
  grades AI replies the way a harm-reduction worker would.

## Study 2A: substance inference (pipeline check, **not a finding**)
- **Task:** guess the substance from messages with drug names masked.
  - TF-IDF + logistic regression: **28%** (cross-validated by held-out scenario).
  - Claude Haiku zero-shot: **45%** (21 answered "unsure").
  - Chance: 17%.
- These numbers only measure the substance clues we wrote into our own templates, so they are not evidence
  about real writing. Real data needs Erowid's permission (draft email: `study2/erowid_permission_email.md`).
- See `study2/results.md` and `fig8_study2_confusion`.
- **Dual-use:** inferring what someone uses from how they write could be used for surveillance or profiling.
  This project never builds anything that profiles identifiable people, and any write-up must say so.

## Limitations (say these up front)
1. **AI-written messages.** All 60 are AI-written composites, labeled as such everywhere. Real messages are
   messier, angrier and more ambiguous.
2. **Same-vendor judge.** The judge is Claude Opus judging Claude Sonnet, so a vendor-level style preference is
   possible. AnnoMI validation helps; your hand scores are the stronger check.
3. **Circularity.** The rubric, the RAG corpus and the MI prompt share sources and vocabulary (see Findings 1
   and 2).
4. **One model, one sample per message.** There was no temperature control (the API rejects it on this model;
   decisions #1), and each condition got a single reply per message.
5. **Ceiling effects** limit how much any condition can improve.
6. **The stigma counter misses some terms.** "Addicted" and "MAT" are not counted. Mention vs use is handled
   with a simple quote/"labels like" rule.

## Where everything is
| File | Contents |
|---|---|
| `results/judged.csv` | One row per reply: rubric scores with the judge's reasons, behavior codes, stigma counts |
| `results/responses.jsonl` | All 180 replies, with the retrieved excerpts for RAG |
| `results/table_*.csv`, `results/summary.json` | All statistics |
| `results/decisions.md` | Every deviation from PLAN.md, and why |
| `figures/` | 8 figures plus `figures/README.md` |
