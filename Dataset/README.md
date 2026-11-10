# AITE dataset (live)

Collected continuously by **Prolabs Robotics AITE** - Agent mode, powered by **Parallel Web Technologies** (ProLab Robotics).
This file and `stats.json` are rewritten on every sync.

| | |
|---|---|
| Text records (originals + DataGen variants) | **123,963** (861 originals, 123,102 variants) |
| Web images (free licences, with attribution) | **82** |
| Generated detection images (boxes, polygons, captions, VQA) | **4,680** |
| Robot VLA episodes (frames + actions + instruction) | **4,680** (57,581 frames) |
| Topics explored / known | 386 / 104,782 |
| Approx. text tokens | 56,612,270 |
| Running since | 2026-11-09T21:48:16 |
| Updated | 2026-11-10T07:46:31 |

## Layout
- `text/*.jsonl.gz` - one JSON object per line: `messages` (chat SFT), `problem`, `solution`, `topic`, `source`, `url`, `license`, `quality_score`, DataGen fields.
- `detection/*.jsonl.gz` + `images/synthetic/` - generated scenes: `objects[].bbox` (x, y, w, h px), `polygon`, `caption`, `qa`.
- `images/web/` + `text`-style rows in `detection/` with `type: "image-text"` - Wikimedia Commons images, licence + author kept.
- `vla/*.jsonl.gz` + `images/vla/` - pick-and-place episodes: `instruction`, `steps[].observation`, `steps[].action`.

Licences differ per row (see the `license` field) - some sources are non-commercial (e.g. CC-BY-NC). Filter before commercial use.
