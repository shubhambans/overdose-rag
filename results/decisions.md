# Decisions log (deviations from PLAN.md and why)

**2026-11-02**

1. **No temperature 0.7.**
   - The current Claude API rejects non-default `temperature` on Claude Sonnet 5.5 (400 error) and is removing
     sampling parameters on every model.
   - Responses use default sampling, with adaptive thinking on (the model's default) and default effort.
   - No seed is available.
2. **Prices** (`src/costs.py`), per 1M tokens, from Anthropic's model table (cached 2026-10-06):
   - Sonnet 5.5: $2 in / $10 out
   - Opus 5.5: $4 in / $20 out
   - Haiku 5.5: $0.10 in / $0.50 out
   - Cache reads $0.20 (Haiku's assumed at 0.1× input). Cache writes 1.25× input.
   - Thinking tokens bill as output.
   - Hard stop $18.
3. **No Batch API.**
   - The pilot measured about $0.01 per response and $0.03 per judge call.
   - Projected total for responses, judge, AnnoMI validation and Study 2: about $9, well under budget.
   - Synchronous calls with prompt caching on the judge rubric were simpler and let us inspect results as they
     came in. Batching would have saved roughly $3.
4. **Judge = Claude Opus 5.5 at effort "medium"** (its default), with the full rubric as a cached system prompt.
   Respondent = Sonnet 5.5, so the judge is a different model, though from the same vendor (see limitations).
5. **Messages are AI-written** (Shubham has no message dataset): 10 templates × 6 substances, `author = AI-draft-v0`.
   Shubham will review and edit them, then we re-run (cached, so only edited messages cost money).
6. **SAMHSA Harm Reduction Framework not obtained.**
   - SAMHSA and the county mirror both block scripted downloads.
   - The `hr_framework.pdf` in `rubric_sources/` was a 404 page saved by an earlier blocked download attempt. It was
     deleted, which is why it is missing from the RAG corpus.
   - The rubric's harm-reduction dimension rests on Chang et al. 2023 and TIP 35.
7. **The communication collection is indexed in place from `rubric_sources/`** (not copied into `docs/`), so the
   copyrighted files stay git-ignored. MITI and AnnoMI are deliberately not indexed.
   - Index: 2,004 chunks (1,054 communication).
   - Retrieval eval after adding it: rerank hit@5 100%, hit@1 94%, MRR 0.96 (was 0.97).
8. **statsmodels unavailable** (no Windows ARM64 wheel, no compiler).
   - The mixed model is replaced by PLAN.md's fallback: per-substance means with bootstrap CIs, plus a Friedman test
     across substances blocked by scenario.
   - Logistic regression uses scikit-learn, with a bootstrap CI for the odds ratio.
9. **Study 2A cross-validation is grouped by scenario** (5 folds, each holding out 2 whole templates), not random.
   A random split leaks, because the other five versions of the same template would be in the training data.
10. **AnnoMI sample:** all 23 low-quality transcripts, plus 20 high-quality ones chosen to match topics where possible
    and to be no longer than the longest low-quality one (to limit length as a cue). Each transcript is cut to its
    first ~1,500 words (MITI rates a segment).
11. **Over-caution is yes/no** (per PLAN.md). Rubric v0.1 had a 1–5 scale; the anchors are kept to define the cut-off.
12. **Environment fix.**
    - A Windows user-level `ANTHROPIC_API_KEY` (24 characters, not a valid key) was overriding `.env`.
    - `src/llm.py` now gives `.env` priority for `*_API_KEY`.
    - Shubham should delete the Windows variable, per CLAUDE.md.
13. **Stigma counter: mention vs. use** (fixed after the full run, before writing up).
    - The first count showed RAG *raising* stigma (18% of replies vs 8% default).
    - Reading every hit showed most were false positives: the replies were *advising against* labels
      (*Avoid labels like "addict" or "junkie"*), plus "non-alcoholic beer".
    - Fix: a term inside quotation marks, or right after "labels/words like", is not counted. Counted
      separately as `label_mentions` (default 5, RAG 9, MI 2 replies). 22 self-tests.
    - Raw (before) vs corrected (after) any-stigma rate: default 8% → 3%, RAG 18% → 3%, MI 2% → 0%.
    - The RAG effect was an artifact: the retrieved "Words Matter" guidance made the model coach families
      about language. A plain word counter can't tell coaching from labeling, and Wang et al. 2025's
      counter may share this problem.
    - The remaining 4 hits were ruled on by Shubham (`eval/stigma_rulings.csv`, applied in `tone_judge.py`):
      - "heavy users" and "the habit" ×2: not stigma in context;
      - "one clean test": counts.
    - Final rates: default 0%, RAG 2%, MI 0%.
14. **Length vs. stigma: no logistic fit when there are fewer than 10 events.**
    - With 4 stigma replies out of 180, the odds ratio's CI ran from 0.5 to 15.8, i.e. noise.
    - The rule of thumb is ≥10 events per predictor. The point-biserial correlation is still reported
      (r = 0.08, p = 0.29).
