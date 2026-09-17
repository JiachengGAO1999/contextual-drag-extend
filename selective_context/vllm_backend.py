"""Batched selective inference, deliberately separate from the HF oracle."""
import os
import time
from .hf_backend import GenerationResult
from .vllm_mask import request_metadata, METADATA_KEY


class SelectiveVLLMBackend:
    def __init__(self, model, *, max_model_len=32768, max_num_seqs=8,
                 gpu_memory_utilization=.65):
        os.environ['VLLM_ATTENTION_BACKEND']='FLEX_ATTENTION'
        os.environ['VLLM_USE_V1']='1'
        from vllm import LLM
        self.engine=LLM(model=model,tokenizer=model,dtype='bfloat16',
                        max_model_len=max_model_len,max_num_seqs=max_num_seqs,
                        gpu_memory_utilization=gpu_memory_utilization,
                        enable_prefix_caching=False,enable_chunked_prefill=True,
                        max_num_batched_tokens=max_model_len,enforce_eager=True,
                        generation_config='vllm',
                        worker_cls='selective_context.vllm_worker.SelectiveWorker',
                        disable_log_stats=False,seed=2027)
        self.tokenizer=self.engine.get_tokenizer()
        self.max_model_len=max_model_len

    def generate_batch(self,requests,*,max_new_tokens=1024,temperature=.6,top_p=.95,top_k=20,logprobs=None):
        from vllm import SamplingParams
        params=[]
        for req in requests:
            req.validate()
            budget=min(max_new_tokens,self.max_model_len-len(req.input_ids))
            if budget<1:raise ValueError('No generation budget')
            params.append(SamplingParams(temperature=temperature,top_p=top_p,top_k=top_k,
                seed=req.sample_seed,max_tokens=budget,skip_special_tokens=False,logprobs=logprobs,
                # HF oracle stops only at tokenizer EOS. Prevent model config
                # from silently adding other EOS IDs (e.g. Qwen endoftext).
                ignore_eos=True,stop_token_ids=[self.tokenizer.eos_token_id],
                extra_args={METADATA_KEY:request_metadata(req)}))
        t=time.monotonic()
        outputs=self.engine.generate([dict(prompt_token_ids=r.input_ids) for r in requests],params,use_tqdm=False)
        elapsed=time.monotonic()-t
        results=[]
        for req,out in zip(requests,outputs):
            assert list(out.prompt_token_ids)==req.input_ids
            g=out.outputs[0];tokens=list(g.token_ids)
            eos=self.tokenizer.eos_token_id
            reason='eos' if tokens and tokens[-1]==eos else g.finish_reason
            meta=dict(backend='vllm_selective_flex_0.11.0',access_mode=req.access_mode.value,
                     decode_layout=os.environ.get('SC_VLLM_DECODE_LAYOUT','packed'),
                     batch_seconds=elapsed,batch_size=len(requests),request=req.to_dict(),
                     sampling_rng='vllm; not bitwise HF compatible')
            if logprobs is not None:
                meta['logprobs']=[{str(k):v.logprob for k,v in step.items()} for step in g.logprobs]
            results.append(GenerationResult(tokens,self.tokenizer.decode(tokens,skip_special_tokens=False),reason,meta))
        return results
