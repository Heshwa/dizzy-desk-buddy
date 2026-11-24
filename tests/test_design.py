"""Regression checks for the real LCD, readable UI, and component clearance."""
from itertools import product, combinations
import math
import pytest
from PIL import Image, ImageChops
from dizzy import design as d
from dizzy.face import render_face, BACKGROUND, SAFE_RADIUS


def corners(component):
    return product(*[(c-s/2,c+s/2) for c,s in zip(component['center'],component['size'])])


@pytest.mark.parametrize('expression', ['blink','happy','sleepy','listening','speaking','alarm','heart','goodnight','music','idle'])
@pytest.mark.parametrize('mode', ['clock','music','listening','thinking','speaking','alarm'])
def test_lcd_content_stays_within_safe_circle(expression, mode):
    status={'expression':expression,'clock':'2026-11-18T23:59:59+05:30','playing':mode=='music','ringing':mode=='alarm','voice':mode if mode in ('listening','thinking','speaking') else 'idle'}
    for timestamp in (0,1.25,2.6):
        frame=render_face(status,timestamp)
        assert frame.size==(240,240)
        pixels=frame.convert('RGB').load()
        active=0
        for y in range(240):
            for x in range(240):
                if pixels[x,y]!=BACKGROUND[:3]:
                    active+=1
                    assert (x-119.5)**2+(y-119.5)**2<=SAFE_RADIUS**2
        assert active>100


def test_display_is_undistorted_and_recessed():
    assert d.DISPLAY_ACTIVE[0]/d.DISPLAY_ACTIVE[1] == pytest.approx(1)
    assert d.DISPLAY_FRONT_Y > d.HEAD_FRONT_Y
    pocket=d.HEAD_KEEPOUTS['display_pocket']['size']
    assert pocket[0]>=d.DISPLAY_BOARD[0]+2 and pocket[2]>=d.DISPLAY_BOARD[1]+2


def test_head_pockets_have_wall_clearance():
    for component in d.HEAD_KEEPOUTS.values():
        for point in corners(component):
            assert d.head_contains(point)


def test_component_planning_volumes_do_not_overlap():
    for group in (d.HEAD_KEEPOUTS,d.BODY_KEEPOUTS,d.BASE_KEEPOUTS):
        for a,b in combinations(group.values(),2):
            assert any(abs(x-y)>=(u+v)/2 for x,y,u,v in zip(a['center'],b['center'],a['size'],b['size']))


def test_base_components_fit_inside_wall():
    for component in d.BASE_KEEPOUTS.values():
        for x,y,z in corners(component):
            assert (x/(d.HIP_RADII[0]-d.WALL))**2+(y/(d.HIP_RADII[1]-d.WALL))**2+((z-d.HIP_CENTER_Z)/(d.HIP_RADII[2]-d.WALL))**2<1


def test_body_component_envelopes_fit_pear():
    rx,ry,rz=d.BODY_RADII
    for component in d.BODY_KEEPOUTS.values():
        for x,y,z in corners(component):
            relative=z-d.BODY_CENTER_Z
            scale=1-.22*relative/rz
            assert (x/((rx-d.WALL)*scale))**2+(y/((ry-d.WALL)*scale))**2+(relative/(rz-d.WALL))**2<1




def test_round_display_uv_mesh_is_physically_circular():
    from pathlib import Path
    vertices=[]
    for line in (Path(__file__).resolve().parents[1]/'assets/dizzy-round-display.obj').read_text().splitlines():
        if line.startswith('v '): vertices.append(tuple(map(float,line.split()[1:])))
    assert len(vertices)>100
    for x,y,z in vertices[1:]:
        assert math.hypot(x,y)==pytest.approx(d.DISPLAY_ACTIVE[0]/2000,abs=1e-8)
        assert z==0


