# AITE dataset (live)

Collected continuously by **Prolabs Robotics AITE** - Agent mode, powered by **Parallel Web Technologies** (ProLab Robotics).
This file and `stats.json` are rewritten on every sync.

| | |
|---|---|
| Text records (originals + DataGen variants) | **32,733** (332 originals, 32,401 variants) |
| Web images (free licences, with attribution) | **53** |
| Generated detection images (boxes, polygons, captions, VQA) | **804** |
| Robot VLA episodes (frames + actions + instruction) | **800** (9,992 frames) |
| Topics explored / known | 122 / 50,601 |
| Approx. text tokens | 11,497,918 |
| Running since | 2026-11-09T13:11:36 |
| Updated | 2026-11-09T13:12:08 |

## Layout
- `text/*.jsonl.gz` - one JSON object per line: `messages` (chat SFT), `problem`, `solution`, `topic`, `source`, `url`, `license`, `quality_score`, DataGen fields.
- `detection/*.jsonl.gz` + `images/synthetic/` - generated scenes: `objects[].bbox` (x, y, w, h px), `polygon`, `caption`, `qa`.
- `images/web/` + `text`-style rows in `detection/` with `type: "image-text"` - Wikimedia Commons images, licence + author kept.
- `vla/*.jsonl.gz` + `images/vla/` - pick-and-place episodes: `instruction`, `steps[].observation`, `steps[].action`.

Licences differ per row (see the `license` field) - some sources are non-commercial (e.g. CC-BY-NC). Filter before commercial use.
