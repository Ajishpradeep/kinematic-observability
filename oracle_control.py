"""Post-pilot diagnostic: replace detected pixels with reference projections.

Privileged observations; this is not a deployable method or independent validation.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from geometry import project
from run import run_condition, tensor

def main():
    p=argparse.ArgumentParser(); p.add_argument('--data',type=Path,required=True)
    p.add_argument('--out',type=Path,default=Path('results/oracle_pixels')); a=p.parse_args()
    torch.set_num_threads(4); d=dict(np.load(a.data))
    d['uv']=project(tensor(d['truth']),tensor(d['K']),tensor(d['dist'])).numpy()
    d['confidence']=np.ones_like(d['confidence'])
    rows=run_condition(d,('oracle','uniform',150),400,4096)
    for r in rows: r['observations']='oracle_reference_pixels'
    a.out.mkdir(parents=True,exist_ok=True)
    with (a.out/'aggregates.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (a.out/'manifest.json').write_text(json.dumps({'steps':400,'input_sha256':hashlib.sha256(a.data.read_bytes()).hexdigest(),
        'purpose':'post-pilot diagnostic; reference-derived pixels, oracle lengths and reference pelvis translation',
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,['oracle_control.py','run.py','geometry.py'])}},indent=2))

if __name__=='__main__': main()
