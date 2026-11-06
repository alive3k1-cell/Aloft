"""Narrow V11 roof/terrace correction; all other architecture is retained."""
import json, math, os
from pathlib import Path
from collections import defaultdict
import numpy as np
from shapely.geometry import LineString, box
from shapely import constrained_delaunay_triangles
ROOT=Path(os.environ.get('ALMAZOV_WORKDIR','/workspace/ALMAZOV_LIGHT'))
OUT=ROOT/'model/v11';OUT.mkdir(parents=True,exist_ok=True)
objects=[]
def prism(name,shape,z0,z1,material):
    vs=[];fs=[]
    def face(ps):
        k=len(vs);vs.extend(ps);fs.append(list(range(k,k+len(ps))))
    for poly in (shape.geoms if hasattr(shape,'geoms') else [shape]):
        for t in constrained_delaunay_triangles(poly).geoms:
            q=list(t.exterior.coords)[:3]
            face([(x,y,z1) for x,y in q]);face([(x,y,z0) for x,y in q[::-1]])
        for ring in [poly.exterior]+list(poly.interiors):
            for (x,y),(u,v) in zip(ring.coords,list(ring.coords)[1:]):face([(x,y,z0),(u,v,z0),(u,v,z1),(x,y,z1)])
    objects.append(dict(name=name,verts=vs,faces=fs,material=material))
beams=defaultdict(lambda:[[],[]])
def beam(name,a,b,width,depth):
    a=np.array(a,float);b=np.array(b,float);v=(b-a)/np.linalg.norm(b-a)
    s=np.cross(v,[0,0,1] if abs(v[2])<.9 else [1,0,0]);s/=np.linalg.norm(s);t=np.cross(v,s)
    V,F=beams[name];k=len(V)
    for c in [a,b]:V.extend((c+s*width*i/2+t*depth*j/2).tolist() for i,j in [(-1,-1),(1,-1),(1,1),(-1,1)])
    F.extend([[k+i for i in f] for f in [[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]])
# Closed blades with mitered returns, rear supports set back behind the blades.
rear=[(9.6,15.70),(18.25,15.70),(18.25,13.56),(37.16,13.56),(37.16,-.48),(52.36,-.48)]
for name,points,zs in [('REAR',rear,[44.10+.27*i for i in range(8)]),('FRONT',[(19.05,31.47),(52.12,31.47)],[44.95+.225*i for i in range(6)])]:
    shape=LineString(points).buffer(.11,cap_style='flat',join_style='mitre')
    pieces=[]
    for i,z in enumerate(zs):
        prism('ROOF_LOUVRE_'+name+'_BLADE_'+str(i+1),shape,z-.075,z+.075,'ROOF_BLACK')
    for a,b in zip(points,points[1:]):
        a=np.array(a);b=np.array(b);d=b-a;n=np.array([-d[1],d[0]])/np.linalg.norm(d)
        if name=='FRONT':n=-n
        count=math.ceil(np.linalg.norm(d)/2.8)
        for i in range(count+1):
            p=a+d*i/count+n*.13
            beam('ROOF_LOUVRE_'+name+'_RECESSED_SUPPORTS',(*p,min(zs)-.075),(*p,46.50),.05,.05)
# Restore the upper gallery indicated in the latest front reference, keep ground level.
# Top datum follows the source second-floor windows at +5.25m; depths remain visual.
prism('F01_SECOND_FLOOR_TERRACE_SLAB',box(7.70,30.15,51.44,32.55),5.00,5.25,'MAT_FACADE_LIGHT_VISUAL_SAMPLE')
def railing(a,b):
    z=5.25;a=np.array(a,float);b=np.array(b,float);N=math.ceil(np.linalg.norm(b-a)/1.3)
    beam('F01_SECOND_FLOOR_TERRACE_RAIL',(*a,z+1.05),(*b,z+1.05),.035,.035)
    beam('F01_SECOND_FLOOR_TERRACE_RAIL',(*a,z+.12),(*b,z+.12),.022,.022)
    for i in range(N+1):
        p=a+(b-a)*i/N;beam('F01_SECOND_FLOOR_TERRACE_RAIL',(*p,z+.1),(*p,z+1.05),.035,.035)
    for i in range(N):
        p=a+(b-a)*(i+.025)/N;q=a+(b-a)*(i+.975)/N
        beam('F01_SECOND_FLOOR_TERRACE_GLASS',(*p,z+.57),(*q,z+.57),.012,.86)
for a,b in [((7.7,32.45),(51.44,32.45)),((7.7,30.15),(7.7,32.45)),((51.44,32.45),(51.44,30.15))]:railing(a,b)
# Slim supports sit on the existing entrance slab and meet the added terrace.
for x in [10.,19.,28.,37.]:beam('F01_SECOND_FLOOR_TERRACE_SUPPORTS',(x,32.2,0),(x,32.2,5.0),.09,.09)
for name,(V,F) in beams.items():
    mat='ROOF_BLACK' if name.startswith('ROOF') else ('MAT_RAIL_GLASS' if name.endswith('_GLASS') else 'MAT_ALUMINIUM_DARK')
    objects.append(dict(name=name,verts=V,faces=F,material=mat))
# Short visual joins only, source CAD lines and their quantities stay immutable.
joins=[('WEST_CORNER',[[-1.8,15.6],[-1.8,15.6492]]),('COURTYARD_STEP',[[18.03369999588,15.599992216],[18.14982563123,15.6],[18.14982563123,13.4499990713]]),('COURTYARD_CORNER',[[36.98452563123,13.4499990713],[37.04973797788,13.4499990713],[37.04973797788,13.44866097863]]),('EAST_CORNER',[[37.04973797788,-.55173902137],[37.04973797788,-.60000007261]])]
(OUT/'revision_geometry.json').write_text(json.dumps(dict(objects=objects,joins=joins),indent=2))
print('V11 detail meshes:',len(objects))
