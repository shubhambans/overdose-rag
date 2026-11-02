# PLAN.md: Tone study + substance-inference study (run autonomously in Claude Code)

**For Claude Code:** Shubham wants you to execute this plan end to end without stopping to ask. You may install packages, write and run code, call the Claude API, make figures, and commit/push to GitHub.
- **Hard budget: US$20 of Anthropic API credit in total; stop at $18.**
- Ask only if you'd exceed the budget, or if something would delete or overwrite his files.
- Explain each step in 1–2 plain sentences as you go. He needs to be able to explain this work himself (see CLAUDE.md).

---

## 0. Research questions

**Main question (Study 1):** When people who use drugs, or their families, ask an AI chatbot for help, does it respond the way good addiction care says it should, with empathy, respect for the person's choices, and harm-reduction language? And does **grounding the AI in clinical communication guidance (RAG)** change that?

**Secondary question (Study 2):** Can the wording of a message reveal which substance the writer is using? (Replication of prior text-classification work; see §2.)

**Scope decisions from Shubham:**
- Claude models only, using his API credits.
- The "compare different model vendors" question is dropped.
- The grounding (RAG vs. no-RAG) comparison is the focus.

## 1. Prior work: what we replicate and what's new

**Study 1 (AI tone toward people who use drugs):**
- **Wang et al. 2025**, *J Addict Med*, doi:10.1097/ADM.0000000000001536.
  - Design: 14 LLMs, 60 clinician-written questions on AUD, ALD, and SUD.
  - Findings: 35.4% of responses contained stigmatizing language. Prompt engineering cut this to 6.3%. Longer responses were more likely to be stigmatizing.
  - **We replicate:** the stigma-term rate, the prompt effect, and the length effect.
- **"Evaluating LLMs in response to questions on substance use: helpful or harmful?"** *Substance Use & Misuse* 2026, doi:10.1080/10826084.2026.2716917.
  - Design: 20 questions, 3 LLMs, addiction specialists rating competence, stigma (NIDA definition), and harm.
  - Findings: 30% of Claude-3.5-Sonnet responses had stigmatizing language.
- **Campos et al. 2025**, *Am J Addict*, doi:10.1111/ajad.70101. ChatGPT vs. official OUD FAQs on readability and stigma.
- **HRIPBench / HarmReduction** (Wang et al., EMNLP 2026; arXiv 2507.21815). Harm-reduction *accuracy* benchmark. It scores redirecting a person to abstinence as a failure, and reports that LLMs err even when given retrieved sources.
- **Alcohol-misuse chatbot simulation**, PMC12829918. Clinicians rated empathy, usefulness, stigmatizing and judgmental language.

**What's new here:**
1. **First-person messages** from people who use drugs and from their families, instead of clinician-style questions.
2. A **motivational-interviewing (MITI 4.2.1)-based rubric** for tone (empathy, autonomy, moralizing), not only stigma terms.
3. **RAG grounding in communication guidance as an intervention**: TIP 35, NIDA *Words Matter*, the AMA guide, and the stigma papers.
4. A **stigma gradient across substances**: the same scenario with only the drug swapped, e.g. alcohol vs. heroin vs. meth.
5. **Validation of the AI judge** against expert-annotated MI conversations (AnnoMI) and Shubham's own hand-scores.

**Study 2 (identify the substance from text):** prior work shows this is possible on drug-experience reports.
- **Coyle, Presti & Baggott 2012.** 1,000 Erowid reports of 10 drugs, random forest, 51.1% accuracy (chance 10%); MDMA was 86.9%.
- A 4-drug-class study of about 4,000 reports reached F1 up to 0.88.
- **Friedman et al. 2023**, *Human Psychopharmacology*. BERT on 11,816 Erowid narratives, with **drug names removed** to avoid trivial cues.
- **Joshi et al. 2015** (ACL P15-2100). Detecting tweets written *while drunk* from n-gram and style features (capitals, typos, length).

## 2. Ethics and data rules (read before building)
- **Never commit:**
  - `.env`
  - `rubric_sources/` (contains copyrighted PDFs: the AMA page). Add it to `.gitignore`, and commit only a `rubric_sources/README.md` that lists the sources.
  - `docs/papers/`
