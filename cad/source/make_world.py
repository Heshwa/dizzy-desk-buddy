"""Write a geometry inspection world, with a measured articulation exercise."""
import math
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
CAD = ROOT / 'cad'
data = json.loads((CAD / 'preview-data.json').read_text())
scale = data['scale']
parts = [part for part in data['parts'] if part['region']!='coupon' and (not part['hardware'] or part.get('visible_exterior',False))]
scene = CAD / 'simulation'
scene.mkdir(exist_ok=True)

def shape(part):
    color = ' '.join(map(str, part['color']))
    name = part['id']
    return f'''  Shape {{
    appearance PBRAppearance {{ baseColor {color} roughness 0.57 metalness 0 }}
    geometry Mesh {{ url [ "../output/webots/{name}.obj" ] }}
  }}'''

def move_group(region, label, pivot):
    anchor = ' '.join(str(coordinate * scale / 1000) for coordinate in pivot)
    return f'''DEF {label} Pose {{
  translation {anchor}
  children [
    Pose {{
      translation {' '.join(str(-float(coordinate)) for coordinate in anchor.split())}
      children [
{chr(10).join(shape(part) for part in parts if part['region']==region)}
      ]
    }}
  ]
}}'''

angle = math.atan2(.06, .40)
camera = f'''
Viewpoint {{
  fieldOfView 0.66
  position 0.058 -0.40 0.21
  orientation 0.987 0.023 0.159 1.309
}}'''
world = f'''#VRML_SIM R2025a utf8
WorldInfo {{ title "Dizzy CAD joint and exterior review" basicTimeStep 32 }}
{camera}
Background {{ skyColor [ 0.27 0.32 0.31 ] }}
DirectionalLight {{ direction 0.3 1 -2 intensity 2 }}
DirectionalLight {{ direction -1 1 -0.5 intensity 0.7 }}
Solid {{
  translation 0 0 -0.004
  children [ Shape {{
    appearance PBRAppearance {{ baseColor 0.43 0.37 0.30 roughness 0.8 metalness 0 }}
    geometry Box {{ size 0.65 0.65 0.008 }}
  }} ]
}}
Group {{
 children [
{chr(10).join(shape(part) for part in parts if part['region']=='fixed')}
 ]
}}
{move_group('head','HEAD',(0,0,109.5))}
{move_group('L','LEFT',( -56,0,94))}
{move_group('R','RIGHT',(56,0,94))}
Robot {{
  name "CAD articulation review"
  controller "cad_pose_review"
  supervisor TRUE
}}
'''
# Webots uses a project-level worlds/controllers structure.
worlds = scene / 'worlds'
worlds.mkdir(exist_ok=True)
(worlds / 'dizzy-cad.wbt').write_text(world.replace('../output/','../../output/'))
controllers = scene / 'controllers' / 'cad_pose_review'
controllers.mkdir(parents=True, exist_ok=True)
(controllers / 'cad_pose_review.py').write_text('''"""Inspect exported CAD at rest and at all commanded joint extremes."""
import math
import os
from pathlib import Path
from controller import Supervisor

robot = Supervisor()
head = robot.getFromDef('HEAD').getField('rotation')
left = robot.getFromDef('LEFT').getField('rotation')
right = robot.getFromDef('RIGHT').getField('rotation')
poses = [(0,0,0), (-45,0,120), (45,120,0), (-45,120,120), (45,120,120), (0,0,0)]
test = os.environ.get('DIZZY_CAD_TEST') == '1'
for yaw, l, r in poses:
    head.setSFRotation([0,0,1,math.radians(yaw)])
    left.setSFRotation([-1,0,0,math.radians(l)])
    right.setSFRotation([-1,0,0,math.radians(r)])
    for step in range(2 if test else 28):
        if robot.step(32) == -1:
            raise SystemExit(0)
    for field, angle in ((head,yaw),(left,l),(right,r)):
        assert abs(field.getSFRotation()[3]-math.radians(angle)) < 1e-6
print('CAD_POSES_OK', len(poses), flush=True)
if test:
    result = os.environ.get('DIZZY_CAD_TEST_REPORT')
    if result:
        Path(result).write_text('CAD_POSES_OK '+str(len(poses))+'\\n')
    robot.simulationQuit(0)
''')
