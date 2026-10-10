"""Focused offline checks using unique synthetic temporary fixtures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


convert = load('convert').convert
retouch = load('retouch').retouch


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fixer_skill_test_')
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.baseline = self.dir / 'baseline.png'
        image = Image.new('RGBA', (16, 16), (200, 100, 40, 255))
        image.putpixel((5, 5), (20, 20, 20, 255))
        image.putpixel((0, 0), (89, 77, 66, 0))  # preserve hidden RGB
        image.save(self.baseline)
        self.sha = hashlib.sha256(self.baseline.read_bytes()).hexdigest()
        self.patch = self.dir / 'patch.json'
        self.changes = [{'x': 6, 'y': 5, 'before': [200, 100, 40, 255], 'after': [20, 20, 20, 255]}]

    def apply(self, changes=None, sha=None, region=(4, 4, 8, 8)):
        self.patch.write_text(json.dumps(self.changes if changes is None else changes), encoding='utf-8')
        retouch(self.baseline, self.baseline, self.patch, self.dir / 'output', sha or self.sha, region)

    def test_exact_patch_and_hidden_rgb(self):
        self.apply()
        before = Image.open(self.baseline)
        after = Image.open(self.dir / 'output/retouched.png')
        actual = {(x, y) for y in range(16) for x in range(16) if before.getpixel((x, y)) != after.getpixel((x, y))}
        self.assertEqual(actual, {(6, 5)})
        self.assertEqual(after.getpixel((0, 0)), (89, 77, 66, 0))
        self.assertEqual(before.getchannel('A').tobytes(), after.getchannel('A').tobytes())
        original = (self.dir / 'output/retouched.png').read_bytes()
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual((self.dir / 'output/retouched.png').read_bytes(), original)

    def test_reject_invalid_patches_without_output(self):
        c = self.changes[0]
        cases = [[], {}, [c, c], [{**c, 'x': 2}], [{**c, 'x': True}],
                 [{**c, 'before': [0, 0, 0, 255]}], [{**c, 'after': c['before']}],
                 [{**c, 'after': [1, 2, 3, 255]}], [{**c, 'after': [20, 20, 20, 0]}],
                 [{**c, 'after': [20, 20, 20]}], [{'x': 5}], ['bad']]
        for value in cases:
            with self.subTest(patch=value):
                with self.assertRaises(ValueError):
                    self.apply(value)
                self.assertFalse((self.dir / 'output').exists())

    def test_reject_wrong_hash_and_region(self):
        with self.assertRaises(ValueError):
            self.apply(sha='0' * 64)
        with self.assertRaises(ValueError):
            self.apply(region=(-1, 0, 16, 16))
        self.assertFalse((self.dir / 'output').exists())

    def test_reject_unreviewed_conversion(self):
        for mode, size, color in [('RGB', (16, 16), 'red'), ('RGBA', (16, 17), 'red'),
                                   ('RGBA', (16, 16), (1, 2, 3, 100)),
                                   ('RGBA', (16, 16), (1, 2, 3, 0))]:
            image = self.dir / 'unreviewed.png'
            Image.new(mode, size, color).save(image)
            with self.assertRaises(ValueError):
                convert(image, self.dir / 'conversion', 8)
            self.assertFalse((self.dir / 'conversion').exists())

    def test_normal_conversion_is_repeatable(self):
        convert(self.baseline, self.dir / 'first', 8)
        convert(self.baseline, self.dir / 'second', 8)
        self.assertEqual((self.dir / 'first/fixer.png').read_bytes(), (self.dir / 'second/fixer.png').read_bytes())



if __name__ == '__main__':
    unittest.main(verbosity=2)
