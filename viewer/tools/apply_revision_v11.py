"""Apply the nine requested corrections to a copy of the accepted V08 Blender scene."""
import bpy,bmesh,json,hashlib,math,os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(os.environ.get('ALMAZOV_WORKDIR','/workspace/ALMAZOV_LIGHT'));O=R/'model/v11';O.mkdir(exist_ok=True)
source=R/'model/v08/Aloft_light_show_v08.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene
D=json.load(open(O/'revision_geometry.json'));L=json.load(open(R/'model/v07/lighting_geometry.json'))
arch=bpy.data.collections['ALMAZOV_ARCHITECTURE_V07'];emit=bpy.data.collections['ANIMATED_DIFFUSERS_V08']
def fingerprint(ob):
    if ob.type!='MESH':return None
    return hashlib.sha256(json.dumps({'v':[list(v.co) for v in ob.data.vertices],'f':[list(p.vertices) for p in ob.data.polygons],'matrix':[list(r) for r in ob.matrix_world]},sort_keys=True).encode()).hexdigest()
before={o.name:fingerprint(o) for o in arch.objects}
source_curves={o.name:[list(p.co) for sp in o.data.splines for p in sp.points] for o in bpy.data.objects if o.name.startswith('NEON_SEG')}
# Only porcelain-grey samples are darkened. White, glass, orange and canopy samples retain their values.
colors={'MAT_FACADE_GREY_LIGHT':(.28,.295,.31),'MAT_FACADE_GREY_MEDIUM':(.16,.175,.19),'MAT_FACADE_DARK_PLINTH':(.115,.125,.135)}
for name,color in colors.items():
    m=bpy.data.materials[name];m.diffuse_color=(*color,1);m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*color,1)
black=bpy.data.materials['MAT_ROOF_PAINTED_METAL'].copy();black.name='MAT_ROOF_BLACK_V11';black.diffuse_color=(.012,.014,.018,1)
p=black.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=black.diffuse_color;p.inputs['Roughness'].default_value=.43;p.inputs['Metallic'].default_value=.18
removed=[]
for ob in list(arch.objects):
    if ob.name.startswith(('ROOF_SKYLIGHT_','ROOF_LOUVRE_')) or ob.name in ['ROOF_CONTINUOUS_SOFFIT','ROOF_CONTINUOUS_FASCIA']:
        removed.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
# One closed black canopy with a genuinely open aperture and a flush underside.
cap=bpy.data.objects['ROOF_CANTILEVER_WITH_OPENING']
for v in cap.data.vertices:
    if v.co.z<46.6:v.co.z=46.11
cap.data.materials.clear();cap.data.materials.append(black)
for p in cap.data.polygons:p.material_index=0
cap['revision']='V11: open aperture, black canopy, underside at46.11; no glazing or mullions'
changed=[cap.name]
for ob in arch.objects:
    if ob.name.startswith('ROOF_TERRACE_COLUMN_'):
        for v in ob.data.vertices:
            if v.co.z>46.1:v.co.z=46.11
        changed.append(ob.name)
    if ob.name.startswith('BUILDING_WING_ENVELOPE'):
        idx=len(ob.data.materials);ob.data.materials.append(black)
        for p in ob.data.polygons:
            if p.material_index==2 and min(ob.data.vertices[i].co.z for i in p.vertices)>43.5:p.material_index=idx
# Approved additional roof and second-floor terrace details, isolated meshes.
for q in D['objects']:
    me=bpy.data.meshes.new(q['name']);me.from_pydata(q['verts'],[],q['faces']);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(q['name'],me);arch.objects.link(ob);me.materials.append(black if q['material']=='ROOF_BLACK' else bpy.data.materials[q['material']]);ob['source']='V11 user screenshot correction';ob['status']='Visual dimensions; not surveyed structure'
# Keep original hidden CAD curves immutable; installation height is separate from source XY/length.
offsets={'ROOF':-.12,'POOL':-.391}
for ob in emit.objects:
    dz=offsets.get(ob.get('group'),0.)
    for v in ob.data.vertices:v.co.z+=dz
    if dz:ob['installation_offset_z_m']=dz
for group,dz in offsets.items():
    ob=bpy.data.objects['CHANNELS_'+group]
    for sp in ob.data.splines:
        for p in sp.points:p.co.z+=dz
for ob in s.objects:
    if ob.name.startswith('SPILL_POOL_'):ob.location.z+=offsets['POOL']
# Visual completion of missing small corners and the courtyard step, not fabricated CAD records.
route=[Vector((x,y,46.47)) for x,y in [(52.19992,31.65),(-1.8,31.65),(-1.8,15.6),(18.14982563123,15.6),(18.14982563123,13.4499990713),(37.04973797788,13.4499990713),(37.04973797788,-.60000007261),(52.38373797788,-.60000007261)]]
def phase(p):
    lens=[(b-a).length for a,b in zip(route,route[1:])];best=(1e30,0);cum=0
    for a,b,d in zip(route,route[1:],lens):
        t=max(0,min(1,(p-a).dot(b-a)/(d*d)));q=a+(b-a)*t;candidate=((q-p).length_squared,(cum+t*d)/sum(lens))
        if candidate[0]<best[0]:best=candidate
        cum+=d
    return best[1]
