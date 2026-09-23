"""Small-scale test: embed a random sample of chunks, index with FAISS, and
run one similarity search against a test sentence.
"""
import json
import random

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

CHUNKS_PATH = "corpus_chunks.jsonl"
SAMPLE_SIZE = 200
SEED = 42
MODEL_NAME = "all-MiniLM-L6-v2"
TEST_SENTENCE = (
    "Basic Authentication for Exchange Online was permanently disabled "
    "in 2022 and is no longer supported"
)


def load_chunks(path):
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
    return chunks


def main():
    all_chunks = load_chunks(CHUNKS_PATH)
    print(f"Loaded {len(all_chunks)} total chunks from {CHUNKS_PATH}")

    random.seed(SEED)
    sample = random.sample(all_chunks, SAMPLE_SIZE)
    print(f"Sampled {len(sample)} random chunks (seed={SEED})\n")

    model = SentenceTransformer(MODEL_NAME)

    texts = [c["text"] for c in sample]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    embeddings = np.asarray(embeddings, dtype="float32")

    # Normalized embeddings + inner product = cosine similarity search.
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    print(f"Built FAISS index with {index.ntotal} vectors (dim={embeddings.shape[1]})\n")

    query_embedding = model.encode(
        [TEST_SENTENCE], normalize_embeddings=True, show_progress_bar=False
    )
    query_embedding = np.asarray(query_embedding, dtype="float32")

    scores, indices = index.search(query_embedding, k=1)
    best_idx = int(indices[0][0])
    best_score = float(scores[0][0])
    match = sample[best_idx]

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
