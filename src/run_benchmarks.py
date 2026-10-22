"""Three real inference repeats on the holdout; one development pass, no result reuse."""
from pathlib import Path
import argparse, subprocess, sys

root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--partition',choices=['dev','test','both'],default='both');args=p.parse_args()
for partition in (['dev','test'] if args.partition=='both' else [args.partition]):
    seeds=[17] if partition=='dev' else [17,23,41]
    for seed in seeds:
        for method in ['full_text','vector','dynamic_vector']:
            out=root/f'results/real/{method}-{partition}-seed{seed}.jsonl'
            subprocess.run([sys.executable,str(root/'benchmark.py'),'predict','--questions',str(root/f'data/eval/questions.{partition}.jsonl'),
                            '--method',method,'--seed',str(seed),'--out',str(out)],cwd=root,check=True)
