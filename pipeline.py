"""End-to-end Knowledge Decay pipeline for a single URL or raw article text."""
import sys
from urllib.parse import urlparse

from broken_links import check_broken_links
from combine_signals import combine_signals, generate_explanation
from deprecated_tech import check_deprecated_tech
from extract_article_text import (
    extract_article_links,
    extract_article_text,
    is_valid_article_text,
)
from extract_date import UNKNOWN, extract_date
from semantic_similarity import compute_semantic_similarity
from temporal_metadata import check_temporal_metadata
from terminology_drift import check_terminology_drift

# A date_info shaped like extract_date's output, for input with no page to pull
# a date from: temporal_metadata treats this exactly like a page with no date.
_NO_DATE_INFO = {"date": UNKNOWN, "method": "none", "kind": None, "raw": None,
                  "source": None, "ambiguous_date_format": False}


def looks_like_url(s):
    """True if `s` (stripped) parses as a single http(s) URL rather than prose."""
    s = s.strip()
    if not s or "\n" in s or " " in s:
        return False
    parsed = urlparse(s)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _run_signals(text, date_info, broken_links_result):
    results = {
        "semantic_similarity": compute_semantic_similarity(text),
        "terminology_drift": check_terminology_drift(text),
        "broken_links": broken_links_result,
        "deprecated_tech": check_deprecated_tech(text),
        "temporal_metadata": check_temporal_metadata(
            date_info["date"],
            ambiguous_date_format=date_info["ambiguous_date_format"],
        ),
    }
    combined = combine_signals(results)
    return {"text": text, "date_info": date_info, "results": results,
            "combined": combined, "explanation": generate_explanation(results)}


def run_pipeline(url):
    text = extract_article_text(url)
    if not is_valid_article_text(text):
        return {"error": text}  # "fetch_failed" or "extraction_failed"

    date_info = extract_date(url)
    # Real link targets come from the HTML hrefs; the visible text has no URLs.
    links = extract_article_links(url) or []
    return _run_signals(text, date_info, check_broken_links(urls=links))


def run_pipeline_for_text(text):
    """Run the pipeline on raw pasted article text (no page to fetch).

    There is no HTML to pull a date from, so temporal_metadata is excluded, same
    as a page with no date; links are whichever bare URLs appear in the pasted
    text itself.
    """
    if not text or not text.strip():
        return {"error": "empty_text"}
    return _run_signals(text, _NO_DATE_INFO, check_broken_links(text=text))


def run_pipeline_from_input(user_input):
    """Run the URL pipeline if `user_input` is a bare URL, else the text pipeline."""
    if looks_like_url(user_input):
        return run_pipeline(user_input)
    return run_pipeline_for_text(user_input)


if __name__ == "__main__":
    url = (sys.argv[1] if len(sys.argv) > 1 else
           "https://inventivehq.com/blog/azure-active-directory-microsoft-entra-id-guide")
    out = run_pipeline(url)
    print(f"URL: {url}")
    if "error" in out:
        print(f"Pipeline stopped: {out['error']}")
        sys.exit(1)

    r, c = out["results"], out["combined"]
    print(f"Article text: {len(out['text'])} chars\n")
    print("--- Raw signal results ---")
    print(f"date: {out['date_info']['date']} ({out['date_info']['method']})")
    print(f"semantic_similarity: {r['semantic_similarity']['similarity']:.3f} "
          f"over {r['semantic_similarity']['paragraphs']} paragraphs")
    td = r["terminology_drift"]
    print(f"terminology_drift: score {td['score']} "
          f"(counted {[(f['term'], f['count']) for f in td['found']]}, "
          f"exempted {td['exempted']} explanatory mentions)")
    print(f"broken_links: score {r['broken_links']['score']} "
          f"(checked {r['broken_links']['total']}, "
          f"inconclusive {len(r['broken_links']['inconclusive'])})")
    for b in r["broken_links"]["broken"]:
        print(f"    BROKEN ({b['reason']}): {b['url']}")
    for i in r["broken_links"]["inconclusive"]:
        print(f"    INCONCLUSIVE ({i['reason']}): {i['url']}")
    print(f"deprecated_tech: score {r['deprecated_tech']['score']}")
    print(f"temporal_metadata: months_old {r['temporal_metadata']['months_old']}, "
          f"score {r['temporal_metadata']['score']}")
    print(f"\nExcluded (not applicable): {c['excluded']}")
    print("Effective weights: " + ", ".join(
        f"{n}={w:.1%}" for n, w in c["effective_weights"].items()))
    print("Signal decay (0-1): " + ", ".join(
        f"{n}={d:.2f}" for n, d in c["signal_decay"].items()))
    print(f"\n=== Knowledge Decay Score: {c['score']} / 100 ===\n")
    print("Explanation:")
    for line in out["explanation"] or ["(no signal contributed meaningfully)"]:
        print(f"- {line}")
