"""Batch evaluation of the Knowledge Decay prototype against a labelled dataset.

Usage (run from the Research folder, with the virtual environment active):

    python batch_eval.py run      # score every labelled article, save results.csv
    python batch_eval.py analyse  # metrics, threshold sweep, ROC, ablation, timing

dataset.csv columns used:
    id, url, label (Outdated / Current), text_file (optional), rater2_label (optional)

Positive class = "Outdated". An article is predicted Outdated when its
Knowledge Decay Score is >= the threshold (default 30, the green/amber border).
Uses only the Python standard library for the analysis step.
"""
import argparse
import csv
import json
import math
import os
import statistics
import sys
import time

SIGNALS = ("semantic_similarity", "terminology_drift", "broken_links",
           "deprecated_tech", "temporal_metadata")
SHORT = {"semantic_similarity": "semantic", "terminology_drift": "terminology",
         "broken_links": "links", "deprecated_tech": "deprecated",
         "temporal_metadata": "temporal"}
VALID_LABELS = ("Outdated", "Current")


# ----------------------------------------------------------------------------
# Step 1: run the pipeline over the dataset
# ----------------------------------------------------------------------------
def _raw_fields(out):
    """Pull a few readable raw values out of a pipeline result."""
    r = out["results"]
    sem = r["semantic_similarity"]
    sim = sem["similarity"] if isinstance(sem, dict) else sem
    td, bl = r["terminology_drift"], r["broken_links"]
    dt, tm = r["deprecated_tech"], r["temporal_metadata"]
    return {
        "raw_similarity": sim if not isinstance(sim, str) else "",
        "paragraphs": sem.get("paragraphs", "") if isinstance(sem, dict) else "",
        "term_count": td.get("score", ""),
        "term_exempted": td.get("exempted", ""),
        "links_total": bl.get("total", ""),
        "links_broken": len(bl.get("broken", [])),
        "links_inconclusive": len(bl.get("inconclusive", [])),
        "deprecated_count": dt.get("score", ""),
        "months_old": tm.get("months_old", "") if tm.get("months_old") is not None else "",
        "date_method": out["date_info"].get("method", ""),
    }


def run_batch(dataset_path, results_path, snapshot_dir, force):
    from pipeline import run_pipeline, run_pipeline_for_text  # needs the prototype

    with open(dataset_path, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("label", "").strip() in VALID_LABELS]
    if not rows:
        sys.exit("No rows with label Outdated/Current found in " + dataset_path)

    done = {}
    if os.path.exists(results_path) and not force:
        with open(results_path, newline="", encoding="utf-8") as f:
            done = {r["id"]: r for r in csv.DictReader(f)}
    os.makedirs(snapshot_dir, exist_ok=True)

    fields = ["id", "url", "label", "rater2_label", "mode", "status", "score",
              *[f"decay_{SHORT[s]}" for s in SIGNALS], "excluded", "low_confidence",
              "raw_similarity", "paragraphs", "term_count", "term_exempted",
              "links_total", "links_broken", "links_inconclusive",
              "deprecated_count", "months_old", "date_method", "seconds", "text_chars"]
    out_rows = list(done.values())
    for i, row in enumerate(rows, 1):
        rid = row["id"].strip()
        if rid in done:
            continue
        text_file = (row.get("text_file") or "").strip()
        rec = {k: "" for k in fields}
        rec.update(id=rid, url=row.get("url", "").strip(), label=row["label"].strip(),
                   rater2_label=(row.get("rater2_label") or "").strip())
        start = time.perf_counter()
        try:
            if text_file:
                with open(text_file, encoding="utf-8") as tf:
                    out = run_pipeline_for_text(tf.read())
                rec["mode"] = "text"
            else:
                out = run_pipeline(rec["url"])
                rec["mode"] = "url"
        except Exception as e:  # never let one article stop the batch
            out = {"error": f"exception: {type(e).__name__}: {e}"}
        rec["seconds"] = round(time.perf_counter() - start, 2)

        if "error" in out:
            rec["status"] = str(out["error"])[:120]
        else:
            c = out["combined"]
            rec["status"] = "ok"
            rec["score"] = "" if c["score"] is None else c["score"]
            for s in SIGNALS:
                d = c["signal_decay"].get(s)
                rec[f"decay_{SHORT[s]}"] = "" if d is None else round(d, 4)
            rec["excluded"] = ";".join(c["excluded"])
            rec["low_confidence"] = ";".join(c["low_confidence"])
            rec["text_chars"] = len(out["text"])
            rec.update(_raw_fields(out))
            with open(os.path.join(snapshot_dir, f"{rid}.txt"), "w", encoding="utf-8") as sf:
                sf.write(out["text"])
        out_rows.append(rec)
        print(f"[{i}/{len(rows)}] {rid}: {rec['status']} score={rec['score']} "
              f"({rec['seconds']}s)", flush=True)
        # save after every article so a crash loses nothing
        with open(results_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(out_rows)
    print(f"\nSaved {results_path} ({len(out_rows)} rows). Next: python batch_eval.py analyse")


# ----------------------------------------------------------------------------
# Step 2: analysis (pure Python, no extra libraries)
# ----------------------------------------------------------------------------
def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def confusion(pairs, thr):
    """pairs = [(is_outdated, score)]; predicted Outdated if score >= thr."""
    tp = sum(1 for y, s in pairs if y and s >= thr)
    fp = sum(1 for y, s in pairs if not y and s >= thr)
    fn = sum(1 for y, s in pairs if y and s < thr)
    tn = sum(1 for y, s in pairs if not y and s < thr)
    return tp, fp, fn, tn


def metrics(tp, fp, fn, tn):
    n = tp + fp + fn + tn
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    spec = tn / (tn + fp) if tn + fp else 0.0
    acc = (tp + tn) / n if n else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "specificity": spec, "accuracy": acc}


