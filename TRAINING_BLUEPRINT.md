# How to train an AI model with AITE data

This guide has two parts:

- **Part 1 (everyone):** train a model in a few clicks, without writing code.
- **Part 2 (technical users):** the full blueprint for turning an existing open model into a much stronger specialist.

---

## Part 1 - For everyone

### What "training" means here

You don't build an AI from nothing; that costs millions. You start from a good open model (Qwen, Llama and others) and
**teach it more** with your own examples. Each AITE example is a question with a correct, worked answer. The model
studies the examples again and again until it answers similar questions the same way. This is called *fine-tuning*.

### The easy way: the Trainer page in AITE (Mac with Apple silicon)

1. Open AITE and click **Trainer** at the top.
2. **Get the trainer.** One click downloads Apple's free MLX training tools (about 0.5 GB, once) into AITE's own folder.
3. **Choose a model.** *Small* trains in minutes; bigger models learn more but need more memory. AITE tells you what fits your Mac.
4. **Your data.** AITE counts the examples collected by Agent mode. Pick how long to train: *Quick test*, *Short*, *Normal* or *Long*.
5. **Train.** Press **Start training** and watch the "mistakes" line go down. You can keep using the Mac, and closing AITE does not stop it.
6. **Try it.** Ask a question and compare the answer **before** and **after** training.
7. **Keep your model.** **Save as a standalone model** creates one folder you can open in the free app *LM Studio*.

Tips:

- Collect first. A few hundred examples make a visible difference; thousands make a strong one.
- If the blue dashed line (the check on unseen examples) stops going down while the ink line keeps falling, the model is memorising. Train shorter next time.
- **Quality beats quantity.** In step 3, try *High quality* only.

### No Mac with Apple silicon?

Use the same data with free online notebooks (Google Colab, Kaggle) or a rented GPU. Part 2 shows how, and the
dataset files work as they are.

---

## Part 2 - Technical blueprint

### 2.1 What AITE produces

All files are under `Dataset/` (in the GitHub repo and locally). Each shard is gzip JSONL.

| Folder | One row is | Use it for |
|---|---|---|
| `text/*.jsonl.gz` | `messages` (chat), `text` (plain), `problem`, `solution`, `topic`, `source`, `url`, `license`, `quality_tier`, `split`, `tokens`, DataGen fields (`style`, `format`, `answer`, `variant_of`) | SFT (`messages`), continued pre-training (`text`), preference pairs |
| `detection/*.jsonl.gz` + `images/synthetic/` | an image + `objects[]` with `bbox` [x, y, w, h], `polygon`, `label` + `caption` + `qa` | object detection / segmentation, VLM grounding and VQA |
| `detection/*.jsonl.gz` (`type: image-text`) + `images/web/` | a Wikimedia Commons image + caption + licence + author | VLM captioning |
| `vla/*.jsonl.gz` + `images/vla/` | `instruction`, `steps[]` with `observation.image`, `gripper_xy`, `action {dx, dy, grip, terminate}` | vision-language-action policies |
| `stats.json`, `stats/history.csv` | live counts | monitoring |

Built-in hygiene:

- Duplicates are removed globally across all workers and runs.
- Hugging Face **test and validation splits are never used**, so GSM8K-test and MATH-test stay clean for evaluation.
- Every variant with changed numbers is **re-solved with SymPy**.
- The `split` field is assigned per *original* record, so a record and its variants never leak across train and validation.

### 2.2 The training recipe (from an existing model to a specialist)

**Stage 0 - Prepare the data**

1. Filter by licence. Some rows are CC-BY-NC (non-commercial), e.g. camel-ai and SciQ. Drop them if the model will be used commercially: `row["license"]`.
2. Filter by `quality_tier` (start with `high` + `medium`) and decide on DataGen variants. Variants teach robustness to wording, but keep originals at 30% or more of the mix.
3. Mix in **general data (10-30%)**, e.g. a slice of a general instruction set, so the model does not forget everyday skills ("catastrophic forgetting").
4. Keep AITE's `validation` split aside. Also hold out whole **topics** to measure generalisation.

**Stage 1 (optional) - Continued pre-training (CPT) on `text`**

- Teaches domain knowledge and style. It only pays off with a lot of tokens (hundreds of millions or more). Run Agent mode for days to weeks, or combine with other open corpora.
- Learning rate about 1e-5 to 5e-5 (full) with warm-up, 1 epoch, sequence packing, plus 20-50% replay of general text.

**Stage 2 - Supervised fine-tuning (SFT) on `messages`** (the main step)

- LoRA or QLoRA for small budgets; full fine-tuning on big GPUs.
- Starting hyper-parameters (adjust using the validation loss):

| Model size | Method | LR | LoRA rank / layers | Batch (eff.) | Epochs |
|---|---|---|---|---|---|
| 0.5-1.5B | LoRA | 1e-4 (PEFT) / 1e-5 (mlx-lm default) | r=16, all linear / 8-16 layers | 16-32 | 2-3 |
| 3-8B | QLoRA 4-bit | 1e-4 to 2e-4 | r=16-64 | 32-64 | 1-3 |
| 8-70B | QLoRA or full (multi-GPU) | 1e-5 (full) / 1e-4 (LoRA) | r=64 | 64-128 | 1-2 |

- Mask the prompt (train on answers only); AITE's Trainer does this by default.
- Use the base model's own chat template; the `messages` field fits every modern template.

**Stage 3 - Preference tuning (DPO / ORPO / KTO)**

