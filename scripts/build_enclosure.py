"""Build the rounded shell and recessed LCD opening from measured dimensions."""
from pathlib import Path
import math
import sys

import numpy as np
from shapely import constrained_delaunay_triangles
from shapely.geometry import Point, box

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dizzy import design


class Mesh:
    def __init__(self):
        self.vertices = []
        self.normals = []
        self.faces = []

    def triangle(self, points, normals):
        points, normals = list(points), list(normals)
        cross=np.cross(points[1]-points[0],points[2]-points[0])
        if np.linalg.norm(cross)<1e-9: return
        if np.dot(cross,normals[0])<0:
            points.reverse();normals.reverse()
        indices = []
        for point, normal in zip(points, normals):
            indices.append(len(self.vertices) + 1)
            self.vertices.append(point)
            self.normals.append(normal)
        self.faces.append(indices)

    def plane(self, polygon, axis, coordinate, normal_sign):
        axes = [index for index in range(3) if index != axis]
        normal = np.zeros(3)
        normal[axis] = normal_sign
        for triangle in constrained_delaunay_triangles(polygon).geoms:
            points = []
            for u, v in list(triangle.exterior.coords)[:3]:
                point = np.zeros(3)
                point[axis] = coordinate
                point[axes] = (u, v)
                points.append(point)
            if np.dot(np.cross(points[1] - points[0], points[2] - points[0]), normal) < 0:
                points.reverse()
            self.triangle(points, [normal] * 3)

    def tunnel(self, polygon, axis, first, second, into_hole=True):
        axes = [index for index in range(3) if index != axis]
        coordinates = list(polygon.exterior.coords)
        for a, b in zip(coordinates, coordinates[1:]):
            points = []
            for uv, depth in ((a, first), (b, first), (b, second), (a, second)):
                point = np.zeros(3)
                point[axis] = depth
                point[axes] = uv
                points.append(point)
            normal = np.cross(points[1] - points[0], points[2] - points[0])
            normal /= np.linalg.norm(normal)
            midpoint = np.array([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2])
            toward_center = np.array(polygon.centroid.coords[0]) - midpoint
            if (np.dot(normal[axes], toward_center) > 0) != into_hole:
                points.reverse()
                normal *= -1
            self.triangle(points[:3], [normal] * 3)
            self.triangle([points[0], points[2], points[3]], [normal] * 3)

    def save(self, filename):
        lines = ['# Dizzy enclosure geometry, vertices in metres']
        lines += ['v ' + ' '.join(f'{coordinate / 1000:.9f}' for coordinate in point) for point in self.vertices]
        lines += ['vn ' + ' '.join(f'{coordinate:.8f}' for coordinate in normal) for normal in self.normals]
        lines += ['f ' + ' '.join(f'{index}//{index}' for index in face) for face in self.faces]
        (ROOT / 'assets' / filename).write_text('\n'.join(lines) + '\n')


def rounded_rectangle(width, height, radius, center=(0, 0)):
    polygon = box(-width / 2 + radius, -height / 2 + radius,
                  width / 2 - radius, height / 2 - radius).buffer(radius, quad_segs=12)
    from shapely.affinity import translate
    return translate(polygon, *center)


def ellipse_polygon(rx, ry):
    from shapely.affinity import scale
    return scale(Point(0, 0).buffer(1, quad_segs=64), rx, ry)


