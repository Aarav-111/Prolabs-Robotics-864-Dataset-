<p align="center">
<img src="assets/aite-banner.svg" alt="AITE banner" width="100%">
</p>

<p align="center">
<img src="https://img.shields.io/badge/by-Prolabs%20Robotics-6366f1?style=flat-square" alt="Prolabs Robotics">
<img src="https://img.shields.io/badge/Output-PDF%20%7C%20TXT%20%7C%20JSON-22d3ee?style=flat-square" alt="Output formats">
<img src="https://img.shields.io/badge/DataGen-10%20styles%20x%2011%20formats-818cf8?style=flat-square" alt="DataGen">
<img src="https://img.shields.io/badge/Answers-verified%20with%20SymPy-22c55e?style=flat-square" alt="SymPy verified">
<img src="https://img.shields.io/badge/Agent%20mode-runs%2024%2F7-f59e0b?style=flat-square" alt="Agent mode runs 24/7">
<img src="https://img.shields.io/badge/Trainer-on%20your%20Mac%20(MLX)-10a37f?style=flat-square" alt="Trainer on your Mac">
<img src="https://img.shields.io/badge/API%20keys-none-64748b?style=flat-square" alt="No API keys">
<img src="https://img.shields.io/badge/License-MIT-6366f1?style=flat-square" alt="License: MIT">
</p>

<p align="center">
<b>Overview</b> &nbsp;|&nbsp; <b>Three modes</b> &nbsp;|&nbsp; <b>How it works</b> &nbsp;|&nbsp; <b>Agent mode</b> &nbsp;|&nbsp; <b>Sources</b> &nbsp;|&nbsp; <b>DataGen</b> &nbsp;|&nbsp; <b>Train a model</b> &nbsp;|&nbsp; <b>Setup</b> &nbsp;|&nbsp; <b>Why AITE</b>
</p>

---

## Overview

> AITE (Artificial Intelligence Training Environment) by Prolabs Robotics is the world's biggest dataset generator for LLM training.

AITE finds problems and solutions across the internet, keeps only the best ones, and multiplies them into large training datasets that are ready to use.

The data it collects lives right here, in [`Dataset/`](Dataset). Agent mode updates it every 5 minutes, and the live numbers are in [`Dataset/README.md`](Dataset/README.md) and [`Dataset/stats.json`](Dataset/stats.json).

---

## Three Modes

| Mode | For | What it does |
| --- | --- | --- |
| **Agent** (default) | building a big dataset | Runs non-stop, collecting text, images and robot data on endless topics. It can only be paused, never stopped. |
| **Manual** | one exact dataset | Choose topics, quantity and quality, preview the result, then export one PDF, TXT or JSON file. |
| **Trainer** | your own AI model | Teaches an open AI model on your Mac with the collected data. No code needed. |

---

## How It Works

<p align="center">
<img src="assets/aite-pipeline.svg" alt="AITE pipeline: input, web search, filter, DataGen, output" width="100%">
</p>

| Step | Stage | What happens |
| --- | --- | --- |
| 1 | **Input** | Pick your topics, how many records you want, the quality level and a file type (PDF, TXT or JSON). |
| 2 | **Web search** | Collects material from Stack Exchange, Hugging Face, Wikibooks, arXiv, OpenAlex, Wikipedia and DuckDuckGo. |
| 3 | **Filter** | Scores every item and removes spam, duplicates, unanswered questions and off-topic content. |
| 4 | **DataGen** | Each record becomes many new versions (see below). |
| 5 | **Output** | Preview everything, then export one combined, training-ready file. |

---

## Agent Mode

Press **Start collecting** once. After that, AITE keeps building the dataset by itself, even while its window is closed, until you press **Pause**.

