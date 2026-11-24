"""Continuous forearm lofts and smoothly blended thumb/palm geometry, in mm."""
import math
import numpy as np

# Local coordinates relative to (side*66, 0, 79) at rest.
PROFILE=[(-20,5,9.5,10.5),(-17,5,10.4,11.3),(-5,3,10.,11.5),(5,1,9.5,11.),(13,0,8.,10.),(16,0,4.5,6.),(17,0,.01,.01)]
CUFF=[(-22,5,9.8,10.8),(-21,5,11.,12.),(-16,5,11.,12.),(-15,5,10.2,11.2)]


def build_hands(Mesh, root):
    def loft(profile,side):
        mesh=Mesh();rings=[]
        # Smooth interpolated radii: enough axial samples to avoid stacked beads.
        for i in range(len(profile)-1):
            p0=np.array(profile[max(0,i-1)],dtype=float)
            p1=np.array(profile[i],dtype=float);p2=np.array(profile[i+1],dtype=float)
            p3=np.array(profile[min(len(profile)-1,i+2)],dtype=float)
            for j in range(5):
                t=j/5
                p=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
                p[2:]=np.maximum(p[2:],.01);rings.append(p)
        rings.append(np.array(profile[-1]))
        def point(p,angle):
            z,cx,rx,ry=p
            return np.array([side*(cx+rx*math.cos(angle)),ry*math.sin(angle)-.2*(17-z),z])
        for i in range(len(rings)-1):
            for j in range(64):
                angles=[j*math.tau/64,(j+1)*math.tau/64]
                pts=[point(rings[k],a) for k,a in [(i,angles[0]),(i+1,angles[0]),(i+1,angles[1]),(i,angles[1])]]
                ns=[]
                for k,a in [(i,angles[0]),(i+1,angles[0]),(i+1,angles[1]),(i,angles[1])]:
                    tangent=point(rings[min(k+1,len(rings)-1)],a)-point(rings[max(0,k-1)],a)
                    around=np.array([-side*rings[k][2]*math.sin(a),rings[k][3]*math.cos(a),0])
                    n=np.cross(around,tangent)*side;n/=np.linalg.norm(n);ns.append(n)
                for ids in [(0,1,2),(0,2,3)]:mesh.triangle([pts[k] for k in ids],[ns[k] for k in ids])
        for ring,sign in [(rings[0],-1),(rings[-1],1)]:
            centre=np.array([side*ring[1],-.2*(17-ring[0]),ring[0]])
            for j in range(64):mesh.triangle([centre,point(ring,j*math.tau/64),point(ring,(j+1)*math.tau/64)],[np.array([0,0,sign])]*3)
        return mesh

    def sdf(points):
        p=np.asarray(points)
        a=(np.sqrt(np.sum((p/np.array([10.5,10.,12.5]))**2,axis=-1))-1)*10
        b=(np.sqrt(np.sum(((p-np.array([-8.,-3.5,4.5]))/np.array([5.,6.5,8.]))**2,axis=-1))-1)*5
        h=np.maximum(3-np.abs(a-b),0)/3
        return np.minimum(a,b)-h*h*3*.25
    def normal(p):
        delta=np.eye(3)*.01
        n=sdf(p+delta)-sdf(p-delta)
        return n/np.linalg.norm(n)
    xs=np.linspace(-15,12,32);ys=np.linspace(-13,12,30);zs=np.linspace(-14,15,34)
    grid=np.stack(np.meshgrid(xs,ys,zs,indexing='ij'),axis=-1);values=sdf(grid)
    offsets=[(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]
    tetrahedra=[(0,5,1,6),(0,1,2,6),(0,2,3,6),(0,3,7,6),(0,7,4,6),(0,4,5,6)]
    palms={-1:Mesh(),1:Mesh()}
    for i in range(len(xs)-1):
        for j in range(len(ys)-1):
            for k in range(len(zs)-1):
                indices=[(i+a,j+b,k+c) for a,b,c in offsets]
                vals=[values[index] for index in indices]
                if min(vals)>0 or max(vals)<0:continue
                pts=[grid[index] for index in indices]
                for tet in tetrahedra:
                    inside=[t for t in tet if vals[t]<=0];outside=[t for t in tet if vals[t]>0]
                    if not inside or not outside:continue
                    crossings=[pts[a]+(pts[b]-pts[a])*(-vals[a]/(vals[b]-vals[a])) for a in inside for b in outside]
                    centre=np.mean(crossings,axis=0);n=normal(centre)
                    u=crossings[0]-centre;u/=np.linalg.norm(u);v=np.cross(n,u)
                    crossings.sort(key=lambda p:math.atan2(np.dot(p-centre,v),np.dot(p-centre,u)))
                    for t in range(1,len(crossings)-1):
                        tri=[crossings[0],crossings[t],crossings[t+1]]
                        for side,mesh in palms.items():
                            points=[np.array([side*(p[0]+7),p[1]-10,p[2]-30]) for p in tri]
                            normals=[normal(p)*np.array([side,1,1]) for p in tri]
                            mesh.triangle(points,normals)
    for side,name in [(-1,'left'),(1,'right')]:
        loft(PROFILE,side).save('dizzy-'+name+'-sleeve.obj')
        loft(CUFF,side).save('dizzy-'+name+'-cuff.obj')
        palms[side].save('dizzy-'+name+'-palm.obj')

    marks=Mesh()
    for side in (-1,1):
        def v(x,z):return np.array([x,-24*math.sqrt(1-((z-94)/15)**2)-.04,z])
        for i in range(64):
            a,b=i*math.tau/64,(i+1)*math.tau/64
            pts=[v(side*50,94),v(side*50+5.5*math.cos(a),94+5.5*math.sin(a)),v(side*50+5.5*math.cos(b),94+5.5*math.sin(b))]
            marks.triangle(pts,[np.array([0.,-1.,0.])]*3)
    marks.save('dizzy-pod-marks.obj')
    # Filleted shoulder housings avoid the hard cut ends of primitive cylinders.
    pod=Mesh();profile=[]
    for x in np.linspace(-20,20,65):
        excess=max(abs(x)-16,0)
        inset=4-math.sqrt(max(0,16-excess*excess))
        profile.append((x,24-inset,15-inset))
    for i in range(len(profile)-1):
        for j in range(96):
            pts=[];normals=[]
            for k,a in [(i,j*math.tau/96),(i+1,j*math.tau/96),(i+1,(j+1)*math.tau/96),(i,(j+1)*math.tau/96)]:
                x,ry,rz=profile[k]
                pts.append(np.array([x,ry*math.cos(a),rz*math.sin(a)]))
                before=profile[max(k-1,0)];after=profile[min(k+1,len(profile)-1)]
                tangent=np.array([after[0]-before[0],(after[1]-before[1])*math.cos(a),(after[2]-before[2])*math.sin(a)])
                around=np.array([0,-ry*math.sin(a),rz*math.cos(a)])
                n=np.cross(around,tangent);n/=np.linalg.norm(n);normals.append(n)
            for ids in [(0,1,2),(0,2,3)]:pod.triangle([pts[k] for k in ids],[normals[k] for k in ids])
    for (x,ry,rz),sign in [(profile[0],-1),(profile[-1],1)]:
        for j in range(96):
            pts=[np.array([x,0,0])]+[np.array([x,ry*math.cos(a),rz*math.sin(a)]) for a in (j*math.tau/96,(j+1)*math.tau/96)]
            pod.triangle(pts,[np.array([sign,0,0])]*3)
    pod.save('dizzy-shoulder-housing.obj')