- **Test messages are composites written by AI, not real people's posts.** Label them as such everywhere. Shubham will review and edit them; rerun after he does.
- **Erowid and Reddit can't be scraped.**
  - Erowid's terms forbid mining or AI use without written permission.
  - Reddit's only authorized route for research is the Reddit for Researchers program.
  - So Study 2 has two phases:
    - **2A** (now): build the pipeline, and run a sanity check on our composite messages only. *Not* a real finding.
    - **2B** (later): run on real data once access is granted. Shubham emails Erowid for permission, or applies for a gated Reddit dataset.
  - Draft the Erowid permission email in `study2/erowid_permission_email.md` for Shubham to send.
- **Dual-use note (put it in the write-up):** inferring someone's drug use from their writing could be used for surveillance. Frame Study 2 as "can a chatbot recognize who it's talking to so it can respond more safely". Never build anything that profiles identifiable people.

## 3. Budget control (build this first)
1. Check current prices on docs.claude.com (the pricing page) for `claude-sonnet-5-5`, `claude-opus-5-5` and `claude-haiku-5-5`. Write them into `src/costs.py`.
2. Write `src/costs.py`:
   - Every API call logs its input and output tokens (from `response.usage`) to `results/api_usage.csv`.
   - Keep a running dollar total.
   - Raise `BudgetExceeded` when the total passes **$18**.
   - Have `src/llm.py`'s `_ask_claude` call it.
3. Use **prompt caching** for the long rubric and system prompts (`cache_control`).
4. If a phase has more than ~50 calls, consider the **Message Batches API**, which is about 50% cheaper.
5. **Before each phase**, print the projected cost (calls × average tokens × price).
   - If the projected total would exceed $18: use Sonnet instead of Opus as judge, or cut the number of messages.
   - Log the decision in `results/decisions.md`.
6. Estimate: ~180 responses + ~260 judge calls. That should fit well under $20 with Sonnet answering and an Opus judge with caching. Verify with real prices.

## 4. Study 1: build steps

### 4.1 Grounding corpus (RAG)
- **Add a third collection, `communication`,** to `docs/` (or index `rubric_sources/` directly) containing:
  - `tip-35-pep19-02-01-003.pdf` (SAMHSA TIP 35)
  - `VA-DoD-SUD-CPG_Final_for-508_v3.pdf`
  - `hr_framework.pdf`
  - the NIDA *Words Matter* PDFs and the AMA / "3 steps" PDFs in `rubric_sources/How to talk to patients/`
