"""Terminology drift signal: flags outdated Microsoft product terms in text."""
import re

from deprecated_tech import _sentence_at  # same sentence splitting as the Basic Auth check

# old term -> current term
GLOSSARY = {
    "Azure AD": "Microsoft Entra ID",
    "Azure Active Directory": "Microsoft Entra ID",
    "Azure AD PowerShell": "Microsoft Graph PowerShell",
    "MFA Server": "Microsoft Entra multifactor authentication",
    "Conditional Access baseline policies": "Conditional Access policies",
}

# Longest terms first so "Azure AD PowerShell" wins over its prefix "Azure AD"
# and each span of text is only counted once.
_PATTERN = re.compile(
    r"(?<!\w)("
    + "|".join(re.escape(t) for t in sorted(GLOSSARY, key=len, reverse=True))
    + r")(?!\w)",
    re.IGNORECASE,
)
_LOOKUP = {t.lower(): t for t in GLOSSARY}

# An outdated term mentioned in the same sentence as one of these is being
# explained as outdated (e.g. "Azure AD was renamed to Microsoft Entra ID"),
# not used as current terminology, so that mention is not counted as drift.
_EXPLAINING_RE = re.compile(
    r"(?<!\w)(?:renam(?:e|ed|ing)|rebrand(?:ed|ing)?|now\s+called|formerly|previously)(?!\w)",
    re.IGNORECASE,
)

# A sentence that also names "Entra ID" alongside the outdated term is reliably
# contrasting old vs. new (e.g. "Azure AD ... now Entra ID"), not just reusing
# the old name, so it's exempted too even without one of the trigger words above.
_ENTRA_ID_RE = re.compile(r"(?<!\w)Entra\s+ID(?!\w)", re.IGNORECASE)


def check_terminology_drift(text):
    """Return {'found': [{term, replacement, count}], 'score': int, 'exempted': int}.

    score is the total number of outdated-term occurrences (0 = clean). Mentions
    in a sentence that explains the change (renamed, formerly, previously, ...)
    are not counted; `exempted` says how many were skipped that way.
    """
    counts = {}
    exempted = 0
    for m in _PATTERN.finditer(text):
        sentence = _sentence_at(text, m.start())
        if _EXPLAINING_RE.search(sentence) or _ENTRA_ID_RE.search(sentence):
            exempted += 1
            continue
        canonical = _LOOKUP[m.group(1).lower()]
        counts[canonical] = counts.get(canonical, 0) + 1
    found = [
        {"term": t, "replacement": GLOSSARY[t], "count": c}
        for t, c in counts.items()
    ]
    return {"found": found, "score": sum(counts.values()), "exempted": exempted}


if __name__ == "__main__":
    sample = (
        "To manage users, use the Azure AD PowerShell module and configure "
        "MFA Server for multi-factor authentication."
    )
    result = check_terminology_drift(sample)
    print(f"Text: {sample}\n")
    if not result["found"]:
        print("No outdated terms found.")
    for f in result["found"]:
        print(f"- '{f['term']}' x{f['count']} -> '{f['replacement']}'")
    print(f"\nDrift score: {result['score']}")