- AITE data contains natural *chosen / rejected* pairs. Multiple-choice variants carry the correct answer and SymPy-checked wrong *distractors*.
- Build pairs as `chosen` = the worked solution and `rejected` = the same solution ending in a distractor (or a sample from the SFT model that gets the answer wrong).
- Train DPO with beta about 0.1 and LR about 5e-7 to 5e-6 for 1 epoch. Correctness is checkable, so you can also run **RL with verifiable rewards** (GRPO) on the `answer` field.

**Stage 4 - Evaluate**

- AITE validation loss and accuracy on held-out topics.
- Standard benchmarks with `lm-evaluation-harness`: GSM8K (test), MATH, MMLU-STEM, ARC, HumanEval/MBPP-test. AITE never trains on those test splits.
- Compare against the starting model, and check general ability did not drop (MMLU, IFEval).

### 2.3 Hardware guide

| Hardware | What you can train |
|---|---|
| Mac M1/M2 with 8 GB | LoRA on 0.5-1.5B models (AITE Trainer) |
| Mac with 16-24 GB | LoRA on 3B, QLoRA on 7-8B (slow) |
| Mac with 32-64 GB | LoRA on 7-14B |
| 1x 24 GB GPU (RTX 4090) | QLoRA up to 14B |
| 1x 80 GB GPU (A100/H100) | full SFT 7-8B, QLoRA 70B |
| 8x 80 GB | full SFT 70B, CPT of 7-8B |

### 2.4 Code (for technical users)

**Load AITE data with Hugging Face `datasets`**

```python
from datasets import load_dataset
ds = load_dataset("json", data_files="Dataset/text/*.jsonl.gz", split="train")
ds = ds.filter(lambda r: r["quality_tier"] in ("high", "medium") and "NC" not in (r["license"] or ""))
train = ds.filter(lambda r: r["split"] == "train")
valid = ds.filter(lambda r: r["split"] == "validation")
```

**SFT with TRL + PEFT (any NVIDIA GPU, Colab or Kaggle)**

```python
from trl import SFTTrainer, SFTConfig
from peft import LoraConfig
trainer = SFTTrainer(
    model="Qwen/Qwen2.5-1.5B-Instruct",
    train_dataset=train.select_columns(["messages"]),
    eval_dataset=valid.select_columns(["messages"]),
    peft_config=LoraConfig(r=16, lora_alpha=32, target_modules="all-linear", task_type="CAUSAL_LM"),
    args=SFTConfig(output_dir="out", learning_rate=1e-4, num_train_epochs=2, per_device_train_batch_size=4,
                   gradient_accumulation_steps=8, assistant_only_loss=True, eval_strategy="steps", eval_steps=200,
                   bf16=True, logging_steps=10),
)
trainer.train()
```

**The same on a Mac, from the command line (what the Trainer page runs)**

```bash
python "AITE 1.py" --train --model mlx-community/Qwen2.5-1.5B-Instruct-4bit --iters 1000
# or directly with mlx-lm on the prepared data folder:
python -m mlx_lm lora --model mlx-community/Qwen2.5-1.5B-Instruct-4bit --train --data trainer_runs/<run>/data \
    --iters 1000 --batch-size 4 --num-layers 8 --mask-prompt --grad-checkpoint
python -m mlx_lm fuse --model mlx-community/Qwen2.5-1.5B-Instruct-4bit --adapter-path trainer_runs/<run>/adapter --save-path my-model
```

**Detection data to YOLO labels**

```python
import gzip, json, glob, os
for f in glob.glob("Dataset/detection/*.jsonl.gz"):
    for row in map(json.loads, gzip.open(f, "rt")):
        if row["type"] != "detection":
            continue
        W, H = row["width"], row["height"]
        lines = [f"{CLASSES.index(o['label'])} {(o['bbox'][0] + o['bbox'][2] / 2) / W:.6f} {(o['bbox'][1] + o['bbox'][3] / 2) / H:.6f} "
                 f"{o['bbox'][2] / W:.6f} {o['bbox'][3] / H:.6f}" for o in row["objects"]]
        open(os.path.splitext(row["image"])[0] + ".txt", "w").write("\n".join(lines))
```

**Vision-language models (VLM)**

- Fine-tune Qwen2-VL / Qwen2.5-VL, SmolVLM or LLaVA on the `messages` of `detection` and `image-text` rows. The `<image>` marker points to `row["image"]`.
- Use TRL (`SFTTrainer` with a vision collator) on GPUs, or `mlx-vlm` on a Mac.

**Robot VLA policies**

- Convert `vla/*.jsonl.gz` episodes to the LeRobot dataset format (one episode per row: frames, `gripper_xy` as state, `action`) or to RLDS/Open-X.
- Train ACT or Diffusion Policy (LeRobot), or fine-tune OpenVLA / pi0 with the instruction as the language goal.
- The episodes are a clean simulated top-down gantry. Pre-train on them, then fine-tune on a few real robot recordings to close the sim-to-real gap.

### 2.5 How much data to expect

- Agent mode runs as many tasks in parallel as the polite per-site limits allow. On one Mac with a home connection it collects text continuously; it stops only when paused. Watch `Dataset/stats.json` for your rate.
- For SFT, 10k-100k good examples already make a strong specialist.
- For CPT you want far more tokens. Run the agent for weeks, add other open corpora, or treat AITE as the high-quality "anneal" slice at the end of pre-training.
- Generated images and VLA episodes are unlimited and cheap. AITE caps them to a share of the real text (Settings > Agent > Mix), so they never crowd out the valuable data.

### 2.6 Licences and responsibility

Every row keeps its `source`, `url` and `license`. Generated images and VLA episodes are CC0. Web images keep their
author and licence (CC0, CC BY or CC BY-SA only). Respect attribution and share-alike terms, and remove
non-commercial rows for commercial models.
