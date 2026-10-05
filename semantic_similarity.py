"""Semantic similarity signal: how closely an article matches the current corpus.

Each article paragraph is embedded (same model and chunking as the corpus) and
matched to its nearest corpus chunk by cosine similarity, using an exact FAISS
inner-product index (IndexFlatIP) over the stored, unit-normalised corpus
embeddings. The article's score is the mean of those best-match similarities:
low similarity = content has drifted from current documentation = high decay.
"""
import json

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from process_corpus import chunk_paragraphs

CHUNKS_PATH = "corpus_chunks.jsonl"
EMBEDDINGS_PATH = "corpus_embeddings.npy"
MODEL_NAME = "all-MiniLM-L6-v2"

_state = {}


def _load():
    """Load the model and chunk metadata, and build the FAISS index, once.

    The index lives only in memory; nothing new is written to disk. Inner
    product on unit vectors is cosine similarity, so IndexFlatIP gives the same
    exact search as a dot product against the full embedding matrix.
    """
    if not _state:
        _state["model"] = SentenceTransformer(MODEL_NAME)
        embeddings = np.ascontiguousarray(np.load(EMBEDDINGS_PATH), dtype="float32")
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        _state["index"] = index
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            _state["chunks"] = [json.loads(line) for line in f]
        assert len(_state["chunks"]) == index.ntotal
    return _state


def compute_semantic_similarity(text):
    """Return {'similarity', 'paragraphs', 'best_matches'}.

    similarity is the mean best-match cosine similarity (0-1) over the article's
    paragraphs. Returns "not_applicable" as the similarity if the text has no
    usable paragraphs.
    """
    s = _load()
    paragraphs = chunk_paragraphs(text)
    if not paragraphs:
        return {"similarity": "not_applicable", "paragraphs": 0, "best_matches": []}

    q = s["model"].encode(paragraphs, normalize_embeddings=True, show_progress_bar=False)
    q = np.ascontiguousarray(q, dtype="float32")
    sims, idx = s["index"].search(q, 1)  # cosine (unit vectors), best match only
    best, best_idx = sims[:, 0], idx[:, 0]

    matches = [
        {"paragraph": paragraphs[i][:80], "similarity": float(best[i]),
         "source": s["chunks"][best_idx[i]]["source"]}
        for i in range(len(paragraphs))
    ]
    return {"similarity": float(best.mean()), "paragraphs": len(paragraphs),
            "best_matches": matches}
