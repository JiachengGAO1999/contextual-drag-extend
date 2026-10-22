"""Synthetic exact-edge regression including rounded tiles and shrinking batches."""
import torch
from types import SimpleNamespace
from selective_context.safe_flex_mask import make_safe_selective_mask

def main():
    device='cuda'
    from torch.nn.attention.flex_attention import create_block_mask
    total=0
    for count in [8,5,3,1]:
        for length in [127,129,32767]:
            docs=torch.arange(count,device=device)
            table=torch.full((count,32),2**30,device=device,dtype=torch.int32)
            table[:,4:12]=length-2
            meta=SimpleNamespace(doc_ids=docs,total_cache_tokens=length)
            def convert(lookup,q,k):
                rid=lookup[q]
                return k>=0,torch.zeros_like(rid)+length-1,k
            meta._convert_physical_to_logical=convert
            def base(b,h,q,k):return k<length
            safe=make_safe_selective_mask(meta,base,table,torch)
            q=torch.arange(count+128,device=device)[:,None]
            k=torch.arange(length+128,device=device)[None,:]
            expected=(q<count)&(k<length)&~((k>=4)&(k<12))
            assert torch.equal(safe(0,0,q,k),expected)
            # Demonstrate the old unguarded lookup has an out-of-range domain.
            try: torch.arange(count)[torch.tensor(count)]
            except IndexError: pass
            else: raise AssertionError('Expected old padding lookup to fail')
            mask=create_block_mask(safe,None,None,count,length,device=device,BLOCK_SIZE=(128,128),_compile=True)
            torch.cuda.synchronize()
            total+=1
    print(f'SAFE_FLEX_GPU_PASS {total} shapes; exact edges and padded indices',flush=True)

if __name__=='__main__':main()