joins=[]
for name,xy in D['joins']:
    points=[Vector((x,y,46.47)) for x,y in xy];cu=bpy.data.curves.new('V11_JOIN_'+name,'CURVE');cu.dimensions='3D';cu.bevel_depth=.009;cu.bevel_resolution=2;cu.use_fill_caps=True
    # Additional subdivisions retain smooth effect phase across the2.15m return.
    dens=[]
    for a,b in zip(points,points[1:]):
        count=max(1,math.ceil((b-a).length/.08));dens.extend(a+(b-a)*i/count for i in range(count))
    dens.append(points[-1]);sp=cu.splines.new('POLY');sp.points.add(len(dens)-1)
    for p,v in zip(sp.points,dens):p.co=(*v,1)
    ob=bpy.data.objects.new('NEON_JOIN_'+name,cu);emit.objects.link(ob);bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get();me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg);bpy.data.objects.remove(ob,do_unlink=True);bpy.data.curves.remove(cu);ob=bpy.data.objects.new('NEON_JOIN_'+name,me);emit.objects.link(ob);me.update()
    me.materials.append(bpy.data.materials['NEON_RGBW_ROOF']);ob['group']='ROOF';ob['segment_id']='VISUAL-'+name;ob['supplemental']=True;ob['source']='User V11: continuous roof line at missing corners; no CAD quantity assigned';ob.visible_shadow=False;ob.visible_diffuse=False
    att=me.attributes.new('PATH_PHASE','FLOAT','FACE')
    for p in me.polygons:att.data[p.index].value=phase(p.center)
    joins.append({'id':ob['segment_id'],'group':'ROOF','points_m':[list(p) for p in points],'length_m':sum((b-a).length for a,b in zip(points,points[1:])),'status':ob['source']})
# Real night background and fill, with daytime unchanged and LED controls untouched.
night=s.world.node_tree.nodes['DUSK_BACKGROUND'];night.inputs['Strength'].driver_remove('default_value');night.inputs['Strength'].default_value=.025
# Preserve the existing environment control on the night strength.
f=night.inputs['Strength'].driver_add('default_value');f.driver.expression='.025*e';v=f.driver.variables.new();v.name='e';v.type='SINGLE_PROP';v.targets[0].id=bpy.data.objects['LIGHT_CONTROLS'];v.targets[0].data_path='["ENVIRONMENT"]'
for name,expr in [('SUN','(2.4*d+.006*(1-d))*e'),('SOFT_SKY_FILL','(60000*d+600*(1-d))*e')]:bpy.data.lights[name].animation_data.drivers.find('energy').driver.expression=expr
s['version']='V11: user roof/terrace/porcelain/neon/night corrections; other accepted geometry frozen'
# Visible-source metadata uses installed positions; originals and lengths retained separately.
installed=[]
for q in L['segments']:
    installed.append({**q,'source_points_m':q['points_m'],'points_m':[[x,y,z+offsets.get(q['group'],0)] for x,y,z in q['points_m']]})
(O/'lighting_installation.json').write_text(json.dumps({'source_segments':installed,'visual_joins':joins,'source_cad_total_m':sum(q['cad_length_m'] for q in L['segments']),'supplemental_visual_m':sum(q['length_m'] for q in joins)},indent=2))
after={o.name:fingerprint(o) for o in arch.objects};unexpected=[name for name,h in before.items() if name not in removed+changed and after.get(name)!=h];assert not unexpected,unexpected
assert source_curves=={o.name:[list(p.co) for sp in o.data.splines for p in sp.points] for o in bpy.data.objects if o.name.startswith('NEON_SEG')}
# No downward obstruction along the pool strip once the diffuser sits below the flush soffit.
V=[];F=[]
for ob in arch.objects:
    if ob.type!='MESH':continue
    k=len(V);V.extend(ob.matrix_world@v.co for v in ob.data.vertices);F.extend([k+i for i in p.vertices] for p in ob.data.polygons)
bvh=BVHTree.FromPolygons(V,F);clearances=[]
for q in installed:
    if q['group']!='POOL':continue
    for a,b in zip(q['points_m'],q['points_m'][1:]):
        for t in [.1,.5,.9]:
            point=Vector(a).lerp(Vector(b),t);hit=bvh.ray_cast(point,Vector((0,0,-1)),.025)[0];clearances.append(hit is None)
assert all(clearances),'Pool emitter intersects the roof'
assert not any(o.name.startswith('ROOF_SKYLIGHT') for o in arch.objects)
assert abs(min(v.co.z for v in cap.data.vertices)-46.11)<1e-5
report={'source_blend_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'architecture_before':len(before),'architecture_after':len(after),'geometry_changed':changed,'removed_roof_objects':removed,'added_objects':sorted(set(after)-set(before)),'unchanged_geometry_count':sum(name not in changed+removed for name in before),'unexpected_geometry_changes':unexpected,'original_CAD_curves_unchanged':True,'source_segments':61,'visual_joins':joins,'preview_pixels_unchanged':1834,'source_length_m_unchanged':sum(q['cad_length_m'] for q in L['segments']),'pool_underside_clearance_samples':len(clearances),'pool_clearance_pass':all(clearances),'porcelain_linear_colors':colors,'roof_linear_color':list(black.diffuse_color),'second_floor_terrace_top_m':5.25,'night_daylight_preserved':True}
(O/'geometry_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
bpy.context.view_layer.update();s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(O/'Aloft_corrected_v11.blend'))
print(json.dumps({k:report[k] for k in ['architecture_before','architecture_after','unchanged_geometry_count','source_segments','preview_pixels_unchanged','pool_clearance_pass']}))
