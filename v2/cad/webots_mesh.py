"""Export CAD-derived shell meshes in metres for the separate Webots fit world."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from build import parts, pieces, OUT, V
import MeshPart

Origins={
    'body':(0,0,81),'yaw':(0,0,140),'pitch':(0,0,149),
    'left_arm':(0,69,110),'right_arm':(0,-69,110),
    'left_hip':(0,32,53),'right_hip':(0,-32,53),
    'left_ankle':(0,32,21),'right_ankle':(0,-32,21)}
visible=('Helmet_front','Helmet_rear','Face_bezel','Left_crown_cap','Right_crown_cap','Torso_front','Torso_back',
    'Chest_grille','Talk_button','Talk_guide','Expansion_blank','Battery_door','Neck_yaw_support','Rear_controls','Left_shoulder_support','Right_shoulder_support')
groups={}
for name,_,solid,color,_,link in pieces:
    if link not in Origins or (name not in visible and not any(b in name for b in ('sleeve','mitten','calf','sole','_foot','shoulder_cap'))):
        continue
    local=solid.copy()
    local.translate(-V(*Origins[link]))
    mesh=MeshPart.meshFromShape(Shape=local,LinearDeflection=.45,AngularDeflection=.50,Relative=False)
    points,facets=mesh.Topology
    path=OUT/'webots'/f'{name}.obj'
    with path.open('w') as stream:
        for point in points:
            stream.write(f'v {point.x/1000:.7f} {point.y/1000:.7f} {point.z/1000:.7f}\n')
        for face in facets:
            stream.write('f '+' '.join(str(int(i)+1) for i in face)+'\n')
    groups.setdefault(link,[]).append({'file':path.name,'color':list(color)})
(OUT/'webots'/'links.json').write_text(json.dumps(groups,indent=2))
