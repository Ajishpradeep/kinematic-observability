"""Fail release on inconsistent or nonfinite aggregate results and changed run code."""
import csv
import hashlib
import json
from pathlib import Path
import math

for folder in ['synthetic','optitrack','optitrack_400','oracle_pixels']:
    root=Path('results')/folder
    rows=list(csv.DictReader((root/'aggregates.csv').open()))
    manifest=json.loads((root/'manifest.json').read_text())
    for name,expected in manifest['source_sha256'].items():
        actual=hashlib.sha256(Path(name).read_bytes()).hexdigest()
        assert actual==expected,(folder,name,'source changed since execution')
    for row in rows:
        for key in ['joint_mm','distal_mm','distal_depth_mm','bend_deg','reprojection_px','length_reference_mm','length_constraint_mm']:
            assert math.isfinite(float(row[key])) and float(row[key])>=0,(folder,row,key)
        if row['method'].startswith('fk') or row['method']=='length_project':
            assert float(row['length_constraint_mm'])<1e-6,(folder,'length guarantee failed')
        if row['method']=='fk_hard':
            assert float(row['cap_violation_fraction'])==0,(folder,'hard bound failed')
    n={}
    for row in rows:
        key=(row['subject'],row['view'])
        n.setdefault(key,int(row['n']))
        assert n[key]==int(row['n']),(folder,'unequal comparison rows')
    print(folder,len(rows),'aggregate rows: PASS')
