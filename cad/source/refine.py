"""Mechanical details applied to the generated FreeCAD assembly."""
import math


def switch_opening(b):
    bounds = b.component_shapes['master_switch'].BoundBox
    return b.box((bounds.XLength+.6,60,bounds.ZLength+.6),
                 (bounds.Center.x,49*b.S,bounds.Center.z))


def shoulder_lead_entry(b, sign):
    return b.cylinder(3.2,21,(sign*15,8,94*b.S),(sign,0,0))


def refine(b):
    """Add details whose interfaces are specified in the prototype manifest."""
    V = b.V
    S = b.S

    def replace(name, shape):
        shape = shape.removeSplitter()
        if shape.isNull() or not shape.isValid():
            raise ValueError('Invalid refinement for ' + name)
        b.doc.getObject(name).Shape = shape
        b.shapes[name] = shape
        for entry in b.printed:
            if entry['id'] == name:
                entry['shape'] = shape
                return
        raise KeyError(name)

    replace('Neck_bearing_seat',b.ring(14*S,12,6,(0,0,108.5*S)))

    # Match the reference pad footprint and touch plane exactly.
    for sign, side in [(-1,'L'),(1,'R')]:
        matrix=b.App.Matrix()
        matrix.A11=8*S
        matrix.A22=9*S
        matrix.A33=S
        pad=b.cylinder(1,2,(0,0,0)).transformGeometry(matrix)
        replace('Foot_pad_'+side,b.moved(pad,(sign*28*S,-60*S,0)))

    # Recessed chest capsule follows the same convex skin as the Webots control.
    capsule=[]
    for index in range(65):
        angle=index*math.tau/64
        x,z=math.cos(angle),math.sin(angle)
        capsule.append(V(8.5*S*math.copysign(abs(x)**.6,x),-60,
                         94*S+3*S*math.copysign(abs(z)**.6,z)))
    window=b.Part.Face(b.Part.makePolygon(capsule)).extrude(V(0,60,0))
    button=b.loft_body(-.85).cut(b.loft_body(1.7)).common(window)
    replace('Record_button',button)

    def disk(start_x, radius, length, z, sign):
        return b.cylinder(radius, length, (start_x,0,z),(sign,0,0))

    # Correct port alignment with the relocated master switch.
    hip=b.shapes['Hip_rear']
    replace('Hip_rear',hip.cut(switch_opening(b)))
    replace('LED_holder',b.shapes['LED_holder'].cut(b.component_shapes['camera_LED']))
    for entry in b.MAN['components']:
        name=entry['id']
        if name.startswith('decoupling_'):
            current=b.shapes['HW_'+name]
            shift=66.5*S-current.CenterOfMass.z
            placed=b.moved(current,(0,0,shift))
            b.doc.getObject('HW_'+name).Shape=placed
            b.shapes['HW_'+name]=b.component_shapes[name]=placed
            for model in b.hardware:
                if model['id']=='HW_'+name:model['shape']=placed
            entry['reference_center_mm'][2]=66.5
    strip=b.shapes['Passive_strip']
    replace('Passive_strip',b.moved(strip,(0,0,67.5*S-strip.BoundBox.Center.z)))
    # Add calibrated LCD board ledge to the circular-aperture test pieces.
    for gap in (.2,.3,.4):
        tag=str(gap).replace('.', 'p')
        aperture=b.box((57,51,4),(0,0,2)).cut(b.cylinder(16.2+gap,6,(0,0,-1)))
        replace('CAL_display_'+tag,aperture.cut(b.box((52+2*gap,46+2*gap,4),(0,0,4))))
    # Retain the reference ear-cap outline. A keyed stem operates the separate switch.
    for sign, side in [(-1,'L'),(1,'R')]:
        x=sign*50.5*S
        cap=disk(x-sign*2*S,14*S,4*S,157*S,sign)
        stem=b.box((4.8,6,6),(x-sign*3.3,0,157*S))
        replace('Volume_cap_'+side,cap.fuse(stem))
        # Shoulder loft sections use 24 mm in Y and 15 mm in Z.
        wires=[]
        for index in range(25):
            offset=-20+40*index/24
            arc=max(abs(offset)-16,0)
            inset=4-math.sqrt(max(0,16-arc*arc))
            w=b.ellipse_wire((15-inset)*S,(24-inset)*S,0)
            w.rotate(V(0,0,0),V(0,1,0),90)
            w.translate(V((sign*36+offset)*S,0,94*S))
            wires.append(w)
        blank=b.Part.makeLoft(wires,True,False)
        service=b.box((39,35.5,16.1),(sign*38*S,0,94*S))
        shaft=disk(sign*47*S,7.6,20,94*S,sign)
        # Fixed servo leads enter the pod on the inboard end, behind the
        # supported output axis. Keep the outer visible cover closed.
        cover=blank.cut(service.fuse(shaft).fuse(shoulder_lead_entry(b,sign)))
        replace('Shoulder_housing_'+side,cover)
        # Foot follows the reference ellipsoid up to the hidden join at the hip.
        foot=b.clip(b.clip(b.ellipsoid(tuple(a*S for a in b.D.FOOT_RADII),(sign*28*S,-60*S,30*S)),1,-78*S,-29*S),2,2*S,90)
        inner=b.ellipsoid(tuple(a*S-2.5 for a in b.D.FOOT_RADII),(sign*28*S,-60*S,30*S))
        hip=b.ellipsoid(tuple(a*S for a in b.D.HIP_RADII),(0,0,30*S))
        foot=foot.cut(inner).cut(hip)
        replace('Foot_'+side,foot)
        # Separate curved colour insert over the flattened sole.
        path=[]
        for n in range(65):
            a=math.tau*n/64
            x=math.cos(a);z=math.sin(a)
            path.append(V(sign*28*S+14*S*math.copysign(abs(x)**.7,x),-78*S-.4,
                          30*S+20*S*math.copysign(abs(z)**.7,z)))
        sole=b.Part.Face(b.Part.makePolygon(path)).extrude(V(0,1.1,0))
        if 'Sole_insert_'+side in b.shapes:
            replace('Sole_insert_'+side,sole)
        else:
            b.add('Sole_insert_'+side,sole,'fixed',(.66,.55,.45),
                  note='Accent insert. Flattened Webots sole orientation retained.')
        # Round palm and thumb follow the two original generating ellipsoids.
        # Smooth CAD surfaces replace the densely sampled test loft.
        palm_center=(sign*73*S,-10*S,49*S)
        palm=b.ellipsoid((10.5*S,10*S,12.5*S),palm_center)
        thumb=b.ellipsoid((5*S,6.5*S,8*S),(sign*65*S,-13.5*S,53.5*S))
        palm=palm.fuse(thumb)
        cavity=b.ellipsoid((7.5*S,7*S,9.5*S),palm_center)
        palm=palm.cut(cavity)
        palm=palm.cut(b.cylinder(1.7,6,(sign*73*S,-10*S,59*S)))
        replace('Palm_'+side,palm)

    # Recreate the curved chest outline, using the original superellipse and a
    # shallow thickening of the front surface.
    uv=[]
    for n in range(97):
        a=math.tau*n/96
        x=math.cos(a);z=math.sin(a)
        uv.append(V(23*S*math.copysign(abs(x)**.6,x),-75,84*S+18*S*math.copysign(abs(z)**.6,z)))
    window=b.Part.Face(b.Part.makePolygon(uv)).extrude(V(0,75,0))
    exterior=b.loft_body(-.65)
    interior=b.loft_body(1.0)
    chest=exterior.cut(interior).common(window)
    chest=chest.cut(b.box((18,20,6.6),(0,-34*S,94*S)))
    replace('Chest_inset',chest)
    replace('Torso_front',b.shapes['Torso_front'].cut(chest))
    # Only keep the accent outside the structural shell, with room for glue-free
    # fit samples at this prototype stage.
    waist=b.loft_body(-.6).cut(b.loft_body(0))
    waist=waist.common(b.box((150,150,13*S),(0,0,51*S)))
    waist=waist.cut(b.ellipsoid(tuple(a*S for a in b.D.HIP_RADII),(0,0,30*S)))
    replace('Waist_band',waist)