- **Endless topics.** A built-in map of the sciences, then OpenAlex's catalogue of about 4,500 research topics, then Wikipedia's links between ideas. Add your own *focus topics* to go first.
- **Training-ready data.**
  - **Text:** chat-format question/answer rows, plus a plain `text` field, a fixed train/validation split, token counts, a quality tier and the source licence.
  - **Web images:** free-licence images from Wikimedia Commons, each with its caption, author and licence.
  - **Generated images:** scenes with exact object boxes, outlines, captions and question/answer pairs, for object recognition.
  - **Robot VLA episodes:** pick-and-place runs with frames, actions and an instruction, for vision-language-action models.
- **Parallel Web Technologies** (by ProLab Robotics). Hundreds of tasks run at once across many sites and topics, and every site keeps its own polite rate limit.
- **Live stats.** CPU, memory, network and counts appear on screen every second and are pushed to this repo every 5 minutes.
- **Settings on the page.** Quality, records per topic, DataGen variations, CPU cap, data types and focus topics. Changes apply immediately.

---

## Sources

<p align="center">
<img src="assets/aite-sources.svg" alt="Sources: Stack Exchange, Hugging Face, Wikibooks, arXiv, OpenAlex, Wikipedia, DuckDuckGo" width="100%">
</p>

---

## DataGen

<p align="center">
<img src="assets/aite-datagen.svg" alt="DataGen turns one record into many versions" width="100%">
</p>

Each good record becomes many new versions:

- **New numbers**, re-solved with SymPy so every answer stays correct.
- **Swapped names and items**, and synonyms.
- **10 writing styles x 11 formats.**

---

## Train a Model

Open the **Trainer** page and follow its six steps: get the trainer, choose a model, check your data, train, try it, keep it.

AITE fine-tunes an open model (Qwen 2.5 or Llama 3.2) **on your Mac** with Apple's MLX: no code, no cloud, no API keys. The **Try it** step compares the model's answers before and after training. The finished model opens in LM Studio.

The full guide, in plain words plus a technical blueprint (data prep, SFT, DPO, evaluation, vision and robot models, cloud GPUs), is in **[TRAINING_BLUEPRINT.md](TRAINING_BLUEPRINT.md)**.

---

## Setup

```bash
git clone https://github.com/Aarav-111/Prolabs-Robotics-864-Dataset-.git
cd Prolabs-Robotics-864-Dataset-
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app/AITE.py                 # the app (Agent page opens first)
```

| Command | What it does |
| --- | --- |
| `python app/AITE.py` | Opens the app. |
| `python app/AITE.py --agent` | Agent mode without a window (e.g. on a server). |
| `python app/AITE.py --train --iters 200` | The Trainer without a window (Mac with Apple silicon). |
| `python app/AITE.py --run '{"topics":["algebra"],"quantity":10}' --out data.json` | One Manual-mode run. |
| `python app/AITE.py --selftest` | Offline self-test. |

**Pushing the dataset to GitHub.** Agent mode commits `Dataset/` to `main` every 5 minutes. Pushing uses your normal git login. Otherwise, put a GitHub token with *Contents: read and write* permission in `app/github_token.txt`; that file is never committed. To push somewhere else, change the repository link in **Settings > GitHub**.

---

## Why AITE

| Need | How AITE handles it |
| --- | --- |
| Scale | One good record is multiplied into many versions. |
| Quality | Spam, duplicates, unanswered questions and off-topic items are removed before anything is multiplied. |
| Correct answers | Changed numbers are re-solved with SymPy. |
| Variety | 10 writing styles and 11 formats per record. |
| Ready to use | Preview, then export one combined file as PDF, TXT or JSON. |
| Never stops | Agent mode collects day and night and only pauses when you say so. |
| Your own model | The Trainer turns the data into a fine-tuned model on your Mac. |
| Private and free | No API keys, no paid services; the trainer runs locally. |

---

<p align="center">
<b>AITE</b> by Prolabs Robotics<br>
<a href="mailto:prolabsrobotics@gmail.com">prolabsrobotics@gmail.com</a>
</p>