def ellipsoid_surface(mesh, radii, front, bottom, inward=False):
    rx, ry, rz = radii
    end = math.acos(front / ry)
    def point(theta, phi):
        return np.array([rx*math.sin(theta)*math.cos(phi), ry*math.cos(theta), rz*math.sin(theta)*math.sin(phi)])
    def clip(points):
        result=[]
        for a,b in zip(points, points[1:]+points[:1]):
            a_in,b_in=a[2]>=bottom,b[2]>=bottom
            if a_in: result.append(a)
            if a_in != b_in:
                result.append(a+(b-a)*((bottom-a[2])/(b[2]-a[2])))
        return result
    for ring in range(40):
        t0,t1=end*ring/40,end*(ring+1)/40
        for segment in range(96):
            p0,p1=2*math.pi*segment/96,2*math.pi*(segment+1)/96
            quad=[point(t0,p0),point(t1,p0),point(t1,p1),point(t0,p1)]
            triangles=[quad[:3]]
            if ring: triangles.append([quad[0],quad[2],quad[3]])
            for triangle in triangles:
                polygon=clip(triangle)
                for i in range(1,len(polygon)-1):
                    vertices=[polygon[0],polygon[i],polygon[i+1]]
                    normals=[]
                    for v in vertices:
                        n=v/np.square(radii);n/=np.linalg.norm(n)
                        normals.append(-n if inward else n)
                    if np.dot(np.cross(vertices[1]-vertices[0],vertices[2]-vertices[0]),normals[0])<0:
                        vertices.reverse();normals.reverse()
                    
                    if np.linalg.norm(np.cross(vertices[1]-vertices[0],vertices[2]-vertices[0])) > 1e-8:
                        mesh.triangle(vertices,normals)


def build_head():
    mesh=Mesh()
    outer=np.array(design.HEAD_SIZE)/2
    inner=outer-design.WALL
    front=design.HEAD_FRONT_Y
    bottom=design.HEAD_BOTTOM_Z
    ellipsoid_surface(mesh,outer,front,bottom)
    ellipsoid_surface(mesh,inner,front+design.WALL,bottom+design.WALL,inward=True)
    openings=[Point(0,design.DISPLAY_CENTER_Z).buffer(design.BEZEL_RADIUS,quad_segs=32),
              Point(design.CAMERA_CENTER[0],design.CAMERA_CENTER[2]).buffer(design.CAMERA_PORT_RADIUS,quad_segs=16),
              Point(design.LED_CENTER[0],design.LED_CENTER[2]).buffer(design.LED_PORT_RADIUS,quad_segs=12)]
    openings=[opening for i,opening in enumerate(openings) if not any(i!=j and other.contains(opening) for j,other in enumerate(openings))]
    for radii,depth,direction in ((outer,front,-1),(inner,front+design.WALL,1)):
        factor=math.sqrt(1-(depth/radii[1])**2)
        surface=ellipse_polygon(radii[0]*factor,radii[2]*factor)
        for opening in openings:
            assert surface.contains(opening), 'Front opening does not fit curved shell'
            surface=surface.difference(opening)
        mesh.plane(surface,1,depth,direction)
    for opening in openings:mesh.tunnel(opening,1,front,front+design.WALL)
    neck=Point(0,0).buffer(design.NECK_APERTURE,quad_segs=32)
    for radii,depth,direction in ((outer,bottom,-1),(inner,bottom+design.WALL,1)):
        factor=math.sqrt(1-(depth/radii[2])**2)
        surface=ellipse_polygon(radii[0]*factor,radii[1]*factor)
        assert surface.contains(neck), 'Neck aperture exceeds bottom cut'
        mesh.plane(surface.difference(neck),2,depth,direction)
    mesh.tunnel(neck,2,bottom,bottom+design.WALL)
    mesh.save('dizzy-head-shell.obj')


def build_crown_marks():
    mesh=Mesh()
    rx,ry,rz=np.array(design.HEAD_SIZE)/2
    def vertex(x,y):
        z=rz*math.sqrt(1-(x/rx)**2-(y/ry)**2)
        n=np.array([x/rx**2,y/ry**2,z/rz**2]);n/=np.linalg.norm(n)
        return np.array([x,y,z])+n*.025,n
    # A broad soft-touch crown pad with a fine centre seam, two electrodes below.
    for side in (-1,1):
        for ix in range(20):
            for iy in range(26):
                x0=side*(.6+ix*.95);x1=side*(.6+(ix+1)*.95)
                y0=-13+iy;y1=y0+1
                if max((x0/20)**2+(y0/13)**2,(x1/20)**2+(y1/13)**2)>1:continue
                pairs=[vertex(x0,y0),vertex(x1,y0),vertex(x1,y1),vertex(x0,y1)]
                for ids in ((0,1,2),(0,2,3)):
                    mesh.triangle([pairs[i][0] for i in ids],[pairs[i][1] for i in ids])
    mesh.save('dizzy-crown-marks.obj')


