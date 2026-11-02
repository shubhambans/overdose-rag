"""Study 1 analysis: statistics, CSV tables (results/), and figures 1-7 (figures/).

Primary comparisons are PAIRED by message: every message was answered under all three conditions,
so each message acts as its own control.
  - Rubric scores, rag vs default and mi_prompt vs default: Wilcoxon signed-rank test + mean and
    median difference with 95% bootstrap CIs (resampling messages). Holm correction across the 5 dims.
  - Any-stigma rate: McNemar's exact test (only messages where the two conditions disagree count).
Secondary: substance gradient (per-substance means with bootstrap CIs; Friedman test across substances
within each condition, blocked by scenario), sender (person vs family), response length vs stigma
(logistic regression), and over-caution rates.

statsmodels has no prebuilt package for this machine (Windows ARM64), so the mixed model in PLAN.md
is replaced by the per-substance bootstrap means that PLAN.md lists as the fallback.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve

import figstyle as fs

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
DIMS = ["empathy", "autonomy", "nonjudgment", "harm_reduction", "helpfulness"]
SUBS = list(fs.SUB_LABEL)
RNG = np.random.default_rng(2026)
B = 4000
WANG_DEFAULT, WANG_PROMPTED = 0.354, 0.063
CAVEAT = "60 AI-written composite messages (10 scenarios x 6 substances); responses by Claude Sonnet 5.5; scored by Claude Opus 5.5 judge (blinded)."


def boot_ci(values, fn=np.mean, b=B):
    v = np.asarray(values, float)
    if len(v) == 0:
        return np.nan, np.nan
    idx = RNG.integers(0, len(v), (b, len(v)))
    s = np.apply_along_axis(fn, 1, v[idx])
    return np.percentile(s, 2.5), np.percentile(s, 97.5)


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def holm(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(p) - rank) * p[i])
        adj[i] = min(running, 1.0)
    return adj


def mcnemar(a, b):
    """Exact McNemar on paired 0/1 arrays. Returns (n_a_only, n_b_only, p)."""
    a, b = np.asarray(a), np.asarray(b)
    n01, n10 = int(((a == 0) & (b == 1)).sum()), int(((a == 1) & (b == 0)).sum())
    if n01 + n10 == 0:
        return n10, n01, 1.0
    return n10, n01, stats.binomtest(min(n01, n10), n01 + n10, 0.5).pvalue


def load():
    d = pd.read_csv(RES / "judged.csv")
    if "judge_error" in d:
        bad = d.judge_error.notna().sum()
        if bad:
            print(f"Dropping {bad} rows with judge errors")
        d = d[d.judge_error.isna()]
    return d


# ---------------- tables ----------------

def paired_tests(d):
    rows = []
    for comp in ["rag", "mi_prompt"]:
        ps = []
        block = []
        for dim in DIMS + ["overcaution", "any_stigma"]:
            w = d.pivot_table(index="message_id", columns="condition", values=dim)
            w = w[["default", comp]].dropna()
            diff = w[comp] - w["default"]
            row = dict(comparison=f"{comp} vs default", measure=dim, n_pairs=len(w),
                       mean_default=w["default"].mean(), mean_other=w[comp].mean(), mean_diff=diff.mean())
            row["mean_diff_lo"], row["mean_diff_hi"] = boot_ci(diff)
            row["median_diff"] = diff.median()
            row["median_diff_lo"], row["median_diff_hi"] = boot_ci(diff, np.median)
            row["n_better"], row["n_worse"], row["n_same"] = int((diff > 0).sum()), int((diff < 0).sum()), int((diff == 0).sum())
            if dim in ("overcaution", "any_stigma"):
                _, _, p = mcnemar(w["default"], w[comp])
                row["test"], row["p"] = "McNemar exact", p
            else:
                p = 1.0 if (diff != 0).sum() == 0 else stats.wilcoxon(w[comp], w["default"], zero_method="wilcox").pvalue
                row["test"], row["p"] = "Wilcoxon signed-rank", p
                ps.append(p)
            block.append(row)
        adj = holm(ps)
        for r, a in zip([r for r in block if r["measure"] in DIMS], adj):
            r["p_holm"] = a
        rows += block
    t = pd.DataFrame(rows)
    t.round(4).to_csv(RES / "table_paired_tests.csv", index=False)
    return t


def condition_means(d):
    rows = []
    for c in fs.CONDITIONS:
        s = d[d.condition == c]
        r = dict(condition=c, n=len(s), words_mean=s.words.mean())
        for dim in DIMS:
            r[dim] = s[dim].mean()
            r[dim + "_lo"], r[dim + "_hi"] = boot_ci(s[dim])
        k = int(s.any_stigma.sum())
        r["any_stigma_rate"], (r["any_stigma_lo"], r["any_stigma_hi"]) = k / len(s), wilson(k, len(s))
        r["any_stigma_incl_mirrored"] = (s.stigma_total > 0).mean()
        k = int(s.overcaution.sum())
        r["overcaution_rate"], (r["overcaution_lo"], r["overcaution_hi"]) = k / len(s), wilson(k, len(s))
        rows.append(r)
    t = pd.DataFrame(rows)
    t.round(4).to_csv(RES / "table_condition_means.csv", index=False)
    return t


def substance_table(d):
    rows = []
    for c in fs.CONDITIONS:
        for s in SUBS:
            x = d[(d.condition == c) & (d.substance == s)]
            r = dict(condition=c, substance=s, n=len(x), any_stigma_rate=x.any_stigma.mean(),
                     overcaution_rate=x.overcaution.mean(), words=x.words.mean())
            for dim in DIMS:
                r[dim] = x[dim].mean()
                r[dim + "_lo"], r[dim + "_hi"] = boot_ci(x[dim])
            rows.append(r)
    t = pd.DataFrame(rows)
    t.round(4).to_csv(RES / "table_by_substance.csv", index=False)
    # Friedman: do substances differ, blocking on scenario? (within each condition)
    fr = []
    for c in fs.CONDITIONS:
        for dim in DIMS:
            w = d[d.condition == c].pivot_table(index="template_id", columns="substance", values=dim)[SUBS].dropna()
            if w.nunique().max() <= 1 and w.values.std() == 0:
                p = 1.0
                stat = 0.0
            else:
                try:
                    stat, p = stats.friedmanchisquare(*[w[s] for s in SUBS])
                except ValueError:
                    stat, p = np.nan, np.nan
            fr.append(dict(condition=c, dimension=dim, n_scenarios=len(w), friedman_chi2=stat, p=p,
                           lowest=w.mean().idxmin(), highest=w.mean().idxmax(),
                           range=w.mean().max() - w.mean().min()))
    f = pd.DataFrame(fr)
    f["p_holm"] = holm(f.p.fillna(1).values)
    f.round(4).to_csv(RES / "table_substance_friedman.csv", index=False)
    return t, f


def sender_table(d):
    rows = []
    for c in fs.CONDITIONS:
        for dim in DIMS + ["overcaution", "any_stigma"]:
            a = d[(d.condition == c) & (d.sender == "person")][dim]
            b = d[(d.condition == c) & (d.sender == "family")][dim]
            p = stats.mannwhitneyu(a, b).pvalue if a.nunique() + b.nunique() > 2 else 1.0
            rows.append(dict(condition=c, measure=dim, person=a.mean(), family=b.mean(),
                             diff=a.mean() - b.mean(), p_mannwhitney=p))
    t = pd.DataFrame(rows)
    t.round(4).to_csv(RES / "table_sender.csv", index=False)
    return t


def length_model(d):
    y = d.any_stigma.values
    x = d.words.values.reshape(-1, 1) / 100.0  # per 100 words
    out = dict(n=len(d), n_with_stigma=int(y.sum()))
    if 0 < y.sum() < len(y):
        out["point_biserial_r"], out["p"] = stats.pointbiserialr(y, d.words.values)
    # Rule of thumb: logistic regression needs >= 10 events per predictor; with fewer, the fit is noise.
    out["fit"] = "yes" if 10 <= y.sum() <= len(y) - 10 else "no (fewer than 10 responses with stigma)"
    if out["fit"] == "yes":
        m = LogisticRegression(C=1e6, max_iter=1000).fit(x, y)
        out["odds_ratio_per_100_words"] = float(np.exp(m.coef_[0][0]))
        bs = []
        for _ in range(1000):
            i = RNG.integers(0, len(y), len(y))
            if 0 < y[i].sum() < len(i):
                bs.append(np.exp(LogisticRegression(C=1e6, max_iter=1000).fit(x[i], y[i]).coef_[0][0]))
        out["or_lo"], out["or_hi"] = np.percentile(bs, [2.5, 97.5])
        out["model"] = m
    pd.DataFrame([{k: v for k, v in out.items() if k != "model"}]).round(4).to_csv(RES / "table_length_vs_stigma.csv", index=False)
    return out


def replication(cm):
    get = lambda c: cm.set_index("condition").loc[c]
    rows = [
        dict(measure="Any stigmatizing term, default", ours=get("default").any_stigma_rate,
             ours_ci=f"{get('default').any_stigma_lo:.1%} to {get('default').any_stigma_hi:.1%}",
             wang_2025=WANG_DEFAULT,
             note="Wang: 14 LLMs, 60 clinician-written questions. Ours: 1 model, first-person messages; unprompted terms only"),
        dict(measure="Any stigmatizing term, with anti-stigma prompt", ours=get("mi_prompt").any_stigma_rate,
             ours_ci=f"{get('mi_prompt').any_stigma_lo:.1%} to {get('mi_prompt').any_stigma_hi:.1%}",
             wang_2025=WANG_PROMPTED, note="Prompts differ: Wang's prompt engineering vs our MI/harm-reduction system prompt"),
        dict(measure="Any stigmatizing term, with guidance (RAG)", ours=get("rag").any_stigma_rate,
             ours_ci=f"{get('rag').any_stigma_lo:.1%} to {get('rag').any_stigma_hi:.1%}", wang_2025=np.nan,
             note="No equivalent condition in Wang et al."),
    ]
    t = pd.DataFrame(rows)
    t.to_csv(RES / "table_replication_wang2025.csv", index=False)
    return t


# ---------------- figures ----------------

def fig1(cm):
    fig, ax = fs.plt.subplots(figsize=(9, 4.6))
    xs = np.arange(len(DIMS))
    off = {"default": -0.22, "rag": 0, "mi_prompt": 0.22}
    for c in fs.CONDITIONS:
        r = cm.set_index("condition").loc[c]
        m = np.array([r[d] for d in DIMS])
        lo = m - np.array([r[d + "_lo"] for d in DIMS])
        hi = np.array([r[d + "_hi"] for d in DIMS]) - m
        ax.errorbar(xs + off[c], m, yerr=[lo, hi], fmt=fs.MARKER[c], color=fs.COLOR[c], ms=8,
                    elinewidth=2, capsize=0, label=fs.LABEL[c], mec=fs.SURFACE, mew=1.2)
    ax.set_xticks(xs, [fs.DIM_LABEL[d] for d in DIMS])
    lo_y = max(1, np.floor(min(cm[[d + "_lo" for d in DIMS]].min()) * 2) / 2 - 0.25)
    ax.set_ylim(lo_y, 5.15)
    ax.set_ylabel("Mean judge score (1-5), 95% CI")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="lower left", ncol=3, bbox_to_anchor=(0, 1.0), fontsize=9)
    ax.set_title("Rubric scores by condition", pad=28)
    fs.save(fig, "fig1_rubric_by_condition", CAVEAT + " Higher = better on every dimension. Note the axis does not start at 1.")


def fig2(cm):
    fig, ax = fs.plt.subplots(figsize=(7.5, 4.6))
    for i, c in enumerate(fs.CONDITIONS):
        r = cm.set_index("condition").loc[c]
        ax.bar(i, r.any_stigma_rate * 100, width=0.55, color=fs.COLOR[c], edgecolor=fs.SURFACE, linewidth=2)
        ax.errorbar(i, r.any_stigma_rate * 100, yerr=[[100 * (r.any_stigma_rate - r.any_stigma_lo)], [100 * (r.any_stigma_hi - r.any_stigma_rate)]],
                    color=fs.INK2, elinewidth=1.5, capsize=0)
        ax.text(i, r.any_stigma_hi * 100 + 1.2, f"{r.any_stigma_rate:.0%}", ha="center", color=fs.INK, fontsize=10)
    for y, txt in [(WANG_DEFAULT * 100, "Wang et al. 2025, default: 35.4%"), (WANG_PROMPTED * 100, "Wang et al. 2025, prompt-engineered: 6.3%")]:
        ax.axhline(y, color=fs.MUTED, ls="--", lw=1.2)
        ax.text(2.42, y + 0.6, txt.replace(": ", ":\n"), ha="left", va="bottom", fontsize=8.5, color=fs.INK2)
    ax.set_xticks(range(3), [fs.LABEL[c] for c in fs.CONDITIONS])
    ax.set_ylim(0, 42)
    ax.set_xlim(-0.5, 3.35)
    ax.set_ylabel("% of responses with any stigmatizing term")
    ax.grid(axis="x", visible=False)
    ax.set_title("Stigmatizing language by condition")
    fs.save(fig, "fig2_stigma_rate_by_condition",
            "Counts only terms the sender did not use first (mirroring rule). Wilson 95% CIs. Wang et al. used clinician-written questions "
            "across 14 LLMs, so the reference lines are context, not a like-for-like comparison.")


def fig3(d, st):
    dflt = st[st.condition == "default"].set_index("substance")
    order = sorted(SUBS, key=lambda s: dflt.loc[s, DIMS].mean())
    fig, axes = fs.plt.subplots(1, 3, figsize=(13, 4.4), sharey=True)
    vmin = max(1, np.floor(st[DIMS].min().min() * 2) / 2)
    for ax, c in zip(axes, fs.CONDITIONS):
        m = st[st.condition == c].set_index("substance").loc[order, DIMS].values
        im = ax.imshow(m, cmap=fs.SEQ, vmin=vmin, vmax=5, aspect="auto")
        ax.grid(False)
        ax.set_xticks(range(len(DIMS)), [fs.DIM_LABEL[x] for x in DIMS], rotation=35, ha="right")
        ax.set_yticks(range(len(order)), [fs.SUB_LABEL[s] for s in order])
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                ax.text(j, i, f"{m[i, j]:.1f}", ha="center", va="center", fontsize=8.5,
                        color="white" if (m[i, j] - vmin) / (5 - vmin) > 0.6 else fs.INK)
        ax.set_title(fs.LABEL[c], fontsize=11)
        for s in ax.spines.values():
            s.set_visible(False)
    fig.subplots_adjust(bottom=0.3, top=0.85)
    cb = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.015)
    cb.set_label("Mean score (n = 10 per cell)")
    fig.suptitle("Scores by substance and condition", x=0.01, ha="left", fontweight="bold", fontsize=12)
    fs.save(fig, "fig3_substance_heatmap",
            "Substances ordered by mean default-condition score (lowest first). Each cell = 10 messages; "
            "differences of ~0.3 are within noise (see results/table_by_substance.csv for CIs).")


def fig4(d):
    fig, axes = fs.plt.subplots(2, 2, figsize=(10, 6), sharex=True, sharey=True)
    for row, comp in enumerate(["rag", "mi_prompt"]):
        for col, dim in enumerate(["empathy", "nonjudgment"]):
            ax = axes[row, col]
            w = d.pivot_table(index="message_id", columns="condition", values=dim)
            diff = (w[comp] - w["default"]).dropna().astype(int)
            vals = np.arange(-4, 5)
            counts = [int((diff == v).sum()) for v in vals]
            colors = [fs.COLOR[comp] if v > 0 else (fs.COLOR["default"] if v < 0 else fs.MUTED) for v in vals]
            ax.bar(vals, counts, color=colors, width=0.7, edgecolor=fs.SURFACE, linewidth=2)
            for v, n in zip(vals, counts):
                if n:
                    ax.text(v, n + 0.8, str(n), ha="center", fontsize=8.5, color=fs.INK2)
            ax.set_title(f"{fs.DIM_LABEL[dim]}: {fs.LABEL[comp]} minus default", fontsize=10)
            ax.grid(axis="x", visible=False)
            ax.set_xticks(vals)
    for ax in axes[1]:
        ax.set_xlabel("Change in score for the same message")
    for ax in axes[:, 0]:
        ax.set_ylabel("Number of messages")
    fig.suptitle("Per-message change vs the default assistant", x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fs.save(fig, "fig4_paired_change", "Each bar counts messages (of 60) by how much the score changed. Right of 0 = better than default; grey = no change.")


def fig5(d, lm):
    fig, ax = fs.plt.subplots(figsize=(8, 4.6))
    jit = RNG.uniform(-0.04, 0.04, len(d))
    for c in fs.CONDITIONS:
        s = d.condition == c
        ax.scatter(d.words[s], d.any_stigma[s] + jit[s.values], s=22, marker=fs.MARKER[c], color=fs.COLOR[c],
                   alpha=0.75, label=fs.LABEL[c], edgecolor=fs.SURFACE, linewidth=0.6)
    if "model" in lm:
        g = np.linspace(d.words.min(), d.words.max(), 200)
        ax.plot(g, lm["model"].predict_proba((g / 100).reshape(-1, 1))[:, 1], color=fs.INK, lw=2,
                label=f"Logistic fit (OR per 100 words {lm['odds_ratio_per_100_words']:.2f}, 95% CI {lm['or_lo']:.2f}-{lm['or_hi']:.2f})")
        title = "Response length vs probability of stigmatizing language"
    else:
        title = f"Response length vs stigma: too few events to fit ({lm['n_with_stigma']} of {lm['n']} responses)"
    ax.set_yticks([0, 0.5, 1], ["0 (none)", "0.5", "1 (any)"])
    ax.set_xlabel("Response length (words)")
    ax.set_ylabel("Any stigmatizing term")
    ax.legend(fontsize=8.5, loc="center right")
    ax.set_title(title)
    fs.save(fig, "fig5_length_vs_stigma", "Points jittered vertically. Pooled across conditions; replicates the length analysis of Wang et al. 2025.")


def fig6(d):
    fig, ax = fs.plt.subplots(figsize=(8, 4.4))
    senders = [("person", "From a person who uses"), ("family", "From family / friends")]
    w = 0.26
    top = 0
    for i, c in enumerate(fs.CONDITIONS):
        for j, (s, _) in enumerate(senders):
            x = d[(d.condition == c) & (d.sender == s)]
            k, n = int(x.overcaution.sum()), len(x)
            lo, hi = wilson(k, n)
            ax.bar(j + (i - 1) * w, 100 * k / n, width=w, color=fs.COLOR[c], edgecolor=fs.SURFACE, linewidth=2,
                   label=fs.LABEL[c] if j == 0 else None)
            ax.errorbar(j + (i - 1) * w, 100 * k / n, yerr=[[100 * (k / n - lo)], [100 * (hi - k / n)]], color=fs.INK2, elinewidth=1.3)
            ax.text(j + (i - 1) * w, 100 * hi + 1.5, f"{k}/{n}", ha="center", fontsize=8.5, color=fs.INK2)
            top = max(top, 100 * hi)
    ax.set_xticks(range(2), [l for _, l in senders])
    ax.set_ylim(0, max(25, top + 10))
    ax.set_ylabel("% judged over-cautious")
    ax.grid(axis="x", visible=False)
    ax.legend(fontsize=9, loc="upper right")
    ax.set_title("Over-caution (refusing, hedging, hotline-dumping)")
    fs.save(fig, "fig6_overcaution", "Wilson 95% CIs. Labels show count / number of responses.")


def fig7():
    f = RES / "judge_validation.csv"
    if not f.exists():
        print("  (no judge_validation.csv yet; skipping fig7)")
        return None
    v = pd.read_csv(f)
    y = (v.mi_quality == "high").astype(int)
    auc = roc_auc_score(y, v.relational_mean)
    fig, (a1, a2) = fs.plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.4, 1]})
    dims = ["empathy", "autonomy", "nonjudgment", "relational_mean"]
    names = ["Empathy", "Autonomy", "Non-judgment", "Mean of 3"]
    qc = {"high": fs.COLOR["mi_prompt"], "low": fs.COLOR["rag"]}
    for k, dim in enumerate(dims):
        for q, dx in [("low", -0.17), ("high", 0.17)]:
            vals = v[v.mi_quality == q][dim]
            a1.boxplot(vals, positions=[k + dx], widths=0.26, showfliers=False, patch_artist=True,
                       boxprops=dict(facecolor="none", edgecolor=fs.MUTED), medianprops=dict(color=fs.INK, lw=2),
                       whiskerprops=dict(color=fs.MUTED), capprops=dict(color=fs.MUTED))
            a1.scatter(k + dx + RNG.uniform(-0.08, 0.08, len(vals)), vals + RNG.uniform(-0.08, 0.08, len(vals)), s=16,
                       color=qc[q], marker="s" if q == "low" else "D", alpha=0.8, edgecolor=fs.SURFACE, linewidth=0.5,
                       label=(f"{q.capitalize()}-quality MI (n={len(vals)})" if k == 0 else None))
    a1.set_xticks(range(len(dims)), names)
    a1.set_ylabel("Judge score (1-5)")
    a1.grid(axis="x", visible=False)
    a1.legend(fontsize=8.5, loc="upper left", ncol=2, bbox_to_anchor=(0, -0.08), frameon=False)
    a1.set_title("Judge scores on expert-labelled MI transcripts", fontsize=11)
    for dim, name, ls in [("relational_mean", "Mean of 3", "-"), ("empathy", "Empathy", "--"), ("autonomy", "Autonomy", ":")]:
        fpr, tpr, _ = roc_curve(y, v[dim])
        a2.plot(fpr, tpr, ls=ls, color=fs.INK if dim == "relational_mean" else fs.INK2, lw=2 if dim == "relational_mean" else 1.4,
                label=f"{name} (AUC {roc_auc_score(y, v[dim]):.2f})")
    a2.plot([0, 1], [0, 1], color=fs.GRID, lw=1)
    a2.set_xlabel("False positive rate")
    a2.set_ylabel("True positive rate")
    a2.legend(fontsize=8.5, loc="lower right")
    a2.set_title("ROC: high vs low quality", fontsize=11)
    flag = "" if auc >= 0.75 else "  BELOW 0.75 THRESHOLD: judge not validated"
    fig.suptitle(f"Judge validation on AnnoMI: AUC {auc:.2f}{flag}", x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fs.save(fig, "fig7_judge_validation", "AnnoMI: real counselling transcripts labelled high/low MI quality by experts. "
            "Judge rated the therapist on the first ~1,500 words. Ties are common because scores are integers.")
    return auc


def main():
    d = load()
    print(f"{len(d)} judged responses; conditions: {d.condition.value_counts().to_dict()}")
    cm = condition_means(d)
    pt = paired_tests(d)
    st, fr = substance_table(d)
    sd = sender_table(d)
    lm = length_model(d)
    rep = replication(cm)
    fig1(cm); fig2(cm); fig3(d, st); fig4(d); fig5(d, lm); fig6(d)
    auc = fig7()
    summary = dict(n=len(d), condition_means=cm.round(3).to_dict("records"),
                   paired=pt.round(4).to_dict("records"), friedman=fr.round(4).to_dict("records"),
                   sender=sd.round(4).to_dict("records"),
                   length={k: (float(v) if isinstance(v, (int, float, np.floating, np.integer)) else None) for k, v in lm.items() if k != "model"},
                   replication=rep.to_dict("records"), judge_auc=auc)
    (RES / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    pd.set_option("display.width", 200)
    print(cm[["condition", "n", "words_mean"] + DIMS + ["any_stigma_rate", "any_stigma_incl_mirrored", "overcaution_rate"]].round(2).to_string(index=False))
    print(pt[["comparison", "measure", "mean_diff", "mean_diff_lo", "mean_diff_hi", "n_better", "n_worse", "p", "p_holm"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
