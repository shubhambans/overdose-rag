# Figures

Every figure is saved as PNG (300 dpi) and SVG. Colors: blue = default assistant, orange = with guidance (RAG),
green = MI-style prompt. All Study 1 figures use 60 **AI-written composite messages** (not real people's words).

| File | What it shows | Takeaway |
|---|---|---|
| `fig1_rubric_by_condition` | Mean judge score (1–5) with 95% CI for each rubric dimension and condition | Everything is near the ceiling (4–5). The MI prompt is highest on every dimension, with its biggest gain on autonomy (+0.6). RAG gives small gains. |
| `fig2_stigma_rate_by_condition` | % of replies with any unprompted stigmatizing term, with Wang et al. 2025 reference lines | Stigmatizing terms were rare: 3% default, 3% RAG, 0% MI, far below Wang's 35% (different design, so the lines are context only). |
| `fig3_substance_heatmap` | Mean score per substance × dimension, per condition | No reliable differences between substances (Friedman tests not significant after Holm). Meth/default harm reduction (4.1) is the lowest cell. |
| `fig4_paired_change` | For each message, how much empathy and non-judgment changed vs default | Changes are almost all 0 or +1, and almost never negative: RAG and the MI prompt rarely made a reply worse. |
| `fig5_length_vs_stigma` | Reply length vs whether it contained a stigmatizing term | Only 4 of 180 replies had a term, too few to fit a model. Wang's length effect can't be tested here. |
| `fig6_overcaution` | % of replies judged over-cautious, by sender and condition | 0 of 180. No refusals or hotline-dumping in any condition. |
| `fig7_judge_validation` | Judge scores on AnnoMI real counseling transcripts (expert-labeled high vs low MI quality) and ROC curves | The judge separates good from poor MI almost perfectly (AUC 0.98), so its scores track a real quality signal. |
| `fig8_study2_confusion` | Study 2A: predicted vs true substance from masked messages | **Pipeline check only, not a finding.** It runs on our own template messages. |
