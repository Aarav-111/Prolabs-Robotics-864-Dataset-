# AITE dataset (live)

Collected continuously by **Prolabs Robotics AITE** - Agent mode, powered by **Parallel Web Technologies** (Prolabs Robotics).
This file and `stats.json` are rewritten on every sync.

| | |
|---|---|
| Text records (originals + DataGen variants) | **4,986,658** (27,465 originals, 4,959,193 variants) |
| Web images (free licences, with attribution) | **4,891** |
| Generated detection images (boxes, polygons, captions, VQA) | **14,064** |
| Robot VLA episodes (frames + actions + instruction) | **14,064** (173,566 frames) |
| Topics explored / known | 27,437 / 109,914 |
| Approx. text tokens | 2,542,525,058 |
| Running since | 2026-11-12T17:25:00 |
| Updated | 2026-11-14T13:27:24 |

## Layout
- `text/*.jsonl.gz` - one JSON object per line: `question`, `expected_answer`, `messages` (chat SFT), `problem`, `solution`, `topic`, `source`, `url`, `license`, `quality_score`, DataGen fields. The `text` field is `Question:` then `Expected answer:`.
- `detection/*.jsonl.gz` + `images/synthetic/` - generated scenes: `question`, `expected_answer`, `objects[].bbox` (x, y, w, h px), `polygon`, `caption`, `qa`.
- `images/web/` + rows in `detection/` with `type: "image-text"` - Wikimedia Commons images, licence + author kept. `question` is "Describe this image." and `expected_answer` is the caption.
- `preference/*.jsonl.gz` - `question` is the prompt, `expected_answer` is the chosen answer.
- `vla/*.jsonl.gz` + `images/vla/` - pick-and-place episodes: `question` (the instruction), `expected_answer`, `steps[].observation`, `steps[].action`.

Licences differ per row (see the `license` field) - some sources are non-commercial (e.g. CC-BY-NC). Filter before commercial use.
