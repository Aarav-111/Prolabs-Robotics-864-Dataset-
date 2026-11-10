# AITE dataset (live)

Collected continuously by **Prolabs Robotics AITE** - Agent mode, powered by **Parallel Web Technologies** (ProLab Robotics).
This file and `stats.json` are rewritten on every sync.

| | |
|---|---|
| Text records (originals + DataGen variants) | **185,038** (1,149 originals, 183,889 variants) |
| Web images (free licences, with attribution) | **212** |
| Generated detection images (boxes, polygons, captions, VQA) | **14,064** |
| Robot VLA episodes (frames + actions + instruction) | **14,064** (173,566 frames) |
| Topics explored / known | 1,153 / 109,912 |
| Approx. text tokens | 85,683,122 |
| Running since | 2026-11-10T08:16:47 |
| Updated | 2026-11-10T08:17:18 |

## Layout
- `text/*.jsonl.gz` - one JSON object per line: `messages` (chat SFT), `problem`, `solution`, `topic`, `source`, `url`, `license`, `quality_score`, DataGen fields.
- `detection/*.jsonl.gz` + `images/synthetic/` - generated scenes: `objects[].bbox` (x, y, w, h px), `polygon`, `caption`, `qa`.
- `images/web/` + `text`-style rows in `detection/` with `type: "image-text"` - Wikimedia Commons images, licence + author kept.
- `vla/*.jsonl.gz` + `images/vla/` - pick-and-place episodes: `instruction`, `steps[].observation`, `steps[].action`.

Licences differ per row (see the `license` field) - some sources are non-commercial (e.g. CC-BY-NC). Filter before commercial use.
