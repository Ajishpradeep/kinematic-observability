"""Run synthetic controls or the local real-data adapter; emit aggregates only."""
import argparse
import csv
import hashlib
import json
import platform
import time
from pathlib import Path
import numpy as np
import torch
from geometry import fk, lengths, project, refine, metrics

METHODS=['raw','length_project','fk_prior','cartesian_reprojection','fk_reprojection','fk_soft','fk_hard']

def tensor(x): return torch.as_tensor(x,dtype=torch.float64)

def synthetic(seed,n=1024):
    rng=np.random.default_rng(seed)
    q=np.zeros((n,7)); q[:,:2]=rng.uniform(-.4,.4,(n,2)); q[:,2]=rng.uniform(2,4,n)
    q[:,3]=rng.uniform(-np.pi,np.pi,n); q[:,4]=rng.uniform(-1.2,1.2,n)
    q[:,5]=rng.uniform(-np.pi,np.pi,n); q[:,6]=rng.uniform(.05,2.6,n)
    lens=rng.uniform([.25,.22],[.36,.32],(n,2))
    truth=fk(tensor(q),tensor(lens))
    qp=q.copy(); qp[:,:3]+=rng.normal(0,.03,(n,3)); qp[:,3:6]+=rng.normal(0,.15,(n,3)); qp[:,6]+=rng.normal(0,.15,n)
    initial=fk(tensor(qp),tensor(lens))+tensor(rng.normal(0,.015,(n,3,3)))
    K=np.repeat(np.array([[[1200.,0,960],[0,1200,540],[0,0,1.]]]),n,0); dist=np.zeros((n,5))
    uv=project(truth,tensor(K),tensor(dist)).numpy()+rng.normal(0,3,(n,3,2))
    return dict(truth=truth.numpy(),initial=initial.numpy(),uv=uv,confidence=np.ones((n,3)),K=K,dist=dist,
                oracle_lengths=lens,generic_lengths=np.repeat([[.305,.27]],n,0),
                subject=np.full(n,f'seed{seed}'),cohort=np.full(n,'synthetic'),view=np.full(n,'random'))


def run_condition(data,condition,steps,batch):
    length_name,obs,cap=condition
    lens=data['generic_lengths'] if length_name=='generic' else data['oracle_lengths'].copy()
    if length_name=='oracle_minus10': lens=lens*.9
    if length_name=='oracle_plus10': lens=lens*1.1
    uv=data['uv'].copy()
    w=np.ones_like(data['confidence']) if obs=='uniform' else np.clip(data['confidence'],.05,1)
    if obs in ('proximal_missing','distal_wrong'): w[:,:2]=0
    if obs=='distal_wrong': uv[:,2,0]+=30; w[:,2]=1
    records=[]
    for method in METHODS:
        values={}; t=time.perf_counter()
        for start in range(0,len(lens),batch):
            sl=slice(start,start+batch)
            init,truth,L,U,W,K,D=[tensor(x[sl]) for x in (data['initial'],data['truth'],lens,uv,w,data['K'],data['dist'])]
            pred=refine(init,L,U,W,K,D,method,steps,cap)
            from geometry import bend
            measured=metrics(pred,truth,L,U,W,K,D)
            measured['cap_violation_fraction']=(bend(pred)>np.radians(cap)+1e-6).double()
            measured['near_cap_fraction']=(abs(bend(pred)-np.radians(cap))<np.radians(1)).double()
            for key,v in measured.items(): values.setdefault(key,[]).append(v.numpy())
        values={k:np.concatenate(v) for k,v in values.items()}
        for subject in np.unique(data['subject']):
            for view in ['all',*sorted(np.unique(data['view']))]:
                mask=data['subject']==subject
                if view!='all': mask&=data['view']==view
                if not mask.any(): continue
                row={'subject':str(subject),'cohort':str(data['cohort'][mask][0]),'view':str(view),
                     'lengths':length_name,'observations':obs,'cap_deg':cap,'method':method,'n':int(mask.sum()),
                     **{k:float(v[mask].mean()) for k,v in values.items()}}
                records.append(row)
        print(f'{length_name}/{obs}/{cap} {method}: {time.perf_counter()-t:.1f}s',flush=True)
    return records


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--steps',type=int,default=200)
    ap.add_argument('--batch',type=int,default=4096)
    ap.add_argument('--synthetic-n',type=int,default=1024)
    ap.add_argument('--smoke',action='store_true')
    args=ap.parse_args(); torch.set_num_threads(4)
    conditions=[('oracle','uniform',150),('oracle','weighted',150),('generic','weighted',150),
                ('oracle','proximal_missing',150),('generic','proximal_missing',150),
                ('oracle','distal_wrong',150),('oracle_minus10','weighted',150),
                ('oracle_plus10','weighted',150),('oracle','weighted',90)]
    if args.smoke: conditions=conditions[:1]
    records=[]
    datasets=[dict(np.load(args.data))] if args.data else [synthetic(seed,args.synthetic_n) for seed in (17,29,43)]
    for data in datasets:
        for condition in conditions: records+=run_condition(data,condition,args.steps,args.batch)
    args.out.mkdir(parents=True,exist_ok=True)
    with open(args.out/'aggregates.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0])); w.writeheader(); w.writerows(records)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path('PROTOCOL.md'),*sorted(Path('.').glob('*.py'))]}
    meta={'kind':'local_real' if args.data else 'synthetic','steps':args.steps,'batch':args.batch,
          'synthetic_n':args.synthetic_n,'seeds':None if args.data else [17,29,43],
          'python':platform.python_version(),'numpy':np.__version__,'torch':torch.__version__,
          'device':'cpu','dtype':'float64','threads':4,'source_sha256':hashes,
          'input_sha256':hashlib.sha256(args.data.read_bytes()).hexdigest() if args.data else None,
          'row_count':len(records),'conditions':conditions,'unix_time':time.time()}
    (args.out/'manifest.json').write_text(json.dumps(meta,indent=2))

if __name__=='__main__': main()
