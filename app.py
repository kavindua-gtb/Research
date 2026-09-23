"""Streamlit UI for the Knowledge Decay pipeline: paste a URL or article text, get a score."""
import streamlit as st

from pipeline import looks_like_url, run_pipeline_from_input

# ============================================================================
# Optional gauge chart for the Knowledge Decay Score. Self-contained: delete
# this whole block plus its one call site below (`render_score_gauge(score)`)
# to remove the feature entirely -- nothing else in this file depends on it.
import plotly.graph_objects as go


def render_score_gauge(score):
    """Render a 0-100 gauge for `score`, bands matching the green/amber/red
    thresholds used elsewhere on this page (0-30 / 30-60 / 60-100)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": " / 100"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#1f1f1f"},
            "steps": [
                {"range": [0, 30], "color": "#a5d6a7"},
                {"range": [30, 60], "color": "#ffcc80"},
                {"range": [60, 100], "color": "#ef9a9a"},
            ],
            "threshold": {
                "line": {"color": "#1f1f1f", "width": 4},
                "thickness": 0.9,
                "value": score,
            },
        },
    ))
    fig.update_layout(height=280, margin=dict(l=30, r=30, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)
# ============================================================================

SIGNAL_LABELS = {
    "semantic_similarity": "Semantic similarity",
    "terminology_drift": "Terminology drift",
    "broken_links": "Broken links",
    "deprecated_tech": "Deprecated technology",
    "temporal_metadata": "Temporal metadata",
}

st.set_page_config(page_title="Knowledge Decay Checker", page_icon="\U0001F550")
st.title("Knowledge Decay Checker")
st.write(
    "Paste an article URL, or the raw text of an article, and submit to see how "
    "stale its content is."
)

user_input = st.text_area(
    "Paste a URL or the article's text",
    height=220,
    placeholder="e.g. https://example.com/article OR paste the article text directly here",
)
submitted = st.button("Submit", type="primary")

if submitted:
    if not user_input.strip():
        st.warning("Please paste a URL or some article text first.")
    else:
        label = "Fetching and analyzing the URL..." if looks_like_url(user_input) \
            else "Analyzing the pasted text..."
        with st.spinner(label):
            result = run_pipeline_from_input(user_input)

        if "error" in result:
            messages = {
                "fetch_failed": "Could not fetch that URL.",
                "extraction_failed": "Fetched the page, but couldn't find article "
                                      "text on it.",
                "blocked": "That site blocked the request (403/429), likely "
                           "bot-blocking rather than a dead page.",
                "empty_text": "No text to analyze.",
            }
            st.error(messages.get(result["error"], f"Pipeline stopped: {result['error']}"))
        else:
            r, c = result["results"], result["combined"]

            st.subheader("Knowledge Decay Score")
            if c["score"] is None:
                st.write("N/A (no signal was applicable to this input)")
            else:
                score = c["score"]
                if score < 30:
                    color = "#2e7d32"  # green: low decay
                elif score <= 60:
                    color = "#e65100"  # amber/orange: moderate decay
                else:
                    color = "#c62828"  # red: high decay
                st.markdown(
                    f"<div style='font-size:4rem; font-weight:700; "
                    f"color:{color}; line-height:1.1;'>{score} / 100</div>",
                    unsafe_allow_html=True,
                )
                render_score_gauge(score)

            st.subheader("Signal breakdown")
            for name in ("semantic_similarity", "terminology_drift", "broken_links",
                         "deprecated_tech", "temporal_metadata"):
                sr = r[name]
                with st.container(border=True):
                    if name in c["excluded"]:
                        st.markdown(f"**{SIGNAL_LABELS[name]}** — not applicable")
                        continue

                    decay = c["signal_decay"][name]
                    weight = c["effective_weights"][name]
                    st.markdown(
                        f"**{SIGNAL_LABELS[name]}** — decay {decay:.2f}, "
                        f"weight {weight:.0%}"
                    )
                    if name == "semantic_similarity":
                        st.write(
                            f"Similarity to current documentation: "
                            f"{sr['similarity']:.1%} over {sr['paragraphs']} paragraphs."
                        )
                    elif name == "terminology_drift":
                        if sr["found"]:
                            for f in sr["found"]:
                                st.write(f"- '{f['term']}' x{f['count']} → '{f['replacement']}'")
                        else:
                            st.write("No outdated terminology found.")
                        if sr["exempted"]:
                            st.caption(f"{sr['exempted']} mention(s) exempted as explanatory.")
                    elif name == "broken_links":
                        st.write(
                            f"Checked {sr['total']} link(s); "
                            f"{len(sr['broken'])} broken, "
                            f"{len(sr['inconclusive'])} inconclusive."
                        )
                        for b in sr["broken"]:
                            st.write(f"- BROKEN ({b['reason']}): {b['url']}")
                        for i in sr["inconclusive"]:
                            st.caption(f"Inconclusive ({i['reason']}): {i['url']}")
                    elif name == "deprecated_tech":
                        if sr["found"]:
                            for f in sr["found"]:
                                st.write(f"- '{f['technology']}' x{f['count']}: {f['status']}")
                        else:
                            st.write("No deprecated technology found.")
                    elif name == "temporal_metadata":
                        note = " (ambiguous date format)" if sr.get("low_confidence") else ""
                        st.write(f"{sr['months_old']} months old{note}.")

            st.subheader("Explanation")
            if result["explanation"]:
                for line in result["explanation"]:
                    st.write(f"- {line}")
            else:
                st.write("(no signal contributed meaningfully)")