def build_bezel():
    mesh = Mesh()
    outer = Point(0, 0).buffer(design.BEZEL_RADIUS, quad_segs=32)
    opening = Point(0, 0).buffer(28.8, quad_segs=48)
    frame = outer.difference(opening)
    front = design.HEAD_FRONT_Y
    mesh.plane(frame, 1, front, -1)
    mesh.plane(frame, 1, front + 1, 1)
    mesh.tunnel(opening, 1, front, front + 1)
    mesh.tunnel(outer, 1, front, front + 1, into_hole=False)
    mesh.save('dizzy-bezel.obj')
    black=Mesh()
    glass=opening.difference(Point(0,0).buffer(design.DISPLAY_ACTIVE[0]/2+.12,quad_segs=48))
    for center,radius in ((design.CAMERA_CENTER,design.CAMERA_PORT_RADIUS),(design.LED_CENTER,design.LED_PORT_RADIUS)):
        glass=glass.difference(Point(center[0],center[2]).buffer(radius,quad_segs=24))
    black.plane(glass,1,front+.12,-1);black.save('dizzy-face-glass.obj')


def build_display():
    # Explicit circular geometry/UVs: square framebuffer corners are invisible.
    radius = design.DISPLAY_ACTIVE[0] / 2000
    segments = 192
    lines = ['# Circular LCD in local XY plane, texture origin at upper left', 'v 0 0 0', 'vt 0.5 0.5', 'vn 0 0 1']
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x, y = math.cos(angle), math.sin(angle)
        lines += [f'v {radius*x:.9f} {radius*y:.9f} 0', f'vt {0.5+0.5*x:.9f} {0.5+0.5*y:.9f}']
    for i in range(segments):
        a, b = i + 2, (i + 1) % segments + 2
        lines.append(f'f 1/1/1 {a}/{a}/1 {b}/{b}/1')
    (ROOT / 'assets/dizzy-round-display.obj').write_text('\n'.join(lines) + '\n')


def build_body():
    mesh = Mesh()
    radii = design.BODY_RADII
    def vertex(theta, phi):
        c = math.cos(theta)
        return np.array([radii[0] * (1 - .22 * c) * math.sin(theta) * math.cos(phi),
                         radii[1] * (1 - .22 * c) * math.sin(theta) * math.sin(phi), radii[2] * c])
    def normal(theta, phi):
        if theta < 1e-6: return np.array([0., 0., 1.])
        if theta > math.pi - 1e-6: return np.array([0., 0., -1.])
        a = vertex(theta + 1e-5, phi) - vertex(theta - 1e-5, phi)
        b = vertex(theta, phi + 1e-5) - vertex(theta, phi - 1e-5)
        n = np.cross(a, b)
        return n / np.linalg.norm(n)
    for ring in range(36):
        for segment in range(64):
            t0, t1 = math.pi * ring / 36, math.pi * (ring + 1) / 36
            p0, p1 = 2 * math.pi * segment / 64, 2 * math.pi * (segment + 1) / 64
            angles = [(t0, p0), (t1, p0), (t1, p1), (t0, p1)]
            points = [vertex(*pair) for pair in angles]
            normals = [normal(*pair) for pair in angles]
            if ring < 35: mesh.triangle(points[:3], normals[:3])
            if ring > 0: mesh.triangle([points[0], points[2], points[3]], [normals[0], normals[2], normals[3]])
    mesh.save('dizzy-body.obj')
    belt=Mesh()
    for face in mesh.faces:
        pts=[mesh.vertices[i-1] for i in face]
        if all(-20 < p[2] < -7 for p in pts):
            belt.triangle([p+mesh.normals[i-1]*.6 for p,i in zip(pts,face)],[mesh.normals[i-1] for i in face])
    belt.save('dizzy-waist.obj')


