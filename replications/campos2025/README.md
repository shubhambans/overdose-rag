# Replication: Campos et al. 2025 (ChatGPT vs official opioid FAQs)

**Original:** Campos VM, Heringer DL, Costa GPA, Oliva HNP, Anand A. *Readability, linguistic complexity, and stigma in
ChatGPT responses to opioid use disorder FAQs: A comparative analysis.* Am J Addict 2026;35(3):362–369.
doi:10.1111/ajad.70101. PMID 41189042.

**Type: conceptual replication.**
- **Copied exactly:**
  - the design: an official FAQ answer paired with the chatbot's answer to the same question;
  - all outcome measures: word and sentence counts, lexical density, characters and syllables per word, the six
    readability indices, and stigma terms;
  - the statistics: paired t test, or Wilcoxon when the differences aren't normal.
- **Not copied:** their 50 FAQs, which aren't published (the paper is paywalled). Ours are 50 *real, verbatim*
  official Q&As from the same kinds of sources.

## What we did
1. **FAQs (`faqs_index.csv`, rebuilt with `build/`):**
   - **Sources:** 50 OUD Q&As copied word for word from 10 organizations.
     - 25 federal: NIDA ×21, MedlinePlus ×3, VA ×1.
     - 14 state: CT, OR, PA, WA.
     - 8 academic: Yale Medicine, Cleveland Clinic.
     - 3 professional society: AAFP.
   - **Not included:** SAMHSA and CDC block scripted downloads.
   - **Checking:** every 6-word stretch of each answer was checked against the source page.
   - **Answer texts:** kept local (`faqs.csv`, git-ignored) because some are copyrighted. The index lists
     questions and URLs.
2. **Claude answers:** each question was sent with **no system prompt**, as someone would type it into a chatbot,
   to:
   - Claude Sonnet 5.5 (the model class behind Claude.ai);
   - Claude Haiku 5.5.
   - **Extension, not in Campos:** Sonnet with a plain-language instruction (6th–8th grade). This tests the
     authors' own recommendation of "plain language prompting".
3. **Measures:** `run.py`, using `textstat` for the readability indices. Markdown is stripped first.
4. **Stigma:** `eval/stigma_terms.py` (NIDA *Words Matter*, plus the mention-vs-use and mirroring rules).

## Results (50 paired questions; Claude minus FAQ, with bootstrap 95% CI)
| Measure | FAQ | Sonnet 5.5 | Haiku 5.5 | Sonnet + plain-language prompt | Campos: ChatGPT minus FAQ |
|---|---|---|---|---|---|
| Words | 117 | 339 (+222, 199 to 247) | 312 (+195) | 192 (+75) | +177 |
| Flesch–Kincaid grade (main scoring) | 11.3 | 9.6 (**−1.8**, −2.6 to −1.0) | 10.5 (−0.9, ns) | **4.5 (−6.8)** | **+3.6** |
| Flesch–Kincaid grade (sensitivity: bullets not split) | | **+2.7** | +0.9 | −6.0 | +3.6 |
| SMOG grade (main) | 13.1 | 11.7 (−1.3) | 12.6 (−0.5, ns) | 8.1 (−5.0) | +3.0 |
| Flesch Reading Ease (higher = easier) | 48.8 | 47.3 (−1.5, ns) | 46.0 (−2.8, ns) | **78.6 (+29.9)** | −20.4 |
| Stigma terms per answer | 0.02 | 0.06 | 0.02 | 0.04 | 0.98 vs 0.28 |

Full tables: `results/table_paired_differences.csv` and `results/table_sensitivity_no_line_split.csv`.

## What it means
1. **Length replicates:** Claude's answers are 2.7–2.9× longer than the official FAQs, the same pattern as
   ChatGPT.
2. **Readability depends on how you score bullet points.**
   - Claude formats its answers as bulleted lists.
   - **Main scoring:** each bullet or heading counts as its own sentence. Claude then scores *easier* than the
     FAQs.
   - **Sensitivity scoring:** bullets run on into each other. Sonnet then scores 2–4 grades *harder*, close to
     Campos's ChatGPT result.
   - Readability formulas were built for prose, and Campos doesn't say how they handled formatting. This is a
     methodological finding: report both scorings.
3. **A one-line plain-language prompt fixes most of it.** Reading level drops to about 4th–5th grade, below the
   6th–8th grade health-literacy target, and answers shrink by 43%. This supports Campos's recommendation.
4. **Stigma is rare on both sides.**
   - **Claude's remaining hits:** "users" describing a group (5) and "one part may test clean", about
     drug-checking a pill (1).
   - **Official FAQs:** one Cleveland Clinic answer uses "substance abuse".
   - **Shubham to confirm:** by his earlier rulings, "users" for a group is not stigma, while "test clean" counts.

## Limitations
- The FAQ set is ours, not Campos's.
  - It leans on NIDA (21/50).
  - Our official answers are longer (117 vs their 77 words).
- One sample per question; no temperature control (the API rejects it).
- Readability formulas are crude for any formatted text.
