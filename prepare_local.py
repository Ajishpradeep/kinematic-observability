"""Adapt the existing local cohort cache; never copy source code or release trajectories.

Run only on a trusted NPZ cache: the historical phase column uses pickle objects.
Output is private and ignored. The public runner consumes a documented generic NPZ schema.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cohort-root',type=Path,required=True)
    ap.add_argument('--out',type=Path,default=Path('local/cohort.npz'))
    ap.add_argument('--stride',type=int,default=5)
    args=ap.parse_args()
    if args.stride<1: raise ValueError('stride must be positive')
    source=args.cohort_root/'report/frames.npz'
    d=dict(np.load(source,allow_pickle=True))
    names=sorted(np.unique(d['subject']))
    identities={s:f'P{i+1:02d}' for i,s in enumerate(names)}
    # Equal-person development mean, not pooled-frame proportions.
    subject_lengths={}
    for s in names:
        g=d['gt_cam'][d['subject']==s]/1000
        subject_lengths[s]=np.stack([np.median(np.linalg.norm(np.diff(g[:,ids],axis=1),axis=-1),axis=0)
                                     for ids in ([0,2,4],[1,3,5])])
    dev=[s for s in names if np.any((d['subject']==s)&(d['cohort']=='within'))]
    generic=np.mean([subject_lengths[s] for s in dev],axis=0)
    rows={k:[] for k in ('truth','initial','uv','confidence','K','dist','oracle_lengths','generic_lengths','subject','cohort','view','capture','frame','side')}
    audits=[]; total=0; rejected=0
    for i,cap in enumerate(sorted(np.unique(d['capture']))):
        idx=np.flatnonzero(d['capture']==cap)[::args.stride]
        total+=len(idx)*2
        mask=d['is_swing'][idx]&~d['gt_glitch'][idx]&(d['swing_t'][idx]>=0)&(d['swing_t'][idx]<=3)&d['v2_ok'][idx]
        idx=idx[mask]
        if not len(idx): continue
        s=str(d['subject'][idx[0]])
        cache=args.cohort_root/s.lower()/(str(cap).split('/',1)[1]+'.npz')
        c=dict(np.load(cache))
        local=d['row'][idx]
        if not np.array_equal(c['frame'][local],d['frame'][idx]): raise ValueError('Frame alignment mismatch')
        absolute=c['gt_cam_mm'][local]/1000
        # The source detector ran on UNDISTORTED frames. Reapplying lens distortion
        # here would silently introduce a second geometric error.
        projected=absolute@c['K'].T
        projected=projected[...,:2]/projected[...,2:]
        if not np.allclose(projected,c['gt_2d'][local],atol=1e-5):
            raise ValueError('Cached reference is not in the expected undistorted pixel frame')
        pelvis=absolute[:,[6,7]].mean(1,keepdims=True)
        prediction=(d['gt_cam'][idx]+d['v2_d'][idx])/1000+pelvis
        # Explicit numerical convention check before using reference translation.
        if not np.allclose(absolute-pelvis,d['gt_cam'][idx]/1000,atol=1e-6): raise ValueError('Root/camera convention mismatch')
        for side,(core,il) in enumerate((([0,2,4],[6,8,10]),([1,3,5],[7,9,11]))):
            truth=absolute[:,core]; initial=prediction[:,core]
            uv=c['il24_kpt'][local][:,il]; conf=c['il24_conf'][local][:,il]
            ok=np.isfinite(truth).all((1,2))&np.isfinite(initial).all((1,2))&np.isfinite(uv).all((1,2))&np.isfinite(conf).all(1)
            ok&=(truth[...,2]>.1).all(1)&(initial[...,2]>.1).all(1)
            rejected+=int((~ok).sum()); n=int(ok.sum())
            values=dict(truth=truth[ok],initial=initial[ok],uv=uv[ok],confidence=conf[ok],
                        K=np.repeat(c['K'][None],n,0),dist=np.zeros((n,5)),
                        oracle_lengths=np.repeat(subject_lengths[s][side][None],n,0),
                        generic_lengths=np.repeat(generic[side][None],n,0),
                        subject=np.full(n,identities[s]),cohort=d['cohort'][idx][ok],view=d['view'][idx][ok],
                        capture=np.full(n,f'C{i:04d}'),frame=d['frame'][idx][ok],side=np.full(n,side))
            for k,v in values.items(): rows[k].append(v)
        audits.append({'capture':f'C{i:04d}','source':str(cache),'sha256':sha(cache)})
    out={k:np.concatenate(v) for k,v in rows.items()}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(args.out,**out)
    manifest={'input_sha256':sha(source),'source':str(source),'stride':args.stride,'eligible_before_filters':total,
              'retained_chains':len(out['truth']),'nonfinite_or_depth_rejections_after_swing_filter':rejected,
              'identity_map':identities,'captures':audits,'output_sha256':sha(args.out)}
    args.out.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({k:manifest[k] for k in ('stride','eligible_before_filters','retained_chains','output_sha256')}))

if __name__=='__main__': main()
