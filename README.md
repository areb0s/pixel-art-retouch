# fixer-local-retouch

Project-local Pi skill for source-preserving pixel-art conversion and human-selected local retouching. No game integration, generation service, model download, automatic installation or global registration.

## Local placement and runtime

Place this directory at `<project>/.pi/skills/fixer-local-retouch/` (keep `SKILL.md` at its root). Review the skill before granting project trust. Pi discovers project skills; invoke `/skill:fixer-local-retouch` when needed. No npm package or settings change is required.

Use an existing Python interpreter with Pillow, NumPy, SciPy and OpenCV available; retouch alone requires Pillow. Check imports first and stop/report missing dependencies rather than installing or creating an environment. `vendor/requirements.txt` preserves upstream dependency information, not an automatic setup step. Local smoke validation used Python 3.13.7, Pillow 11.1.0, NumPy 2.2.1, SciPy 1.15.0 and OpenCV 4.13.0; this is not a universal version guarantee.

Read [SKILL.md](SKILL.md) for scope and preservation rules. From this directory, set `PY` to the verified existing executable, then use fresh output directories outside the package:

```bash
"$PY" -B -c 'import PIL, numpy, scipy, cv2'
"$PY" -B -X utf8 scripts/convert.py SOURCE_RGBA NEW_CONVERSION_DIRECTORY --size AGREED_SIZE
"$PY" -B -X utf8 scripts/retouch.py BASELINE REFERENCE PATCH_JSON NEW_RETOUCH_DIRECTORY \
  --baseline-sha SHA256 --region LEFT TOP RIGHT BOTTOM
```

Conversion expects square RGBA input. Choose size and edits for the current asset. Patch entries contain `x`, `y`, `before` and `after` RGBA. Retouch enforces baseline hash, existing pixels, unique coordinates, region bounds, palette and alpha preservation. Do not overwrite originals or weaken guards. Inspect resulting images as well as preservation evidence; a smoke test does not establish artistic quality.

## Included / excluded

Included: skill instructions, three Python scripts (`convert.py`, `retouch.py` and synthetic-focused `test_workflow.py`), pinned vendored Fixer source, manifest, upstream documentation and license. Excluded: original project images/docs, game code/assets/config/saves, generated outputs, caches and credentials.

`convert.py` and `retouch.py` work on user-supplied inputs. Run `"$PY" -B -m unittest scripts.test_workflow` from this directory for self-contained synthetic checks of conversion repeatability, input guards and retouch preservation/rejection behavior. Temporary fixtures are created outside the package. These checks do not establish artistic quality.

## Provenance and license boundary

Vendored upstream: [Retro-Diffusion/pixel-art-fixer](https://github.com/Retro-Diffusion/pixel-art-fixer), commit `ef376e57e1c272633ca2dbf5f29ec3fcf6596465`. [vendor/manifest.json](vendor/manifest.json) binds the upstream files by SHA-256. All vendor files and `scripts/retouch.py` are preserved byte-for-byte from the source skill.

The MIT notice in [vendor/LICENSE](vendor/LICENSE) applies to the vendored upstream material only. No license is asserted here for the local wrapper scripts, skill instructions or packaging documents; this repository as a whole is not represented as MIT-licensed. Upstream README image links are references, not bundled game assets.
