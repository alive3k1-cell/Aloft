import json,struct,hashlib,os
from pathlib import Path
V=Path(__file__).resolve().parents[1];R=Path(os.environ.get('ALMAZOV_WORKDIR','/workspace/ALMAZOV_LIGHT'));O=R/'model/v12'
def read(path):
 b=path.read_bytes();n=struct.unpack_from('<I',b,12)[0];return json.loads(b[20:20+n]),b[28+n:]
def accessor(d,b,i):
 a=d['accessors'][i];v=d['bufferViews'][a['bufferView']];start=v.get('byteOffset',0)+a.get('byteOffset',0);width={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[a['componentType']]*{'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];stride=v.get('byteStride',width)
 return b''.join(b[start+k*stride:start+k*stride+width] for k in range(a['count']))
def geometry(d,b):
 out={}
 for m in d['meshes']:
  parts=[]
  for p in m['primitives']:
   q={key:hashlib.sha256(accessor(d,b,i)).hexdigest() for key,i in p['attributes'].items() if not key.startswith('_SPILL_')};q['indices']=hashlib.sha256(accessor(d,b,p['indices'])).hexdigest();q['material']=d['materials'][p['material']]['name'];parts.append(q)
  out[m['name']]=parts
 return out
old,ob=read(V/'assets/aloft_v11.glb');new,nb=read(V/'assets/aloft_v12.glb');a=geometry(old,ob);b=geometry(new,nb)
removed={'F01_GROUND_TERRACE_RAIL','F01_GROUND_TERRACE_RAIL_GLASS','F01_GROUND_TERRACE_END','F01_GROUND_TERRACE_END_GLASS'}
assert set(a)-set(b)==removed,(set(a)-set(b));assert not set(b)-set(a);assert all(a[n]==h for n,h in b.items()),[n for n,h in b.items() if a[n]!=h]
report=json.loads((O/'geometry_validation.json').read_text());assert report['all_retained_meshes_curves_transforms_and_diffuse_materials_identical']
spill=json.loads((O/'spill_validation.json').read_text());assert spill['blocked_rays']>0 and not spill['specular_proxy_contribution']
assert max(spill['probes_0_255']['pool_inner_floor'][:8])==0
assert max(spill['probes_0_255']['courtyard_rear_wall'][:8])==0
assert min(spill['probes_0_255']['upper_front_lit_surface'][4:8])==255
meta=json.loads((V/'assets/scene.json').read_text());assert meta['architecture_meshes']==90 and meta['source_segments']==61 and meta['visible_segments']==65 and meta['logical_pixels']==1834
assert meta['glb_sha256']==hashlib.sha256((V/'assets/aloft_v12.glb').read_bytes()).hexdigest()
solid=[m for m in new['materials'] if m['name'].startswith(('MAT_FACADE','MAT_ROOF','MAT_TERRACOTTA'))]
assert all(m.get('alphaMode','OPAQUE')=='OPAQUE' and m['pbrMetallicRoughness']['baseColorFactor'][3]==1 and 'KHR_materials_transmission' not in m.get('extensions',{}) for m in solid)
result={'retained_gltf_mesh_geometry_and_material_assignment_identical':len(b),'removed_meshes':sorted(removed),'solid_materials_opaque':True,'native':report,'spill':{k:v for k,v in spill.items() if k!='position_accessor_sha256'}}
(V/'test-output/v12/geometry.json').write_text(json.dumps(result,indent=2));print('V12 geometry/source/material/occlusion checks passed; retained meshes:',len(b))