def test_pin_allocation_is_unique_and_respects_esp32_capabilities():
    import json
    from pathlib import Path
    config=json.loads((Path(__file__).resolve().parents[1]/'hardware/pinmap.json').read_text())
    pins=list(config['pins'].values())
    assert len({p['gpio'] for p in pins})==len(pins)
    for pin in pins:
        assert pin['gpio'] not in (0,2,5,6,7,8,9,10,11,12,15)
        if pin['gpio']>=34:
            assert pin['direction']=='input' and pin['pullup_ohms']==10000
        if pin['direction']=='touch':
            assert pin['gpio'] in (4,13,14,27,32,33)


def test_complete_bom_includes_support_parts():
    import csv
    from pathlib import Path
    with (Path(__file__).resolve().parents[1]/'hardware/BOM.csv').open() as file:
        parts=list(csv.DictReader(file))
    ids=[p['ID'] for p in parts]
    assert len(ids)==len(set(ids))
    assert {'MCU','LCD','CAM','FLEX','SERVO','AMP','SPK','MIC','RTC','CELL','TOUCH','SW','PULLUP','LED','PSU','POWER','CAP1','CAP2','CAP3','WIRE','MECH','CASE','PROGRAM','HOST'}<=set(ids)


def test_webots_proto_has_balanced_nested_nodes():
    import re
    from pathlib import Path
    source=(Path(__file__).resolve().parents[1]/'protos/Dizzy.proto').read_text()
    source=re.sub(r'"[^"\n]*"|#[^\n]*','',source)
    stack=[]
    for token in re.findall(r'[\[\]{}]',source):
        if token in '[{':stack.append(token)
        else:assert stack.pop()=={']':'[','}':'{'}[token]
    assert not stack


def test_head_shell_contains_a_curved_ellipsoid_surface():
    from pathlib import Path
    count=0
    for line in (Path(__file__).resolve().parents[1]/'assets/dizzy-head-shell.obj').read_text().splitlines():
        if line.startswith('v '):
            p=tuple(float(n)*1000 for n in line.split()[1:])
            if abs(p[1]-d.HEAD_FRONT_Y)<.01 or abs(p[2]-d.HEAD_BOTTOM_Z)<.01:continue
            if abs(sum((x/(extent/2))**2 for x,extent in zip(p,d.HEAD_SIZE))-1)<1e-5:count+=1
    assert count>3000




def test_three_motor_power_allowances_fit_selected_supply():
    import json
    from pathlib import Path
    data=json.loads((Path(__file__).resolve().parents[1]/'hardware/power.json').read_text())
    assert sum(data['current_allowances_amps'].values())<data['required_negotiated_current']
    assert data['main_battery'] is False


def test_all_fixed_component_envelopes_clear_each_other_in_common_coordinates():
    parts={**d.BODY_KEEPOUTS,**d.BASE_KEEPOUTS}
    for (an,a),(bn,b) in combinations(parts.items(),2):
        assert any(abs(x-y)>=(u+v)/2 for x,y,u,v in zip(a['center'],b['center'],a['size'],b['size'])), (an,bn)


def test_actual_sculpted_arms_clear_head_body_hips_and_feet():
    import numpy as np
    from pathlib import Path
    vertices=[]
    for part in ('sleeve','cuff','palm'):
        filename=Path(__file__).resolve().parents[1]/f'assets/dizzy-right-{part}.obj'
        vertices += [list(map(lambda n:float(n)*1000,line.split()[1:])) for line in filename.read_text().splitlines() if line.startswith('v ')]
    vertices=np.unique(np.round(vertices,5),axis=0)
    x=vertices[:,0]+d.ARM_CENTER_X
    # Rotation around X preserves this lateral gap for every head yaw and arm pose.
    assert min(x)>max(d.HEAD_SIZE[:2])/2+2.5
    body_max_x=max(d.BODY_RADII[0]*(1-.22*math.cos(t))*math.sin(t) for t in np.linspace(0,math.pi,1001))
    assert min(x)>body_max_x+2.5
    assert min(x)>d.FOOT_CENTER[0]+d.FOOT_RADII[0]+2.5
    for degrees in range(121):
        angle=math.radians(degrees)
        local_z=vertices[:,2]+d.ARM_CENTER_Z-d.ARM_PIVOT_Z
        y=vertices[:,1]*math.cos(angle)+local_z*math.sin(angle)
        z=-vertices[:,1]*math.sin(angle)+local_z*math.cos(angle)+d.ARM_PIVOT_Z
        assert np.min(z)>2.5
        hip=(x/d.HIP_RADII[0])**2+(y/d.HIP_RADII[1])**2+((z-d.HIP_CENTER_Z)/d.HIP_RADII[2])**2
        assert np.min(hip)>1.05


