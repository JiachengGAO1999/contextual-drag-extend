"""Opt-in, version-pinned vLLM worker. Does not modify installed package files.

Only V1, single GPU, eager engine and FlexAttention are supported initially.
Request identity is resolved after scheduling, from the live InputBatch.
"""
from contextvars import ContextVar
from functools import wraps
import importlib.metadata
import os
import torch
from .vllm_mask import METADATA_KEY, NEVER, key_block_onsets

_RUNNER = ContextVar('selective_vllm_runner', default=None)
_ATTENTION = ContextVar('selective_vllm_attention', default=None)


def install():
    if importlib.metadata.version('vllm') != '0.11.0':
        raise RuntimeError('Selective worker requires exactly vLLM 0.11.0')
    from vllm.v1.worker.gpu_model_runner import GPUModelRunner
    from vllm.v1.attention.backends.flex_attention import FlexAttentionMetadata
    from vllm.v1.attention.backends import flex_attention as flex_module
    if getattr(GPUModelRunner, '_selective_installed', False):return
    # Packed prefill and per-request decode share compiled functions across
    # bounded batch sizes (1..8). Torch's default eight variants is too small.
    # Keep a finite limit and fail visibly if unexpected variants exceed it.
    torch._dynamo.config.recompile_limit = int(os.environ.get('SC_FLEX_COMPILE_LIMIT', '64'))
    torch._dynamo.config.accumulated_recompile_limit = max(
        torch._dynamo.config.accumulated_recompile_limit,
        2 * torch._dynamo.config.recompile_limit)
    if os.environ.get('SC_FLEX_NO_CUDAGRAPHS') == '1':
        # vLLM enforce_eager does not disable upstream reduce-overhead mask capture.
        flex_module.create_block_mask_compiled = torch.compile(
            flex_module.create_block_mask, fullgraph=True, dynamic=False,
            options={'triton.cudagraphs': False})
    original_prepare = GPUModelRunner._prepare_inputs
    original_mask = FlexAttentionMetadata.get_mask_mod
    # Qwen3 head_dim=128 + custom index tensors exceeds A100 shared memory
    # with the upstream 64x64 tile. This changes kernel tiling, not mask edges.
    original_options = flex_module.get_kernel_options
    def kernel_options(*args, **kwargs):
        options=original_options(*args, **kwargs)
        options.update(BLOCK_M=32, BLOCK_N=32)
        return options
    flex_module.get_kernel_options=kernel_options
    if os.environ.get('SC_VLLM_DECODE_LAYOUT','packed')=='per_request':
        original_forward=flex_module.FlexAttentionImpl.forward
        compiled_flex=flex_module.flex_attention_compiled

        @wraps(original_forward)
        def forward(self, layer, query, key, value, kv_cache, attn_metadata, *args, **kwargs):
            marker=_ATTENTION.set(attn_metadata)
            try:return original_forward(self,layer,query,key,value,kv_cache,attn_metadata,*args,**kwargs)
            finally:_ATTENTION.reset(marker)

        def flex_per_request(query,key,value,score_mod,block_mask,scale,enable_gqa=False,kernel_options=None):
            meta=_ATTENTION.get()
            if meta is None or meta.num_actual_tokens!=meta.num_reqs or meta.max_query_len!=1:
                return compiled_flex(query,key,value,score_mod,block_mask,scale,enable_gqa=enable_gqa,kernel_options=kernel_options)
            if score_mod is not None:raise RuntimeError('Per-request decode score_mod unsupported')
            count=meta.num_reqs
            if not hasattr(meta,'_per_request_decode_mask'):
                original=meta.mask_mod
                starts=meta.query_start_loc
                def mask(b,h,q,k):
                    return (q==0)&original(torch.zeros_like(b),h,starts[b],k)
                meta._per_request_decode_mask=flex_module.create_block_mask_compiled(mask,count,None,1,key.shape[2],device=query.device,BLOCK_SIZE=(128,128))
            # KV batch expansion is a zero-stride view, not a cache copy.
            q=query[0].permute(1,0,2).unsqueeze(2)
            k=key.expand(count,-1,-1,-1);v=value.expand(count,-1,-1,-1)
            decode_options=dict(kernel_options or {})
            # Upstream forces the prefill kernel even for one-token queries.
            # Separate request batches permit Torch's split-KV decode kernel.
            decode_options['FORCE_USE_FLEX_ATTENTION']=False
            out=compiled_flex(q,k,v,None,meta._per_request_decode_mask,scale,enable_gqa=enable_gqa,kernel_options=decode_options)
            return out.squeeze(2).permute(1,0,2).unsqueeze(0)

        flex_module.FlexAttentionImpl.forward=forward
        flex_module.flex_attention_compiled=flex_per_request

    @wraps(original_prepare)
    def prepare(self, *args, **kwargs):
        marker = _RUNNER.set(self)
        try:return original_prepare(self, *args, **kwargs)
        finally:_RUNNER.reset(marker)

    @wraps(original_mask)
    def get_mask(self):
        base = original_mask(self)
        if not hasattr(self, '_selective_table'):
            runner = _RUNNER.get()
            if runner is None:
                # Only profiling metadata may be created without a live batch.
                raise RuntimeError('Selective metadata built outside request context')
            request_ids=tuple(runner.input_batch.req_ids)
            if len(request_ids)!=self.num_reqs:raise RuntimeError('Unsupported microbatch mapping')
            cached=getattr(runner,'_selective_table_cache',None)
            if cached is None or cached[0]!=request_ids:
                tables=[]
                for rid in request_ids:
                    state=runner.requests[rid]
                    params=state.sampling_params
                    meta=(params.extra_args or {}).get(METADATA_KEY)
                    if meta is None:raise RuntimeError('Request missing selective metadata')
                    if meta['prompt_length']!=state.num_prompt_tokens:raise RuntimeError('Prompt length mismatch')
                    tables.append(key_block_onsets(meta))
                width=max(map(len,tables))
                cpu=torch.full((len(tables),width),NEVER,dtype=torch.int32)
                for i,row in enumerate(tables):cpu[i,:len(row)]=torch.tensor(row,dtype=torch.int32)
                table=cpu.to(self.block_table.device)
                runner._selective_table_cache=(request_ids,table)
            self._selective_table=runner._selective_table_cache[1]
        table=self._selective_table
        from .safe_flex_mask import make_safe_selective_mask
        return make_safe_selective_mask(self, base, table, torch)

    GPUModelRunner._prepare_inputs=prepare
    FlexAttentionMetadata.get_mask_mod=get_mask
    GPUModelRunner._selective_installed=True


install()
from vllm.v1.worker.gpu_worker import Worker


class SelectiveWorker(Worker):
    """Dedicated worker selected via EngineArgs.worker_cls."""
    pass
