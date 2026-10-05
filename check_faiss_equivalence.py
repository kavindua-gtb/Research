"""Check that the FAISS semantic-similarity search matches the NumPy version.

Usage:
    python check_faiss_equivalence.py before   # record results with current code
    python check_faiss_equivalence.py after    # record again, then compare to before

Each run saves compute_semantic_similarity's output for the same 3 inputs to
faiss_check_<label>.json. The "after" run also prints the largest similarity
difference and whether every paragraph's best-matching source file is unchanged.
"""
import json
import os
import sys

from semantic_similarity import compute_semantic_similarity

TEST_SENTENCE = ("Azure AD Conditional Access policies require users to complete "
                 "multi-factor authentication before they can access cloud apps.")


def _inputs():
    texts = {}
    for path in ("lepide_article.txt", "scratch_article.txt"):
        with open(path, "r", encoding="utf-8") as f:
            texts[path] = f.read()
    texts["test_sentence"] = TEST_SENTENCE
    return texts


def record(label):
    out_path = f"faiss_check_{label}.json"
    if label == "before" and os.path.exists(out_path):
        sys.exit(f"{out_path} already exists; delete it first to re-record.")
    results = {name: compute_semantic_similarity(text) for name, text in _inputs().items()}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved {out_path}")
    for name, r in results.items():
        print(f"  {name}: similarity {r['similarity']:.6f} over {r['paragraphs']} paragraphs")
    return results


def compare(before, after):
    max_diff = 0.0
    all_same_source = True
    for name in before:
        b, a = before[name], after[name]
        if b["paragraphs"] != a["paragraphs"]:
            print(f"  {name}: paragraph count changed {b['paragraphs']} -> {a['paragraphs']}")
            all_same_source = False
            continue
        diffs = [abs(b["similarity"] - a["similarity"])]
        for i, (bm, am) in enumerate(zip(b["best_matches"], a["best_matches"])):
            diffs.append(abs(bm["similarity"] - am["similarity"]))
            if bm["source"] != am["source"]:
                all_same_source = False
                print(f"  {name} paragraph {i}: source {bm['source']} -> {am['source']}")
        print(f"  {name}: mean {b['similarity']:.6f} -> {a['similarity']:.6f}, "
              f"largest diff {max(diffs):.2e}")
        max_diff = max(max_diff, *diffs)
    print(f"\nLargest similarity difference overall: {max_diff:.2e}")
    print(f"Best-matching source identical for every paragraph: {all_same_source}")


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "before"
    results = record(label)
    if label == "after":
        with open("faiss_check_before.json", "r", encoding="utf-8") as f:
            print("\nComparison with before:")
            compare(json.load(f), results)
