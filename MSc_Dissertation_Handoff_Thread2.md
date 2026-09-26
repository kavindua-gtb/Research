# MSc Dissertation Handoff — Thread 2 → Thread 3

**Read this fully before doing anything else.** This is a continuation document for a new Claude conversation thread. The previous thread (this one) covered Chapters 3–4 and the start of the actual system implementation, and is approaching its context limit.

This is the **second** handoff in this project. The first thread ("MSc Research (Chapter 1-2)") produced `MSc_Dissertation_Handoff.md`, already in the GitHub repo, covering Chapters 1–2. Read that one too if it's still there — this document assumes it as prior context and does not repeat it in full.

---

## 1. Who this is for

**Kavindu** — ~15 years IT infrastructure experience (Microsoft 365: Intune/Autopilot, Entra ID, Defender, Conditional Access, SharePoint, Teams, Exchange Online; Windows Server; Azure). **Zero prior programming/coding background.** Completing an MSc in Artificial Intelligence at London Metropolitan University, delivered via NEXT Campus, Colombo. Supervisor: **Dr. Kaneeka Vidanage**.

**Always explain technical/coding things in plain English.** He learns fast and asks good clarifying questions, but never assume familiarity with basic dev concepts — PATH, virtual environments, git identity, HTTP status codes, etc. have all needed patient first-principles explanation in this thread.

---

## 2. The project

**Dissertation:** A multi-signal framework for detecting "knowledge decay" in enterprise knowledge bases — specifically, detecting when third-party technical articles (blog posts, tutorials) about Microsoft Entra ID have become outdated relative to Microsoft's own current documentation.

**Five signals**, equally weighted (20% each by default):
1. **Semantic similarity** — SBERT (`all-MiniLM-L6-v2`) + FAISS against a real corpus of Microsoft Learn docs
2. **Terminology drift** — glossary-based detection of superseded terms (e.g. "Azure AD" → "Microsoft Entra ID")
3. **Broken links** — HTTP status checking of links within an article
4. **Deprecated technology** — keyword-list detection of retired tools/protocols (ADAL, ~~Azure AD Graph API~~, Basic Authentication, WS-Federation)
5. **Temporal metadata** — how long since an article was last reviewed/updated

**Explicitly out of scope** (deliberate, agreed decisions, not oversights): DPR (dense passage retrieval), any trained NLP entity/topic classifier — replaced with simpler keyword/rule-based approaches. This was a deliberate scope-down from an earlier, over-ambitious ChatGPT-authored technical spec, chosen because the student has zero coding background and a fixed deadline.

**Corpus:** git-cloned `MicrosoftDocs/entra-docs` (public GitHub repo, real Microsoft documentation), not scraped.

