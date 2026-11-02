# Study 2: Can the wording of a message reveal the substance?

**Why ask this (framing):** if a chatbot can tell from how someone writes what they're probably using, it could
respond more safely. For example, it could mention fentanyl test strips to someone who uses opioids without them
having to say so. **Dual-use warning:** the same ability could be used for surveillance, e.g. profiling people from
their posts. This project never builds anything that profiles identifiable people, and every write-up must state
this risk.

## 2A: pipeline check (done, `substance_inference.py`)
- **NOT A FINDING.** It runs on our 60 AI-written template messages, where only substance-specific details differ,
  so accuracy only reflects how much substance information we wrote into those slots.
- **Pipeline:**
  1. Mask drug names and slang with `[SUBSTANCE]` (following Friedman et al. 2023).
  2. Baseline: TF-IDF + logistic regression, cross-validated by held-out scenario.
  3. Claude Haiku 5.5 zero-shot.
- **Results:** `results.md`, `predictions.csv`, and `figures/fig8_study2_confusion.png`.

## 2B: real data (needs permission first)
**Data access.** Scraping is not allowed:
- Erowid's terms forbid mining or AI use without written permission. Shubham sends `erowid_permission_email.md`.
- Reddit's authorized route for research is the **Reddit for Researchers** program, or a published gated dataset
  with its own data-use agreement.

**Plan once data is available:**
1. **Replicate Coyle, Presti & Baggott (2012).**
   - Their design: 10 drugs, ~1,000 Erowid experience reports, random forest.
   - Their results: 51.1% accuracy (chance 10%), MDMA 86.9%.
   - Use the same drug set if possible, and report per-drug accuracy.
2. **Replicate Friedman et al. (2023), *Human Psychopharmacology*.**
   - Their design: BERT-family classifier on Erowid narratives with drug names removed.
   - Reuse our `mask()` function and extend the lexicon from the real data.
   - Inspect the top features for leakage (residual names, dosage units unique to one drug).
3. **New: LLM zero-shot comparison.**
   - Run Haiku (or Sonnet) on the same masked reports, with an "unsure" option.
   - Measure accuracy and calibration against the supervised models.
4. **Optional: "written while intoxicated" style features (Joshi et al. 2015, ACL P15-2100).**
   - Features: capitals, typos, length, punctuation.
   - Only if a dataset has trustworthy labels for state at time of writing; Erowid reports are usually written
     afterwards.
5. **Ethics before running:**
   - IRB/ethics review if required.
   - Store no usernames.
   - Report only aggregate results.
   - Quote no reports verbatim without permission.

## Files
- `substance_inference.py`: 2A pipeline (masking, baseline, LLM zero-shot, figure 8)
- `results.md`, `predictions.csv`: 2A outputs
- `llm_cache.jsonl`: cached Haiku answers (re-runs are free)
- `erowid_permission_email.md`: draft for Shubham to send
