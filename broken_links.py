"""Broken links signal: finds URLs in text and checks whether each one resolves."""
import re
import urllib.error
import urllib.request

import truststore
truststore.inject_into_ssl()  # trust the OS certificate store, same as Windows/curl

NOT_APPLICABLE = "not_applicable"
_URL_RE =re.compile(r"https?://[^\s<>\"'\)\]]+", re.IGNORECASE)
_TRAILING_PUNCT = ".,;:!?"
_INCONCLUSIVE_STATUSES = {"403", "429"}  # likely bot-blocking, not a dead page
_HEADERS = {"User-Agent": "Mozilla/5.0 (link-checker)"}


def extract_urls(text):
    """Return unique URLs in order of first appearance."""
    urls = []
    for m in _URL_RE.finditer(text):
        url = m.group(0).rstrip(_TRAILING_PUNCT)
        if url not in urls:
            urls.append(url)
    return urls


def check_url(url, timeout=10):
    """Return (status, detail).

    status is "ok" (final 2xx), "inconclusive" (403/429) or "broken" (anything else).
    """
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        # urllib follows redirects, so the status is that of the final page.
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                return "ok", str(resp.status)
            return "broken", str(resp.status)
    except urllib.error.HTTPError as e:
        code = str(e.code)
        return ("inconclusive" if code in _INCONCLUSIVE_STATUSES else "broken"), code
    except Exception as e:  # DNS failure, timeout, SSL error, etc.
        return "broken", f"{type(e).__name__}: {e}"


def check_broken_links(text=None, timeout=10, urls=None):
    """Return {'total', 'broken': [{url, reason}], 'inconclusive': [{url, reason}], 'score'}.

    Inconclusive links (403/429) are excluded from both the broken count and total.
    total = links checked conclusively; score = broken / total
    (0.0 = all good, 1.0 = all broken). If there are no URLs at all, or every URL
    was inconclusive (so nothing was determined), score is "not_applicable".
    URLs are found in `text`, unless an explicit `urls` list is given (e.g. hrefs
    extracted from a page's HTML), in which case `text` is not searched.
    """
    if urls is None:
        urls = extract_urls(text)
    else:  # explicit links (e.g. hrefs from the page HTML); dedupe, keep order
        urls = list(dict.fromkeys(urls))
    if not urls:
        # No links at all is different from "links were checked and all worked".
        return {"total": 0, "broken": [], "inconclusive": [], "score": NOT_APPLICABLE}
    broken, inconclusive, total = [], [], 0
    for url in urls:
        status, detail = check_url(url, timeout)
        if status == "inconclusive":
            inconclusive.append({"url": url, "reason": detail})
            continue
        total += 1
        if status == "broken":
            broken.append({"url": url, "reason": detail})
    # Links existed but none could be checked conclusively: nothing was determined.
    score = len(broken) / total if total else NOT_APPLICABLE
    return {"total": total, "broken": broken, "inconclusive": inconclusive, "score": score}


if __name__ == "__main__":
    sample = (
        "For more information, see "
        "https://learn.microsoft.com/en-us/entra/fundamentals/new-name and also "
        "https://docs.microsoft.com/en-us/azure/active-directory/this-page-does-not-exist-12345"
    )
    result = check_broken_links(sample)
    print(f"URLs checked conclusively: {result['total']}")
    if not result["broken"]:
        print("No broken links.")
    for b in result["broken"]:
        print(f"- BROKEN ({b['reason']}): {b['url']}")
    for i in result["inconclusive"]:
        print(f"- INCONCLUSIVE ({i['reason']}, excluded from score): {i['url']}")
    print(f"\nBroken link score: {result['score']:.2f} "
          f"({len(result['broken'])}/{result['total']})")
