import json,hashlib,zipfile,shutil,os
from pathlib import Path
V=Path(__file__).resolve().parents[1];M=V.parent/'models';R=Path(os.environ.get('ALMAZOV_WORKDIR','/workspace/ALMAZOV_LIGHT'));O=R/'model/v12'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pack(path,items):
 manifest={name:hashlib.sha256(data).hexdigest() for name,data in items.items()}
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name,data in items.items():z.writestr(name,data)
  z.writestr('SHA256.json',json.dumps(manifest,indent=2))
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  for name,h in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==h
readme='''ALOFT — V12

Распакуйте ZIP и откройте Aloft_Interactive_v12.html в Chrome или Edge на компьютере.
Blender и интернет для просмотра не требуются.

Исправления:
1. Ночь светлее и читаемее. После18:35 продолжается плавное затухание сумеречного света; резкого провала в чёрный нет. Дневные значения и пользовательская экспозиция сохранены.
2. Вспомогательный свет учитывает перекрытия стенами и крышей. Убраны ложные зеркальные блики от этих вспомогательных источников. Остекление сохраняет собственный материал и отражения окружения.
3. Нижнее стеклянное ограждение первого этажа удалено вместе с рамками. Терраса второго этажа сохранена.

Остальная архитектура V11 не изменена: все90 оставшихся архитектурных объектов совпадают по геометрии, трансформациям и назначениям материалов. Сохранены фасадное остекление, крыша, ламели, колонны, панельные рисунки, цвета и неон.

Перекрытие вспомогательного света в браузере предварительно рассчитано по неподвижной непрозрачной архитектуре:5 проб вдоль каждого из11 источников, интерполяция между вершинами. Это визуальное приближение, не IES/расчёт освещённости. Изменение цвета RGBW, яркости, сценария и камеры работает в реальном времени. В Cycles перекрытие света рассчитывается штатным трассировщиком.

BLENDER: откройте Aloft_corrected_v12.blend в Blender4.3+. Rendered показывает свет, Space над Timeline запускает сохранённую анимацию. LIGHT_CONTROLS содержит RGBW, уровни, MODE, SPEED и DAYLIGHT.
'''
html=M/'Aloft_Interactive_v12.html';shutil.copy2(V/'dist/index.html',html)
pack(M/'Aloft_Interactive_v12.zip',{html.name:html.read_bytes(),'README_RU.txt':readme.encode()})
items={name:(O/name).read_bytes() for name in ['Aloft_corrected_v12.blend','geometry_validation.json','spill_validation.json']};items['README_RU.txt']=readme.encode();items['lighting_installation.json']=(R/'model/v11/lighting_installation.json').read_bytes()
for name in ['apply_revision_v12.py','export_blender.py','bake_spill_visibility_v12.py','verify_revision_v12.py']:items['sources/'+name]=(V/'tools'/name).read_bytes()
pack(M/'Aloft_Blender_v12.zip',items)
for name in ['twilight_1835','night','pool','pool_cinematic','terrace']:shutil.copy2(V/f'test-output/v12/{name}.png',M/f'Aloft_v12_{name}.png')
review=json.loads((V/'test-output/v12/review.json').read_text());assert not review['errors']
report={'version':12,'geometry':json.loads((V/'test-output/v12/geometry.json').read_text()),'browser':json.loads((V/'test-output/browser_validation.json').read_text()),'review':review,'environment_state_tests':'passed: smooth twilight after18:35, moderate night, original daylight','artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in [html,M/'Aloft_Interactive_v12.zip',M/'Aloft_Blender_v12.zip',V/'assets/aloft_v12.glb']}}
assert report['browser']['initial']['architecture']==90 and not report['browser']['browser_errors']
(M/'Aloft_v12_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(M/'Aloft_v12_status.md').write_text(readme);print(json.dumps(report['artifacts'],indent=2))