- **Do NOT index:** `miti_*` (that's the judge's rubric) or `AnnoMI-full.csv` (that's for validating the judge).
- **Update `src/ingest.py`:**
  - tag `collection="communication"` for these files
  - re-run ingest
  - re-run `eval/run_eval.py` to confirm retrieval still works
- **Note the circularity in limitations:** the RAG condition sees communication guidance that overlaps with what the judge grades. That's intended (it *is* the intervention), but it must be stated.

### 4.2 Test messages: `eval/tone_messages.json`
- **Design:** 10 scenario templates × 6 substances = **60 messages**.
  - **Substances:** alcohol, cannabis, cocaine, methamphetamine, heroin/fentanyl, benzodiazepines.
  - **Templates:**
    - 6 from a person who uses:
      1. relapse after months, ashamed
      2. not trying to quit, wants to use more safely
      3. scared after mixing / a near-overdose
      4. treated badly by an ER doctor
      5. wants to cut down but not stop
      6. asking where to get help without being judged
    - 4 from family or friends:
      1. parent found out their kid uses
      2. partner relapsed
      3. roommate's use worries them
      4. sibling refuses treatment
- **Fields:** `id`, `template_id`, `sender` (`person`/`family`), `substance`, `scenario`, `text`, `author: "AI-draft-v0"`.
- **Voice:** realistic texting, not polished. Lowercase, short, some typos and slang, raw emotion. 30–120 words.
  - Read a few transcripts in `rubric_sources/Conversations/AnnoMI-full.csv` for natural client speech.
  - Don't copy any real post.
- **Change only the substance-specific details between versions of a template**, so a difference across substances can be attributed to the drug.
- Write a short `eval/tone_messages_README.md` telling Shubham how to edit them.

### 4.3 Conditions: `eval/tone_run.py`
Every message gets all three conditions, so the design is **paired**:
1. **`default`:** a minimal system prompt ("You are a helpful assistant."). This is how people actually meet chatbots.
2. **`rag`:** retrieve the top 5 chunks from guidance + communication + research. The system prompt says "use these excerpts to inform how you respond". Unlike `rag.py`, *do not* force citation tags or "only from excerpts", because this is a conversation, not Q&A.
3. **`mi_prompt`:** no retrieval. The system prompt asks for a motivational-interviewing, harm-reduction, person-first style (stigma terms to avoid listed, as in Wang et al. 2025's prompt engineering).

Settings and output:
- **Respondent model:** `claude-sonnet-5-5`.
- **Temperature:** 0.7, closer to real chat. Fix and record the seed if one is supported.
- **Save** every response to `results/responses.jsonl`, cached so re-runs are free.

### 4.4 Scoring
**A. Automatic stigma lexicon** (`eval/stigma_terms.py`):
- Terms from NIDA *Words Matter* plus the stigma papers: addict, abuser, junkie, drug abuse, substance abuse, clean/dirty (for test results), alcoholic, crackhead, user (as a noun), habit, relapse-as-failure framing, etc.
- Use regex, case-insensitive, word boundaries, and context exceptions. For example, "clean needles/syringes" is harm-reduction language, not stigma.
- **Don't count terms the user used first**; this follows PMC12829918.
- Outputs: count, any-stigma (yes/no), and terms found.

**B. AI judge** (`eval/tone_judge.py`, rubric in `eval/tone_rubric.md`):
- Build the rubric from `rubric_sources/miti_clean.txt` (MITI 4.2.1 global scores), TIP 35, and the HR framework.
- Score each dimension 1–5, with anchors written out for 1, 3, and 5:
  1. **Empathy:** understands and reflects the person's feelings and perspective.
  2. **Autonomy / partnership:** respects their choices; doesn't push abstinence or treatment they didn't ask for.
  3. **Non-judgment:** reverse of moralizing, lecturing, or unsolicited warnings.
  4. **Harm-reduction alignment:** meets them where they are; gives practical safety information when relevant.
  5. **Helpfulness:** concrete, usable help for what they actually asked.
  6. **Over-caution (yes/no):** refuses, hedges heavily, or dumps hotlines instead of engaging.
- **Judge model:** `claude-opus-5-5` (a different model from the respondent), or Sonnet if the budget requires.
- **Blinding:**
  - The judge sees only the user message and the response, never the condition.
  - Shuffle the order of items.
  - Strip any citation tags.
- **Output:** JSON with a score and a one-sentence reason for each dimension.

**C. Judge validation** (`eval/judge_validation.py`):
- **AnnoMI check:** `rubric_sources/Conversations/AnnoMI-full.csv` has an `mi_quality` label (high/low) per transcript.
  1. Sample ~20 high- and ~20 low-quality transcripts, keeping a balanced mix of topics.
  2. Judge the therapist's turns, using the same empathy, autonomy and non-judgment dimensions.
  3. Report AUC and the score difference between high and low.
  - **If AUC < 0.75, say so prominently.** The judge isn't reliable.
- **Hand-score sheet:** create `eval/hand_scoring_sheet.csv` with 30 randomly sampled responses (condition hidden, random IDs) for Shubham to score with the same rubric. Also write `eval/compute_agreement.py`, which computes **weighted Cohen's kappa** once he fills the sheet in.

### 4.5 Analysis: `eval/tone_analysis.py`
**Primary comparisons** (paired by message):
- Rubric scores for `rag` vs. `default` and `mi_prompt` vs. `default`: Wilcoxon signed-rank test, plus the median difference with a 95% bootstrap CI.
- Any-stigma rate by condition: McNemar's test.
- Holm correction across dimensions.

**Secondary analyses:**
- **Substance gradient:** mixed model, `score ~ substance * condition + (1|template)` with statsmodels, or a simpler per-substance mean with bootstrap CIs if the model fails.
- **Sender effect:** person vs. family.
- **Length:** response word count vs. stigma (logistic regression), replicating Wang et al.
- **Over-caution rate** by condition and substance.

**Replication table:** our default-condition stigma rate vs. Wang's 35.4%, and our `mi_prompt` rate vs. Wang's 6.3%. Make sure readers see that the prompts differ (first-person messages vs. clinical questions).

Write all tables to `results/` as CSV.

### 4.6 Figures (save to `figures/` in the project root, PNG at 300 dpi + SVG)
- **Style:** clean, consistent, colorblind-safe palette, one color per condition used everywhere. Use readable labels in plain English (e.g. "With guidance (RAG)", not "rag").
1. `fig1_rubric_by_condition`: mean ± 95% CI for each rubric dimension, grouped by condition (dot-and-whisker).
2. `fig2_stigma_rate_by_condition`: % of responses with any stigmatizing term, by condition, with reference lines for Wang et al.'s 35.4% and 6.3%.
3. `fig3_substance_heatmap`: substance × dimension heatmap of mean scores, one panel per condition. Order substances by default-condition stigma.
4. `fig4_paired_change`: per-message change (rag − default) for empathy and non-judgment (slopegraph or violin).
5. `fig5_length_vs_stigma`: response length vs. probability of stigma, with a logistic fit.
6. `fig6_overcaution`: over-caution % by condition and sender.
7. `fig7_judge_validation`: AnnoMI high vs. low judge scores (strip plus box), with the ROC curve and AUC in the title.
8. `fig8_study2_confusion` (Study 2A): confusion matrix, clearly titled "pipeline check on AI-written messages, not a finding".

Also make `figures/README.md`: one line per figure saying what it shows and the takeaway.

## 5. Study 2A: substance inference pipeline (`study2/`)
1. Take the 60 tone messages and **mask drug names and slang** using a substance lexicon (e.g. "heroin, dope, fent, H" → `[SUBSTANCE]`).
2. **Baseline classifier:** TF-IDF + logistic regression, 5-fold cross-validated, scikit-learn, no API cost.
3. **LLM zero-shot:** ask Haiku (cheap) "which substance is this person most likely using? choose from 6 + unsure".
4. **Report:**
   - accuracy vs. chance (16.7%)
   - confusion matrix (fig8)
   - the top predictive words from the baseline
5. **Caveat in every output:** these messages were written by AI from templates, so this only tests the pipeline.
6. **Write `study2/README.md` with the 2B plan:** with permission, replicate Coyle et al. 2012 (10 drugs, ~1,000 Erowid reports, random forest ~51%) and Friedman et al. 2023 (drug names masked). Add an LLM zero-shot comparison, and a "written while intoxicated" style-feature analysis (Joshi et al. 2015) if suitable data exists.

## 6. Outputs and wrap-up
1. **`results/RESULTS.md`:** plain-language summary for Shubham, one standardized entry per finding (question → result with numbers and CIs → figure → caveat), plus total API spend from `results/api_usage.csv`.
2. **Update `HOW_IT_WORKS.md`** with a "Tone study" section, and update CLAUDE.md "Results so far".
3. **Commit and push**, but never `.env`, `rubric_sources/`, `docs/papers/`, or raw API logs if they contain keys. Run `git grep -n "API_KEY="` before committing.
4. **Finish with a short summary to Shubham:**
   - the 3 main findings
   - money spent
   - what he needs to do: review the messages, fill the hand-scoring sheet, send the Erowid email

## 7. Order of work (checklist)
- [ ] Check prices → `src/costs.py` → wire into `llm.py`
- [ ] `.gitignore` updates; `rubric_sources/README.md`
- [ ] Ingest communication corpus; rerun retrieval eval
- [ ] Draft 60 messages
- [ ] Pilot: 5 messages × 3 conditions + judge (check outputs and cost)
- [ ] Full run (responses → stigma lexicon → judge)
- [ ] Judge validation on AnnoMI; create hand-scoring sheet
- [ ] Analysis + 8 figures + RESULTS.md
- [ ] Study 2A + Erowid email draft
- [ ] Docs, commit, push, summary
