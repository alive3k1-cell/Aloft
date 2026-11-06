"""Package only verified V11 outputs; retain all earlier versions."""
import json,hashlib,zipfile,shutil,os
from pathlib import Path
V=Path(__file__).resolve().parents[1];ROOT=V.parent;M=ROOT/'models';R=Path(os.environ.get('ALMAZOV_WORKDIR','/workspace/ALMAZOV_LIGHT'));O=R/'model/v11'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pack(path,items):
    manifest={name:hashlib.sha256(data).hexdigest() for name,data in items.items()}
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in items.items():z.writestr(name,data)
        z.writestr('SHA256.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name,h in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==h
readme='''ALOFT — V11, исправления по девяти пунктам

Просмотрщик: распакуйте ZIP и откройте Aloft_Interactive_v11.html в Chrome или Edge на компьютере.
Blender и интернет не требуются. Управление и прежние сценарии сохранены.

Что исправлено:
• Серый керамогранит темнее; белая отделка и терракота сохранены.
• Кровля чёрная, над бассейном открытый проём без стекла и поперечных переплётов.
• Нижняя плоскость кровли выровнена; колонны доведены до её поверхности.
• Неон бассейна размещён под подшивкой, кровельный неон — на открытой части кромки.
• На уступе во дворе и коротких угловых стыках световая линия непрерывна.
• Ламели крыши имеют ровный шаг, закрытые торцы, стыкуются на углах; опоры утоплены за ними.
• Добавлена длинная терраса второго этажа с ограждением и опорами. Нижняя терраса сохранена.
• Ночь действительно тёмная: затемнены небо, фоновый и отражённый свет. Дневные значения, RGBW, экспозиция и сценарии не изменены.

Остальная архитектура сохранена. Прежние версии доступны отдельно.
Размеры новых деталей выбраны для визуализации по предоставленным изображениям.
61 исходная линия DWG и 1834 точки эффекта сохранены. Четыре коротких добавленных соединения (2,4301 м) — визуальные дополнения по замечаниям, отдельно от исходной CAD-ведомости.

BLENDER: откройте Aloft_corrected_v11.blend в Blender4.3+. Rendered показывает свет; Space над Timeline запускает прежний8-секундный цикл. LIGHT_CONTROLS содержит RGBW, уровни, MODE, SPEED, DAYLIGHT. Исходный V08 не перезаписан.
'''
html=M/'Aloft_Interactive_v11.html';shutil.copy2(V/'dist/index.html',html)
pack(M/'Aloft_Interactive_v11.zip',{html.name:html.read_bytes(),'README_RU.txt':readme.encode()})
items={name:(O/name).read_bytes() for name in ['Aloft_corrected_v11.blend','lighting_installation.json','revision_geometry.json','geometry_validation.json']}
items['README_RU.txt']=readme.encode()
for name in ['prepare_revision_v11.py','apply_revision_v11.py','export_blender.py']:items['sources/'+name]=(V/'tools'/name).read_bytes()
pack(M/'Aloft_Blender_v11.zip',items)
for src,dest in [('pool','pool_day'),('pool_night','pool_night'),('courtyard','roof_day'),('courtyard_night','roof_night'),('terrace','terrace'),('general_day','day'),('general_night','night')]:shutil.copy2(V/f'test-output/v11/after-{src}.png',M/f'Aloft_v11_{dest}.png')
report={'version':11,'geometry':json.loads((V/'test-output/v11/geometry.json').read_text()),'browser':json.loads((V/'test-output/browser_validation.json').read_text()),'night':json.loads((V/'test-output/v11/night_validation.json').read_text()),'review':json.loads((V/'test-output/v11/after.json').read_text()),'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in [html,M/'Aloft_Interactive_v11.zip',M/'Aloft_Blender_v11.zip',V/'assets/aloft_v11.glb']}}
(M/'Aloft_v11_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(M/'Aloft_v11_status.md').write_text(readme)
print(json.dumps(report['artifacts'],indent=2))
