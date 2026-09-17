"""Tmux resident engine; reuse it for frozen-manifest experiments without reload."""
import code
import os


def main():
    os.environ.setdefault('SC_VLLM_DECODE_LAYOUT', 'per_request')
    from selective_context.vllm_backend import SelectiveVLLMBackend
    from selective_context.phase0.vllm_run import main as run
    backend = SelectiveVLLMBackend('/data2/huangrj/models/qwen3-8b', max_num_seqs=8)

    def run_manifest(manifest, output, batch_size=8):
        return run(['--manifest', str(manifest), '--output', str(output),
                    '--batch-size', str(batch_size)], backend=backend)

    print('SELECTIVE_VLLM_RESIDENT_READY', flush=True)
    code.interact(banner='Use run_manifest(manifest, new_output, batch_size=8). '
                 'backend is also available. No experiment starts automatically.',
                 local={'backend': backend, 'run_manifest': run_manifest})


if __name__ == '__main__':
    main()
