import sys,json,time,subprocess,colorsys,hashlib
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter,maximum_filter,map_coordinates
from PIL import Image
R=Path(__file__).resolve().parents[1]
sys.path.append(str(R/'tools/video_python'))
import OpenEXR,PyOpenColorIO as ocio

O=R/'video/v09';probe='--probe' in sys.argv;suffix='_probe' if probe else ''
def channels(path):return OpenEXR.File(str(path),separate_channels=True).channels()
def rgb(ch,name,components='RGB'):return np.stack([ch['ViewLayer.'+name+'.'+k].pixels for k in components],axis=-1).astype(np.float32)
def pfm_write(path,a):
 with path.open('wb') as f:f.write(f'PF\n{a.shape[1]} {a.shape[0]}\n-1.0\n'.encode());f.write(np.ascontiguousarray(a[::-1],dtype='<f4').tobytes())
def pfm_read(path):
 with path.open('rb') as f:
  assert f.readline().strip()==b'PF';w,h=map(int,f.readline().split());assert float(f.readline())<0
  return np.frombuffer(f.read(),dtype='<f4').reshape(h,w,3)[::-1].copy()
start=time.time();ch=channels(O/('backplate'+suffix+'.exr'))
color=rgb(ch,'Combined');albedo=rgb(ch,'Denoising Albedo');normal=rgb(ch,'Denoising Normal','XYZ');H,W=color.shape[:2]
denoised=O/('denoised'+suffix+'.npy')
if not denoised.exists():
 for name,data in [('color',color),('albedo',albedo),('normal',normal)]:pfm_write(O/(name+suffix+'.pfm'),data)
 cmd=[str(R/'tools/oidn-2.3.3.x86_64.linux/bin/oidnDenoise'),'-d','cpu','--hdr',str(O/('color'+suffix+'.pfm')),'--alb',str(O/('albedo'+suffix+'.pfm')),'--nrm',str(O/('normal'+suffix+'.pfm')),'-o',str(O/('clean'+suffix+'.pfm')),'-q','high','--threads','4','--affinity','0']
 subprocess.run(cmd,check=True);np.save(denoised,pfm_read(O/('clean'+suffix+'.pfm')))
base=np.load(denoised);assert np.isfinite(base).all()
cfg=ocio.Config.CreateFromFile('/usr/share/blender/datafiles/colormanagement/config.ocio');tx=ocio.DisplayViewTransform(src='scene_linear',display='sRGB',view='AgX');proc=cfg.getProcessor(tx).getDefaultCPUProcessor()
def display(a):
 a=np.ascontiguousarray(a,dtype=np.float32);proc.applyRGB(a);return a
