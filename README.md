# نسخة احتياطية: فيلم «عائلة الناصر» الترويجي / Nasser Family promo film (backup)

Source code for the 135 s, 9:16 (1080×1920, 30 fps) promo film of the Nasser Family platform.
Backup taken 2026-11-24 (film release v4).

## What is here
- `src/` – the whole pipeline in Python (numpy / OpenCV / PIL → ffmpeg):
  - `film.py`, `scenes1.py`, `scenes2.py`, `scenes3.py`, `logo.py` – frame compositor, the 8 scenes, motion-graphics logo
  - `mkcaps.py`, `mkbrand.py` – Arabic captions / brand assets (font: Amiri Quran)
  - `cap_*.py`, `camseq.py`, `boot.py`, `geo.py` – capture of the real app screens with Playwright
  - `render.py` – per-scene render + transitions (`python3 render.py sceneN t0 t1`)
  - `music2.py` – synthesized maqam score (pure numpy/scipy, ~-15 LUFS)
  - `runA10.sh`, `runB10.sh`, `enc4.sh` – the two render workers and the final encodes (WhatsApp ≤16 MB, 1080p)
- `deliver/` – narration script (`.txt`), subtitles (`.srt`) and the film score (`.m4a`)
- `brief/master_prompt.txt` – the original creative brief

## Intentionally NOT in this backup
This repository is public, so the following are kept out of it:
the rendered videos, and the captured app screens / portraits (`assets/`, `seq/`, `caps/`),
because they show family members' faces and the family tree, which the platform itself protects.
Keep those in a private location (e.g. a private repository or cloud drive).

## Rebuild outline
1. Build the platform with the camera hook, capture screens (`cap_*.py`, `camseq.py`) into `assets/`, `seq/`.
2. `python3 mkbrand.py && python3 mkcaps.py` (check every PNG in `caps/` has 4 channels).
3. `python3 music2.py` → `music2.wav`.
4. Render the 8 scenes with `render.py`, concat with `-c copy`, mux the audio, run `enc4.sh`.
