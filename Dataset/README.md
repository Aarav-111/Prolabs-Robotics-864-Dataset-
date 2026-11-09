# AITE dataset (live)

Collected continuously by **Prolabs Robotics AITE** - Agent mode, powered by **Parallel Web Technologies** (ProLab Robotics).
This file and `stats.json` are rewritten on every sync.

| | |
|---|---|
| Text records (originals + DataGen variants) | **39,773** (387 originals, 39,386 variants) |
| Web images (free licences, with attribution) | **76** |
| Generated detection images (boxes, polygons, captions, VQA) | **4,224** |
| Robot VLA episodes (frames + actions + instruction) | **4,224** (52,029 frames) |
| Topics explored / known | 146 / 102,494 |
| Approx. text tokens | 14,352,783 |
| Running since | 2026-11-09T21:48:16 |
| Updated | 2026-11-09T21:48:48 |

## Layout
- `text/*.jsonl.gz` - one JSON object per line: `messages` (chat SFT), `problem`, `solution`, `topic`, `source`, `url`, `license`, `quality_score`, DataGen fields.
- `detection/*.jsonl.gz` + `images/synthetic/` - generated scenes: `objects[].bbox` (x, y, w, h px), `polygon`, `caption`, `qa`.
- `images/web/` + `text`-style rows in `detection/` with `type: "image-text"` - Wikimedia Commons images, licence + author kept.
- `vla/*.jsonl.gz` + `images/vla/` - pick-and-place episodes: `instruction`, `steps[].observation`, `steps[].action`.

Licences differ per row (see the `license` field) - some sources are non-commercial (e.g. CC-BY-NC). Filter before commercial use.
