import bpy,json,math,hashlib,os
from pathlib import Path
from mathutils import Vector
R=Path(os.environ.get('ALMAZOV_WORKDIR','/workspace/ALMAZOV_LIGHT'));O=Path(__file__).resolve().parents[1]/'assets';O.mkdir(parents=True,exist_ok=True)
source=R/'model/v11/Aloft_corrected_v11.blend';bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene
def web(v):return [float(v[0]),float(v[2]),-float(v[1])]
metadata={'version':11,'project':'Aloft · Ташкент','source_blend_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'units':'m','basis':'Blender XYZ -> WebGL X,Z,-Y','groups':json.load(open(R/'model/v07/lighting_geometry.json'))['summary'],'referenceCameras':[]}
center=Vector((26,16,23))
for n in range(1,7):
 cam=bpy.data.objects['REFERENCE_'+str(n)];d=json.load(open(R/f'model/v07/camera_reference{n}.json'));p=cam.matrix_world.translation;direction=cam.matrix_world.to_quaternion()@Vector((0,0,-1));distance=max(10,(center-p).dot(direction))
 metadata['referenceCameras'].append({'id':str(n),'name':'Референс '+str(n),'image':d['reference'],'position':web(p),'target':web(p+direction*distance),'type':d.get('camera_type','PERSP'),'fov':math.degrees(2*math.atan(d['resolution'][1]/(2*d['focal_pixels']))) if 'focal_pixels' in d else 45.,'orthoHeight':d.get('ortho_scale',1)*d['resolution'][1]/d['resolution'][0],'principalPoint':d['principal_point'],'resolution':d['resolution']})
installation=json.load(open(R/'model/v11/lighting_installation.json'))
metadata['segments']=[{'id':q['id'],'group':q['group'],'points':[web(v) for v in q['points_m']],'supplemental':q['id'].startswith('VISUAL-')} for q in installation['source_segments']+installation['visual_joins']]
metadata['source_cad_total_m']=installation['source_cad_total_m'];metadata['supplemental_visual_m']=installation['supplemental_visual_m'];metadata['supplemental_segments']=len(installation['visual_joins'])
metadata['spill']=[]
for ob in s.objects:
 if ob.type=='LIGHT' and ob.name.startswith('SPILL_'):
  group='POOL' if 'POOL' in ob.name else ('UPPER_FRAME' if 'UPPER_FRAME' in ob.name else 'BIG_FRAME')
  metadata['spill'].append({'group':group,'position':web(ob.matrix_world.translation),'direction':web(Vector(ob['emission_direction'])),'xAxis':web(ob.matrix_world.to_3x3().col[0]),'width':ob.data.size,'height':ob.data.size_y})
arch=list(bpy.data.collections['ALMAZOV_ARCHITECTURE_V07'].objects);site=list(bpy.data.collections['ILLUSTRATIVE_SITE_NOT_SURVEYED'].objects);emit=list(bpy.data.collections['ANIMATED_DIFFUSERS_V08'].objects)
for ob in arch:ob['viewer_role']='architecture';ob['viewer_source']=ob.name
for ob in site:ob['viewer_role']='context';ob['viewer_source']=ob.name
colors={'ROOF':(.9,.015,.5),'BIG_FRAME':(.015,.8,.55),'UPPER_FRAME':(.5,.9,.035),'POOL':(0,0,0)}
for g in colors:
 m=bpy.data.materials['NEON_RGBW_'+g];m.animation_data_clear();m.node_tree.animation_data_clear();m.node_tree.nodes.clear();p=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(p.outputs[0],out.inputs['Surface']);p.inputs['Base Color'].default_value=(.3,.3,.3,1);p.inputs['Emission Color'].default_value=(*colors[g],1);p.inputs['Emission Strength'].default_value=12.;p.inputs['Roughness'].default_value=.3
for ob in emit:
 ob.hide_viewport=False;ob.hide_render=False;ob['viewer_role']='neon';ob['viewer_source']=ob.name
 uv=ob.data.uv_layers.new(name='LIGHT_PATH')
 for p in ob.data.polygons:
  phase=ob.data.attributes['PATH_PHASE'].data[p.index].value
  for li in p.loop_indices:uv.data[li].uv=(phase,0.)
 bpy.context.view_layer.objects.active=ob
channels=[];dg=bpy.context.evaluated_depsgraph_get()
for ob in list(s.objects):
 if ob.name.startswith('CHANNELS_'):
  me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg);copy=bpy.data.objects.new(ob.name+'_WEB',me);s.collection.objects.link(copy);copy.matrix_world=ob.matrix_world.copy();copy['viewer_role']='channel';channels.append(copy)
bpy.ops.object.select_all(action='DESELECT')
for ob in arch+site+emit+channels:ob.hide_select=False;ob.select_set(True)
bpy.context.view_layer.objects.active=arch[0]
args={'filepath':str(O/'aloft_v11.glb'),'export_format':'GLB','use_selection':True,'export_apply':True,'export_extras':True,'export_cameras':False,'export_lights':False,'export_texcoords':True}
props=bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
if 'export_gpu_instances' in props:args['export_gpu_instances']=True
bpy.ops.export_scene.gltf(**args)
metadata['architecture_meshes']=len(arch);metadata['source_segments']=61;metadata['visible_segments']=len(emit);metadata['logical_pixels']=1834;metadata['site_status']='Illustrative presentation context, not a survey';metadata['white_cct_status']='Unconfirmed; viewer Kelvin control is a visual approximation';metadata['day_time_status']='Visual sky control, not a georeferenced solar calculation';metadata['glb_sha256']=hashlib.sha256((O/'aloft_v11.glb').read_bytes()).hexdigest()
(O/'scene.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2));print(json.dumps({k:metadata[k] for k in ['architecture_meshes','source_segments','logical_pixels','glb_sha256']},indent=2))
