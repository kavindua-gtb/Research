"""Extract a "last updated" / "published" date from an arbitrary webpage.

Order of attempts: 1) structured metadata (JSON-LD, meta tags),
2) labelled dates in visible text, 3) "date_unknown" (never guess).
If the page cannot be fetched at all the result is "fetch_failed" instead.
"""
import json
import re
import urllib.request
from datetime import date, datetime
from html.parser import HTMLParser

import truststore
truststore.inject_into_ssl()  # trust the OS certificate store, same as Windows/curl

UNKNOWN = "date_unknown"  # fetched fine, no date found
FETCH_FAILED = "fetch_failed"  # could not fetch the page, so nothing was checked
_HEADERS = {"User-Agent": "Mozilla/5.0 (date-extractor)"}

# Meta tag keys (from property=, name= or itemprop=), lowercased -> kind.
_META_KEYS = {
    "article:modified_time": "modified",
    "og:updated_time": "modified",
    "datemodified": "modified",
    "last-modified": "modified",
    "article:published_time": "published",
    "og:published_time": "published",
    "datepublished": "published",
    "pubdate": "published",
    "date": "published",
    "dc.date": "published",
    "dc.date.issued": "published",
}
_JSONLD_KEYS = {"dateModified": "modified", "datePublished": "published"}

_MONTHS = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
_DATE_TEXT = (
    rf"(?:{_MONTHS}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"  # March 15, 2024
    rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTHS}\.?,?\s+\d{{4}}"  # 15 March 2024
    r"|\d{4}-\d{2}-\d{2}"  # 2024-03-15
    r"|\d{1,2}/\d{1,2}/\d{4})"  # 03/15/2024 or 15/03/2024, see parse_text_date
)
_LABELS = (
    r"(?:last\s+updated(?:\s+on)?|last\s+modified(?:\s+on)?|updated(?:\s+on)?|"
    r"modified(?:\s+on)?|published(?:\s+on)?|posted(?:\s+on)?)"
)
_TEXT_RE = re.compile(rf"\b({_LABELS})\s*[:\-]?\s*({_DATE_TEXT})", re.IGNORECASE)


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = []  # (key, content)
        self.jsonld = []  # raw script bodies
        self.text = []  # visible text chunks
        self._in_jsonld = False
        self._skip = 0  # depth inside script/style/noscript

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta" and a.get("content"):
            for attr in ("property", "name", "itemprop"):
                if a.get(attr):
                    self.meta.append((a[attr].lower(), a["content"]))
        elif tag == "time" and a.get("datetime"):
            pass  # <time> is ambiguous (could be any date), so it is not used
        elif tag == "script":
            if a.get("type", "").lower() == "application/ld+json":
                self._in_jsonld = True
            else:
                self._skip += 1
        elif tag in ("style", "noscript"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "script":
            if self._in_jsonld:
                self._in_jsonld = False
            elif self._skip:
                self._skip -= 1
        elif tag in ("style", "noscript") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_jsonld:
            self.jsonld.append(data)
        elif not self._skip:
            self.text.append(data)


def parse_date(value):
    """Parse ISO-8601 or common written dates to a date; None if unparseable."""
    value = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", value.strip()).replace(".", "")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%d %B %Y",
                "%d %b %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.replace("Sept", "Sep"), fmt).date()
        except ValueError:
            continue
    return None


_SLASH_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def parse_text_date(value):
    """Parse a date from visible text; return (date or None, ambiguous flag).

    Slash dates are resolved by position: a first number over 12 can only be a
    day (DD/MM/YYYY), a second number over 12 can only be a day (MM/DD/YYYY).
    If both are 12 or under and differ (e.g. 03/04/2024) the order is genuinely
    ambiguous: MM/DD/YYYY is used (the corpus convention) and flagged.
    """
    m = _SLASH_RE.match(value.strip())
    if not m:
        return parse_date(value), False
    a, b, year = (int(g) for g in m.groups())
    if a > 12:
        day, month, ambiguous = a, b, False
    elif b > 12:
        month, day, ambiguous = a, b, False
    else:
        month, day, ambiguous = a, b, a != b  # 03/03/2024 reads the same either way
    try:
        return date(year, month, day), ambiguous
    except ValueError:
        return None, False


def _walk_jsonld(node, out):
    if isinstance(node, dict):
        for key, kind in _JSONLD_KEYS.items():
            if isinstance(node.get(key), str):
                out.append((kind, node[key]))
        for v in node.values():
            _walk_jsonld(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_jsonld(v, out)


def _pick(candidates, parse=lambda raw: (parse_date(raw), False)):
    """Prefer a modified date over a published one; first parseable wins."""
    for want in ("modified", "published"):
        for kind, raw, source in candidates:
            if kind != want:
                continue
            d, ambiguous = parse(raw)
            if d:
                return {"date": d.isoformat(), "kind": kind, "raw": raw,
                        "source": source, "ambiguous_date_format": ambiguous}
    return None


def extract_date_from_html(html):
    """Return {'date', 'method', 'kind', 'raw', 'source', 'ambiguous_date_format'}.

    date is 'date_unknown' if nothing was found. ambiguous_date_format is True only
    for a visible-text slash date whose day/month order could not be determined.
    """
    p = _PageParser()
    p.feed(html)

    # 1a) JSON-LD
    ld = []
    for body in p.jsonld:
        try:
            found = []
            _walk_jsonld(json.loads(body), found)
            ld += [(k, r, "json-ld") for k, r in found]
        except ValueError:
            continue
    if hit := _pick(ld):
        return {**hit, "method": "structured:json-ld"}

    # 1b) Meta tags
    metas = [(_META_KEYS[k], v, f"meta:{k}") for k, v in p.meta if k in _META_KEYS]
    if hit := _pick(metas):
        return {**hit, "method": "structured:meta"}

    # 2) Labelled dates in visible text
    text = " ".join(" ".join(p.text).split())
    texts = []
    for m in _TEXT_RE.finditer(text):
        label = m.group(1).lower()
        kind = "published" if label.startswith(("publ", "post")) else "modified"
        texts.append((kind, m.group(2), f"text:{m.group(0)}"))
    if hit := _pick(texts, parse_text_date):
        return {**hit, "method": "text-pattern"}

    # 3) Give up rather than guess
    return {"date": UNKNOWN, "method": "none", "kind": None, "raw": None,
            "source": None, "ambiguous_date_format": False}


def extract_date(url, timeout=15):
    """Fetch `url` and extract its last-updated/published date.

    Any fetch problem (network, SSL, HTTP error, timeout, ...) is returned as
    date "fetch_failed" with the error text, never raised.
    """
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            html = resp.read().decode(charset, errors="replace")
    except Exception as e:
        return {"date": FETCH_FAILED, "method": "none", "kind": None, "raw": None,
                "source": None, "ambiguous_date_format": False,
                "error": f"{type(e).__name__}: {e}"}
    return extract_date_from_html(html)