def build_seated():
    hip=Mesh()
    ellipsoid_surface(hip, design.HIP_RADII, -58, -28)
    hip.plane(ellipse_polygon(60*math.sqrt(1-(28/30)**2),58*math.sqrt(1-(28/30)**2)),2,-28,-1)
    hip.save('dizzy-hips.obj')
    foot=Mesh()
    ellipsoid_surface(foot,design.FOOT_RADII,-18,-28)
    foot.plane(ellipse_polygon(23*math.sqrt(1-(18/30)**2),30*math.sqrt(1-(18/30)**2)),1,-18,-1)
    foot.plane(ellipse_polygon(23*math.sqrt(1-(28/30)**2),30*math.sqrt(1-(28/30)**2)),2,-28,-1)
    foot.save('dizzy-foot.obj')
    sole=Mesh(); sole.plane(rounded_rectangle(30,42,10),1,-18.05,-1);sole.save('dizzy-sole.obj')
    # Curved chest inset and flush control patches follow the torso surface.
    def patch(filename, cx, cz, rx, rz):
        m=Mesh()
        def v(x,z): return np.array([x,design.body_front(x,z)-(.65 if filename=='dizzy-chest.obj' else .85),z]),np.array([0.,-1.,0.])
        for ring in range(8):
            for i in range(64):
                pts=[]
                for r,a in ((ring/8,i),( (ring+1)/8,i),((ring+1)/8,i+1),(ring/8,i+1)):
                    pts.append(v(cx+rx*r*math.copysign(abs(math.cos(a*math.tau/64))**.6,math.cos(a*math.tau/64)),cz+rz*r*math.copysign(abs(math.sin(a*math.tau/64))**.6,math.sin(a*math.tau/64)))[0])
                if ring:m.triangle(pts[:3],[np.array([0.,-1.,0.])]*3)
                m.triangle([pts[0],pts[2],pts[3]],[np.array([0.,-1.,0.])]*3)
        m.save(filename)
    patch('dizzy-chest.obj',0,84,23,18)
    patch('dizzy-talk.obj',0,94,8.5,3.)

    # Small control symbols sit on their flush caps, following the same curvature.
    glyph=Mesh()
    def rect(x,z,w,h):
        pts=[np.array([xx,design.body_front(xx,zz)-1.02,zz]) for xx,zz in [(x-w/2,z-h/2),(x+w/2,z-h/2),(x+w/2,z+h/2),(x-w/2,z+h/2)]]
        n=[np.array([0.,-1.,0.])]*3
        glyph.triangle(pts[:3],n);glyph.triangle([pts[0],pts[2],pts[3]],n)
    rect(0,94,1.5,2.4)
    glyph.save('dizzy-control-symbols.obj')
    grille=Mesh()
    def hip_hole(cx,cz,r):
        def v(x,z):
            y=-58*math.sqrt(1-(x/60)**2-((z-30)/30)**2)-.08
            return np.array([x,y,z])
        for i in range(24):
            angles=[i*math.tau/24,(i+1)*math.tau/24]
            grille.triangle([v(cx,cz)]+[v(cx+r*math.cos(a),cz+r*math.sin(a)) for a in angles],[np.array([0.,-1.,0.])]*3)
    for x in (-8,-4,0,4,8):
        for z in (38,40.5,43):hip_hole(x,z,.65)
    hip_hole(0,48,1)
    grille.save('dizzy-audio-ports.obj')


def build():
    from build_hands import build_hands
    build_hands(Mesh, ROOT)
    build_seated()
    build_head()
    build_bezel()
    build_display()
    build_crown_marks()
    build_body()
    port=Mesh()
    port.plane(rounded_rectangle(9.2,3.8,1.7,(0,30)),1,58.03,1)
    port.save('dizzy-usbc-port.obj')
    (ROOT / 'assets/dizzy-face.obj').unlink(missing_ok=True)


if __name__ == '__main__':
    build()
