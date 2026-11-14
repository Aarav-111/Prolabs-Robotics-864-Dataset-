# AITE dataset (live)

Collected continuously by **Prolabs Robotics AITE** - Agent mode, powered by **Parallel Web Technologies** (Prolabs Robotics).
This file and `stats.json` are rewritten on every sync.

| | |
|---|---|
| Text records (originals + DataGen variants) | **4,363,183** (24,056 originals, 4,339,127 variants) |
| Web images (free licences, with attribution) | **3,963** |
| Generated detection images (boxes, polygons, captions, VQA) | **14,064** |
| Robot VLA episodes (frames + actions + instruction) | **14,064** (173,566 frames) |
| Topics explored / known | 25,501 / 109,914 |
| Approx. text tokens | 2,276,829,827 |
| Running since | 2026-11-12T17:25:00 |
| Updated | 2026-11-14T11:18:19 |

## Layout
- `text/*.jsonl.gz` - one JSON object per line: `question`, `expected_answer`, `messages` (chat SFT), `problem`, `solution`, `topic`, `source`, `url`, `license`, `quality_score`, DataGen fields. The `text` field is `Question:` then `Expected answer:`.
- `detection/*.jsonl.gz` + `images/synthetic/` - generated scenes: `question`, `expected_answer`, `objects[].bbox` (x, y, w, h px), `polygon`, `caption`, `qa`.
- `images/web/` + rows in `detection/` with `type: "image-text"` - Wikimedia Commons images, licence + author kept. `question` is "Describe this image." and `expected_answer` is the caption.
- `preference/*.jsonl.gz` - `question` is the prompt, `expected_answer` is the chosen answer.
- `vla/*.jsonl.gz` + `images/vla/` - pick-and-place episodes: `question` (the instruction), `expected_answer`, `steps[].observation`, `steps[].action`.

Licences differ per row (see the `license` field) - some sources are non-commercial (e.g. CC-BY-NC). Filter before commercial use.
