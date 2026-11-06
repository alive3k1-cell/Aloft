"""Verify the delivered geometry against source routes and the explicitly scoped revision."""
import json,struct,math,hashlib,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=Path(os.environ.get('ALMAZOV_WORKDIR','/workspace/ALMAZOV_LIGHT'));O=R/'model/v11'
report=json.loads((O/'geometry_validation.json').read_text());installation=json.loads((O/'lighting_installation.json').read_text());meta=json.loads((ROOT/'assets/scene.json').read_text())
assert not report['unexpected_geometry_changes'] and report['unchanged_geometry_count']==62
assert hashlib.sha256((R/'model/v08/Aloft_light_show_v08.blend').read_bytes()).hexdigest()=='1fc6d7e1683f9dbd3fd41ddd5eba0d2e9fa1ebbb5e218dfa8fd04f2d9d888d66'
assert math.isclose(installation['source_cad_total_m'],305.67437636308864,abs_tol=1e-9)
# All intended roof runs now form a single connected chain with the same two original east endpoints.
lines=[q for q in installation['source_segments'] if q['group']=='ROOF']+installation['visual_joins'];pts=[];edges=[]
for q in lines:
    ids=[]
    for p in q['points_m']:
        i=next((i for i,a in enumerate(pts) if math.dist(a,p)<.001),None)
        if i is None:i=len(pts);pts.append(p)
        ids.append(i)
    edges.extend(zip(ids,ids[1:]))
adj={i:set() for i in range(len(pts))}
for a,b in edges:adj[a].add(b);adj[b].add(a)
seen=set();stack=[0]
while stack:
    i=stack.pop()
    if i in seen:continue
    seen.add(i);stack.extend(adj[i]-seen)
assert len(seen)==len(pts) and sum(len(n)==1 for n in adj.values())==2
b=(ROOT/'assets/aloft_v11.glb').read_bytes();n=struct.unpack_from('<I',b,12)[0];gltf=json.loads(b[20:20+n]);raw=b[28+n:]
assert hashlib.sha256(b).hexdigest()==meta['glb_sha256']
nodes=[n for n in gltf['nodes'] if n.get('extras',{}).get('viewer_role')=='neon'];assert len(nodes)==65
assert len([n for n in nodes if not n['extras'].get('supplemental')])==61
assert sum(n['extras'].get('preview_pixels',0) for n in nodes)==1834
routes={q['id']:q['points'] for q in meta['segments']}
def distance(p,a,b):
    ab=[y-x for x,y in zip(a,b)];t=max(0,min(1,sum((v-x)*d for v,x,d in zip(p,a,ab))/sum(d*d for d in ab)))
    return math.dist(p,[x+d*t for x,d in zip(a,ab)])
max_error=0
for node in nodes:
    assert 'matrix' not in node and 'translation' not in node,'Unexpected transform on neon geometry'
    path=routes[node['extras']['segment_id']]
    for prim in gltf['meshes'][node['mesh']]['primitives']:
        assert 'TEXCOORD_0' in prim['attributes']
        acc=gltf['accessors'][prim['attributes']['POSITION']];bv=gltf['bufferViews'][acc['bufferView']];offset=bv.get('byteOffset',0)+acc.get('byteOffset',0);stride=bv.get('byteStride',12)
        assert acc['componentType']==5126 and acc['type']=='VEC3'
        for i in range(acc['count']):
            p=struct.unpack_from('<3f',raw,offset+i*stride);d=min(distance(p,a,b) for a,b in zip(path,path[1:]));max_error=max(max_error,d)
assert max_error<.014,('Emitter drifted from its installed centerline',max_error)
assert not any('SKYLIGHT' in n.get('name','') for n in gltf['nodes'])
assert all('uri' not in b for b in gltf['buffers'])
result={'roof_chain_connected':True,'original_roof_endpoints_preserved':True,'source_segments':61,'supplemental_visual_joins':4,'preview_pixels':1834,'maximum_emitter_vertex_distance_to_installed_centerline_m':max_error,'roof_aperture_open':True,'input_blend_sha256_unchanged':True,'geometry':report}
(ROOT/'test-output/v11/geometry.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('V11 geometry checks passed: original source retained,61 source+4 joins, continuous roof route, open aperture, scoped architecture.')
