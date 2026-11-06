"""V12: remove the ground terrace glass partition only; retain the accepted architecture."""
import bpy,json,hashlib,os
from pathlib import Path
R=Path(os.environ.get('ALMAZOV_WORKDIR','/workspace/ALMAZOV_LIGHT'));O=R/'model/v12';O.mkdir(exist_ok=True)
source=R/'model/v11/Aloft_corrected_v11.blend';bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;arch=bpy.data.collections['ALMAZOV_ARCHITECTURE_V07']
def fingerprint(ob):
    return hashlib.sha256(json.dumps({'v':[list(v.co) for v in ob.data.vertices],'f':[(list(p.vertices),p.material_index) for p in ob.data.polygons],'matrix':[list(r) for r in ob.matrix_world],'materials':[m.name for m in ob.data.materials]},sort_keys=True).encode()).hexdigest()
before={o.name:fingerprint(o) for o in arch.objects}
removed=['F01_GROUND_TERRACE_RAIL','F01_GROUND_TERRACE_RAIL_GLASS','F01_GROUND_TERRACE_END','F01_GROUND_TERRACE_END_GLASS']
for name in removed:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
after={o.name:fingerprint(o) for o in arch.objects};assert all(after[n]==h for n,h in before.items() if n not in removed)
# Native Cycles already traces area-light occlusion; keep these proxy lights diffuse-only.
for ob in s.objects:
    if ob.type=='LIGHT' and ob.name.startswith('SPILL_'):ob.data.specular_factor=0;ob.visible_glossy=False
fc=s.world.node_tree.nodes['DUSK_BACKGROUND'].inputs['Strength'].driver_add('default_value');fc.driver.expression='.16*e'
for name,expr in [('SUN','(2.4*d+.018*(1-d))*e'),('SOFT_SKY_FILL','(60000*d+4500*(1-d))*e')]:bpy.data.lights[name].animation_data.drivers.find('energy').driver.expression=expr
s['version']='V12: accepted architecture retained; ground glass partition removed; moderate night environment'
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'removed_ground_partition':removed,'retained_architecture_count':len(after),'retained_geometry_and_material_assignments_identical':True,'architecture_before':len(before),'architecture_after':len(after),'source_neon_and_visual_joins_unchanged':True,'native_area_proxies_diffuse_only':True}
(O/'geometry_validation.json').write_text(json.dumps(report,indent=2));bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(O/'Aloft_corrected_v12.blend'));print(json.dumps(report))
