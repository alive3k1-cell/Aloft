import json,subprocess,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'video/v09';f=O/'Aloft_light_show_1080x1920_30s.mp4'
meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_entries','stream=codec_name,width,height,pix_fmt,avg_frame_rate,nb_read_frames:format=duration,size','-of','json',str(f)]))
v=meta['streams'][0];assert v['codec_name']=='h264' and [v['width'],v['height']]==[1080,1920]
assert v['avg_frame_rate']=='24/1' and int(v['nb_read_frames'])==720 and abs(float(meta['format']['duration'])-30)<.02
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(f),'-f','null','-'],check=True)
report=json.load(open(O/'video_validation.json'));assert report['unique_frame_images']>600
assert report['mask_sum_alpha_mean_absolute_error']<1e-4
assert report['last_to_first_mean_absolute_RGB']<.2
source=R/'model/v08/Aloft_light_show_v08.blend';assert hashlib.sha256(source.read_bytes()).hexdigest()==report['source_blend_sha256']
report['ffprobe']=meta;report['complete_video_decode_passed']=True;report['native_V08_source_unchanged']=True
report['old_video']={'resolution':[448,640],'duration_seconds':8,'unique_motion_frames_per_second':8}
report['pixel_count_ratio']=1080*1920/(448*640);report['duration_ratio']=30/8
(O/'video_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
