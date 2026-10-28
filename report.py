"""Generate tables and figures only from aggregate CSVs. No participant trajectories."""
import csv
from collections import defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LABELS={'raw':'Initial prediction','length_project':'Length projection','fk_prior':'FK + 3D tether',
        'cartesian_reprojection':'Cartesian + pixels','fk_reprojection':'FK + pixels',
        'fk_soft':'FK + soft cap + pixels','fk_hard':'FK + hard cap + pixels'}
COLORS=['#667085','#9a6700','#7c3aed','#0891b2','#14532d','#2563eb','#dc2626']

def read(path,cohort):
    return [r for r in csv.DictReader(path.open()) if r['view']=='all' and r['cohort']==cohort]

def group(rows):
    groups=defaultdict(list)
    for r in rows: groups[(r['lengths'],r['observations'],r['cap_deg'],r['method'])].append(r)
    return groups

def val(groups,key,metric):
    return float(np.mean([float(r[metric]) for r in groups[key]]))

def main():
    out=Path('results'); lines=['# Measured results','',
        'Real-data means weight each of the three evaluation participants equally. Synthetic means weight each of three seeds equally. Units and denominators are not pooled across these experiments.','']
    for kind,cohort in [('synthetic','synthetic'),('optitrack','new')]:
        rows=read(out/kind/'aggregates.csv',cohort); g=group(rows)
        lines += [f'## {kind}','', '| Lengths | Observations | Cap | Method | Wrist mm | Depth mm | Bend error ° | Reprojection px | Constraint deviation mm |',
                  '|---|---|---:|---|---:|---:|---:|---:|---:|']
        for key in g:
            metrics=['distal_mm','distal_depth_mm','bend_deg','reprojection_px','length_constraint_mm']
            values=[val(g,key,m) for m in metrics]
            lines.append(f'| {key[0]} | {key[1]} | {key[2]} | {LABELS[key[3]]} | '+ ' | '.join(f'{x:.3f}' for x in values)+' |')
        lines+=['','### Evaluation units','', '| Unit | Retained chains | Raw wrist mm | FK + pixels wrist mm | Hard 150° wrist mm |','|---|---:|---:|---:|---:|']
        for s in sorted({r['subject'] for r in rows}):
            rr={r['method']:r for r in rows if r['subject']==s and r['lengths']=='oracle' and r['observations']=='weighted' and r['cap_deg']=='150'}
            lines.append(f"| {s} | {rr['raw']['n']} | {float(rr['raw']['distal_mm']):.3f} | {float(rr['fk_reprojection']['distal_mm']):.3f} | {float(rr['fk_hard']['distal_mm']):.3f} |")
        fig,axes=plt.subplots(1,3,figsize=(13,4.5),layout='constrained')
        for ax,(obs,cap,title) in zip(axes,[('weighted','150','All observations · 150° cap'),('proximal_missing','150','Only distal observation · 150° cap'),('weighted','90','All observations · wrong 90° cap')]):
            for (method,label),color in zip(LABELS.items(),COLORS):
                key=('oracle',obs,cap,method)
                ax.scatter(val(g,key,'reprojection_px'),val(g,key,'distal_mm'),color=color,s=50,label=label)
            ax.set_title(title,fontsize=10); ax.set_xlabel('Reprojection error (px)'); ax.set_ylabel('Wrist 3D error (mm)')
            ax.grid(alpha=.18); ax.spines[['top','right']].set_visible(False)
        handles,labels=axes[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='outside lower center',ncol=4,frameon=False,fontsize=8)
        fig.suptitle(f'{kind}: small image residual does not establish small 3D error\nOracle lengths; '+('three participant means' if kind=='optitrack' else 'three seeded experiments'),fontsize=12)
        fig.savefig(out/kind/'accuracy-vs-fit.png',dpi=180)
        fig.savefig(out/kind/'accuracy-vs-fit.svg')
        plt.close(fig)
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__': main()
