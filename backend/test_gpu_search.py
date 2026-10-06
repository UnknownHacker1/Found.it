"""
Checks that the GPU search returns the same results as faiss.IndexFlatIP.

Run:  python backend/test_gpu_search.py   (skips if there is no NVIDIA GPU)
"""

import sys

import faiss
import numpy as np

from gpu_search import GpuFlatIP, gpu_available


def unit_vectors(n, d, seed):
    x = np.random.default_rng(seed).standard_normal((n, d), dtype=np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def check(n, d, n_queries, k):
    table = unit_vectors(n, d, 1)
    queries = unit_vectors(n_queries, d, 2)

    reference = faiss.IndexFlatIP(d)
    reference.add(table)
    ref_scores, ref_ids = reference.search(queries, k)

    scores, ids = GpuFlatIP(table).search(queries, k)
    assert scores.shape == ref_scores.shape and ids.shape == ref_ids.shape

    # The table is stored in fp16, so scores can differ slightly and near-ties can swap places
    recall = np.mean([len(set(a) & set(b)) / k for a, b in zip(ref_ids, ids)])
    assert recall >= 0.99, recall
    assert np.abs(np.sort(scores, axis=1) - np.sort(ref_scores, axis=1)).max() < 2e-3
    return recall


if __name__ == "__main__":
    if not gpu_available():
        print("No NVIDIA GPU or CuPy here, skipping")
        sys.exit(0)
    # covers a tiny table, odd sizes, other embedding sizes, and more queries than one batch
    for n, d, n_queries, k in ((5, 384, 2, 5), (777, 384, 3, 10), (50_000, 384, 20, 30), (10_000, 128, 9, 30)):
        recall = check(n, d, n_queries, k)
        print(f"n={n} d={d} queries={n_queries} k={k}: recall {recall:.4f} OK")
