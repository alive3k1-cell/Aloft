"""Bake view-independent area-fill visibility; append attributes without changing geometry."""
import bpy,json,struct,math,hashlib,os,time
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
R=Path(os.environ.get('ALMAZOV_WORKDIR','/workspace/ALMAZOV_LIGHT'));V=Path(__file__).resolve().parents[1];A=V/'assets'
bpy.ops.wm.open_mainfile(filepath=str(R/'model/v12/Aloft_corrected_v12.blend'))
vertices=[];faces=[]
for ob in bpy.data.collections['ALMAZOV_ARCHITECTURE_V07'].objects:
 if ob.type!='MESH':continue
 start=len(vertices);vertices.extend(ob.matrix_world@v.co for v in ob.data.vertices)
 for p in ob.data.polygons:
  mat=ob.data.materials[p.material_index]
  if mat and mat.name=='MAT_RAIL_GLASS':continue
  faces.append([start+i for i in p.vertices])
bvh=BVHTree.FromPolygons(vertices,faces)
def native(v):return Vector((v[0],-v[2],v[1]))
meta=json.loads((A/'scene.json').read_text());lights=[]
for q in meta['spill']:
 center=native(q['position']);axis=native(q['xAxis']);lights.append((native(q['direction']),[center+axis*q['width']*f for f in [-.45,-.225,0,.225,.45]]))
path=A/'aloft_v12.glb';blob=path.read_bytes();jsonsize=struct.unpack_from('<I',blob,12)[0];gltf=json.loads(blob[20:20+jsonsize]);binary=bytearray(blob[28+jsonsize:]);original_positions={}
assert not any('_SPILL_VIS0' in p['attributes'] for m in gltf['meshes'] for p in m['primitives']), 'Export a fresh GLB before baking visibility'
placements={}
def walk(i,parent,role=None,instanced=False):
 node=gltf['nodes'][i];extra=node.get('extras',{});role=extra.get('viewer_role',role)
 if 'matrix' in node:local=Matrix([node['matrix'][k:k+4] for k in range(0,16,4)]).transposed()
 else:
  q=node.get('rotation',[0,0,0,1]);local=Matrix.Translation(Vector(node.get('translation',[0,0,0])))@Quaternion((q[3],*q[:3])).to_matrix().to_4x4()@Matrix.Diagonal((*node.get('scale',[1,1,1]),1))
 matrix=parent@local;instanced=instanced or 'EXT_mesh_gpu_instancing' in node.get('extensions',{})
 if 'mesh' in node and role=='architecture':placements[node['mesh']]=(matrix,instanced)
 for child in node.get('children',[]):walk(child,matrix,role,instanced)
for i in gltf['scenes'][gltf.get('scene',0)]['nodes']:walk(i,Matrix.Identity(4))
cache={};blocked=0;ray_count=0;began=time.time()
def visibility(p):
 global blocked,ray_count
 key=tuple(round(v,5) for v in p)
 if key in cache:return cache[key]
 values=[]
 for direction,samples in lights:
  vis=0.;total=0.
  for source in samples:
   delta=source-p;d=delta.length
   if d<.008:vis+=1;total+=1;continue
   if (p-source).dot(direction)<-.001:continue
   unit=delta/d;w=1/(d*d+.01);ray_count+=1
   hit=bvh.ray_cast(p+unit*.003,unit,max(0,d-.006))[0]
   if hit is None:vis+=w
   else:blocked+=1
   total+=w
  values.append(round(255*vis/total) if total else 0)
 values.append(0);cache[key]=values;return values
count=0
for mi,(matrix,instanced) in placements.items():
 for primitive in gltf['meshes'][mi]['primitives']:
  ai=primitive['attributes']['POSITION'];acc=gltf['accessors'][ai];bv=gltf['bufferViews'][acc['bufferView']];offset=bv.get('byteOffset',0)+acc.get('byteOffset',0);stride=bv.get('byteStride',12);assert acc['componentType']==5126
  xyz=[struct.unpack_from('<3f',binary,offset+i*stride) for i in range(acc['count'])];original_positions[ai]=hashlib.sha256(b''.join(struct.pack('<3f',*p) for p in xyz)).hexdigest()
  # Shared instanced signs retain their own emission/environment reflections; facade fill is excluded.
  values=[[0]*12 for _ in xyz] if instanced else [visibility(native(matrix@Vector(p))) for p in xyz]
  for j in range(3):
   while len(binary)%4:binary.append(0)
   offset=len(binary);data=bytes(v for row in values for v in row[j*4:j*4+4]);binary.extend(data)
   bvi=len(gltf['bufferViews']);gltf['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(data),'target':34962})
   ai=len(gltf['accessors']);gltf['accessors'].append({'bufferView':bvi,'componentType':5121,'count':len(values),'type':'VEC4','normalized':True});primitive['attributes']['_SPILL_VIS'+str(j)]=ai
  count+=len(values)
 print('Occlusion mesh',mi,'vertices',count,'cached points',len(cache),flush=True)
# Diagnostic: front facade sources must be blocked from the courtyard terrace's inner floor.
probes={}
for name,p in [('pool_inner_floor',[3,23,40.35]),('courtyard_rear_wall',[15,15.59,35]),('upper_front_lit_surface',[11.75,31.66,40])]:probes[name]=visibility(Vector(p))[:11]
assert max(probes['pool_inner_floor'][:8])==0,probes
assert max(probes['courtyard_rear_wall'][:8])==0,probes
assert max(probes['upper_front_lit_surface'][4:8])>0,probes
while len(binary)%4:binary.append(0)
gltf['buffers'][0]['byteLength']=len(binary);encoded=json.dumps(gltf,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
path.write_bytes(struct.pack('<III',0x46546c67,2,12+8+len(encoded)+8+len(binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
report={'method':'static_visibility_5_samples_per_strip','proxy_count':len(lights),'specular_proxy_contribution':False,'architecture_vertices':count,'cached_receiver_points':len(cache),'ray_count':ray_count,'blocked_rays':blocked,'probes_0_255':probes,'position_accessor_sha256':original_positions,'seconds':round(time.time()-began,2),'geometry_positions_indices_materials_unchanged':True,'limits':'Static opaque-architecture visibility, five weighted samples per strip, interpolated at vertices; illustrative fill, not a photometric calculation.'}
meta['spill_occlusion']={k:v for k,v in report.items() if k not in ['position_accessor_sha256','probes_0_255']};meta['glb_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();(A/'scene.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2));(R/'model/v12/spill_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='position_accessor_sha256'},indent=2))
