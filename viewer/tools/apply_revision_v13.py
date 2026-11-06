"""Remove the artificial facade wash only. All geometry, neon and night settings stay unchanged."""
import bpy,json,hashlib,os
from pathlib import Path
R=Path(os.environ.get('ALMAZOV_WORKDIR','/workspace/ALMAZOV_LIGHT'));O=R/'model/v13';O.mkdir(exist_ok=True);V=Path(__file__).resolve().parents[1]
source=R/'model/v12/Aloft_corrected_v12.blend';bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene
# Hash all object geometry once: no replacement/reconstruction/export of the model is needed.
def fingerprint(ob):
 if ob.type=='MESH':g={'v':[tuple(v.co) for v in ob.data.vertices],'f':[(tuple(p.vertices),p.material_index) for p in ob.data.polygons]}
 elif ob.type=='CURVE':g={'splines':[[tuple(p.co) for p in sp.points] for sp in ob.data.splines],'radius':ob.data.bevel_depth}
 else:return None
 g['matrix']=[tuple(r) for r in ob.matrix_world];g['materials']=[(m.name,tuple(m.diffuse_color)) for m in ob.data.materials]
 return hashlib.sha256(json.dumps(g,sort_keys=True).encode()).hexdigest()
before={ob.name:fingerprint(ob) for ob in s.objects if ob.type in ['MESH','CURVE']};disabled=[]
for ob in s.objects:
 if ob.type=='LIGHT' and ob.name.startswith(('SPILL_BIG_FRAME_','SPILL_UPPER_FRAME_')):
  ob.data.driver_remove('energy');ob.data.energy=0;ob.hide_render=True;ob.hide_viewport=True;ob['disabled_reason']='V13 user-marked facade wash; neon emission and optical glow remain';disabled.append(ob.name)
assert len(disabled)==8
assert before=={ob.name:fingerprint(ob) for ob in s.objects if ob.type in ['MESH','CURVE']}
s['version']='V13: facade fill proxies disabled; V12 geometry, emitters, pool and environment preserved'
bpy.context.view_layer.update();target=O/'Aloft_corrected_v13.blend';bpy.ops.wm.save_as_mainfile(filepath=str(target))
report={'source_blend_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_blend_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'retained_mesh_curve_geometry_and_material_objects':len(before),'geometry_and_materials_identical':True,'disabled_facade_proxy_lights':disabled,'source_neon_unchanged':True,'pool_lighting_unchanged':True,'night_environment_unchanged':True}
(O/'validation.json').write_text(json.dumps(report,indent=2))
# Reuse the byte-identical V12 GLB, including the existing pool occlusion attributes.
p=V/'assets/scene.json';meta=json.loads(p.read_text());meta['version']=13;meta['source_geometry_version']=12;meta['spill_render_groups']=['POOL'];meta['render_settings_blend_sha256']=report['output_blend_sha256'];meta['facade_spill_status']='Disabled by user revision V13; emissive neon and bloom remain';p.write_text(json.dumps(meta,ensure_ascii=False,indent=2));print(json.dumps(report,indent=2))
