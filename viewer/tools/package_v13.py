"""Package the verified V13 viewer and Blender file without rebuilding geometry."""
import hashlib, json, os, shutil, zipfile
from pathlib import Path

V = Path(__file__).resolve().parents[1]
M = V.parent / 'models'
R = Path(os.environ.get('ALMAZOV_WORKDIR', '/workspace/ALMAZOV_LIGHT'))
O = R / 'model/v13'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def pack(path, items):
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in items.items()}
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in items.items():
            z.writestr(name, data)
        z.writestr('SHA256.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name, h in manifest.items():
            assert hashlib.sha256(z.read(name)).hexdigest() == h

readme = '''ALOFT — V13: исправление засветки фасадных рам

Распакуйте ZIP и откройте Aloft_Interactive_v13.html в Chrome или Edge.
Blender и интернет для просмотра не требуются.

Отключены восемь вспомогательных ламп большой и верхней фасадных рам.
Они создавали яркие пятна на поверхностях в отмеченных пользователем местах.
Сами линии неона, RGBW-управление, анимация и мягкое оптическое свечение сохранены.
Настройки ночи V12, архитектура, материалы и подсветка бассейна не менялись.

Проверены три режима качества и все сценарии: фасадные лампы остаются выключенными.
В контрольных областях без Bloom засветка уменьшена более чем на 95% относительно V12.
Реальная геометрия GLB совпадает с V12 побайтово. В BLEND проверено совпадение
геометрии, трансформаций и назначений материалов всех 262 мешей и кривых.

BLENDER: откройте Aloft_corrected_v13.blend в Blender 4.3+.
Восемь вспомогательных фасадных ламп скрыты при рендере и имеют нулевую энергию;
их драйверы энергии сняты. Сами излучающие материалы неона сохранены.
Cycles рассчитывает свет от них штатным трассировщиком; его изображение
может отличаться от браузера. Подсветка бассейна сохранена.

Версия предназначена для визуализации, не для расчёта освещённости.
Предыдущие версии сохранены в репозитории.
'''

native = json.loads((O / 'validation.json').read_text())
browser = json.loads((V / 'test-output/v13/after.json').read_text())
facade = json.loads((V / 'test-output/v13/facade_validation.json').read_text())
assert native['geometry_and_materials_identical'] and len(native['disabled_facade_proxy_lights']) == 8
assert sha(O / 'Aloft_corrected_v13.blend') == native['output_blend_sha256']
assert not browser['errors'] and browser['result']['poolFillRetained'] and facade['passed']
for quality in ['fast', 'balanced', 'cinematic']:
    assert browser['result'][quality]['facadeSpillZero']
    assert browser['result'][quality]['stats']['architecture'] == 90
glb = V / 'assets/aloft_v12.glb'
assert sha(glb) == 'b8b6f69b577c8d2975dfb51e2b933d282d00cb72c4ec765298429da2fd8d6169'
html = M / 'Aloft_Interactive_v13.html'
shutil.copy2(V / 'dist/index.html', html)
build = json.loads((V / 'dist/build.json').read_text())
assert sha(html) == build['html_sha256']
pack(M / 'Aloft_Interactive_v13.zip', {html.name: html.read_bytes(), 'README_RU.txt': readme.encode()})
pack(M / 'Aloft_Blender_v13.zip', {
    'Aloft_corrected_v13.blend': (O / 'Aloft_corrected_v13.blend').read_bytes(),
    'validation.json': (O / 'validation.json').read_bytes(),
    'README_RU.txt': readme.encode(),
    'sources/apply_revision_v13.py': (V / 'tools/apply_revision_v13.py').read_bytes(),
})
shutil.copy2(V / 'test-output/v13/front-final.png', M / 'Aloft_v13_front.png')
(M / 'Aloft_v13_status.md').write_text(readme)
report = {'version': 13, 'native': native, 'browser': browser, 'facade_comparison': facade,
          'glb_byte_identical_to_v12': True,
          'artifacts': {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in
                        [html, M / 'Aloft_Interactive_v13.zip', M / 'Aloft_Blender_v13.zip', glb]}}
(M / 'Aloft_v13_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report['artifacts'], indent=2))
