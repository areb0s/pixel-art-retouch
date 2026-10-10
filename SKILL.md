---
name: fixer-local-retouch
description: Use when creating or refining pixel art and game sprites while preserving the supplied design. Prepare the source, convert it to a Fixer grid, compare with the original, apply human-selected local pixel edits, and verify preservation. Not for full regeneration or independent redesign.
compatibility: Python with Pillow, NumPy, SciPy and OpenCV. Fixer source and MIT license are bundled; no network, model download or automatic installation.
---

# Fixer conversion + local pixel retouch

**Automatic conversion preserves the source shape and colors as a starting point. Final improvements require comparing the original and selecting edits with human judgment.** Even a few changed pixels can materially alter expression and character.

## Scope and baseline

- The user-specified original is the design authority. Do not replace it with a generated alternative character.
- Confirm the target resolution, allowed edit region and output count from the current request. Do not ask again about settled choices.
- Never overwrite originals or baselines. Save new results in a fresh directory at the agreed output location. Do not expand scope, install dependencies, download models, animate or integrate into a game without authorization.

## Runtime

- Paths below are relative to the directory containing this `SKILL.md`. Resolve them to absolute paths before use.
- Find and verify an existing Python executable. Prefix script commands with that interpreter and `-B -X utf8`; for example, `"$PY" -B -X utf8 scripts/convert.py ...`, where `PY` is its path.
- Check imports first: conversion requires Pillow, NumPy, SciPy and OpenCV; retouch alone requires Pillow.
- Report missing dependencies or execution errors and stop. Do not automatically install, create a new environment or substitute another algorithm.
- `vendor/` is a fixed copy of Fixer. Preserve its [pinned manifest](vendor/manifest.json) and [upstream license](vendor/LICENSE). No global registration or pip installation is needed.

## Workflow

### 1. Confirm source and scope

Actually open the original, any available baseline, and the proposed edit region. Describe specific discrepancies, such as eye-cluster shape or moustache boundaries. Record source and baseline SHA-256 hashes, and make a separate working copy. Protect only the selected inputs with a unique temporary backup and hash list.

### 2. Prepare the source

Visually verify the crop and transparency mask. Preserve proportions and add only necessary padding to produce square RGBA input. Do not stretch or distort. Distinguish background/ground-shadow removal from design changes.

### 3. Convert with Fixer (when no approved baseline exists)

`scripts/convert.py SOURCE_RGBA NEW_OUTPUT_DIRECTORY --size AGREED_SIZE`

- Extend transparent RGB from the nearest opaque color to avoid sampling fringes.
- Use Fixer `process(..., force_step=source_side/target_side)` for the agreed grid. Do not describe this as automatic resolution detection.
- Build a median-cut palette of at most 32 colors from opaque source pixels, then apply it without dithering.
- Area-downsample source alpha and binarize it at `>=128`.
- Inspect `fixer.png` and conversion metadata. These are not yet artistically approved results.
- If an approved baseline already exists, start from its copy rather than reconverting.

### 4. Compare and retouch locally

Compare the source and baseline at native size and integer nearest-neighbor enlargement. Select only necessary pixels inside the agreed region and describe them in a JSON list. Each entry has `x`, `y`, `before` RGBA and `after` RGBA; include the selection rationale in fields such as `region`.

`scripts/retouch.py BASELINE REFERENCE PATCH_JSON NEW_OUTPUT_DIRECTORY --baseline-sha SHA256 --region LEFT TOP RIGHT BOTTOM`

Right and bottom bounds are exclusive. The tool checks baseline hash, existing pixel values, duplicate coordinates, region violations, new colors and alpha changes. On rejection, reconsider the source and plan; do not force the patch or weaken checks.

Whole-image filters, full-body repainting and palette replacement are not local retouching. Do not broaden the scope even if more work seems useful.

### 5. Separate preservation checks from visual evaluation

- Reopen the saved PNG and confirm that exactly the planned pixels changed.
- Preserve dimensions, alpha, silhouette, existing palette and all pixels outside the patch, **including hidden RGB in transparent pixels**.
- Inspect generated `comparison.png`, `changed-pixels.png` and `validation.json`. Composite previews onto a neutral background before enlargement.
- Actually open source/before/after images to assess facial readability and fidelity to the original impression. Add enlarged regional comparisons if needed. Pixel validity or edit count is not a substitute for artistic quality.
- Record user evaluation separately. Positive feedback does not automatically authorize further edits or game integration.

## Completion report

Briefly report output paths, comparison images, edit region/count, preservation verification and whether the user evaluated the result. On failure, report the exact error and remaining outputs without overwriting earlier evidence. New installation or further retouching requires a separate request.