def auc_and_roc(pairs):
    """ROC points and AUC (probability an Outdated article scores above a Current one)."""
    pos = [s for y, s in pairs if y]
    neg = [s for y, s in pairs if not y]
    if not pos or not neg:
        return None, []
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    auc = wins / (len(pos) * len(neg))
    pts = []
    for thr in sorted({s for _, s in pairs} | {0, 101}, reverse=True):
        tp, fp, fn, tn = confusion(pairs, thr)
        pts.append((thr, fp / (fp + tn) if fp + tn else 0, tp / (tp + fn) if tp + fn else 0))
    return auc, pts


def kappa(a, b):
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in set(a) | set(b))
    return (po - pe) / (1 - pe) if pe != 1 else 1.0


def rescore(row, drop=None, only=None):
    """Recompute the score from stored decays, mirroring combine_signals (equal weights)."""
    active = []
    for s in SIGNALS:
        d = _f(row.get(f"decay_{SHORT[s]}"))
        if d is None:
            continue
        if drop and s == drop:
            continue
        if only and s != only:
            continue
        active.append(d)
    return 100 * sum(active) / len(active) if active else None


def analyse(results_path, thr, outdir):
    with open(results_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    os.makedirs(outdir, exist_ok=True)
    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    total = len(rows)
    scored = [r for r in rows if r["status"] == "ok" and _f(r["score"]) is not None]
    failed = [r for r in rows if r not in scored]
    say(f"# Evaluation summary\n")
    say(f"Articles in dataset run: {total}; scored: {len(scored)}; not scored: {len(failed)}")
    for r in failed:
        say(f"  - not scored: {r['id']} ({r['status']})")
    n_out = sum(r["label"] == "Outdated" for r in scored)
    say(f"Labels among scored articles: Outdated = {n_out}, Current = {len(scored) - n_out}\n")

    pairs = [(r["label"] == "Outdated", _f(r["score"])) for r in scored]

    # consistency check of the re-scoring used for the ablation
    bad = [r["id"] for r in scored if rescore(r) is None
           or abs(rescore(r) - _f(r["score"])) > 0.15]
    say(f"Re-scoring check (stored score vs recomputed from signal decays): "
        f"{'OK' if not bad else 'MISMATCH for ' + ', '.join(bad)}\n")

    # ---- main result at the chosen threshold
    tp, fp, fn, tn = confusion(pairs, thr)
    m = metrics(tp, fp, fn, tn)
    say(f"## Confusion matrix (predict Outdated if score >= {thr})\n")
    say("| | Predicted Outdated | Predicted Current |")
    say("|---|---|---|")
    say(f"| Actually Outdated | TP = {tp} | FN = {fn} |")
    say(f"| Actually Current | FP = {fp} | TN = {tn} |\n")
    say(f"Precision {m['precision']:.3f} | Recall {m['recall']:.3f} | F1 {m['f1']:.3f} | "
        f"Specificity {m['specificity']:.3f} | Accuracy {m['accuracy']:.3f}\n")
    with open(os.path.join(outdir, "confusion.json"), "w") as f:
        json.dump({"threshold": thr, "tp": tp, "fp": fp, "fn": fn, "tn": tn, **m}, f, indent=2)

    # ---- threshold sweep
    say("## Threshold sweep\n")
    say("| Threshold | TP | FP | FN | TN | Precision | Recall | F1 |")
    say("|---|---|---|---|---|---|---|---|")
    sweep, best = [], None
    for t in range(0, 101, 5):
        a, b, c, d = confusion(pairs, t)
        mm = metrics(a, b, c, d)
        sweep.append([t, a, b, c, d, round(mm["precision"], 3), round(mm["recall"], 3), round(mm["f1"], 3)])
        say(f"| {t} | {a} | {b} | {c} | {d} | {mm['precision']:.3f} | {mm['recall']:.3f} | {mm['f1']:.3f} |")
        if best is None or mm["f1"] > best[1] + 1e-9:
            best = (t, mm["f1"])
    say(f"\nBest F1 on this dataset: {best[1]:.3f} at threshold {best[0]} "
        f"(tuned on the same data it is measured on, so this is optimistic).\n")
    with open(os.path.join(outdir, "threshold_sweep.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["threshold", "tp", "fp", "fn", "tn", "precision", "recall", "f1"])
        w.writerows(sweep)

    # ---- ROC
    auc, pts = auc_and_roc(pairs)
    if auc is not None:
        say(f"## ROC\n\nAUC = {auc:.3f}\n")
        with open(os.path.join(outdir, "roc_points.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["threshold", "false_positive_rate", "true_positive_rate"])
            w.writerows(pts)

    # ---- ablation
    say("## Ablation (equal weights, signal removed or used alone)\n")
    say("| Variant | Articles | F1 @ threshold | Precision | Recall | AUC |")
    say("|---|---|---|---|---|---|")
    abl = []

    def variant(name, **kw):
        pr = [(r["label"] == "Outdated", rescore(r, **kw)) for r in scored]
        pr = [(y, s) for y, s in pr if s is not None]
        if not pr:
            return
        a, b, c, d = confusion(pr, thr)
        mm = metrics(a, b, c, d)
        au, _ = auc_and_roc(pr)
        abl.append([name, len(pr), round(mm["f1"], 3), round(mm["precision"], 3),
                    round(mm["recall"], 3), "" if au is None else round(au, 3)])
        say(f"| {name} | {len(pr)} | {mm['f1']:.3f} | {mm['precision']:.3f} | "
            f"{mm['recall']:.3f} | {'' if au is None else f'{au:.3f}'} |")

    variant("All five signals")
    for s in SIGNALS:
        variant(f"Without {SHORT[s]}", drop=s)
    for s in SIGNALS:
        variant(f"{SHORT[s]} only", only=s)
    say()
    with open(os.path.join(outdir, "ablation.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variant", "articles", "f1", "precision", "recall", "auc"])
        w.writerows(abl)

    # ---- signal coverage
    say("## Signal coverage (how often each signal was applicable)\n")
    for s in SIGNALS:
        k = sum(_f(r.get(f"decay_{SHORT[s]}")) is not None for r in scored)
        say(f"- {SHORT[s]}: applicable for {k} of {len(scored)} articles")
    say()

    # ---- timing
    secs = [_f(r["seconds"]) for r in rows if _f(r["seconds"]) is not None]
    ok_secs = [_f(r["seconds"]) for r in scored]
    if ok_secs:
        say("## Performance\n")
        say(f"Seconds per scored article: mean {statistics.mean(ok_secs):.1f}, "
            f"median {statistics.median(ok_secs):.1f}, max {max(ok_secs):.1f}, "
            f"total {sum(ok_secs):.0f} s for {len(ok_secs)} articles\n")

    # ---- inter-rater agreement
    both = [(r["label"], r["rater2_label"]) for r in rows
            if r.get("rater2_label") in VALID_LABELS]
    if len(both) >= 5:
        k = kappa([a for a, _ in both], [b for _, b in both])
        agree = sum(a == b for a, b in both) / len(both)
        say("## Labelling agreement\n")
        say(f"Second rater labelled {len(both)} articles: raw agreement {agree:.2f}, "
            f"Cohen's kappa {k:.2f}\n")

    # ---- errors to look at
    say("## Misclassified articles (at the chosen threshold)\n")
    for r in scored:
        y, s = r["label"] == "Outdated", _f(r["score"])
        if y != (s >= thr):
            kind = "FALSE NEGATIVE (missed outdated)" if y else "FALSE POSITIVE (flagged current)"
            say(f"- {r['id']} score {s}: {kind} | {r['url']}")
    with open(os.path.join(outdir, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nFiles written to {outdir}/ (report.md, threshold_sweep.csv, roc_points.csv, "
          f"ablation.csv, confusion.json)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=["run", "analyse"])
    ap.add_argument("--dataset", default="dataset.csv")
    ap.add_argument("--results", default="results.csv")
    ap.add_argument("--snapshots", default="snapshots")
    ap.add_argument("--threshold", type=float, default=30.0)
    ap.add_argument("--outdir", default="eval_output")
    ap.add_argument("--force", action="store_true", help="re-run articles already in results.csv")
    a = ap.parse_args()
    if a.command == "run":
        run_batch(a.dataset, a.results, a.snapshots, a.force)
    else:
        analyse(a.results, a.threshold, a.outdir)
