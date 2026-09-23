"""Deprecated technology signal: flags retired/deprecated Entra ID / Azure AD technologies."""
import re

# canonical name -> (status / recommended replacement, [alternate spellings])
DEPRECATED = {
    "Azure AD Graph API": (
        "Retired; use Microsoft Graph API",
        [],
    ),
    "ADAL": (
        "Deprecated; use MSAL (Microsoft Authentication Library)",
        ["Azure AD Authentication Library"],
    ),
    "Basic Authentication": (
        "Retired in 2022 for legacy auth protocols; use modern authentication (OAuth 2.0)",
        [],
    ),
    "WS-Federation legacy endpoints": (
        "Being phased out; migrate to supported federation endpoints",
        [],
    ),
}

# Technologies that are only deprecated in certain contexts: a mention counts only
# if one of these words appears in the same sentence.
CONTEXT_REQUIRED = {
    "Basic Authentication": [
        "Exchange", "legacy", "protocol", "deprecated", "retired", "retirement",
    ],
}

_CONTEXT_RE = {
    tech: re.compile(
        r"(?<!\w)(?:" + "|".join(re.escape(w) for w in words) + r")s?(?!\w)",
        re.IGNORECASE,
    )
    for tech, words in CONTEXT_REQUIRED.items()
}
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")

_LOOKUP = {}
for _canonical, (_, _aliases) in DEPRECATED.items():
    for _name in [_canonical, *_aliases]:
        _LOOKUP[_name.lower()] = _canonical

# Longest names first so overlapping terms are matched once, as one span.
_PATTERN = re.compile(
    r"(?<!\w)("
    + "|".join(re.escape(n) for n in sorted(_LOOKUP, key=len, reverse=True))
    + r")(?!\w)",
    re.IGNORECASE,
)


def _sentence_at(text, pos):
    """Return the sentence of `text` that contains character offset `pos`."""
    start = 0
    for m in _SENTENCE_BREAK.finditer(text):
        if m.start() >= pos:
            return text[start:m.start()]
        start = m.end()
    return text[start:]


def check_deprecated_tech(text):
    """Return {'found': [{technology, status, count}], 'score': int}.

    score is the total number of deprecated-technology mentions (0 = clean).
    Technologies in CONTEXT_REQUIRED only count when a context word appears in the
    same sentence.
    """
    counts = {}
    for m in _PATTERN.finditer(text):
        canonical = _LOOKUP[m.group(1).lower()]
        ctx = _CONTEXT_RE.get(canonical)
        if ctx and not ctx.search(_sentence_at(text, m.start())):
            continue
        counts[canonical] = counts.get(canonical, 0) + 1
    found = [
        {"technology": t, "status": DEPRECATED[t][0], "count": c}
        for t, c in counts.items()
    ]
    return {"found": found, "score": sum(counts.values())}


if __name__ == "__main__":
    samples = [
        "Basic Authentication for Exchange Online legacy protocols was retired in 2022",
        "The API uses Basic Authentication for internal testing",
    ]
    for n, sample in enumerate(samples, 1):
        result = check_deprecated_tech(sample)
        print(f"{n}) {sample}")
        if not result["found"]:
            print("   No deprecated technologies found.")
        for f in result["found"]:
            print(f"   - '{f['technology']}' x{f['count']}: {f['status']}")
        print(f"   Deprecated tech score: {result['score']}\n")