random=np.random.default_rng(1441).uniform(-.35,.35,(H,W,1)).astype(np.float32)
def quantize(a,dither):return np.clip(np.floor(np.clip(a,0,1)*255+.5+dither),0,255).astype(np.uint8)
base8=quantize(display(base.copy()),random)
Image.fromarray(base8).save(O/('clean_background'+suffix+'.png'))
light=channels(O/('light_buffers'+suffix+'.exr'))
groups=['ROOF','BIG_FRAME','UPPER_FRAME','POOL']
masks=np.stack([light['ViewLayer.MASK_'+g+'.X'].pixels for g in groups],axis=-1).astype(np.float32)
total=masks.sum(axis=-1);coverage=light['ViewLayer.Combined.A'].pixels.astype(np.float32)
assert total.max()>.05 and all(masks[:,:,i].sum()>0 for i in range(4))
assert np.mean(abs(total-coverage))<1e-4
weights=masks/np.maximum(total[:,:,None],1e-12)*coverage[:,:,None]
phase=np.clip(light['ViewLayer.PHASE.X'].pixels/np.maximum(total,1e-12),0,1).astype(np.float32)
neon=coverage>1e-6;nr,nc=np.nonzero(neon);u=phase[neon];covers=weights[neon]
# One geometry/visibility calculation, followed by a fresh material evaluation on
# every output frame. No frame interpolation or enlargement of the old video.
affected=maximum_filter(neon.astype(np.uint8),size=75)>0;ar,ac=np.nonzero(affected)
lookup=np.full((H,W),-1,dtype=np.int32);lookup[affected]=np.arange(len(ar));ni=lookup[neon]
base_part=base[affected]*(1-coverage[affected,None]);rand_part=random[affected]
factor=4;LH=(H+factor-1)//factor;LW=(W+factor-1)//factor
low_index=(nr//factor)*LW+(nc//factor);sample_coords=np.stack([(ar+.5)/factor-.5,(ac+.5)/factor-.5])
colors=np.array([[.9,.015,.5],[.015,.8,.55],[.5,.9,.035],[0,0,0]],np.float32)
levels=np.array([.85,.8,.8,.22],np.float32)
knots=[(0,0),(3,0),(5,2),(12,2),(14,3),(22,3),(24,1),(28,1),(30,0)]
def mode_weights(t):
 out=np.zeros(4,dtype=np.float32)
 for (a,ma),(b,mb) in zip(knots,knots[1:]):
  if a<=t<=b:
   f=(t-a)/(b-a);f=f*f*(3-2*f);out[ma]+=1-f;out[mb]+=f;return out
 out[0]=1;return out
def hsv_array(h,s,v):
 h=(h%1)*6;i=np.floor(h).astype(np.int32);f=h-i;p=v*(1-s);q=v*(1-s*f);tt=v*(1-s*(1-f))
 return np.stack([np.select([i==0,i==1,i==2,i==3,i==4,i==5],[v,q,p,p,tt,v]),np.select([i==0,i==1,i==2,i==3,i==4,i==5],[tt,v,v,q,p,p]),np.select([i==0,i==1,i==2,i==3,i==4,i==5],[p,p,tt,v,v,q])],axis=-1).astype(np.float32)
def signals(t,mode):
 cycle=t/8.;result=np.zeros((len(u),3),np.float32)
 for g in range(4):
  if g==3:
   if mode!=0:result+=covers[:,g,None]*np.float32(26*.65*levels[g])
   continue
  color=np.broadcast_to(colors[g],(len(u),3))
  if mode in (1,2):
   h,s,v=colorsys.rgb_to_hsv(*colors[g]);h=h+.4*.5*np.sin(np.float32(np.pi*2)*(cycle+(u*.65 if mode==2 else 0.)))
   if np.ndim(h)==0:h=np.full(len(u),h,dtype=np.float32)
   color=hsv_array(h,s,v)
  gain=np.ones(len(u),np.float32)
  if mode==2:gain=1-.65*(1-(.5+.5*np.sin(np.float32(np.pi*4)*(u-cycle))))
  if mode==3:gain=.08+.92*np.maximum(0,1-abs(((u-cycle+.5)%1)-.5)/.22)**2
  result+=covers[:,g,None]*color*(gain*np.float32(26*.65*levels[g]))[:,None]
 return result
def frame(t):
 mix=mode_weights(t);emission=np.zeros((len(u),3),np.float32)
 for mode,v in enumerate(mix):
  if v>1e-7:emission+=v*signals(t,mode)
 low=np.zeros((LH*LW,3),np.float32)
 np.add.at(low,low_index,emission/(factor*factor));low=low.reshape(LH,LW,3)
 glow=.13*gaussian_filter(low,(.7,.7,0))+.1*gaussian_filter(low,(2.4,2.4,0))
 halo=np.stack([map_coordinates(glow[:,:,i],sample_coords,order=1,mode='constant') for i in range(3)],axis=-1)
 linear=base_part.copy();linear[ni]+=emission;linear+=halo
 out=base8.copy();out[affected]=quantize(display(linear),rand_part);return out
settings=json.load(open(O/('probe_settings.json' if probe else 'render_settings.json')))
stats={'resolution':[W,H],'fps':24,'duration_seconds':30,'frame_count':720,'neon_coverage_pixels':int(neon.sum()),'changed_region_pixels':int(affected.sum()),'mask_sum_alpha_mean_absolute_error':float(np.mean(abs(total-coverage))),'denoiser':'Intel Open Image Denoise2.3.3, RT HDR, high, noisy albedo/normal auxiliaries','color_management':'Blender AgX, sRGB, exposure0, lookNone','program_knots_seconds_and_mode':knots,'background_static':True,'material_recalculated_each_frame':True,'optical_bloom':'Two spatial Gaussian lobes, scene-linear, group material flux','moving_reflections_or_pixel_spill':False,'source_blend_sha256':settings['source_blend_sha256']}
if probe:
 for t in [0.,8.,18.,26.]:Image.fromarray(frame(t)).save(O/f'probe_{int(t):02}.png')
else:
 outfile=O/'Aloft_light_show_1080x1920_30s.mp4'
 cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','24','-i','pipe:0','-an','-c:v','libx264','-threads','4','-preset','medium','-crf','16','-pix_fmt','yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart',str(outfile)]
 movie=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 hashes=[]
 for i in range(720):
  a=frame(i/24);movie.stdin.write(a.tobytes());hashes.append(hashlib.sha256(a.tobytes()).hexdigest())
  if i in [0,192,432,624]:Image.fromarray(a).save(O/f'poster_{i:03}.png')
  if i%120==0:print('Encoded',i,'/720 frames',round(time.time()-start,1),'s',flush=True)
 movie.stdin.close();assert movie.wait()==0
 stats['unique_frame_images']=len(set(hashes));stats['last_to_first_mean_absolute_RGB']=float(abs(frame(719/24).astype(float)-frame(0).astype(float)).mean());stats['bytes']=outfile.stat().st_size;stats['sha256']=hashlib.sha256(outfile.read_bytes()).hexdigest()
stats['seconds']=round(time.time()-start,2)
(O/('probe_composition.json' if probe else 'video_validation.json')).write_text(json.dumps(stats,indent=2));print(json.dumps(stats,indent=2),flush=True)
