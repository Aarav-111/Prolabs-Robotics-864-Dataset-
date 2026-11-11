# AITE dataset (live)

Collected continuously by **Prolabs Robotics AITE** - Agent mode, powered by **Parallel Web Technologies** (Prolabs Robotics).
This file and `stats.json` are rewritten on every sync.

| | |
|---|---|
| Text records (originals + DataGen variants) | **526,596** (2,962 originals, 523,634 variants) |
| Web images (free licences, with attribution) | **468** |
| Generated detection images (boxes, polygons, captions, VQA) | **14,064** |
| Robot VLA episodes (frames + actions + instruction) | **14,064** (173,566 frames) |
| Topics explored / known | 2,812 / 109,914 |
| Approx. text tokens | 268,218,852 |
| Running since | 2026-11-11T11:27:36 |
| Updated | 2026-11-11T11:47:20 |

## Layout
- `text/*.jsonl.gz` - one JSON object per line: `messages` (chat SFT), `problem`, `solution`, `topic`, `source`, `url`, `license`, `quality_score`, DataGen fields.
- `detection/*.jsonl.gz` + `images/synthetic/` - generated scenes: `objects[].bbox` (x, y, w, h px), `polygon`, `caption`, `qa`.
- `images/web/` + `text`-style rows in `detection/` with `type: "image-text"` - Wikimedia Commons images, licence + author kept.
- `vla/*.jsonl.gz` + `images/vla/` - pick-and-place episodes: `instruction`, `steps[].observation`, `steps[].action`.

Licences differ per row (see the `license` field) - some sources are non-commercial (e.g. CC-BY-NC). Filter before commercial use.
