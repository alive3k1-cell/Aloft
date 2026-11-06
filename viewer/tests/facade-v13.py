"""Compare raw browser captures in the user-marked facade regions, excluding neon lines."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

P = Path(__file__).resolve().parents[1] / 'test-output/v13'
# Native model X/Z coordinates; the test uses a fixed orthographic camera.
ROIS = {'large_left': (50.2, 51.3, 11, 35.5),
        'upper_above': (5.5, 18, 43.45, 44),
        'upper_below': (5.5, 18, 42.2, 42.9)}
report = {'conditions': '23:30, lime, static reference, exposure 0.4, bloom 0; neon on/off',
          'method': 'Absolute RGB difference in facade regions, excluding emitting lines; 8-bit channels. Small edge differences from antialiasing/transmission are allowed.',
          'regions_native_xz': ROIS, 'measurements': {}}
for label in ['before-balanced', 'after-fast', 'after-balanced', 'after-cinematic']:
    a = np.asarray(Image.open(P / (label + '-on.png')).convert('RGB')).astype(int)
    b = np.asarray(Image.open(P / (label + '-off.png')).convert('RGB')).astype(int)
    h, w = a.shape[:2]
    metrics = {}
    for name, (x0, x1, z0, z1) in ROIS.items():
        l, r = round(w/2 + (26-x1)*h/51), round(w/2 + (26-x0)*h/51)
        t, u = round(h/2 - (z1-23.5)*h/51), round(h/2 - (z0-23.5)*h/51)
        d = abs(a[t:u, l:r] - b[t:u, l:r])
        metrics[name] = {'pixel_rectangle': [l, t, r, u],
                         'mean_absolute_rgb_delta': float(d.mean()),
                         'max_channel_delta': int(d.max()),
                         'changed_pixel_fraction': float((d.max(axis=2) > 0).mean())}
        if label.startswith('after'):
            assert d.mean() < 1, (label, name, metrics[name])
    report['measurements'][label] = metrics
baseline = report['measurements']['before-balanced']
assert baseline['large_left']['mean_absolute_rgb_delta'] > 15
assert baseline['upper_below']['mean_absolute_rgb_delta'] > 15
for name in ROIS:
    reduction = 1 - report['measurements']['after-balanced'][name]['mean_absolute_rgb_delta'] / baseline[name]['mean_absolute_rgb_delta']
    assert reduction > .95, (name, reduction)
report['passed'] = True
(P / 'facade_validation.json').write_text(json.dumps(report, indent=2))
print('Facade regions: original defect reproduced; wash reduced >95% in all regions; all 3 qualities passed.')
