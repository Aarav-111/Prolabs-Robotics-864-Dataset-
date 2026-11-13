# AITE dataset (live)

Collected continuously by **Prolabs Robotics AITE** - Agent mode, powered by **Parallel Web Technologies** (Prolabs Robotics).
This file and `stats.json` are rewritten on every sync.

| | |
|---|---|
| Text records (originals + DataGen variants) | **2,673,393** (14,616 originals, 2,658,777 variants) |
| Web images (free licences, with attribution) | **1,967** |
| Generated detection images (boxes, polygons, captions, VQA) | **14,064** |
| Robot VLA episodes (frames + actions + instruction) | **14,064** (173,566 frames) |
| Topics explored / known | 14,268 / 109,914 |
| Approx. text tokens | 1,459,008,546 |
| Running since | 2026-11-12T17:25:00 |
| Updated | 2026-11-13T08:59:54 |

## Layout
- `text/*.jsonl.gz` - one JSON object per line: `question`, `expected_answer`, `messages` (chat SFT), `problem`, `solution`, `topic`, `source`, `url`, `license`, `quality_score`, DataGen fields. The `text` field is `Question:` then `Expected answer:`.
- `detection/*.jsonl.gz` + `images/synthetic/` - generated scenes: `question`, `expected_answer`, `objects[].bbox` (x, y, w, h px), `polygon`, `caption`, `qa`.
- `images/web/` + rows in `detection/` with `type: "image-text"` - Wikimedia Commons images, licence + author kept. `question` is "Describe this image." and `expected_answer` is the caption.
- `preference/*.jsonl.gz` - `question` is the prompt, `expected_answer` is the chosen answer.
- `vla/*.jsonl.gz` + `images/vla/` - pick-and-place episodes: `question` (the instruction), `expected_answer`, `steps[].observation`, `steps[].action`.

Licences differ per row (see the `license` field) - some sources are non-commercial (e.g. CC-BY-NC). Filter before commercial use.
