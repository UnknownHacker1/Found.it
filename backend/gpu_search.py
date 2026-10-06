"""
GPU search for Found.it.

Found.it ranks files with an exact inner-product search over normalized sentence
embeddings (faiss.IndexFlatIP). FAISS has no GPU build for Windows, so this module
runs the same search on an NVIDIA GPU with a small CUDA C++ kernel. CuPy compiles
the kernel at runtime with NVRTC, so users only need the normal NVIDIA driver, not
the CUDA toolkit.

The search is limited by memory, not math: every query has to read the whole
vector table once. So the table lives on the GPU in fp16, which halves the bytes
read, and one pass over memory scores a whole batch of queries. Products are still
added up in fp32.
"""

import warnings

import numpy as np

# CuPy finds the pip-installed CUDA pieces on its own; it just warns that CUDA_PATH isn't set
warnings.filterwarnings("ignore", message="CUDA path could not be detected")

try:
    import cupy as cp
    import torch

    _IMPORTS_OK = True
except Exception:  # CuPy or a CUDA build of PyTorch is missing
    _IMPORTS_OK = False

MAX_BATCH = 8  # queries scored together in one pass over the table
_GROUP = 16  # lanes that share one row (two rows per warp)
_BLOCK = 256  # threads per block

_KERNEL_SOURCE = r"""
#include <cuda_fp16.h>

#define MAX_BATCH 8
#define GROUP 16

// Scores every row of an fp16 table against a batch of fp32 queries.
// Each half-warp (16 lanes) owns one row. A lane reads 16 bytes (8 fp16 values)
// at a time, so the 16 lanes cover 256 contiguous bytes per load and the reads
// stay fully coalesced. The queries sit in shared memory, so each row is read
// from global memory once no matter how many queries are in the batch.
extern "C" __global__ void ip_scores_fp16(const uint4* __restrict__ table,
                                          const float* __restrict__ queries,
                                          float* __restrict__ scores,
                                          int n_rows,
                                          int chunks,
                                          int n_queries)
{
  extern __shared__ float q[];
  const int dim = chunks * 8;
  for (int i = threadIdx.x; i < n_queries * dim; i += blockDim.x)
  {
    q[i] = queries[i];
  }
  __syncthreads();

  const int warp_lane = threadIdx.x & 31;
  const int half      = warp_lane / GROUP;
  const int lane      = warp_lane % GROUP;
  const int warp_id   = (blockIdx.x * blockDim.x + threadIdx.x) >> 5;
  const int n_warps   = (gridDim.x * blockDim.x) >> 5;

  // The loop bound is the same for the whole warp, so every lane reaches the shuffles below.
  for (int base = warp_id * 2; base < n_rows; base += n_warps * 2)
  {
    const int row    = base + half;
    const bool valid = row < n_rows;

    float acc[MAX_BATCH];
#pragma unroll
    for (int j = 0; j < MAX_BATCH; ++j)
    {
      acc[j] = 0.0f;
    }

    if (valid)
    {
      const uint4* r = table + (size_t) row * chunks;
      for (int c = lane; c < chunks; c += GROUP)
      {
        const uint4 v    = __ldg(r + c);
        const __half2* h = reinterpret_cast<const __half2*>(&v);
        const float2 a   = __half22float2(h[0]);
        const float2 b   = __half22float2(h[1]);
        const float2 e   = __half22float2(h[2]);
        const float2 f   = __half22float2(h[3]);
#pragma unroll
        for (int j = 0; j < MAX_BATCH; ++j)
        {
          if (j < n_queries)
          {
            const float* qj = q + j * dim + c * 8;
            acc[j] += a.x * qj[0] + a.y * qj[1] + b.x * qj[2] + b.y * qj[3] + e.x * qj[4] + e.y * qj[5]
                    + f.x * qj[6] + f.y * qj[7];
          }
        }
      }
    }

#pragma unroll
    for (int j = 0; j < MAX_BATCH; ++j)
    {
      if (j < n_queries)
      {
        float s = acc[j];
#pragma unroll
        for (int offset = GROUP / 2; offset > 0; offset >>= 1)
        {
          s += __shfl_down_sync(0xffffffffu, s, offset, GROUP);
        }
        if (valid && lane == 0)
        {
          scores[(size_t) j * n_rows + row] = s;
        }
      }
    }
  }
}
"""

_kernel = None


def _get_kernel():
    global _kernel
    if _kernel is None:
        _kernel = cp.RawKernel(_KERNEL_SOURCE, "ip_scores_fp16", options=("--std=c++17",))
    return _kernel


def gpu_available() -> bool:
    """True if there is a CUDA GPU and the kernel compiles on it."""
    if not _IMPORTS_OK:
        return False
    try:
        if cp.cuda.runtime.getDeviceCount() < 1 or not torch.cuda.is_available():
            return False
        _get_kernel().compile()
        return True
    except Exception:
        return False


class GpuFlatIP:
    """Exact inner-product search on the GPU. Same search() as faiss.IndexFlatIP."""

    def __init__(self, embeddings: np.ndarray):
        x = np.ascontiguousarray(embeddings, dtype=np.float32)
        if x.ndim != 2:
            raise ValueError("embeddings must be a 2-D array")
        n, d = x.shape
        if d % 8 != 0:
            raise ValueError("embedding size must be a multiple of 8")
        self.ntotal = n
        self.d = d
        self._chunks = d // 8
        # fp16 copy of the table on the GPU, viewed as 16-byte chunks for the kernel
        self._table = cp.asarray(x.astype(np.float16))
        self._table_u4 = self._table.view(cp.uint32).reshape(n, self._chunks, 4)
        props = cp.cuda.runtime.getDeviceProperties(cp.cuda.Device().id)
        self.device_name = props["name"].decode() if isinstance(props["name"], bytes) else str(props["name"])
        sms = props["multiProcessorCount"]
        rows_per_block = (_BLOCK // 32) * 2
        self._grid = int(max(1, min(-(-n // rows_per_block), sms * 32)))
        self._kernel = _get_kernel()

    def scores(self, queries) -> "cp.ndarray":
        """Raw scores on the GPU, shape (n_queries, ntotal). Up to MAX_BATCH queries."""
        q = cp.ascontiguousarray(cp.asarray(queries, dtype=cp.float32).reshape(-1, self.d))
        n_queries = q.shape[0]
        if n_queries > MAX_BATCH:
            raise ValueError(f"at most {MAX_BATCH} queries per call")
        out = cp.empty((n_queries, self.ntotal), dtype=cp.float32)
        self._kernel(
            (self._grid,),
            (_BLOCK,),
            (self._table_u4, q, out, np.int32(self.ntotal), np.int32(self._chunks), np.int32(n_queries)),
            shared_mem=n_queries * self.d * 4,
        )
        return out

    def search(self, queries, k: int):
        """Top k by inner product. Returns (scores, ids) as numpy arrays, like FAISS."""
        q = np.ascontiguousarray(queries, dtype=np.float32).reshape(-1, self.d)
        k = int(min(k, self.ntotal))
        if k <= 0 or self.ntotal == 0:
            empty = np.zeros((len(q), 0))
            return empty.astype(np.float32), empty.astype(np.int64)
        all_scores, all_ids = [], []
        for start in range(0, len(q), MAX_BATCH):
            s = self.scores(q[start : start + MAX_BATCH])
            top = torch.topk(torch.as_tensor(s, device="cuda"), k, dim=1)
            all_scores.append(top.values.cpu().numpy())
            all_ids.append(top.indices.cpu().numpy())
        return np.vstack(all_scores), np.vstack(all_ids).astype(np.int64)
