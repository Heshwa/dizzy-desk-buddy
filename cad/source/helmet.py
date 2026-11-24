"""Matching helmet shells and two curved, flush crown inlays."""
import math


def helmet_parts(cad):
    scale = cad.S
    center = (0, 0, 157 * scale)
    radii = tuple(value / 2 * scale for value in cad.D.HEAD_SIZE)
    front_plane = cad.D.HEAD_FRONT_Y * scale
    bottom_plane = (157 + cad.D.HEAD_BOTTOM_Z) * scale
    outer = cad.clip(cad.clip(cad.ellipsoid(radii, center), 1, front_plane, 100),
                     2, bottom_plane, 300)
    inner = cad.clip(cad.clip(cad.ellipsoid(tuple(radius - cad.WALL for radius in radii), center),
                              1, front_plane + cad.WALL, 100),
                     2, bottom_plane + cad.WALL, 300)
    skin = outer.cut(inner)
    shell = skin.cut(cad.cylinder(34.5 * scale, 12, (0, -30 * scale, center[2]), (0, 1, 0)))
    shell = shell.cut(cad.cylinder(14.4, 14, (0, 0, 110 * scale)))
    for sign in (-1, 1):
        shell = shell.cut(cad.box((18, 9, 10), (sign * 49 * scale, 0, center[2])))

    # Project an ellipse through the same curved top surface. A smaller opening
    # through the inner skin leaves a continuous seat under the removable pads.
    def crown_tool(extra):
        loop = cad.ellipse_wire(22.0 * scale + extra, 14.2 * scale + extra, center[2] + 32 * scale)
        return cad.Part.Face(loop).extrude(cad.V(0, 0, 23 * scale))

    seat_solid = cad.ellipsoid(tuple(radius - 1.5 for radius in radii), center)
    top_layer = outer.cut(seat_solid)
    inlay_blank = top_layer.common(crown_tool(0))
    panel_recess = top_layer.common(crown_tool(.28))
    inlays = {
        'Crown_inlay_L': cad.clip(inlay_blank, 0, -60, -.35),
        'Crown_inlay_R': cad.clip(inlay_blank, 0, .35, 60),
    }
    shell = shell.cut(panel_recess).cut(crown_tool(-1.55))

    split = 18 * scale
    front = cad.clip(shell, 1, -100, split - .15)
    rear = cad.clip(shell, 1, split + .15, 100)
    for x, z in [(-30, 155), (30, 155), (0, 188)]:
        x_mm, z_mm = x * scale, z * scale
        boss = cad.box((8, 9, 8), (x_mm, split, z_mm)).common(outer)
        if x:
            rib = cad.box((29, 9, 8), (math.copysign(43 * scale, x), split, z_mm))
        else:
            rib = cad.box((8, 9, 30), (0, split, 201 * scale))
        boss = boss.fuse(rib.common(outer))
        bore = cad.cylinder(1.7, 15, (x_mm, split - 8, z_mm), (0, 1, 0))
        nut = cad.Part.makePolygon([
            cad.V(x_mm + 3.2 * math.cos(i * math.tau / 6), split - 2,
                  z_mm + 3.2 * math.sin(i * math.tau / 6))
            for i in range(7)
        ])
        boss = boss.cut(bore).cut(cad.Part.Face(nut).extrude(cad.V(0, 2.6, 0)))
        front = front.fuse(cad.clip(boss, 1, -100, split - .15))
        rear = rear.fuse(cad.clip(boss, 1, split + .15, 100))
        rear = rear.cut(cad.cylinder(1.7, 70, (x_mm, split, z_mm), (0, 1, 0)))

    return {'Helmet_front': front, 'Helmet_rear': rear, **inlays}
