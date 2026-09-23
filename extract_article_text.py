"""Fetch a webpage and extract just the main article prose (no nav, ads, chrome)."""
import re
import urllib.error
import urllib.request
from urllib.parse import urldefrag, urljoin, urlparse

import truststore
truststore.inject_into_ssl()  # trust the OS certificate store, same as Windows/curl

from bs4 import BeautifulSoup

_HEADERS = {"User-Agent": "Mozilla/5.0 (article-extractor)"}
_BLOCKED_STATUSES = {403, 429}  # likely bot-blocking, not a dead page

# Tags that are never article prose.
_NOISE_TAGS = ["script", "style", "noscript", "template", "svg", "iframe", "form",
               "nav", "header", "footer", "aside", "button", "select", "dialog"]

# class/id tokens that mark page clutter (matched as whole tokens, e.g. "cookie-banner").
_NOISE_TOKENS = re.compile(
    r"(?:^|[-_ ])(?:nav|navbar|navigation|menu|sidebar|footer|header|banner|cookie|"
    r"consent|popup|modal|advert|advertisement|ads?|sponsor|promo|share|sharing|"
    r"social|related|recommended|newsletter|subscribe|breadcrumbs?|comments?|"
    r"toc|skip)(?:$|[-_ ])",
    re.IGNORECASE,
)

_TEXT_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre"]
_MIN_ARTICLE_CHARS = 300
MIN_EXTRACTED_CHARS = 500  # shorter than this likely means the wrong block was grabbed
FETCH_FAILED = "fetch_failed"  # could not fetch the page
EXTRACTION_FAILED = "extraction_failed"  # fetched, but no plausible article found
BLOCKED = "blocked"  # page responded 403/429: likely bot-blocking, not a dead page


def fetch_html(url, timeout=15):
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _is_noise(tag):
    if tag.name in ("html", "body", "article", "main"):
        return False
    classes = " ".join(tag.get("class") or [])
    return bool(_NOISE_TOKENS.search(f"{classes} {tag.get('id') or ''}"))


def _clean(soup):
    for tag in soup(_NOISE_TAGS):
        tag.decompose()
    for tag in [t for t in soup.find_all(True) if _is_noise(t)]:
        if not tag.decomposed:
            tag.decompose()


def _prose_length(tag):
    return sum(len(p.get_text(" ", strip=True)) for p in tag.find_all("p"))


def _find_main(soup):
    """Pick the container most likely to hold the article."""
    for candidate in soup.find_all("article"):
        if len(candidate.get_text(" ", strip=True)) >= _MIN_ARTICLE_CHARS:
            return candidate
    for selector in ("main", "[role=main]"):
        found = soup.select_one(selector)
        if found and len(found.get_text(" ", strip=True)) >= _MIN_ARTICLE_CHARS:
            return found
    # Fallback: the block with the most paragraph text.
    blocks = soup.find_all(["div", "section"])
    return max(blocks, key=_prose_length, default=soup.body or soup)


def extract_text_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    _clean(soup)
    main = _find_main(soup)
    chunks, seen = [], set()
    for el in main.find_all(_TEXT_TAGS):
        # Skip containers of other text elements (e.g. <li> holding <p>) to avoid repeats.
        if el.name in ("li", "blockquote") and el.find(_TEXT_TAGS):
            continue
        text = " ".join(el.get_text(" ", strip=True).split())
        if text and text not in seen:
            seen.add(text)
            chunks.append(text)
    return "\n\n".join(chunks)


def extract_links_from_html(html, base_url):
    """Return the unique http(s) link targets (hrefs) inside the main article body.

    Uses the same clutter removal and main-container choice as the text extractor,
    so nav/footer/sidebar links are excluded. Relative links are resolved against
    `base_url`; mailto:, tel:, javascript: and same-page #fragments are dropped.
    """
    soup = BeautifulSoup(html, "html.parser")
    _clean(soup)
    main = _find_main(soup)
    links = []
    for a in main.find_all("a", href=True):
        absolute, _ = urldefrag(urljoin(base_url, a["href"].strip()))
        if urlparse(absolute).scheme in ("http", "https") and absolute not in links:
            links.append(absolute)
    return links


def extract_article_links(url, timeout=15):
    """Fetch `url` and return its article-body links, or None on any fetch error."""
    try:
        return extract_links_from_html(fetch_html(url, timeout), url)
    except Exception:
        return None


def extract_article_text(url, timeout=15):
    """Fetch `url` and return the main article prose as plain text.

    Returns "blocked" if the page itself responded 403/429 (likely bot-blocking,
    not a dead page -- same idea as the inconclusive-link handling in
    broken_links.py, just applied to the page fetch itself), "fetch_failed" on
    any other fetch error (network, SSL, other HTTP status, timeout, ...), and
    "extraction_failed" if the extracted text is under MIN_EXTRACTED_CHARS,
    which likely means the wrong part of the page was grabbed.
    """
    try:
        html = fetch_html(url, timeout)
    except urllib.error.HTTPError as e:
        return BLOCKED if e.code in _BLOCKED_STATUSES else FETCH_FAILED
    except Exception:
        return FETCH_FAILED
    text = extract_text_from_html(html)
    if len(text) < MIN_EXTRACTED_CHARS:
        return EXTRACTION_FAILED
    return text


def is_valid_article_text(result):
    """True only if `result` is real article text, not a failure sentinel.

    Always check this before treating the output of extract_article_text as prose,
    because the failure sentinels are ordinary strings too.
    """
    return (
        isinstance(result, str)
        and result.strip() != ""
        and result not in (FETCH_FAILED, EXTRACTION_FAILED, BLOCKED)
    )


if __name__ == "__main__":
    urls = [
        "https://inventivehq.com/blog/azure-active-directory-microsoft-entra-id-guide",
        "https://www.bmit.com.mt/blog/microsoft-is-renaming-azure-ad-to-microsoft-entra-id/",
        "https://this-host-does-not-exist.invalid/post",
    ]
    for url in urls:
        result = extract_article_text(url)
        if is_valid_article_text(result):
            print(f"{url}\n  OK: {len(result)} chars, starts: {result[:60]!r}\n")
        else:
            print(f"{url}\n  SKIPPED: {result}\n")
