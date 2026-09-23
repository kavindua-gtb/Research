"""Aggregation step: combine the five decay signals into one Knowledge Decay Score."""

NOT_APPLICABLE = "not_applicable"

SIGNALS = (
    "semantic_similarity",
    "terminology_drift",
    "broken_links",
    "deprecated_tech",
    "temporal_metadata",
)

# Start with equal weighting; weights are renormalised over applicable signals.
WEIGHTS = {name: 0.2 for name in SIGNALS}

# Count-based signals saturate: this many hits (or overdue months) = maximum decay.
TERMINOLOGY_CAP = 5    # outdated terms
DEPRECATED_CAP = 3     # deprecated technologies
TEMPORAL_CAP = 36      # months past the 12-month freshness window

# A signal is mentioned in the explanation when its decay is at least this much.
MEANINGFUL_DECAY = 0.2


def _is_na(result):
    if result == NOT_APPLICABLE:
        return True
    return isinstance(result, dict) and result.get("score") == NOT_APPLICABLE


def _similarity(result):
    return result["similarity"] if isinstance(result, dict) else result


def _clamp(x):
    return max(0.0, min(1.0, float(x)))


def signal_decay(name, result):
    """Normalise one signal's result to a 0-1 decay value (1 = most decayed)."""
    if name == "semantic_similarity":
        return _clamp(1 - _similarity(result))  # low similarity = high decay
    if name == "broken_links":
        return _clamp(result["score"])  # already broken / total
    if name == "terminology_drift":
        return _clamp(result["score"] / TERMINOLOGY_CAP)
    if name == "deprecated_tech":
        return _clamp(result["score"] / DEPRECATED_CAP)
    if name == "temporal_metadata":
        return _clamp(result["score"] / TEMPORAL_CAP)
    raise KeyError(f"Unknown signal: {name}")


def combine_signals(results, weights=WEIGHTS):
    """Combine signal results into a weighted Knowledge Decay Score (0-100).

    Signals whose result is "not_applicable" are excluded and their weight is
    redistributed proportionally across the rest. Returns
    {'score', 'signal_decay', 'effective_weights', 'excluded', 'low_confidence'};
    score is None if no signal is applicable.
    """
    missing = [n for n in SIGNALS if n not in results]
    if missing:
        raise ValueError(f"Missing signal results: {missing}")

    excluded = [n for n in SIGNALS if _is_na(results[n])]
    active = [n for n in SIGNALS if n not in excluded]
    if not active:
        return {"score": None, "signal_decay": {}, "effective_weights": {},
                "excluded": excluded, "low_confidence": []}

    total_weight = sum(weights[n] for n in active)
    effective = {n: weights[n] / total_weight for n in active}
    decay = {n: signal_decay(n, results[n]) for n in active}
    score = 100 * sum(effective[n] * decay[n] for n in active)

    low_conf = [n for n in active
                if isinstance(results[n], dict) and results[n].get("low_confidence")]
    return {"score": round(score, 1), "signal_decay": decay,
            "effective_weights": effective, "excluded": excluded,
            "low_confidence": low_conf}


def _age_phrase(months):
    if months >= 24:
        return f"over {months // 12} years"
    if months >= 12:
        return "over a year"
    return f"{months} months"


def generate_explanation(results):
    """Return a list of plain-English sentences, one per meaningful signal."""
    sentences = []
    for name in SIGNALS:
        r = results[name]
        if _is_na(r) or signal_decay(name, r) < MEANINGFUL_DECAY:
            continue

        if name == "semantic_similarity":
            sim = round(_similarity(r) * 100)
            sentences.append(
                f"This article's similarity to current documentation is {sim}%.")
        elif name == "terminology_drift":
            pairs = [f"'{f['term']}' (now '{f['replacement']}')" for f in r["found"]]
            sentences.append(
                f"This article uses outdated terminology: {_quoted_list_raw(pairs)}.")
        elif name == "broken_links":
            n, total = len(r["broken"]), r["total"]
            verb = "appears" if n == 1 else "appear"
            sentences.append(
                f"{n} of the {total} links in this article {verb} to be broken.")
        elif name == "deprecated_tech":
            techs = [f"'{f['technology']}' ({f['status']})" for f in r["found"]]
            sentences.append(
                f"This article references deprecated technology: {_quoted_list_raw(techs)}.")
        elif name == "temporal_metadata":
            note = " (the date format was ambiguous, so this is approximate)" \
                if r.get("low_confidence") else ""
            sentences.append(
                f"This article has not been reviewed in {_age_phrase(r['months_old'])}"
                f"{note}.")
    return sentences


def _quoted_list_raw(items):
    """Join already-formatted items: 'a', 'a and b', 'a, b and c'."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + f" and {items[-1]}"


if __name__ == "__main__":
    from temporal_metadata import check_temporal_metadata

    results = {
        "semantic_similarity": 0.3,
        "terminology_drift": {
            "found": [
                {"term": "Azure AD PowerShell", "replacement": "Microsoft Graph PowerShell", "count": 1},
                {"term": "MFA Server", "replacement": "Microsoft Entra multifactor authentication", "count": 1},
            ],
            "score": 2,
        },
        "broken_links": {
            "total": 2,
            "broken": [{"url": "https://docs.microsoft.com/en-us/azure/active-directory/gone", "reason": "404"}],
            "inconclusive": [],
            "score": 0.5,
        },
        "deprecated_tech": {
            "found": [{"technology": "ADAL",
                       "status": "Deprecated; use MSAL (Microsoft Authentication Library)",
                       "count": 1}],
            "score": 1,
        },
        "temporal_metadata": check_temporal_metadata("date_unknown"),
    }

    combined = combine_signals(results)
    print(f"Knowledge Decay Score: {combined['score']} / 100")
    print(f"Excluded (not applicable): {combined['excluded']}")
    print("Effective weights: " + ", ".join(
        f"{n}={w:.1%}" for n, w in combined["effective_weights"].items()))
    print("Signal decay (0-1): " + ", ".join(
        f"{n}={d:.2f}" for n, d in combined["signal_decay"].items()))
    print("\nExplanation:")
    for line in generate_explanation(results):
        print(f"- {line}")
