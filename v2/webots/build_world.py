"""Generate the Webots joint/contact rig in metres, with reference masses in kg."""
from pathlib import Path
import json
import sys
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
IVORY = '0.86 0.82 0.72'
CLAY = '0.69 0.30 0.21'
INK = '0.08 0.13 0.15'
MINT = '0.32 0.81 0.71'
CAD = '--cad' in sys.argv
meshes = json.loads((ROOT.parent/'cad/output/webots/links.json').read_text()) if CAD else {}

def visual(link, defaults):
    if link not in meshes:
        return defaults
    return [shape('Mesh { url [ "../../cad/output/webots/'+item['file']+'" ] }',
        ' '.join(map(str,item['color']))) for item in meshes[link]]

def shape(node, color, xyz='0 0 0', rotation='0 0 1 0'):
    return f'''Pose {{ translation {xyz} rotation {rotation}
      children [ Shape {{ appearance PBRAppearance {{ baseColor {color} roughness 0.67 metalness 0 }}
      geometry {node} }} ] }}'''

def ellipsoid(scale, color, xyz='0 0 0'):
    return f'Transform {{ translation {xyz} scale {scale} children [ {shape("Sphere { radius 1 subdivision 3 }",color)} ] }}'

def box(dimensions, color, xyz='0 0 0'):
    return shape('Box { size '+dimensions+' }',color,xyz)

def solid(name, xyz, mass, visuals, collision):
    return f'''Solid {{ name "{escape(name)}" translation {xyz} children [ {" ".join(visuals)} ]
     boundingObject {collision} physics Physics {{ density -1 mass {mass} }} }}'''

def joint(name, axis, anchor, travel, end, torque=0.12):
    return f'''HingeJoint {{
      jointParameters HingeJointParameters {{ axis {axis} anchor {anchor} minStop {travel[0]} maxStop {travel[1]} dampingConstant 0.012 }}
      device [
        RotationalMotor {{ name "{name}" maxVelocity 4 maxTorque {torque}
          minPosition {travel[0]} maxPosition {travel[1]} acceleration 15 }}
        PositionSensor {{ name "{name}_angle" }}
      ]
      endPoint {end}
    }}'''

def leg(side):
    side_sign = 1 if side == 'left' else -1
    hip_at = f'0 {side_sign*.032} -0.028'
    foot = solid(side+' foot','0 0 -0.032',.033,visual(side+'_ankle',[
        ellipsoid('.037 .026 .013',IVORY,'0.009 0 -0.009'),
        box('.072 .051 .007',INK,'0.009 0 -0.017'),
        ellipsoid('.022 .017 .009',CLAY,'0.027 0 -0.005')]),
        'Pose { translation 0.009 0 -0.012 children [ Box { size .072 .051 .017 } ] }')
    ankle = joint(side+'_ankle','1 0 0','0 0 -0.032',(-.44,.44),foot)
    shin = solid(side+' hip',hip_at,.036,[
        *visual(side+'_hip',[ellipsoid('.020 .021 .024',CLAY,'0 0 -0.015')]),ankle],
        'Pose { translation 0 0 -0.012 children [ Box { size .027 .032 .025 } ] }')
    return joint(side+'_hip','0 -1 0',hip_at,(-.53,.53),shin)

def arm(side):
    side_sign = 1 if side=='left' else -1
    anchor = f'0 {side_sign*0.069} 0.029'
    hand = ellipsoid('.022 .015 .018',IVORY,'0.003 0 -0.067')
    sleeve = ellipsoid('.020 .018 .029',CLAY,'0 0 -0.034')
    thumb = ellipsoid('.009 .008 .012',IVORY,'0.016 0 -0.054')
    arm_solid = solid(side+' arm',anchor,.016,visual(side+'_arm',[hand,sleeve,thumb]),
        'Pose { translation .003 0 -.044 children [ Box { size .034 .026 .074 } ] }')
    return joint(side+'_arm','0 -1 0',anchor,(0,1.5707963),arm_solid,.10)

def head():
    helmet = ellipsoid('.039 .050 .035',IVORY,'0 0 0.031')
    bezel = shape('Cylinder { radius .031 height .005 subdivision 48 }',CLAY,'0.033 0 0.029','0 1 0 1.5707963')
    visor = shape('Cylinder { radius .027 height .004 subdivision 48 }',INK,'0.036 0 0.029','0 1 0 1.5707963')
    eyes = [ellipsoid('.0016 .0048 .0065',MINT,f'0.039 {sign*.009} .032') for sign in (-1,1)]
    helm = solid('tilting helmet','0 0 .009',.052,[*visual('pitch',[helmet,bezel]),visor,*eyes],
        'Pose { translation 0 0 0.034 children [ Sphere { radius .031 } ] }')
    pitch = joint('pitch','0 -1 0','0 0 .009',(-.3490659,.4363323),helm,.11)
    carriage = solid('yaw carriage','0 0 .059',.009,[*visual('yaw',[ellipsoid('.021 .024 .012',CLAY)]),pitch],
        'Cylinder { radius .019 height .01 }')
    return joint('yaw','0 0 1','0 0 .059',(-.7853982,.7853982),carriage,.11)

def build():
    body=[*visual('body',[ellipsoid('.041 .048 .052',IVORY,'0 0 0.010'),
          ellipsoid('.007 .031 .030',CLAY,'0.039 0 .012'),
          ellipsoid('.004 .009 .009',INK,'0.046 0 0.019')]),head(),
          arm('left'),arm('right'),leg('left'),leg('right')]
    world = f'''#VRML_SIM R2025a utf8
WorldInfo {{
  title "Dizzy V2 floor gait"
  basicTimeStep 8
  contactProperties [ ContactProperties {{ material1 "default" material2 "default" coulombFriction [ 0.78 ] bounce 0 softCFM 0.0002 }} ]
}}
Viewpoint {{ orientation -0.239 -0.354 -0.904 2.10 position 0.57 0.43 0.29 fieldOfView 0.78 }}
Background {{ skyColor [ 0.09 0.14 0.18 ] }}
DirectionalLight {{ direction -0.7 -0.8 -1 intensity 1.6 }}
DirectionalLight {{ direction -0.4 1 -1 intensity 0.7 }}
Solid {{
  translation 0 0 -0.012
  children [ {box('1.4 1.4 .024','0.28 0.34 0.35')} ]
  boundingObject Box {{ size 1.4 1.4 .024 }}
}}
Robot {{
  translation 0 0 .081
  name "Dizzy V2 motion rig"
  supervisor TRUE
  controller "dizzy_v2"
  selfCollision TRUE
  children [ {" ".join(body)} ]
  boundingObject Pose {{ translation 0 0 .017 children [ Box {{ size .065 .075 .072 }} ] }}
  physics Physics {{ density -1 mass .157 centerOfMass [ 0 0 -0.014 ] }}
}}
'''
    (ROOT/'worlds'/('dizzy_v2_cad.wbt' if CAD else 'dizzy_v2.wbt')).write_text(world)

if __name__=='__main__':
    build()