**GitHub repo (public):** `https://github.com/kavindua-gtb/Research` — the single source of truth for all documents and deliverables. **Claude cannot push to it directly** — only public read access via `git clone` or `web_fetch`. Every file Claude produces must be handed to Kavindu to upload himself (drag-and-drop via GitHub's web UI, or via `git add/commit/push` inside Claude Code on his VM).

---

## 3. Chapters 1–2 status

Done in Thread 1. Polished, citations verified, Figure 2 (concept map) corrected. Two categories of **unconfirmed-as-applied** open items carried over from Thread 1, never verified as actually fixed in the live document:
- A handful of typos: "propsal," "cchapter," "sstudy," "obscenness" (→ "obsolescence," repeated), "addres," inconsistent "it professional" capitalization, one stray first-person "we" breaking third-person convention.
- 7 specific find-and-replace text edits tying Chapter 2's Critical Analysis prose to the 5 named pathways in the corrected Figure 2 (exact before/after text was given in chat, never confirmed pasted in).

**One additional open item found in Thread 2:** `Karpukhin et al. (2020)` (the DPR paper) sits in the Chapter 1–2 reference list but was never confirmed as actually cited anywhere in the body text — possible orphan reference, never resolved.

---

## 4. Chapters 3–4 status: COMPLETE, independently verified against the student's own merged document

**Final delivered file:** `24077283_Chapters_3_4_Draft_FINAL.docx`. This was then cross-checked against the student's own manually-merged master (`24077283_Draft4.docx`) — verified page by page, image by image.

### What's confirmed correct (checked directly, not assumed):
- **All 7 Chapter 4 figures rebuilt from scratch and individually verified**, including fixing real bugs found along the way:
  - **4.1 Stakeholder onion** — fixed two garbled/typo'd labels ("ENTERPISE" → "ENTERPRISE", scrambled "BENFIIEICAIEIS" → "BENEFICIARIES", "AUTHORTATIVE" → "AUTHORITATIVE")
  - **4.2 Use case diagram** — removed all crossing lines, fixed a backwards `<<extend>>` arrow (was pointing base→extension instead of extension→base)
  - **4.3 Class diagram** — added 3 classes that existed in the sequence diagrams but were missing from the class diagram (a specific thing the supervisor said examiners check for): `ContentExtractor`, `FAISSIndex`, `EvaluationModule`, with proper UML generalisation/aggregation notation and a "Decay Signals" package grouping
  - **4.4 Activity diagram** — added a missing "No" label on the decision branch, added a missing end-node (the error path was previously a dead end with nowhere to terminate)
  - **4.5 / 4.6 Sequence diagrams** — added proper activation bars, fixed arrow conventions to standard UML (solid+filled arrowhead for calls, dashed+open arrowhead for returns)
  - **4.7 Architecture diagram** — fixed a real bug where a connector line ran straight through box text (looked like a strikethrough at first glance), plus several arrow-direction/routing bugs found only by checking each connector individually rather than trusting the full-image render
- **Chapter 3 compressed per direct, confirmed supervisor feedback** (Session 3 transcript, see below): §3.1, 3.2, 3.3, 3.4, 3.6 all collapsed from expanded subsectioned versions back into tight single paragraphs — removed "what is X" definitional explanations, kept only the selection made and the reasoning + citations. This deliberately reversed an earlier expansion done earlier in this same thread (done before the word-count picture was fully understood).
- **Chapter 4 diagram descriptions trimmed to 1–2 lines** per the same supervisor feedback — confirmed correctly applied for Figures 4.3, 4.4, 4.5, 4.6, 4.7.

### ⚠️ Two confirmed open items (found during final verification, not yet fixed):
1. **Figure 4.1 (onion) description** in the student's live document is still a full, untrimmed paragraph — reworded differently from the original but not compressed to 1–2 lines as instructed.
2. **Figure 4.2 (use case) description** — same issue, still a full paragraph, not trimmed.

Exact replacement text for both was offered but not yet confirmed as wanted/applied — **ask Kavindu if he still wants this done** before doing anything else with Chapter 4.

### Deferred by Kavindu's own choice (not forgotten, low priority):
- Optional UML multiplicities on class diagram relationships
- Optional flow chart visualisation of Table 3.1 (Research Methodology Execution Workflow)

### Reference list
A full 24-entry Harvard-formatted reference list (16 original Ch1–2 entries + 8 new Ch3–4 methodology citations: Alexander & Beus-Dukic 2009, Anderson 2010, Hevner et al. 2004, Oates 2006, Peffers et al. 2007, Saunders/Lewis/Thornhill 2019, Schwaber & Sutherland 2020, Sommerville 2016) was delivered as `References.docx`. **Not yet confirmed as pasted into the live master document.**

---

## 5. Key authoritative source documents (all read and verified, all in the GitHub repo)

- **"CS7P01NM - Project Friendly Guide.pdf"** (37 pages) — the authoritative structure/format guide, supersedes the earlier, thinner `Thesis Overview.pdf`. Confirms:
  - **8-chapter structure**: 1 Introduction, 2 Literature Review, 3 Methodology, 4 Analysis and Design (Kavindu's document titles this "System Requirement Specification" — confirmed fine to keep, content matches), 5 Implementation, **6 Testing and Validation** (a distinct chapter from Evaluation — content still undecided, pending supervisor clarification, see open items), 7 Evaluation and Performance Analysis, 8 Conclusion/Limitations/Future Work.
  - **Word count**: 12,000–15,000 words, **excludes references and appendices** (confirmed directly by the supervisor in the Session 3 transcript). Corresponds to "40–100 pages" per an updated version of the guide (originally said 40–60; supervisor had it revised upward).
  - **Format**: Arial, 12pt body / 14pt bold headings, **1.5 line spacing** (not double — this overrides London Met's general default, confirmed by this module-specific document), 1-inch margins, page numbers bottom-right in Arial 12, figure/table captions in Arial italic 12.
- **"Supervision Season 03 - Transcript.txt"** — a long, multi-student group supervision session. **Kavindu's own segment is lines 978–1288 only** (he introduces himself as "Kavindi," labelled "Speaker 4"). Everything before line 978 is feedback for a **different student** ("Dinuka") and must never be misattributed to Kavindu. Key confirmed points from his actual segment:
  - The ~100-page target was **verbally reconfirmed** by the supervisor directly to Kavindu ("plus or minus 10 is not a concern to reduce marks") — but this is only verbal, never formally/in writing, so **don't deliberately aim for exactly 100 pages** — let genuine content decide length.
  - Methodology sections should name alternatives briefly, not explain what each one *is* — explicitly said to generalise to "the others as well" (i.e. applies to Kavindu even though first said to Dinuka).
  - Diagram descriptions should be 1–2 lines after each figure, not paragraphs.
  - Class diagram / sequence diagram consistency matters to examiners — this led to the 3-missing-classes fix above.
- **Draft2.docx** = Chapters 1–2 (from Thread 1).

---

## 6. THE ACTUAL PROGRAM — implementation status

This is a real, working system, built incrementally with Claude Code on an Azure VM, tested against real content at every stage — not just synthetic examples.

### Environment
- **Azure VM, Windows 11** (deliberately chosen over Windows Server despite a BYOL licensing complication that was flagged and apparently resolved), 16GB RAM, **Python 3.12 specifically** (not the newest version — avoids a known `faiss-cpu` wheel-availability problem on very new Python releases). Git, Claude Code both installed and working.
- **Every session, the routine is:** (1) Start the VM in the Azure Portal (2) RDP in (3) `cd C:\Projects\Research` (4) run `claude` to relaunch Claude Code in the project folder.
- **Always stop the VM via the Azure Portal's Stop button**, never by shutting down Windows from inside the VM — the latter still gets billed, only the Portal's "Stopped (deallocated)" state actually stops charges.
- GitHub repo is cloned onto the VM at `C:\Projects\Research`. Git push authentication is working (browser OAuth via Git Credential Manager) after resolving an initial identity-not-configured issue and a diverged-history conflict (needed `git pull` before `push`, since Kavindu had also uploaded files directly via GitHub's web UI). **Last confirmed real commit** (verified via actual `git log` output, not assumed): `"Working Streamlit UI with gauge chart, all 5 signals, and pipeline verified on real articles"`.

### Milestones 0–7: all DONE and verified. Milestone 8: not yet started — this is the next real work.

| Milestone | Status | Key detail |
|---|---|---|
| 0. Environment setup | ✅ Done | See above |
| 1. Corpus acquisition | ✅ Done | Cloned `MicrosoftDocs/entra-docs`, 4,984 markdown files, confirmed genuine articles not just repo boilerplate |
| 2/3. Chunking | ✅ Done | 123,193 chunks from 4,969 files, saved as `corpus_chunks.jsonl`. 11 files legitimately produced zero chunks (confirmed benign — Microsoft's reusable "include" snippet files, tables only, no prose) |
| 4. Core proof of concept | ✅ Done, strongly proven | SBERT + FAISS (`IndexFlatIP`, cosine similarity). On-topic test (Entra ID rename question) scored **0.86** against the full corpus; off-topic control ("sourdough bread") scored only **0.28** — proves the system distinguishes real relevance from noise |
| 5. Remaining 4 signals | ✅ Done, all debugged against real edge cases | See detail below |
| 6. Aggregation + explanation | ✅ Done | `combine_signals.py`: equal weighting, `not_applicable` signals excluded with weight redistributed rather than zeroed or crashing. `generate_explanation()` produces genuinely plain-English sentences, confirmed readable |
| 7. Streamlit UI | ✅ Done, tested on 5 real articles | See detail below |
| 8. Evaluation dataset + batch harness | ❌ Not started | **This is the next step** |

### Signal implementation detail (Milestone 5)
- **`terminology_drift.py`**: glossary-based, case-insensitive, whole-word, no double-counting overlaps. Has a context-word exemption (won't count an old term as drift if "Entra ID" appears in the same sentence — i.e. the article is explaining the rename, not stuck using the old name). **Known, accepted limitation for Ch6**: the score caps/saturates at 5 mentions, so a 6-mention and a 17-mention article both show identical maximum decay on this signal.
- **`broken_links.py`**: HTTP status checking, follows redirects, treats 403/429 (bot-blocking) as `"inconclusive"` (excluded from score, not counted as broken) — applies both per-link and to the all-links-inconclusive case and the zero-links case (both `not_applicable`, not scored as clean). Treats the full 2xx range as success (a real bug — a legitimate 202 was being wrongly flagged broken — was found and fixed).
- **`deprecated_tech.py`**: keyword-list (ADAL, Azure AD Graph API, Basic Authentication, WS-Federation), same context-word sentence-boundary exemption logic as terminology drift for "Basic Authentication" specifically (avoids false positives on unrelated uses of that generic phrase).
- **`temporal_metadata.py` + `extract_date.py`**: for the corpus, reads Microsoft's clean `ms.date` frontmatter. For real third-party articles, tries structured JSON-LD → meta tags → visible-text date patterns, with graceful fallback states: `"date_unknown"`, `"fetch_failed"` (needed a `truststore` package fix for a Windows-VM-specific TLS interception issue), and an `"ambiguous_date_format"` flag for genuinely ambiguous slash-dates. 12-month freshness threshold, 1 point per month over. **All numeric thresholds here (and the signal caps above) are explicitly provisional — meant to be tuned using real results once Milestone 8 exists, not before.**

### Streamlit UI (Milestone 7) — real-world test results
Single combined input box (auto-detects URL vs. pasted text), colour-coded score (green <30, amber 30–60, red >60 — **also explicitly provisional/unvalidated**), a working Plotly gauge chart (a fancier custom "needle" version was attempted and abandoned as not worth the effort — the simpler bar-style gauge is what's committed). Tested end-to-end on 5 real articles:
- InventiveHQ Entra ID guide → **21.7/100**
- Quest blog (Conditional Access) → **~40.4–40.6/100**
- GeeksforGeeks (mixed/partially-updated terminology) → **28.2/100**
- Lepide blog → blocked by the site's own bot-protection even after the SSL fix; worked around by pasting the article's raw text directly into the app instead of the URL (text saved as `lepide_article_text.txt`)
- Ravenswood Technology (genuinely fresh, correctly-branded content) → **5.3/100** — a deliberate **true-negative** test, proving the system doesn't just flag everything as decayed

**Known, deliberately-unresolved limitation for Ch6**: a single maxed-out signal can still result in an overall low/green score once diluted across 5 equally-weighted signals — mathematically correct given the current design, flagged as an honest limitation to write up rather than silently patch now.

### Milestone 8 — the actual next step
Plan already agreed: ~40–60 labelled articles, split across real-known-fresh, real-known-outdated, and deliberately-synthetic-modified categories. Then a batch evaluation script (precision/recall/F1) and an ablation study (each signal removed in turn). **All the provisional thresholds mentioned above should be revisited using this milestone's real results.**

---

## 7. Documents delivered this thread (all in `/mnt/user-data/outputs` at time of writing — confirm still needed / re-deliver if this thread's outputs are no longer accessible)

- `24077283_Chapters_3_4_Draft_FINAL.docx`
- `References.docx` (24-entry reference list)
- `Implementation_Build_Tracker.xlsx` (milestone tracker — last updated mid-Milestone 6/7, **should be updated to reflect Milestone 7 fully done and Milestone 8 as next**)
- Individual PNGs for all 7 Chapter 4 figures, the corrected Chapter 2 concept map, and the corrected Chapter 1 (?) figure — delivered individually across the thread
- `lepide_article_text.txt` (workaround for the blocked Lepide article)

---

## 8. Important cross-cutting notes

- **Academic integrity boundary, already firmly set**: Kavindu asked about using an AI "humanizer" tool to evade AI-detection software on the dissertation's written text. This was declined as a bright line — real risk given the signed academic integrity declaration on his cover sheet. Natural, non-robotic writing style itself is fine and already the standard. He was advised to ask his supervisor directly what AI-assistance disclosure is expected (the Friendly Guide has no explicit policy, but the transcript shows the supervisor casually accepting "Figure source: ChatGPT"-style attribution from another student). **Not confirmed whether he's actually asked this yet.**
- **A healthy, recurring pattern this whole thread**: real mistakes were made and caught by careful re-verification (a citation misattribution, a missing-arrowhead bug from directional-math error, a wrong character-count threshold) — always corrected transparently once found. The working standard throughout: verify before asserting, check the actual rendered/executed result rather than trust a description of it, be honest about the line between "confirmed" and "assumed." **Keep this standard in the new thread.**

---

## 9. Immediate next steps for the new thread

Ask Kavindu directly:
1. Does he still want the Figure 4.1 / 4.2 description compression finished (2 known open text edits, exact replacements can be regenerated)?
2. Ready to start Milestone 8 (evaluation dataset), or anything else first?
3. Any updates from his supervisor since this handoff was written — particularly on Chapter 6's content (Testing and Validation) and the AI-disclosure question?
4. Any changes to Chapters 1–2's still-open items (typos, the 7 find-replace edits, the Karpukhin orphan reference)?
