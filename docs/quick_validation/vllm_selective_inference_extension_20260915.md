# vLLM selective-inference 扩展方向

## 决定

为支持后续扩大样本量，暂定将 vLLM 作为大规模实验执行器，保留当前 HF eager backend 作为精确 oracle 和小规模正确性审计器。

首个目标只支持当前 RQ 使用的 `late_block`，不让 `path_block` 阻塞架构优化。

## 目标语义

对每个请求保留原始 token、位置和完整 prompt。`late_block` 的 prefill 使用普通 causal attention；只有 generated query 不得访问指定的 token 区间 `[lo, hi)`。不能通过删除 token、placeholder、修改 KV 或 logits processor 近似替代。

## 暂定架构

1. 使用固定版本的 vLLM V1 offline engine 和 paged KV cache，不优先使用 HTTP server。
2. 通过请求 metadata 传递 `mode`、`prompt_len`、`mask_spans` 和后续的 `path_units`。
3. 在 vLLM FlexAttention 的 logical mask 层实现 per-request interval mask；必要时添加 block-sparsity hint。
4. R2 与 L_E_v1 使用同一个 vLLM engine 生成，保持 seed、sampling 和 scorer 协议一致。
5. `path_block` 后续再扩展为 query-dependent mask；其 prefill 状态不同，不能未经审计复用 R2 prefix cache。

## 验收门槛

- 3–5 个固定样本上完成 HF/vLLM parity smoke；先用 greedy 检查 token-level 行为，再检查原始采样设置下的 paired 统计行为。
- 验证 `late_block` 的 prompt token、mask 区间、首 token 语义、EOS、Thinking extraction 和 scorer 不发生协议变化。
- benchmark 1/2/4/8 并发请求的 prefill/decode 时间、tokens/s、显存和 prefix-cache 命中情况。
- 固定 vLLM commit、PyTorch、CUDA、模型路径和运行配置；未经 parity 不启用 FP8 KV 或 speculative decoding。

## 当前不做

- 不把任意 HF 4D `attention_mask` 直接传给 stock vLLM。
- 不把 attention mask 改写为 logits processor。
- 不先实现 `path_block`、结构控制或更多实验条件。
- 不在 vLLM parity 完成前用 vLLM/HF 混合结果作为正式主结果。

