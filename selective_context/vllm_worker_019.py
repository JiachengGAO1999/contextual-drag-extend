"""Experimental selective worker for the isolated vLLM 0.19.1 path.

This deliberately does not replace :mod:`selective_context.vllm_worker`, whose
vLLM 0.11.0 implementation backs the frozen Qwen3-8B experiments.  The modern
port initially supports only packed decode; correctness must be revalidated on
each target architecture before scientific use.
"""
from contextvars import ContextVar
from functools import wraps
import importlib.metadata
import os
from pathlib import Path

import torch

from .vllm_mask import METADATA_KEY, NEVER, key_block_onsets


_RUNNER = ContextVar("selective_vllm_019_runner", default=None)


def install() -> None:
    if importlib.metadata.version("vllm") != "0.19.1":
        raise RuntimeError("Experimental selective worker requires exactly vLLM 0.19.1")
    if os.environ.get("SC_VLLM_DECODE_LAYOUT", "packed") != "packed":
        raise RuntimeError("vLLM 0.19.1 selective worker currently supports packed decode only")

    from vllm.v1.attention.backends import flex_attention as flex_module
    from vllm.v1.attention.backends.flex_attention import FlexAttentionMetadata
    from vllm.v1.worker.gpu_model_runner import GPUModelRunner

    if getattr(GPUModelRunner, "_selective_019_installed", False):
        return

    torch._dynamo.config.recompile_limit = int(os.environ.get("SC_FLEX_COMPILE_LIMIT", "64"))
    torch._dynamo.config.accumulated_recompile_limit = max(
        torch._dynamo.config.accumulated_recompile_limit,
        2 * torch._dynamo.config.recompile_limit,
    )
    if os.environ.get("SC_FLEX_NO_CUDAGRAPHS") == "1":
        flex_module.create_block_mask_compiled = torch.compile(
            flex_module.create_block_mask,
            fullgraph=True,
            dynamic=False,
            options={"triton.cudagraphs": False},
        )

    original_prepare = GPUModelRunner._prepare_inputs
    original_mask = FlexAttentionMetadata.get_mask_mod
    original_options = flex_module.get_kernel_options

    def kernel_options(*args, **kwargs):
        options = original_options(*args, **kwargs)
        # Conservative tile for custom index tensors and head dimensions up to
        # Gemma-4's 256. This changes tiling, never the logical mask edges.
        options.update(BLOCK_M=32, BLOCK_N=32)
        return options

    @wraps(original_prepare)
    def prepare(self, *args, **kwargs):
        marker = _RUNNER.set(self)
        try:
            return original_prepare(self, *args, **kwargs)
        finally:
            _RUNNER.reset(marker)

    @wraps(original_mask)
    def get_mask(self):
        base = original_mask(self)
        if not hasattr(self, "_selective_table"):
            runner = _RUNNER.get()
            if runner is None:
                raise RuntimeError("Selective metadata built outside request context")
            request_ids = tuple(runner.input_batch.req_ids)
            if len(request_ids) != self.num_reqs:
                raise RuntimeError("Unsupported microbatch mapping")
            cached = getattr(runner, "_selective_table_cache", None)
            if cached is None or cached[0] != request_ids:
                tables = []
                for request_id in request_ids:
                    state = runner.requests[request_id]
                    params = state.sampling_params
                    metadata = (params.extra_args or {}).get(METADATA_KEY)
                    if metadata is None:
                        raise RuntimeError("Request missing selective metadata")
                    if metadata["prompt_length"] != state.num_prompt_tokens:
                        raise RuntimeError("Prompt length mismatch")
                    tables.append(key_block_onsets(metadata))
                width = max(map(len, tables))
                cpu = torch.full((len(tables), width), NEVER, dtype=torch.int32)
                for index, row in enumerate(tables):
                    cpu[index, : len(row)] = torch.tensor(row, dtype=torch.int32)
                table = cpu.to(self.block_table.device)
                runner._selective_table_cache = (request_ids, table)
            self._selective_table = runner._selective_table_cache[1]
            marker = os.environ.get("SC_SELECTIVE_MASK_MARKER")
            if marker:
                Path(marker).touch(exist_ok=True)
            print("SELECTIVE_019_MASK_ACTIVE", flush=True)
        from .safe_flex_mask import make_safe_selective_mask

        return make_safe_selective_mask(self, base, self._selective_table, torch)

    flex_module.get_kernel_options = kernel_options
    GPUModelRunner._prepare_inputs = prepare
    FlexAttentionMetadata.get_mask_mod = get_mask
    GPUModelRunner._selective_019_installed = True


install()
from vllm.v1.worker.gpu_worker import Worker


class SelectiveWorker019(Worker):
    """Dedicated opt-in worker for the vLLM 0.19.1 compatibility branch."""

    pass
