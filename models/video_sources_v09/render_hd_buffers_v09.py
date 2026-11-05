import bpy,json,sys,time,hashlib
from pathlib import Path
from bpy_extras.object_utils import world_to_camera_view

R=Path(__file__).resolve().parents[1];B=R/'model/v08';O=R/'video/v09';O.mkdir(parents=True,exist_ok=True)
probe='--probe' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(B/'Aloft_light_show_v08.blend'))
s=bpy.context.scene;c=bpy.data.objects['LIGHT_CONTROLS'];s.camera=bpy.data.objects['REFERENCE_3']
s.render.resolution_x=1080;s.render.resolution_y=1920;s.render.resolution_percentage=50 if probe else 100
s.render.use_persistent_data=True;s.use_nodes=False;s.cycles.use_denoising=False;s.cycles.use_animated_seed=False
c['MODE']=2;c.update_tag();s.frame_set(1);bpy.context.view_layer.update()
arch=list(bpy.data.collections['ALMAZOV_ARCHITECTURE_V07'].objects)
# Fit the existing camera to a9:16 frame without altering any model geometry.
points=[ob.matrix_world@v.co for ob in arch if ob.type=='MESH' for v in ob.data.vertices if (ob.matrix_world@v.co).z>=-1.5]
def project_bounds():
 projected=[world_to_camera_view(s,s.camera,p) for p in points]
 return [min(p.x for p in projected),min(p.y for p in projected),max(p.x for p in projected),max(p.y for p in projected)]
bounds=project_bounds();s.camera.data.lens*=min(.87/(bounds[2]-bounds[0]),.88/(bounds[3]-bounds[1]));bounds=project_bounds()
for axis,target,idx in [('x',.5,0),('y',.53,1)]:
 center=(bounds[idx]+bounds[idx+2])/2;key='shift_'+axis;before=world_to_camera_view(s,s.camera,points[0])[idx]
 old=getattr(s.camera.data,key);setattr(s.camera.data,key,old+.001);after=world_to_camera_view(s,s.camera,points[0])[idx]
 setattr(s.camera.data,key,old+(target-center)/((after-before)/.001));bounds=project_bounds()
assert bounds[0]>=.04 and bounds[1]>=.04 and bounds[2]<=.96 and bounds[3]<=.98,bounds
settings={'resolution':[1080,1920],'probe':probe,'camera':s.camera.name,'camera_lens_mm':s.camera.data.lens,'projected_architecture_bounds':bounds,'matrix_world':[list(r) for r in s.camera.matrix_world],'view_transform':s.view_settings.view_transform,'look':s.view_settings.look,'display':s.display_settings.display_device,'exposure':s.view_settings.exposure,'gamma':s.view_settings.gamma,'source_blend_sha256':hashlib.sha256((B/'Aloft_light_show_v08.blend').read_bytes()).hexdigest()}
s.render.image_settings.file_format='OPEN_EXR_MULTILAYER';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='16';s.render.image_settings.exr_codec='ZIP'
vl=bpy.context.view_layer;vl.cycles.denoising_store_passes=True
emitters=list(bpy.data.collections['ANIMATED_DIFFUSERS_V08'].objects)
for ob in emitters:ob.hide_render=True
s.cycles.samples=32 if probe else 256;s.cycles.adaptive_threshold=.05 if probe else .012;s.cycles.adaptive_min_samples=16 if probe else 32
s.render.filepath=str(O/('backplate_probe.exr' if probe else 'backplate.exr'));t=time.time();bpy.ops.render.render(write_still=True);settings['backplate_seconds']=time.time()-t
for ob in emitters:ob.hide_render=False
vl.cycles.denoising_store_passes=False
for name in ['ALMAZOV_ARCHITECTURE_V07','ILLUSTRATIVE_SITE_NOT_SURVEYED']:vl.layer_collection.children[name].holdout=True
occ=bpy.data.collections.new('CHANNEL_HOLDOUT');s.collection.children.link(occ)
for ob in list(s.objects):
 if ob.name.startswith('CHANNELS_'):
  for coll in list(ob.users_collection):coll.objects.unlink(ob)
  occ.objects.link(ob)
 if ob.type=='LIGHT':ob.hide_render=True
vl.layer_collection.children[occ.name].holdout=True
black=bpy.data.worlds.new('BUFFER_BLACK');black.use_nodes=True;black.node_tree.nodes.get('Background').inputs['Strength'].default_value=0.;s.world=black;s.render.film_transparent=True
s.cycles.max_bounces=0;s.cycles.diffuse_bounces=0;s.cycles.glossy_bounces=0;s.cycles.transmission_bounces=0
for name in ['PHASE','MASK_ROOF','MASK_BIG_FRAME','MASK_UPPER_FRAME','MASK_POOL']:
 a=vl.aovs.add();a.name=name;a.type='VALUE'
for g in ['ROOF','BIG_FRAME','UPPER_FRAME','POOL']:
 m=bpy.data.materials['NEON_RGBW_'+g];m.node_tree.animation_data_clear();ns=m.node_tree.nodes;ns.clear();lk=m.node_tree.links
 e=ns.new('ShaderNodeEmission');e.inputs['Color'].default_value=(1,1,1,1);e.inputs['Strength'].default_value=1.;out=ns.new('ShaderNodeOutputMaterial');lk.new(e.outputs[0],out.inputs['Surface'])
 attr=ns.new('ShaderNodeAttribute');attr.attribute_name='PATH_PHASE';a=ns.new('ShaderNodeOutputAOV');a.aov_name='PHASE';lk.new(attr.outputs['Fac'],a.inputs['Value'])
 for group in ['ROOF','BIG_FRAME','UPPER_FRAME','POOL']:
  a=ns.new('ShaderNodeOutputAOV');a.aov_name='MASK_'+group;a.inputs['Value'].default_value=1. if g==group else 0.
s.cycles.samples=128 if probe else 1024;s.cycles.adaptive_min_samples=16 if probe else 32;s.cycles.adaptive_threshold=.01 if probe else .003
s.render.filepath=str(O/('light_buffers_probe.exr' if probe else 'light_buffers.exr'));t=time.time();bpy.ops.render.render(write_still=True);settings['mask_seconds']=time.time()-t
(O/('probe_settings.json' if probe else 'render_settings.json')).write_text(json.dumps(settings,indent=2));print(json.dumps(settings,indent=2),flush=True)