def test_shoulder_servos_fit_their_pods_and_clear_other_boards():
    for component in d.SHOULDER_KEEPOUTS.values():
        cx,cy,cz=component['center']
        for x,y,z in corners(component):
            assert abs(x-cx)<=d.SHOULDER_LENGTH/2-d.WALL
            inset=4-math.sqrt(16-max(abs(x-cx)-16,0)**2)
            assert ((y-cy)/(d.SHOULDER_RADII[0]-inset-d.WALL))**2+((z-cz)/(d.SHOULDER_RADII[1]-inset-d.WALL))**2<=1
    parts={**d.BODY_KEEPOUTS,**d.BASE_KEEPOUTS,**d.SHOULDER_KEEPOUTS}
    for (an,a),(bn,b) in combinations(parts.items(),2):
        assert any(abs(x-y)>=(u+v)/2 for x,y,u,v in zip(a['center'],b['center'],a['size'],b['size'])),(an,bn)
    assert d.HEAD_CENTER_Z+d.HEAD_BOTTOM_Z >= d.ARM_PIVOT_Z+d.SHOULDER_RADII[1]+1.5


def test_compact_revision_preserves_real_component_envelope_sizes():
    assert d.HEAD_CENTER_Z+d.HEAD_SIZE[2]/2<210
    assert sorted(d.BASE_KEEPOUTS['esp32_board']['size'])==[12.,30.,58.]
    assert sorted(d.BASE_KEEPOUTS['pca9685_driver']['size'])==[14.,26.,64.]
    for component in d.SHOULDER_KEEPOUTS.values():
        assert sorted(component['size'])==[14.,34.,34.]


def test_sculpted_palms_are_closed_continuous_meshes():
    from pathlib import Path
    from collections import Counter, defaultdict
    for side in ('left','right'):
        filename=Path(__file__).resolve().parents[1]/f'assets/dizzy-{side}-palm.obj'
        vertices=[tuple(round(float(n),8) for n in line.split()[1:]) for line in filename.read_text().splitlines() if line.startswith('v ')]
        edges=Counter();adjacency=defaultdict(set)
        for i in range(0,len(vertices),3):
            for a,b in ((0,1),(1,2),(2,0)):
                x,y=vertices[i+a],vertices[i+b]
                edges[tuple(sorted((x,y)))]+=1
                adjacency[x].add(y);adjacency[y].add(x)
        assert set(edges.values())=={2}
        reached=set();todo=[vertices[0]]
        while todo:
            current=todo.pop()
            if current in reached:continue
            reached.add(current);todo.extend(adjacency[current]-reached)
        assert reached==set(vertices)



def test_world_saved_poses_cannot_displace_the_current_hand_roots():
    from pathlib import Path
    import re
    text=(Path(__file__).resolve().parents[1]/'worlds/dizzy.wbt').read_text()
    for index,sign in ((1,-1),(2,1)):
        for values in re.findall(rf'hidden translation_{index} ([^\n]+)',text):
            point=list(map(float,values.split()))
            assert point==pytest.approx([sign*d.ARM_CENTER_X/1000,0,d.ARM_CENTER_Z/1000],abs=.0001)


def test_idle_and_listening_do_not_blink_without_an_event():
    for expression in ('idle', 'listening', 'happy', 'heart'):
        status={'expression':expression,'clock':'2026-11-19T13:20:00+05:30','voice':expression if expression=='listening' else 'idle'}
        assert render_face(status,0).tobytes()==render_face(status,1).tobytes()
    status={'expression':'idle','clock':'2026-11-19T13:20:00+05:30'}
    normal=render_face(status,0)
    status['expression']='blink'
    assert normal.tobytes()!=render_face(status,0).tobytes()
