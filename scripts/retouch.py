"""Apply visually chosen, exact pixel edits; never decide edits automatically."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps


def retouch(baseline, reference, patches, output, baseline_sha, region):
    if output.exists():
        raise ValueError('Output directory already exists; use a fresh directory.')
    digest = hashlib.sha256(baseline.read_bytes()).hexdigest()
    if digest != baseline_sha:
        raise ValueError('Baseline SHA-256 mismatch; do not apply this patch to another image.')
    before = Image.open(baseline)
    if before.mode != 'RGBA':
        raise ValueError('Baseline must be RGBA.')
    before.load()
    source = Image.open(reference).convert('RGBA')
    left, top, right, bottom = region
    if not (0 <= left < right <= before.width and 0 <= top < bottom <= before.height):
        raise ValueError('Region must be an in-bounds [left, top, right, bottom) rectangle.')
    changes = json.loads(patches.read_text(encoding='utf-8'))
    if not isinstance(changes, list) or not changes:
        raise ValueError('Patch must be a nonempty JSON list of x/y/before/after records.')
    palette = {p for p in before.getdata() if p[3] > 0}
    expected = set()
    after = before.copy()
    for change in changes:
        if not isinstance(change, dict) or not {'x', 'y', 'before', 'after'} <= change.keys():
            raise ValueError('Each patch entry needs x, y, before and after.')
        x, y = change['x'], change['y']
        if type(x) is not int or type(y) is not int or not (left <= x < right and top <= y < bottom):
            raise ValueError('Patch coordinate is outside the agreed region or is not an integer.')
        if (x, y) in expected:
            raise ValueError('Duplicate patch coordinate.')
        for key in ('before', 'after'):
            color = change[key]
            if not isinstance(color, list) or len(color) != 4 or any(type(v) is not int or not 0 <= v <= 255 for v in color):
                raise ValueError('Colors must be four integer RGBA channels in 0..255.')
        old, new = tuple(change['before']), tuple(change['after'])
        if old != before.getpixel((x, y)) or old == new:
            raise ValueError('Old pixel mismatch or no-op patch.')
        if old[3] != 255 or new[3] != old[3] or new not in palette:
            raise ValueError('Only opaque pixels and existing colors may be used; alpha is locked.')
        after.putpixel((x, y), new)
        expected.add((x, y))
    output.mkdir(parents=True, exist_ok=False)
    (output / 'before.png').write_bytes(baseline.read_bytes())
    after.save(output / 'retouched.png')
    (output / 'pixel-changes.json').write_bytes(patches.read_bytes())
    with Image.open(output / 'retouched.png') as exported:
        actual = {(x, y) for y in range(before.height) for x in range(before.width)
                  if exported.getpixel((x, y)) != before.getpixel((x, y))}
        if (actual != expected or exported.tobytes() != after.tobytes()
                or exported.getchannel('A').tobytes() != before.getchannel('A').tobytes()):
            raise ValueError('Export verification failed; retain output for diagnosis, do not accept it.')

    def preview(image, scale):
        bg = Image.new('RGBA', image.size, '#ded8cc')
        bg.alpha_composite(image)
        return bg.convert('RGB').resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)

    panel = max(384, before.width, before.height)
    scale = max(1, panel // max(before.size))
    ref = preview(source, max(1, panel // max(source.size)))
    if max(ref.size) > panel:
        ref = ImageOps.contain(ref, (panel, panel), Image.Resampling.LANCZOS)
    board = Image.new('RGB', ((panel + 32) * 3, panel + 85 + before.height), '#eeeae2')
    draw = ImageDraw.Draw(board)
    for i, (label, image) in enumerate([
        ('ORIGINAL REFERENCE', ref), ('BEFORE / FIXER', preview(before, scale)),
        (f'AFTER / {len(actual)} PIXELS EDITED', preview(after, scale)),
    ]):
        x = 16 + i * (panel + 32)
        draw.text((x, 16), label, fill='#28231d')
        board.paste(image, (x + (panel - image.width) // 2, 50 + (panel - image.height) // 2))
    for i, image in enumerate([before, after]):
        board.paste(preview(image, 1), (16 + (i + 1) * (panel + 32), panel + 71))
    board.save(output / 'comparison.png')
    diff = Image.new('RGB', before.size, '#ded8cc')
    for xy in actual:
        diff.putpixel(xy, (210, 30, 115))
    diff.resize((before.width * scale, before.height * scale), Image.Resampling.NEAREST).save(output / 'changed-pixels.png')
    report = {
        'status': 'pixel_preservation_verified', 'quality': 'requires human visual review',
        'baseline_sha256': digest,
        'reference_sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
        'result_sha256': hashlib.sha256((output / 'retouched.png').read_bytes()).hexdigest(),
        'size': list(before.size), 'allowed_region': list(region),
        'changed_pixels': len(actual), 'unchanged_pixels': before.width * before.height - len(actual),
        'alpha_unchanged': True, 'silhouette_unchanged': True,
        'no_new_colors': True, 'outside_patch_unchanged_including_hidden_rgb': True,
    }
    (output / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('reference', type=Path)
    parser.add_argument('patches', type=Path)
    parser.add_argument('output', type=Path, help='New output directory')
    parser.add_argument('--baseline-sha', required=True)
    parser.add_argument('--region', type=int, nargs=4, required=True, metavar=('LEFT', 'TOP', 'RIGHT', 'BOTTOM'))
    args = parser.parse_args()
    try:
        retouch(args.baseline, args.reference, args.patches, args.output, args.baseline_sha, args.region)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Retouch stopped: {error}\n')
