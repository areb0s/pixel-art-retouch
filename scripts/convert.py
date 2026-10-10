"""Source-derived Fixer conversion. Existing dependencies only; no downloads."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
VENDOR = Path(__file__).resolve().parents[1] / 'vendor'


def convert(source, output, size):
    import cv2
    import numpy as np
    from PIL import Image
    from scipy.ndimage import distance_transform_edt

    if output.exists():
        raise ValueError('Output directory already exists; choose a fresh directory.')
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = json.loads((VENDOR / 'manifest.json').read_text(encoding='utf-8'))
    for name, digest in manifest['files'].items():
        if hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Bundled Fixer file changed: {name}')
    sys.path.insert(0, str(VENDOR))
    from pixelfixer.api import process

    with Image.open(source) as image:
        if image.mode != 'RGBA' or image.width != image.height:
            raise ValueError('Input must be a square RGBA crop; review mask and pad, never stretch.')
        if not 16 <= image.width <= 2000 or not 1 <= size <= image.width:
            raise ValueError('Source side must be 16..2000; target side must be 1..source side.')
        a = np.array(image)
    if not np.isin(a[:, :, 3], [0, 255]).all() or not (a[:, :, 3] == 255).any():
        raise ValueError('Input needs a reviewed binary alpha mask with visible pixels.')
    mask = a[:, :, 3] > 127
    _, indices = distance_transform_edt(~mask, return_indices=True)
    rgb = a[:, :, :3][tuple(indices)]
    rgba = np.dstack([rgb, a[:, :, 3]])
    opaque = a[:, :, :3][mask].reshape(1, -1, 3)
    palette = Image.fromarray(opaque).quantize(colors=32, method=Image.Quantize.MEDIANCUT)
    cv2.setRNGSeed(123)
    np.random.seed(123)
    result = process(rgba, force_step=a.shape[0] / size, return_png=False)
    fixed = result.pop('array')
    if fixed.shape[:2] != (size, size):
        raise ValueError(f'Unexpected Fixer dimensions: {fixed.shape}')
    alpha = np.where(cv2.resize(a[:, :, 3], (size, size), interpolation=cv2.INTER_AREA) >= 128,
                     255, 0).astype('uint8')
    fixed[:, :, 3] = alpha
    final = Image.fromarray(fixed).convert('RGB').quantize(
        palette=palette, dither=Image.Dither.NONE).convert('RGBA')
    final.putalpha(Image.fromarray(alpha))
    output.mkdir(parents=True, exist_ok=False)
    final.save(output / 'fixer.png')
    (output / 'conversion.json').write_text(json.dumps({
        'source_sha256': source_sha,
        'rng_protocol': 'seed123-single-forced',
        'result_sha256': hashlib.sha256((output / 'fixer.png').read_bytes()).hexdigest(),
        'target': size, 'palette': 'source opaque median-cut, at most 32 colors, no dithering',
        'alpha': 'source area coverage >= 128', 'fixer_commit': manifest['commit'],
        'fixer': result,
        'versions': {'Pillow': Image.__version__, 'numpy': np.__version__, 'opencv': cv2.__version__},
        'quality': 'requires visual review; not automatic artistic acceptance',
    }, indent=2), encoding='utf-8')
    print(output / 'fixer.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path, help='New output directory')
    parser.add_argument('--size', type=int, required=True, help='Explicitly agreed target side in pixels')
    args = parser.parse_args()
    try:
        convert(args.source, args.output, args.size)
    except (ValueError, OSError, ImportError) as error:
        parser.exit(1, f'Conversion stopped: {error}\n')
