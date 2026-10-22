"""Rerun every retrieval-based prediction after the whitespace split bug fix."""
from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parent
for partition,seeds in [('dev',[17]),('test',[17,23,41])]:
    for seed in seeds:
        for method in ['vector','dynamic_vector']:
            subprocess.run([sys.executable,str(root/'benchmark.py'),'predict','--questions',str(root/f'data/eval/questions.{partition}.jsonl'),
                            '--method',method,'--seed',str(seed),'--out',str(root/f'results/real/{method}-{partition}-seed{seed}.jsonl')],cwd=root,check=True)
subprocess.run([sys.executable,str(root/'benchmark.py'),'predict','--questions',str(root/'data/eval/questions.dynamic.jsonl'),
                '--method','dynamic_vector','--out',str(root/'results/real/dynamic_vector-diagnostic.jsonl')],cwd=root,check=True)
