"""Full-corpus test: embed all chunks, index with FAISS, and run one
similarity search against a test sentence.
"""
import json
import os
import sys

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

CHUNKS_PATH = "corpus_chunks.jsonl"
EMBEDDINGS_CACHE_PATH = "corpus_embeddings.npy"
MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_TEST_SENTENCE = (
    "Azure Active Directory was renamed to Microsoft Entra ID, and the old "
    "Azure AD PowerShell module is deprecated in favor of the Microsoft "
    "Graph PowerShell SDK."
)
TEST_SENTENCE = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TEST_SENTENCE
BATCH_SIZE = 256


def load_chunks(path):
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
    return chunks


def main():
    all_chunks = load_chunks(CHUNKS_PATH)
    print(f"Loaded {len(all_chunks)} total chunks from {CHUNKS_PATH}\n")

    model = SentenceTransformer(MODEL_NAME)

    if os.path.exists(EMBEDDINGS_CACHE_PATH):
        embeddings = np.load(EMBEDDINGS_CACHE_PATH)
        print(f"Loaded cached embeddings from {EMBEDDINGS_CACHE_PATH}\n")
    else:
        texts = [c["text"] for c in all_chunks]
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
            batch_size=BATCH_SIZE,
        )
        embeddings = np.asarray(embeddings, dtype="float32")
        np.save(EMBEDDINGS_CACHE_PATH, embeddings)
        print(f"\nCached embeddings to {EMBEDDINGS_CACHE_PATH}\n")

    # Normalized embeddings + inner product = cosine similarity search.
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    print(f"\nBuilt FAISS index with {index.ntotal} vectors (dim={embeddings.shape[1]})\n")

    query_embedding = model.encode(
        [TEST_SENTENCE], normalize_embeddings=True, show_progress_bar=False
    )
    query_embedding = np.asarray(query_embedding, dtype="float32")

    scores, indices = index.search(query_embedding, k=1)
    best_idx = int(indices[0][0])
    best_score = float(scores[0][0])
    match = all_chunks[best_idx]

    print("=== Test sentence ===")
    print(TEST_SENTENCE)
    print()
    print("=== Closest matching chunk ===")
    print(f"Similarity score: {best_score:.4f}")
    print(f"Title: {match['title']}")
    print(f"Source: {match['source']}")
    print(f"Text: {match['text']}")


if __name__ == "__main__":
    main()
