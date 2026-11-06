import bpy,json,hashlib,os
from pathlib import Path
R=Path(os.environ.get('ALMAZOV_WORKDIR','/workspace/ALMAZOV_LIGHT'));O=R/'model/v12'
def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));data={}
 for ob in bpy.context.scene.objects:
  if ob.type not in ['MESH','CURVE']:continue
  if ob.type=='MESH':geometry={'vertices':[tuple(v.co) for v in ob.data.vertices],'polygons':[(tuple(p.vertices),p.material_index) for p in ob.data.polygons]}
  else:geometry={'splines':[[tuple(p.co) for p in sp.points] for sp in ob.data.splines],'radius':ob.data.bevel_depth}
  geometry['matrix']=[tuple(row) for row in ob.matrix_world];geometry['materials']=[(m.name,tuple(m.diffuse_color)) for m in ob.data.materials]
  data[ob.name]=hashlib.sha256(json.dumps(geometry,sort_keys=True).encode()).hexdigest()
 return data
before=snapshot(R/'model/v11/Aloft_corrected_v11.blend');after=snapshot(O/'Aloft_corrected_v12.blend');report=json.loads((O/'geometry_validation.json').read_text());removed=report['removed_ground_partition'];assert set(before)-set(after)==set(removed);assert not(set(after)-set(before));assert all(before[n]==h for n,h in after.items())
report['all_retained_meshes_curves_transforms_and_diffuse_materials_identical']=True;report['retained_mesh_and_curve_objects_checked']=len(after);(O/'geometry_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
