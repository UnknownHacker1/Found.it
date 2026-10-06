"""
Benchmark: Found.it's GPU search vs FAISS on the CPU (what Found.it used before)
and vs plain PyTorch on the GPU.

Uses random unit vectors with the same size as Found.it's embeddings (384).
Brute-force search costs the same whatever the vectors contain, so this measures
speed honestly; recall is checked against FAISS on the same data.

Run from the repo root:  python benchmarks/gpu_search_bench.py
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import cupy as cp
import faiss
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from gpu_search import MAX_BATCH, GpuFlatIP  # noqa: E402


def unit_vectors(n, d, seed):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((n, d), dtype=np.float32)
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    return x


def median_ms(fn, repeats, warmup=3):
    for _ in range(warmup):
        fn()
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return statistics.median(times)


def kernel_ms(index, q, repeats=30):
    """Median time of the scoring kernel alone, measured with CUDA events."""
    qd = cp.asarray(q)
    index.scores(qd)  # warm-up
    start, stop = cp.cuda.Event(), cp.cuda.Event()
    times = []
    for _ in range(repeats):
        start.record()
        index.scores(qd)
        stop.record()
        stop.synchronize()
        times.append(cp.cuda.get_elapsed_time(start, stop))
    return statistics.median(times)


def peak_bandwidth_gbs():
    p = cp.cuda.runtime.getDeviceProperties(0)
    clock_khz = p.get("memoryClockRate") or cp.cuda.runtime.deviceGetAttribute(36, 0)
    bus_bits = p.get("memoryBusWidth") or cp.cuda.runtime.deviceGetAttribute(37, 0)
    return 2.0 * clock_khz * 1e3 * (bus_bits / 8) / 1e9


def copy_bandwidth_gbs(nbytes=512 * 1024 * 1024, repeats=10):
    """Practical ceiling: a plain device-to-device copy (bytes read + bytes written)."""
    a = cp.empty(nbytes // 4, dtype=cp.float32)
    b = cp.empty_like(a)
    cp.copyto(b, a)
    start, stop = cp.cuda.Event(), cp.cuda.Event()
    best = 0.0
    for _ in range(repeats):
        start.record()
        cp.copyto(b, a)
        stop.record()
        stop.synchronize()
        best = max(best, 2 * nbytes / (cp.cuda.get_elapsed_time(start, stop) / 1000) / 1e9)
    del a, b
    cp.get_default_memory_pool().free_all_blocks()
    return best


def free_gpu():
    cp.get_default_memory_pool().free_all_blocks()
    torch.cuda.empty_cache()


def run(n, d, k, n_queries, repeats):
    base = unit_vectors(n, d, seed=1)
    queries = unit_vectors(n_queries, d, seed=2)
    row = {"n": n}

    cpu = faiss.IndexFlatIP(d)
    cpu.add(base)
    row["faiss_cpu_ms"] = median_ms(lambda: cpu.search(queries[:1], k), repeats)
    row["faiss_cpu_batch_ms_per_query"] = median_ms(lambda: cpu.search(queries[:MAX_BATCH], k), repeats) / MAX_BATCH
    ref_scores, ref_ids = cpu.search(queries, k)

    gpu = GpuFlatIP(base)
    row["gpu_search_ms"] = median_ms(lambda: gpu.search(queries[:1], k), repeats)
    batch = queries[:MAX_BATCH]
    row["gpu_batch_ms_per_query"] = median_ms(lambda: gpu.search(batch, k), repeats) / len(batch)
    scoring_ms = kernel_ms(gpu, queries[:1])
    row["scoring_only_ms"] = scoring_ms
    row["achieved_gbs"] = n * d * 2 / (scoring_ms / 1000) / 1e9

    got_scores, got_ids = gpu.search(queries, k)
    hits = sum(len(set(a) & set(b)) for a, b in zip(ref_ids, got_ids))
    row["recall_at_k"] = hits / (len(queries) * k)
    row["max_score_error"] = float(np.max(np.abs(np.sort(got_scores, axis=1) - np.sort(ref_scores, axis=1))))
    del gpu
    free_gpu()

    for name, dtype in (("torch_fp32_ms", torch.float32), ("torch_fp16_ms", torch.float16)):
        table = torch.as_tensor(base, device="cuda").to(dtype)

        def torch_search():
            q = torch.as_tensor(queries[:1], device="cuda").to(dtype)
            top = torch.topk(q @ table.T, k, dim=1)
            return top.values.float().cpu().numpy(), top.indices.cpu().numpy()

        row[name] = median_ms(torch_search, repeats)
        del table
        free_gpu()

    row["speedup_vs_faiss_cpu"] = row["faiss_cpu_ms"] / row["gpu_search_ms"]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[100_000, 1_000_000])
    ap.add_argument("--dim", type=int, default=384)
    ap.add_argument("--k", type=int, default=30, help="Found.it asks FAISS for top_k * 3 = 30")
    ap.add_argument("--queries", type=int, default=50)
    ap.add_argument("--repeats", type=int, default=30)
    ap.add_argument("--out", default="benchmarks/results.json")
    args = ap.parse_args()

    p = cp.cuda.runtime.getDeviceProperties(0)
    name = p["name"].decode() if isinstance(p["name"], bytes) else str(p["name"])
    info = {
        "gpu": name,
        "faiss_threads": faiss.omp_get_max_threads(),
        "peak_bandwidth_gbs": peak_bandwidth_gbs(),
        "copy_bandwidth_gbs": copy_bandwidth_gbs(),
    }
    print(f"GPU: {info['gpu']} | FAISS CPU threads: {info['faiss_threads']}")
    print(f"Memory bandwidth: {info['peak_bandwidth_gbs']:.0f} GB/s on paper, "
          f"{info['copy_bandwidth_gbs']:.0f} GB/s measured with a plain copy")

    rows = [run(n, args.dim, args.k, args.queries, args.repeats) for n in args.sizes]

    print()
    print("One query at a time (what Found.it does per search):")
    print("| vectors | FAISS CPU | PyTorch GPU fp32 | PyTorch GPU fp16 | Found.it GPU | speedup vs FAISS | kernel bandwidth | recall@k |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['n']:,} | {r['faiss_cpu_ms']:.2f} ms | {r['torch_fp32_ms']:.2f} ms | {r['torch_fp16_ms']:.2f} ms | "
              f"{r['gpu_search_ms']:.2f} ms | {r['speedup_vs_faiss_cpu']:.1f}x | "
              f"{r['achieved_gbs']:.0f} GB/s ({100 * r['achieved_gbs'] / info['peak_bandwidth_gbs']:.0f}% of peak) | "
              f"{r['recall_at_k']:.4f} |")
    print()
    print(f"Batches of {MAX_BATCH} queries (time per query):")
    print("| vectors | FAISS CPU | Found.it GPU | speedup |")
    print("|---|---|---|---|")
    for r in rows:
        print(f"| {r['n']:,} | {r['faiss_cpu_batch_ms_per_query']:.2f} ms | {r['gpu_batch_ms_per_query']:.2f} ms | "
              f"{r['faiss_cpu_batch_ms_per_query'] / r['gpu_batch_ms_per_query']:.1f}x |")

    Path(args.out).write_text(json.dumps({"info": info, "rows": rows}, indent=2))
    print(f"\nSaved {args.out}")


if __name__ == "__main__":
    main()
