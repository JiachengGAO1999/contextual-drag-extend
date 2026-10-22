"""Read-only API probe for porting the selective worker across vLLM versions."""
from __future__ import annotations

import importlib.metadata
import inspect
import json


def signature(value: object) -> str:
    try:
        return str(inspect.signature(value))
    except (TypeError, ValueError):
        return "<unavailable>"


def main() -> None:
    report = {"vllm": importlib.metadata.version("vllm")}
    try:
        from vllm.v1.worker.gpu_model_runner import GPUModelRunner
        from vllm.v1.attention.backends.flex_attention import FlexAttentionMetadata
        from vllm.v1.attention.backends import flex_attention as flex_module

        report.update(
            {
                "imports": "passed",
                "GPUModelRunner._prepare_inputs": signature(GPUModelRunner._prepare_inputs),
                "FlexAttentionMetadata.get_mask_mod": signature(FlexAttentionMetadata.get_mask_mod),
                "FlexAttentionImpl.forward": signature(flex_module.FlexAttentionImpl.forward),
                "flex_attention_compiled": signature(flex_module.flex_attention_compiled)
                if hasattr(flex_module, "flex_attention_compiled") else None,
                "create_block_mask_compiled": signature(flex_module.create_block_mask_compiled)
                if hasattr(flex_module, "create_block_mask_compiled") else None,
                "get_kernel_options": signature(flex_module.get_kernel_options)
                if hasattr(flex_module, "get_kernel_options") else None,
                "metadata_annotations": sorted(getattr(FlexAttentionMetadata, "__annotations__", {})),
            }
        )
    except Exception as exc:
        report.update({"imports": "failed", "error": repr(exc)})
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
