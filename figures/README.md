# Figures

Every figure is saved as PNG (300 dpi) and SVG. Colors: blue = default assistant, orange = with guidance (RAG),
green = MI-style prompt. All Study 1 figures use 60 **AI-written composite messages** (not real people's words).

| File | What it shows | Takeaway |
|---|---|---|
| `fig1_rubric_by_condition` | Mean judge score (1–5) with 95% CI for each rubric dimension and condition | Everything is near the ceiling (4–5). The MI prompt is highest on every dimension, with its biggest gain on autonomy (+0.6). RAG gives small gains. |
| `fig2_stigma_rate_by_condition` | % of replies with any unprompted stigmatizing term, with Wang et al. 2025 reference lines | Stigmatizing terms were rare: 0% default, 2% RAG (1 reply), 0% MI after review, far below Wang's 35% (different design, so the lines are context only). |
| `fig3_substance_heatmap` | Mean score per substance × dimension, per condition | No reliable differences between substances (Friedman tests not significant after Holm). Meth/default harm reduction (4.1) is the lowest cell. |
| `fig4_paired_change` | For each message, how much empathy and non-judgment changed vs default | Changes are almost all 0 or +1, and almost never negative: RAG and the MI prompt rarely made a reply worse. |
| `fig5_length_vs_stigma` | Reply length vs whether it contained a stigmatizing term | Only 1 of 180 replies had a term after review, too few to fit a model. Wang's length effect can't be tested here. |
| `fig6_overcaution` | % of replies judged over-cautious, by sender and condition | 0 of 180. No refusals or hotline-dumping in any condition. |
| `fig7_judge_validation` | Judge scores on AnnoMI real counseling transcripts (expert-labeled high vs low MI quality) and ROC curves | The judge separates good from poor MI almost perfectly (AUC 0.98), so its scores track a real quality signal. |
| `fig8_study2_confusion` | Study 2A: predicted vs true substance from masked messages | **Pipeline check only, not a finding.** It runs on our own template messages. |
| `fig9_hripbench_safety` | HRIPBench replication: Claude's safety-boundary accuracy vs the paper's 11 models, plus which way Claude's errors go | Claude matches the paper's best models (Sonnet 87.3%). Its errors are mostly over-cautious ("not safe" when the source says safe), rarely risky. |
| `fig10_wang_replication` | Wang et al. 2025 replication: % of replies with stigmatizing language, native vs engineered prompt, Claude vs Wang | Native 20–22% (Wang 35%); one anti-stigma prompt brings it to 0–1.7% (Wang 6.3%). |
| `fig11_hard_vs_main` | Mean judge score per dimension and condition, main set vs the 30 harder messages | Shows whether harder messages break the ceiling effect, and whether the MI prompt's advantage holds. |
