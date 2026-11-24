"""Render CAD and exploded views with correct visibility between parts."""
import io
import json
import math
from pathlib import Path
import subprocess
import tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont

CAD=Path(__file__).resolve().parents[1]
data=json.loads((CAD/'preview-data.json').read_text())
scale=data['scale']
models=[p for p in data['parts'] if p['region']!='coupon']
font=ImageFont.load_default(size=34)
subtitle=ImageFont.load_default(size=18)
def exposed(p):
    return p['id'].startswith(('Helmet','Torso','Hip','Foot_','Chest','Waist','Face_','Crown',
                              'Forearm','Palm','Cuff','Shoulder_housing','Volume','Sole','Record'))
with tempfile.TemporaryDirectory() as tmp:
    tool=Path(tmp)/'raster'
    subprocess.run(['clang++','-O2','-std=c++17',str(CAD/'source/raster.cpp'),'-o',str(tool)],check=True)
    for view,(azimuth,elevation) in {
            'front':(-90,0),'side':(0,0),'rear':(90,0),'three-quarter':(-70,12),
            'exploded':(-68,15),'internals':(-67,17)}.items():
        angle=math.radians(azimuth)
        tilt=math.radians(elevation)
        eye=[math.cos(angle)*math.cos(tilt),math.sin(angle)*math.cos(tilt),math.sin(tilt)]
        entries=[]
        for p in models:
            if p['hardware'] and not p.get('visible_exterior',False) and view!='internals':
                continue
            if view=='internals' and not p['hardware'] and exposed(p):
                continue
            if view not in ('exploded','internals') and not (exposed(p) or p.get('visible_exterior',False) or p['id'].startswith(('Neck_hollow','Neck_retaining','Bottom_cover'))):
                continue
            offset=np.zeros(3)
            if view=='exploded':
                vector=np.array(p['center'])-np.array([0,0,100*scale])
                offset=vector/max(1,np.linalg.norm(vector))*38
            entries.append(' '.join(map(str,[*p['color'],*offset]))+'\n'+str(CAD/p['path']))
        runtime=' '.join(map(str,[1500,1500,5.0 if view=='exploded' else 5.9,
                                 *eye,0,0,110*scale,len(entries)]))
        raster=subprocess.run([str(tool)],input=(runtime+'\n'+'\n'.join(entries)+'\n').encode(),capture_output=True,check=True)
        frame=Image.open(io.BytesIO(raster.stdout)).resize((1050,1050),Image.Resampling.LANCZOS)
        draw=ImageDraw.Draw(frame)
        draw.text((34,24),'Dizzy / '+view.replace('-',' '),font=font,fill='#203a39')
        draw.text((35,69),'CAD prototype · component interfaces provisional',font=subtitle,fill='#426b62')
        frame.save(CAD/'reports'/(view+'.png'))
print('Rendered six CAD views with depth testing')
