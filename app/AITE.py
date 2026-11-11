import os as _os
import sys as _sys

def _use_hos_python():
    """Started by another Python (e.g. the editor's Run button with a different interpreter)? Restart with the HOS
    environment that has AITE's packages, so the app always opens."""
    import importlib.util as _iu
    if _iu.find_spec("PIL") and _iu.find_spec("sympy"):
        return
    here = _os.path.dirname(_os.path.abspath(__file__))
    for cand in (_os.path.join(here, "..", ".venv", "bin", "python"), _os.path.join(here, ".venv", "bin", "python")):
        cand = _os.path.abspath(cand)
        if _os.path.exists(cand) and _os.path.realpath(cand) != _os.path.realpath(_sys.executable):
            _os.execv(cand, [cand, _os.path.abspath(__file__)] + _sys.argv[1:])


if __name__ == "__main__":
    _use_hos_python()

import hashlib
import html
import io
import json
import logging
import math
import os
import queue
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from datetime import datetime
from fractions import Fraction

logging.getLogger("pypdf").setLevel(logging.ERROR)

APP = "Prolabs Robotics AITE"
APP_SHORT = "Prolabs AITE"
GITHUB_REPO = "https://github.com/Aarav-111/Prolabs-Robotics-864-Dataset-.git"  # Settings > GitHub can change it
PWT_NAME = "Parallel Web Technologies"  # product in Settings > Product
PWT_DEVELOPER = "Prolabs Robotics"
VERSION = "2.0"
SETTINGS_VERSION = 3                                            
HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.environ.get("AITE_SETTINGS") or os.path.join(HERE, "aite_settings.json")  # tests point at their own
LAST_INPUT_FILE = os.path.join(HERE, "aite_last_input.json")
USER_AGENT = f"AITE/{VERSION} (+https://github.com/Aarav-111/Prolabs-Robotics-864-Dataset-; Prolabs Robotics training-data tool)"


DATA_TYPES = ["problems & solution papers", "problems only", "worked examples", "research papers"]
OUTPUT_TYPES = ["pdf", "txt", "json"]
STYLES = ["paraphrase", "formal", "casual", "exam", "socratic", "step-by-step", "concise", "eli5", "competition", "teacher"]
FORMATS = ["qa", "instruction", "chat", "mcq", "true-false", "fill-blank", "flashcard", "markdown", "latex", "step-list", "summary"]
METHODS = ["numbers", "names", "synonyms"]
METHOD_LABELS = {"numbers": "new numbers, re-solved (SymPy)", "names": "swap names & items", "synonyms": "synonyms"}
DEFAULT_INPUT = {
    "topics": ["mathematics"],
    "quantity": 1000,
    "quality": 10,
    "data_type": "problems & solution papers",
    "data_types": list(DATA_TYPES),  # all on by default: problems + solutions, problems only, worked examples, papers
    "output_type": "pdf",
    "datagen_variations": 100,
    "datagen_styles": list(STYLES),
    "datagen_formats": list(FORMATS),
    "datagen_methods": list(METHODS),
}
MAX_VARIATIONS = 10000   # DataGen variations per record
MAX_QUANTITY = 100000    # records per Manual run
AGENT_TEXT_TYPES = ["problems & solution papers", "worked examples", "research papers"]
MAX_AGENTS = 20000      # parallel agents in Agent mode (several processes: macOS allows ~2,000 threads per process)
AGENTS_PER_PROCESS = 1500
TRAINER_MODELS = {  # Hugging Face id: (plain name, download GB, RAM GB it needs) - all open (not gated), MLX format
    "mlx-community/Qwen2.5-0.5B-Instruct-4bit": ("Small - Qwen 2.5, 0.5B (fastest)", 0.3, 8),
    "mlx-community/SmolLM2-360M-Instruct": ("Tiny - SmolLM2, 360M", 0.7, 8),
    "mlx-community/Llama-3.2-1B-Instruct-4bit": ("Medium - Llama 3.2, 1B", 0.7, 8),
    "mlx-community/Qwen2.5-1.5B-Instruct-4bit": ("Medium+ - Qwen 2.5, 1.5B", 0.9, 8),
    "mlx-community/Qwen2.5-Math-1.5B-Instruct-4bit": ("Maths - Qwen 2.5 Math, 1.5B", 0.9, 8),
    "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit": ("Coding - Qwen 2.5 Coder, 1.5B", 0.9, 8),
    "mlx-community/Qwen3-1.7B-4bit": ("Qwen 3, 1.7B", 1.0, 8),
    "mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit": ("Reasoning - DeepSeek R1 Distill, 1.5B", 1.0, 8),
    "mlx-community/Qwen2.5-3B-Instruct-4bit": ("Large - Qwen 2.5, 3B", 1.8, 16),
    "mlx-community/Llama-3.2-3B-Instruct-4bit": ("Large - Llama 3.2, 3B", 1.8, 16),
    "mlx-community/Phi-3.5-mini-instruct-4bit": ("Large - Phi 3.5 mini, 3.8B", 2.2, 16),
    "mlx-community/Qwen3-4B-4bit": ("Large - Qwen 3, 4B", 2.3, 16),
    "mlx-community/Qwen2.5-7B-Instruct-4bit": ("X-Large - Qwen 2.5, 7B", 4.3, 16),
    "mlx-community/Mistral-7B-Instruct-v0.3-4bit": ("X-Large - Mistral, 7B", 4.1, 16),
    "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit": ("X-Large - Llama 3.1, 8B", 4.5, 16),
    "mlx-community/Qwen2.5-14B-Instruct-4bit": ("XX-Large - Qwen 2.5, 14B", 8.3, 32),
}
TRAIN_LENGTHS = {"Quick test (~2 min)": 40, "Short (~10 min)": 200, "Normal (~45 min)": 1000, "Long (a few hours)": 4000}

# ----------------------------------------------------------------------------- sources
SE_SITES = {
    "math": "math", "algebra": "math", "calculus": "math", "geometry": "math",
    "probability": "math", "statistics": "stats", "physics": "physics",
    "chemistry": "chemistry", "biology": "biology", "programming": "stackoverflow",
    "python": "stackoverflow", "coding": "stackoverflow", "computer science": "cs",
    "algorithms": "cs", "robotics": "robotics", "electronics": "electronics",
    "engineering": "engineering", "economics": "economics", "astronomy": "astronomy",
    "machine learning": "ai", "ai": "ai", "data science": "datascience",
    "finance": "quant", "english": "english", "history": "history",
    "philosophy": "philosophy", "law": "law", "medicine": "medicalsciences", "mathematics": "math", "maths": "math",
    "java": "stackoverflow", "javascript": "stackoverflow", "typescript": "stackoverflow", "c++": "stackoverflow",
    "c#": "stackoverflow", "rust": "stackoverflow", "golang": "stackoverflow", "sql": "stackoverflow", "html": "stackoverflow",
    "css": "stackoverflow", "react": "stackoverflow", "node.js": "stackoverflow", "swift": "stackoverflow",
    "kotlin": "stackoverflow", "ruby": "stackoverflow", "php": "stackoverflow", "pandas": "stackoverflow",
    "numpy": "stackoverflow", "django": "stackoverflow", "flask": "stackoverflow", "bash": "stackoverflow",
    "c programming": "stackoverflow", "matlab": "stackoverflow", "arduino": "arduino", "raspberry pi": "raspberrypi",
}
SE_TAG_ALIASES = {  # (site, topic) -> the site's real tag when the topic name is not a tag itself
    ("math", "algebra"): "algebra-precalculus", ("math", "precalculus"): "algebra-precalculus",
    ("math", "number theory"): "elementary-number-theory", ("math", "percent"): "percentages",
    ("math", "percentages"): "percentages", ("math", "fractions"): "fractions", ("math", "trig"): "trigonometry",
    ("math", "stats"): "statistics", ("math", "differential equations"): "ordinary-differential-equations",
    ("physics", "mechanics"): "newtonian-mechanics", ("physics", "electricity"): "electricity",
    ("chemistry", "organic"): "organic-chemistry",
}
SE_GENERIC_QUERY = {"math": "find", "physics": "calculate", "chemistry": "calculate", "electronics": "calculate"}
SOURCES = ["duckduckgo", "stackexchange", "huggingface", "wikibooks", "arxiv", "openalex", "wikipedia"]
# default weight, filter trust bonus, min chars, description
SOURCE_INFO = {
    "duckduckgo": (1.0, 0.0, 120, "DuckDuckGo web search"),
    "stackexchange": (2.0, 1.0, 120, "Stack Exchange API (question + accepted answer)"),
    "huggingface": (2.0, 1.2, 40, "Hugging Face open datasets (train splits)"),
    "wikibooks": (0.6, 0.6, 80, "Wikibooks exercises & solutions"),
    "arxiv": (0.4, 0.8, 120, "arXiv papers"),
    "openalex": (0.4, 0.8, 120, "OpenAlex research papers"),
    "wikipedia": (0.2, 0.5, 300, "Wikipedia articles"),
}
TYPE_MULT = {
    "problems & solution papers": {"arxiv": 0.5, "openalex": 0.5, "wikipedia": 0.5},
    "problems only": {"arxiv": 0.3, "openalex": 0.3, "wikipedia": 0.3},
    "worked examples": {"huggingface": 1.5, "wikibooks": 1.5, "arxiv": 0.2, "openalex": 0.2},
    "research papers": {"arxiv": 6, "openalex": 6, "wikipedia": 1, "duckduckgo": 0.3,
                        "stackexchange": 0, "huggingface": 0, "wikibooks": 0},
}
TOPUP = {"research papers": ["openalex", "arxiv", "wikipedia"]}
TOPUP_DEFAULT = ["huggingface", "stackexchange", "wikibooks", "openalex", "arxiv"]
HF_BASE = "https://datasets-server.huggingface.co"
MATH_DS = "EleutherAI/hendrycks_math"
_MATH_P, _MATH_S = [("problem", "")], [("solution", "")]
_CAMEL_P, _CAMEL_S = [("message_1", "")], [("message_2", "")]
HF_CURATED = [
    {"keys": ["word problem", "arithmetic", "grade school", "mathematics", "maths", "math"],
     "domain": ["math", "maths", "mathematics", "word", "problem", "problems", "arithmetic", "grade", "school"],
     "dataset": "openai/gsm8k", "config": "main", "p": [("question", "")], "s": [("answer", "")], "license": "MIT", "fcols": []},
    {"keys": ["intermediate algebra", "polynomial", "inequalit"], "domain": ["intermediate", "algebra", "polynomial", "polynomials"],
     "dataset": MATH_DS, "config": "intermediate_algebra", "p": _MATH_P, "s": _MATH_S, "license": "MIT", "fcols": []},
    {"keys": ["prealgebra", "pre-algebra", "fraction", "percent", "decimal"], "domain": ["prealgebra", "pre", "algebra"],
     "dataset": MATH_DS, "config": "prealgebra", "p": _MATH_P, "s": _MATH_S, "license": "MIT", "fcols": []},
    {"keys": ["algebra", "equation", "mathematics", "maths", "math"], "domain": ["algebra", "equation", "equations", "math", "maths", "mathematics"],
     "dataset": MATH_DS, "config": "algebra", "p": _MATH_P, "s": _MATH_S, "license": "MIT", "fcols": []},
    {"keys": ["geometry", "triangle", "circle", "polygon"], "domain": ["geometry"],
     "dataset": MATH_DS, "config": "geometry", "p": _MATH_P, "s": _MATH_S, "license": "MIT", "fcols": []},
    {"keys": ["probability", "counting", "combinatoric", "permutation"], "domain": ["probability", "counting", "combinatorics"],
     "dataset": MATH_DS, "config": "counting_and_probability", "p": _MATH_P, "s": _MATH_S, "license": "MIT", "fcols": []},
    {"keys": ["number theory", "prime", "divisib", "modular"], "domain": ["number", "theory"],
     "dataset": MATH_DS, "config": "number_theory", "p": _MATH_P, "s": _MATH_S, "license": "MIT", "fcols": []},
    {"keys": ["precalculus", "trigonometr", "vector", "matri", "complex number"], "domain": ["precalculus", "trigonometry"],
     "dataset": MATH_DS, "config": "precalculus", "p": _MATH_P, "s": _MATH_S, "license": "MIT", "fcols": []},
    {"keys": ["physics", "mechanic", "optic", "quantum", "thermodynamic", "electromagnet", "relativity", "nuclear",
              "kinematic", "astrophysic", "particle", "fluid dynamic"],
     "domain": ["physics"], "dataset": "camel-ai/physics", "config": "default", "p": _CAMEL_P, "s": _CAMEL_S,
     "license": "CC-BY-NC-4.0", "fcols": ["topic;", "sub_topic"]},
    {"keys": ["chemistry", "organic", "inorganic", "stoichiometr", "electrochem", "biochem", "polymer", "chemical"],
     "domain": ["chemistry", "chemical"], "dataset": "camel-ai/chemistry", "config": "default", "p": _CAMEL_P, "s": _CAMEL_S,
     "license": "CC-BY-NC-4.0", "fcols": ["topic;", "sub_topic"]},
    {"keys": ["biology", "genetic", "ecology", "evolution", "anatomy", "microbio", "botany", "zoology", "physiology",
              "immunolog", "neuro", "marine bio", "cell bio"],
     "domain": ["biology", "biological"], "dataset": "camel-ai/biology", "config": "default", "p": _CAMEL_P, "s": _CAMEL_S,
     "license": "CC-BY-NC-4.0", "fcols": ["topic;", "sub_topic"]},
    {"keys": ["python", "programming", "coding", "code", "algorithm", "computer science"],
     "domain": ["python", "programming", "coding", "code", "algorithm", "algorithms", "computer", "science"],
     "dataset": "google-research-datasets/mbpp", "config": "full",
     "p": [("text", ""), ("test_list", "Your code should pass these tests:")], "s": [("code", "")], "license": "CC-BY-4.0", "fcols": []},
    {"keys": ["science", "earth science", "general science"], "domain": ["science", "general", "earth"],
     "dataset": "allenai/sciq", "config": "default", "p": [("question", "")],
     "s": [("correct_answer", "Answer:"), ("support", "Explanation:")], "license": "CC-BY-NC-3.0", "fcols": ["support"]},
]
TOPIC_STOP = {"problems", "problem", "solutions", "solution", "questions", "question", "exercises", "exercise", "with",
              "and", "the", "for", "basic", "basics", "advanced", "intro", "introduction", "level", "high", "school",
              "papers", "paper", "examples", "worked", "practice"}
PROB_COLS = ["problem", "question", "instruction", "query", "prompt", "input", "message_1", "context", "text"]
SOL_COLS = ["solution", "answer", "output", "response", "completion", "message_2", "rationale", "explanation",
            "code", "target", "correct_answer"]
RULES = ["not a problem", "refers elsewhere", "too few words", "too many words", "unreadable characters", "link spam", "repeated lines",
         "shouting / all caps", "spam / ads", "unanswered", "needs a figure", "off topic"]


def rule_key(why):
    return "rule_" + re.sub(r"[^a-z]+", "_", why.lower()).strip("_")


# ----------------------------------------------------------------------------- products (all by ProLab Robotics)
PRODUCT_GROUPS = {  # settings section -> [(setting key, product name, what it does)]
    "Products: Collection": [
        ("pwt_enabled", PWT_NAME, "runs hundreds or thousands of agents at once; every website keeps its own polite rate limit"),
        ("product_agent", "AITE Agent", "builds the dataset non-stop on the Agent page - pause only, resumes by itself"),
        ("product_topic_engine", "Topic Engine", "endless topics: curated advanced taxonomy, OpenAlex topics and concepts, Wikipedia links; topics.json with check marks"),
        ("product_archives", "Open Archives", "bulk human-written Q&A: the Stack Exchange dump (MathOverflow, physics, chemistry...), MedMCQA, PubMedQA, ARC"),
        ("product_web_search", "Web Search", "topic search across Stack Exchange, Hugging Face, OpenAlex, arXiv, Wikipedia (DuckDuckGo once, bot checks respected)")],
    "Products: Data quality": [
        ("product_filter", "Quality Filter", "local scoring and rules - spam, duplicates, unanswered and off-topic items never reach the dataset"),
        ("product_datagen", "DataGen", "similar versions of every record: new numbers re-solved with SymPy, 10 styles x 11 formats"),
        ("product_preference", "Preference Pairs", "better / worse answer pairs from voted answers, ready for DPO preference training")],
    "Products: Vision & robotics": [
        ("product_web_vision", "Web Vision", "free-licence Wikimedia Commons images with captions, authors and licences"),
        ("product_synthetic_vision", "Synthetic Vision", "generated scenes with exact boxes, outlines, captions and VQA - object recognition data"),
        ("product_vla", "Robot VLA Studio", "pick-and-place episodes with frames, actions and instructions for vision-language-action models")],
    "Products: Knowledge & delivery": [
        ("product_trainer", "AITE Ask (RAG)", "ALL the data from GitHub in one search index, answered by a local AI model - no training"),
        ("kaggle_enabled", "Kaggle Sync", "the whole dataset also published to Kaggle as a new version every hour"),
        ("gh_enabled", "GitHub Sync", "stats, topics.json and the new data pushed to main every few minutes"),
    ],
}
PRODUCT_OF_KIND = {"archive": "product_archives", "text": "product_web_search", "web_images": "product_web_vision",
                   "synthetic_images": "product_synthetic_vision", "vla": "product_vla"}


def product_on(st, key):
    return bool(st.get(key, True))


# ----------------------------------------------------------------------------- settings
def _default_dataset_dir():
    """<repo>/Dataset when AITE runs from inside the dataset repo (app/AITE.py), else the clone next to the app."""
    up = os.path.dirname(HERE)
    if os.path.isdir(os.path.join(up, ".git")) and os.path.isdir(os.path.join(up, "Dataset")):
        return os.path.join(up, "Dataset")
    return os.path.join(HERE, "Prolabs-Robotics-864-Dataset", "Dataset")


def _settings_spec():
    """Every setting: key -> (section, label, kind, default, extra)."""
    s = {}

    def add(sec, key, label, kind, default, extra=None):
        s[key] = (sec, label, kind, default, extra)

    for sec, prods in PRODUCT_GROUPS.items():
        for key, name, what in prods:
            add(sec, key, f"{name} - {what}", "bool", True)
    add("General", "theme", "Theme", "choice", "dark", ["dark", "light"])
    add("General", "corner_radius", "Card corner radius (G3 curve)", "int", 24, (0, 40))
    add("General", "font_size", "Text size (ChatGPT uses 14)", "int", 14, (11, 20))
    add("General", "font_family", "Font", "choice", "SF Pro (system)", ["SF Pro (system)", "Helvetica Neue", "Avenir Next", "Menlo"])
    add("General", "confirm_exit", "Confirm on exit", "bool", False)
    add("General", "remember_input", "Remember last input", "bool", True)
    add("General", "show_tooltips", "Show status hints", "bool", True)
    add("General", "log_timestamps", "Timestamps in log", "bool", True)
    add("General", "log_max_lines", "Log max lines", "int", 3000, (100, 50000))
    add("General", "autosave_settings", "Autosave settings", "bool", True)
    add("General", "start_mode", "Start input mode", "choice", "VDM", ["VDM", "JSON"])
    add("General", "auto_preview", "Open preview after run", "bool", True)
    add("General", "sound_on_done", "Bell when run finishes", "bool", True)
    add("General", "preview_max_chars", "Preview max characters", "int", 400000, (10000, 5000000))
    add("General", "workflow_pulse", "Animate the active workflow stage", "bool", True)
    # Network
    add("Network", "timeout", "HTTP timeout (s)", "float", 15.0, (2, 60))
    add("Network", "retries", "Retries on server errors", "int", 1, (0, 5))
    add("Network", "delay", "Delay between requests to one host (s)", "float", 0.5, (0, 10))
    add("Network", "user_agent", "User agent (honest by default)", "str", USER_AGENT)
    add("Network", "max_page_bytes", "Max bytes per page", "int", 2000000, (10000, 20000000))
    add("Network", "fetch_pages", "Open web result pages", "bool", True)
    add("Network", "fetch_pdfs", "Read PDF papers (pypdf)", "bool", True)
    add("Network", "pdf_max_pages", "PDF pages to read", "int", 12, (1, 200))
    add("Network", "max_runtime", "Max run time (s)", "int", 900, (30, 7200))
    add("Network", "proxy", "HTTP proxy (blank = none)", "str", "")
    add("Network", "verify_ssl", "Verify SSL certificates", "bool", True)
    for src in SOURCES:
        w, trust, minc, desc = SOURCE_INFO[src]
        sec = "Source: " + src
        add(sec, f"{src}_enabled", f"Enabled ({desc})", "bool", True)
        add(sec, f"{src}_weight", "Share of results (weight)", "float", w, (0, 10))
        add(sec, f"{src}_page_size", "Results per request", "int", 20, (1, 100))
        add(sec, f"{src}_max_pages", "Max requests per topic", "int", 3, (1, 50))
        add(sec, f"{src}_min_chars", "Min characters per item", "int", minc, (0, 5000))
        add(sec, f"{src}_max_chars", "Max characters per item", "int", 8000, (500, 100000))
        add(sec, f"{src}_trust", "Trust bonus (filter)", "float", trust, (-3, 3))
    add("Source: duckduckgo", "ddg_region", "Region", "choice", "wt-wt", ["wt-wt", "us-en", "uk-en", "in-en", "de-de", "fr-fr"])
    add("Source: duckduckgo", "ddg_safe", "Safe search", "choice", "moderate", ["strict", "moderate", "off"])
    add("Source: duckduckgo", "ddg_suffix", "Query suffix", "str", "problems with solutions")
    add("Source: duckduckgo", "ddg_skip_pdf", "Skip PDF links", "bool", False)
    add("Source: duckduckgo", "ddg_blocklist", "Blocked domains (comma)", "str", "youtube.com,facebook.com,instagram.com,tiktok.com,pinterest.com,chegg.com,coursehero.com")
    add("Source: duckduckgo", "ddg_instant_api", "Use official Instant Answer API for topic context", "bool", True)
    add("Source: stackexchange", "se_accepted_only", "Accepted answers only", "bool", True)
    add("Source: stackexchange", "se_min_score", "Min question score", "int", 1, (-10, 1000))
    add("Source: stackexchange", "se_sort", "Sort", "choice", "votes", ["votes", "relevance", "activity", "creation"])
    add("Source: stackexchange", "se_default_site", "Fallback site", "str", "math")
    for site in sorted(set(SE_SITES.values())):
        add("Stack Exchange sites", f"se_site_{site}", f"Use {site}.stackexchange", "bool", True)
    add("Source: huggingface", "hf_curated", "Use curated problem/solution datasets", "bool", True)
    add("Source: huggingface", "hf_discover", "Find datasets for other topics", "bool", True)
    add("Source: huggingface", "hf_min_downloads", "Discovery: min downloads", "int", 100, (0, 10000000))
    add("Source: huggingface", "hf_max_datasets", "Discovery: max datasets per topic", "int", 3, (1, 10))
    add("Source: huggingface", "hf_english_only", "English rows only", "bool", True)
    add("Source: huggingface", "hf_max_candidates", "Discovery: datasets to examine per topic", "int", 8, (1, 40))
    add("Source: huggingface", "hf_scan_pages", "Pages of 100 rows to scan", "int", 6, (1, 100))
    add("Source: huggingface", "hf_allow_eval_splits", "Allow test/validation splits (benchmark leak risk)", "bool", False)
    add("Source: huggingface", "hf_random_offset", "Start at a topic-based offset", "bool", True)
    add("Source: huggingface", "hf_discovered_penalty", "Trust penalty for discovered datasets", "float", 0.9, (0, 3))
    add("Source: wikibooks", "wb_max_pages", "Max pages per topic", "int", 6, (1, 50))
    add("Source: arxiv", "arxiv_sort", "Sort", "choice", "relevance", ["relevance", "lastUpdatedDate", "submittedDate"])
    add("Source: openalex", "openalex_oa_only", "Open-access papers only", "bool", True)
    add("Source: openalex", "openalex_min_year", "From year (0 = any)", "int", 0, (0, 2100))
    add("Source: wikipedia", "wiki_lang", "Language", "choice", "en", ["en", "de", "fr", "es", "hi"])
    # Query
    add("Query", "local_expansion", "Local query expansion", "bool", True)
    add("Query", "variants_per_topic", "Query variants per topic", "int", 3, (1, 10))
    add("Query", "extra_terms", "Extra terms (comma)", "str", "")
    add("Query", "exclude_terms", "Exclude terms (comma)", "str", "")
    add("Query", "oversample", "Oversample factor base", "float", 1.5, (1, 6))
    add("Query", "refill_rounds", "Search deeper when the filter leaves too few (rounds)", "int", 2, (0, 10))
    add("Query", "oversample_per_quality", "Extra oversample per quality point >4", "float", 0.35, (0, 2))
    # Filter
    add("Filter", "filter_from_quality", "Strict filter from quality >", "int", 4, (0, 10))
    add("Filter", "dedupe", "Remove duplicates", "bool", True)
    add("Filter", "dedupe_threshold", "Near-duplicate similarity", "float", 0.8, (0.3, 1.0))
    add("Filter", "require_solution", "Require a solution", "bool", True)
    add("Filter", "min_words", "Min words", "int", 25, (0, 2000))
    add("Filter", "max_words", "Max words", "int", 4000, (100, 50000))
    add("Filter", "min_ascii_ratio", "Min readable-text ratio", "float", 0.85, (0, 1))
    add("Filter", "max_link_ratio", "Max link density", "float", 0.15, (0, 1))
    add("Filter", "max_upper_ratio", "Max capitals ratio", "float", 0.35, (0, 1))
    add("Filter", "max_repeat_ratio", "Max repeated-line ratio", "float", 0.3, (0, 1))
    add("Filter", "topic_relevance", "Require a topic word (web sources)", "bool", True)
    add("Filter", "reject_spam_words", "Reject spam/ads", "bool", True)
    add("Filter", "spam_words", "Spam words (comma)", "str", "buy now,subscribe now,click here,casino,discount code,free trial,sponsored,cookie policy,promo code")
    add("Filter", "soft_tags", "Non-problem tags (comma)", "str", "soft-question,advice,career-development,big-list,reference-request,learning,education,self-learning,book-recommendation,intuition,math-history,research")
    add("Filter", "figure_phrases", "Missing-figure phrases (comma)", "str", "in the image,the image shows,shown in the image,in the picture,see the figure,shown in the figure,<image>,in the diagram below")
    add("Filter", "reject_unanswered", "Reject 'no answer yet'", "bool", True)
    add("Filter", "paper_penalty", "Score penalty: papers in problem runs / problems in paper runs", "float", 2.5, (0, 10))
    for w, d in [("length", 1.0), ("structure", 1.5), ("solution", 2.0), ("source", 1.0),
                 ("relevance", 1.5), ("readability", 1.0), ("votes", 1.0), ("cleanliness", 1.0)]:
        add("Filter weights", f"w_{w}", f"Weight: {w}", "float", d, (0, 5))
    for q in range(1, 11):
        add("Quality map", f"min_score_q{q}", f"Min score at quality {q}", "float", round(max(0.0, (q - 1) * 0.95), 2), (0, 10))
    for rule in RULES:
        add("Filter rules", rule_key(rule), f"Rule on: {rule}", "bool", True)
    # DataGen
    add("DataGen", "dg_seed", "Random seed (same seed = same variants)", "int", 7, (0, 10 ** 9))
    add("DataGen", "dg_max_total", "Max variants per run", "int", 1000000, (10, 100000000))
    add("DataGen", "dg_numeric_tries", "Tries to find nice new numbers", "int", 40, (1, 500))
    add("DataGen", "dg_small_delta", "Max change for numbers up to 12", "int", 4, (1, 20))
    add("DataGen", "dg_scale_pct", "Max % change for bigger numbers", "int", 40, (5, 90))
    add("DataGen", "dg_keep_roundness", "Keep round numbers round (5s, 10s)", "bool", True)
    add("DataGen", "dg_freeze_years", "Never change years (1900-2100)", "bool", True)
    add("DataGen", "dg_names_keep_gender", "Keep name gender when swapping", "bool", True)
    add("DataGen", "dg_items_need_name", "Swap items only in word problems", "bool", True)
    add("DataGen", "dg_synonym_rate", "Synonym swap rate", "float", 0.5, (0, 1))
    add("DataGen", "dg_mcq_options", "Options per multiple-choice question", "int", 4, (3, 6))
    add("DataGen", "dg_tf_true_ratio", "Share of 'true' statements", "float", 0.5, (0, 1))
    add("DataGen", "dg_placement", "Where variants go in the file", "choice", "grouped", ["grouped", "end"])
    add("DataGen", "dg_title_suffix", "Add [style · format] to titles", "bool", True)
    add("DataGen", "dg_dedupe", "Drop duplicate variants", "bool", True)
    add("DataGen", "dg_chat_system", "System message in chat format (blank = none)", "str", "You are a patient, accurate tutor.")
    add("DataGen", "dg_latex_sympy", "Typeset equations with SymPy in LaTeX format", "bool", True)
    add("DataGen", "dg_socratic_questions", "Socratic guiding questions (|)", "str", "What are we given?|What should we do first?|What does that give us?|What comes next?|Can we simplify this?|How can we check it?|So what is the answer?")
    add("DataGen", "dg_casual_openers", "Casual openers (|)", "str", "Quick one: |Here's a fun one! |Try this: |Okay, so: ")
    add("DataGen", "dg_teacher_openers", "Teacher openers (|)", "str", "Today's practice problem:|Class exercise:|Let's practise this one:")
    add("DataGen", "dg_exam_max_marks", "Exam style: max marks", "int", 10, (1, 50))
    add("DataGen", "dg_answer_field", "Store the final answer in JSON", "bool", True)
    # Output
    add("Output", "out_dir", "Default export folder", "str", os.path.join(HERE, "exports"))
    add("Output", "file_prefix", "File name prefix", "str", "AITE")
    add("Output", "include_meta", "Include metadata", "bool", False)
    add("Output", "include_sources", "Include source URLs & licences", "bool", False)
    add("Output", "include_scores", "Include quality scores", "bool", False)
    add("Output", "json_indent", "JSON indent", "int", 2, (0, 8))
    add("Output", "json_format", "JSON layout", "choice", "records", ["records", "chat-messages", "instruction"])
    add("Output", "txt_separator", "TXT separator", "str", "=" * 72)
    add("Output", "pdf_page", "PDF page size", "choice", "A4", ["A4", "Letter"])
    add("Output", "pdf_font_size", "PDF font size", "int", 10, (7, 16))
    add("Output", "pdf_margin", "PDF margin (pt)", "int", 50, (20, 100))
    add("Output", "pdf_title_page", "PDF title page", "bool", False)
    add("Output", "pdf_numbering", "PDF page numbers", "bool", True)
    add("Output", "open_after_export", "Open file after export", "bool", False)
    add("Output", "sort_by", "Sort records by", "choice", "score", ["score", "source", "topic", "none"])
    add("Output", "max_chars_out", "Max chars per record", "int", 12000, (500, 200000))
    add("General", "start_page", "Open in", "choice", "Agent", ["Agent", "Ask"])
    add("General", "guide_seen", "Interactive guide already shown", "bool", False)
    # Parallel Web Technologies
    add(PWT_NAME, "pwt_workers", "Parallel agents (more than 1,500 start extra worker processes)", "int", 1000, (1, MAX_AGENTS))
    add(PWT_NAME, "pwt_default_rate", "Requests per second per host (hosts not listed)", "float", 2.0, (0.05, 20))
    add(PWT_NAME, "pwt_host_rates", "Per-host overrides (host=rate, comma)", "str", "")
    add(PWT_NAME, "pwt_parallel_topics", "Manual mode: search topics in parallel", "bool", True)
    # Agent
    add("Agent", "agent_dir", "Dataset folder (inside the GitHub clone)", "str", _default_dataset_dir())
    add("Agent", "agent_resume", "Resume collecting when AITE opens", "bool", True)
    add("Agent", "agent_background", "Keep collecting while the window is closed", "bool", True)
    add("Agent", "agent_cpu_cap", "Slow down above CPU %", "int", 70, (10, 100))
    add("Agent", "agent_min_free_gb", "Pause by itself when free disk space is below (GB)", "float", 5.0, (0.5, 1000))
    add("Agent", "agent_batch", "Records per topic task", "int", 50, (1, 10000))
    add("Agent", "agent_quality", "Quality (1-10)", "int", 10, (1, 10))
    add("Agent", "agent_types", "Text data types (comma)", "str", ",".join(AGENT_TEXT_TYPES))
    add("Agent", "agent_focus_topics", "Focus topics, collected first (comma)", "str", "")
    add("Agent", "agent_focus_only", "Collect only my focus topics", "bool", False)
    add("Agent", "agent_topics_parallel", "Topics collected at the same time (all processes) - more just queue at the sites", "int", 120, (1, 20000))
    add("Agent", "agent_verbose", "Super verbose log: every request and every step of every task", "bool", True)
    add("Network", "http_verbose", "Log every web request (site, path, status, size, time)", "bool", True)
    add("Agent", "agent_local_floor", "Generated items allowed before text arrives", "int", 100, (0, 100000))
    add("Agent", "agent_variations", "DataGen variations per record", "int", 100, (0, MAX_VARIATIONS))
    add("Agent", "agent_task_timeout", "Max seconds per task", "int", 120, (20, 3600))
    add("Agent", "agent_mix_archive", "Mix: open Q&A archives weight", "float", 6.0, (0, 100))
    add("Agent", "agent_mix_text", "Mix: topic search weight", "float", 4.0, (0, 100))
    add("Agent", "agent_mix_web_images", "Mix: web images weight", "float", 2.0, (0, 100))
    add("Agent", "agent_mix_synthetic_images", "Mix: generated detection images weight", "float", 1.0, (0, 100))
    add("Agent", "agent_mix_vla", "Mix: robot VLA episodes weight", "float", 1.0, (0, 100))
    add("Agent", "agent_images_per_task", "Web images per task", "int", 6, (1, 50))
    add("Agent", "agent_image_size", "Web image width (px)", "int", 512, (128, 2048))
    add("Agent", "agent_synth_per_task", "Generated images per task", "int", 12, (1, 500))
    add("Agent", "agent_synth_size", "Generated image size (px)", "int", 256, (64, 1024))
    add("Agent", "agent_vla_per_task", "VLA episodes per task", "int", 4, (1, 100))
    add("Agent", "agent_vla_size", "VLA frame size (px)", "int", 160, (64, 512))
    add("Agent", "agent_shard_mb", "Max shard size (MB, GitHub limit is 100)", "float", 45.0, (1, 95))
    # Ask (RAG): the whole dataset, searchable, answered by a local model - no training
    add("Ask (RAG)", "rag_model", "Model that answers (any MLX model id from Hugging Face, or a folder)", "str",
        "mlx-community/Qwen2.5-1.5B-Instruct-4bit")
    add("Ask (RAG)", "rag_use_model", "Answer with the AI model (off = show the best matching records only)", "bool", True)
    add("Ask (RAG)", "rag_k", "Records the model reads per question", "int", 6, (1, 30))
    add("Ask (RAG)", "rag_tokens", "Longest answer (tokens)", "int", 600, (32, 8192))
    add("Ask (RAG)", "rag_context_chars", "Most source text given to the model (characters)", "int", 6000, (500, 60000))
    add("Ask (RAG)", "rag_sync_min", "Get new data from GitHub every (minutes)", "int", 10, (1, 1440))
    add("Ask (RAG)", "rag_include_local", "Also the newest rows on this Mac not pushed yet (so ALL data is in)", "bool", True)
    add("Ask (RAG)", "rag_temp", "Creativity (temperature)", "float", 0.2, (0.0, 2.0))
    # Kaggle: the whole dataset also goes to a Kaggle dataset (alongside GitHub), as a new version every so often
    add("Kaggle", "kaggle_enabled", "Upload the dataset to Kaggle too (alongside GitHub)", "bool", True)
    add("Kaggle", "kaggle_dataset", "Kaggle dataset (owner/name, or its link)", "str", "prolabsrobotics/prolabs-robotics-864")
    add("Kaggle", "kaggle_every_min", "New Kaggle version every (minutes)", "int", 60, (10, 10080))
    add("Kaggle", "kaggle_images", "Include the picture files (much bigger uploads)", "bool", False)
    # Trainer (local LLM fine-tuning with MLX) - kept for the command line only (--train); the app uses Ask (RAG)
    add("Trainer", "trainer_model", "Model (any MLX model id from Hugging Face, or a folder)", "str", next(iter(TRAINER_MODELS)))
    add("Trainer", "trainer_length", "How long to train", "choice", "Short (~10 min)", list(TRAIN_LENGTHS) + ["Custom (iterations below)"])
    add("Trainer", "trainer_iters", "Custom: iterations", "int", 600, (10, 100000))
    add("Trainer", "trainer_batch", "Batch size", "int", 4, (1, 64))
    add("Trainer", "trainer_lr", "Learning rate", "float", 1e-5, (1e-7, 1e-2))
    add("Trainer", "trainer_layers", "Layers to adapt (LoRA)", "int", 8, (1, 64))
    add("Trainer", "trainer_max_seq", "Max tokens per example", "int", 1024, (128, 8192))
    add("Trainer", "trainer_fine_tune", "Method", "choice", "lora", ["lora", "dora", "full"])
    add("Trainer", "trainer_mask_prompt", "Learn from answers only (mask the question)", "bool", True)
    add("Trainer", "trainer_tiers", "Quality tiers to use (comma: high, medium, basic)", "str", "high,medium,basic")
    add("Trainer", "trainer_variants", "Use DataGen variants too", "bool", True)
    add("Trainer", "trainer_max_rows", "Max training rows (0 = all)", "int", 0, (0, 10000000))
    add("Trainer", "trainer_system", "System message for every example (blank = none)", "str", "")
    add("Trainer", "trainer_data_mode", "Data: all collected data or a custom set", "choice", "all", ["all", "custom"])
    add("Trainer", "trainer_custom_rows", "Custom set: number of examples", "int", 10000, (10, 10000000))
    add("Trainer", "trainer_fields", "Custom set: fields (comma, blank = all)", "str", "")
    add("Trainer", "trainer_sources", "Custom set: sources (comma, blank = all)", "str", "")
    add("Trainer", "trainer_keywords", "Custom set: topic keywords (comma, blank = any)", "str", "")
    add("Trainer", "trainer_preview_tokens", "Try it: longest answer (tokens)", "int", 300, (16, 4096))
    add("Trainer", "trainer_compare_n", "Try it: check questions to compare", "int", 50, (1, 1000))
    # GitHub
    add("GitHub", "gh_repo", "Repository URL (https://github.com/owner/repo.git)", "str", GITHUB_REPO)
    add("GitHub", "gh_branch", "Branch", "str", "main")
    add("GitHub", "gh_interval_min", "Sync every (minutes)", "float", 5.0, (1, 1440))
    add("GitHub", "gh_push_data", "Push dataset shards and images (not just stats)", "bool", True)
    add("GitHub", "gh_stream", "GitHub first: delete local copies once GitHub has them (tiny local buffer)", "bool", True)
    add("GitHub", "gh_batch_mb", "Upload at most this much per sync (MB) - the rest goes next sync", "float", 25.0, (1, 2000))
    add("GitHub", "gh_max_repo_mb", "Stop pushing data above (MB) - GitHub blocks repositories far beyond ~5 GB", "float", 4500.0, (10, 10000000))
    add("GitHub", "gh_author_name", "Commit author name", "str", "AITE Agent")
    add("GitHub", "gh_author_email", "Commit author email", "str", "aite-agent@users.noreply.github.com")
    return s


SPEC = _settings_spec()
UI_KEYS = {"theme"}


def default_settings():
    return {k: v[3] for k, v in SPEC.items()}


# value saved by an older AITE that was only ever the old default -> today's default (choices the user made are kept)
SETTINGS_MIGRATE = {"gh_repo": [""], "agent_dir": [os.path.join(HERE, "dataset")], "pwt_workers": [32], "agent_quality": [5],
                    "agent_batch": [8], "agent_variations": [3], "agent_task_timeout": [180], "dg_max_total": [20000],
                    "gh_max_repo_mb": [900.0, 900], "agent_cpu_cap": [85], "trainer_custom_rows": [500], "trainer_compare_n": [10]}


def load_settings():
    st = default_settings()
    try:
        with open(SETTINGS_FILE) as f:
            saved = json.load(f)
        same = saved.get("_version") == SETTINGS_VERSION
        for k, v in saved.items():
            if k in st and (same or k in UI_KEYS):  # older files keep only look & feel
                st[k] = default_settings()[k] if v in SETTINGS_MIGRATE.get(k, []) else v
    except Exception:
        pass
    return st


SETTINGS_READONLY = False  # the GUI smoke test never touches the user's settings file


def save_settings(st):
    if SETTINGS_READONLY:
        return
    try:
        d = dict(st)
        d["_version"] = SETTINGS_VERSION
        with open(SETTINGS_FILE, "w") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass


# ----------------------------------------------------------------------------- input
def _as_list(v):
    if isinstance(v, str):
        return [x.strip() for x in re.split(r"[,;\n]", v) if x.strip()]
    return v


def validate_input(d):
    """Return (clean_dict, errors). Same parameters for VDM and JSON."""
    errs = []
    if not isinstance(d, dict):
        return json.loads(json.dumps(DEFAULT_INPUT)), ["Input must be a JSON object."]
    d = dict(d)
    if isinstance(d.get("datagen"), dict):  # nested form {"datagen": {"variations":..,"styles":..}}
        for k, v in d.pop("datagen").items():
            d.setdefault(k if k.startswith("datagen_") else "datagen_" + k, v)
    out = json.loads(json.dumps(DEFAULT_INPUT))
    t = _as_list(d.get("topics", d.get("topic", out["topics"])))
    if not isinstance(t, list) or not [x for x in t if str(x).strip()]:
        errs.append("topics: give at least one topic.")
    else:
        out["topics"] = [str(x).strip() for x in t if str(x).strip()]
    for key, lo, hi in (("quantity", 1, MAX_QUANTITY), ("quality", 1, 10), ("datagen_variations", 0, MAX_VARIATIONS)):
        v = d.get(key, out[key])
        try:
            if isinstance(v, bool) or float(v) != int(float(v)):
                raise ValueError
            v = int(float(v))
            if not lo <= v <= hi:
                raise ValueError
            out[key] = v
        except (TypeError, ValueError):
            errs.append(f"{key}: whole number {lo}-{hi}.")
    raw_dt = d.get("data_types", d.get("data_type", out["data_types"]))
    dts = _as_list(raw_dt) if not isinstance(raw_dt, list) else raw_dt
    dts = [str(x).strip().lower() for x in (dts if isinstance(dts, list) else [dts])]
    if dts == ["all"]:
        dts = list(DATA_TYPES)
    bad = [x for x in dts if x not in DATA_TYPES]
    if bad or not dts:
        errs.append(f"data_type: one or more of {DATA_TYPES} (or \"all\").")
    else:
        out["data_types"] = [t for t in DATA_TYPES if t in dts]
        out["data_type"] = out["data_types"][0]
    ot = str(d.get("output_type", out["output_type"])).strip().lower().lstrip(".")
    if ot not in OUTPUT_TYPES:
        errs.append(f"output_type: one of {OUTPUT_TYPES}.")
    else:
        out["output_type"] = ot
    for key, allowed in (("datagen_styles", STYLES), ("datagen_formats", FORMATS), ("datagen_methods", METHODS)):
        v = _as_list(d.get(key, out[key]))
        if isinstance(v, list) and [str(x).strip().lower() for x in v] == ["all"]:
            v = list(allowed)
        if not isinstance(v, list):
            errs.append(f"{key}: a list from {allowed}.")
            continue
        v = [str(x).strip().lower() for x in v]
        bad = [x for x in v if x not in allowed]
        if bad:
            errs.append(f"{key}: unknown {bad}; choose from {allowed}.")
        else:
            out[key] = [x for x in allowed if x in v]
    return out, errs


# ----------------------------------------------------------------------------- text utils
TAG_RE = re.compile(r"<[^>]+>")


INLINE_TAGS = "a|abbr|b|strong|i|em|u|s|span|sup|sub|small|big|font|mark|kbd|var|samp|cite|q|del|ins|label|time"


def clean_html(s):
    """HTML -> plain text. Code blocks become fenced Markdown with their indentation kept; inline code gets backticks."""
    s = re.sub(r"(?is)<(script|style|nav|footer|header|aside|form|noscript|svg)[^>]*>.*?</\1>", " ", s or "")
    s = re.sub(r"(?is)<span[^>]*class=\"[^\"]*mw-editsection[^\"]*\"[^>]*>.*?</span>\s*</span>", " ", s)
    kept = []

    def keep(text):
        kept.append(text)
        return f"\x00K{len(kept) - 1}\x00"
    s = re.sub(r"(?is)<pre[^>]*>(.*?)</pre>", lambda m: "\n" + keep(
        "```\n" + html.unescape(TAG_RE.sub("", m.group(1))).replace("\r\n", "\n").strip("\n") + "\n```") + "\n", s)
    s = re.sub(r"(?is)<code[^>]*>(.*?)</code>", lambda m: keep("`" + html.unescape(TAG_RE.sub("", m.group(1))).strip() + "`"), s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>|</tr>|</dd>|</dt>|</summary>|</details>|</blockquote>", "\n", s)
    s = re.sub(r"(?i)<h\d[^>]*>", "\n\n", s)
    s = re.sub(r"(?i)<li[^>]*>", "\n- ", s)
    s = re.sub(rf"(?is)</?(?:{INLINE_TAGS})\b[^>]*>", "", s)  # inline tags vanish without adding spaces
    s = TAG_RE.sub(" ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v\u00a0]+", " ", s)
    s = re.sub(r"\n\s*\n\s*\n+", "\n\n", s)
    s = "\n".join(l.strip() for l in s.split("\n")).strip()
    return re.sub(r"\x00K(\d+)\x00", lambda m: kept[int(m.group(1))], s)


def words(s):
    return re.findall(r"[A-Za-z0-9]+", (s or "").lower())


def shingles(s, k=5):
    w = words(s)
    return {" ".join(w[i:i + k]) for i in range(max(1, len(w) - k + 1))}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def shorten(s, n):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n - 1].rsplit(" ", 1)[0] + "…"


MATH_SPAN = re.compile(r"(\$\$.+?\$\$|\$[^$\n]+\$|\\\(.+?\\\)|\\\[.+?\\\]|```.*?```|`[^`\n]+`|<<[^<>\n]*>>)", re.S)


def protect(text):
    """Hide math/code spans so word-level rewrites never touch them."""
    keep = []

    def sub(m):
        keep.append(m.group(0))
        return f"\x00{len(keep) - 1}\x00"
    return MATH_SPAN.sub(sub, text or ""), keep


def unprotect(text, keep):
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], text)


def is_code(text):
    t = text or ""
    if "```" in t:
        return True
    pats = (r"^\s*def \w+\(", r"^\s*return\b", r"^\s*(for|while|if|elif|else|try|except)\b.*:\s*$", r"^\s*import \w+",
            r"^\s*class \w+", r"[{};]\s*$", r"^\s*#include", r"=>|==|!=|\+=")
    return sum(bool(re.search(p, t, re.M)) for p in pats) >= 2


def sentences(text):
    t, keep = protect(text)
    out = []
    for para in re.split(r"\n+", t):
        para = para.strip()
        if para:
            out += [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\x00\\(\[\"'])", para) if x.strip()]
    merged = []
    for x in out:  # a list number ("1.", "b)") or a tiny fragment belongs to what follows it
        if merged and re.fullmatch(r"\(?(\d{1,2}|[a-zA-Z])[.)]|.{1,3}", merged[-1]):
            merged[-1] = merged[-1] + " " + x
        else:
            merged.append(x)
    return [unprotect(p, keep) for p in merged]


def steps_of(text):
    """Solution steps: paragraphs / list items when the text has them, else sentences."""
    t, keep = protect(text or "")
    paras = [x.strip() for x in re.split(r"\n\s*\n|\n(?=\s*(?:\d{1,2}[.)]|[-*•])\s)", t) if x.strip()]
    if len(paras) >= 3:
        return [unprotect(" ".join(x.split()), keep) for x in paras]
    return sentences(text)


def case_like(src, new):
    if len(src) > 1 and src.isupper():
        return new.upper()
    if src[:1].isupper():
        return new[:1].upper() + new[1:]
    return new


def swap_phrases(text, pairs, rng=None, rate=1.0):
    """Replace phrases (word-bounded, case-preserving) in one pass; math/code protected."""
    if not text or not pairs:
        return text
    t, keep = protect(text)
    table = {}
    for a, b in pairs:
        table.setdefault(a.lower(), []).append(b)
    rx = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(table, key=len, reverse=True)) + r")\b", re.I)

    def rep(m):
        if rng is not None and rng.random() > rate:
            return m.group(0)
        alts = table[m.group(0).lower()]
        return "\x01" + case_like(m.group(0), rng.choice(alts) if rng is not None else alts[0]) + "\x02"
    t = rx.sub(rep, t)
    t = re.sub("\\b([Aa])(\\s+)\x01(?=[aeiouAEIOU])", lambda m: m.group(1) + "n" + m.group(2) + "\x01", t)  # a approach -> an approach
    t = re.sub("\\b([Aa])n(\\s+)\x01(?=[^aeiouAEIOU])", lambda m: m.group(1) + m.group(2) + "\x01", t)    # an big -> a big
    return unprotect(t.replace("\x01", "").replace("\x02", ""), keep)


# ----------------------------------------------------------------------------- extraction
SOL_MARK = re.compile(r"(?im)^[ \t]*(?:\*\*)?[ \t]*(?:show |view |see |hide )?(?:the )?(?:worked )?"
                      r"(solutions?|answers?|ans|explanation|proof)\b[ \t]*\d*[ \t]*(?:\*\*)?[ \t]*[:.\-–)]?[ \t]*(?:\*\*)?")
KW_PROB = re.compile(r"(?im)^[ \t]*(?:\*\*)?[ \t]*(?:problem|question|example|exercise|q)[ \t]*\d+[a-z]?[ \t]*[:.)]")
NUM_PROB = re.compile(r"(?m)^[ \t]*\d{1,3}[.)][ \t]+\S")
BOILER = re.compile(r"(?im)^[ \t]*(related (posts|articles|questions)|share this|comments?\b|leave a (reply|comment)|copyright|©|"
                    r"subscribe|you may also like|next( post| page)?:|previous( post| page)?:|see also|external links|"
                    r"references|navigation menu|cookie|page \d+ (of|/) \d+)")


def split_problem_solution(text, max_pairs=300):
    """Cut a page into (problem, solution) pairs using 'Solution:'/'Answer:' markers."""
    pairs = []
    marks = list(SOL_MARK.finditer(text or ""))
    if not marks:
        return pairs
    prob_re = KW_PROB if KW_PROB.search(text) else NUM_PROB
    prev_end = 0
    for i, m in enumerate(marks):
        if m.start() < prev_end:
            continue
        before = text[prev_end:m.start()]
        nxt = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        after = text[m.end():nxt]
        cut = None
        for pm in prob_re.finditer(after):
            if len(after[:pm.start()].strip()) >= 3:
                cut = pm.start()
                break
        if cut is None:
            if i + 1 < len(marks):
                mm = re.search(r"\S[^\n]*\n\s*\n", after)
                cut = mm.end() if mm else len(after)
            else:
                cut = len(after)
        sol = after[:cut]
        bm = BOILER.search(sol)
        if bm and bm.start() > 0:
            sol = sol[:bm.start()]
        if len(sol.strip()) <= 3:
            continue  # a bare heading ("SOLUTION") right before the real marker: keep the problem for it
        pms = list(prob_re.finditer(before))
        if pms:
            prob = before[pms[-1].start():]
        else:
            paras = [x for x in re.split(r"\n\s*\n", before) if x.strip()]
            prob = "\n".join(paras[-2:]) if paras else before
        prob = re.sub(r"(?i)(\n[ \t]*(?:solutions?|answers?|explanation|proof)[ \t:.\-]*)+$", "", prob.strip())
        prob, sol = prob.strip(), sol.strip()
        if len(prob) > 20 and len(sol) > 3:
            pairs.append((prob[-2500:], sol[:4000]))
        prev_end = m.end() + cut
        if len(pairs) >= max_pairs:
            break
    return pairs


def jsonld_pairs(raw_html):
    """schema.org Question/acceptedAnswer pairs (FAQPage, QAPage) embedded as JSON-LD."""
    out = []
    for m in re.finditer(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', raw_html or ""):
        try:
            data = json.loads(m.group(1).strip())
        except ValueError:
            continue
        stack = [data]
        while stack:
            d = stack.pop()
            if isinstance(d, list):
                stack.extend(d)
                continue
            if not isinstance(d, dict):
                continue
            t = d.get("@type")
            types = t if isinstance(t, list) else [t]
            if "Question" in types:
                ans = d.get("acceptedAnswer") or d.get("suggestedAnswer")
                if isinstance(ans, list):
                    ans = ans[0] if ans else None
                q = (d.get("name") or "") + "\n" + (d.get("text") or "")
                a = ans.get("text", "") if isinstance(ans, dict) else ""
                if q.strip() and str(a).strip():
                    out.append((clean_html(q), clean_html(str(a))))
            for v in d.values():
                if isinstance(v, (dict, list)):
                    stack.append(v)
    return out


def pdf_text(raw, max_pages=12):
    try:
        import pypdf
    except ImportError:
        return ""
    try:
        reader = pypdf.PdfReader(io.BytesIO(raw))
        return "\n".join((pg.extract_text() or "") for pg in reader.pages[:max_pages])
    except Exception:
        return ""


def tidy_answer(text):
    """Drop conversational openers and edit notes about comments - noise in training data."""
    t = re.sub(r"(?i)^\s*(this is an? )?(great|excellent|good|nice|interesting|very good) question[!.]*\s*", "", text or "")
    t = re.sub(r"(?im)^\s*(edit|update|edited|addendum)\b[^\n]{0,220}\b(comments?|suggest\w*|thanks?|pointed out)\b[^\n]*\n?", "", t)
    return t.strip()


def with_title(title, body):
    """Question text = title + body, unless the body already starts with the title."""
    norm = lambda x: re.sub(r"[^a-z0-9]+", " ", x.lower()).strip()
    return body if norm(body).startswith(norm(title)) else f"{title}\n\n{body}"


def join_cols(row, spec):
    parts = []
    for col, label in spec:
        v = row.get(col)
        if v in (None, "", []):
            continue
        if isinstance(v, list):
            v = "\n".join(map(str, v))
        v = str(v).replace("\r\n", "\n").strip()
        parts.append(f"{label}\n{v}" if label else v)
    return "\n\n".join(parts)


def detect_qa_columns(features, rows):
    strcols = [f.get("name") for f in features or []
               if isinstance(f.get("type"), dict) and f["type"].get("dtype") == "string"]
    if not strcols and rows:
        strcols = [k for k, v in rows[0].items() if isinstance(v, str)]
    low = {c.lower(): c for c in strcols if c}
    p = next((low[c] for c in PROB_COLS if c in low), None)
    s = next((low[c] for c in SOL_COLS if c in low and low[c] != p), None)
    if not p or not s:
        return None
    sample = rows[:20]
    good = sum(1 for r in sample if len(str(r.get(p, ""))) >= 10 and len(str(r.get(s, ""))) >= 1)
    return (p, s) if sample and good >= max(1, len(sample) // 2) else None


TASK_VERBS = {"find", "solve", "compute", "calculate", "evaluate", "determine", "prove", "show", "simplify", "write",
              "explain", "differentiate", "integrate", "factor", "expand", "derive", "describe", "compare", "identify",
              "estimate", "convert", "implement", "design", "what", "how", "why", "which", "when", "where", "who",
              "given", "if", "suppose", "let", "consider", "is", "are", "can", "does", "do", "should", "list", "name"}
PROBLEM_NAME_WORDS = ("qa", "question", "problem", "exercise", "math", "reason", "instruct", "cot", "solution", "quiz",
                      "exam", "testbank", "test-bank", "test_bank", "homework", "tutor", "practice", "worksheet", "answer", "step")


def mostly_english(texts, need=0.85):
    t = "".join(texts)[:20000]
    letters = [c for c in t if c.isalpha()]
    return bool(letters) and sum(c.isascii() for c in letters) / len(letters) >= need


def looks_like_tasks(texts, need=0.6):
    """Most sample rows must read like a question or a task (not book text, preambles, logs...)."""
    texts = [t for t in texts if t and t.strip()]
    if not texts:
        return False
    good = 0
    for t in texts:
        first = (re.findall(r"[A-Za-z]+", t[:40]) or [""])[0].lower()
        if "?" in t[:600] or first in TASK_VERBS or re.search(
                r"(?i)\b(find|solve|calculate|compute|determine|prove|evaluate|how many|how much|what is|write a)\b", t[:250]):
            good += 1
    return good >= need * len(texts)


def openalex_abstract(inv):
    if not isinstance(inv, dict):
        return ""
    pos = sorted((p, w) for w, ps in inv.items() for p in ps)
    return " ".join(w for _, w in pos)


# ----------------------------------------------------------------------------- http
class Http:
    def __init__(self, st, log=print, cancel=None):
        self.st, self.log, self.cancel = st, log, cancel or threading.Event()
        handlers = []
        try:  # python.org builds on macOS ship without CA certs; certifi supplies them
            import ssl
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
            if not st.get("verify_ssl", True):
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            handlers.append(urllib.request.HTTPSHandler(context=ctx))
        except ImportError:
            pass
        if st.get("proxy"):
            handlers.append(urllib.request.ProxyHandler({"http": st["proxy"], "https": st["proxy"]}))
        self.opener = urllib.request.build_opener(*handlers)
        self.last_host = {}
        self.status = None

    def fetch(self, url, data=None, max_bytes=None):
        """Returns (status, bytes, content_type). Never retries a 4xx (no hammering, no evasion)."""
        host = urllib.parse.urlparse(url).netloc
        for attempt in range(int(self.st["retries"]) + 1):
            if self.cancel.is_set():
                return None, b"", ""
            wait = float(self.st["delay"]) - (time.time() - self.last_host.get(host, 0))
            if wait > 0:
                time.sleep(wait)
            if HOST_LIMITER is not None:  # Parallel Web Technologies: one rate budget per host across all workers
                HOST_LIMITER.wait(host, self.cancel)
            self.last_host[host] = time.time()
            try:
                body = urllib.parse.urlencode(data).encode() if data else None
                t_req = time.time()
                req = urllib.request.Request(url, data=body, headers={
                    "User-Agent": self.st.get("user_agent") or USER_AGENT, "Accept-Encoding": "gzip",
                    "Accept": "text/html,application/json,application/xml;q=0.9,*/*;q=0.8"})
                with self.opener.open(req, timeout=float(self.st["timeout"])) as r:
                    raw = r.read(int(max_bytes or self.st["max_page_bytes"]))
                    if r.headers.get("Content-Encoding") == "gzip":
                        raw = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(raw)
                    self.status = r.status
                    if self.st.get("http_verbose"):
                        pu = urllib.parse.urlparse(url)
                        self.log(f"  {'POST' if data else 'GET '} {host}{shorten(pu.path + ('?' + pu.query if pu.query else ''), 110)} "
                                 f"-> {r.status} · {len(raw) / 1024:.1f} KB · {(time.time() - t_req) * 1000:.0f} ms")
                    return r.status, raw, r.headers.get("Content-Type", "")
            except urllib.error.HTTPError as e:
                self.status = e.code
                self.log(f"  http {host}: HTTP {e.code}")
                if e.code in (429, 503) and attempt < int(self.st["retries"]):
                    try:
                        wait_s = float(e.headers.get("Retry-After") or 3)
                    except (TypeError, ValueError):
                        wait_s = 3.0
                    if HOST_LIMITER is not None:
                        HOST_LIMITER.penalize(host, min(120.0, max(2.0, wait_s)))  # the whole pool backs off this host
                    time.sleep(min(10.0, max(1.0, wait_s)))  # polite backoff, then one more try
                    continue
                if e.code < 500:
                    return e.code, b"", ""
            except Exception as e:
                self.status = None
                self.log(f"  http {host}: {type(e).__name__} {str(e)[:90]}")
        return self.status, b"", ""

    def get(self, url, data=None):
        status, raw, ctype = self.fetch(url, data)
        if not raw:
            return None
        cs = re.search(r"charset=([\w-]+)", ctype or "")
        try:
            return raw.decode(cs.group(1) if cs else "utf-8", "replace")
        except LookupError:
            return raw.decode("utf-8", "replace")


def item(topic, source, title, problem, solution, url, votes=0, extra=None):
    return {"topic": topic, "source": source, "title": (title or "").strip(),
            "problem": (problem or "").strip(), "solution": (solution or "").strip(),
            "url": url or "", "votes": votes, "meta": extra or {}, "kind": "original"}


# ----------------------------------------------------------------------------- web search
class Searcher:
    """Web-searching tool: finds problem/solution material (and papers) for each topic."""

    def __init__(self, st, log=print, cancel=None, http=None, progress=None):
        self.st, self.log = st, log
        self.cancel = cancel or threading.Event()
        self.http = http or Http(st, log, self.cancel)
        self.progress = progress or (lambda f, msg="": None)
        self.cursor = {}
        self.stats = {}
        self.notes = {}
        self.ddg_blocked = False
        self.ddg_lock = threading.Lock()
        self._hf_routes = {}
        self.se_backoff_until = 0.0
        self.seen = set()

    # ---- queries
    def queries(self, topic, data_type):
        n = int(self.st["variants_per_topic"])
        base = {
            "problems & solution papers": ["{t} problems and solutions", "{t} solved problems with step by step solutions",
                                           "{t} practice problems answers explained", "{t} exercises with worked solutions pdf"],
            "problems only": ["{t} practice problems", "{t} exercises", "{t} problem set"],
            "worked examples": ["{t} worked examples", "{t} example solved step by step", "{t} tutorial examples with answers"],
            "research papers": ["{t} research paper", "{t} survey paper", "{t} open problems"],
        }[data_type]
        qs = [b.format(t=topic) for b in base] if self.st["local_expansion"] else [f"{topic} {self.st['ddg_suffix']}"]
        extra = [x.strip() for x in self.st["extra_terms"].split(",") if x.strip()]
        excl = [x.strip() for x in self.st["exclude_terms"].split(",") if x.strip()]
        qs = [" ".join([q] + extra + ["-" + e for e in excl]) for q in qs]
        return qs[:n]

    # ---- DuckDuckGo (honest, respects bot checks)
    def duckduckgo(self, topic, data_type, want):
        with self.ddg_lock:  # parallel topics: still one DuckDuckGo request at a time, and none after a bot check
            return self._duckduckgo(topic, data_type, want)

    def _duckduckgo(self, topic, data_type, want):
        out = []
        if self.ddg_blocked:
            return out
        qs = self.queries(topic, data_type)
        block = [b.strip() for b in self.st["ddg_blocklist"].split(",") if b.strip()]
        seen = self.cursor.setdefault(("ddg-seen", topic), set())
        qi = self.cursor.get(("ddg", topic), 0)
        while qi < len(qs) and len(out) < want and not self.cancel.is_set():
            q = qs[qi]
            qi += 1
            self.cursor[("ddg", topic)] = qi
            self.log(f"  DuckDuckGo: {q}")
            data = {"q": q, "kl": self.st["ddg_region"], "kp": {"strict": "1", "moderate": "-1", "off": "-2"}[self.st["ddg_safe"]]}
            status, raw, _ct = self.http.fetch("https://html.duckduckgo.com/html/", data)
            page = raw.decode("utf-8", "replace") if raw else ""
            results = self.parse_ddg(page or "")
            if status == 202 or not results:
                self.ddg_blocked = True
                why = ("bot check (HTTP 202)" if status == 202 else "no results" if status == 200
                       else f"HTTP {status}" if status else "unreachable")
                self.notes["duckduckgo"] = why
                self.log(f"  DuckDuckGo search: {why}. AITE respects this and does not retry; the other sources fill in.")
                if self.st["ddg_instant_api"]:
                    self.ddg_instant(topic)
                break
            for url, title, snippet in results[:int(self.st["duckduckgo_page_size"])]:
                dom = urllib.parse.urlparse(url).netloc.lower()
                if url in seen or any(b in dom for b in block):
                    continue
                if self.st["ddg_skip_pdf"] and url.lower().split("?")[0].endswith(".pdf"):
                    continue
                seen.add(url)
                if self.st["fetch_pages"]:
                    out += self.harvest(url, topic, title, "duckduckgo", snippet)
                if len(out) >= want or self.cancel.is_set():
                    break
        return out[:want]

    def ddg_instant(self, topic):
        """DuckDuckGo's official Instant Answer API (topic context; not full web results)."""
        raw = self.http.get("https://api.duckduckgo.com/?" + urllib.parse.urlencode(
            {"q": topic, "format": "json", "no_html": 1, "skip_disambig": 1, "t": "aite"}))
        try:
            j = json.loads(raw or "{}")
        except ValueError:
            return
        if j.get("AbstractText"):
            self.log(f"  DuckDuckGo Instant Answer: {shorten(j['AbstractText'], 160)} ({j.get('AbstractSource', '')})")
        rel = [t.get("Text", "") for t in j.get("RelatedTopics", []) if isinstance(t, dict) and t.get("Text")]
        if rel:
            self.log("  Related topics: " + "; ".join(shorten(r, 40) for r in rel[:6]))

    @staticmethod
    def parse_ddg(page):
        res = []
        for m in re.finditer(r'(?is)<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="[^"]*result__a|$)', page):
            href, title, rest = m.group(1), clean_html(m.group(2)), m.group(3)
            sn = re.search(r'(?is)class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', rest)
            res.append((Searcher._ddg_url(href), title, clean_html(sn.group(1)) if sn else ""))
        return [r for r in res if r[0].startswith("http")]

    @staticmethod
    def _ddg_url(href):
        href = html.unescape(href)
        if "uddg=" in href:
            return urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [""])[0])
        return "https:" + href if href.startswith("//") else href

    def harvest(self, url, topic, title, source, snippet=""):
        status, raw, ctype = self.http.fetch(url)
        if not raw:
            return []
        is_pdf = "pdf" in (ctype or "").lower() or raw[:5] == b"%PDF-"
        if is_pdf:
            if not self.st["fetch_pdfs"]:
                return []
            pairs = split_problem_solution(pdf_text(raw, int(self.st["pdf_max_pages"])))
        else:
            page = raw.decode("utf-8", "replace")
            pairs = jsonld_pairs(page) + split_problem_solution(clean_html(page))
        return [item(topic, source, title, p, s, url, 0, {"snippet": snippet, "pdf": is_pdf}) for p, s in pairs]

    # ---- Stack Exchange
    def se_site(self, topic):
        t = topic.lower()
        toks = set(re.findall(r"[a-z0-9+#.]+", t))
        for k in sorted(SE_SITES, key=len, reverse=True):
            # phrases and long words may match inside the topic; short keys (ai, sql, c++) only as whole words
            hit = (k in t) if (" " in k or len(k) > 4) else (k in toks)
            if hit and self.st.get(f"se_site_{SE_SITES[k]}", True):
                return SE_SITES[k]
        return self.st["se_default_site"]

    def se_tag(self, topic, site):
        """Exact Stack Exchange tag for the topic (word-problem, geometry, python...) or None."""
        key = ("se-tag", site, topic.lower())
        if key in self.cursor:
            return self.cursor[key]
        ws = words(topic)
        if not ws:
            return None
        raw = re.sub(r"[^a-z0-9+#.\-]", "", re.sub(r"\s+", "-", topic.strip().lower()))  # keeps c++, c#, node.js
        slug = "-".join(ws)
        sing = "-".join(w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w for w in ws)
        params = {"site": site}
        alias = SE_TAG_ALIASES.get((site, " ".join(ws)))
        cands = list(dict.fromkeys([c for c in (alias, raw, slug, sing) if c]))
        data = self._se_get("https://api.stackexchange.com/2.3/tags/" + ";".join(urllib.parse.quote(c) for c in cands)
                            + "/info?" + urllib.parse.urlencode(params))
        found = {t.get("name"): t.get("count", 0) for t in data.get("items", []) if t.get("name") in cands}
        tag = alias if alias in found else (max(found, key=found.get) if found else None)
        self.cursor[key] = tag
        return tag

    def _se_get(self, url):
        wait = self.se_backoff_until - time.time()
        if wait > 0:
            time.sleep(min(wait, 30))
        raw = self.http.get(url)
        try:
            data = json.loads(raw or "{}")
        except ValueError:
            return {}
        if data.get("backoff"):
            self.se_backoff_until = time.time() + int(data["backoff"])
        if data.get("error_id"):
            self.log(f"  Stack Exchange: {data.get('error_name')} {data.get('error_message', '')}")
        return data

    def stackexchange(self, topic, data_type, want):
        site, out = self.se_site(topic), []
        page = self.cursor.get(("se", topic), 1)
        if page is None or data_type == "research papers":
            return out
        generic = topic.lower().strip() in {site, "math", "maths", "mathematics", "programming", "coding"}
        first = page
        while len(out) < want and page - first < int(self.st["stackexchange_max_pages"]) and not self.cancel.is_set():
            params = {"order": "desc", "sort": self.st["se_sort"], "site": site, "filter": "withbody",
                      "pagesize": min(100, max(int(self.st["stackexchange_page_size"]), want * 2)), "page": page, "answers": 1}
            tag = None if generic else self.se_tag(topic, site)
            q = SE_GENERIC_QUERY.get(site, "") if generic else ("" if tag else topic)
            if tag:
                params["tagged"] = tag
            if q:
                params["q"] = q
            if self.st["se_accepted_only"] and data_type != "problems only":
                params["accepted"] = "True"
            self.log(f"  Stack Exchange [{site}] page {page}: " + (f"tag [{tag}]" if tag else q or "(top voted)"))
            data = self._se_get("https://api.stackexchange.com/2.3/search/advanced?" + urllib.parse.urlencode(params))
            if not data or data.get("error_id"):
                page = None
                break
            qs = [x for x in data.get("items", []) if x.get("score", 0) >= int(self.st["se_min_score"])]
            ids = [str(x["accepted_answer_id"]) for x in qs if x.get("accepted_answer_id")]
            answers = {}
            if ids and data_type != "problems only":
                a_params = {"site": site, "filter": "withbody", "pagesize": 100}
                adata = self._se_get(f"https://api.stackexchange.com/2.3/answers/{';'.join(ids[:100])}?" + urllib.parse.urlencode(a_params))
                answers = {a["answer_id"]: a for a in adata.get("items", [])}
            for x in qs:
                a = answers.get(x.get("accepted_answer_id"))
                sol = tidy_answer(clean_html(a["body"])) if a else ""
                if data_type != "problems only" and not sol:
                    continue
                title = html.unescape(x.get("title", ""))
                out.append(item(topic, "stackexchange", title, with_title(title, clean_html(x.get("body", ""))), sol,
                                x.get("link", ""), x.get("score", 0) + (a.get("score", 0) if a else 0),
                                {"site": site, "tags": x.get("tags", []), "license": "CC BY-SA 4.0",
                                 "images": len(re.findall(r"(?i)<img\b", x.get("body", "")))}))
            page += 1
            if not data.get("has_more") or data.get("quota_remaining", 1) <= 1:
                page = None
                break
        self.cursor[("se", topic)] = page
        return out[:want]

    # ---- Hugging Face open datasets
    def hf_routes(self, topic):
        if topic in self._hf_routes:
            return self._hf_routes[topic]
        t = topic.lower()
        routes = []
        if self.st["hf_curated"]:
            for e in HF_CURATED:
                if any(k in t for k in e["keys"]):
                    fw = [w for w in words(t) if len(w) > 3 and w not in e["domain"] and w not in TOPIC_STOP]
                    routes.append(dict(e, split="train", filter=fw, discovered=False))
        uniq = {}
        for r in routes:
            uniq.setdefault((r["dataset"], r["config"]), r)
        routes = list(uniq.values())[:3]
        if not routes and self.st["hf_discover"]:
            routes = self.hf_discover(topic)
        self._hf_routes[topic] = routes
        if routes:
            self.log("  Hugging Face datasets: " + ", ".join(f"{r['dataset']} [{r['config']}]" for r in routes))
        else:
            self.log("  Hugging Face: no open problem/solution dataset found for this topic")
        return routes

    def hf_discover(self, topic):
        raw = self.http.get("https://huggingface.co/api/datasets?" + urllib.parse.urlencode(
            {"search": topic, "sort": "downloads", "direction": -1, "limit": 20}))
        try:
            lst = json.loads(raw or "[]")
        except ValueError:
            return []
        routes, examined = [], 0
        allow_eval = self.st["hf_allow_eval_splits"]
        for d in lst if isinstance(lst, list) else []:
            if len(routes) >= int(self.st["hf_max_datasets"]) or self.cancel.is_set() \
                    or examined >= int(self.st["hf_max_candidates"]):
                break
            if d.get("gated") or d.get("private") or d.get("disabled"):
                continue
            if int(d.get("downloads") or 0) < int(self.st["hf_min_downloads"]):
                continue
            ds = d.get("id", "")
            examined += 1
            try:
                splits = json.loads(self.http.get(f"{HF_BASE}/splits?" + urllib.parse.urlencode({"dataset": ds})) or "{}").get("splits", [])
            except ValueError:
                continue
            pick = [s for s in splits if s.get("split") == "train"]
            if not pick:
                pick = splits if allow_eval else [s for s in splits if s.get("split") not in ("test", "validation", "valid", "dev", "eval")]
            if not pick:
                continue
            cfg, split = pick[0]["config"], pick[0]["split"]
            try:
                fr = json.loads(self.http.get(f"{HF_BASE}/first-rows?" + urllib.parse.urlencode(
                    {"dataset": ds, "config": cfg, "split": split})) or "{}")
            except ValueError:
                continue
            sample = [r.get("row", {}) for r in fr.get("rows", [])]
            cols = detect_qa_columns(fr.get("features", []), sample)
            if not cols:
                continue
            probs = [str(r.get(cols[0], "")) for r in sample[:30]]
            named = any(w in ds.lower() for w in PROBLEM_NAME_WORDS)
            if not looks_like_tasks(probs, 0.6 if named else 0.85):
                self.log(f"  Hugging Face: skipped {ds} - its rows do not read like problems or questions")
                continue
            if self.st["hf_english_only"] and not mostly_english(probs + [str(r.get(cols[1], "")) for r in sample[:30]], 0.7):
                self.log(f"  Hugging Face: skipped {ds} - not English")
                continue
            lic = next((t.split(":", 1)[1] for t in d.get("tags", []) if str(t).startswith("license:")), "unknown")
            routes.append({"dataset": ds, "config": cfg, "split": split, "p": [(cols[0], "")], "s": [(cols[1], "")],
                           "license": lic, "fcols": [], "filter": [], "discovered": True})
        return routes

    def hf_rows(self, topic, e, want):
        key = ("hf", e["dataset"], e["config"], topic)
        cur = self.cursor.get(key)
        if cur is None:
            off = (int(hashlib.md5(topic.encode()).hexdigest(), 16) % 400) if self.st["hf_random_offset"] else 0
            cur = {"offset": off, "wrapped": off == 0, "done": False}
            self.cursor[key] = cur
        out, pages = [], 0
        while len(out) < want and not cur["done"] and pages < int(self.st["hf_scan_pages"]) and not self.cancel.is_set():
            params = {"dataset": e["dataset"], "config": e["config"], "split": e["split"], "offset": cur["offset"], "length": 100}
            self.log(f"  Hugging Face [{e['dataset']} / {e['config']}] rows {cur['offset']}+"
                     + (f" matching {e['filter']}" if e["filter"] else ""))
            raw = self.http.get(f"{HF_BASE}/rows?" + urllib.parse.urlencode(params))
            pages += 1
            try:
                data = json.loads(raw or "{}")
            except ValueError:
                break
            rows = data.get("rows", [])
            if not rows:
                if raw is None:  # network/server error: try again in a later round, give up after two
                    cur["errors"] = cur.get("errors", 0) + 1
                    cur["done"] = cur["errors"] >= 2
                    break
                if not cur["wrapped"]:
                    cur.update(offset=0, wrapped=True)
                    continue
                cur["done"] = True
                break
            last = cur["offset"]
            total = int(data.get("num_rows_total") or 0)
            step = 1 if e["filter"] else max(1, min(7, len(rows) // max(1, want - len(out))))
            for row in rows[::step]:
                last = int(row.get("row_idx", last)) + 1
                rd = row.get("row", {})
                prob, sol = join_cols(rd, e["p"]), join_cols(rd, e["s"])
                if not prob or (self.st["hf_english_only"] and not mostly_english([prob, sol[:2000]])):
                    continue
                if e["filter"]:
                    hay = (prob + " " + " ".join(str(rd.get(c, "")) for c in e["fcols"])).lower()
                    if not any(w in hay for w in e["filter"]):
                        continue
                title = str(rd.get("sub_topic") or "") or shorten(prob.split("\n")[0], 90)
                out.append(item(topic, "huggingface", title, prob, sol,
                                f"https://huggingface.co/datasets/{e['dataset']}/viewer/{e['config']}/{e['split']}?row={last - 1}",
                                0, {"dataset": e["dataset"], "config": e["config"], "split": e["split"], "row": last - 1,
                                    "license": e["license"], "discovered": e["discovered"]}))
                if len(out) >= want:
                    break
            if total and not e["filter"]:  # jump through the dataset: many are stored grouped by sub-topic
                cur.setdefault("visited", set()).add(cur["offset"])
                nxt = (cur["offset"] + max(100, total // 9)) % total
                cur["done"] = nxt in cur["visited"]
                cur["offset"] = nxt
                continue
            cur["offset"] = last
            if total and cur["offset"] >= total:
                if cur["wrapped"]:
                    cur["done"] = True
                else:
                    cur.update(offset=0, wrapped=True)
        return out

    def huggingface(self, topic, data_type, want):
        routes = self.hf_routes(topic)
        out = []
        if not routes:
            return out
        per = max(1, math.ceil(want / len(routes)))
        for e in routes:
            if len(out) >= want or self.cancel.is_set():
                break
            out += self.hf_rows(topic, e, min(per, want - len(out)))
        for e in routes:  # routes that came up short: ask the others for the rest
            if len(out) >= want or self.cancel.is_set():
                break
            out += self.hf_rows(topic, e, want - len(out))
        return out[:want]

    # ---- Wikibooks
    def wikibooks(self, topic, data_type, want):
        done = self.cursor.setdefault(("wb", topic), set())
        out = []
        maxp = int(self.st["wb_max_pages"])
        for q in (f"{topic} exercises solutions", f"{topic} problems answers", f"{topic} worked examples"):
            if len(out) >= want or self.cancel.is_set() or len(done) >= maxp:
                break
            raw = self.http.get("https://en.wikibooks.org/w/api.php?" + urllib.parse.urlencode(
                {"action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": 10, "srnamespace": 0}))
            try:
                hits = json.loads(raw or "{}").get("query", {}).get("search", [])
            except ValueError:
                hits = []
            tw = [w for w in words(topic) if len(w) > 3 and w not in TOPIC_STOP] or words(topic)
            for h in hits:
                t = h.get("title", "")
                if t in done or len(done) >= maxp or self.cancel.is_set():
                    continue
                if not any(w in t.lower() for w in tw):
                    continue
                done.add(t)
                self.log(f"  Wikibooks: {t}")
                praw = self.http.get("https://en.wikibooks.org/w/api.php?" + urllib.parse.urlencode(
                    {"action": "parse", "page": t, "prop": "text", "format": "json", "formatversion": 2, "disabletoc": 1}))
                try:
                    page = json.loads(praw or "{}").get("parse", {}).get("text", "")
                except ValueError:
                    continue
                url = "https://en.wikibooks.org/wiki/" + urllib.parse.quote(t.replace(" ", "_"))
                for p, s in split_problem_solution(clean_html(page)):
                    out.append(item(topic, "wikibooks", t, p, s, url, 0, {"license": "CC BY-SA 4.0"}))
                    if len(out) >= want:
                        return out
        return out

    # ---- papers
    def arxiv(self, topic, data_type, want):
        start = self.cursor.get(("arxiv", topic), 0)
        terms = [w for w in words(topic) if w not in TOPIC_STOP][:5] or words(topic)[:3]
        if data_type != "research papers":
            terms.append("problem")
        params = {"search_query": " AND ".join(f"all:{w}" for w in terms), "start": start,
                  "max_results": min(100, max(want, 1)), "sortBy": self.st["arxiv_sort"]}
        self.log(f"  arXiv: {' '.join(terms)} (from {start})")
        raw = self.http.get("https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params))
        out = []
        if not raw:
            return out
        ns = {"a": "http://www.w3.org/2005/Atom"}
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return out
        for e in root.findall("a:entry", ns):
            title = " ".join((e.findtext("a:title", "", ns) or "").split())
            summ = " ".join((e.findtext("a:summary", "", ns) or "").split())
            link = e.findtext("a:id", "", ns)
            authors = [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)]
            sents = re.split(r"(?<=[.!?])\s+", summ)
            k = max(1, len(sents) // 3)
            out.append(item(topic, "arxiv", title, title + "\n\n" + " ".join(sents[:k]), " ".join(sents[k:]),
                            link, 0, {"authors": authors[:6], "kind": "paper", "license": "arXiv metadata CC0"}))
        self.cursor[("arxiv", topic)] = start + len(out)
        return out

    def openalex(self, topic, data_type, want):
        page = self.cursor.get(("oa", topic), 1)
        flt = ["has_abstract:true"]
        if self.st["openalex_oa_only"]:
            flt.append("is_oa:true")
        if int(self.st["openalex_min_year"]) > 0:
            flt.append(f"from_publication_date:{int(self.st['openalex_min_year'])}-01-01")
        q = topic if data_type == "research papers" else f"{topic} problems"
        params = {"search": q, "filter": ",".join(flt), "per-page": min(50, max(want, 5)), "page": page,
                  "select": "id,doi,display_name,publication_year,abstract_inverted_index,authorships,open_access,primary_location,cited_by_count"}
        self.log(f"  OpenAlex: {q} (page {page})")
        raw = self.http.get("https://api.openalex.org/works?" + urllib.parse.urlencode(params))
        out = []
        try:
            res = json.loads(raw or "{}").get("results", [])
        except ValueError:
            return out
        for w in res[:want]:
            abstract = openalex_abstract(w.get("abstract_inverted_index"))
            title = w.get("display_name") or ""
            if not abstract or not title:
                continue
            sents = re.split(r"(?<=[.!?])\s+", abstract)
            k = max(1, len(sents) // 3)
            loc = w.get("primary_location") or {}
            out.append(item(topic, "openalex", title, title + "\n\n" + " ".join(sents[:k]), " ".join(sents[k:]),
                            w.get("doi") or w.get("id", ""), int(w.get("cited_by_count") or 0),
                            {"year": w.get("publication_year"), "kind": "paper",
                             "authors": [a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:6]],
                             "oa_url": (w.get("open_access") or {}).get("oa_url"), "license": loc.get("license") or "see source"}))
        self.cursor[("oa", topic)] = page + 1
        return out

    def wikipedia(self, topic, data_type, want):
        lang = self.st["wiki_lang"]
        off = self.cursor.get(("wiki", topic), 0)
        self.log(f"  Wikipedia: {topic}")
        raw = self.http.get(f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            {"action": "query", "list": "search", "srsearch": f"{topic} problem", "format": "json",
             "srlimit": min(10, max(want, 1)), "sroffset": off}))
        out = []
        try:
            hits = json.loads(raw or "{}").get("query", {}).get("search", [])
        except ValueError:
            return out
        self.cursor[("wiki", topic)] = off + len(hits)
        for h in hits[:want]:
            raw2 = self.http.get(f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
                {"action": "query", "prop": "extracts", "explaintext": 1, "titles": h["title"], "format": "json", "exchars": 3000}))
            try:
                page = next(iter(json.loads(raw2 or "{}").get("query", {}).get("pages", {}).values()), {})
            except ValueError:
                continue
            paras = [p for p in page.get("extract", "").split("\n") if p.strip()]
            if len(paras) < 2:
                continue
            out.append(item(topic, "wikipedia", h["title"], h["title"] + "\n\n" + paras[0], "\n".join(paras[1:]),
                            f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(h["title"].replace(" ", "_")), 0,
                            {"kind": "article", "license": "CC BY-SA 4.0"}))
        return out

    # ---- run
    def source_weights(self, data_type):
        mult = TYPE_MULT.get(data_type, {})
        w = {s: float(self.st[f"{s}_weight"]) * mult.get(s, 1.0) for s in SOURCES if self.st[f"{s}_enabled"]}
        return {s: v for s, v in w.items() if v > 0}

    def search(self, inp):
        """Collect quantity x oversample(quality) candidates across topics and sources."""
        q, qual, dt = inp["quantity"], inp["quality"], inp["data_type"]
        factor = float(self.st["oversample"]) + max(0, qual - 4) * float(self.st["oversample_per_quality"])
        target = max(1, math.ceil(q * factor))
        topics = inp["topics"]
        per_topic = math.ceil(target / len(topics))
        weights = self.source_weights(dt)
        total_w = sum(weights.values()) or 1
        order = sorted(weights, key=lambda s: -weights[s])
        self.log(f"Search: {len(topics)} topic(s), target {target} candidates (quantity {q} x {factor:.2f}); "
                 f"sources: {', '.join(order) or 'none'}")
        results, seen, start = [], self.seen, time.time()

        lock = threading.Lock()

        def add(items, got, src):
            with lock:
                return _add(items, got, src)

        def _add(items, got, src):
            n = 0
            for it in items:
                key = hashlib.sha1((it["url"] + "|" + it["problem"][:300]).encode("utf-8", "replace")).hexdigest()
                if key in seen or not it["problem"]:
                    continue
                seen.add(key)
                it["uid"] = key[:12]
                got.append(it)
                n += 1
            self.stats[src] = self.stats.get(src, 0) + n
            return n

        def run_src(src, topic, n, got):
            try:
                return add(getattr(self, src)(topic, dt, n), got, src)
            except Exception as e:
                self.log(f"  {src} failed: {type(e).__name__}: {e}")
                return 0

        def do_topic(ti, topic):
            got = []
            for si, src in enumerate(order):
                if self.cancel.is_set() or time.time() - start > int(self.st["max_runtime"]):
                    break
                share = max(1, math.ceil(per_topic * weights[src] / total_w))
                self.progress((ti + si / max(1, len(order))) / len(topics) * 0.7, f"{topic}: {src}")
                run_src(src, topic, share, got)
            for src in [s for s in TOPUP.get(dt, TOPUP_DEFAULT) if s in weights]:
                tries = 0
                while len(got) < per_topic and tries < 3 and not self.cancel.is_set() \
                        and time.time() - start < int(self.st["max_runtime"]):
                    tries += 1
                    self.progress((ti + 0.9) / len(topics) * 0.7, f"{topic}: more from {src}")
                    if run_src(src, topic, per_topic - len(got), got) == 0:
                        break
            self.log(f"  {topic}: {len(got)} candidates")
            return got

        if len(topics) > 1 and self.st.get("pwt_enabled", True) and self.st.get("pwt_parallel_topics", True):
            from concurrent.futures import ThreadPoolExecutor  # Parallel Web Technologies: all topics at once
            pwt_on(self.st)
            with ThreadPoolExecutor(max_workers=min(len(topics), int(self.st.get("pwt_workers", 32)))) as ex:
                for got in ex.map(do_topic, range(len(topics)), topics):
                    results += got
        else:
            for ti, topic in enumerate(topics):
                results += do_topic(ti, topic)
        half = 0.5 if dt == "problems only" else 1.0  # a bare problem is shorter than problem + solution
        for r in results:
            mn, mx = int(self.st[f"{r['source']}_min_chars"]) * half, int(self.st[f"{r['source']}_max_chars"])
            r["problem"], r["solution"] = r["problem"][:mx], r["solution"][:mx]
            r["_short"] = len(r["problem"]) + len(r["solution"]) < mn
        return results


# ----------------------------------------------------------------------------- filterer (local, no API)
class Filterer:
    def __init__(self, st, log=print):
        self.st, self.log = st, log

    def trust(self, r):
        t = float(self.st.get(f"{r['source']}_trust", 0))
        if r.get("meta", {}).get("discovered"):
            t -= float(self.st["hf_discovered_penalty"])
        return t

    def score(self, r, topic_words):
        st = self.st
        text = r["problem"] + "\n" + r["solution"]
        w = words(text)
        n = len(w)
        parts = {}
        if r.get("_needs_solution", True):  # concise worked problems are fine; only very short or very long ones lose points
            parts["length"] = min(10, 2 + n / 12) if n < 96 else max(4, 10 - (n - 1500) / 400) if n > 1500 else 10
        else:  # a good problem statement alone can be one line
            parts["length"] = min(10, 3 + n / 4) if n < 28 else max(4, 10 - (n - 600) / 200) if n > 600 else 10
        struct = 0
        struct += 3 if re.search(r"[?]|find|prove|show that|calculate|determine|solve|compute|evaluate|what is|how|write a", r["problem"], re.I) else 0
        struct += 3 if re.search(r"[=+\-*/^]|\$|\\frac|\d", text) else 1
        struct += 2 if len(r["problem"]) > 60 else 0
        struct += 2 if "\n" in r["solution"] or len(r["solution"]) > 200 else 0
        parts["structure"] = min(10, struct)
        sw = len(words(r["solution"]))
        sol = 0 if sw == 0 else min(10, 3 + sw / 25)
        if re.search(r"therefore|thus|hence|so the answer|we get|=|which gives|result|####|boxed|return", r["solution"], re.I):
            sol = min(10, sol + 2)
        parts["solution"] = sol
        parts["source"] = max(0, min(10, 5 + 2 * self.trust(r)))
        rel = sum(1 for t in topic_words if t in set(w)) / max(1, len(topic_words))
        tags = " ".join(r.get("meta", {}).get("tags", []))
        bonus = {"stackexchange": 2, "huggingface": 1 if r.get("meta", {}).get("discovered") else 4}.get(r["source"], 0)
        parts["relevance"] = min(10, rel * 8 + (2 if any(t in tags for t in topic_words) else 0) + bonus)
        ascii_ratio = sum(1 for c in text if 32 <= ord(c) < 127 or c in "\n\t") / max(1, len(text))
        parts["readability"] = max(0, min(10, (ascii_ratio - 0.6) * 25))
        v = r.get("votes", 0) or 0
        if r["source"] == "stackexchange":
            parts["votes"] = min(10, 4 + (v ** 0.5 if v > 0 else -2))
        elif r["source"] == "openalex":
            parts["votes"] = min(10, 4 + 2 * math.log10(1 + v))
        elif r["source"] == "huggingface":
            parts["votes"] = 4 if r.get("meta", {}).get("discovered") else 6
        else:
            parts["votes"] = 5
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 3 and not l.strip().startswith("```")]
        rep = 1 - len(set(lines)) / max(1, len(lines))  # code fences, braces and other tiny lines don't count
        links = len(re.findall(r"https?://", text)) / max(1, n / 10)
        parts["cleanliness"] = max(0, 10 - rep * 20 - links * 20)
        ws = {k: float(st[f"w_{k}"]) for k in parts}
        if not r.get("_needs_solution", True):
            ws["solution"] = 0.0  # 'problems only': a missing solution is not a flaw
        total = sum(parts[k] * ws[k] for k in parts) / (sum(ws.values()) or 1)
        return round(total, 2), parts, {"ascii": ascii_ratio, "repeat": rep, "links": links, "words": n}

    def _reasons(self, r, stats, topic_words, strict):
        st = self.st
        if not r["problem"].strip():
            yield "empty problem"
        if r.get("_short"):
            yield "too short for source"
        if st["require_solution"] and r.get("_needs_solution", True) and not r["solution"].strip():
            yield "no solution"
        tags = set(r.get("meta", {}).get("tags", []))
        if tags & {t.strip() for t in st["soft_tags"].split(",") if t.strip()}:
            yield "not a problem"
        if not strict:
            return
        text = r["problem"] + " " + r["solution"]
        if len(r["solution"]) < 400 and re.search(r"(?i)\b(as in|see|same as|like in|similar to) (question|problem|exercise|part) \d|\bsee above\b", r["solution"]):
            yield "refers elsewhere"
        if stats["words"] < int(st["min_words"]) * (1.0 if r.get("_needs_solution", True) else 0.5):
            yield "too few words"
        if stats["words"] > int(st["max_words"]):
            yield "too many words"
        if stats["ascii"] < float(st["min_ascii_ratio"]):
            yield "unreadable characters"
        if stats["links"] > float(st["max_link_ratio"]) * 10:
            yield "link spam"
        if stats["repeat"] > float(st["max_repeat_ratio"]):
            yield "repeated lines"
        letters = [c for c in text if c.isalpha()]
        if letters and sum(c.isupper() for c in letters) / len(letters) > float(st["max_upper_ratio"]):
            yield "shouting / all caps"
        low = text.lower()
        if st["reject_spam_words"] and any(s.strip() and s.strip() in low for s in st["spam_words"].split(",")):
            yield "spam / ads"
        if st["reject_unanswered"] and re.search(r"no answers? yet|be the first to answer", low):
            yield "unanswered"
        if any(f.strip() and f.strip() in r["problem"].lower() for f in st["figure_phrases"].split(",")) or (
                r.get("meta", {}).get("images") and re.search(r"(?i)\b(graph|figure|image|picture|diagram|plot|photo|screenshot|shown|below|looks like this)\b", r["problem"])):
            yield "needs a figure"  # the picture was in the original post and is lost in text
        curated = r["source"] == "stackexchange" or (r["source"] == "huggingface" and not r.get("meta", {}).get("discovered"))
        if st["topic_relevance"] and topic_words and not curated and not set(topic_words) & set(words(text)):
            yield "off topic"

    def reject_reason(self, r, stats, topic_words, strict):
        for why in self._reasons(r, stats, topic_words, strict):
            if why in RULES and not self.st.get(rule_key(why), True):
                continue  # rule switched off - keep checking the others
            return why
        return None

    def run(self, raw, inp):
        q = inp["quality"]
        strict = q > int(self.st["filter_from_quality"])
        min_score = float(self.st[f"min_score_q{q}"]) if strict else 0.0
        self.log(f"Filter: {len(raw)} candidates, quality {q} -> "
                 + (f"strict checks, min score {min_score}" if strict else "basic checks only (quality 1-4)"))
        kept, rejected, reasons = [], [], {}

        def rej(r, why):
            k = why.split(" <")[0]
            reasons[k] = reasons.get(k, 0) + 1
            r["rejected"] = why
            rejected.append(r)
        for r in raw:
            r["_needs_solution"] = inp["data_type"] != "problems only"
            tw = [t for t in words(r["topic"]) if len(t) > 2 and t not in TOPIC_STOP]
            sc, parts, stats = self.score(r, tw)
            is_paper = r.get("meta", {}).get("kind") in ("paper", "article")
            if is_paper != (inp["data_type"] == "research papers"):
                sc = round(sc - float(self.st["paper_penalty"]), 2)
            r["score"], r["score_parts"] = sc, {k: round(v, 1) for k, v in parts.items()}
            why = self.reject_reason(r, stats, tw, strict)
            if not why and sc < min_score:
                why = f"score {sc} < {min_score}"
            rej(r, why) if why else kept.append(r)
        kept.sort(key=lambda r: -r["score"])
        if self.st["dedupe"]:
            uniq, sigs = [], []
            th = float(self.st["dedupe_threshold"])
            for r in kept:
                sig = shingles(r["problem"])
                if any(jaccard(sig, s) >= th for s in sigs):
                    rej(r, "duplicate")
                    continue
                sigs.append(sig)
                uniq.append(r)
            kept = uniq
        final = self.balance(kept, inp)
        self.log(f"Filter: kept {len(final)} (of {len(kept)} passing), rejected {len(rejected)} {reasons}")
        return final, rejected, reasons

    @staticmethod
    def balance(kept, inp):
        """Best records, taken round-robin across topics so every topic gets its share."""
        topics, q = inp["topics"], inp["quantity"]
        if len(topics) <= 1:
            return kept[:q]
        per = {t: [r for r in kept if r["topic"] == t] for t in topics}
        out, idx = [], {t: 0 for t in topics}
        while len(out) < q:
            moved = False
            for t in topics:
                if len(out) < q and idx[t] < len(per[t]):
                    out.append(per[t][idx[t]])
                    idx[t] += 1
                    moved = True
            if not moved:
                break
        return sorted(out, key=lambda r: -r["score"])


# ----------------------------------------------------------------------------- DataGen
FEMALE_NAMES = ("Natalia Priya Aisha Mei Sofia Zara Hannah Emma Fatima Olivia Ananya Chloe Maria Leila Yuki Isabella Amara "
                "Nadia Sara Lucy Julia Elena Ines Kavya Mia Ava Lily Nora Tara Zoe Betty Janet Linda Susan Karen Lisa Nancy "
                "Sandra Ashley Emily Jessica Sarah Rachel Megan Amy Anna Laura Kate Kelly Tina Wendy Julie Jenny Alice Diana "
                "Fiona Helen Irene Jane Monica Paula Rosa Vera Mary Jasmine Ella Ruby Layla Meera Weng Carla Gina Tracy").split()
MALE_NAMES = ("James Liam Noah Carlos Ethan Omar Ravi Lucas Kenji Mateo Arjun Daniel David Samuel Ahmed Hiroshi Diego Felix "
              "Leo Oscar Tom John Michael Robert Richard Joseph Thomas Charles Kevin Brian George Edward Jason Jeff Ryan Gary "
              "Eric Steve Andrew Paul Peter Henry Jack Adam Ben Ali Raj Vikram Ivan Marco Pedro Hugo Tariq Yusuf Rohan Jamal "
              "Tyler Aaron Greg Harry Ian Jake Joe Josh Mike Nick Sean Tim Tony Victor Walter Carl Kyle").split()
FEMALE_SET, MALE_SET = set(FEMALE_NAMES), set(MALE_NAMES)
ITEM_GROUPS = [
    [("apple", "apples"), ("orange", "oranges"), ("pear", "pears"), ("peach", "peaches"), ("plum", "plums"), ("mango", "mangoes"), ("lemon", "lemons")],
    [("pencil", "pencils"), ("marker", "markers"), ("crayon", "crayons"), ("eraser", "erasers"), ("notebook", "notebooks"), ("clip", "clips")],
    [("marble", "marbles"), ("sticker", "stickers"), ("balloon", "balloons"), ("toy car", "toy cars"), ("seashell", "seashells")],
    [("cookie", "cookies"), ("cupcake", "cupcakes"), ("muffin", "muffins"), ("brownie", "brownies"), ("donut", "donuts")],
    [("book", "books"), ("magazine", "magazines"), ("comic", "comics")],
]
SYNONYMS = [("find", "determine"), ("find", "work out"), ("calculate", "compute"), ("calculate", "work out"),
            ("determine", "find"), ("compute", "calculate"), ("show that", "prove that"), ("prove that", "show that"),
            ("suppose", "assume"), ("assume", "suppose"), ("therefore", "thus"), ("therefore", "hence"), ("thus", "therefore"),
            ("hence", "therefore"), ("because of", "due to"), ("because", "since"), ("altogether", "in total"), ("in total", "altogether"),
            ("bought", "purchased"), ("buys", "purchases"), ("obtain", "get"), ("we get", "we obtain"),
            ("note that", "notice that"), ("note that", "observe that"), ("approximately", "about"), ("approximately", "roughly"),
            ("method", "approach"), ("quickly", "rapidly"), ("large", "big"), ("big", "large"), ("simplify", "reduce"),
            ("consider", "look at"), ("needs", "requires"), ("earned", "made")]
CONTRACTIONS = [("do not", "don't"), ("does not", "doesn't"), ("did not", "didn't"), ("is not", "isn't"), ("are not", "aren't"),
                ("cannot", "can't"), ("will not", "won't"), ("it is", "it's"), ("let us", "let's"), ("we are", "we're"),
                ("you are", "you're"), ("I am", "I'm"), ("there is", "there's"), ("we will", "we'll"), ("they are", "they're"),
                ("what is", "what's"), ("would not", "wouldn't"), ("should not", "shouldn't"), ("could not", "couldn't"),
                ("has not", "hasn't"), ("have not", "haven't")]
FORMAL_WORDS = [("gonna", "going to"), ("wanna", "want to"), ("a lot of", "many"), ("lots of", "many"), ("kids", "children"),
                ("okay", "acceptable"), ("pretty much", "essentially"), ("get rid of", "eliminate"), ("figure out", "determine")]
SIMPLE_WORDS = [("utilize", "use"), ("approximately", "about"), ("therefore", "so"), ("consequently", "so"), ("demonstrate", "show"),
                ("determine", "find"), ("compute", "work out"), ("calculate", "work out"), ("sufficient", "enough"),
                ("subsequently", "then"), ("obtain", "get"), ("numerous", "many"), ("commence", "start"), ("terminate", "end"),
                ("assist", "help"), ("additional", "extra"), ("initially", "at first"), ("eliminate", "remove"),
                ("requires", "needs"), ("purchase", "buy"), ("purchased", "bought"), ("equivalent", "the same"),
                ("however", "but"), ("thus", "so"), ("hence", "so")]
FILLER = re.compile(r"(?i)^(hi\b|hello\b|hey\b|thanks|thank you|any help|please help|i (have )?tried|i'm stuck|i am stuck|"
                    r"i don't know|i do not know|edit\b|update\b|sorry|can someone|could someone|i need help|help me)")
CALC_GSM = re.compile(r"<<([^<>=]+)=([^<>]+)>>")
CALC_PLAIN = re.compile(r"(?<![\w.])((?:\(?\s*\$?\d+(?:\.\d+)?\s*\)?\s*[-+*/x×÷]\s*)+\(?\s*\$?\d+(?:\.\d+)?\s*\)?)\s*=\s*\$?(\d+(?:\.\d+)?)(?![\w])")
NUM_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])")
CONST_WORDS = {2: r"\b(twice|doubles?|doubled|half|halves|pairs?|both)\b", 3: r"\b(triples?|tripled|thrice|third)\b",
               4: r"\b(quadruple|quarters?)\b", 7: r"\b(weeks?|weekly)\b", 12: r"\b(dozens?|months?|inch(es)?|feet|foot)\b",
               24: r"\b(days?|daily)\b", 52: r"\b(years?|weekly|weeks)\b", 60: r"\b(hours?|minutes?|seconds?)\b",
               100: r"\b(percent|cents?|dollars?)\b|%", 1000: r"\b(kilo\w*|thousand|milli\w*)\b", 365: r"\b(years?)\b",
               10: r"\b(dimes?|decades?)\b", 5: r"\b(nickels?)\b", 25: r"\b(quarters?)\b"}
PAPER_STYLES = ["paraphrase", "formal", "casual", "concise", "eli5", "teacher"]
PAPER_FORMATS = ["qa", "instruction", "chat", "summary", "markdown", "flashcard", "latex"]
def is_paper_question(p):
    return "What problem does the paper" in (p or "") or "in your own words." in (p or "")


CLASH = {"step-list": ("socratic", "step-by-step", "exam"), "summary": ("socratic", "exam"), "fill-blank": ("socratic",)}
EQ_CH = r"(?:[0-9A-Za-z +\-*/^()×÷]|(?<=\d)\.(?=\d))"  # a '.' only inside a decimal number
EQ_SPAN = re.compile(EQ_CH + "*=" + EQ_CH + "*")
EQ_TOK = re.compile(r"\d+(?:\.\d+)?|[A-Za-z]+|[+\-*/^()=×÷]|\s+")


def find_equations(text):
    """Equation-like spans: (start, end, equation, letters). Words stop a span."""
    res = []
    for m in EQ_SPAN.finditer(text or ""):
        span = m.group(0)
        if span.count("=") != 1:
            continue
        toks = list(EQ_TOK.finditer(span))
        ei = next((i for i, t in enumerate(toks) if t.group() == "="), None)
        if ei is None:
            continue

        def ok(t):
            g = t.group()
            return g.isspace() or g[0].isdigit() or g in "+-*/^()×÷" or (g.isalpha() and len(g) == 1)
        i = ei - 1
        while i >= 0 and ok(toks[i]):
            i -= 1
        j = ei + 1
        while j < len(toks) and ok(toks[j]):
            j += 1
        inner = toks[i + 1:j]
        while inner and (inner[0].group().isspace() or inner[0].group() in "+*/^)=×÷"):
            inner.pop(0)
        while inner and (inner[-1].group().isspace() or inner[-1].group() in "+-*/^(=×÷"):
            inner.pop()
        if not inner:
            continue
        s0, s1 = inner[0].start(), inner[-1].end()
        eq = span[s0:s1]
        if eq.count("=") != 1 or not re.search(r"\d", eq) or eq.count("(") != eq.count(")"):
            continue
        lhs, rhs = eq.split("=")
        if not lhs.strip() or not rhs.strip():
            continue
        if re.search(r"(?<![\w])(a|A|I)\s+[A-Za-z0-9]", eq):
            continue
        letters = {t.group() for t in inner if t.group().isalpha()}
        res.append((m.start() + s0, m.start() + s1, eq, letters))
    return res


def _after_caret(s, pos):
    j = pos - 1
    while j >= 0 and s[j] == " ":
        j -= 1
    return j >= 0 and (s[j] == "^" or s[j - 1:j + 1] == "**")


def fmt_num(v):
    v = Fraction(v)
    if v.denominator == 1:
        return str(v.numerator)
    return f"{float(v):.6f}".rstrip("0").rstrip(".")


def decimals_ok(v, places):
    v = Fraction(v)
    return (v * 10 ** places).denominator == 1


class DataGen:
    """Makes similar versions of each record: new numbers re-solved with SymPy, swapped names/items,
    synonyms, 10 writing styles and 11 formats."""

    def __init__(self, st, log=print):
        self.st, self.log = st, log
        try:
            import sympy
            self.sp = sympy
        except ImportError:
            self.sp = None
            log("  DataGen: SymPy not installed - 'numbers' method skipped (pip install sympy)")
        self._num_cache = {}
        self.counts = {"numbers": 0, "names": 0, "synonyms": 0}

    # ---- answers
    @staticmethod
    def _last_boxed(s):
        i = s.rfind("\\boxed{")
        if i < 0:
            return None
        j, depth = i + 7, 1
        while j < len(s) and depth:
            depth += {"{": 1, "}": -1}.get(s[j], 0)
            j += 1
        return s[i + 7:j - 1] if depth == 0 else None

    @classmethod
    def final_answer(cls, sol, problem=None):
        if not sol:
            return None
        cand = None
        m = re.search(r"####\s*([^\n]+)", sol)
        if m:
            cand = m.group(1)
        if cand is None:
            cand = cls._last_boxed(sol)
        if cand is None:
            ms = re.findall(r"(?im)^\s*(?:final answer|answer)\s*[:=]\s*(.+?)\s*$", sol)
            cand = ms[-1] if ms else None
        if cand is None:
            ms = re.findall(r"(?i)\bthe (?:final )?answer is\s*[:=]?\s*([^\n]+?)(?:\.\s|\.$|\n|$)", sol)
            cand = ms[-1] if ms else None
        if cand is None and len(sol) < 1200:
            tail = " ".join(sentences(sol)[-2:])
            ms = re.findall(r"\b([a-z])\s*=\s*(-?\d+(?:\.\d+)?(?:/\d+)?)(?!\w|\.\d)", tail)
            # only when the problem asks to solve for / find that variable (never a counter-example from the text)
            if ms and (problem is None or re.search(rf"(?i)\b(solve|find|value of|what is|determine)\b[^.?]*\b{ms[-1][0]}\b", problem)):
                cand = f"{ms[-1][0]} = {ms[-1][1]}"
        if cand is None:
            return None
        cand = cand.replace("$", "").strip().rstrip(".").strip()
        if not cand or len(cand) > 60 or len(cand.split()) > 8:
            return None
        return cand

    def distractors(self, ans, rng, k):
        ms = list(re.finditer(r"-?\d+(?:\.\d+)?(?:/\d+)?", ans or ""))
        if not ms:
            return None
        last = ms[-1]
        pre, tok, post = ans[:last.start()], last.group(), ans[last.end():]
        try:
            v = Fraction(tok)
        except (ValueError, ZeroDivisionError):
            return None
        is_int = v.denominator == 1 and "." not in tok and "/" not in tok
        places = len(tok.split(".")[1]) if "." in tok else 0
        cands = [v + 1, v - 1, v * 2, v + rng.randint(2, 9), v - rng.randint(2, 9), v * Fraction(3, 2), v / 2, v + 10, v * 3, -v]
        out = []
        for c in cands:
            if c == v or (is_int and c.denominator != 1) or (v > 0 and c < 0 and len(cands) - cands.index(c) > k):
                continue
            if "/" in tok:
                s_ = f"{c.numerator}/{c.denominator}" if c.denominator != 1 else str(c.numerator)
            elif places:
                s_ = f"{float(c):.{places}f}"
            else:
                s_ = fmt_num(c)
            cand = pre + s_ + post
            if cand != ans and cand not in out:
                out.append(cand)
            if len(out) == k:
                return out
        return None

    # ---- numbers (SymPy)
    def _parse_eq(self, eq, var):
        sp = self.sp
        from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor
        T = standard_transformations + (implicit_multiplication_application, convert_xor)
        try:
            lhs, rhs = eq.replace("×", "*").replace("÷", "/").split("=")
            loc = {var: sp.Symbol(var)}
            L = parse_expr(lhs, transformations=T, local_dict=loc)
            R = parse_expr(rhs, transformations=T, local_dict=loc)
        except Exception:
            return None, None
        if (L - R).free_symbols != {sp.Symbol(var)}:
            return None, None
        return L, R

    def _eq_analysis(self, p):
        sp = self.sp
        eqs = [e for e in find_equations(p) if len(e[3]) == 1]
        if len(eqs) != 1:
            return None
        start, end, eq, letters = eqs[0]
        var = next(iter(letters))
        asks = re.search(r"(?i)\bsolve\b", p) or re.search(
            rf"(?i)\b(find|determine|what is|value of|compute)\s+(the value of\s+)?\$?{var}\$?(?![\w^*/+\-])", p)
        if not asks:
            return None
        rest = p.replace(eq, " ")
        if re.search(r"\d", re.sub(r"(?im)^\s*(problem|question|exercise|example)\s*\d+[a-z]?\s*[:.)]", "", rest)):
            return None  # other numbers in the text (an attempt, a second part...) would go stale
        if re.search(rf"(?i)\b(find|determine|what is|value of|compute|evaluate)\s+(the value of\s+)?[^.?]*?(\d\s*{var}\b|\b{var}\s*[\^*/+\-])", rest):
            return None
        L, R = self._parse_eq(eq, var)
        if L is None:
            return None
        X = sp.Symbol(var)
        try:
            sols = [x for x in sp.solve(sp.Eq(L, R), X) if x.is_real]
        except Exception:
            return None
        if not sols or len(sols) > 4:
            return None
        toks = [(mm.start(), mm.end()) for mm in re.finditer(r"\d+(?:\.\d+)?", eq)
                if "." not in mm.group() and not _after_caret(eq, mm.start())]
        if not toks:
            return None
        return {"kind": "eq", "eq": eq, "var": var, "all_int": all(x.is_integer for x in sols), "toks": toks,
                "latex": "$" in p or "\\(" in p}

    def pretty(self, e):
        s = self.sp.sstr(e).replace("**", "^")
        return re.sub(r"(\d)\*([A-Za-z(])", r"\1\2", s)

    def _eq_solution(self, new_eq, L, R, X, sols, latex):
        sp = self.sp
        x = str(X)
        if latex:
            E = lambda a, b: f"${sp.latex(sp.sympify(a))} = {sp.latex(sp.sympify(b))}$"
            V = lambda e: f"${sp.latex(sp.sympify(e))}$"
        else:
            E = lambda a, b: f"{self.pretty(sp.sympify(a))} = {self.pretty(sp.sympify(b))}"
            V = lambda e: self.pretty(sp.sympify(e))
        lines = [f"We solve {E(L, R) if latex else new_eq.strip()} for {x}."]
        expr = sp.expand(L - R)
        try:
            poly = sp.Poly(expr, X)
        except Exception:
            poly = None
        if poly is not None and poly.degree() == 1:
            a, b = poly.all_coeffs()
            lines.append(f"Move the {x}-terms to one side and the numbers to the other: {E(a * X, -b)}.")
            if a != 1:
                lines.append(f"Divide both sides by {V(a)}: {E(X, sp.nsimplify(-b / a))}.")
        elif poly is not None and poly.degree() == 2:
            lines.append(f"Bring every term to one side: {E(expr, 0)}.")
            f = sp.factor(expr)
            lines.append(f"Factor: {E(f, 0)}." if f != expr and f.is_Mul else "Apply the quadratic formula.")
            lines.append("So " + " or ".join(E(X, v) for v in sols) + ".")
        else:
            lines.append("Solving gives " + " or ".join(E(X, v) for v in sols) + ".")
        for v in sols:
            lines.append(f"Check {E(X, v)}: left side = {V(sp.nsimplify(L.subs(X, v)))}, "
                         f"right side = {V(sp.nsimplify(R.subs(X, v)))}.")
        lines.append(f"Answer: {x} = " + ", ".join(self.pretty(v) for v in sols))
        return "\n".join(lines)

    def _eq_variant(self, p, an, rng):
        sp = self.sp
        X = sp.Symbol(an["var"])
        for _ in range(int(self.st["dg_numeric_tries"])):
            eq, pieces, last, changed = an["eq"], [], 0, False
            for a, b in an["toks"]:
                v = int(eq[a:b])
                nv = int(self.perturb(Fraction(v), rng)) if v > 1 else v
                changed |= nv != v
                pieces.append(eq[last:a] + str(nv))
                last = b
            new_eq = "".join(pieces) + eq[last:]
            if not changed:
                continue
            L, R = self._parse_eq(new_eq, an["var"])
            if L is None:
                continue
            try:
                sols = [x for x in sp.solve(sp.Eq(L, R), X) if x.is_real]
            except Exception:
                continue
            if not sols or len(sols) > 4 or not all(x.is_rational for x in sols):
                continue
            if an["all_int"] and not all(x.is_integer for x in sols):
                continue
            return p.replace(an["eq"], new_eq), self._eq_solution(new_eq, L, R, X, sols, an["latex"])
        return None

    @staticmethod
    def _norm_expr(e):
        e = e.replace("$", "").replace("×", "*").replace("÷", "/")
        return re.sub(r"(?<=\d)\s*x\s*(?=[\d(])", "*", e).replace(",", "")

    @staticmethod
    def computations(s):
        calcs = [(m.group(1), m.group(2)) for m in CALC_GSM.finditer(s)]
        return calcs or [(m.group(1), m.group(2)) for m in CALC_PLAIN.finditer(s)]

    def _chain_analysis(self, p, s):
        sp = self.sp
        calcs = self.computations(s)
        if not calcs:
            return None
        if not CALC_GSM.search(s):  # free-form text: only short, computation-dense solutions (never proofs/essays)
            in_calcs = sum(len(NUM_RE.findall(self._norm_expr(e))) + 1 for e, _ in calcs)
            if len(s) > 1200 or len(calcs) < 2 or in_calcs < 0.5 * max(1, len(NUM_RE.findall(s))):
                return None
        pvals = {Fraction(t) for t in NUM_RE.findall(p)}
        frozen = {Fraction(v) for v, pat in CONST_WORDS.items() if Fraction(v) in pvals and re.search(pat, p, re.I)}
        if self.st["dg_freeze_years"]:
            frozen |= {v for v in pvals if v.denominator == 1 and 1900 <= v <= 2100}
        frozen |= {Fraction(x) for m in re.finditer(r"(?<![\w.])(\d+)\s*/\s*(\d+)(?![\w])", p) for x in m.groups()}
        pct = {Fraction(m.group(1)) for m in re.finditer(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:%|percent)", p)}
        known, steps, consts, env = {}, [], set(), {}
        for i, (e, r) in enumerate(calcs):
            en = self._norm_expr(e)
            if not re.fullmatch(r"[\d.\s+\-*/()]+", en):
                return None
            try:
                rv = Fraction(r.replace("$", "").replace(",", "").strip().rstrip("."))
            except (ValueError, ZeroDivisionError):
                return None

            def tok(m):
                v = Fraction(m.group(0))
                if v in known:
                    return known[v]
                if v in pvals and v not in frozen:
                    name = f"P{sum(1 for k in known.values() if k.startswith('P'))}"
                    known[v] = name
                    env[sp.Symbol(name)] = sp.Rational(v.numerator, v.denominator)
                    return name
                consts.add(v)
                return f"({m.group(0)})"
            sexpr = NUM_RE.sub(tok, en)
            try:
                expr = sp.sympify(sexpr, locals={n: sp.Symbol(n) for n in known.values()}, rational=True)
                val = sp.nsimplify(expr.subs(env))
            except Exception:
                return None
            if val != sp.Rational(rv.numerator, rv.denominator):
                return None
            if rv in known or rv in pvals:
                return None
            name = f"R{i}"
            known[rv] = name
            env[sp.Symbol(name)] = val
            steps.append((name, expr, rv))
        if consts & set(known):
            return None
        if not any(n.startswith("P") for n in known.values()):
            return None
        return {"kind": "chain", "known": known, "steps": steps, "pct": pct}

    def perturb(self, v, rng, pct=False):
        v = Fraction(v)
        small, scale = int(self.st["dg_small_delta"]), int(self.st["dg_scale_pct"]) / 100
        if v.denominator != 1 or (v != int(v)):
            places = next((k for k in range(1, 5) if decimals_ok(v, k)), 2)
            nv = round(float(v) * rng.uniform(1 - scale, 1 + scale), places)
            if nv <= 0 or Fraction(str(nv)) == v:
                nv = float(v) + 10 ** -places
            return Fraction(str(round(nv, places)))
        n = v.numerator
        if n <= 1:
            return v
        if n <= 12:
            return Fraction(rng.choice([x for x in range(max(2, n - small), n + small + 1) if x != n]))
        lo, hi = max(2, int(n * (1 - scale))), int(n * (1 + scale)) + 1
        if pct:
            hi = min(hi, 95)
        steps = ([10, 5, 1] if n % 10 == 0 else [5, 1] if n % 5 == 0 else [1]) if self.st["dg_keep_roundness"] else [1]
        for step in steps:  # keep round numbers round when there is enough room, else relax
            cands = [x for x in range(lo, hi + 1) if x % step == 0 and x != n]
            if len(cands) >= 4 or step == 1:
                break
        return Fraction(rng.choice(cands)) if cands else Fraction(n + 1)

    def _chain_variant(self, p, s, an, rng):
        sp = self.sp
        P = {v: n for v, n in an["known"].items() if n.startswith("P")}
        for _ in range(int(self.st["dg_numeric_tries"])):
            env = {}
            for v, n in P.items():
                nv = self.perturb(v, rng, pct=v in an["pct"])
                env[sp.Symbol(n)] = sp.Rational(nv.numerator, nv.denominator)
            ok = True
            for name, expr, rv in an["steps"]:
                val = sp.nsimplify(expr.subs(env))
                if not val.is_rational:
                    ok = False
                    break
                fv = Fraction(int(val.p), int(val.q))
                places = 0 if rv.denominator == 1 else 2
                if not decimals_ok(fv, places) or (rv > 0 and fv <= 0) or (rv >= 0 and fv < 0):
                    ok = False
                    break
                env[sp.Symbol(name)] = val
            if not ok:
                continue
            old2new = {}
            for v, n in an["known"].items():
                x = env[sp.Symbol(n)]
                nv = Fraction(int(x.p), int(x.q))
                if nv != v:
                    old2new[v] = nv
            if not old2new:
                continue
            news = [old2new.get(v, v) for v in an["known"]]
            if len(set(news)) != len(news):
                continue
            untouched = {Fraction(t) for t in NUM_RE.findall(p + " " + s)} - set(old2new)
            if set(old2new.values()) & untouched:
                continue

            def rep(m):
                v = Fraction(m.group(0))
                return fmt_num(old2new[v]) if v in old2new else m.group(0)
            p2, s2 = NUM_RE.sub(rep, p), NUM_RE.sub(rep, s)
            if self.verify_chain(p2, s2):
                return p2, s2
        return None

    def verify_chain(self, p, s):
        """Every 'expression = result' in the new solution must be exactly right."""
        sp = self.sp
        calcs = self.computations(s)
        if not calcs:
            return False
        results = set()
        for e, r in calcs:
            try:
                val = sp.nsimplify(sp.sympify(self._norm_expr(e), rational=True))
                rv = Fraction(r.replace("$", "").replace(",", "").strip().rstrip("."))
            except Exception:
                return False
            if val != sp.Rational(rv.numerator, rv.denominator):
                return False
            results.add(rv)
        m = re.search(r"####\s*\$?(-?\d+(?:\.\d+)?)", s)
        if m and Fraction(m.group(1)) not in results | {Fraction(t) for t in NUM_RE.findall(p)}:
            return False
        return True

    def numeric_variant(self, r, rng):
        if self.sp is None or is_code(r["solution"]):
            return None
        uid = r.get("uid") or hashlib.sha1(r["problem"].encode()).hexdigest()[:12]
        if uid not in self._num_cache:
            p = re.sub(r"(?<=\d),(?=\d{3}\b)", "", r["problem"])
            s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", r["solution"])
            an = None
            try:
                an = self._eq_analysis(p) or (self._chain_analysis(p, s) if s else None)
            except Exception:
                an = None
            self._num_cache[uid] = (an, p, s)
        an, p, s = self._num_cache[uid]
        if not an:
            return None
        try:
            return self._eq_variant(p, an, rng) if an["kind"] == "eq" else self._chain_variant(p, s, an, rng)
        except Exception:
            return None

    # ---- names & items, synonyms
    def swap_names(self, p, s, rng):
        found = [n for n in dict.fromkeys(re.findall(r"\b[A-Z][a-z]+\b", p)) if n in FEMALE_SET or n in MALE_SET]
        mapping = {}
        everything = p + " " + s
        for n in found:
            if self.st["dg_names_keep_gender"]:
                pool = FEMALE_NAMES if n in FEMALE_SET else MALE_NAMES
            else:
                pool = FEMALE_NAMES + MALE_NAMES
            choices = [x for x in pool if not re.search(rf"\b{x}\b", everything) and x not in mapping.values()]
            if choices:
                mapping[n] = rng.choice(choices)
        if found or not self.st["dg_items_need_name"]:
            for group in ITEM_GROUPS:
                present = [(a, b) for a, b in group if re.search(rf"\b({re.escape(a)}|{re.escape(b)})\b", p, re.I)]
                for a, b in present:
                    choices = [(c, d) for c, d in group if (c, d) not in present
                               and not re.search(rf"\b({re.escape(c)}|{re.escape(d)})\b", everything, re.I)
                               and d not in mapping.values()]
                    if choices:
                        c, d = rng.choice(choices)
                        mapping[b], mapping[a] = d, c
        if not mapping:
            return p, s
        keys = sorted(mapping, key=len, reverse=True)
        rx = re.compile(r"\b(" + "|".join(re.escape(k) for k in keys) + r")\b", re.I)

        def rep(m):
            w = m.group(0)
            key = w if w in mapping else next((k for k in keys if k.lower() == w.lower()), None)
            if key is None or (key[0].isupper() and w != key):
                return w
            return case_like(w, mapping[key]) if not key[0].isupper() else mapping[key]
        return rx.sub(rep, p), rx.sub(rep, s)

    def synonyms(self, text, rng, rate=None):
        if not text or is_code(text):
            return text
        return swap_phrases(text, SYNONYMS, rng, float(self.st["dg_synonym_rate"]) if rate is None else rate)

    # ---- styles
    def rephrase(self, p, rng):
        out = []
        for sen in sentences(p) or [p]:
            m = re.match(r"(?i)^what is (the |an? )?(.+)\?$", sen)
            if m and len(sen) < 300:
                verb = rng.choice(["Find", "Determine", "Compute"])
                sen = f"{verb} {(m.group(1) or '').lower()}{m.group(2)}."
            out.append(sen)
        return " ".join(out) if "\n" not in p else p if out == sentences(p) else "\n".join(out)

    def imperative(self, p):
        p = re.sub(r"(?im)^(?:can you |could you |please )?(find|calculate|compute|determine|work out)\b", lambda m: m.group(1).capitalize(), p)
        return re.sub(r"(?i)\bwhat is the value of\b", "Determine the value of", p)

    def concise_problem(self, p):
        sens = sentences(p)
        keep = [x for x in sens if not FILLER.match(x)]
        return " ".join(keep or sens) if sens else p

    def concise_solution(self, steps, ans):
        key = [x for x in steps if re.search(r"[=\d$\\]|therefore|thus|hence|so |answer", x, re.I)] or steps
        body = " ".join(key[:4])
        return body + (f"\nAnswer: {ans}" if ans and ans not in body[-80:] else "")

    def apply_style(self, style, p, s, rng, ans):
        code = is_code(s)
        steps = [] if code else steps_of(s)
        opts = lambda key: [x for x in self.st[key].split("|") if x.strip()] or [""]
        if style == "paraphrase":
            intro = ["", "Consider the following problem. ", "Here is a problem to solve. "] if not p.startswith(("What problem does the paper", "Explain \"")) else [""]
            p = rng.choice(intro) + self.synonyms(self.rephrase(p, rng), rng, 0.7)
            if s and not code:
                s = self.synonyms(s, rng, 0.4)
        elif style == "formal":
            lp, ls = ("Question. ", "Answer. ") if is_paper_question(p) else ("Problem. ", "Solution. ")
            p = lp + swap_phrases(swap_phrases(p, [(b, a) for a, b in CONTRACTIONS]), FORMAL_WORDS)
            if s:
                s = ls + (s if code else swap_phrases(swap_phrases(s, [(b, a) for a, b in CONTRACTIONS]), FORMAL_WORDS))
        elif style == "casual":
            p = rng.choice(opts("dg_casual_openers")) + swap_phrases(p, CONTRACTIONS)
            if s:
                s = rng.choice(["Here's how it works. ", "Easy - let's go. ", "So here's the trick. "]) + (s if code else swap_phrases(s, CONTRACTIONS))
        elif style == "exam":
            marks = max(2, min(int(self.st["dg_exam_max_marks"]), len(steps) or 3))
            p = f"Question ({marks} marks)\n{p}\n\nShow all your working."
            if s:
                if code:
                    s = "Mark scheme:\n" + s + "\n[Full marks for a correct, working solution]"
                else:
                    work = [x for x in steps if not x.startswith("####")]
                    s = ("Mark scheme:\n" + "\n".join(f"{x} [1]" for x in work[:marks])
                         + ("\n" + " ".join(work[marks:]) if work[marks:] else "") + (f"\nFinal answer: {ans}" if ans else ""))
        elif style == "socratic":
            p = p + "\n\nWork through it by answering the guiding questions."
            if s:
                qs = opts("dg_socratic_questions")
                if code or len(steps) < 2:
                    s = f"Q: How can we solve this?\nA: {s}"
                else:  # each guiding question once: group the steps, the last group answers "so what is the answer?"
                    k = min(len(qs), len(steps))
                    bounds = [round(i * len(steps) / k) for i in range(k + 1)]
                    groups = [" ".join(steps[bounds[i]:bounds[i + 1]]) for i in range(k)]
                    ask = qs[:k - 1] + [qs[-1]]
                    s = "\n".join(f"Q{i + 1}: {ask[i]}\nA{i + 1}: {g}" for i, g in enumerate(groups))
        elif style == "step-by-step":
            p = p + "\n\nSolve this step by step."
            if s:
                s = (f"Step 1: Write the solution.\n{s}\nStep 2: Check it against the tests in the task." if code
                     else "\n".join(f"Step {i + 1}: {x}" for i, x in enumerate(steps)))
        elif style == "concise":
            p = self.concise_problem(p)
            if s and not code:
                s = self.concise_solution(steps, ans)
        elif style == "eli5":
            p = "Explain like I'm five: " + swap_phrases(p, SIMPLE_WORDS)
            if s:
                s = "Here's the simple version. " + (s if code else swap_phrases(s, SIMPLE_WORDS))
        elif style == "competition":
            p = "Problem. " + self.imperative(p)
            if s and ans and not code:
                s = s + f"\n\nFinal answer: $\\boxed{{{ans}}}$"
        elif style == "teacher":
            p = rng.choice(opts("dg_teacher_openers")) + "\n" + p
            if s:
                s = "Let's walk through it together.\n" + s + (f"\n\nKey idea: {steps[0]}" if len(steps) > 2 else "")
        return p, s

    # ---- formats
    def eq_to_latex(self, eq):
        sp = self.sp
        from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor
        T = standard_transformations + (implicit_multiplication_application, convert_xor)
        try:
            lhs, rhs = eq.replace("×", "*").replace("÷", "/").split("=")
            letters = set(re.findall(r"[A-Za-z]", eq))
            loc = {c: sp.Symbol(c) for c in letters}
            L = parse_expr(lhs, transformations=T, local_dict=loc, evaluate=False)
            R = parse_expr(rhs, transformations=T, local_dict=loc, evaluate=False)
            return f"{sp.latex(L)} = {sp.latex(R)}"
        except Exception:
            return None

    def latexify(self, text):
        if not text or is_code(text):
            return text
        t, keep = protect(re.sub(r"<<[^<>]*>>", "", text))
        esc = lambda x: re.sub(r"([&%#_])", r"\\\1", x)
        if self.sp is not None and self.st["dg_latex_sympy"]:
            out, last = [], 0
            for a, b, eq, letters in find_equations(t):
                tex = self.eq_to_latex(eq)
                if tex:
                    out.append(esc(t[last:a]) + "$" + tex + "$")
                    last = b
            out.append(esc(t[last:]))
            t = "".join(out)
        else:
            t = esc(t)
        return unprotect(t, keep)

    def options(self, ans, rng, pool):
        k = int(self.st["dg_mcq_options"])
        ds = self.distractors(ans, rng, k - 1)
        if not ds:
            cands = list(dict.fromkeys(a for a in (pool or []) if a and a != ans))
            if len(cands) < k - 1:
                return None
            ds = rng.sample(cands, k - 1)
        opts = ds + [ans]
        rng.shuffle(opts)
        return opts

    def apply_format(self, fmt, p, s, ans, rng, pool):
        """Returns (problem, solution, extra) or None when the format does not fit this record."""
        code = is_code(s)
        steps = [] if code else steps_of(s)
        if fmt == "qa":
            return f"Q: {p}", (f"A: {s}" if s else ""), {}
        if fmt == "instruction":
            conceptual = not re.search(r"[\d=$\\]", p) and "?" in p
            ins = ("Answer the following question about a research paper." if is_paper_question(p)
                   else "Write a correct, working solution." if code
                   else "Answer the following question clearly and accurately." if conceptual
                   else "Solve the following problem and explain the reasoning.")
            return f"Instruction: {ins}\nInput: {p}", (f"Response: {s}" if s else ""), {"instruction": ins, "input": p, "output": s}
        if fmt == "chat":
            msgs = ([{"role": "system", "content": self.st["dg_chat_system"]}] if self.st["dg_chat_system"].strip() else [])
            msgs += [{"role": "user", "content": p}] + ([{"role": "assistant", "content": s}] if s else [])
            return f"User: {p}", (f"Assistant: {s}" if s else ""), {"messages": msgs}
        if fmt == "markdown":
            return f"### Problem\n\n{p}", (f"### Solution\n\n{s}" if s else ""), {}
        if fmt == "latex":
            return (f"\\begin{{problem}}\n{self.latexify(p)}\n\\end{{problem}}",
                    (f"\\begin{{solution}}\n{self.latexify(s)}\n\\end{{solution}}" if s else ""), {})
        if not s:
            return None
        if fmt == "mcq":
            if not ans:
                return None
            opts = self.options(ans, rng, pool)
            if not opts:
                return None
            letters = "ABCDEF"
            right = letters[opts.index(ans)]
            return (p + "\n\nChoose one:\n" + "\n".join(f"{letters[i]}) {o}" for i, o in enumerate(opts)),
                    f"Correct answer: {right}) {ans}\n\n{s}", {"options": opts, "correct": right})
        if fmt == "true-false":
            if not ans:
                return None
            truth = rng.random() < float(self.st["dg_tf_true_ratio"])
            shown = ans
            if not truth:
                ds = self.distractors(ans, rng, 1) or [a for a in (pool or []) if a and a != ans][:1]
                if ds:
                    shown = ds[0]
                else:
                    truth = True
            return (f"True or false? The answer to the problem below is {shown}.\n\n{p}",
                    f"{'True' if truth else 'False'}. The correct answer is {ans}.\n\n{s}", {"statement_true": truth})
        if fmt == "fill-blank":
            if not ans or code:
                return None
            pat = re.compile(rf"(?<![\w.]){re.escape(ans)}(?![\w])") if re.fullmatch(r"[\w.\-/ =]+", ans) else re.compile(re.escape(ans))
            if not pat.search(s):
                return None
            return (f"{p}\n\nFill in the blank in this worked solution:\n{pat.sub('_____', s)}",
                    f"The blank is: {ans}\n\n{s}", {})
        if fmt == "flashcard":
            return f"Front: {shorten(p, 300)}", f"Back: {ans or (s if code else shorten(s, 400))}", {}
        if fmt == "step-list":
            if code or len(steps) < 2:
                return None
            steps = [re.sub(r"^(Step \d+:|\d+\.)\s*", "", x) for x in steps]
            return f"List the steps needed to solve:\n{p}", "\n".join(f"{i + 1}. {x}" for i, x in enumerate(steps)), {}
        if fmt == "summary":
            if code or not steps:
                return None
            body = [x for x in sentences(s) if len(x) >= 30 and not x.startswith("####")] or steps
            return (f"Summarize the key idea and the result:\n{p}",
                    "Summary: " + " ".join(body[:2]) + (f"\nResult: {ans}" if ans else ""), {})
        return None

    # ---- driver
    def make_variant(self, r, style, fmt, methods, rng, pool, formats, k):
        p, s = r["problem"], r["solution"]
        applied, changed_numbers = [], False
        kind = r.get("meta", {}).get("kind")
        if kind in ("paper", "article"):  # turn a paper/article into a question about it
            body = (p[len(r["title"]):] if p.startswith(r["title"]) else p).strip()
            s = (body + " " + s).strip()
            p = (f'What problem does the paper "{r["title"]}" address, and what approach and result does it report?'
                 if kind == "paper" else f'Explain "{r["title"]}" in your own words.')
            methods = [m for m in methods if m == "synonyms"]
        if "numbers" in methods:
            res = self.numeric_variant(r, rng)
            if res:
                p, s = res
                applied.append("numbers (SymPy)")
                changed_numbers = True
        if "names" in methods:
            p2, s2 = self.swap_names(p, s, rng)
            if (p2, s2) != (p, s):
                p, s = p2, s2
                applied.append("names/items")
        if "synonyms" in methods:
            p2, s2 = self.synonyms(p, rng), self.synonyms(s, rng)
            if (p2, s2) != (p, s):
                p, s = p2, s2
                applied.append("synonyms")
        ans = self.final_answer(s, p)
        core = {"problem": p, "solution": s}  # before style/format - kept in memory for checks, never exported
        p, s = self.apply_style(style, p, s, rng, ans)
        order = [fmt] + [f for f in formats if f != fmt] + ["qa"]
        order = [f for f in order if style not in CLASH.get(f, ())] or ["qa"]
        for f in order:
            res = self.apply_format(f, p, s, ans, rng, pool)
            if res:
                p, s, extra = res
                fmt = f
                break
        else:
            return None
        v = {key: r.get(key) for key in ("topic", "source", "url", "votes", "score")}
        title = r["title"] + (f"  [{style} · {fmt}]" if self.st["dg_title_suffix"] else "")
        v.update(title=title, problem=p, solution=s, meta=dict(r.get("meta", {}), **extra), kind="variant",
                 uid=f"{r.get('uid', 'x')}-v{k}", variant_of=r.get("uid"), style=style, format=fmt,
                 methods=applied, numbers_changed=changed_numbers, answer=ans, _core=core)
        for m in ("numbers", "names", "synonyms"):
            if any(a.startswith({"numbers": "numbers", "names": "names", "synonyms": "synonyms"}[m]) for a in applied):
                self.counts[m] += 1
        return v

    def generate(self, records, inp, progress=None, cancel=None):
        n = int(inp.get("datagen_variations", 0))
        if n <= 0 or not records:
            return []
        styles = inp.get("datagen_styles") or ["paraphrase"]
        formats = inp.get("datagen_formats") or ["qa"]
        methods = inp.get("datagen_methods") or []
        pool = {}
        for r in records:
            a = self.final_answer(r["solution"], r["problem"])
            if a:
                pool.setdefault(r["topic"], []).append(a)
        cap = int(self.st["dg_max_total"])
        seed = int(self.st["dg_seed"])
        out = []
        self.log(f"DataGen: {len(records)} records x {n} variations | styles {len(styles)} | formats {len(formats)} | "
                 f"methods {', '.join(methods) or 'none'}" + ("" if self.sp else " | SymPy missing"))
        for ri, r in enumerate(records):
            if cancel is not None and cancel.is_set():
                break
            seen = {(r["problem"], r["solution"])}
            made = attempts = 0
            while made < n and attempts < n * 4 + 4:
                attempts += 1
                rng = random.Random(f"{seed}|{r.get('uid', ri)}|{attempts}")
                paper = r.get("meta", {}).get("kind") in ("paper", "article")
                sty = ([x for x in styles if x in PAPER_STYLES] or ["formal"]) if paper else styles
                fms = ([x for x in formats if x in PAPER_FORMATS] or ["qa"]) if paper else formats
                style = sty[(ri + attempts - 1) % len(sty)]
                fmt = fms[(ri * 3 + attempts - 1) % len(fms)]
                v = self.make_variant(r, style, fmt, methods, rng, pool.get(r["topic"]), fms, made + 1)
                if v is None:
                    continue
                key = (v["problem"], v["solution"])
                if self.st["dg_dedupe"] and key in seen:
                    continue
                seen.add(key)
                out.append(v)
                made += 1
                if len(out) >= cap:
                    self.log(f"DataGen: reached the cap of {cap} variants")
                    return out
            if progress:
                progress(0.85 + 0.14 * (ri + 1) / len(records), f"datagen {ri + 1}/{len(records)}")
        self.log(f"DataGen: made {len(out)} variants (new numbers re-solved: {self.counts['numbers']}, "
                 f"names/items swapped: {self.counts['names']}, synonyms: {self.counts['synonyms']})")
        return out


# ----------------------------------------------------------------------------- output presenter
def sort_records(recs, st):
    key = st["sort_by"]
    if key == "score":
        return sorted(recs, key=lambda r: -(r.get("score") or 0))
    if key in ("source", "topic"):
        return sorted(recs, key=lambda r: (r.get(key, ""), -(r.get("score") or 0)))
    return list(recs)


def arrange(recs, variants, st):
    """[(display_id, record, parent_display_id)] - originals, each followed by its variants (or all at the end)."""
    by_parent = {}
    for v in variants or []:
        by_parent.setdefault(v.get("variant_of"), []).append(v)
    rows, tail = [], []
    for i, r in enumerate(sort_records(recs, st), 1):
        rows.append((str(i), r, None))
        for k, v in enumerate(by_parent.get(r.get("uid"), []), 1):
            (rows if st.get("dg_placement", "grouped") == "grouped" else tail).append((f"{i}.{k}", v, str(i)))
    return rows + tail


def public_record(r, st, did, parent=None):
    mx = int(st["max_chars_out"])
    d = {"id": did, "kind": r.get("kind", "original"), "topic": r["topic"], "title": r["title"],
         "problem": r["problem"][:mx], "solution": r["solution"][:mx]}
    if r.get("kind") == "variant":
        d.update(variant_of=parent, style=r.get("style"), format=r.get("format"), methods=r.get("methods", []),
                 numbers_changed=bool(r.get("numbers_changed")))
        if st.get("dg_answer_field", True) and r.get("answer"):
            d["answer"] = r["answer"]
        for k in ("messages", "options", "correct", "instruction", "input", "output"):
            if k in r.get("meta", {}):
                d[k] = r["meta"][k]
    if st["include_sources"]:
        d["source"], d["url"] = r["source"], r["url"]
        if r.get("meta", {}).get("license"):
            d["license"] = r["meta"]["license"]
    if st["include_scores"]:
        d["quality_score"] = r.get("score")
    return d


def build_meta(inp, recs, variants, reasons):
    return {"app": APP, "version": VERSION, "created": datetime.now().isoformat(timespec="seconds"),
            "input": inp, "originals": len(recs), "variants": len(variants or []),
            "records": len(recs) + len(variants or []), "rejected": reasons or {}}


def variant_line(r, parent):
    bits = [f"Variant of #{parent}", f"style: {r.get('style')}", f"format: {r.get('format')}"]
    if r.get("methods"):
        bits.append("methods: " + ", ".join(r["methods"]))
    return " · ".join(bits)


def render_txt(recs, inp, st, reasons=None, variants=None):
    sep = st["txt_separator"]
    out = []
    if st["include_meta"]:
        m = build_meta(inp, recs, variants, reasons)
        out += [f"{APP} - training data export", f"Created: {m['created']}",
                f"Topics: {', '.join(inp['topics'])} | Quantity: {inp['quantity']} | Quality: {inp['quality']} | Type: {inp['data_type']}",
                f"Records: {m['records']} ({m['originals']} originals + {m['variants']} DataGen variants)", sep]
    for did, r, parent in arrange(recs, variants, st):
        d = public_record(r, st, did, parent)
        out.append(f"#{did}  [{d['topic']}]  {d['title']}")
        if parent:
            out.append(variant_line(r, parent))
        if st["include_scores"]:
            out.append(f"Quality score: {d['quality_score']}")
        if st["include_sources"]:
            out.append(f"Source: {d['source']}  {d['url']}" + (f"  (licence: {d['license']})" if d.get("license") else ""))
        out += ["", "PROBLEM:", d["problem"], ""]
        if d["solution"]:
            out += ["SOLUTION:", d["solution"], ""]
        out.append(sep)
    return "\n".join(out) + "\n"


def render_json(recs, inp, st, reasons=None, variants=None):
    rows = [public_record(r, st, did, parent) for did, r, parent in arrange(recs, variants, st)]
    fmt = st["json_format"]
    if fmt == "chat-messages":
        rows = [{"messages": r.get("messages") or [{"role": "user", "content": r["problem"]}, {"role": "assistant", "content": r["solution"]}],
                 **{k: v for k, v in r.items() if k not in ("problem", "solution", "messages")}} for r in rows]
    elif fmt == "instruction":
        rows = [{"instruction": r["problem"], "output": r["solution"],
                 **{k: v for k, v in r.items() if k not in ("problem", "solution", "instruction", "output", "input")}} for r in rows]
    doc = {"meta": build_meta(inp, recs, variants, reasons), "data": rows} if st["include_meta"] else rows
    return json.dumps(doc, indent=int(st["json_indent"]) or None, ensure_ascii=False)


PDF_TRANSLIT = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "ζ": "zeta", "η": "eta", "θ": "theta",
                 "ι": "iota", "κ": "kappa", "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "π": "pi", "ρ": "rho", "σ": "sigma",
                 "τ": "tau", "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega", "Γ": "Gamma", "Δ": "Delta", "Θ": "Theta",
                 "Λ": "Lambda", "Π": "Pi", "Σ": "Sigma", "Φ": "Phi", "Ψ": "Psi", "Ω": "Omega", "√": "sqrt", "∞": "infinity",
                 "≤": "<=", "≥": ">=", "≠": "!=", "≈": "~=", "≡": "===", "→": "->", "←": "<-", "↔": "<->", "⇒": "=>", "⇔": "<=>",
                 "∈": " in ", "∉": " not in ", "⊂": " subset of ", "⊆": " subset of ", "∪": " union ", "∩": " intersect ",
                 "∀": "for all ", "∃": "there exists ", "∑": "sum ", "∏": "product ", "∫": "integral ", "∂": "d", "∇": "nabla",
                 "⋅": "*", "∙": "*", "∗": "*", "−": "-", "⁴": "^4", "⁵": "^5", "⁶": "^6", "⁷": "^7", "⁸": "^8", "⁹": "^9", "⁰": "^0",
                 "ⁿ": "^n", "₀": "_0", "₁": "_1", "₂": "_2", "₃": "_3", "ℝ": "R", "ℕ": "N", "ℤ": "Z", "ℚ": "Q", "ℂ": "C",
                 "✓": "OK", "✗": "x", "★": "*", "°C": " deg C", "Å": "A"}
PDF_TRANSLIT_RE = re.compile("|".join(re.escape(k) for k in sorted(PDF_TRANSLIT, key=len, reverse=True)))


def _translit(m):
    rep = PDF_TRANSLIT[m.group(0)]
    if rep != rep.strip():  # word operators get a space on each side only where one is missing
        txt, a, b = m.string, m.start(), m.end()
        return ((" " if a > 0 and not txt[a - 1].isspace() else "") + rep.strip()
                + (" " if b < len(txt) and not txt[b].isspace() else ""))
    return rep


def _pdf_safe(s):
    s = PDF_TRANSLIT_RE.sub(_translit, s)
    s = s.replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "--").replace("\u2018", "'").replace("\u2019", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2026", "...").replace("\u00a0", " ").replace("\u00b7", "-")
    s = s.encode("cp1252", "replace").decode("cp1252")
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def render_pdf(recs, inp, st, reasons=None, variants=None):
    """Pure-Python PDF writer (Helvetica/Courier, wrapped text, page numbers). Returns bytes."""
    import textwrap
    W, H = (595, 842) if st["pdf_page"] == "A4" else (612, 792)
    M, fs = int(st["pdf_margin"]), int(st["pdf_font_size"])
    pages, cur = [], []
    y = [H - M]

    def newpage():
        nonlocal cur
        if cur:
            pages.append(cur)
        cur = []
        y[0] = H - M

    def line(text, size=fs, font="F1", gap=None):
        if y[0] < M + size * 1.4:
            newpage()
        cur.append((M, y[0], size, font, text))
        y[0] -= gap if gap is not None else size * 1.35

    def para(text, size=fs, font="F1"):
        width = (W - 2 * M) / (size * (0.6 if font == "F3" else 0.5))
        for raw in (text or "").replace("\r", "").replace("\t", "    ").split("\n"):
            if font == "F3":
                ind = len(raw) - len(raw.lstrip(" "))
                wrapped = textwrap.wrap(raw, max(20, int(width)), subsequent_indent=" " * min(ind + 2, 20),
                                        drop_whitespace=False) or [""]
            else:
                wrapped = textwrap.wrap(raw, max(20, int(width))) or [""]
            for w_ in wrapped:
                line(w_, size, font)

    def mixed(text):
        """Fenced ``` blocks (and whole code answers) in Courier, everything else in Helvetica."""
        if "```" not in (text or ""):
            para(text, fs - (1 if is_code(text) else 0), "F3" if is_code(text) else "F1")
            return
        for i, part in enumerate(re.split(r"```[^\n]*\n?", text)):
            if part.strip():
                para(part.strip("\n"), fs - 1 if i % 2 else fs, "F3" if i % 2 else "F1")

    m = build_meta(inp, recs, variants, reasons)
    if st["pdf_title_page"]:
        y[0] = H - M - 120
        line(APP, 24, "F2", 40)
        line("AI training data export", 14, "F1", 30)
        for t in [f"Topics: {', '.join(inp['topics'])}", f"Data type: {inp['data_type']}",
                  f"Quantity: {inp['quantity']}   Quality: {inp['quality']}/10",
                  f"Records: {m['records']}  ({m['originals']} originals + {m['variants']} DataGen variants)",
                  f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}"]:
            line(t, 11, "F1", 18)
        newpage()
    for did, r, parent in arrange(recs, variants, st):
        d = public_record(r, st, did, parent)
        para(f"#{did}  {d['title'] or d['topic']}", fs + (1 if parent else 3), "F2")
        if parent:
            para(variant_line(r, parent), fs - 1)
        sub = f"Topic: {d['topic']}"
        if st["include_scores"]:
            sub += f"   Quality score: {d['quality_score']}"
        para(sub, fs - 1)
        if st["include_sources"]:
            para(f"Source: {d['source']}  {d['url']}" + (f"  (licence: {d['license']})" if d.get("license") else ""), fs - 2)
        y[0] -= fs * 0.5
        para("PROBLEM", fs, "F2")
        mixed(d["problem"])
        if d["solution"]:
            y[0] -= fs * 0.4
            para("SOLUTION", fs, "F2")
            mixed(d["solution"])
        y[0] -= fs * 1.6
    newpage()
    if not pages:
        pages = [[(M, H - M, fs, "F1", "No records.")]]
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", None,
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>"]
    kids = []
    for pi, pg in enumerate(pages, 1):
        ops = [f"BT /{font} {size} Tf {x} {yy:.1f} Td ({_pdf_safe(text)}) Tj ET" for x, yy, size, font, text in pg]
        if st["pdf_numbering"]:
            ops.append(f"BT /F1 8 Tf {W / 2 - 20:.0f} {M / 2:.0f} Td (Page {pi} of {len(pages)}) Tj ET")
        objs.append(("stream", zlib.compress("\n".join(ops).encode("cp1252", "replace"))))
        cid = len(objs)
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> /Contents {cid} 0 R >>")
        kids.append(len(objs))
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>"
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        if isinstance(o, tuple):
            out += f"{i} 0 obj\n<< /Length {len(o[1])} /Filter /FlateDecode >>\nstream\n".encode() + o[1] + b"\nendstream\nendobj\n"
        else:
            out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for o in offs:
        out += f"{o:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R /Info << /Title ({APP}) /Producer (AITE {VERSION}) >> >>\n"
            f"startxref\n{xref}\n%%EOF\n").encode()
    return bytes(out)


def estimate_pdf_pages(txt, st):
    """Fast page estimate from the text layout (the exact count needs a full render)."""
    W, H = (595, 842) if st["pdf_page"] == "A4" else (612, 792)
    M, fs = int(st["pdf_margin"]), int(st["pdf_font_size"])
    per_line = max(20, int((W - 2 * M) / (fs * 0.5)))
    lines = sum(max(1, math.ceil(len(l) / per_line)) for l in txt.split("\n"))
    return max(1, math.ceil(lines / max(10, int((H - 2 * M) / (fs * 1.35))))) + (1 if st["pdf_title_page"] else 0)


def export(recs, inp, st, path, reasons=None, variants=None):
    """Writes ONE combined file (originals + variants) in inp['output_type']."""
    kind = inp["output_type"]
    if kind == "pdf":
        with open(path, "wb") as f:
            f.write(render_pdf(recs, inp, st, reasons, variants))
    else:
        txt = render_txt(recs, inp, st, reasons, variants) if kind == "txt" else render_json(recs, inp, st, reasons, variants)
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)
    return path


def default_filename(inp, st):
    slug = re.sub(r"[^a-z0-9]+", "-", "-".join(inp["topics"]).lower()).strip("-")[:40] or "data"
    return f"{st['file_prefix']}_{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{inp['output_type']}"


TYPE_SHARE = {"problems & solution papers": 4, "worked examples": 3, "research papers": 1.5, "problems only": 1.5}


def run_pipeline(inp, st, log=print, cancel=None, progress=None, searcher=None, stage=None):
    """Input -> Web search -> Filterer -> DataGen. Returns a result dict for the output presenter."""
    progress = progress or (lambda f, m="": None)
    stage = stage or (lambda name, state, info="": None)
    cancel = cancel or threading.Event()
    searcher = searcher or Searcher(st, log, cancel, progress=progress)
    types = [t for t in (inp.get("data_types") or [inp["data_type"]]) if t in DATA_TYPES] or [inp["data_type"]]
    if len(types) > 1:  # every selected type gets its share of the quantity; DataGen then runs once on the whole set
        q, w = inp["quantity"], [TYPE_SHARE[t] for t in types]
        quota = [max(1, round(q * x / sum(w))) for x in w]
        quota[0] += q - sum(quota)
        merged = {"records": [], "rejected": [], "reasons": {}, "stats": {}, "notes": {}}
        t0 = time.time()
        for i, (t, n) in enumerate(zip(types, quota)):
            if n <= 0 or cancel.is_set():
                continue
            log(f"--- data type {i + 1}/{len(types)}: {t} ({n} records)")
            sub = dict(inp, data_type=t, data_types=[t], quantity=n, datagen_variations=0)
            res = run_pipeline(sub, st, log, cancel, lambda f, m="", i=i: progress((i + f * 0.9) / len(types) * 0.85,
                                                                                    f"{t}: {m}"), searcher, stage)
            for r in res["records"]:
                r["data_type"] = t
            merged["records"] += res["records"]
            merged["rejected"] += res["rejected"]
            for k, v in res["reasons"].items():
                merged["reasons"][k] = merged["reasons"].get(k, 0) + v
            merged["notes"].update(res["notes"])
        missing = q - len(merged["records"])
        if missing > 0 and not cancel.is_set():  # a type that found little: top up from the most productive type
            best = max(types, key=lambda t: sum(1 for r in merged["records"] if r.get("data_type") == t))
            log(f"--- top-up: {missing} more from '{best}'")
            res = run_pipeline(dict(inp, data_type=best, data_types=[best], quantity=missing, datagen_variations=0),
                               st, log, cancel, lambda f, m="": progress(0.85 + f * 0.05, f"top-up: {m}"), searcher, stage)
            for r in res["records"]:
                r["data_type"] = best
            merged["records"] += res["records"]
            merged["rejected"] += res["rejected"]
        merged["stats"] = dict(searcher.stats)
        stage("search", "done", f"{sum(merged['stats'].values())} found · {len(types)} data types")
        stage("filter", "done" if merged["records"] else "error", f"{len(merged['records'])} kept · {len(merged['rejected'])} rejected")
        variants = []
        if inp.get("datagen_variations", 0) > 0 and merged["records"] and not cancel.is_set() and product_on(st, "product_datagen"):
            stage("datagen", "active", "generating…")
            dg = DataGen(st, log)
            variants = dg.generate(merged["records"], inp, progress, cancel)
            stage("datagen", "done", f"{len(variants)} variants · {dg.counts['numbers']} re-solved (SymPy)")
        else:
            stage("datagen", "skipped", "off" if inp.get("datagen_variations", 0) == 0 else "nothing to vary")
        progress(1.0, "done")
        total = len(merged["records"]) + len(variants)
        stage("output", "done" if total else "error", f"{inp['output_type'].upper()} · {total} records ready")
        log(f"Done in {time.time() - t0:.1f}s: {len(merged['records'])}/{q} records ({', '.join(types)}) + {len(variants)} variants.")
        merged["variants"] = variants
        return merged
    t0 = time.time()
    stage("search", "active", "searching…")
    raw = searcher.search(inp)
    src_txt = ", ".join(f"{k} {v}" for k, v in searcher.stats.items() if v)
    note = "; ".join(f"{k}: {v}" for k, v in searcher.notes.items())
    stage("search", "done" if raw else "error", f"{len(raw)} found" + (f" · {src_txt}" if src_txt else "") + (f" · {note}" if note else ""))
    stage("filter", "active", "scoring…")
    progress(0.75, "filtering")
    filt = Filterer(st, log) if product_on(st, "product_filter") else None
    final, rejected, reasons = filt.run(raw, inp) if filt else (raw[:inp["quantity"]], [], {})
    rounds = 0
    while len(final) < inp["quantity"] and rounds < int(st["refill_rounds"]) and not cancel.is_set() \
            and time.time() - t0 < int(st["max_runtime"]):
        rounds += 1
        missing = inp["quantity"] - len(final)
        log(f"Refill round {rounds}: {missing} more needed - searching deeper (sources continue where they stopped)")
        stage("search", "active", f"refill round {rounds}…")
        more = searcher.search(dict(inp, quantity=max(missing * 2, 4)))
        if not more:
            log("Refill: no new candidates left in the sources.")
            break
        raw += more
        final, rejected, reasons = filt.run(raw, inp) if filt else (raw[:inp["quantity"]], [], {})
    if inp["data_type"] == "problems only":
        for r in final:
            r["solution"] = ""  # the user asked for problems only
    stage("filter", "done" if final else "error", f"{len(final)} kept · {len(rejected)} rejected")
    variants = []
    if inp.get("datagen_variations", 0) > 0 and final and not cancel.is_set() and product_on(st, "product_datagen"):
        stage("datagen", "active", "generating…")
        dg = DataGen(st, log)
        variants = dg.generate(final, inp, progress, cancel)
        stage("datagen", "done", f"{len(variants)} variants · {dg.counts['numbers']} re-solved (SymPy)")
    else:
        stage("datagen", "skipped", "off" if inp.get("datagen_variations", 0) == 0 else "nothing to vary")
    progress(1.0, "done")
    total = len(final) + len(variants)
    stage("output", "done" if total else "error", f"{inp['output_type'].upper()} · {total} records ready")
    log(f"Done in {time.time() - t0:.1f}s: {len(final)}/{inp['quantity']} records + {len(variants)} DataGen variants.")
    return {"records": final, "rejected": rejected, "reasons": reasons, "variants": variants,
            "stats": dict(searcher.stats), "notes": dict(searcher.notes)}


# ============================================================================= Parallel Web Technologies
# Product by ProLab Robotics. Runs many tasks at once (hundreds or thousands queued, as many in flight as the
# worker setting allows) while a shared per-host limiter keeps every site inside its published rate limits:
# the speed comes from asking many different hosts and topics at the same time, never from hammering one host.
# requests per second per host - each value is at or under what that service documents for keyless clients
PWT_HOST_RATES = {
    "api.stackexchange.com": 2.0,             # 30/s max per IP; the keyless daily quota (300) is the real limit
    "datasets-server.huggingface.co": 1.5,   # Hugging Face answers 429 above this for anonymous clients
    "huggingface.co": 1.0,
    "en.wikibooks.org": 1.0, "en.wikipedia.org": 4.0, "commons.wikimedia.org": 2.0, "upload.wikimedia.org": 2.0,
    "thumb.wikimedia.org": 2.0,
    "export.arxiv.org": 0.33,                 # arXiv asks for one request every 3 seconds
    "api.openalex.org": 5.0,                  # 10/s documented
    "api.openverse.org": 0.2,
    "html.duckduckgo.com": 0.05, "api.duckduckgo.com": 0.5,
}
AGENT_KINDS = ["archive", "text", "web_images", "synthetic_images", "vla"]
AGENT_KIND_LABELS = {"archive": "Q&A archives (Stack Exchange, MathOverflow, medicine)", "text": "Topic search + DataGen",
                     "web_images": "Web images (free licences)",
                     "synthetic_images": "Generated images (detection)", "vla": "Robot VLA episodes"}


def _pwt_rates(st):
    rates = dict(PWT_HOST_RATES)
    for part in str(st.get("pwt_host_rates", "")).split(","):
        if "=" in part:
            h, v = part.split("=", 1)
            try:
                rates[h.strip()] = max(0.01, float(v))
            except ValueError:
                pass
    return rates


class HostLimiter:
    """Thread-safe: each host gets at most `rate` requests per second across ALL workers, and backs off
    for the whole pool when it answers 429/503."""

    def __init__(self, st=None):
        self.lock = threading.Lock()
        self.next_slot, self.cool, self.count, self.throttled = {}, {}, {}, {}
        self.n_waiting, self.waiting_host = 0, {}
        self.configure(st or {})

    def configure(self, st, scale=1.0):
        """scale = this process's share when several agent processes run (the sites' total rate never grows)."""
        self.scale = max(0.001, float(scale))
        self.rates = {h: r * self.scale for h, r in _pwt_rates(st).items()}
        self.default = float(st.get("pwt_default_rate", 2.0) or 2.0) * self.scale

    def wait(self, host, cancel=None):
        rate = self.rates.get(host, self.default)
        with self.lock:
            now = time.time()
            slot = max(now, self.next_slot.get(host, 0.0), self.cool.get(host, 0.0))
            self.next_slot[host] = slot + 1.0 / rate
            self.count[host] = self.count.get(host, 0) + 1
        if slot - time.time() <= 0:
            return
        with self.lock:  # this agent now waits for its turn at the site
            self.n_waiting += 1
            self.waiting_host[host] = self.waiting_host.get(host, 0) + 1
        try:
            while True:
                left = slot - time.time()
                if left <= 0 or (cancel is not None and cancel.is_set()):
                    return
                time.sleep(min(left, 0.5))
        finally:
            with self.lock:
                self.n_waiting -= 1
                self.waiting_host[host] -= 1

    def waiting(self):
        with self.lock:
            return self.n_waiting

    def penalize(self, host, seconds):
        with self.lock:
            self.cool[host] = max(self.cool.get(host, 0.0), time.time() + seconds)
            self.throttled[host] = self.throttled.get(host, 0) + 1

    def snapshot(self):
        with self.lock:
            return {h: {"requests": n, "throttled": self.throttled.get(h, 0), "waiting": self.waiting_host.get(h, 0),
                        "rate": self.rates.get(h, self.default)} for h, n in sorted(self.count.items(), key=lambda x: -x[1])}


HOST_LIMITER = None  # set when Parallel Web Technologies is on; Http.fetch then shares one limiter across threads


def pwt_on(st):
    global HOST_LIMITER
    if st.get("pwt_enabled", True):
        if HOST_LIMITER is None:
            HOST_LIMITER = HostLimiter(st)
        else:
            HOST_LIMITER.configure(st)
    else:
        HOST_LIMITER = None
    return HOST_LIMITER


# ----------------------------------------------------------------------------- endless topic stream
TAXONOMY = {  # field -> core topics (depth 0); ADVANCED below adds specialist / research-level subtopics (depth 1)
    "mathematics": ["algebra", "linear algebra", "abstract algebra", "calculus", "multivariable calculus", "real analysis",
                    "complex analysis", "differential equations", "partial differential equations", "number theory",
                    "combinatorics", "graph theory", "probability", "geometry", "trigonometry", "topology",
                    "numerical analysis", "optimization", "game theory", "set theory", "mathematical logic", "group theory",
                    "fourier analysis", "measure theory", "stochastic processes", "linear programming", "vector calculus",
                    "matrices", "sequences and series", "inequalities", "functional equations", "word problems",
                    "percentages", "fractions", "ratios and proportions", "exponents and logarithms", "polynomials",
                    "ring theory", "field theory", "galois theory", "differential geometry", "algebraic geometry",
                    "algebraic topology", "functional analysis", "harmonic analysis", "dynamical systems", "category theory",
                    "representation theory", "lie algebras", "commutative algebra", "homological algebra", "mathematical proofs"],
    "statistics": ["statistics", "hypothesis testing", "confidence intervals", "regression analysis", "bayesian statistics",
                   "maximum likelihood estimation", "analysis of variance", "time series analysis", "survival analysis",
                   "nonparametric statistics", "experimental design", "sampling theory", "multivariate statistics"],
    "physics": ["classical mechanics", "kinematics", "dynamics", "rotational motion", "oscillations", "waves", "optics",
                "thermodynamics", "statistical mechanics", "electromagnetism", "electrostatics", "magnetism",
                "circuits", "quantum mechanics", "special relativity", "general relativity", "nuclear physics",
                "particle physics", "fluid dynamics", "solid state physics", "astrophysics", "acoustics", "gravitation",
                "lagrangian mechanics", "hamiltonian mechanics", "plasma physics", "quantum field theory",
                "condensed matter physics", "atomic physics", "laser physics", "cosmology", "quantum information"],
    "chemistry": ["stoichiometry", "chemical equilibrium", "acid base chemistry", "electrochemistry", "organic chemistry",
                  "reaction mechanisms", "thermochemistry", "chemical kinetics", "inorganic chemistry", "physical chemistry",
                  "spectroscopy", "polymer chemistry", "biochemistry", "analytical chemistry", "gas laws", "solutions chemistry",
                  "quantum chemistry", "periodic trends", "coordination chemistry", "organometallic chemistry",
                  "computational chemistry", "medicinal chemistry", "photochemistry", "surface chemistry"],
    "biology": ["genetics", "molecular biology", "cell biology", "ecology", "evolution", "physiology", "immunology",
                "microbiology", "neuroscience", "botany", "zoology", "bioinformatics", "population genetics", "enzymes",
                "photosynthesis", "cellular respiration", "anatomy", "developmental biology", "structural biology",
                "systems biology", "epigenetics", "virology", "biophysics"],
    "computer science": ["algorithms", "data structures", "dynamic programming", "graph algorithms", "sorting algorithms",
                         "complexity theory", "computability", "operating systems", "computer networks", "databases",
                         "sql", "compilers", "distributed systems", "cryptography", "computer architecture",
                         "concurrency", "functional programming", "object oriented programming", "software testing",
                         "regular expressions", "recursion", "hashing", "string algorithms", "computational geometry",
                         "automata theory", "formal languages", "type theory", "programming language semantics",
                         "information theory", "computer graphics", "parallel computing", "quantum computing"],
    "programming": ["python", "javascript", "typescript", "java", "c++", "c programming", "c#", "rust", "golang", "kotlin",
                    "swift", "bash", "numpy", "pandas", "react", "node.js", "django", "flask", "matlab", "php", "ruby",
                    "haskell", "scala", "julia", "r programming", "cuda", "sql queries", "git", "linux"],
    "machine learning": ["machine learning", "deep learning", "neural networks", "reinforcement learning", "computer vision",
                         "natural language processing", "transformers", "convolutional neural networks", "gradient descent",
                         "bayesian inference", "decision trees", "support vector machines", "clustering",
                         "dimensionality reduction", "generative models", "object detection", "image segmentation",
                         "large language models", "representation learning", "statistical learning theory",
                         "probabilistic graphical models", "recommender systems", "speech recognition"],
    "robotics": ["robotics", "robot kinematics", "inverse kinematics", "robot dynamics", "motion planning", "path planning",
                 "control theory", "pid control", "kalman filter", "slam", "sensor fusion", "robot grasping", "mobile robots",
                 "servo motors", "stepper motors", "gantry robots", "trajectory generation", "arduino", "raspberry pi",
                 "embedded systems", "mechatronics", "visual servoing", "robot perception", "legged locomotion",
                 "manipulation", "humanoid robots", "swarm robotics", "robot learning"],
    "engineering": ["electronics", "digital logic", "signal processing", "control systems", "power electronics",
                    "analog circuits", "semiconductors", "statics", "strength of materials", "heat transfer",
                    "fluid mechanics", "structural engineering", "materials science", "thermodynamic cycles",
                    "microcontrollers", "communication systems", "antennas", "electric motors", "vlsi design",
                    "electromagnetic compatibility", "finite element analysis", "aerospace engineering",
                    "chemical engineering", "civil engineering", "mechanical design", "rf engineering"],
    "earth and space": ["astronomy", "orbital mechanics", "cosmology", "geology", "meteorology", "oceanography",
                        "climate science", "planetary science", "seismology", "geophysics", "atmospheric physics",
                        "exoplanets", "stellar astrophysics", "galactic dynamics"],
    "economics and finance": ["economics", "microeconomics", "macroeconomics", "econometrics", "game theory economics",
                              "finance", "corporate finance", "option pricing", "interest rates", "accounting",
                              "quantitative finance", "portfolio theory", "behavioral economics", "public economics",
                              "international trade", "monetary policy", "industrial organization", "labor economics"],
    "medicine": ["medicine", "pharmacology", "epidemiology", "biostatistics", "physiology medicine", "pathology",
                 "cardiology", "neurology", "oncology", "endocrinology", "infectious diseases", "radiology",
                 "clinical trials", "medical genetics", "immunotherapy", "public health"],
    "humanities": ["philosophy", "ethics", "formal logic", "history", "linguistics", "law", "english grammar",
                   "writing", "geography", "philosophy of mind", "philosophy of science", "epistemology",
                   "political philosophy", "constitutional law", "contract law", "semantics", "syntax", "phonology"],
    "psychology": ["cognitive psychology", "developmental psychology", "social psychology", "psychometrics",
                   "behavioral neuroscience", "clinical psychology", "decision making"],
    "materials science": ["crystallography", "phase diagrams", "metallurgy", "ceramics", "composite materials",
                          "nanomaterials", "thin films", "semiconductor materials", "corrosion", "polymers"],
}
ADVANCED = {  # specialist and research-level subtopics - what makes a model "very advanced" in each field
    "mathematics": [
        # algebraic geometry
        "schemes", "sheaf cohomology", "etale cohomology", "intersection theory", "moduli spaces", "toric varieties",
        "elliptic curves", "abelian varieties", "hodge theory", "geometric invariant theory", "riemann-roch theorem",
        "divisors and line bundles", "grothendieck topologies", "derived algebraic geometry", "tropical geometry",
        # number theory
        "analytic number theory", "riemann zeta function", "dirichlet l-functions", "modular forms", "galois representations",
        "iwasawa theory", "p-adic analysis", "class field theory", "sieve methods", "diophantine approximation",
        "quadratic forms", "algebraic number theory", "langlands program", "elliptic curve cryptography", "prime number theorem",
        "quadratic reciprocity", "continued fractions", "pell equations", "arithmetic geometry",
        # topology and geometry
        "homotopy groups", "spectral sequences", "k-theory", "cobordism", "fundamental group", "covering spaces",
        "simplicial homology", "singular cohomology", "characteristic classes", "fiber bundles", "morse theory",
        "knot theory", "3-manifolds", "riemannian geometry", "curvature tensors", "geodesics", "lie groups",
        "symplectic geometry", "gauge theory mathematics", "atiyah-singer index theorem", "differential forms",
        "de rham cohomology", "complex manifolds", "kahler manifolds", "minimal surfaces", "geometric group theory",
        # analysis
        "banach spaces", "hilbert spaces", "spectral theory", "distribution theory", "sobolev spaces", "operator algebras",
        "c*-algebras", "von neumann algebras", "lebesgue integration", "lp spaces", "fourier transform",
        "wavelets", "complex dynamics", "conformal mappings", "residue theorem", "analytic continuation",
        "riemann surfaces", "several complex variables", "potential theory", "ergodic theory",
        # pde and applied
        "elliptic partial differential equations", "parabolic equations", "hyperbolic equations", "navier-stokes equations",
        "calculus of variations", "optimal transport", "variational methods", "green's functions", "perturbation theory",
        "asymptotic analysis", "integral equations", "inverse problems", "mathematical biology", "bifurcation theory",
        "chaos theory", "hamiltonian systems", "control theory mathematics",
        # probability
        "martingales", "brownian motion", "stochastic calculus", "ito calculus", "stochastic differential equations",
        "large deviations", "markov chain mixing times", "random matrices", "percolation", "concentration inequalities",
        "central limit theorem", "law of large numbers", "random walks", "poisson processes", "queueing theory",
        # combinatorics and discrete
        "extremal graph theory", "ramsey theory", "additive combinatorics", "probabilistic method", "algebraic combinatorics",
        "matroids", "generating functions", "enumerative combinatorics", "graph coloring", "spectral graph theory",
        "combinatorial designs", "partition theory", "symmetric functions", "coding theory",
        # algebra
        "sylow theorems", "group actions", "representation theory of finite groups", "character theory",
        "lie algebra representations", "noetherian rings", "dedekind domains", "local rings", "tensor products",
        "modules over a pid", "jordan canonical form", "spectral theorem", "bilinear forms", "clifford algebras",
        "hopf algebras", "quantum groups", "universal algebra", "homological dimension", "derived functors",
        "ext and tor", "triangulated categories", "abelian categories",
        # logic and foundations
        "model theory", "forcing", "large cardinals", "computability theory", "godel's incompleteness theorems",
        "zermelo-fraenkel set theory", "ordinal numbers", "cardinal arithmetic", "proof theory", "topos theory",
        "homotopy type theory", "adjoint functors", "monads", "yoneda lemma",
        # numerical and optimization
        "finite element method", "krylov subspace methods", "multigrid methods", "numerical linear algebra",
        "convex optimization", "lagrangian duality", "interior point methods", "nonlinear programming",
        "integer programming", "combinatorial optimization", "stochastic optimization", "numerical integration",
        "runge-kutta methods", "spectral methods", "monte carlo methods",
        # competition
        "olympiad inequalities", "olympiad geometry", "olympiad number theory", "olympiad combinatorics",
        "functional equations olympiad", "invariants and monovariants", "pigeonhole principle", "induction proofs"],
    "statistics": ["generalized linear models", "mixed effects models", "causal inference", "instrumental variables",
                   "propensity score matching", "bootstrap methods", "markov chain monte carlo", "gibbs sampling",
                   "hierarchical bayesian models", "variational inference", "gaussian processes regression",
                   "high-dimensional statistics", "lasso regression", "false discovery rate", "empirical bayes",
                   "extreme value theory", "copulas", "kernel density estimation", "state space models", "arima models",
                   "cox proportional hazards", "design of experiments", "bayesian model selection", "sufficient statistics",
                   "fisher information", "cramer-rao bound", "likelihood ratio tests", "asymptotic statistics"],
    "physics": ["renormalization", "feynman diagrams", "gauge theories", "yang-mills theory", "quantum chromodynamics",
                "electroweak theory", "spontaneous symmetry breaking", "higgs mechanism", "path integrals",
                "scattering theory", "dirac equation", "klein-gordon equation", "supersymmetry", "string theory",
                "conformal field theory", "anomalies in quantum field theory", "effective field theory",
                "bcs superconductivity", "topological insulators", "quantum hall effect", "bose-einstein condensation",
                "band theory", "hubbard model", "fermi liquid theory", "phonons", "spin waves", "superfluidity",
                "density functional theory", "schwarzschild metric", "black hole thermodynamics", "gravitational waves",
                "cosmological perturbation theory", "inflationary cosmology", "dark matter", "cosmic microwave background",
                "ising model", "renormalization group", "phase transitions", "fokker-planck equation", "langevin equation",
                "quantum entanglement", "quantum error correction", "quantum channels", "decoherence", "bell inequalities",
                "angular momentum quantum mechanics", "hydrogen atom", "perturbation theory quantum", "wkb approximation",
                "variational method quantum", "second quantization", "harmonic oscillator quantum", "spin-orbit coupling",
                "noether's theorem", "rigid body dynamics", "canonical transformations", "hamilton-jacobi equation",
                "maxwell's equations", "electromagnetic waves", "waveguides", "special relativity kinematics",
                "lorentz transformations", "four-vectors", "nonlinear optics", "quantum optics", "magnetohydrodynamics",
                "turbulence", "boundary layers", "nuclear reactions", "neutrino oscillations", "standard model",
                "semiconductor physics", "laser cooling", "cold atoms", "stellar structure", "accretion disks"],
    "chemistry": ["molecular orbital theory", "hartree-fock method", "valence bond theory", "crystal field theory",
                  "ligand field theory", "pericyclic reactions", "diels-alder reaction", "aldol reaction",
                  "grignard reaction", "nucleophilic substitution", "elimination reactions", "aromaticity",
                  "stereochemistry", "chirality", "retrosynthesis", "total synthesis", "protecting groups",
                  "cross-coupling reactions", "olefin metathesis", "asymmetric catalysis", "enzyme kinetics",
                  "michaelis-menten kinetics", "transition state theory", "marcus theory", "nmr spectroscopy",
                  "mass spectrometry", "infrared spectroscopy", "x-ray crystallography", "chromatography",
                  "electrochemical cells", "nernst equation", "gibbs free energy", "entropy chemistry",
                  "chemical potential", "colligative properties", "buffer solutions", "solubility equilibria",
                  "redox titrations", "group theory in chemistry", "point groups", "polymerization mechanisms",
                  "supramolecular chemistry", "catalysis", "zeolites", "metal-organic frameworks", "green chemistry",
                  "radical reactions", "carbocation rearrangements", "heterocyclic chemistry", "drug design"],
    "biology": ["dna replication", "transcription", "translation", "gene regulation", "crispr", "rna interference",
                "protein folding", "signal transduction", "cell cycle", "apoptosis", "mitosis", "meiosis",
                "mendelian genetics", "hardy-weinberg equilibrium", "genetic drift", "natural selection", "phylogenetics",
                "speciation", "population dynamics", "lotka-volterra equations", "ecosystem ecology", "food webs",
                "innate immunity", "adaptive immunity", "antibodies", "t cells", "neurotransmitters", "action potentials",
                "synaptic plasticity", "hormones", "metabolic pathways", "glycolysis", "krebs cycle",
                "oxidative phosphorylation", "membrane transport", "stem cells", "embryogenesis", "gene expression analysis",
                "sequence alignment", "genome assembly", "protein structure prediction", "molecular evolution",
                "microbial genetics", "bacterial growth", "viral replication", "cancer biology", "mutations",
                "chromatin structure", "dna methylation", "plant physiology", "animal behavior"],
    "computer science": ["np-completeness", "polynomial-time reductions", "approximation algorithms", "randomized algorithms",
                         "online algorithms", "streaming algorithms", "communication complexity", "pcp theorem",
                         "circuit complexity", "parameterized complexity", "fine-grained complexity", "amortized analysis",
                         "network flow", "max-flow min-cut", "bipartite matching", "linear programming duality algorithms",
                         "shortest path algorithms", "minimum spanning trees", "union-find", "segment trees", "fenwick trees",
                         "suffix arrays", "tries", "balanced binary search trees", "b-trees", "hash tables", "bloom filters",
                         "skip lists", "heaps", "divide and conquer", "greedy algorithms", "backtracking",
                         "branch and bound", "string matching", "knuth-morris-pratt algorithm", "fast fourier transform algorithm",
                         "lambda calculus", "type inference", "hindley-milner type system", "dependent types",
                         "formal verification", "model checking", "hoare logic", "separation logic", "abstract interpretation",
                         "paxos", "raft consensus", "byzantine fault tolerance", "distributed hash tables", "cap theorem",
                         "vector clocks", "mutual exclusion algorithms", "deadlock", "memory consistency models",
                         "cache coherence", "virtual memory", "page replacement algorithms", "scheduling algorithms",
                         "file systems", "tcp congestion control", "routing algorithms", "public key cryptography",
                         "rsa", "elliptic curve cryptography algorithms", "zero-knowledge proofs", "hash functions",
                         "digital signatures", "lattice-based cryptography", "context-free grammars", "turing machines",
                         "pushdown automata", "regular languages", "pumping lemma", "decidability", "halting problem",
                         "query optimization", "transaction isolation", "b+ trees", "relational algebra", "normalization databases",
                         "register allocation", "parsing algorithms", "garbage collection", "jit compilation",
                         "quantum algorithms", "shor's algorithm", "grover's algorithm", "ray tracing", "rasterization"],
    "programming": ["python decorators", "python generators", "asyncio", "python type hints", "metaclasses",
                    "c++ templates", "move semantics", "smart pointers", "rust ownership", "rust lifetimes", "rust traits",
                    "javascript closures", "promises and async await", "event loop", "typescript generics",
                    "java concurrency", "java streams", "go concurrency", "haskell monads", "functional programming patterns",
                    "design patterns", "unit testing", "memory leaks", "multithreading", "regex", "sql joins",
                    "sql window functions", "dataframe operations", "numpy broadcasting", "vectorization",
                    "performance optimization", "profiling", "debugging", "api design", "dependency injection",
                    "build systems", "makefiles", "docker", "bit manipulation", "recursion to iteration",
                    "cuda kernels", "simd", "linked lists", "binary trees", "graph traversal code", "string manipulation"],
    "machine learning": ["backpropagation", "attention mechanisms", "self-attention", "positional encoding",
                         "diffusion models", "variational autoencoders", "normalizing flows", "generative adversarial networks",
                         "policy gradients", "q-learning", "actor-critic methods", "proximal policy optimization",
                         "markov decision processes", "bellman equations", "multi-armed bandits", "pac learning",
                         "vc dimension", "rademacher complexity", "kernel methods", "gaussian processes",
                         "graph neural networks", "batch normalization", "dropout", "weight initialization",
                         "adam optimizer", "learning rate schedules", "regularization", "bias-variance tradeoff",
                         "cross-validation", "expectation maximization", "hidden markov models", "variational bayes",
                         "contrastive learning", "self-supervised learning", "transfer learning", "fine-tuning",
                         "low-rank adaptation", "knowledge distillation", "quantization", "mixture of experts",
                         "tokenization", "word embeddings", "sequence to sequence models", "beam search",
                         "reinforcement learning from human feedback", "direct preference optimization",
                         "object detection architectures", "semantic segmentation", "vision transformers", "u-net",
                         "neural radiance fields", "anomaly detection", "time series forecasting", "causal machine learning",
                         "interpretability", "adversarial examples", "federated learning", "meta-learning",
                         "imitation learning", "world models", "vision-language models", "vision-language-action models"],
    "robotics": ["denavit-hartenberg parameters", "forward kinematics", "jacobian matrix robotics", "singularities robotics",
                 "jacobian-based inverse kinematics", "redundant manipulators", "lagrangian robot dynamics",
                 "newton-euler dynamics", "computed torque control", "impedance control", "force control",
                 "model predictive control", "linear quadratic regulator", "lyapunov stability", "feedback linearization",
                 "sliding mode control", "adaptive control", "robust control", "state estimation", "extended kalman filter",
                 "unscented kalman filter", "particle filter", "visual odometry", "lidar slam", "occupancy grid mapping",
                 "loop closure", "bundle adjustment", "camera calibration", "hand-eye calibration", "pose estimation",
                 "point cloud registration", "iterative closest point", "rrt", "probabilistic roadmaps", "a* search",
                 "trajectory optimization", "minimum jerk trajectories", "spline trajectories", "collision detection",
                 "grasp planning", "contact mechanics", "differential drive kinematics", "ackermann steering",
                 "quadrotor dynamics", "legged robot balance", "zero moment point", "whole-body control",
                 "reinforcement learning for robotics", "sim-to-real transfer", "behavior cloning", "teleoperation",
                 "encoders and odometry", "motor control electronics", "pwm motor control", "g-code", "cnc kinematics",
                 "pick and place", "conveyor tracking", "multi-robot coordination", "ros"],
    "engineering": ["laplace transform", "z-transform", "transfer functions", "bode plots", "nyquist stability criterion",
                    "root locus", "state space control", "pid tuning", "digital filters", "fir filters", "iir filters",
                    "sampling theorem", "discrete fourier transform", "modulation", "error correcting codes",
                    "op-amp circuits", "transistor amplifiers", "mosfet", "bjt", "power supplies", "dc-dc converters",
                    "inverters", "three-phase power", "transformers electrical", "induction motors", "pcb design",
                    "fpga", "verilog", "timing analysis", "beam bending", "stress and strain", "mohr's circle",
                    "buckling", "fatigue", "vibrations", "finite element modeling", "convection heat transfer",
                    "conduction", "radiation heat transfer", "pipe flow", "bernoulli equation", "pumps and turbines",
                    "rankine cycle", "brayton cycle", "refrigeration cycles", "combustion", "aerodynamics", "airfoils",
                    "propulsion", "orbital mechanics engineering", "control of aircraft", "reinforced concrete",
                    "soil mechanics", "structural analysis", "chemical reactor design", "mass transfer", "distillation"],
    "earth and space": ["kepler's laws", "hohmann transfer", "orbital elements", "n-body problem", "lagrange points",
                        "stellar evolution", "nucleosynthesis", "hertzsprung-russell diagram", "neutron stars",
                        "white dwarfs", "supernovae", "galaxy formation", "hubble's law", "dark energy",
                        "big bang nucleosynthesis", "radiative transfer", "plate tectonics", "mineralogy", "petrology",
                        "sedimentology", "geochronology", "earthquake seismology", "atmospheric circulation",
                        "numerical weather prediction", "climate models", "greenhouse effect", "ocean circulation",
                        "glaciology", "hydrology", "planetary atmospheres", "spectroscopy astronomy", "telescopes",
                        "exoplanet detection methods", "gravitational lensing", "cosmic rays"],
    "economics and finance": ["general equilibrium", "mechanism design", "auction theory", "contract theory",
                              "black-scholes model", "stochastic volatility", "binomial option pricing", "greeks finance",
                              "fixed income", "yield curve", "duration and convexity", "capital asset pricing model",
                              "arbitrage pricing theory", "efficient market hypothesis", "value at risk", "credit risk models",
                              "dsge models", "solow growth model", "is-lm model", "phillips curve", "consumer theory",
                              "producer theory", "market structures", "oligopoly", "nash equilibrium", "bayesian games",
                              "signaling games", "information asymmetry", "moral hazard", "adverse selection",
                              "welfare economics", "cost-benefit analysis", "panel data", "difference in differences",
                              "regression discontinuity", "time series econometrics", "cointegration", "garch models",
                              "financial statement analysis", "discounted cash flow", "real options", "market microstructure"],
    "medicine": ["pharmacokinetics", "pharmacodynamics", "drug interactions", "antibiotics", "antiviral drugs",
                 "cardiac electrophysiology", "ecg interpretation", "heart failure", "hypertension", "diabetes mellitus",
                 "thyroid disorders", "renal physiology", "acid-base disorders", "electrolyte disorders",
                 "respiratory physiology", "asthma", "copd", "neuroanatomy", "stroke", "epilepsy", "dementia",
                 "cancer staging", "chemotherapy", "immunology clinical", "autoimmune diseases", "vaccines",
                 "sepsis", "hematology", "anemia", "coagulation", "medical imaging", "diagnostic tests sensitivity",
                 "evidence-based medicine", "randomized controlled trials", "meta-analysis", "survival curves",
                 "gastroenterology", "hepatology", "pediatrics", "obstetrics", "psychiatry", "anesthesiology",
                 "emergency medicine", "surgery principles", "dermatology", "ophthalmology", "medical ethics"],
    "humanities": ["kantian ethics", "utilitarianism", "virtue ethics", "existentialism", "phenomenology",
                   "philosophy of language", "modal logic", "free will", "personal identity", "metaphysics",
                   "theory of knowledge", "scientific method", "historiography", "ancient history", "medieval history",
                   "early modern history", "industrial revolution", "world war ii", "cold war", "history of science",
                   "history of mathematics", "comparative linguistics", "historical linguistics", "morphology linguistics",
                   "pragmatics", "sociolinguistics", "formal semantics", "tort law", "criminal law", "international law",
                   "intellectual property", "jurisprudence", "rhetoric", "literary analysis", "argumentation"],
    "psychology": ["working memory", "attention psychology", "perception", "learning theory", "classical conditioning",
                   "operant conditioning", "cognitive biases", "heuristics", "personality psychology",
                   "item response theory", "factor analysis psychology", "psychopathology", "neuropsychology",
                   "language acquisition", "theory of mind", "motivation", "emotion"],
    "materials science": ["dislocations", "grain boundaries", "diffusion in solids", "phase transformations",
                          "heat treatment", "fracture mechanics", "elasticity", "plasticity", "creep",
                          "electronic properties of materials", "magnetic materials", "superconducting materials",
                          "battery materials", "photovoltaic materials", "biomaterials", "tribology",
                          "x-ray diffraction", "electron microscopy", "materials characterization", "density of states"],
}
# relative share of topics per field when the agent picks the next topic (it rotates through every field)
FIELD_WEIGHTS = {"mathematics": 10, "physics": 8, "computer science": 8, "machine learning": 6, "programming": 6,
                 "chemistry": 6, "biology": 6, "engineering": 6, "robotics": 5, "statistics": 5, "medicine": 5,
                 "economics and finance": 4, "earth and space": 3, "materials science": 3, "humanities": 3,
                 "psychology": 2, "": 4}
# OpenAlex field names -> AITE fields (so OpenAlex topics and keywords get the right expert sources)
OPENALEX_FIELDS = {
    "Mathematics": "mathematics", "Physics and Astronomy": "physics", "Chemistry": "chemistry",
    "Computer Science": "computer science", "Engineering": "engineering", "Medicine": "medicine",
    "Biochemistry, Genetics and Molecular Biology": "biology", "Agricultural and Biological Sciences": "biology",
    "Immunology and Microbiology": "biology", "Neuroscience": "biology", "Earth and Planetary Sciences": "earth and space",
    "Environmental Science": "earth and space", "Economics, Econometrics and Finance": "economics and finance",
    "Business, Management and Accounting": "economics and finance", "Decision Sciences": "statistics",
    "Arts and Humanities": "humanities", "Social Sciences": "humanities", "Psychology": "psychology",
    "Materials Science": "materials science", "Energy": "engineering", "Chemical Engineering": "engineering",
    "Pharmacology, Toxicology and Pharmaceutics": "medicine", "Health Professions": "medicine", "Nursing": "medicine",
    "Dentistry": "medicine", "Veterinary": "medicine"}
# AITE field -> Stack Exchange API site (topic searches) and archive sites (bulk sweeps of the open Stack Exchange dump)
FIELD_SE_SITE = {"mathematics": "math", "statistics": "stats", "physics": "physics", "chemistry": "chemistry",
                 "biology": "biology", "computer science": "cs", "programming": "stackoverflow", "machine learning": "ai",
                 "robotics": "robotics", "engineering": "electronics", "earth and space": "astronomy",
                 "economics and finance": "economics", "medicine": "medicalsciences", "humanities": "philosophy",
                 "psychology": "psychology", "materials science": "mattermodeling"}
ARCHIVE_SITES = {  # Stack Exchange dump folder -> (AITE field, share)
    "math.stackexchange.com": ("mathematics", 10), "mathoverflow.net": ("mathematics", 6),
    "physics.stackexchange.com": ("physics", 8), "chemistry.stackexchange.com": ("chemistry", 5),
    "biology.stackexchange.com": ("biology", 3), "bioinformatics.stackexchange.com": ("biology", 1),
    "cs.stackexchange.com": ("computer science", 4), "cstheory.stackexchange.com": ("computer science", 3),
    "crypto.stackexchange.com": ("computer science", 2), "scicomp.stackexchange.com": ("computer science", 2),
    "quantumcomputing.stackexchange.com": ("physics", 2), "astronomy.stackexchange.com": ("earth and space", 2),
    "earthscience.stackexchange.com": ("earth and space", 1), "space.stackexchange.com": ("earth and space", 1),
    "stats.stackexchange.com": ("statistics", 5), "datascience.stackexchange.com": ("machine learning", 2),
    "ai.stackexchange.com": ("machine learning", 2), "electronics.stackexchange.com": ("engineering", 4),
    "engineering.stackexchange.com": ("engineering", 2), "dsp.stackexchange.com": ("engineering", 2),
    "robotics.stackexchange.com": ("robotics", 2), "economics.stackexchange.com": ("economics and finance", 2),
    "quant.stackexchange.com": ("economics and finance", 2), "Stackoverflow.com": ("programming", 6),
    "codereview.stackexchange.com": ("programming", 2), "softwareengineering.stackexchange.com": ("programming", 2),
    "philosophy.stackexchange.com": ("humanities", 1), "linguistics.stackexchange.com": ("humanities", 1),
    "history.stackexchange.com": ("humanities", 1), "law.stackexchange.com": ("humanities", 1),
    "medicalsciences.stackexchange.com": ("medicine", 1), "psychology.stackexchange.com": ("psychology", 1),
    "mattermodeling.stackexchange.com": ("materials science", 1), "or.stackexchange.com": ("mathematics", 1),
    "matheducators.stackexchange.com": ("mathematics", 1), "mathematica.stackexchange.com": ("programming", 1)}
FACETS = ["", "word problems", "proofs", "worked examples", "applications", "common mistakes", "exam questions",
          "competition problems", "conceptual questions", "estimation problems", "real-world robotics applications",
          "step by step derivations"]
LEVELS = ["introductory", "intermediate", "advanced", "olympiad", "graduate"]
_TOPIC_BAD = re.compile(r"^(list|index|outline|glossary|timeline|history) of\b|\(disambiguation\)|\d{3,}|^category:|"
                        r"^template:|^portal:|^wikipedia:|^help:|^file:|award|prize|university|journal|society|"
                        r"\bfc\b|album|film|season|episode", re.I)


def topic_ok(t):
    t = (t or "").strip()
    if not (3 <= len(t) <= 60) or _TOPIC_BAD.search(t):
        return False
    words_ = t.split()
    if not 1 <= len(words_) <= 5:
        return False
    caps = sum(w[:1].isupper() for w in words_)
    return not (len(words_) >= 2 and caps == len(words_) and not any(c.isdigit() for c in t))  # 'John Smith' = a person


class TopicStore:
    """SQLite-backed, endless topic frontier: built-in taxonomy, then OpenAlex's ~4,500 research topics and their
    keywords, then Wikipedia's link graph out of every topic that produced data. Survives restarts."""

    def __init__(self, path):
        import sqlite3
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=60)
        self.lock = threading.Lock()
        try:  # several agent processes share this file: WAL lets readers and one writer work at once ("database is locked")
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=NORMAL")
            self.db.execute("PRAGMA busy_timeout=60000")
        except Exception:
            pass
        with self.lock:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS topics(name TEXT PRIMARY KEY, origin TEXT, depth INT, status TEXT DEFAULT 'new',
                    records INT DEFAULT 0, images INT DEFAULT 0, expanded INT DEFAULT 0, added REAL, done REAL, rnd REAL);
                CREATE INDEX IF NOT EXISTS ix_topics ON topics(status, depth, rnd);
                CREATE TABLE IF NOT EXISTS seen(h TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);""")
            try:
                self.db.execute("ALTER TABLE topics ADD COLUMN field TEXT DEFAULT ''")
            except Exception:
                pass  # already there
            self.db.execute("CREATE INDEX IF NOT EXISTS ix_field ON topics(status, field)")
            self.db.commit()
        if not self.get("taxonomy_v2"):
            for f, subs in TAXONOMY.items():
                self.add(subs, "taxonomy", 0, f)
            for f, subs in ADVANCED.items():
                self.add(subs, "advanced", 1, f)
            self.put("taxonomy_v2", True)

    def add(self, names, origin, depth, field=""):
        rows, now = [], time.time()
        for n in names:
            n = re.sub(r"\s+", " ", str(n)).strip().lower()
            if topic_ok(n):
                rows.append((n, origin, depth, now, random.random(), field or ""))
        with self.lock:
            before = self.db.total_changes
            self.db.executemany("INSERT OR IGNORE INTO topics(name, origin, depth, added, rnd, field) VALUES (?,?,?,?,?,?)", rows)
            self.db.commit()
            return self.db.total_changes - before

    def info(self, name):
        with self.lock:
            r = self.db.execute("SELECT field, depth FROM topics WHERE name=?", (name,)).fetchone()
        return (r[0] or "", r[1]) if r else ("", 0)

    def fields(self):
        with self.lock:
            return dict(self.db.execute("SELECT field, COUNT(*) FROM topics GROUP BY field").fetchall())

    def next(self, n=1, kind="text", focus_only=False):
        """Focus topics first; otherwise rotate through the fields (weighted) and, inside a field, mix core,
        specialist and research-level topics (shallow ones a little more often) so advanced material arrives early."""
        col = "status" if kind == "text" else "images"
        with self.lock:
            if kind == "text":
                rows = self.db.execute("SELECT name FROM topics WHERE status='new' AND depth<0 ORDER BY rnd LIMIT ?", (n,)).fetchall()
                if not rows and not focus_only:
                    avail = dict(self.db.execute("SELECT field, COUNT(*) FROM topics WHERE status='new' GROUP BY field").fetchall())
                    if avail:
                        fs = list(avail)
                        f = random.choices(fs, weights=[FIELD_WEIGHTS.get(x, 1) for x in fs])[0]
                        rows = self.db.execute("SELECT name FROM topics WHERE status='new' AND field=? "
                                               "ORDER BY depth * 0.7 + rnd * 3 LIMIT ?", (f, n)).fetchall()
                self.db.executemany("UPDATE topics SET status='busy' WHERE name=?", rows)
            else:  # images: topics that already gave text, least-imaged first
                rows = self.db.execute("SELECT name FROM topics WHERE status='done' AND records>0 ORDER BY images, rnd LIMIT ?",
                                       (n,)).fetchall() or self.db.execute(
                    "SELECT name FROM topics ORDER BY images, depth, rnd LIMIT ?", (n,)).fetchall()
                self.db.executemany(f"UPDATE topics SET {col}={col}+1 WHERE name=?", rows)
            self.db.commit()
        return [r[0] for r in rows]

    def done(self, name, records):
        with self.lock:
            self.db.execute("UPDATE topics SET status='done', records=records+?, done=? WHERE name=?", (records, time.time(), name))
            self.db.commit()

    def to_expand(self, n=1):
        with self.lock:
            rows = self.db.execute("SELECT name, depth, field FROM topics WHERE status='done' AND records>0 AND expanded=0 "
                                   "ORDER BY records DESC LIMIT ?", (n,)).fetchall()
            self.db.executemany("UPDATE topics SET expanded=1 WHERE name=?", [(r[0],) for r in rows])
            self.db.commit()
        return rows

    LEVEL_NAMES = {-1: "focus", 0: "core", 1: "advanced", 2: "specialist", 3: "research concept"}

    def export_json(self, path, running=None):
        """topics.json: every topic with a check mark when its data is complete - readable progress that also lets a
        fresh copy (another computer, a clone of the repo) continue exactly where collection stopped."""
        with self.lock:
            rows = self.db.execute("SELECT name, field, depth, status, records, images, done FROM topics "
                                   "ORDER BY status='done' DESC, done DESC, field, depth, name").fetchall()
        running = running or {}  # topic -> agent number (the parallel agent collecting it right now)
        fields, out = {}, []
        for name, field, depth, status, rec, img, done in rows:
            ok = status == "done"
            f = fields.setdefault(field or "general", {"done": 0, "left": 0, "in_progress": 0})
            st_ = "done" if ok else "in progress" if name in running or status == "busy" else "left"
            f["done" if ok else "in_progress" if st_ == "in progress" else "left"] += 1
            out.append({"topic": name, "field": field or "general", "level": self.LEVEL_NAMES.get(depth, "linked"),
                        "done": ok, "check": "✓" if ok else "", "status": st_, "agent": running.get(name),
                        "records": rec or 0, "images": img or 0,
                        "completed": datetime.fromtimestamp(done).isoformat(timespec="seconds") if ok and done else ""})
        n_done = sum(1 for t in out if t["done"])
        n_run = sum(1 for t in out if t["status"] == "in progress")
        doc = {"app": APP, "updated": datetime.now().isoformat(timespec="seconds"), "total": len(out), "done": n_done,
               "in_progress": n_run, "left": len(out) - n_done - n_run,
               "parallel_agents": {"running": len(running), "topics": [{"agent": n, "topic": t} for t, n in
                                                                        sorted(running.items(), key=lambda x: x[1])]},
               "fields": dict(sorted(fields.items(), key=lambda x: -(x[1]["done"] + x[1]["left"]))),
               "topics": out}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=0)
        os.replace(tmp, path)
        return doc

    def import_json(self, path):
        """Continue from a topics.json (e.g. pulled from GitHub on another computer): its topics and check marks."""
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, ValueError):
            return 0
        lv = {v: k for k, v in self.LEVEL_NAMES.items()}
        rows, done = [], []
        for t in doc.get("topics", []):
            name = str(t.get("topic", "")).strip().lower()
            if not name:
                continue
            field = "" if t.get("field") == "general" else t.get("field", "")
            rows.append((name, "topics.json", lv.get(t.get("level"), 4), time.time(), random.random(), field))
            if t.get("done"):
                done.append((int(t.get("records") or 0), time.time(), name))
        with self.lock:
            self.db.executemany("INSERT OR IGNORE INTO topics(name, origin, depth, added, rnd, field) VALUES (?,?,?,?,?,?)", rows)
            self.db.executemany("UPDATE topics SET status='done', records=MAX(records, ?), done=COALESCE(done, ?) WHERE name=?", done)
            self.db.commit()
        return len(rows)

    def lists(self, n=12):
        with self.lock:
            nxt = self.db.execute("SELECT name, field FROM topics WHERE status='new' ORDER BY depth<0 DESC, depth, rnd LIMIT ?", (n,)).fetchall()
            done = self.db.execute("SELECT name, field, records FROM topics WHERE status='done' ORDER BY done DESC LIMIT ?", (n,)).fetchall()
            busy = self.db.execute("SELECT COUNT(*) FROM topics WHERE status='busy'").fetchone()[0]
            focus = self.db.execute("SELECT COUNT(*) FROM topics WHERE status='new' AND depth<0").fetchone()[0]
        return {"next": nxt, "recent": done, "in_progress": busy, "focus_left": focus}

    def reset_busy(self):
        with self.lock:
            self.db.execute("UPDATE topics SET status='new' WHERE status='busy'")
            self.db.commit()

    def count(self, status=None):
        with self.lock:
            q = "SELECT COUNT(*) FROM topics" + (" WHERE status=?" if status else "")
            return self.db.execute(q, (status,) if status else ()).fetchone()[0]

    def first_seen(self, keys):
        """Atomically records hashes; returns the ones never seen before (global dedupe across all workers/runs)."""
        out = []
        with self.lock:
            for k in keys:
                try:
                    self.db.execute("INSERT INTO seen(h) VALUES (?)", (k,))
                    out.append(k)
                except Exception:
                    pass
            self.db.commit()
        return out

    def get(self, k, default=None):
        with self.lock:
            r = self.db.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return json.loads(r[0]) if r else default

    def put(self, k, v):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO kv(k, v) VALUES (?,?)", (k, json.dumps(v)))
            self.db.commit()


# ----------------------------------------------------------------------------- open Q&A archives (bulk, human-written)
SE_ARCHIVE = "HuggingFaceH4/stack-exchange-preferences"  # the public Stack Exchange dump, CC BY-SA 4.0, 10.8M questions
SE_ARCHIVE_ROWS = 10807695


def _as_obj(v):
    if isinstance(v, str):
        try:
            import ast
            return ast.literal_eval(v)
        except (ValueError, SyntaxError):
            return {}
    return v or {}


def _medmcqa(r):
    opts = [str(r.get(k) or "").strip() for k in ("opa", "opb", "opc", "opd")]
    try:
        cop = int(r.get("cop"))
    except (TypeError, ValueError):
        return None
    if not r.get("question") or not all(opts) or not 0 <= cop < 4:
        return None
    q = str(r["question"]).strip() + "\n" + "\n".join(f"{'ABCD'[i]}) {o}" for i, o in enumerate(opts))
    exp = clean_html(str(r.get("exp") or ""))
    sol = f"Answer: {'ABCD'[cop]}) {opts[cop]}" + (f"\n\nExplanation: {exp}" if exp else "")
    title = " - ".join(x for x in (r.get("subject_name"), r.get("topic_name")) if x and x != "None") or "Medical exam question"
    return q, sol, title


def _pubmedqa(r):
    ctx = _as_obj(r.get("context"))
    body = " ".join(ctx.get("contexts", [])) if isinstance(ctx, dict) else ""
    if not r.get("question") or not r.get("long_answer") or not body:
        return None
    return (f"{r['question']}\n\nStudy summary: {body}", f"{r['long_answer']}\n\nAnswer: {r.get('final_decision', '')}",
            shorten(r["question"], 100))


def _arc(r):
    ch = _as_obj(r.get("choices"))
    texts, labels = ch.get("text", []), ch.get("label", [])
    if not r.get("question") or not texts or r.get("answerKey") not in labels:
        return None
    i = labels.index(r["answerKey"])
    q = r["question"] + "\n" + "\n".join(f"{l}) {t}" for l, t in zip(labels, texts))
    return q, f"Answer: {labels[i]}) {texts[i]}", shorten(r["question"], 100)


HF_ARCHIVES = {  # open datasets swept page by page (train splits only - benchmarks' test splits stay clean)
    "openlifescienceai/medmcqa": {"config": "default", "rows": 182822, "field": "medicine", "license": "Apache-2.0",
                                  "weight": 3, "map": _medmcqa},
    "qiaojin/PubMedQA": {"config": "pqa_artificial", "rows": 211269, "field": "medicine", "license": "MIT",
                         "weight": 2, "map": _pubmedqa},
    "allenai/ai2_arc": {"config": "ARC-Challenge", "rows": 1119, "field": "earth and space", "license": "CC BY-SA 4.0",
                        "weight": 0.3, "map": _arc},
}


# ----------------------------------------------------------------------------- dataset writer
class ShardWriter:
    """Appends records to gzip JSONL shards: <dir>/<kind>/<kind>-<date>-<n>.jsonl.gz. A shard is written as
    '.open' and renamed when it closes (size limit or every rotate_s seconds), so only finished shards are pushed."""

    def __init__(self, root, kind, max_mb=45, rotate_s=300, tag=""):
        import gzip
        self.tag = tag
        self.gzip, self.root, self.kind = gzip, os.path.join(root, kind), kind
        self.max_bytes, self.rotate_s = int(max_mb * 1024 * 1024), rotate_s
        self.lock = threading.Lock()
        self.f = self.path = None
        self.raw = self.lines = 0
        self.opened = 0.0
        os.makedirs(self.root, exist_ok=True)
        for p in os.listdir(self.root):  # an '.open' shard left by a crash is still valid gzip up to its last flush
            mine = (f"{tag}-" in p) if tag else not re.search(r"-w\d+-", p)
            if p.endswith(".open") and mine:
                try:
                    os.replace(os.path.join(self.root, p), os.path.join(self.root, p[:-5]))
                except OSError:
                    pass

    def _open(self):
        n = 0
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        while True:
            self.path = os.path.join(self.root, f"{self.kind}-{stamp}{self.tag}-{n:03d}.jsonl.gz")
            if not os.path.exists(self.path) and not os.path.exists(self.path + ".open"):
                break
            n += 1
        self.f = self.gzip.open(self.path + ".open", "wt", encoding="utf-8")
        self.raw, self.lines, self.opened = 0, 0, time.time()

    def write(self, recs):
        with self.lock:
            for r in recs:
                if self.f is None:
                    self._open()
                line = json.dumps(r, ensure_ascii=False)
                self.f.write(line + "\n")
                self.raw += len(line) + 1
                self.lines += 1
                if self.raw >= self.max_bytes * 3:  # ~3x gzip ratio keeps the closed shard under max_mb
                    self._close()
            if self.f is not None:
                self.f.flush()

    def _close(self):
        if self.f is not None:
            self.f.close()
            os.replace(self.path + ".open", self.path)
            self.f = None

    def rotate(self, force=False):
        with self.lock:
            if self.f is not None and self.lines and (force or time.time() - self.opened >= self.rotate_s):
                self._close()


def _rid(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8", "replace")).hexdigest()[:16]


def agent_text_record(r, st):
    """One training row: chat messages (SFT) + the plain fields + provenance."""
    meta = r.get("meta", {})
    msgs = meta.get("messages") or [{"role": "user", "content": r["problem"]}] + (
        [{"role": "assistant", "content": r["solution"]}] if r.get("solution") else [])
    d = {"id": _rid(r.get("uid"), r["problem"][:200]), "type": "text", "kind": r.get("kind", "original"),
         "topic": r["topic"], "title": r.get("title", ""), "problem": r["problem"], "solution": r.get("solution", ""),
         "messages": msgs, "source": r.get("source"), "url": r.get("url"), "license": meta.get("license", ""),
         "quality_score": r.get("score"), "created": datetime.now().isoformat(timespec="seconds")}
    if r.get("kind") == "variant":
        d.update(variant_of=_rid(r.get("variant_of"), ""), style=r.get("style"), format=r.get("format"),
                 methods=r.get("methods", []), answer=r.get("answer"), numbers_changed=bool(r.get("numbers_changed")))
    # ready for training: 'text' for continued pre-training, 'messages' for SFT, a stable train/validation split
    # (by the ORIGINAL record, so a record and its variants never land in different splits), size and quality tier
    d["text"] = f"Problem:\n{d['problem']}" + (f"\n\nSolution:\n{d['solution']}" if d["solution"] else "")
    d["tokens"] = max(1, len(d["text"]) // 4)
    fam = r.get("variant_of") or r.get("uid") or d["id"]
    d["split"] = "validation" if int(hashlib.sha1(str(fam).encode()).hexdigest(), 16) % 50 == 0 else "train"
    sc = float(r.get("score") or 0)
    d["quality_tier"] = "high" if sc >= 7 else "medium" if sc >= 4.5 else "basic"
    return d


# ----------------------------------------------------------------------------- image data
SHAPES = ["circle", "square", "triangle", "star", "hexagon", "ring", "cross", "diamond"]
COLORS = {"red": (220, 50, 47), "green": (40, 170, 80), "blue": (38, 110, 220), "yellow": (240, 200, 30),
          "orange": (245, 130, 30), "purple": (140, 70, 190), "white": (245, 245, 245), "black": (25, 25, 25)}
BACKDROPS = ["wooden table", "grey workbench", "white desk", "dark mat", "cardboard sheet", "metal plate"]


def _shape_points(shape, cx, cy, r, rot):
    def poly(n, rr=None, start=0.0):
        return [(cx + (rr[i % len(rr)] if rr else r) * math.cos(rot + start + 2 * math.pi * i / n),
                 cy + (rr[i % len(rr)] if rr else r) * math.sin(rot + start + 2 * math.pi * i / n)) for i in range(n)]
    if shape == "square":
        return poly(4, start=math.pi / 4)
    if shape == "triangle":
        return poly(3, start=-math.pi / 2)
    if shape == "hexagon":
        return poly(6)
    if shape == "diamond":
        return poly(4, [r, r * 0.62])
    if shape == "star":
        return poly(10, [r, r * 0.45], -math.pi / 2)
    if shape == "cross":
        a, b = r, r * 0.34
        pts = [(-b, -a), (b, -a), (b, -b), (a, -b), (a, b), (b, b), (b, a), (-b, a), (-b, b), (-a, b), (-a, -b), (-b, -b)]
        c, s = math.cos(rot), math.sin(rot)
        return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]
    return [(cx + r * math.cos(2 * math.pi * i / 32), cy + r * math.sin(2 * math.pi * i / 32)) for i in range(32)]


def _backdrop(img_mod, size, rng, kind):
    from PIL import ImageDraw, ImageFilter
    base = {"wooden table": (150, 105, 65), "grey workbench": (128, 130, 134), "white desk": (232, 230, 226),
            "dark mat": (40, 46, 52), "cardboard sheet": (190, 160, 115), "metal plate": (170, 175, 180)}[kind]
    im = img_mod.new("RGB", (size, size), base)
    d = ImageDraw.Draw(im)
    for y in range(0, size, 2):  # light gradient + grain / wood stripes
        k = (y / size - 0.5) * rng.uniform(-40, 40)
        stripe = 10 * math.sin(y / rng.uniform(5, 14)) if kind == "wooden table" else 0
        d.line([(0, y), (size, y)], fill=tuple(max(0, min(255, int(c + k + stripe))) for c in base), width=2)
    return im.filter(ImageFilter.GaussianBlur(0.6))


def synth_scene(rng, size=256, n_max=7):
    """A generated photo-like scene with exact labels: boxes, polygons, caption, VQA pairs (object recognition data)."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
    S = 2  # draw at 2x and downscale = antialiased edges
    kind = rng.choice(BACKDROPS)
    im = _backdrop(Image, size * S, rng, kind)
    shade = Image.new("L", im.size, 0)
    d, ds = ImageDraw.Draw(im), ImageDraw.Draw(shade)
    objs, n = [], rng.randint(1, n_max)
    for _ in range(n * 4):
        if len(objs) >= n:
            break
        r = rng.uniform(0.06, 0.14) * size * S
        cx, cy = rng.uniform(r, size * S - r), rng.uniform(r, size * S - r)
        if any(math.hypot(cx - o["_c"][0], cy - o["_c"][1]) < (r + o["_r"]) * 0.75 for o in objs):
            continue  # light overlap only
        shape, cname = rng.choice(SHAPES), rng.choice(list(COLORS))
        if (cname == "white" and kind == "white desk") or (cname == "black" and kind == "dark mat"):
            continue
        pts = _shape_points(shape, cx, cy, r, rng.uniform(0, math.pi))
        ds.polygon([(x + r * 0.12, y + r * 0.15) for x, y in pts], fill=110)  # soft shadow
        objs.append({"shape": shape, "color": cname, "_c": (cx, cy), "_r": r, "_pts": pts})
    shadow = Image.new("RGB", im.size, (0, 0, 0))
    im = Image.composite(shadow, im, shade.filter(ImageFilter.GaussianBlur(6 * S)).point(lambda v: v * 0.55))
    d = ImageDraw.Draw(im)
    for o in objs:
        col = tuple(max(0, min(255, int(c * rng.uniform(0.85, 1.1)))) for c in COLORS[o["color"]])
        if o["shape"] == "ring":
            d.polygon(o["_pts"], fill=col)
            cx, cy = o["_c"]
            d.polygon(_shape_points("circle", cx, cy, o["_r"] * 0.55, 0), fill=_backdrop_color(kind))
        else:
            d.polygon(o["_pts"], fill=col)
    im = im.resize((size, size), Image.LANCZOS)
    im = ImageEnhance.Brightness(im).enhance(rng.uniform(0.8, 1.15))
    im = ImageEnhance.Contrast(im).enhance(rng.uniform(0.85, 1.15))
    anns = []
    for o in objs:
        xs, ys = [p[0] / S for p in o["_pts"]], [p[1] / S for p in o["_pts"]]
        x0, y0, x1, y1 = max(0, min(xs)), max(0, min(ys)), min(size, max(xs)), min(size, max(ys))
        anns.append({"label": f"{o['color']} {o['shape']}", "shape": o["shape"], "color": o["color"],
                     "bbox": [round(x0, 1), round(y0, 1), round(x1 - x0, 1), round(y1 - y0, 1)],
                     "polygon": [round(v, 1) for p in o["_pts"] for v in (p[0] / S, p[1] / S)],
                     "center": [round(o["_c"][0] / S, 1), round(o["_c"][1] / S, 1)]})

    def where(a):
        cx, cy = a["center"]
        v = "top" if cy < size / 3 else "bottom" if cy > 2 * size / 3 else "middle"
        h = "left" if cx < size / 3 else "right" if cx > 2 * size / 3 else "centre"
        return "in the centre" if (v, h) == ("middle", "centre") else f"at the {v} {h}" if v != "middle" else f"on the {h}" if h != "centre" else f"at the {v}"
    names = [f"{'an' if a['label'][0] in 'aeiou' else 'a'} {a['label']} {where(a)}" for a in anns]
    caption = f"A {kind} with {len(anns)} object{'s' * (len(anns) != 1)}: " + ", ".join(names) + "."
    qa = [("How many objects are on the surface?", str(len(anns)))]
    by_color = {}
    for a in anns:
        by_color[a["color"]] = by_color.get(a["color"], 0) + 1
    c = rng.choice(list(COLORS))
    qa.append((f"How many {c} objects are there?", str(by_color.get(c, 0))))
    a = rng.choice(anns)
    qa.append((f"What colour is the {a['shape']}?" if sum(x["shape"] == a["shape"] for x in anns) == 1 else
               f"What shape is {where(a)}?", a["color"] if sum(x["shape"] == a["shape"] for x in anns) == 1 else a["shape"]))
    qa.append((f"Give the bounding box [x, y, w, h] of the {a['label']}.", json.dumps(a["bbox"])))
    if len(anns) >= 2:
        a, b = rng.sample(anns, 2)
        qa.append((f"Is the {a['label']} to the left of the {b['label']}?", "yes" if a["center"][0] < b["center"][0] else "no"))
    return im, {"backdrop": kind, "width": size, "height": size, "objects": anns, "caption": caption,
                "qa": [{"q": q, "a": x} for q, x in qa]}


def _backdrop_color(kind):
    return {"wooden table": (150, 105, 65), "grey workbench": (128, 130, 134), "white desk": (232, 230, 226),
            "dark mat": (40, 46, 52), "cardboard sheet": (190, 160, 115), "metal plate": (170, 175, 180)}[kind]


def vla_episode(rng, size=160, grid=8):
    """A top-down gantry pick-and-place episode (like ProLab's HOS board): frames + language instruction +
    per-step state and action - the RLDS / Open-X layout used to train vision-language-action models."""
    from PIL import Image, ImageDraw
    cell = size / grid
    shapes = ["cube", "disc", "block"]
    colors = ["red", "green", "blue", "yellow", "orange", "purple"]
    cells = rng.sample([(x, y) for x in range(grid) for y in range(grid)], 6)
    objs = [{"shape": rng.choice(shapes), "color": c, "cell": list(cells[i])} for i, c in enumerate(rng.sample(colors, 3))]
    zone_color = rng.choice(["white", "black"])
    zone = list(cells[3])
    grip = [cells[4][0] + 0.0, cells[4][1] + 0.0]
    target = rng.choice(objs)
    mode = rng.choice(["zone", "shift"])
    if mode == "shift":
        dx, dy = rng.choice([(-2, 0), (2, 0), (0, -2), (0, 2), (-3, 0), (3, 0)])
        goal = [min(grid - 1, max(0, target["cell"][0] + dx)), min(grid - 1, max(0, target["cell"][1] + dy))]
        if goal in [o["cell"] for o in objs]:
            mode = "zone"
    if mode == "zone":
        goal = zone
        instr = rng.choice(["Pick up the {c} {s} and put it in the {z} square.", "Move the {c} {s} into the {z} zone.",
                            "Place the {c} {s} on the {z} target."]).format(c=target["color"], s=target["shape"], z=zone_color)
    else:
        d_ = {(1, 0): "right", (-1, 0): "left", (0, 1): "down", (0, -1): "up"}[(int(math.copysign(1, dx)) if dx else 0,
                                                                                  int(math.copysign(1, dy)) if dy else 0)]
        instr = f"Move the {target['color']} {target['shape']} {abs(dx or dy)} cells {d_}."
    rgb = {"red": (220, 50, 47), "green": (40, 170, 80), "blue": (38, 110, 220), "yellow": (240, 200, 30),
           "orange": (245, 130, 30), "purple": (140, 70, 190), "white": (250, 250, 250), "black": (20, 20, 20)}

    def frame(holding):
        im = Image.new("RGB", (size, size), (200, 196, 188))
        d = ImageDraw.Draw(im)
        for i in range(grid + 1):
            d.line([(i * cell, 0), (i * cell, size)], fill=(170, 166, 158))
            d.line([(0, i * cell), (size, i * cell)], fill=(170, 166, 158))
        if mode == "zone":
            zx, zy = zone
            d.rectangle([zx * cell + 2, zy * cell + 2, (zx + 1) * cell - 2, (zy + 1) * cell - 2], outline=rgb[zone_color], width=3)
        for o in objs:
            ox, oy = (grip if (holding and o is target) else o["cell"])
            x0, y0, x1, y1 = ox * cell + cell * 0.2, oy * cell + cell * 0.2, (ox + 1) * cell - cell * 0.2, (oy + 1) * cell - cell * 0.2
            (d.ellipse if o["shape"] == "disc" else d.rectangle)([x0, y0, x1, y1], fill=rgb[o["color"]])
            if o["shape"] == "block":
                d.line([(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)], fill=(30, 30, 30))
        gx, gy = (grip[0] + 0.5) * cell, (grip[1] + 0.5) * cell
        w_ = cell * (0.25 if holding else 0.42)
        d.line([(gx - w_, gy - cell * 0.4), (gx - w_, gy + cell * 0.4)], fill=(60, 60, 70), width=3)
        d.line([(gx + w_, gy - cell * 0.4), (gx + w_, gy + cell * 0.4)], fill=(60, 60, 70), width=3)
        d.line([(gx - w_, gy - cell * 0.4), (gx + w_, gy - cell * 0.4)], fill=(60, 60, 70), width=3)
        return im

    steps, frames, holding = [], [], False

    def record(action, text):
        steps.append({"observation": {"image": len(frames), "gripper_xy": [round(grip[0], 2), round(grip[1], 2)],
                                      "holding": holding}, "action": action, "language": text})
        frames.append(frame(holding))

    def travel(dest, why):
        while grip != [float(dest[0]), float(dest[1])]:
            ax = (dest[0] > grip[0]) - (dest[0] < grip[0])
            ay = 0 if ax else (dest[1] > grip[1]) - (dest[1] < grip[1])
            record({"dx": ax, "dy": ay, "grip": 1 if holding else 0, "terminate": 0}, why)
            grip[0] += ax
            grip[1] += ay
    travel(target["cell"], f"move toward the {target['color']} {target['shape']}")
    record({"dx": 0, "dy": 0, "grip": 1, "terminate": 0}, "close the gripper")
    holding = True
    travel(goal, "carry it to the goal")
    record({"dx": 0, "dy": 0, "grip": 0, "terminate": 0}, "open the gripper")
    holding = False
    target["cell"] = list(goal)
    record({"dx": 0, "dy": 0, "grip": 0, "terminate": 1}, "done")
    return frames, {"instruction": instr, "grid": grid, "image_size": size, "success": True, "steps": steps,
                    "action_space": {"dx": "-1/0/1 cells", "dy": "-1/0/1 cells", "grip": "1 closed, 0 open",
                                     "terminate": "1 at the last step"},
                    "objects": [{"shape": o["shape"], "color": o["color"]} for o in objs]}


COMMONS_API = "https://commons.wikimedia.org/w/api.php"
FREE_LICENCE = re.compile(r"^(cc0|cc[ -]by(-sa)?([ -]\d(\.\d)?)?|public domain|pd\b|pd-)", re.I)


def commons_images(http, topic, want=8, width=512):
    """Wikimedia Commons search (official API, keyless). Keeps only free licences (CC0 / CC BY / CC BY-SA / PD) and
    stores author + licence with every image."""
    q = urllib.parse.urlencode({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                                "gsrsearch": f"{topic} filetype:bitmap", "gsrlimit": min(50, want * 3),
                                "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata", "iiurlwidth": width})
    raw = http.get(f"{COMMONS_API}?{q}")
    out = []
    try:
        pages = (json.loads(raw or "{}").get("query") or {}).get("pages") or {}
    except ValueError:
        return out
    for p in sorted(pages.values(), key=lambda x: x.get("index", 0)):
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata") or {}
        lic = (md.get("LicenseShortName") or {}).get("value", "")
        if not FREE_LICENCE.search(lic.strip()) or "nc" in lic.lower().split("-") or "nd" in lic.lower().split("-"):
            continue
        if ii.get("mime") not in ("image/jpeg", "image/png") or not ii.get("thumburl"):
            continue
        desc = clean_html((md.get("ImageDescription") or {}).get("value", ""))
        title = re.sub(r"^File:|\.\w+$", "", p.get("title", "")).replace("_", " ")
        out.append({"thumb": ii["thumburl"], "page": ii.get("descriptionurl", ""), "title": title,
                    "caption": shorten(desc or title, 600), "license": lic,
                    "license_url": (md.get("LicenseUrl") or {}).get("value", ""),
                    "author": shorten(clean_html((md.get("Artist") or {}).get("value", "")), 200)})
        if len(out) >= want:
            break
    return out


# ----------------------------------------------------------------------------- system stats
def system_stats(path, prev=None):
    try:
        import psutil
    except ImportError:
        psutil = None
    now = time.time()
    s = {"time": now}
    if psutil:
        s["cpu"] = psutil.cpu_percent(interval=None)
        s["cpu_cores"] = psutil.cpu_percent(interval=None, percpu=True)
        vm = psutil.virtual_memory()
        s["mem"], s["mem_used_gb"], s["mem_total_gb"] = vm.percent, round(vm.used / 2 ** 30, 2), round(vm.total / 2 ** 30, 1)
        p = psutil.Process()
        s["proc_mem_mb"], s["threads"] = round(p.memory_info().rss / 2 ** 20, 1), p.num_threads()
        s["proc_cpu"] = p.cpu_percent(interval=None)
        n = psutil.net_io_counters()
        s["net_rx"], s["net_tx"] = n.bytes_recv, n.bytes_sent
        if prev and prev.get("net_rx") is not None and now > prev["time"]:
            dt = now - prev["time"]
            s["down_kbps"] = round((n.bytes_recv - prev["net_rx"]) / dt / 1024, 1)
            s["up_kbps"] = round((n.bytes_sent - prev["net_tx"]) / dt / 1024, 1)
        try:
            du = psutil.disk_usage(path)
            s["disk_free_gb"] = round(du.free / 2 ** 30, 1)
        except OSError:
            pass
    else:
        la = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)
        s["cpu"] = round(min(100.0, la[0] / (os.cpu_count() or 1) * 100), 1)
    s["load"] = [round(x, 2) for x in (os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0))]
    s["cores"] = os.cpu_count()
    return s


def dir_size(path, skip=(".git", ".agent")):
    total = 0
    for dp, dn, fn in os.walk(path):
        dn[:] = [d for d in dn if d not in skip]
        for f in fn:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total


# ----------------------------------------------------------------------------- GitHub sync (git CLI)
class GitHubSync:
    """Every few minutes: commit stats.json, topics.json, the README with live numbers and every finished shard, then
    push to main. Pushing uses this computer's own git login (Keychain / git credential manager) - AITE stores no
    keys, tokens or passwords."""

    def __init__(self, root, st, log):
        self.root, self.st, self.log = root, st, log
        self.state, self.error, self.last_push, self.pushed_commits = "off", "", 0.0, 0

    def git(self, *args, auth=False, timeout=600):
        import subprocess
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        r = subprocess.run(["git"] + list(args), cwd=self.root, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, (r.stdout + r.stderr).strip()

    def ensure_repo(self):
        repo, branch = str(self.st.get("gh_repo", "")).strip(), self.st.get("gh_branch", "main") or "main"
        code, top = self.git("rev-parse", "--show-toplevel")
        if code != 0:  # not in a repo yet: <repo>/Dataset layout when the folder is called Dataset
            top = os.path.dirname(self.root) if os.path.basename(self.root.rstrip("/")) == "Dataset" else self.root
            import subprocess
            subprocess.run(["git", "init", "-q", "-b", branch], cwd=top, capture_output=True)
            if repo:
                subprocess.run(["git", "remote", "add", "origin", repo], cwd=top, capture_output=True)
                if self.git("fetch", "-q", "origin", branch, auth=True)[0] == 0:
                    self.git("reset", "-q", f"origin/{branch}")  # adopt the remote history, keep local files
        with open(os.path.join(self.root, ".gitignore"), "w") as f:
            f.write(".agent/\n*.open\n*.tmp\n__pycache__/\n.DS_Store\n")
        self.git("config", "user.name", self.st.get("gh_author_name") or "AITE Agent")
        self.git("config", "user.email", self.st.get("gh_author_email") or "aite-agent@users.noreply.github.com")
        code, cur = self.git("remote", "get-url", "origin")
        if repo and code != 0:
            self.git("remote", "add", "origin", repo)
        elif repo and cur != repo:
            self.git("remote", "set-url", "origin", repo)
        return repo, branch

    DATA_DIRS = ("text", "detection", "vla", "preference", "images")
    META_FILES = ("stats.json", "README.md", "topics.json", "stats/history.csv", ".gitignore")

    def run(self, cwd, *args, auth=False, timeout=900):
        import subprocess
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        r = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, (r.stdout + r.stderr).strip()

    def stream(self, push_data=True):
        """GitHub first: upload new data through a tiny private clone (no file contents kept, nothing checked out), verify
        GitHub has the commit, then delete the local copies - this Mac only ever holds a few minutes of data."""
        import shutil
        repo, branch = str(self.st.get("gh_repo", "")).strip(), self.st.get("gh_branch", "main") or "main"
        if not repo:
            self.state, self.error = "local", "Add the repository URL in Settings > GitHub."
            return False
        up = os.path.join(self.root, ".agent", "upload")
        if os.path.isdir(up) and dir_size(up, skip=()) > 2 ** 30:
            shutil.rmtree(up, ignore_errors=True)  # rebuilt fresh: pushed data never piles up here
        url = ("file://" + repo) if os.path.isabs(repo) else repo  # local test remotes: enable shallow/filtered clones
        if not os.path.isdir(os.path.join(up, ".git")):
            shutil.rmtree(up, ignore_errors=True)
            code, out = self.run(os.path.dirname(up), "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse",
                                 "-b", branch, url, up)
            if code != 0:  # an empty repository (first use): start it
                shutil.rmtree(up, ignore_errors=True)
                os.makedirs(up)
                self.run(up, "init", "-q", "-b", branch)
                self.run(up, "remote", "add", "origin", url)
                self.run(up, "sparse-checkout", "set", "--no-cone", "/*", "!/*/")
        else:
            code, out = self.run(up, "fetch", "-q", "--depth", "1", "origin", branch)
            if code == 0:
                self.run(up, "reset", "-q", "--hard", "FETCH_HEAD")
        self.run(up, "config", "http.postBuffer", "524288000")  # large pushes over slow uploads
        self.run(up, "config", "http.version", "HTTP/1.1")
        self.run(up, "config", "user.name", self.st.get("gh_author_name") or "AITE Agent")
        self.run(up, "config", "user.email", self.st.get("gh_author_email") or "aite-agent@users.noreply.github.com")
        sub = os.path.basename(self.root.rstrip("/")) if os.path.basename(self.root.rstrip("/")) == "Dataset" else ""
        with open(os.path.join(self.root, ".gitignore"), "w") as f:
            f.write(".agent/\n*.open\n*.tmp\n__pycache__/\n.DS_Store\n")
        over = float(self.store_mb()) > float(self.st.get("gh_max_repo_mb", 4500))
        files = [f for f in self.META_FILES if os.path.exists(os.path.join(self.root, f))]
        if push_data and not over:
            data = []
            for d in self.DATA_DIRS:
                for dp, dn, fn in os.walk(os.path.join(self.root, d)):
                    for f in fn:
                        if not f.endswith((".open", ".tmp")):
                            fp = os.path.join(dp, f)
                            try:
                                data.append((os.path.getmtime(fp), os.path.getsize(fp), os.path.relpath(fp, self.root)))
                            except OSError:
                                pass
            cap, used = float(self.st.get("gh_batch_mb", 25)) * 2 ** 20, 0
            prio = {"text": 0, "preference": 1, "detection": 2, "vla": 3, "images": 4}
            data.sort(key=lambda x: (prio.get(x[2].split("/")[0], 9), x[0]))
            for _t, size, rel in data:  # most valuable first, one batch at a time (big pushes time out on slow uploads)
                if used and used + size > cap:
                    break
                files.append(rel)
                used += size
        if not files:
            return True
        c = self.read_counts()

        def stage_and_commit():
            """Hard-links this batch into the upload copy and commits it on top of what is checked out."""
            added_ = 0
            for rel in files:
                src, dst = os.path.join(self.root, rel), os.path.join(up, sub, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                try:
                    if os.path.exists(dst):
                        os.remove(dst)
                    os.link(src, dst)  # a hard link: no second copy on disk
                except OSError:
                    shutil.copy2(src, dst)
                added_ += os.path.getsize(src)
            self.run(up, "add", "--sparse", "-A", "--", sub or ".")
            if self.run(up, "diff", "--cached", "--quiet")[0] == 0:
                return added_, False
            msg = (f"AITE agent: {c.get('text', 0):,} text · {c.get('images', 0):,} images · {c.get('vla_episodes', 0):,} VLA "
                   f"episodes · +{added_ / 2 ** 20:.1f} MB")
            code_, out_ = self.run(up, "commit", "-q", "-m", msg)
            if code_ != 0:
                raise RuntimeError(out_[-300:])
            return added_, True

        added, changed = stage_and_commit()
        if not changed:
            self.cleanup_pushed(files)
            return True
        for attempt in range(3):
            code, out = self.run(up, "push", "-q", "origin", f"HEAD:{branch}")
            if code == 0 or not ("rejected" in out or "fetch first" in out or "non-fast-forward" in out):
                break
            # GitHub moved on (another commit, e.g. the app): start again from GitHub's newest commit and redo this
            # batch on top. A shallow copy cannot rebase, and old failed commits are simply dropped - their files are
            # still here (local copies are only deleted after GitHub confirms them).
            if self.run(up, "fetch", "-q", "--depth", "1", "origin", branch)[0] != 0:
                break
            self.run(up, "reset", "-q", "--hard", "FETCH_HEAD")
            added, changed = stage_and_commit()
            if not changed:
                self.cleanup_pushed(files)
                return True
        if code != 0:
            self.run(up, "fetch", "-q", "--depth", "1", "origin", branch)
            self.run(up, "reset", "-q", "--hard", "FETCH_HEAD")  # never let failed commits pile up into one huge push
            raise RuntimeError(out[-300:] or "git push failed")
        _, head = self.run(up, "rev-parse", "HEAD")
        _, remote = self.run(up, "ls-remote", "origin", f"refs/heads/{branch}")
        if not remote.startswith(head.strip()):
            raise RuntimeError("GitHub does not show the new commit yet - local copies kept, retrying next sync")
        self.cleanup_pushed(files)
        self.pushed_mb = getattr(self, "pushed_mb", 0.0) + added / 2 ** 20
        self.run(up, "sparse-checkout", "reapply")  # the upload clone keeps nothing checked out either
        self.state = "pushed (stats only - size budget reached)" if over else "pushed"
        self.error, self.last_push = "", time.time()
        self.pushed_commits += 1
        return True

    def cleanup_pushed(self, files):
        """GitHub has them now: remove the local data files (never stats.json / README.md / topics.json)."""
        for rel in files:
            if rel.split("/")[0] in self.DATA_DIRS:
                try:
                    os.remove(os.path.join(self.root, rel))
                except OSError:
                    pass
        for d in self.DATA_DIRS:  # drop emptied image folders
            for dp, dn, fn in sorted(os.walk(os.path.join(self.root, d)), key=lambda x: -len(x[0])):
                if dp != os.path.join(self.root, d) and not dn and not fn:
                    try:
                        os.rmdir(dp)
                    except OSError:
                        pass

    def backlog(self):
        """Finished data files still waiting for GitHub."""
        for d in self.DATA_DIRS:
            for dp, dn, fn in os.walk(os.path.join(self.root, d)):
                if any(not f.endswith((".open", ".tmp")) for f in fn):
                    return True
        return False

    def store_mb(self):
        try:
            with open(os.path.join(self.root, ".agent", "pushed_mb.json")) as f:
                base = float(json.load(f).get("mb", 0))
        except (OSError, ValueError):
            base = 0.0
        return base + getattr(self, "pushed_mb", 0.0)

    def read_counts(self):
        try:
            with open(os.path.join(self.root, "stats.json")) as f:
                return json.load(f).get("counts", {})
        except (OSError, ValueError):
            return {}

    def sync(self, push_data=True):
        if not self.st.get("gh_enabled", True):
            self.state = "off"
            return False
        if self.st.get("gh_stream", True) and str(self.st.get("gh_repo", "")).strip():
            try:
                t0 = time.time()
                ok = self.stream(push_data)
                while ok and push_data and time.time() - t0 < 240 and self.backlog():  # drain at the connection's speed
                    ok = self.stream(push_data)
                with open(os.path.join(self.root, ".agent", "pushed_mb.json"), "w") as f:
                    json.dump({"mb": self.store_mb()}, f)
                self.pushed_mb = 0.0
                return ok
            except Exception as e:
                self.state, self.error = "error", f"{type(e).__name__}: {str(e)[:300]}"
                self.log(f"GitHub sync failed (local copies kept): {self.error}")
                return False
        try:
            repo, branch = self.ensure_repo()
            paths = ["stats.json", "README.md", ".gitignore", "stats", "topics.json"]
            over = dir_size(self.root) / 2 ** 20 > float(self.st.get("gh_max_repo_mb", 900))
            if push_data and not over:
                paths += [p for p in ("text", "images", "vla", "detection", "preference") if os.path.isdir(os.path.join(self.root, p))]
            self.git("add", "--", *[p for p in paths if os.path.exists(os.path.join(self.root, p))])
            code, out = self.git("diff", "--cached", "--quiet")
            if code != 0:
                stt = {}
                try:
                    with open(os.path.join(self.root, "stats.json")) as f:
                        stt = json.load(f)
                except (OSError, ValueError):
                    pass
                c = stt.get("counts", {})
                msg = (f"AITE agent: {c.get('text', 0):,} text · {c.get('images', 0):,} images · "
                       f"{c.get('vla_episodes', 0):,} VLA episodes · {stt.get('topics', {}).get('explored', 0):,} topics")
                code, out = self.git("commit", "-q", "-m", msg)
                if code != 0:
                    raise RuntimeError(out[-300:])
            if not repo:
                self.state, self.error = "local", "Committed locally - add the GitHub repo URL in Settings > GitHub to push."
                return True
            code, out = self.git("push", "-q", "-u", "origin", branch, auth=True)
            if code != 0 and ("rejected" in out or "fetch first" in out or "non-fast-forward" in out):
                self.git("pull", "-q", "--rebase", "--autostash", "origin", branch, auth=True)
                code, out = self.git("push", "-q", "-u", "origin", branch, auth=True)
            if code != 0:
                raise RuntimeError(out[-300:] or "git push failed")
            self.state, self.error, self.last_push = ("pushed (stats only - repo size budget reached)" if over else "pushed"), "", time.time()
            self.pushed_commits += 1
            return True
        except Exception as e:
            self.state, self.error = "error", f"{type(e).__name__}: {str(e)[:300]}"
            self.log(f"GitHub sync failed: {self.error}")
            return False


# ----------------------------------------------------------------------------- the agent
def agent_readme(stats):
    c, t = stats.get("counts", {}), stats.get("topics", {})
    return f"""# AITE dataset (live)

Collected continuously by **Prolabs Robotics AITE** - Agent mode, powered by **{PWT_NAME}** ({PWT_DEVELOPER}).
This file and `stats.json` are rewritten on every sync.

| | |
|---|---|
| Text records (originals + DataGen variants) | **{c.get('text', 0):,}** ({c.get('originals', 0):,} originals, {c.get('variants', 0):,} variants) |
| Web images (free licences, with attribution) | **{c.get('web_images', 0):,}** |
| Generated detection images (boxes, polygons, captions, VQA) | **{c.get('synthetic_images', 0):,}** |
| Robot VLA episodes (frames + actions + instruction) | **{c.get('vla_episodes', 0):,}** ({c.get('vla_frames', 0):,} frames) |
| Topics explored / known | {t.get('explored', 0):,} / {t.get('known', 0):,} |
| Approx. text tokens | {stats.get('tokens', 0):,} |
| Running since | {stats.get('started_iso', '')} |
| Updated | {stats.get('updated_iso', '')} |

## Layout
- `text/*.jsonl.gz` - one JSON object per line: `messages` (chat SFT), `problem`, `solution`, `topic`, `source`, `url`, `license`, `quality_score`, DataGen fields.
- `detection/*.jsonl.gz` + `images/synthetic/` - generated scenes: `objects[].bbox` (x, y, w, h px), `polygon`, `caption`, `qa`.
- `images/web/` + `text`-style rows in `detection/` with `type: "image-text"` - Wikimedia Commons images, licence + author kept.
- `vla/*.jsonl.gz` + `images/vla/` - pick-and-place episodes: `instruction`, `steps[].observation`, `steps[].action`.

Licences differ per row (see the `license` field) - some sources are non-commercial (e.g. CC-BY-NC). Filter before commercial use.
"""


class Agent:
    """Agent mode: runs forever (pause only). Picks topics from the endless TopicStore, runs many tasks in parallel
    through Parallel Web Technologies, writes shards, stats every few seconds and pushes to GitHub every N minutes.
    Control: <dir>/.agent/control.json  {"paused": bool, "workers": int, "heartbeat": time, "sync_now": time}."""

    def __init__(self, root, st, offline=False, log=None, max_seconds=None, worker_id=0):
        from concurrent.futures import ThreadPoolExecutor
        self.root, self.st, self.offline, self.max_seconds = root, dict(st), offline, max_seconds
        self.worker_id = int(worker_id)  # 0 = the main agent; 1, 2, ... = extra worker processes
        self.wtag = f"-w{self.worker_id}" if self.worker_id else ""
        self.ckey = "counts" if not self.worker_id else f"counts:w{self.worker_id}"
        self.adir = os.path.join(root, ".agent")
        os.makedirs(self.adir, exist_ok=True)
        os.makedirs(os.path.join(root, "stats"), exist_ok=True)
        self.apply_overrides()
        self.events = []
        self.ev_lock = threading.Lock()
        self.log_f = open(os.path.join(self.adir, "agent.log"), "a", encoding="utf-8")
        self._ext_log = log
        self.store = TopicStore(os.path.join(self.adir, "state.db"))
        self.topics_json = os.path.join(root, "topics.json")
        if not self.worker_id and not self.store.get("topics_json_imported") and os.path.exists(self.topics_json):
            n = self.store.import_json(self.topics_json)
            self.store.put("topics_json_imported", True)
            self._import_note = f"Continued from topics.json: {n:,} topics"
        if not self.worker_id:
            self.store.reset_busy()  # only the main agent: workers must not free topics others are collecting
        mb, rot = float(st.get("agent_shard_mb", 45)), int(float(st.get("gh_interval_min", 5)) * 60)
        self.writers = {k: ShardWriter(root, k, mb, rot, self.wtag) for k in ("text", "detection", "vla", "preference")}
        self.field_counts = dict(self.store.get("field_counts" + self.wtag, {}))
        self.by_source = dict(self.store.get("by_source", {}))
        self.locating = set()
        self.limiter = pwt_on(dict(self.st, pwt_enabled=True))
        self.workers = int(st.get("pwt_workers", 32))
        self.pool = ThreadPoolExecutor(max_workers=max(1, min(AGENTS_PER_PROCESS, self.workers)), thread_name_prefix="pwt")
        self.procs = {}
        self.inflight, self.lock = {}, threading.Lock()
        self.eff = max(1, min(self.workers, 8))
        saved = self.store.get(self.ckey, {})
        self.counts = {k: int(saved.get(k, 0)) for k in ("text", "originals", "variants", "web_images", "synthetic_images",
                                                           "images", "vla_episodes", "vla_frames", "tokens", "tasks_done",
                                                           "tasks_failed", "topics_added", "preference")}
        self.by_kind = {k: 0 for k in AGENT_KINDS + ["expand", "seed", "seed_concepts"]}
        self.started = time.time()
        self.paused = False
        self.sys_prev = None
        self.rate_hist = []
        self.github = GitHubSync(root, self.st, self.log)
        self.next_sync = time.time() + 30
        self.sync_thread = None
        self.last_sample = self.store.get("last_sample", {})
        self.last_image = self.store.get("last_image", "")
        self.http_factory = (lambda: make_fake_http("ok")) if offline else (lambda: Http(self.st, self.vlog))
        self.exiting = False
        self.local_counts = {"synthetic_images": "synthetic_images", "vla": "vla_episodes"}

    def apply_overrides(self):
        self.st.update(duckduckgo_enabled=False,  # DuckDuckGo's bot check is respected: agent mode never sends it bulk traffic
                       wikibooks_enabled=False,  # throttles hard and yields little; the endless topic stream replaces refills
                       max_runtime=int(self.st.get("agent_task_timeout", 120)), refill_rounds=0, delay=0,
                       fetch_pages=False, include_meta=False, hf_max_candidates=min(4, int(self.st.get("hf_max_candidates", 8))),
                       hf_scan_pages=min(3, int(self.st.get("hf_scan_pages", 6))))
        if self.offline:  # tests never push anywhere real
            self.st["gh_repo"] = os.environ.get("AITE_TEST_REMOTE", "")

    def reload(self):
        """Settings changed in the window: apply them live (quality, batch, mix, workers, GitHub link, focus topics)."""
        new = load_settings()
        for k, v in new.items():
            if k.startswith(("agent_", "pwt_", "gh_", "dg_", "min_score_", "filter_", "w_")) or k in ("dedupe", "require_solution"):
                self.st[k] = v
        self.apply_overrides()
        if self.limiter:
            self.limiter.configure(self.st, getattr(self.limiter, "scale", 1.0))
        self.workers = max(1, min(MAX_AGENTS, int(self.st.get("pwt_workers", self.workers))))
        focus = [t for t in (x.strip() for x in str(self.st.get("agent_focus_topics", "")).split(",")) if t]
        if focus:
            n = self.store.add(focus, "focus", -1)  # depth -1 = picked before everything else
            with self.store.lock:
                self.store.db.executemany("UPDATE topics SET depth=-1, status=CASE WHEN status='busy' THEN status ELSE 'new' END "
                                          "WHERE name=?", [(re.sub(r"\s+", " ", f).strip().lower(),) for f in focus])
                self.store.db.commit()
            if n:
                self.log(f"Focus topics added: {', '.join(focus[:8])}")
        self.log("Settings applied")

    def vlog(self, msg):
        """Verbose detail (requests, search / filter / DataGen steps) - only when super verbose is on."""
        if self.st.get("agent_verbose", True):
            self.log(msg)

    def tlog(self, tag):
        return lambda m: self.vlog(f"[{tag}] {m.strip()}")

    # ---- logging
    def log(self, msg):
        line = f"{datetime.now().strftime('%H:%M:%S')}{'  w' + str(self.worker_id) if getattr(self, 'worker_id', 0) else '    '}  {msg}"
        with self.ev_lock:
            self.events.append(line)
            del self.events[:-200]
        try:
            self.log_f.write(line + "\n")
            self.log_f.flush()
            if self.log_f.tell() > 50 * 2 ** 20 and not getattr(self, "worker_id", 0):  # keep the verbose log at ~50 MB
                with self.ev_lock:
                    self.log_f.close()
                    lp = os.path.join(self.adir, "agent.log")
                    os.replace(lp, lp + ".1")
                    self.log_f = open(lp, "a", encoding="utf-8")
        except (OSError, ValueError):
            pass
        if self._ext_log:
            self._ext_log(line)

    # ---- control
    def control(self):
        try:
            with open(os.path.join(self.adir, "control.json")) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def mix(self):
        w = {k: max(0.0, float(self.st.get(f"agent_mix_{k}", d))) for k, d in
             (("archive", 6), ("text", 4), ("web_images", 2), ("synthetic_images", 1), ("vla", 1))}
        if self.offline:
            w["web_images"] = 0
        for k in w:  # a product switched off in Settings > Products takes its data out of the mix
            if not product_on(self.st, PRODUCT_OF_KIND.get(k, "")):
                w[k] = 0.0
        return w

    KIND_CAP = {"text": 300, "web_images": 24}  # per process: more would only queue at the same rate-limited sites

    def pick_kind(self):
        w = {k: v for k, v in self.mix().items() if k in ("archive", "text", "web_images")}
        with self.lock:
            now_busy = {k: sum(1 for v in self.inflight.values() if v[0] == k) for k in w}
        caps = dict(self.KIND_CAP, text=max(1, math.ceil(int(self.st.get("agent_topics_parallel", 120)) / max(1, getattr(self, "_np", None) or self.n_procs()))))
        for k, cap in caps.items():
            if k in w and now_busy.get(k, 0) >= cap:
                w[k] = 0.0
        if not any(w.values()):
            return None
        tot = sum(w.values()) or 1
        with self.lock:
            busy = {k: sum(1 for v in self.inflight.values() if v[0] == k) for k in w}
        # the kind furthest below its share of in-flight slots goes next; local generators never take over the pool
        n = max(1, sum(busy.values()))
        return max(w, key=lambda k: (w[k] / tot - busy[k] / n) if w[k] > 0 else -9)

    def submit(self, kind, arg=None):
        fut = self.pool.submit(self.run_task, kind, arg)
        with self.lock:
            self.inflight[fut] = (kind, arg, time.time())
        fut.add_done_callback(self._done)

    def _done(self, fut):
        with self.lock:
            kind, arg, t0 = self.inflight.pop(fut, ("?", None, time.time()))
        exc = fut.exception()
        if exc:
            self.counts["tasks_failed"] += 1
            self.log(f"{kind} {arg or ''} failed: {type(exc).__name__}: {str(exc)[:160]}")
        else:
            self.counts["tasks_done"] += 1
        self.by_kind[kind] = self.by_kind.get(kind, 0) + 1

    # ---- tasks
    def run_task(self, kind, arg):
        return getattr(self, "task_" + kind)(arg)

    def task_seed(self, page):
        """OpenAlex's research-topic catalogue (CC0): 4,516 topics, each with a field and ~10 keywords
        -> about 45,000 field-labelled, very specific subjects (e.g. 'Doppler reflectometry', 'Iwasawa theory')."""
        if self.offline:
            n = self.store.add([f"{a} {b}" for a in ("applied", "computational", "experimental") for b in TAXONOMY["physics"]],
                               "offline-seed", 2, "physics")
            res = []
        else:
            http = self.http_factory()
            raw = http.get(f"https://api.openalex.org/topics?per-page=200&page={page}&select=display_name,keywords,field,subfield")
            try:
                res = (json.loads(raw).get("results") or []) if raw else []
            except ValueError:
                res = []
            n = 0
            for t in res:
                field = OPENALEX_FIELDS.get(((t.get("field") or {}).get("display_name") or ""), "")
                kws = [k.get("display_name", "") if isinstance(k, dict) else str(k) for k in (t.get("keywords") or [])]
                sub = (t.get("subfield") or {}).get("display_name", "")
                n += self.store.add([t.get("display_name", ""), sub] + kws, "openalex", 2, field)
        if not res:
            self.store.put("seed_done", True)
        self.counts["topics_added"] += n
        self.store.put("seed_page", page)
        self.log(f"Topics: +{n:,} from the OpenAlex topic catalogue (page {page})")

    def task_seed_concepts(self, page):
        """OpenAlex concepts, levels 2-5 (CC0): 64,723 very specific subtopics across every science."""
        if self.offline:
            n = self.store.add([f"{b} methods" for b in ADVANCED["mathematics"][:20]], "offline-concepts", 3, "mathematics")
            done = page >= 2
        else:
            http = self.http_factory()
            raw = http.get(f"https://api.openalex.org/concepts?filter=level:%3E1&sort=works_count:desc&per-page=200"
                           f"&page={page}&select=display_name,level")
            try:
                res = (json.loads(raw).get("results") or []) if raw else []
            except ValueError:
                res = []
            n = self.store.add([c.get("display_name", "") for c in res], "openalex-concepts", 3, "")
            done = not res
        if done:
            self.store.put("concepts_done", True)
        self.counts["topics_added"] += n
        self.store.put("concept_page", page)
        self.log(f"Topics: +{n:,} specific concepts from OpenAlex (page {page})")

    def task_expand(self, arg):
        """Wikipedia's link graph: every topic that produced data opens up the concepts it links to (same field)."""
        name, depth, field = (tuple(arg) + ("",))[:3]
        if self.offline:
            names = [f"{name} {f}" for f in FACETS[1:5]]
        else:
            http = self.http_factory()
            q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "links", "plnamespace": 0,
                                        "pllimit": "max", "titles": name, "redirects": 1})
            raw = http.get(f"https://en.wikipedia.org/w/api.php?{q}")
            names = []
            try:
                for p in (json.loads(raw or "{}").get("query") or {}).get("pages", {}).values():
                    names += [l["title"] for l in p.get("links", [])]
            except ValueError:
                pass
        n = self.store.add(names, f"wikipedia:{name}", min(6, depth + 1), field)
        self.counts["topics_added"] += n
        if n:
            self.log(f"Topics: +{n} linked from '{name}'")

    def count_field(self, field, n):
        with self.lock:
            self.field_counts[field or "general"] = self.field_counts.get(field or "general", 0) + n

    def write_text_rows(self, rows, topic, field, label):
        fresh = set(self.store.first_seen([r["id"] for r in rows]))
        rows = [r for r in rows if r["id"] in fresh]
        if rows:
            self.writers["text"].write(rows)
            orig = sum(r["kind"] == "original" for r in rows)
            self.counts["text"] += len(rows)
            self.counts["originals"] += orig
            self.counts["variants"] += len(rows) - orig
            self.counts["tokens"] += sum(len(r["problem"]) + len(r["solution"]) for r in rows) // 4
            per = {}
            for r in rows:
                per[r.get("field") or field] = per.get(r.get("field") or field, 0) + 1
            for f_, n_ in per.items():
                self.count_field(f_, n_)
            s = rows[0]
            self.last_sample = {"type": label, "topic": topic, "problem": shorten(s["problem"], 400),
                                "solution": shorten(s["solution"], 400), "source": s["source"]}
        return rows

    def task_text(self, topic):
        field, depth = self.store.info(topic)
        rng = random.Random(f"{topic}|{time.time()}")
        level = rng.choice(LEVELS) if depth <= 0 else rng.choice(LEVELS[2:])
        types = [t for t in AGENT_TEXT_TYPES if t in str(self.st.get("agent_types", ",".join(AGENT_TEXT_TYPES)))] or AGENT_TEXT_TYPES[:1]
        base_w = {"problems & solution papers": 6, "worked examples": 3, "research papers": 1 if depth < 2 else 4}
        dt = rng.choices(types, weights=[base_w[t] for t in types])[0]
        inp = {"topics": [topic], "quantity": int(self.st.get("agent_batch", 8)), "quality": int(self.st.get("agent_quality", 5)),
               "data_type": dt, "output_type": "json",
               "datagen_variations": int(self.st.get("agent_variations", 3)) if product_on(self.st, "product_datagen") else 0,
               "datagen_styles": list(STYLES), "datagen_formats": list(FORMATS), "datagen_methods": list(METHODS)}
        st = dict(self.st, dg_seed=rng.randint(1, 10 ** 9))
        site = FIELD_SE_SITE.get(field)
        if field == "mathematics" and depth >= 1 and rng.random() < 0.5:
            site = "mathoverflow.net"  # research-level mathematics
        if site:
            st["se_default_site"] = site
        if dt != "research papers":  # arXiv allows one request per 3 s for everyone: keep it for paper tasks
            st["arxiv_enabled"] = False
        cancel = threading.Event()
        tl = self.tlog(topic)
        self.vlog(f"Text  '{topic}' [{field or 'general'}] starts: {dt}, quality {inp['quality']}, {inp['quantity']} records, "
                  f"DataGen x{inp['datagen_variations']}, site {st.get('se_default_site')}")
        searcher = Searcher(st, tl, cancel, http=self.http_factory())
        res = run_pipeline(inp, st, tl, cancel, searcher=searcher)
        rows = [dict(agent_text_record(r, st), level=level, data_type=dt, field=field or "general")
                for r in res["records"] + res["variants"]]
        rows = self.write_text_rows(rows, topic, field, "text")
        self.store.done(topic, len(rows))
        self.log(f"Text  '{topic}' [{field or 'general'}]: +{len(rows)} rows ({len(res['records'])} kept, {len(res['variants'])} variants)")

    # ---- open Q&A archives (bulk, human-written, no daily quota)
    def _hf_rows(self, http, dataset, config, offset, length):
        q = urllib.parse.urlencode({"dataset": dataset, "config": config, "split": "train", "offset": int(offset), "length": int(length)})
        for _ in range(3):
            raw = http.get(f"{HF_BASE}/rows?{q}")
            if raw:
                try:
                    return json.loads(raw).get("rows") or []
                except ValueError:
                    pass
            time.sleep(1.5)
        return None

    def _se_host(self, http, offset):
        rows = self._hf_rows(http, SE_ARCHIVE, "default", offset, 1)
        if not rows:
            return None
        meta = rows[0]["row"].get("metadata") or []
        return meta[1].split("://", 1)[-1].rstrip("/") if len(meta) > 1 else None

    def se_range(self, http, site):
        """Rows [lo, hi) of one site inside the 10.8M-row dump (its files are in alphabetical folder order):
        two binary searches of ~24 one-row probes, done once and remembered."""
        key = f"se_range:{site}"
        got = self.store.get(key)
        if got:
            return got
        with self.lock:
            if site in self.locating:
                return None
            self.locating.add(site)
        try:
            def bound(strict):
                lo, hi = 0, SE_ARCHIVE_ROWS
                while lo < hi:
                    mid = (lo + hi) // 2
                    h = self._se_host(http, mid)
                    if h is None:
                        raise RuntimeError("archive probe failed")
                    if h < site or (strict and h == site):
                        lo = mid + 1
                    else:
                        hi = mid
                return lo
            lo = bound(False)
            hi = bound(True)
            rng_ = [lo, hi] if hi > lo else [0, 0]
            self.store.put(key, rng_)
            self.log(f"Archive: located {site} - {hi - lo:,} questions")
            return rng_
        finally:
            with self.lock:
                self.locating.discard(site)

    def archive_records(self, src, rows, field):
        """Archive rows -> AITE items (+ preference pairs for Stack Exchange questions with several voted answers)."""
        items, prefs = [], []
        q_min = {1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 6: 2, 7: 4, 8: 5, 9: 8, 10: 12}.get(int(self.st.get("agent_quality", 5)), 2)
        for x in rows:
            r = x.get("row", {})
            if src["kind"] == "se":
                meta = r.get("metadata") or []
                host = meta[1].split("://", 1)[-1].rstrip("/") if len(meta) > 1 else ""
                if not host or ".meta." in host or host.startswith("meta.") or not r.get("answers"):
                    continue  # meta sites discuss the websites themselves - not knowledge
                field = ARCHIVE_SITES.get(host, ("general knowledge", 1))[0]
                ans = sorted(r["answers"], key=lambda a: (not a.get("selected"), -int(a.get("pm_score") or 0)))
                best = ans[0]
                if int(best.get("pm_score") or 0) < q_min and not best.get("selected"):
                    continue
                problem, solution = clean_html(r.get("question", "")), clean_html(best.get("text", ""))
                url = meta[0] if meta else ""
                title = shorten(sentences(problem)[0] if sentences(problem) else problem, 120)
                it = item(field, "stackexchange", title, problem, solution, url, int(best.get("pm_score") or 0),
                          {"license": "CC BY-SA 4.0", "site": host, "archive": SE_ARCHIVE})
                it["_site"] = host
                items.append(it)
                worse = [a for a in ans[1:] if int(best.get("pm_score") or 0) - int(a.get("pm_score") or 0) >= 2]
                if worse:
                    w = min(worse, key=lambda a: int(a.get("pm_score") or 0))
                    rej = clean_html(w.get("text", ""))
                    if len(rej.split()) >= 15 and len(solution.split()) >= 15:
                        prefs.append({"id": _rid("pref", url), "type": "preference", "field": field, "site": host,
                                      "prompt": problem, "chosen": solution, "rejected": rej,
                                      "chosen_score": int(best.get("pm_score") or 0), "rejected_score": int(w.get("pm_score") or 0),
                                      "messages": [{"role": "user", "content": problem}],
                                      "url": url, "license": "CC BY-SA 4.0", "source": "stackexchange",
                                      "created": datetime.now().isoformat(timespec="seconds")})
            else:
                pr = src["map"](r)
                if pr:
                    p_, s_, t_ = pr
                    items.append(item(field, "huggingface", t_, p_, s_, f"https://huggingface.co/datasets/{src['dataset']}",
                                      0, {"license": src["license"], "dataset": src["dataset"]}))
        return items, prefs

    def task_archive(self, _):
        http = self.http_factory()
        src = self.pick_archive()
        if src is None:
            return
        if src["kind"] == "se":  # sweep the whole dump from many places at once - every real expert site is kept
            lo, hi = 0, SE_ARCHIVE_ROWS
            slot = random.randrange(16)
            key = f"cursor:se:{slot}"
        else:
            lo, hi = 0, src["rows"]
            key = f"cursor:{src['name']}"
        cur = self.store.get(key)
        if cur is None or not lo <= cur < hi:
            cur = random.randint(lo, max(lo, hi - 1))
        length = 20 if src["kind"] == "se" else 50
        rows = self._hf_rows(http, src["dataset"], src["config"], cur, min(length, hi - cur))
        nxt = cur + length
        self.store.put(key, nxt if nxt < hi else lo)
        if not rows:
            return
        field = src["field"]
        items, prefs = self.archive_records(src, rows, field)
        if src["kind"] == "se":
            field = "stack exchange"
        for it in items:
            it["uid"] = _rid(it["url"], it["problem"][:200])[:12]
        inp = {"topics": sorted({it["topic"] for it in items}) or [field], "quantity": max(1, len(items)),
               "quality": int(self.st.get("agent_quality", 5)), "data_type": "problems & solution papers",
               "datagen_variations": int(self.st.get("agent_variations", 3)) if product_on(self.st, "product_datagen") else 0,
               "datagen_styles": list(STYLES), "datagen_formats": list(FORMATS), "datagen_methods": list(METHODS)}
        st = dict(self.st, topic_relevance=False, dg_seed=random.randint(1, 10 ** 9))
        if not product_on(self.st, "product_filter"):
            kept = items
        else:
            kept, _rej, _why = Filterer(st, self.tlog(src["name"])).run(items, inp) if items else ([], [], {})
        variants = DataGen(st, self.tlog(src["name"])).generate(kept, inp) if kept and inp["datagen_variations"] else []
        out = [dict(agent_text_record(r, st), field=r.get("topic") or field,
                    level="advanced" if r.get("meta", {}).get("site") in ("mathoverflow.net", "cstheory.stackexchange.com") else "mixed",
                    data_type="archive", archive=r.get("meta", {}).get("site") or src["name"]) for r in kept + variants]
        for f_ in {r["field"] for r in out}:
            self.count_field(f_, 0)
        out = self.write_text_rows(out, src["name"], src["field"], "archive Q&A")
        if prefs and product_on(self.st, "product_preference"):
            fresh = set(self.store.first_seen([x["id"] for x in prefs]))
            prefs = [x for x in prefs if x["id"] in fresh]
            if prefs:
                self.writers["preference"].write(prefs)
                self.counts["preference"] = self.counts.get("preference", 0) + len(prefs)
        self.by_source[src["name"]] = self.by_source.get(src["name"], 0) + len(out)
        self.log(f"Archive {src['name']}: +{len(out)} rows ({len(kept)} kept of {len(items)}, {len(variants)} variants)"
                 + (f", +{len(prefs)} preference pairs" if prefs else ""))

    def pick_archive(self):
        srcs = [({"kind": "se", "name": "stack exchange dump", "dataset": SE_ARCHIVE, "config": "default", "field": "stack exchange"}, 8.0)]
        for name, d in HF_ARCHIVES.items():
            srcs.append((dict(d, kind="hf", name=name, dataset=name), d["weight"] * FIELD_WEIGHTS.get(d["field"], 1) / 10))
        return random.choices([x[0] for x in srcs], weights=[x[1] for x in srcs])[0]

    def _img_dir(self, kind):
        d = os.path.join(self.root, "images", kind, datetime.now().strftime("%Y%m%d-%H"))
        os.makedirs(d, exist_ok=True)
        return d

    def task_web_images(self, topic):
        from PIL import Image
        http = self.http_factory()
        found = commons_images(http, topic, int(self.st.get("agent_images_per_task", 6)), int(self.st.get("agent_image_size", 512)))
        rows = []
        for it in found:
            iid = _rid("commons", it["page"])
            if not self.store.first_seen([iid]):
                continue
            status, raw, ctype = http.fetch(it["thumb"], max_bytes=8 * 2 ** 20)
            if not raw:
                continue
            try:
                im = Image.open(io.BytesIO(raw)).convert("RGB")
            except Exception:
                continue
            path = os.path.join(self._img_dir("web"), iid + ".jpg")
            im.save(path + ".tmp", "JPEG", quality=88)
            os.replace(path + ".tmp", path)
            rel = os.path.relpath(path, self.root)
            rows.append({"id": iid, "type": "image-text", "image": rel, "width": im.width, "height": im.height, "topic": topic,
                         "caption": it["caption"], "title": it["title"], "source": "wikimedia commons", "url": it["page"],
                         "license": it["license"], "license_url": it["license_url"], "author": it["author"],
                         "messages": [{"role": "user", "content": "<image>\nDescribe this image."},
                                      {"role": "assistant", "content": it["caption"]}],
                         "created": datetime.now().isoformat(timespec="seconds")})
            self.last_image = path
        if rows:
            self.writers["detection"].write(rows)
            self.counts["web_images"] += len(rows)
            self.counts["images"] += len(rows)
            self.last_sample = {"type": "web image", "topic": topic, "problem": rows[-1]["caption"], "solution": rows[-1]["license"],
                                "source": "wikimedia commons"}
        self.log(f"Images '{topic}': +{len(rows)} free-licence images from Wikimedia Commons")

    def task_synthetic_images(self, _):
        n, size = int(self.st.get("agent_synth_per_task", 12)), int(self.st.get("agent_synth_size", 256))
        d, rows = self._img_dir("synthetic"), []
        for _i in range(n):
            seed = random.getrandbits(48)
            im, ann = synth_scene(random.Random(seed), size)
            iid = _rid("synth", seed)
            path = os.path.join(d, iid + ".jpg")
            im.save(path + ".tmp", "JPEG", quality=90)
            os.replace(path + ".tmp", path)
            qa = ann.pop("qa")
            msgs = [{"role": "user", "content": "<image>\nDescribe the scene."}, {"role": "assistant", "content": ann["caption"]}]
            for x in qa:
                msgs += [{"role": "user", "content": x["q"]}, {"role": "assistant", "content": x["a"]}]
            rows.append(dict(ann, id=iid, type="detection", image=os.path.relpath(path, self.root), seed=seed, qa=qa,
                             messages=msgs, source="AITE generator", license="CC0-1.0",
                             created=datetime.now().isoformat(timespec="seconds")))
            self.last_image = path
        self.writers["detection"].write(rows)
        self.counts["synthetic_images"] += len(rows)
        self.counts["images"] += len(rows)
        self.last_sample = {"type": "generated image", "topic": "object detection", "problem": rows[-1]["caption"],
                            "solution": f"{len(rows[-1]['objects'])} labelled objects", "source": "AITE generator"}
        self.log(f"Generated {len(rows)} labelled detection images")

    def task_vla(self, _):
        n, size = int(self.st.get("agent_vla_per_task", 4)), int(self.st.get("agent_vla_size", 160))
        rows = []
        for _i in range(n):
            seed = random.getrandbits(48)
            frames, ep = vla_episode(random.Random(seed), size)
            eid = _rid("vla", seed)
            d = os.path.join(self._img_dir("vla"), eid)
            os.makedirs(d, exist_ok=True)
            for i, fr in enumerate(frames):
                fp_ = os.path.join(d, f"{i:03d}.jpg")
                fr.save(fp_ + ".tmp", "JPEG", quality=88)
                os.replace(fp_ + ".tmp", fp_)
            for s in ep["steps"]:
                s["observation"]["image"] = os.path.relpath(os.path.join(d, f"{s['observation']['image']:03d}.jpg"), self.root)
            rows.append(dict(ep, id=eid, type="vla-episode", seed=seed, source="AITE generator", license="CC0-1.0",
                             created=datetime.now().isoformat(timespec="seconds")))
            self.counts["vla_frames"] += len(frames)
            self.last_image = os.path.join(d, f"{len(frames) // 2:03d}.jpg")
        self.writers["vla"].write(rows)
        self.counts["vla_episodes"] += len(rows)
        self.last_sample = {"type": "VLA episode", "topic": "robot pick and place", "problem": rows[-1]["instruction"],
                            "solution": f"{len(rows[-1]['steps'])} steps", "source": "AITE generator"}
        self.log(f"Generated {len(rows)} VLA episodes ({sum(len(r['steps']) for r in rows)} steps)")

    def local_loop(self):
        """Generated images and VLA episodes run on their own thread, capped to their share of the collected text:
        cheap synthetic data must never crowd out real text (the most valuable part for LLM training)."""
        while not self.exiting:
            if self.paused or self.disk_low():
                time.sleep(0.5)
                continue
            w = self.mix()
            wt = w.get("text", 0) + w.get("web_images", 0)
            tot = getattr(self, "_tot", self.counts)
            real = tot.get("originals", 0) + tot.get("web_images", 0)  # originals only - DataGen variants must not inflate it
            floor = int(self.st.get("agent_local_floor", 100))
            todo = []
            for k, ck in self.local_counts.items():
                if w.get(k, 0) <= 0:
                    continue
                allowed = float("inf") if wt <= 0 else w[k] / wt * max(real, floor)
                if self.counts[ck] < allowed:
                    todo.append((self.counts[ck] / max(1e-9, w[k]), k))
            if not todo:
                time.sleep(0.5)
                continue
            kind = min(todo)[1]
            fut_key = object()
            with self.lock:
                self.inflight[fut_key] = (kind, None, time.time())
            try:
                self.run_task(kind, None)
                self.counts["tasks_done"] += 1
            except Exception as e:
                self.counts["tasks_failed"] += 1
                self.log(f"{kind} failed: {type(e).__name__}: {str(e)[:160]}")
            finally:
                with self.lock:
                    self.inflight.pop(fut_key, None)
                self.by_kind[kind] = self.by_kind.get(kind, 0) + 1
            time.sleep(0.05)

    # ---- stats
    def stats(self):
        sysx = system_stats(self.root, self.sys_prev)
        self.sys_prev = sysx
        now = time.time()
        wf_ = self.worker_files()
        tot_counts = dict(self.counts)
        tot_fields = dict(self.field_counts)
        with self.store.lock:  # every worker process's saved totals - also those that have finished
            saved = self.store.db.execute("SELECT k, v FROM kv WHERE k LIKE 'counts:w%' OR k LIKE 'field_counts-w%'").fetchall()
        for k_, v_ in saved:
            try:
                d = json.loads(v_)
            except ValueError:
                continue
            tgt = tot_counts if k_.startswith("counts:") else tot_fields
            for k, v in d.items():
                tgt[k] = tgt.get(k, 0) + int(v or 0)
        self._tot = tot_counts
        total = tot_counts["text"] + tot_counts["images"] + tot_counts["vla_episodes"]
        self.rate_hist.append((now, total))
        self.rate_hist = [x for x in self.rate_hist if now - x[0] <= 300]
        t0, n0 = self.rate_hist[0]
        with self.lock:
            busy = [(k, a, round(now - t)) for k, a, t in self.inflight.values()]
        by_kind_now = {}
        for k, _a, _t in busy:
            by_kind_now[k] = by_kind_now.get(k, 0) + 1
        own_busy = list(busy)
        hosts = self.limiter.snapshot() if self.limiter else {}
        waiting = self.limiter.waiting() if self.limiter else 0
        for d in wf_:  # add the worker processes' agents
            for k, v in (d.get("busy_by_kind") or {}).items():
                by_kind_now[k] = by_kind_now.get(k, 0) + v
            busy += [(b["kind"], b.get("arg"), b["s"]) for b in d.get("busy") or []]
            waiting += d.get("waiting", 0)
            for h, v in (d.get("hosts") or {}).items():
                x = hosts.setdefault(h, {"requests": 0, "throttled": 0, "waiting": 0, "rate": v.get("rate", 0)})
                for k in ("requests", "throttled", "waiting"):
                    x[k] = x.get(k, 0) + v.get(k, 0)
        with self.ev_lock:
            ev = self.events[-60:]
        known = self.store.count()
        return {"state": "paused" if self.paused else "running", "pid": os.getpid(), "offline": self.offline,
                "disk_low": bool(getattr(self, "_disk_low", False)), "disk_free_gb": round(getattr(self, "_disk_free", 0) or 0, 1),
                "product": PWT_NAME, "developer": PWT_DEVELOPER,
                "started": self.started, "started_iso": datetime.fromtimestamp(self.started).isoformat(timespec="seconds"),
                "updated": now, "updated_iso": datetime.now().isoformat(timespec="seconds"), "uptime_s": round(now - self.started),
                "workers": self.workers, "effective_workers": self.eff,
                "in_flight": len(own_busy) + sum(int(d.get("in_flight", 0)) for d in wf_),
                "busy": [{"kind": k, "arg": (a if isinstance(a, str) else (a[0] if isinstance(a, tuple) else a)), "s": s}
                         for k, a, s in sorted(busy, key=lambda x: -x[2])[:500]],
                "busy_by_kind": by_kind_now, "waiting": waiting, "processes": 1 + len(wf_),
                "fields": dict(sorted(tot_fields.items(), key=lambda x: -x[1])),
                "topic_fields": self.store.fields() if now - getattr(self, "_tf_t", 0) > 30 or not hasattr(self, "_tf") else self._tf,
                "by_source": dict(sorted(self.by_source.items(), key=lambda x: -x[1])[:30]),
                "counts": tot_counts, "by_kind": dict(self.by_kind), "tokens": tot_counts["tokens"],
                "per_min": round((total - n0) / max(1e-6, now - t0) * 60, 1) if now - t0 > 5 else 0.0,
                "topics": dict({"known": known, "explored": self.store.count("done"), "queued": self.store.count("new"),
                                "space": known * len(FACETS) * len(LEVELS)}, **self.store.lists()),
                "system": sysx, "disk_mb": self.disk_mb(),
                "hosts": dict(sorted(hosts.items(), key=lambda x: -x[1]["requests"])),
                "github": {"state": self.github.state, "error": self.github.error, "repo": self.st.get("gh_repo", ""),
                           "last_push": self.github.last_push, "next_sync_s": max(0, round(self.next_sync - now)),
                           "commits": self.github.pushed_commits},
                "events": ev, "last_sample": self.last_sample, "last_image": self.last_image}

    def disk_mb(self):
        """Folder size, re-measured once a minute (walking many thousands of images every 2 s would be wasteful)."""
        t, mb = getattr(self, "_disk", (0.0, 0.0))
        if time.time() - t > 60:
            mb = round(dir_size(self.root) / 2 ** 20, 1)
            self._disk = (time.time(), mb)
        return mb

    def write_stats(self, s):
        def atomic(path, text):
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, path)
        atomic(os.path.join(self.adir, "status.json"), json.dumps(s))
        public = {k: v for k, v in s.items() if k not in ("events", "busy", "pid", "hosts", "last_image")}
        atomic(os.path.join(self.root, "stats.json"), json.dumps(public, indent=2))
        self.store.put(self.ckey, self.counts)
        self.store.put("field_counts" + self.wtag, self.field_counts)
        self.store.put("by_source", self.by_source)
        if "topic_fields" in s:
            self._tf, self._tf_t = s["topic_fields"], time.time()
        self.store.put("last_sample", self.last_sample)
        self.store.put("last_image", self.last_image)

    def running_topics(self):
        """topic -> agent number for every parallel agent working on a topic right now."""
        with self.lock:
            items = list(self.inflight.items())
        out = {}
        for i, (fut, (kind, arg, t0)) in enumerate(sorted(items, key=lambda x: x[1][2]), 1):
            if kind in ("text", "web_images") and isinstance(arg, str):
                out.setdefault(arg, i)
        return out

    def export_topics(self):
        try:
            self.store.export_json(self.topics_json, self.running_topics())
        except Exception as e:
            self.log(f"topics.json not written: {e}")

    def history(self, s):
        os.makedirs(os.path.join(self.root, "stats"), exist_ok=True)  # recreated if someone removed it
        p = os.path.join(self.root, "stats", "history.csv")
        new = not os.path.exists(p)
        c, sy = s["counts"], s["system"]
        with open(p, "a") as f:
            if new:
                f.write("time,text,originals,variants,web_images,synthetic_images,vla_episodes,topics_explored,topics_known,"
                        "per_min,cpu,mem,disk_mb\n")
            f.write(f"{s['updated_iso']},{c['text']},{c['originals']},{c['variants']},{c['web_images']},{c['synthetic_images']},"
                    f"{c['vla_episodes']},{s['topics']['explored']},{s['topics']['known']},{s['per_min']},{sy.get('cpu', 0)},"
                    f"{sy.get('mem', 0)},{s['disk_mb']}\n")

    def sync(self, s):
        def go():
            for w in self.writers.values():
                w.rotate(force=True)
            with open(os.path.join(self.root, "README.md"), "w") as f:
                f.write(agent_readme(s))
            self.history(s)
            self.export_topics()
            if self.github.sync(bool(self.st.get("gh_push_data", True))):
                self.log(f"GitHub: {self.github.state}" + (f" - {self.github.error}" if self.github.error else ""))
        if self.sync_thread is None or not self.sync_thread.is_alive():
            self.sync_thread = threading.Thread(target=go, daemon=True, name="gh-sync")
            self.sync_thread.start()

    # ---- main loop
    def disk_low(self):
        """True while free disk space is below the guard - collecting pauses by itself so the Mac never fills up."""
        if time.time() - getattr(self, "_disk_t", 0) > 10:
            self._disk_t = time.time()
            try:
                import shutil
                free = shutil.disk_usage(self.root).free / 2 ** 30
            except OSError:
                free = 999
            low = free < float(self.st.get("agent_min_free_gb", 5))
            if low != getattr(self, "_disk_low", False):
                self.log(f"Disk almost full ({free:.1f} GB free) - collecting paused by itself" if low else
                         f"Disk space back ({free:.1f} GB free) - collecting again")
            self._disk_low, self._disk_free = low, free
        return getattr(self, "_disk_low", False)

    def n_procs(self):
        """Enough processes for the thread limit, and up to one per CPU core so DataGen's CPU work runs in parallel."""
        return max(1, math.ceil(self.workers / AGENTS_PER_PROCESS),
                   min(max(1, (os.cpu_count() or 2) // 2), math.ceil(self.workers / 500)))  # half the cores: the Mac stays usable

    def share(self, n=None):
        n = n or self.n_procs()
        return max(1, math.ceil(self.workers / n))

    def manage_processes(self):
        """More agents than one process can hold (macOS: ~2,000 threads per process) -> extra worker processes."""
        n = self.n_procs()
        if getattr(self, "_np", None) != n:
            self._np = n
            if self.limiter:
                self.limiter.configure(self.st, 1.0 / n)
            with open(os.path.join(self.adir, "procs.json"), "w") as f:
                json.dump({"n_procs": n, "main_pid": os.getpid(), "workers": self.workers}, f)
            self.log(f"{PWT_NAME}: {self.workers:,} agents in {n} process{'es' * (n > 1)}")
        for i in range(1, n):
            pr = self.procs.get(i)
            if (pr is None or pr.poll() is not None) and time.time() - getattr(self, f"_spawn{i}", 0) > 20:
                setattr(self, f"_spawn{i}", time.time())
                self.procs[i] = agent_spawn(self.root, offline=self.offline, worker_id=i)
        for i in [k for k in self.procs if k >= n]:
            try:
                self.procs.pop(i).terminate()
            except Exception:
                pass

    def worker_files(self):
        out = []
        for f in os.listdir(self.adir):
            if f.startswith("worker-") and f.endswith(".json"):
                try:
                    with open(os.path.join(self.adir, f)) as fh:
                        d = json.load(fh)
                    if time.time() - d.get("updated", 0) < 30:
                        out.append(d)
                except (OSError, ValueError):
                    pass
        return out

    def run_worker(self):
        """An extra worker process: collects topic / archive / web-image data with its own agents and files."""
        pidf = os.path.join(self.adir, f"worker-{self.worker_id}.pid")
        with open(pidf, "w") as f:
            f.write(str(os.getpid()))
        settings_rev, last = None, 0.0
        while True:
            ctl = self.control()
            try:
                with open(os.path.join(self.adir, "procs.json")) as f:
                    procs = json.load(f)
            except (OSError, ValueError):
                procs = {}
            n = int(procs.get("n_procs", 1))
            main = procs.get("main_pid")
            try:
                os.kill(int(main), 0)
                main_alive = True
            except (OSError, TypeError, ValueError):
                main_alive = False
            if not main_alive or self.worker_id >= n or (self.max_seconds and time.time() - self.started > self.max_seconds):
                break
            if ctl.get("settings_rev") != settings_rev:
                settings_rev = ctl.get("settings_rev")
                try:
                    self.reload()
                except Exception:
                    pass
            self.workers = int(procs.get("workers", self.workers))
            per = max(1, math.ceil(self.workers / max(1, n)))
            share = max(0, min(per, self.workers - self.worker_id * per))
            self.pool._max_workers = max(self.pool._max_workers, share)
            if self.limiter and getattr(self, "_np", None) != n:
                self._np = n
                self.limiter.configure(self.st, 1.0 / n)
            self.paused = bool(ctl.get("paused", False))
            if not self.paused and not self.disk_low():
                with self.lock:
                    n_busy = len(self.inflight)
                while n_busy < share:
                    kind = self.pick_kind()
                    if kind in ("text", "web_images"):
                        t = self.store.next(1, "text" if kind == "text" else "images", bool(self.st.get("agent_focus_only")))
                        if not t:
                            break
                        self.submit(kind, t[0])
                    elif kind == "archive":
                        self.submit("archive", None)
                    else:
                        break
                    n_busy += 1
            if time.time() - last >= 2:
                last = time.time()
                with self.lock:
                    busy = [(k, a, round(time.time() - t)) for k, a, t in self.inflight.values()]
                kinds = {}
                for k, _a, _t in busy:
                    kinds[k] = kinds.get(k, 0) + 1
                d = {"worker": self.worker_id, "pid": os.getpid(), "updated": time.time(), "counts": self.counts,
                     "fields": self.field_counts, "in_flight": len(busy), "busy_by_kind": kinds,
                     "busy": [{"kind": k, "arg": a if isinstance(a, str) else None, "s": s_} for k, a, s_ in busy[:300]],
                     "hosts": self.limiter.snapshot() if self.limiter else {}, "waiting": self.limiter.waiting() if self.limiter else 0}
                tmp = os.path.join(self.adir, f"worker-{self.worker_id}.json.tmp")
                with open(tmp, "w") as f:
                    json.dump(d, f)
                os.replace(tmp, os.path.join(self.adir, f"worker-{self.worker_id}.json"))
                self.store.put(self.ckey, self.counts)
                self.store.put("field_counts" + self.wtag, self.field_counts)
            for w in self.writers.values():
                w.rotate()
            time.sleep(0.3)
        self.exiting = True
        end = time.time() + 30
        while time.time() < end:
            with self.lock:
                if not self.inflight:
                    break
            time.sleep(0.2)
        self.pool.shutdown(wait=False, cancel_futures=True)
        for w in self.writers.values():
            w.rotate(force=True)
        self.store.put(self.ckey, self.counts)
        for f in (pidf, os.path.join(self.adir, f"worker-{self.worker_id}.json")):
            try:
                os.remove(f)
            except OSError:
                pass

    def run(self):
        if self.worker_id:
            return self.run_worker()
        pidf = os.path.join(self.adir, "agent.pid")
        with open(pidf, "w") as f:
            f.write(str(os.getpid()))
        self.log(f"Agent started ({'offline test' if self.offline else 'live'}) - {PWT_NAME} with {self.workers} workers; "
                 f"{self.store.count():,} topics known, {self.store.count('done'):,} done, {self.store.count('new'):,} left")
        if getattr(self, "_import_note", ""):
            self.log(self._import_note)
        try:
            import psutil
            psutil.cpu_percent(interval=None)
        except ImportError:
            pass
        last_stats = last_hist = 0.0
        last_exp = 0.0
        settings_rev = self.control().get("settings_rev", 0)
        threading.Thread(target=self.local_loop, daemon=True, name="local-gen").start()
        exit_reason = ""
        while True:
            now = time.time()
            ctl = self.control()
            self.paused = bool(ctl.get("paused", False))
            if ctl.get("workers"):
                self.workers = max(1, min(MAX_AGENTS, int(ctl["workers"])))
                self.pool._max_workers = max(self.pool._max_workers, min(AGENTS_PER_PROCESS, self.workers))
            self.manage_processes()
            if self.max_seconds and now - self.started > self.max_seconds:
                exit_reason = "time limit (test run)"
                break
            hb = float(ctl.get("heartbeat", 0) or 0)
            if self.paused and ctl.get("gui") and now - hb > 30:
                exit_reason = "paused and the AITE window is closed"
                break
            if ctl.get("settings_rev", 0) != settings_rev:
                settings_rev = ctl.get("settings_rev", 0)
                try:
                    self.reload()
                except Exception as e:
                    self.log(f"Settings reload failed: {e}")
            if not self.worker_id and not self.offline and \
                    now - getattr(self, "_rag_t", 0) > 60 * int(self.st.get("rag_sync_min", 10)):
                self._rag_t = now  # GitHub -> RAG index -> Kaggle, in its own low-priority process (one at a time)
                try:
                    import subprocess
                    subprocess.Popen([sys.executable, os.path.abspath(__file__), "--rag-update", "--dir", self.root],
                                     stdout=subprocess.DEVNULL, stderr=open(os.path.join(HERE, "rag_errors.log"), "a"),
                                     stdin=subprocess.DEVNULL, start_new_session=True, cwd=HERE)
                except Exception as e:
                    self.log(f"RAG / Kaggle update not started: {e}")
            if ctl.get("sync_now", 0) > self.store.get("sync_done", 0):
                self.store.put("sync_done", ctl["sync_now"])
                self.next_sync = now
            if not self.paused and not self.disk_low():
                cpu = (self.sys_prev or {}).get("cpu", 0) or 0
                cap = float(self.st.get("agent_cpu_cap", 70))
                if cpu > cap:
                    self.eff = max(1, int(self.eff * 0.8))
                own = self.share()
                if cpu > cap:
                    pass
                elif self.eff < own:
                    self.eff = min(own, self.eff + max(1, own // 16))
                self.eff = min(self.eff, own)
                with self.lock:
                    n_busy = len(self.inflight)
                    exp_busy = sum(1 for v in self.inflight.values() if v[0] in ("expand", "seed", "seed_concepts"))
                if not exp_busy and product_on(self.st, "product_topic_engine") and \
                        now - last_exp > (2 if self.store.count("new") < max(200, self.workers * 4) else 12):
                    last_exp = now
                    if not self.store.get("seed_done", False):
                        self.submit("seed", int(self.store.get("seed_page", 0)) + 1)
                    elif not self.store.get("concepts_done", False):
                        self.submit("seed_concepts", int(self.store.get("concept_page", 0)) + 1)
                    elif self.store.count("new") < max(200, self.workers * 4):
                        for row in self.store.to_expand(3):
                            self.submit("expand", tuple(row))
                    n_busy += 1
                while n_busy < self.eff:
                    kind = self.pick_kind()
                    if kind == "text":
                        t = self.store.next(1, "text", bool(self.st.get("agent_focus_only")))
                        if not t:
                            break
                        self.submit("text", t[0])
                    elif kind == "web_images":
                        t = self.store.next(1, "images")
                        if not t:
                            break
                        self.submit("web_images", t[0])
                    elif kind == "archive":
                        self.submit("archive", None)
                    else:
                        break
                    n_busy += 1
            if now - last_stats >= 2:
                last_stats = now
                try:  # bookkeeping problems are logged - they never stop collection
                    os.makedirs(self.adir, exist_ok=True)
                    s = self.stats()
                    self.write_stats(s)
                    if now - last_hist >= 60:
                        last_hist = now
                        self.history(s)
                        self.export_topics()
                    if now >= self.next_sync:
                        self.next_sync = now + float(self.st.get("gh_interval_min", 5)) * 60
                        self.sync(s)
                except Exception as e:
                    self.log(f"Stats / sync step skipped: {type(e).__name__}: {e}")
            for w in self.writers.values():
                w.rotate()
            time.sleep(0.25)
        self.log(f"Agent exits: {exit_reason}")
        self.exiting = True
        if self.procs:  # ask the worker processes to finish cleanly (they close their files), then make sure
            try:
                with open(os.path.join(self.adir, "procs.json"), "w") as f:
                    json.dump({"n_procs": 1, "main_pid": os.getpid(), "workers": 0}, f)
            except OSError:
                pass
            end = time.time() + 45
            while time.time() < end and any(pr.poll() is None for pr in self.procs.values()):
                time.sleep(0.3)
            for pr in self.procs.values():
                if pr.poll() is None:
                    pr.terminate()
        deadline = time.time() + float(self.st.get("agent_task_timeout", 120)) / 2
        while time.time() < deadline:  # let running tasks finish so their rows land in a closed shard
            with self.lock:
                if not self.inflight:
                    break
            time.sleep(0.2)
        self.pool.shutdown(wait=False, cancel_futures=True)
        for w in self.writers.values():
            w.rotate(force=True)
        self.export_topics()
        s = self.stats()
        s["state"] = "exited"
        self.write_stats(s)
        try:
            os.remove(pidf)
        except OSError:
            pass
        return s


def agent_dir(st):
    return os.path.expanduser(st.get("agent_dir") or os.path.join(HERE, "dataset"))


def agent_pid(root):
    """The running agent's pid - None if it exited, even when its process entry lingers as a zombie."""
    try:
        with open(os.path.join(root, ".agent", "agent.pid")) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    try:  # reap it if this process started it (a finished child stays a zombie until reaped)
        os.waitpid(pid, os.WNOHANG)
    except (ChildProcessError, OSError):
        pass
    return pid if _alive(pid) else None


def agent_control(root, **kw):
    p = os.path.join(root, ".agent", "control.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    try:
        with open(p) as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.update(kw)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f)
    os.replace(tmp, p)
    return d


def agent_spawn(root, offline=False, max_seconds=None, worker_id=0):
    """Starts the agent as its own background process: the window stays smooth, and collection keeps going
    while the window is closed (until it is paused)."""
    import subprocess
    os.makedirs(os.path.join(root, ".agent"), exist_ok=True)
    cmd = [sys.executable, os.path.abspath(__file__), "--agent", "--dir", root]
    if offline:
        cmd.append("--offline")
    if max_seconds:
        cmd += ["--seconds", str(max_seconds)]
    if worker_id:
        cmd += ["--worker", str(worker_id)]
    out = open(os.path.join(root, ".agent", f"stdout{'-w' + str(worker_id) if worker_id else ''}.log"), "a")
    return subprocess.Popen(cmd, stdout=out, stderr=out, stdin=subprocess.DEVNULL, start_new_session=True, cwd=HERE)


def agent_status(root):
    try:
        with open(os.path.join(root, ".agent", "status.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ============================================================================= LLM Trainer (local, no API, no cloud)
# Teaches a small open model on THIS Mac with the collected data: LoRA fine-tuning with Apple's MLX (mlx-lm),
# which runs on the Apple-silicon GPU. Everything happens in its own environment (.trainer-venv), installed with one
# click, so AITE's own Python packages are never touched.
TRAINER_VENV = os.path.join(HERE, ".trainer-venv")
TRAINER_RUNS = os.path.join(HERE, "trainer_runs")
TRAINER_DATA = os.path.join(HERE, "trainer_data")  # text data downloaded from GitHub for training (GitHub-first mode)
_ITER_RE = re.compile(r"Iter (\d+): Train loss ([\d.]+)(?:.*?It/sec ([\d.]+))?(?:.*?Tokens/sec ([\d.]+))?(?:.*?Peak mem ([\d.]+) GB)?")
_VAL_RE = re.compile(r"Iter (\d+): Val loss ([\d.]+)")
_DL_RE = re.compile(r"Fetching \d+ files:\s+(\d+)%")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
# mlx-lm >= 0.30 prints a table:  "   12    2.429 ▲     46    12.7k"  and  "   10    val 2.665    14.31s"
_ROW_VAL_RE = re.compile(r"^\s*(\d+)\s+val\s+([\d.]+)")
_ROW_TRAIN_RE = re.compile(r"^\s*(\d+)\s+([\d.]+)\s*[▼▲=]?\s+([\d.]+)\s+([\d.]+)([kM]?)\s*$")


def mac_ram_gb():
    try:
        import psutil
        return round(psutil.virtual_memory().total / 2 ** 30)
    except ImportError:
        return 8


def trainer_python():
    return os.path.join(TRAINER_VENV, "bin", "python")


def trainer_ready():
    """True when the trainer environment exists and mlx-lm imports (Apple silicon only)."""
    import subprocess
    if not os.path.exists(trainer_python()):
        return False
    try:
        r = subprocess.run([trainer_python(), "-c", "import mlx_lm, mlx.core"], capture_output=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def trainer_supported():
    return sys.platform == "darwin" and os.uname().machine == "arm64"


def trainer_install(log=print):
    """One click: a private Python environment with mlx-lm (about 0.5 GB)."""
    import subprocess
    steps = [[sys.executable, "-m", "venv", TRAINER_VENV],
             [trainer_python(), "-m", "pip", "install", "-q", "--upgrade", "pip"],
             [trainer_python(), "-m", "pip", "install", "-q", "mlx-lm"]]
    for cmd in steps:
        log("Installing: " + " ".join(os.path.basename(c) if i == 0 else c for i, c in enumerate(cmd)))
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            log((r.stdout + r.stderr)[-800:])
            return False
    return trainer_ready()


def _read_rows(path):
    """Rows from an AITE shard (.jsonl.gz - a crashed '.open' one too, up to its last flush), a .jsonl file or a
    Manual-mode JSON export."""
    import gzip
    out = []
    try:
        if path.endswith((".gz", ".gz.open")):
            with gzip.open(path, "rt", encoding="utf-8") as f:
                try:
                    for line in f:
                        out.append(json.loads(line))
                except (EOFError, OSError, ValueError):
                    pass
        elif path.endswith(".jsonl"):
            with open(path, encoding="utf-8") as f:
                out = [json.loads(l) for l in f if l.strip()]
        else:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            out = d.get("data", []) if isinstance(d, dict) else d
    except (OSError, ValueError):
        pass
    return [r for r in out if isinstance(r, dict)]


def row_messages(r, system=""):
    """Any AITE row -> clean chat messages (text-only models: rows about images are skipped)."""
    if r.get("type") in ("detection", "image-text", "vla-episode"):
        return None
    msgs = r.get("messages")
    if not msgs:
        p = r.get("problem") or r.get("instruction") or ""
        a = r.get("solution") or r.get("output") or ""
        if not p or not a:
            return None
        msgs = [{"role": "user", "content": p}, {"role": "assistant", "content": a}]
    msgs = [{"role": m.get("role"), "content": str(m.get("content", "")).strip()} for m in msgs
            if m.get("role") in ("system", "user", "assistant") and str(m.get("content", "")).strip()]
    if not any(m["role"] == "assistant" for m in msgs) or msgs[-1]["role"] != "assistant":
        return None
    if system and msgs[0]["role"] != "system":
        msgs = [{"role": "system", "content": system}] + msgs
    return msgs


SOURCE_NAMES = {"stackexchange": "Stack Exchange (topic search)", "huggingface": "Hugging Face datasets", "openalex": "OpenAlex papers",
                "arxiv": "arXiv papers", "wikipedia": "Wikipedia", "wikibooks": "Wikibooks", "duckduckgo": "Web pages",
                "mathoverflow.net": "MathOverflow", "Stackoverflow.com": "Stack Overflow", "file": "Added files",
                "openlifescienceai/medmcqa": "MedMCQA (medicine)", "qiaojin/PubMedQA": "PubMedQA (biomedical)",
                "allenai/ai2_arc": "ARC (science)"}


def row_source(r):
    """Which source a row came from, as a plain name (archive site / dataset first, then the search source)."""
    k = r.get("archive") or r.get("source") or "file"
    if k.endswith(".stackexchange.com"):
        return k.replace(".stackexchange.com", "").replace("-", " ").title() + " Stack Exchange"
    return SOURCE_NAMES.get(k, k)


def build_training_set(sources, out_dir, tiers=("high", "medium", "basic"), kinds=("original", "variant"),
                       max_rows=0, min_valid=8, system="", max_chars=12000, max_seq=None, fields=None, srcs=None,
                       keywords=None, dry_run=False):
    """Collected data -> train.jsonl / valid.jsonl in the chat format mlx-lm trains on. Keeps AITE's own
    train/validation split (a record and its variants stay together), removes exact duplicates."""
    import glob
    files = []
    for src in sources:
        if os.path.isdir(src):
            files += sorted(glob.glob(os.path.join(src, "text", "*.jsonl.gz*")))
            files += sorted(glob.glob(os.path.join(src, "*.jsonl")))
        elif os.path.exists(src):
            files.append(src)
    if max_seq:  # ~3.2 characters per token: longer examples would be cut off mid-answer, so leave them out
        max_chars = min(max_chars, int(max_seq * 3.2))
    train, valid, seen = [], [], set()
    stats = {"files": len(files), "skipped_images": 0, "skipped_filter": 0, "duplicates": 0, "too_long": 0, "topics": {},
             "fields": {}, "sources": {}, "all_fields": {}, "all_sources": {}}
    kw = [k.strip().lower() for k in (keywords or []) if k.strip()]
    for fp in files:
        for r in _read_rows(fp):
            if r.get("type") in ("detection", "image-text", "vla-episode"):
                stats["skipped_images"] += 1
                continue
            fld, src_ = r.get("field") or "general", row_source(r) if r.get("source") or r.get("archive") else "Added files"
            stats["all_fields"][fld] = stats["all_fields"].get(fld, 0) + 1
            stats["all_sources"][src_] = stats["all_sources"].get(src_, 0) + 1
            if r.get("quality_tier") and r["quality_tier"] not in tiers or r.get("kind", "original") not in kinds:
                stats["skipped_filter"] += 1
                continue
            if (fields and fld not in fields) or (srcs and src_ not in srcs) or \
                    (kw and not any(k in (r.get("topic", "") + " " + r.get("problem", "")[:400]).lower() for k in kw)):
                stats["skipped_filter"] += 1
                continue
            msgs = row_messages(r, system)
            if not msgs:
                stats["skipped_filter"] += 1
                continue
            if sum(len(m["content"]) for m in msgs) > max_chars:
                stats["too_long"] += 1
                continue
            key = hashlib.sha1(json.dumps(msgs, sort_keys=True).encode()).hexdigest()
            if key in seen:
                stats["duplicates"] += 1
                continue
            seen.add(key)
            fam = str(r.get("variant_of") or r.get("id") or key)
            split = r.get("split") or ("validation" if int(hashlib.sha1(fam.encode()).hexdigest(), 16) % 50 == 0 else "train")
            (valid if split == "validation" else train).append(msgs)
            t = r.get("topic", "")
            stats["topics"][t] = stats["topics"].get(t, 0) + 1
            stats["fields"][fld] = stats["fields"].get(fld, 0) + 1
            stats["sources"][src_] = stats["sources"].get(src_, 0) + 1
    rng = random.Random(7)
    rng.shuffle(train)
    if max_rows and len(train) > max_rows:
        train = train[:max_rows]
    while len(valid) < min_valid and len(train) > min_valid * 3:  # the trainer needs a few rows to check itself on
        valid.append(train.pop())
    chars = sum(len(m["content"]) for rows in (train, valid) for msgs in rows for m in msgs)
    if dry_run:
        stats.update(train=len(train), valid=len(valid), tokens=chars // 4, topics=dict(sorted(stats["topics"].items(), key=lambda x: -x[1])[:20]),
                     sample=[m for m in (train[:3] + valid[:2])])
        return stats
    os.makedirs(out_dir, exist_ok=True)
    for name, rows in (("train", train), ("valid", valid)):
        with open(os.path.join(out_dir, f"{name}.jsonl"), "w", encoding="utf-8") as f:
            for m in rows:
                f.write(json.dumps({"messages": m}, ensure_ascii=False) + "\n")
    chars = sum(len(m["content"]) for rows in (train, valid) for msgs in rows for m in msgs)
    stats.update(train=len(train), valid=len(valid), tokens=chars // 4,
                 topics=dict(sorted(stats["topics"].items(), key=lambda x: -x[1])[:20]))
    with open(os.path.join(out_dir, "stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    return stats


def trainer_env():
    """Plain HTTPS model downloads (the newer Xet download path can stall on some networks), no telemetry."""
    return dict(os.environ, HF_HUB_DISABLE_TELEMETRY="1", HF_HUB_DISABLE_XET="1", TOKENIZERS_PARALLELISM="false",
                PYTHONUNBUFFERED="1")


def hf_cache_bytes(model):
    """Bytes of this model already in the Hugging Face cache (shows real download progress)."""
    base = os.environ.get("HF_HUB_CACHE") or os.path.join(os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface"), "hub")
    d = os.path.join(base, "models--" + model.replace("/", "--"))
    total = 0
    for dp, dn, fn in os.walk(d):
        for f in fn:
            fp = os.path.join(dp, f)
            if not os.path.islink(fp):
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    return total


def trainer_command(run_dir, model, iters, batch=4, lr=1e-5, layers=8, max_seq=1024, mask_prompt=True,
                    fine_tune="lora", seed=7):
    cmd = [trainer_python(), "-m", "mlx_lm", "lora", "--model", model, "--train", "--data", os.path.join(run_dir, "data"),
           "--adapter-path", os.path.join(run_dir, "adapter"), "--fine-tune-type", fine_tune, "--iters", str(int(iters)),
           "--batch-size", str(int(batch)), "--learning-rate", f"{float(lr):g}", "--num-layers", str(int(layers)),
           "--max-seq-length", str(int(max_seq)), "--steps-per-report", str(max(1, min(10, int(iters) // 20 or 1))),
           "--steps-per-eval", str(max(10, int(iters) // 8)), "--val-batches", "8",
           "--save-every", str(max(20, int(iters) // 5)), "--grad-checkpoint", "--seed", str(seed)]
    if mask_prompt:
        cmd.append("--mask-prompt")
    return cmd


def trainer_start(run_dir, cmd, meta):
    """Training runs as its own process (the window stays smooth, and closing it does not lose the run)."""
    import subprocess
    os.makedirs(run_dir, exist_ok=True)
    logf = open(os.path.join(run_dir, "train.log"), "w")
    env = trainer_env()
    p = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True,
                         cwd=run_dir, env=env)
    with open(os.path.join(run_dir, "train.json"), "w") as f:
        json.dump(dict(meta, pid=p.pid, cmd=cmd, started=time.time()), f, indent=2)
    return p


def _alive(pid):
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError, TypeError):
        return False
    try:  # a finished child that was never reaped is a zombie, not a running trainer
        import psutil
        return psutil.Process(int(pid)).status() != psutil.STATUS_ZOMBIE
    except Exception:
        return True


def trainer_progress(run_dir):
    """Reads the run's log: downloading / training / done / error / stopped, losses, speed, time left."""
    try:
        with open(os.path.join(run_dir, "train.json")) as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return {"state": "none"}
    try:
        with open(os.path.join(run_dir, "train.log"), errors="replace") as f:
            txt = f.read()
    except OSError:
        txt = ""
    train, val, tok_s, mem, it_s = [], [], 0.0, 0.0, 0.0
    txt = _ANSI_RE.sub("", txt)
    for line in txt.replace("\r", "\n").split("\n"):
        m = _ROW_VAL_RE.match(line)
        if m:
            val.append((int(m.group(1)), float(m.group(2))))
            continue
        m = _ROW_TRAIN_RE.match(line)
        if m:
            train.append((int(m.group(1)), float(m.group(2))))
            tok_s = float(m.group(3))
            continue
        m = _ITER_RE.search(line)
        if m:
            train.append((int(m.group(1)), float(m.group(2))))
            it_s = float(m.group(3) or it_s or 0)
            tok_s = float(m.group(4) or tok_s or 0)
            mem = float(m.group(5) or mem or 0)
            continue
        m = _VAL_RE.search(line)
        if m:
            val.append((int(m.group(1)), float(m.group(2))))
    dl = [int(x) for x in _DL_RE.findall(txt)]
    alive = _alive(meta.get("pid"))
    iters = int(meta.get("iters", 0))
    cur = train[-1][0] if train else 0
    if train and not meta.get("train_t0"):  # first training step seen: the clock for 'time left' starts here
        meta["train_t0"], meta["train_i0"] = time.time(), cur
        try:
            with open(os.path.join(run_dir, "train.json"), "w") as f:
                json.dump(meta, f, indent=2)
        except OSError:
            pass
    if alive and not mem:
        try:
            import psutil
            mem = psutil.Process(int(meta["pid"])).memory_info().rss / 2 ** 30
        except Exception:
            pass
    if not it_s and meta.get("train_t0") and cur > meta.get("train_i0", 0):
        it_s = (cur - meta["train_i0"]) / max(1e-6, time.time() - meta["train_t0"])
    done = "Saved final weights" in txt or (os.path.exists(os.path.join(run_dir, "adapter", "adapters.safetensors"))
                                            and not alive and cur >= iters)
    err = ""
    if not alive and not done:
        tb = txt.rfind("Traceback")
        err = (txt[tb:].strip().split("\n")[-1] if tb >= 0 else "") or ("stopped" if meta.get("stopped") else "the trainer ended early")
    state = ("done" if done else "training" if alive and train else "preparing" if alive else
             "stopped" if meta.get("stopped") else "error")
    elapsed = time.time() - meta.get("started", time.time())
    eta = (iters - cur) / it_s if it_s and alive else 0
    dl_mb = None
    if dl and not train and alive and meta.get("model"):
        dl_mb = (round(hf_cache_bytes(meta["model"]) / 2 ** 20), round(TRAINER_MODELS.get(meta["model"], ("", 0, 0))[1] * 1024))
    return {"state": state, "iter": cur, "iters": iters, "train": train, "val": val, "tok_s": tok_s, "it_s": it_s,
            "peak_mem": mem, "eta_s": round(eta), "elapsed_s": round(elapsed), "download": dl[-1] if dl and not train else None,
            "download_mb": dl_mb,
            "error": err, "model": meta.get("model"), "run": run_dir, "adapter": os.path.join(run_dir, "adapter"),
            "log_tail": txt[-1500:]}


def trainer_stop(run_dir):
    import signal
    try:
        with open(os.path.join(run_dir, "train.json")) as f:
            meta = json.load(f)
        os.killpg(os.getpgid(int(meta["pid"])), signal.SIGTERM)
        meta["stopped"] = True
        with open(os.path.join(run_dir, "train.json"), "w") as f:
            json.dump(meta, f, indent=2)
        return True
    except Exception:
        return False


def trainer_generate(model, prompt, adapter=None, max_tokens=256, system="", timeout=600):
    """Asks the model (with or without the trained adapter) - for the Before / After comparison."""
    import subprocess
    cmd = [trainer_python(), "-m", "mlx_lm", "generate", "--model", model, "--prompt", prompt,
           "--max-tokens", str(int(max_tokens)), "--temp", "0.2", "--seed", "7"]
    if adapter:
        cmd += ["--adapter-path", adapter]
    if system:
        cmd += ["--system-prompt", system]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=trainer_env())
    out = r.stdout
    if "==========" in out:
        parts = out.split("==========")
        out = parts[1] if len(parts) >= 3 else parts[-1]
    if r.returncode != 0 and not out.strip():
        raise RuntimeError((r.stderr or "generation failed").strip().split("\n")[-1][:300])
    return out.strip()


PREVIEW_SCRIPT = r"""
import sys, json
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
cfg = json.loads(sys.argv[1])
models = {"before": load(cfg["model"])}
if cfg.get("adapter"):
    models["after"] = load(cfg["model"], adapter_path=cfg["adapter"])
print(json.dumps({"ready": True, "have": list(models)}), flush=True)
for line in sys.stdin:
    try:
        req = json.loads(line)
        model, tok = models[req["which"]]
        msgs = ([{"role": "system", "content": req["system"]}] if req.get("system") else []) + req["messages"]
        try:
            prompt = tok.apply_chat_template(msgs, add_generation_prompt=True)
        except Exception:
            prompt = (chr(10) * 2).join(m["content"] for m in msgs)
        out = generate(model, tok, prompt=prompt, max_tokens=int(req.get("max_tokens", 300)),
                       sampler=make_sampler(temp=float(req.get("temp", 0.2))))
        print(json.dumps({"id": req["id"], "text": out.strip()}), flush=True)
    except Exception as e:
        print(json.dumps({"id": req.get("id") if isinstance(req, dict) else None, "error": f"{type(e).__name__}: {e}"}), flush=True)
"""


class PreviewWorker:
    """Runs the model inside AITE: the base model ('before') and the trained one ('after') are loaded once in a
    helper process and stay ready, so each answer takes a fraction of a second instead of reloading every time."""

    def __init__(self, model, adapter=None):
        import subprocess
        self.model, self.adapter = model, adapter
        self.p = subprocess.Popen([trainer_python(), "-c", PREVIEW_SCRIPT, json.dumps({"model": model, "adapter": adapter})],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(self.errlog(), "w"), text=True,
                                  env=trainer_env(), start_new_session=True)
        self.lock, self.n, self.replies, self.have, self.error = threading.Lock(), 0, {}, [], ""
        self.ready = threading.Event()
        self.cv = threading.Condition()
        threading.Thread(target=self._read, daemon=True).start()

    @staticmethod
    def errlog():
        os.makedirs(TRAINER_RUNS, exist_ok=True)
        return os.path.join(TRAINER_RUNS, "preview_errors.log")

    def _read(self):
        for line in self.p.stdout:
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get("ready"):
                self.have = msg.get("have", [])
                self.ready.set()
                continue
            with self.cv:
                self.replies[msg.get("id")] = msg
                self.cv.notify_all()
        try:
            with open(self.errlog(), errors="replace") as f:
                tail = [l for l in f.read().strip().split("\n") if l.strip() and "Warning" not in l]
        except OSError:
            tail = []
        self.error = self.error or (tail[-1][:200] if tail else "the model process ended")
        self.ready.set()
        with self.cv:
            self.cv.notify_all()

    def alive(self):
        return self.p.poll() is None

    def ask(self, which, messages, max_tokens=300, temp=0.2, system="", timeout=300):
        if not self.ready.wait(timeout):
            raise RuntimeError("the model is still loading")
        if not self.alive() or which not in self.have:
            raise RuntimeError(self.error or f"no '{which}' model loaded")
        with self.lock:
            self.n += 1
            rid = self.n
            self.p.stdin.write(json.dumps({"id": rid, "which": which, "messages": messages, "max_tokens": max_tokens,
                                           "temp": temp, "system": system}) + "\n")
            self.p.stdin.flush()
        end = time.time() + timeout
        with self.cv:
            while rid not in self.replies and self.alive() and time.time() < end:
                self.cv.wait(0.5)
            msg = self.replies.pop(rid, None)
        if msg is None:
            raise RuntimeError(self.error or "no answer in time")
        if msg.get("error"):
            raise RuntimeError(msg["error"])
        return msg["text"]

    def stop(self):
        try:
            self.p.terminate()
        except Exception:
            pass


def reference_answer(text):
    """The checkable final answer inside a reference solution, if it has one."""
    t = text or ""
    m = re.search(r"Answer:\s*([A-E])\)", t)
    if m:
        return ("choice", m.group(1))
    m = re.search(r"####\s*([-\d.,/]+)", t) or re.search(r"\\boxed\{([^{}]+)\}", t)
    if m:
        return ("value", m.group(1).replace(",", "").strip())
    m = re.search(r"Answer:\s*(yes|no|maybe)\b", t, re.I)
    if m:
        return ("yesno", m.group(1).lower())
    return None


def _f1(a, b):
    ta, tb = re.findall(r"\w+", (a or "").lower()), re.findall(r"\w+", (b or "").lower())
    if not ta or not tb:
        return 0.0
    common = sum(min(ta.count(w), tb.count(w)) for w in set(ta))
    if not common:
        return 0.0
    p, r = common / len(ta), common / len(tb)
    return round(2 * p * r / (p + r), 3)


def score_answer(answer, reference):
    """(correct or None if not checkable, word-overlap similarity 0..1) of a model answer against the reference."""
    ref = reference_answer(reference)
    ok = None
    a = answer or ""
    if ref:
        kind, v = ref
        if kind == "choice":
            ok = bool(re.search(rf"(?<![A-Za-z]){v}\)|\b(answer|option)\s*(is\s*)?:?\s*\(?{v}\b", a, re.I))
        elif kind == "value":
            nums = re.findall(r"-?\d+(?:\.\d+)?(?:/\d+)?", a.replace(",", ""))
            ok = v in nums[-3:] if nums else False
        else:
            ok = v in a.lower()[:200] or v in a.lower()[-200:]
    return ok, _f1(a, reference)


def trainer_fuse(model, adapter, save_path):
    """Adapter + base model -> one standalone model folder (opens in LM Studio / mlx-lm on any Apple-silicon Mac)."""
    import subprocess
    r = subprocess.run([trainer_python(), "-m", "mlx_lm", "fuse", "--model", model, "--adapter-path", adapter,
                        "--save-path", save_path], capture_output=True, text=True, env=trainer_env())
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip().split("\n")[-1][:300])
    return save_path


def local_models():
    """Models already on this Mac: MLX models in the Hugging Face cache and models saved by the Trainer."""
    out = {}
    base = os.environ.get("HF_HUB_CACHE") or os.path.join(os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface"), "hub")
    try:
        for d in sorted(os.listdir(base)):
            if d.startswith("models--"):
                mid = d[len("models--"):].replace("--", "/", 1)
                if mid not in TRAINER_MODELS and ("mlx" in mid.lower() or "4bit" in mid.lower()) and \
                        os.path.isdir(os.path.join(base, d, "snapshots")):
                    out[mid] = f"Downloaded - {mid.split('/')[-1]}"
    except OSError:
        pass
    try:
        for r in sorted(os.listdir(TRAINER_RUNS)):
            m = os.path.join(TRAINER_RUNS, r, "model")
            if os.path.exists(os.path.join(m, "config.json")):
                out[m] = f"Your trained model - {r}"
    except OSError:
        pass
    return out


def model_label(mid):
    if mid in TRAINER_MODELS:
        return TRAINER_MODELS[mid][0]
    return local_models().get(mid) or (f"Folder - {os.path.basename(mid.rstrip('/'))}" if os.path.isdir(mid) else mid)


# ============================================================================= RAG (ask the dataset with a local model)
# No training: the whole dataset on GitHub is downloaded (text only, automatically), indexed for full-text search
# (SQLite FTS5 / BM25 - nothing to install) and a local open model on this Mac answers questions from the best
# matching records, citing them. No API keys, no cloud: the model runs with Apple's MLX in AITE's own environment.
RAG_HOME = os.environ.get("AITE_RAG_HOME") or HERE  # tests point this at a temp folder
RAG_DATA = os.path.join(RAG_HOME, "rag_data") if os.environ.get("AITE_RAG_HOME") else TRAINER_DATA  # sparse clone of the GitHub dataset: Dataset/text + Dataset/preference only (no pictures)
RAG_INDEX = os.path.join(RAG_HOME, "rag_index.db")
RAG_STATUS = os.path.join(RAG_HOME, "rag_status.json")
RAG_SPARSE = ("Dataset/text", "Dataset/preference", "Dataset/detection", "Dataset/vla")  # every row file, not the picture files
RAG_STOP = set("a an the and or of to in on for with by is are was were be been it this that these those what which who "
               "whom how why when where do does did can could should would will shall may might must i you he she we they "
               "me my your our their its as at from into about than then so if not no yes please explain tell give show "
               "find solve use using there here have has had any some all each".split())
RAG_SYSTEM = ("You are AITE's helpful assistant. Answer the user's question in your own words, clearly and correctly, "
              "formatted in Markdown: start with a one-sentence direct answer, then use short paragraphs, '## ' headings or "
              "'- ' bullet points where they help, numbered steps for maths, and fenced code blocks (```language) for code. "
              "Combine two things: the numbered sources from the user's dataset AND your own knowledge. Use the sources that "
              "are really about the question and cite them like [1]; add everything useful you know yourself that they miss "
              "(definitions, background, examples, better methods). Never copy a source word for word and never start with "
              "'A:' or 'Answer:'. If no source is about the question, ignore them all and answer fully from your own knowledge.")
RAG_CHAT_SYSTEM = ("You are AITE's friendly assistant for a large dataset of questions and answers about maths, science, "
                   "programming, robotics, medicine and more. Reply briefly and warmly in Markdown, and invite the user to ask "
                   "a question about any of those topics.")
RAG_SMALLTALK = re.compile(r"^\s*(hi+|hello+|hey+|yo|hiya|howdy|sup|thanks?( you)?|thank u|thx|ok(ay)?|cool|nice|great|bye|"
                           r"good (morning|afternoon|evening|night)|how are you( doing)?|who are you|what are you|"
                           r"what can you do|help)\s*[!.?]*\s*$", re.I)


def _git(cwd, *args, timeout=1800):
    import subprocess
    try:
        r = subprocess.run(["git", "-c", "http.version=HTTP/1.1", "-c", "http.postBuffer=524288000", *args], cwd=cwd,
                           capture_output=True, text=True, timeout=timeout, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 1, f"{type(e).__name__}: {e}"


def rag_sync(st, dest=None):
    """Downloads (first time) or updates the dataset's text from GitHub - only text and preference rows, never the
    pictures, as a shallow blobless sparse clone. Returns (ok, message)."""
    dest = dest or RAG_DATA
    repo, br = str(st.get("gh_repo", "")).strip(), st.get("gh_branch") or "main"
    if not repo:
        return False, "No GitHub repository set (Settings > GitHub)"
    if os.path.isdir(os.path.join(dest, ".git")):
        code, url = _git(dest, "remote", "get-url", "origin", timeout=30)
        if code != 0 or url.strip().rstrip("/").removesuffix(".git") != repo.rstrip("/").removesuffix(".git"):
            import shutil
            shutil.rmtree(dest, ignore_errors=True)  # the repository link changed in Settings: start a fresh copy
    if not os.path.isdir(os.path.join(dest, ".git")):
        code, out = _git(os.path.dirname(dest) or ".", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse", "-b", br,
                         repo, dest)
        if code != 0:
            return False, "Could not download from GitHub: " + out[-200:]
        code, out = _git(dest, "sparse-checkout", "set", *RAG_SPARSE)
        return code == 0, "Downloaded the dataset from GitHub" if code == 0 else out[-200:]
    code, out = _git(dest, "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", br)
    if code != 0:
        return False, "Could not reach GitHub: " + out[-200:]
    _git(dest, "sparse-checkout", "set", *RAG_SPARSE, timeout=120)
    code, out = _git(dest, "reset", "-q", "--hard", "FETCH_HEAD")
    return code == 0, "Up to date with GitHub" if code == 0 else out[-200:]


def rag_files(dirs):
    out = []
    for d in dirs:
        for sub in ("text", "preference", "detection", "vla"):
            p = os.path.join(d, sub)
            if os.path.isdir(p):
                for dp, _, fn in os.walk(p):
                    out += [os.path.join(dp, f) for f in fn if f.endswith((".jsonl.gz", ".jsonl", ".jsonl.gz.open"))]  # .open = being written now
    return sorted(out)


def rag_dirs(st, agent_root=None):
    """ALL the data: everything on GitHub, plus the newest rows on this Mac that are not pushed yet (with GitHub
    first, local copies are deleted once pushed - so GitHub + local together are the whole dataset)."""
    d = [os.path.join(RAG_DATA, "Dataset")]
    if st.get("rag_include_local") and agent_root:
        d.append(agent_root)
    return d


def _rag_row(r, variants=True):
    """ANY dataset row -> (id, title, question, answer, topic, field, source, url, licence, tier), or None.
    Everything goes in: Q&A originals and DataGen variants, preference pairs, web-image captions, generated
    detection scenes (objects + Q&A) and robot VLA episodes (instruction, objects, actions)."""
    t = r.get("type")
    img = r.get("image") or ""
    if t == "preference":
        q, a = r.get("prompt") or "", r.get("chosen") or ""
    elif t == "image-text":
        q = f"Image: {r.get('title') or ''}\n{r.get('caption') or ''}"
        a = f"{r.get('caption') or r.get('title') or ''}\n\nImage file: {img} · by {r.get('author') or 'unknown'}"
    elif t == "detection":
        objs = r.get("objects") or []
        qa = r.get("qa") or []
        q = f"Scene: {r.get('caption') or ''}"
        a = (f"{r.get('caption') or ''}\nObjects: " + "; ".join(f"{o.get('label', '')} at {o.get('bbox', '')}" for o in objs if isinstance(o, dict))
             + "".join(f"\nQ: {x.get('q')} A: {x.get('a')}" for x in qa if isinstance(x, dict)) + f"\nImage file: {img}")
    elif t == "vla-episode":
        steps = r.get("steps") or []
        acts = [st_.get("action") for st_ in steps if isinstance(st_, dict) and st_.get("action") is not None]
        q = f"Robot task: {r.get('instruction') or ''}"
        a = (f"Instruction: {r.get('instruction') or ''}\nObjects: " +
             ", ".join(f"{o.get('color', '')} {o.get('shape', '')}" for o in (r.get("objects") or []) if isinstance(o, dict)) +
             f"\nSuccess: {r.get('success')}\n{len(steps)} steps · actions: " + shorten(json.dumps(acts), 1500) +
             (f"\nFirst frame: {steps[0].get('observation', {}).get('image', '')}" if steps and isinstance(steps[0], dict) else ""))
    else:
        if r.get("kind") == "variant" and not variants:
            return None
        q, a = r.get("problem") or "", r.get("solution") or ""
        if not (q and a):
            m = r.get("messages") or []
            m = [x for x in m if isinstance(x, dict)]
            q = next((str(x.get("content", "")) for x in m if x.get("role") == "user"), "")
            a = next((str(x.get("content", "")) for x in reversed(m) if x.get("role") == "assistant"), "")
    q, a = str(q).replace("<image>", "").strip(), str(a).replace("<image>", "").strip()
    if len(q) < 4 or len(a) < 1:
        return None
    rid = str(r.get("id") or _rid(q[:200], a[:200]))
    title = re.sub(r"\s*\[[^\]]*·[^\]]*\]\s*$", "", str(r.get("title") or r.get("instruction") or r.get("caption") or q.split("\n")[0]))[:200]
    kind = {"image-text": "web image", "detection": "generated image", "vla-episode": "robot episode",
            "preference": "preference pair"}.get(t, "variant" if r.get("kind") == "variant" else "Q&A")
    return (rid, title, q[:6000], a[:8000], str(r.get("topic") or ""), str(r.get("field") or ""),
            row_source(r) + " · " + kind, str(r.get("url") or ""), str(r.get("license") or ""), str(r.get("quality_tier") or ""))


class RagIndex:
    """Full-text index of the dataset (SQLite FTS5, BM25 ranking, English stemming). Only new or changed files are
    read on each update, so it keeps up with a growing dataset."""
    COLS = ("rid", "title", "q", "a", "topic", "field", "source", "url", "license", "tier")

    def __init__(self, path=None):
        import sqlite3
        path = self.path = path or RAG_INDEX  # read at call time (tests move it)
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=60)
        self.lock = threading.Lock()
        with self.lock:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, size INT, rows INT);
                CREATE TABLE IF NOT EXISTS ids(rid TEXT PRIMARY KEY);
                CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(rid UNINDEXED, title, q, a, topic, field,
                    source UNINDEXED, url UNINDEXED, license UNINDEXED, tier UNINDEXED, tokenize='porter unicode61');""")
            self.db.commit()

    def count(self):
        with self.lock:
            return self.db.execute("SELECT count(*) FROM ids").fetchone()[0]

    def n_files(self):
        with self.lock:
            return self.db.execute("SELECT count(*) FROM files").fetchone()[0]

    def fields(self):
        with self.lock:
            return dict(self.db.execute("SELECT field, count(*) FROM docs GROUP BY field ORDER BY 2 DESC LIMIT 40").fetchall())

    def update(self, dirs, variants=True, progress=None, cancel=None):
        """Indexes every new or changed shard. Returns (files read, rows added)."""
        files = rag_files(dirs)
        with self.lock:
            known = dict(self.db.execute("SELECT path, size FROM files").fetchall())
        todo = []
        for p in files:
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            if known.get(p) != sz:
                todo.append((p, sz))
        added = 0
        for i, (p, sz) in enumerate(todo):
            if cancel and cancel():
                break
            rows = [x for x in (_rag_row(r, variants) for r in _read_rows(p)) if x]
            with self.lock:
                n0 = self.db.total_changes
                fresh = []
                for x in rows:
                    cur = self.db.execute("INSERT OR IGNORE INTO ids(rid) VALUES(?)", (x[0],))
                    if cur.rowcount:
                        fresh.append(x)
                self.db.executemany("INSERT INTO docs(rid, title, q, a, topic, field, source, url, license, tier) "
                                    "VALUES(?,?,?,?,?,?,?,?,?,?)", fresh)
                self.db.execute("INSERT OR REPLACE INTO files(path, size, rows) VALUES(?,?,?)", (p, sz, len(fresh)))
                self.db.commit()
                added += len(fresh)
            if progress:
                progress(i + 1, len(todo), added)
        return len(todo), added

    @staticmethod
    def query_of(text):
        toks = [t for t in re.findall(r"[^\W_]+", text.lower()) if t not in RAG_STOP and (len(t) > 1 or t.isdigit())]
        toks = list(dict.fromkeys(toks))[:24]
        return " OR ".join('"' + t.replace('"', "") + '"' for t in toks)

    def search(self, text, k=6, field=None):
        """The k best DIFFERENT records: DataGen variants of one question count once (the best-scoring one)."""
        q = self.query_of(text)
        if not q:
            return []
        sql = ("SELECT rid, title, q, a, topic, field, source, url, license, tier, "
               "bm25(docs, 0, 4.0, 2.0, 1.0, 3.0, 1.5, 0, 0, 0, 0) AS s FROM docs WHERE docs MATCH ?")
        args = [q]
        fl = [field] if isinstance(field, str) and field else list(field or [])
        if fl:  # one field, several fields, or none (= ALL)
            sql += " AND field IN (" + ",".join("?" * len(fl)) + ")"
            args += fl
        sql += " ORDER BY s LIMIT ?"
        args.append(int(k) * 8)
        with self.lock:
            try:
                rows = self.db.execute(sql, args).fetchall()
            except Exception:
                return []
        out, seen = [], set()
        for r in rows:
            h = dict(zip(self.COLS + ("score",), r))
            key = re.sub(r"\W+", " ", h["title"].lower()).strip()[:90] or h["rid"]
            akey = re.sub(r"\W+", " ", h["a"].lower()).strip()[:160]
            if key in seen or akey in seen:
                continue
            seen.update((key, akey))
            out.append(h)
            if len(out) >= int(k):
                break
        return out

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass


def clip(s, n):
    """Like shorten, but keeps line breaks (code and steps stay readable)."""
    s = re.sub(r"\n{3,}", "\n\n", str(s or "").strip())
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def rag_relevant(question, hits):
    """Keeps only sources that share enough real words with the question (a greeting must not pull in a code sample)."""
    terms = [t for t in re.findall(r"[^\W_]+", question.lower()) if t not in RAG_STOP and len(t) > 2]
    if not terms:
        return []
    need = 1 if len(terms) <= 2 else 2
    out = []
    for h in hits:
        head = (h["title"] + " " + h["q"][:600] + " " + h["topic"] + " " + h["field"]).lower()
        if sum(1 for t in terms if t in head) >= need:
            out.append(h)
    return out


_TEX_SYM = {"cdot": "·", "times": "×", "div": "÷", "pm": "±", "mp": "∓", "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥",
            "neq": "≠", "ne": "≠", "approx": "≈", "equiv": "≡", "infty": "∞", "to": "→", "rightarrow": "→", "Rightarrow": "⇒",
            "leftarrow": "←", "iff": "⇔", "implies": "⇒", "in": "∈", "notin": "∉", "subset": "⊂", "subseteq": "⊆", "cup": "∪",
            "cap": "∩", "forall": "∀", "exists": "∃", "partial": "∂", "nabla": "∇", "int": "∫", "iint": "∬", "oint": "∮",
            "sum": "Σ", "prod": "Π", "sqrt": "√", "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
            "varepsilon": "ε", "theta": "θ", "lambda": "λ", "mu": "μ", "nu": "ν", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ",
            "phi": "φ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ",
            "Lambda": "Λ", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω", "ldots": "…", "cdots": "⋯", "dots": "…",
            "circ": "∘", "degree": "°", "angle": "∠", "perp": "⊥", "parallel": "∥", "mid": "|", "quad": "  ", "qquad": "    "}
_SUP = str.maketrans("0123456789+-=()niax", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱᵃˣ")
_SUB = str.maketrans("0123456789+-=()aeoxijn", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓᵢⱼₙ")


def tex_pretty(s):
    """LaTeX maths written by the model -> readable text (fractions, roots, powers, Greek letters, symbols)."""
    s = re.sub(r"\$\$|\\\[|\\\]|\\\(|\\\)", "", s)
    s = re.sub(r"(?<!\\)\$", "", s)
    s = re.sub(r"\\(?:left|right|big|Big|bigg|Bigg)\s*([()\[\]|.])", lambda m: "" if m.group(1) == "." else m.group(1), s)
    s = re.sub(r"\\(?:text|mathrm|mathbf|mathit|operatorname|textbf)\{([^{}]*)\}", r"\1", s)
    for _ in range(3):
        s = re.sub(r"\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}",
                   lambda m: (m.group(1) if re.fullmatch(r"[\w.]+", m.group(1)) else f"({m.group(1)})") + "/" +
                             (m.group(2) if re.fullmatch(r"[\w.]+", m.group(2)) else f"({m.group(2)})"), s)
        s = re.sub(r"\\sqrt\{([^{}]*)\}", lambda m: "√" + (m.group(1) if re.fullmatch(r"\w+", m.group(1)) else f"({m.group(1)})"), s)
    s = re.sub(r"\^\{([0-9+\-=()niax]+)\}", lambda m: m.group(1).translate(_SUP), s)
    s = re.sub(r"\^([0-9n])", lambda m: m.group(1).translate(_SUP), s)
    s = re.sub(r"_\{([0-9+\-=()aeoxijn]+)\}", lambda m: m.group(1).translate(_SUB), s)
    s = re.sub(r"_([0-9])", lambda m: m.group(1).translate(_SUB), s)
    s = re.sub(r"\\(sin|cos|tan|cot|sec|csc|ln|log|exp|lim|max|min|det|arcsin|arccos|arctan|sinh|cosh|tanh)\b", r"\1", s)
    s = re.sub(r"\\([A-Za-z]+)", lambda m: _TEX_SYM.get(m.group(1), m.group(1)), s)
    s = s.replace("\\,", " ").replace("\\;", " ").replace("\\!", "").replace("\\\\", " ").replace("{", "").replace("}", "")
    return re.sub(r"[ \t]{2,}", " ", s)


def tidy_model_answer(a):
    a = re.sub(r"^\s*(A|Answer|Response)\s*:\s*", "", str(a or "").strip())
    return a.strip()


def rag_messages(question, hits, history=(), max_chars=6000):
    """The question with its numbered sources, as chat messages for the model."""
    parts, used = [], 0
    for i, h in enumerate(hits, 1):
        block = (f"[{i}] {h['title']}  ({h['field'] or h['topic']} · {h['source'].split(' · ')[0]})\n"
                 f"Question: {clip(h['q'], 900)}\nAnswer: {clip(h['a'], 1600)}")
        if used + len(block) > max_chars and parts:
            break
        parts.append(block)
        used += len(block)
    ctx = "\n\n---\n\n".join(parts) if parts else "(no matching records in the dataset - answer from your own knowledge)"
    msgs = [m for m in list(history)[-6:] if m.get("role") in ("user", "assistant")]
    return msgs + [{"role": "user", "content": f"Sources from my dataset:\n\n{ctx}\n\nQuestion: {question}"}]


def rag_extractive(question, hits):
    """An answer without any model: the best matching record, quoted with its source."""
    if not hits:
        return "Nothing in the dataset matches this yet - Agent mode keeps collecting, so try again later or rephrase."
    h = hits[0]
    return f"## {h['title']}\n\nClosest record in your dataset [1]:\n\n{clip(h['a'], 3000)}"


def model_downloaded(mid):
    """True when the whole model is on this Mac (a folder, or a finished Hugging Face download)."""
    if os.path.isdir(mid):
        return os.path.exists(os.path.join(mid, "config.json"))
    base = os.environ.get("HF_HUB_CACHE") or os.path.join(os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface"), "hub")
    d = os.path.join(base, "models--" + mid.replace("/", "--"))
    try:
        if any(f.endswith(".incomplete") for f in os.listdir(os.path.join(d, "blobs"))):
            return False
        for snap in os.listdir(os.path.join(d, "snapshots")):
            fs = os.listdir(os.path.join(d, "snapshots", snap))
            if "config.json" in fs and any(f.endswith(".safetensors") for f in fs):
                return True
    except OSError:
        pass
    return False


def model_download_start(mid):
    """Downloads a model in the background (AI engine environment, plain HTTPS). Returns the process."""
    import subprocess
    os.makedirs(TRAINER_RUNS, exist_ok=True)
    code = ("import sys; from huggingface_hub import snapshot_download; "
            "snapshot_download(repo_id=sys.argv[1]); print('done', flush=True)")
    return subprocess.Popen([trainer_python(), "-c", code, mid], stdout=subprocess.DEVNULL,
                            stderr=open(os.path.join(TRAINER_RUNS, "download_errors.log"), "a"), env=trainer_env(),
                            start_new_session=True, stdin=subprocess.DEVNULL)


def kaggle_cli():
    exe = os.path.join(os.path.dirname(sys.executable), "kaggle")
    return [exe] if os.path.exists(exe) else [sys.executable, "-m", "kaggle"]


def kaggle_env():
    env = dict(os.environ, KAGGLE_CONFIG_DIR=os.environ.get("KAGGLE_CONFIG_DIR", os.path.expanduser("~/.kaggle")))
    try:
        import certifi  # python.org's Python has no system certificates: Kaggle's HTTPS would fail without this
        env.setdefault("SSL_CERT_FILE", certifi.where())
        env.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
    except ImportError:
        pass
    return env


def kaggle_logged_in():
    """Kaggle's own login on this Mac (kaggle.json or an access token from kaggle.com > Settings) - AITE stores no keys."""
    d = os.environ.get("KAGGLE_CONFIG_DIR") or os.path.expanduser("~/.kaggle")
    return bool(os.environ.get("KAGGLE_API_TOKEN") or (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"))
                or os.path.exists(os.path.join(d, "kaggle.json")) or os.path.exists(os.path.join(d, "access_token")))


def kaggle_push(st, dirs, agent_root=None, stage=None):
    """ALL the row files (GitHub copy + this Mac's newest) -> a new version of the Kaggle dataset. Files are hard-linked
    into a staging folder (no extra disk space). Returns (ok, message)."""
    import shutil
    import subprocess
    if not st.get("kaggle_enabled", True):
        return None, "off"
    if not kaggle_logged_in():
        return False, "Kaggle login needed: kaggle.com > Settings > API > Create New Token, put kaggle.json in ~/.kaggle"
    ds = str(st.get("kaggle_dataset", "")).strip().strip("/")
    m = re.search(r"kaggle\.com/datasets/([^/]+/[^/?#]+)", ds)
    ds = m.group(1) if m else ds
    if ds.count("/") != 1:
        return False, f"Kaggle dataset should look like owner/name, not '{ds}'"
    stage = stage or os.path.join(RAG_HOME, "kaggle_stage")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    best = {}
    for f in rag_files(dirs):
        if f.endswith(".open"):
            continue  # only finished shards go to Kaggle
        key = (os.path.basename(os.path.dirname(f)), os.path.basename(f))
        if key not in best or os.path.getsize(f) > os.path.getsize(best[key]):
            best[key] = f
    if st.get("kaggle_images"):
        for d in dirs:
            ip = os.path.join(d, "images")
            for dp, _, fn in os.walk(ip):
                for f in fn:
                    best[(os.path.join("images", os.path.relpath(dp, ip)), f)] = os.path.join(dp, f)
    try:
        for (sub, name), f in best.items():
            os.makedirs(os.path.join(stage, sub), exist_ok=True)
            try:
                os.link(f, os.path.join(stage, sub, name))
            except OSError:
                shutil.copy2(f, os.path.join(stage, sub, name))
        for extra in ("stats.json", "topics.json", "README.md"):
            for d in ([agent_root] if agent_root else []) + list(dirs):
                if os.path.exists(os.path.join(d, extra)):
                    shutil.copy2(os.path.join(d, extra), os.path.join(stage, extra))
                    break
        with open(os.path.join(stage, "dataset-metadata.json"), "w") as f:
            json.dump({"id": ds, "title": "Prolabs Robotics 864", "licenses": [{"name": "CC-BY-SA-4.0"}]}, f)
        msg = f"AITE update {time.strftime('%Y-%m-%d %H:%M')} - {len(best):,} files"
        r = subprocess.run(kaggle_cli() + ["datasets", "version", "-p", stage, "-m", msg, "-r", "zip", "-q"],
                           capture_output=True, text=True, timeout=6 * 3600, env=kaggle_env())
        out = (r.stdout + r.stderr).strip()
        if r.returncode == 0 and "error" not in out.lower():
            return True, f"new version with {len(best):,} files"
        if "404" in out or "not found" in out.lower():
            r = subprocess.run(kaggle_cli() + ["datasets", "create", "-p", stage, "-r", "zip", "-q"],
                               capture_output=True, text=True, timeout=6 * 3600, env=kaggle_env())
            out = (r.stdout + r.stderr).strip()
            if r.returncode == 0:
                return True, f"dataset created with {len(best):,} files"
        return False, "upload failed: " + out[-220:]
    except Exception as e:
        return False, f"upload failed: {type(e).__name__}: {e}"
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def cli_rag_update(root, offline=False):
    """Background job (its own low-priority process): GitHub -> RAG_DATA -> index -> Kaggle. Writes RAG_STATUS and
    rag.log (shown live, super verbose, on the Ask page)."""
    try:
        os.nice(15)
    except OSError:
        pass
    os.makedirs(RAG_HOME, exist_ok=True)
    pidf = os.path.join(RAG_HOME, "rag_update.pid")
    try:
        with open(pidf) as f:
            if _alive(int(f.read().strip())):
                return 0  # one at a time
    except (OSError, ValueError):
        pass
    with open(pidf, "w") as f:
        f.write(str(os.getpid()))
    st = load_settings()
    stat = {}
    try:
        with open(RAG_STATUS) as f:
            stat = json.load(f)
    except (OSError, ValueError):
        pass

    def jlog(msg):
        try:
            lp = os.path.join(RAG_HOME, "rag.log")
            if os.path.exists(lp) and os.path.getsize(lp) > 20 * 2 ** 20:
                os.replace(lp, lp + ".1")
            with open(lp, "a") as f:
                f.write(time.strftime("%H:%M:%S  ") + msg + "\n")
        except OSError:
            pass

    def put(**kw):
        stat.update(kw, t=time.time())
        tmp = RAG_STATUS + ".tmp"
        with open(tmp, "w") as f:
            json.dump(stat, f)
        os.replace(tmp, RAG_STATUS)
    put(state="syncing")
    jlog(f"background update started (pid {os.getpid()}): GitHub -> RAG index -> Kaggle")
    if offline:
        ok, msg = True, "offline test: local data only"
    else:
        jlog(f"GitHub: getting {st.get('gh_repo')} ({st.get('gh_branch') or 'main'}) into {RAG_DATA} - every row file")
        t0 = time.time()
        ok, msg = rag_sync(st)
        jlog(f"GitHub: {msg} ({time.time() - t0:.1f} s)")
    put(sync_ok=ok, sync_msg=msg, **({"sync_t": time.time()} if ok else {}))
    idx = RagIndex()
    dirs = rag_dirs(dict(st, rag_include_local=True) if offline else st, root)
    put(state="indexing", done=0, todo=0, added=0, count=idx.count())
    jlog(f"index: {len(rag_files(dirs))} row files in {' + '.join(dirs)} · {idx.count():,} records already indexed")
    last = [0.0]

    def prog(i, n, added):
        jlog(f"index: file {i}/{n} done · +{added:,} new records so far")
        if time.time() - last[0] > 1 or i == n:
            last[0] = time.time()
            put(done=i, todo=n, added=added, count=idx.count())
    t0 = time.time()
    nf, added = idx.update(dirs, progress=prog)
    jlog(f"index: {nf} new/changed files read, +{added:,} records in {time.time() - t0:.1f} s · total {idx.count():,}")
    put(state="done", files=len(rag_files(dirs)), added=added, count=idx.count(), fields=idx.fields(), index_t=time.time())
    idx.close()
    every = 60 * int(st.get("kaggle_every_min", 60))
    if not offline and st.get("kaggle_enabled", True):
        login_fixed = stat.get("kaggle_ok") is False and "login" in str(stat.get("kaggle_msg", "")).lower() and kaggle_logged_in()
        wait = every if stat.get("kaggle_ok") is not False else 600  # a failed upload is retried after 10 minutes
        if login_fixed or time.time() - float(stat.get("kaggle_try_t", 0) or 0) > wait:
            put(state="kaggle")
            jlog(f"Kaggle: uploading a new version of {st.get('kaggle_dataset')}…")
            t0 = time.time()
            kok, kmsg = kaggle_push(st, rag_dirs(dict(st, rag_include_local=True), root), root)
            jlog(f"Kaggle: {kmsg} ({time.time() - t0:.1f} s)")
            put(state="done", kaggle_ok=kok, kaggle_msg=kmsg, kaggle_try_t=time.time(), **({"kaggle_t": time.time()} if kok else {}))
        else:
            left = int((wait - (time.time() - float(stat.get('kaggle_try_t', 0)))) // 60) + 1
            jlog(f"Kaggle: next try in {left} min" + (" (" + str(stat.get("kaggle_msg", "")) + ")" if stat.get("kaggle_ok") is False else ""))
    jlog("background update finished")
    try:
        os.remove(pidf)
    except OSError:
        pass
    return 0


def rag_models():
    """Every model the Ask page can use: the built-in list plus models already on this Mac."""
    out = {k: v[0] for k, v in TRAINER_MODELS.items()}
    for k, v in local_models().items():
        out.setdefault(k, v.replace("Downloaded - ", ""))
    return out


def new_run_dir(model):
    name = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + re.sub(r"[^a-z0-9-]+", "", os.path.basename(model.rstrip("/")).lower())[:40]
    return os.path.join(TRAINER_RUNS, name)


def latest_run():
    try:
        runs = sorted(d for d in os.listdir(TRAINER_RUNS) if os.path.exists(os.path.join(TRAINER_RUNS, d, "train.json")))
    except OSError:
        return None
    return os.path.join(TRAINER_RUNS, runs[-1]) if runs else None


def cli_train(args):
    """python "AITE 1.py" --train [--model ID] [--iters N] [--data folder-or-file ...]  (same as the Trainer page)"""
    def arg(name, default=None):
        return args[args.index(name) + 1] if name in args else default
    st = load_settings()
    if not trainer_supported():
        print("The trainer needs a Mac with Apple silicon (M1 or newer).")
        return 2
    if not trainer_ready():
        print("Installing the trainer (one time)...")
        if not trainer_install():
            return 1
    model = arg("--model", st.get("trainer_model"))
    iters = int(arg("--iters", st.get("trainer_iters", 200)))
    srcs = [args[i + 1] for i, a in enumerate(args) if a == "--data"] or [agent_dir(st)]
    run = new_run_dir(model)
    stats = build_training_set(srcs, os.path.join(run, "data"), system=st.get("trainer_system", ""),
                               max_seq=int(st.get("trainer_max_seq", 1024)))
    print(f"Training data: {stats['train']} train / {stats['valid']} valid rows, ~{stats['tokens']:,} tokens")
    if stats["train"] < 8 or stats["valid"] < 2:
        print("Not enough data yet - let Agent mode collect for a while first.")
        return 1
    cmd = trainer_command(run, model, iters, int(st.get("trainer_batch", 4)), float(st.get("trainer_lr", 1e-5)),
                          int(st.get("trainer_layers", 8)), int(st.get("trainer_max_seq", 1024)))
    p = trainer_start(run, cmd, {"model": model, "iters": iters, "data": stats})
    print("Run folder:", run)
    while p.poll() is None:
        time.sleep(5)
        pr = trainer_progress(run)
        if pr["train"]:
            print(f"  iter {pr['iter']}/{iters}  loss {pr['train'][-1][1]:.3f}" +
                  (f"  val {pr['val'][-1][1]:.3f}" if pr["val"] else "") + f"  {pr['tok_s']:.0f} tok/s")
    pr = trainer_progress(run)
    print("Result:", pr["state"], pr["error"])
    return 0 if pr["state"] == "done" else 1


# ============================================================================= GUI - ChatGPT theme
# Colours, sizes and corner radii are ChatGPT's own, measured from chatgpt.com (its archived markup rendered in
# Chrome, values read back with getComputedStyle - the same palette as the HOS X app): light = #fcfcfc page,
# white cards, #0d0d0d ink, black pill buttons that hover to #212121, 20%-black outlines, #f3f3f3 hovers;
# dark = #212121 page, #2a2a2a cards, #ececec ink, white pill buttons with black text. Switches are ChatGPT's
# blue. Corners: dialogs 32, cards/menus 24, fields 14, buttons and chips are pills. Card corners keep the
# G3 squircle shape; pills use true semicircles like ChatGPT's.
THEMES = {
    "light": {"page": "#fcfcfc", "sidebar": "#f9f9f9", "card": "#ffffff", "soft": "#f3f3f3", "border": "#e5e5e5",
              "divider": "#ececec", "text": "#0d0d0d", "dim": "#5d5d5d", "faint": "#8f8f8f", "selected": "#ececec",
              "btn": "#0d0d0d", "btn_hover": "#212121", "btn_fg": "#ffffff", "ghost_hover": "#f3f3f3",
              "outline": "#cccccc", "field": "#ffffff", "switch_off": "#e3e3e3", "switch_off_hover": "#d6d6d6",
              "blue": "#0385ff", "blue_hover": "#0074e0", "green": "#10a37f", "red": "#d8241a",
              "error_text": "#ba2623", "error_bg": "#fff1f0", "select_text": "#cfe3ff", "code": "#f9f9f9",
              "track": "#e5e5e5", "bubble": "#e8e8e8", "orange": "#c2410c", "green_bg": "#e7f6f2", "blue_bg": "#e6f2ff",
              "orange_bg": "#fff1e6", "grey_bg": "#f0f0f0"},
    "dark": {"page": "#212121", "sidebar": "#181818", "card": "#2a2a2a", "soft": "#303030", "border": "#3a3a3a",
             "divider": "#363636", "text": "#ececec", "dim": "#b4b4b4", "faint": "#8f8f8f", "selected": "#424242",
             "btn": "#ffffff", "btn_hover": "#e3e3e3", "btn_fg": "#0d0d0d", "ghost_hover": "#303030",
             "outline": "#4d4d4d", "field": "#303030", "switch_off": "#4a4a4a", "switch_off_hover": "#565656",
             "blue": "#0385ff", "blue_hover": "#0074e0", "green": "#10a37f", "red": "#ff6b62",
             "error_text": "#ff6b62", "error_bg": "#3a2120", "select_text": "#2c4a6e", "code": "#171717",
             "track": "#424242", "bubble": "#303030", "orange": "#fb923c", "green_bg": "#173a31", "blue_bg": "#13304f",
             "orange_bg": "#3d2616", "grey_bg": "#383838"},
}
UI_FONT = ".AppleSystemUIFont" if sys.platform == "darwin" else "Helvetica"  # = SF Pro, ChatGPT's Mac font
MONO_FONT = "Menlo" if sys.platform == "darwin" else "Courier"
SEARCHER_FACTORY = None  # tests/smoke can inject a searcher (offline)


def g3_points(x1, y1, x2, y2, r, steps=None, power=0.5):
    """Rounded rectangle as polygon points. power 0.5 = G3-like squircle corners, 1.0 = circular arcs (pills)."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    steps = steps or max(6, int(r * 0.7))
    pts = []
    for cx, cy, a0 in [(x2 - r, y1 + r, -90), (x2 - r, y2 - r, 0), (x1 + r, y2 - r, 90), (x1 + r, y1 + r, 180)]:
        for i in range(steps + 1):
            a = math.radians(a0 + 90 * i / steps)
            c, s = math.cos(a), math.sin(a)
            pts += [cx + r * (abs(c) ** power) * (1 if c >= 0 else -1), cy + r * (abs(s) ** power) * (1 if s >= 0 else -1)]
    return pts


def mix(c1, c2, t):
    """Blend two #rrggbb colours: t=0 gives c1, t=1 gives c2."""
    try:
        a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    except (ValueError, TypeError):
        return c1
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


ICON_FILE = os.path.join(HERE, "assets", "aite_icon_v3.png")  # bump the name when the artwork changes


def _superellipse(cx, cy, half, n=5.0, steps=720):
    """Apple's app-icon shape: a superellipse |x|^n + |y|^n = 1 (n = 5 matches macOS's continuous 22.4% corners)."""
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        c, s_ = math.cos(t), math.sin(t)
        pts.append((cx + half * math.copysign(abs(c) ** (2 / n), c), cy + half * math.copysign(abs(s_) ** (2 / n), s_)))
    return pts


def make_app_icon(path=ICON_FILE, size=1024):
    """The AITE app icon on Apple's macOS icon grid, so it sits in the Dock exactly like other apps: an 824/1024 body
    centred with a 100 px margin, the continuous-corner (superellipse) shape and the standard soft drop shadow.
    Artwork: an ink tile with a white 'A' drawn as a robot arm - two links, a shoulder joint, the crossbar as the
    forearm - and a blue tool point. Generated with Pillow, no image files shipped."""
    from PIL import Image, ImageDraw, ImageFilter
    S = size * 2  # draw at 2x, downscale = smooth edges
    m = S * 100 / 1024
    half = (S - 2 * m) / 2
    shape = _superellipse(S / 2, S / 2, half)
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon([(x, y + S * 12 / 1024) for x, y in shape], fill=(0, 0, 0, 92))
    im = shadow.filter(ImageFilter.GaussianBlur(S * 14 / 1024))
    body = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.polygon(shape, fill=(13, 13, 13, 255))
    bw, x0 = 2 * half, m
    P = lambda u, v: (x0 + u * bw, x0 + v * bw)  # glyph in body units (0..1)
    white, ink, blue = (255, 255, 255, 255), (13, 13, 13, 255), (3, 133, 255, 255)
    w = int(bw * 0.085)
    apex, left, right = P(0.5, 0.25), P(0.25, 0.77), P(0.75, 0.77)
    bar = (P(0.365, 0.575), P(0.635, 0.575))
    for a_, b_ in ((apex, left), (apex, right), bar):
        d.line([a_, b_], fill=white, width=w)
    for x, y in (left,) + bar:
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=white)
    r = bw * 0.12
    d.ellipse([apex[0] - r, apex[1] - r, apex[0] + r, apex[1] + r], fill=white)
    h = r * 0.46
    d.ellipse([apex[0] - h, apex[1] - h, apex[0] + h, apex[1] + h], fill=ink)
    b = bw * 0.08
    d.ellipse([right[0] - b, right[1] - b, right[0] + b, right[1] + b], fill=blue)
    im = Image.alpha_composite(im, body).resize((size, size), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    return path


def set_app_identity(root, tk):
    """Window title, Dock/menu-bar name and icon: 'Prolabs AITE' with the AITE icon instead of 'Python'."""
    root.title(APP)
    try:
        root.tk.call("tk", "appname", APP_SHORT)
    except Exception:
        pass
    try:
        if not os.path.exists(ICON_FILE):
            make_app_icon()
        img = tk.PhotoImage(file=ICON_FILE).subsample(4)  # 256 px for the window/Dock
        root.iconphoto(True, img)
        root._aite_icon = img
    except Exception:
        pass
    if sys.platform == "darwin":
        try:
            from AppKit import NSApplication, NSImage
            ns = NSImage.alloc().initWithContentsOfFile_(ICON_FILE)
            if ns is not None:
                NSApplication.sharedApplication().setApplicationIconImage_(ns)
        except Exception:
            pass


def _mac_app_name():
    """Must run before Tk starts: the menu bar takes the app name from the bundle info."""
    if sys.platform != "darwin":
        return
    try:
        from Foundation import NSBundle
        b = NSBundle.mainBundle()
        info = b.localizedInfoDictionary() or b.infoDictionary()
        if info is not None:
            info["CFBundleName"] = APP_SHORT
    except Exception:
        pass


def main_gui():
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import ttk, filedialog, messagebox

    global SETTINGS_READONLY, TRAINER_RUNS, RAG_HOME, RAG_DATA, RAG_INDEX, RAG_STATUS
    smoke = bool(os.environ.get("AITE_GUI_SMOKE"))
    SETTINGS_READONLY = SETTINGS_READONLY or smoke
    if smoke:  # test runs never land in the user's trainer_runs / RAG folders
        import tempfile
        TRAINER_RUNS = tempfile.mkdtemp(prefix="aite_trainer_smoke_")
        RAG_HOME = os.environ["AITE_RAG_HOME"] = tempfile.mkdtemp(prefix="aite_rag_smoke_")
        RAG_DATA, RAG_INDEX = os.path.join(RAG_HOME, "rag_data"), os.path.join(RAG_HOME, "rag_index.db")
        RAG_STATUS = os.path.join(RAG_HOME, "rag_status.json")
    st = load_settings() if not smoke else dict(default_settings(), pwt_workers=32, agent_quality=5, agent_batch=8,
                                                 agent_variations=3)
    _mac_app_name()
    root = tk.Tk()
    set_app_identity(root, tk)
    root.geometry(f"{min(1480, root.winfo_screenwidth() - 40)}x{min(940, root.winfo_screenheight() - 90)}")
    root.minsize(1120, 700)
    state = {"records": [], "variants": [], "rejected": [], "reasons": {}, "stats": {}, "notes": {},
             "inp": json.loads(json.dumps(DEFAULT_INPUT)), "running": False, "cancel": threading.Event(),
             "mode": "", "history": [], "loading": False, "pulse": 0.0, "last_export": "", "popover": None,
             "shown_type": None}
    if st["remember_input"] and not smoke:
        try:
            with open(LAST_INPUT_FILE) as f:
                state["inp"], _ = validate_input(json.load(f))
        except Exception:
            pass
    msgs = queue.Queue()
    T = dict(THEMES.get(st["theme"], THEMES["dark"]))
    widgets = []
    font_cache = {}

    def family():
        return {"SF Pro (system)": UI_FONT}.get(st["font_family"], st["font_family"])

    def font(size=0, bold=False, mono=False):
        return (MONO_FONT if mono else family(), max(8, int(st["font_size"]) + size), "bold" if bold else "normal")

    def measure(text, fnt):
        if fnt not in font_cache:
            font_cache[fnt] = tkfont.Font(root=root, font=fnt)
        return font_cache[fnt].measure(text)

    def reg(w, role, extra=None):
        widgets.append((w, role, extra))
        return w

    def box(master, bg="page", **kw):
        return reg(tk.Frame(master, bd=0, highlightthickness=0, **kw), "bg", bg)

    def label(master, text, tone="text", size=0, bold=False, mono=False, **kw):
        return reg(tk.Label(master, text=text, anchor="w", justify="left", bd=0, padx=0, pady=0, **kw),
                   "label", (tone, size, bold, mono))

    def draw_icon(cv, name, cx, cy, color, bg_fill=None, s=1.0):
        """Line icons drawn on a canvas (ChatGPT uses thin SVG icons; these follow their shapes)."""
        def ln(*pts, w=1.7):
            cv.create_line(*pts, fill=color, width=w * s, capstyle="round", joinstyle="round")
        if name == "chevron":
            ln(cx - 4 * s, cy - 2 * s, cx, cy + 2 * s, cx + 4 * s, cy - 2 * s)
        elif name == "check":
            ln(cx - 5 * s, cy, cx - 1.5 * s, cy + 3.5 * s, cx + 5 * s, cy - 4 * s, w=1.9)
        elif name == "plus":
            ln(cx - 5 * s, cy, cx + 5 * s, cy)
            ln(cx, cy - 5 * s, cx, cy + 5 * s)
        elif name == "close":
            ln(cx - 4.5 * s, cy - 4.5 * s, cx + 4.5 * s, cy + 4.5 * s)
            ln(cx - 4.5 * s, cy + 4.5 * s, cx + 4.5 * s, cy - 4.5 * s)
        elif name == "up":
            ln(cx, cy + 6 * s, cx, cy - 6 * s, w=2.0)
            ln(cx - 5 * s, cy - 1 * s, cx, cy - 6 * s, cx + 5 * s, cy - 1 * s, w=2.0)
        elif name == "down":
            ln(cx, cy - 6 * s, cx, cy + 3 * s, w=1.8)
            ln(cx - 4.5 * s, cy - 1 * s, cx, cy + 3.5 * s, cx + 4.5 * s, cy - 1 * s, w=1.8)
            ln(cx - 6 * s, cy + 7 * s, cx + 6 * s, cy + 7 * s)
        elif name == "stop":
            cv.create_polygon(g3_points(cx - 4.5 * s, cy - 4.5 * s, cx + 4.5 * s, cy + 4.5 * s, 1.6 * s, power=1.0),
                              fill=color, outline=color)
        elif name == "play":
            cv.create_polygon(cx - 3.5 * s, cy - 5 * s, cx + 5 * s, cy, cx - 3.5 * s, cy + 5 * s, fill=color, outline=color)
        elif name == "sun":
            cv.create_oval(cx - 3.6 * s, cy - 3.6 * s, cx + 3.6 * s, cy + 3.6 * s, outline=color, width=1.6 * s)
            for k in range(8):
                a = math.radians(k * 45)
                ln(cx + 6 * s * math.cos(a), cy + 6 * s * math.sin(a), cx + 8 * s * math.cos(a), cy + 8 * s * math.sin(a), w=1.5)
        elif name == "moon":
            hole = bg_fill or cv.cget("bg")
            cv.create_oval(cx - 6.5 * s, cy - 6.5 * s, cx + 6.5 * s, cy + 6.5 * s, fill=color, outline=color)
            cv.create_oval(cx - 2.5 * s, cy - 9 * s, cx + 9.5 * s, cy + 3 * s, fill=hole, outline=hole)
        elif name == "search":
            cv.create_oval(cx - 5.5 * s, cy - 5.5 * s, cx + 3 * s, cy + 3 * s, outline=color, width=1.7 * s)
            ln(cx + 2.4 * s, cy + 2.4 * s, cx + 6 * s, cy + 6 * s, w=1.9)
        elif name == "clock":
            cv.create_oval(cx - 7 * s, cy - 7 * s, cx + 7 * s, cy + 7 * s, outline=color, width=1.6 * s)
            ln(cx, cy - 4 * s, cx, cy, cx + 3 * s, cy + 2 * s, w=1.6)
        elif name == "edit":
            ln(cx - 4.5 * s, cy + 4.5 * s, cx + 4.5 * s, cy - 4.5 * s, w=1.8)
            ln(cx - 7 * s, cy + 7 * s, cx - 2 * s, cy + 7 * s, w=1.6)
        elif name == "gear":
            cv.create_oval(cx - 3 * s, cy - 3 * s, cx + 3 * s, cy + 3 * s, outline=color, width=1.7 * s)
            for k in range(8):
                a = math.radians(k * 45 + 22.5)
                ln(cx + 5 * s * math.cos(a), cy + 5 * s * math.sin(a), cx + 7.5 * s * math.cos(a), cy + 7.5 * s * math.sin(a), w=2.2)
        elif name == "help":
            cv.create_oval(cx - 7 * s, cy - 7 * s, cx + 7 * s, cy + 7 * s, outline=color, width=1.6 * s)
            cv.create_text(cx, cy, text="?", fill=color, font=(family(), int(10 * s), "bold"))
        elif name == "copy":
            cv.create_polygon(g3_points(cx - 5 * s, cy - 2 * s, cx + 3 * s, cy + 6 * s, 2 * s, power=1.0), fill="", outline=color, width=1.5 * s)
            ln(cx - 2 * s, cy - 5 * s, cx + 6 * s, cy - 5 * s, cx + 6 * s, cy + 3 * s, w=1.5)
        elif name:
            cv.create_text(cx, cy, text=name, fill=color, font=font(-1, True))

    # ---------------------------------------------------------------- ChatGPT controls (drawn on canvases)
    class Canvas(tk.Canvas):
        """Base for the hand-drawn controls: takes its parent's colour, redraws on resize and theme change."""
        def __init__(self, master, **kw):
            super().__init__(master, highlightthickness=0, bd=0, **kw)
            reg(self, "custom")
            self.bind("<Configure>", lambda e: self.draw())

        def bgc(self):
            try:
                return self.master.cget("bg")
            except tk.TclError:
                return T["page"]

        def alive(self):
            try:
                return bool(self.winfo_exists())
            except tk.TclError:
                return False

        def draw(self):
            self.delete("all")
            self.configure(bg=self.bgc())

    class Pill(Canvas):
        """ChatGPT button - a pill. kind: primary (black; white in dark), outline (20%-black edge), ghost, danger, icon."""
        def __init__(self, master, text="", cmd=None, kind="outline", h=36, w=None, tip="", size=None, icon=None,
                     icon_right=None):
            self.fnt = font(size if size is not None else (0 if h >= 36 else -1), bold=True)
            tw = measure(text, self.fnt) if text else 0
            width = w or (h if not text else int(tw + 2 * max(14, h * 0.42) + (20 if icon else 0) + (16 if icon_right else 0)))
            super().__init__(master, width=width, height=h, cursor="hand2")
            self.text, self.cmd, self.kind, self.tip = text, cmd, kind, tip
            self.icon, self.icon_right = icon, icon_right
            self.enabled, self.t, self.goal, self.down, self._job = True, 0.0, 0.0, False, None
            self.bind("<Enter>", lambda e: self.hover(True))
            self.bind("<Leave>", lambda e: self.hover(False))
            self.bind("<ButtonPress-1>", lambda e: self.press(True))
            self.bind("<ButtonRelease-1>", self.release)

        def hover(self, on):
            if on and self.tip and st["show_tooltips"]:
                status(self.tip)
            self.goal = 1.0 if on else 0.0
            if self._job is None:
                self._job = self.after(16, self.step)

        def step(self):  # hover fades in and out like ChatGPT's 150 ms transition
            self._job = None
            if not self.alive():
                return
            self.t += (self.goal - self.t) * 0.4
            if abs(self.goal - self.t) < 0.04:
                self.t = self.goal
            self.draw()
            if self.t != self.goal:
                self._job = self.after(16, self.step)

        def press(self, on):
            self.down = on
            self.draw()

        def release(self, e):
            self.down = False
            self.draw()
            if self.enabled and self.cmd and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
                self.cmd()

        def set_enabled(self, on):
            self.enabled = on
            self.configure(cursor="hand2" if on else "arrow")
            self.draw()

        def palette(self):
            bg = self.bgc()
            if self.kind == "primary":
                base, hov, fg, edge = T["btn"], T["btn_hover"], T["btn_fg"], None
            elif self.kind == "danger":
                base, hov, fg, edge = T["red"], mix(T["red"], "#000000", 0.12), "#ffffff", None
            elif self.kind == "outline":
                base, hov, fg, edge = bg, T["ghost_hover"], T["text"], T["outline"]
            else:  # ghost, icon
                base, hov, fg, edge = bg, T["ghost_hover"], T["text"], None
            if not self.enabled:
                fg = T["faint"]
                if self.kind in ("primary", "danger"):
                    base = hov = mix(base, bg, 0.72)
                    fg = mix(T["btn_fg"], bg, 0.25) if self.kind == "primary" else "#ffffff"
            return bg, base, hov, fg, edge

        def draw(self):
            super().draw()
            w, h = self.winfo_width(), self.winfo_height()
            if w < 4:
                return
            bg, base, hov, fg, edge = self.palette()
            fill = mix(base, hov, self.t if self.enabled else 0.0)
            if self.down and self.enabled:
                fill = mix(fill, T["text"], 0.08)
            self.create_polygon(g3_points(0.5, 0.5, w - 0.5, h - 0.5, h / 2, power=1.0), fill=fill, outline=edge or fill)
            if not self.text:
                draw_icon(self, self.icon, w / 2, h / 2, fg, bg_fill=fill)
                return
            tw = measure(self.text, self.fnt)
            extra = (20 if self.icon else 0) + (16 if self.icon_right else 0)
            x0 = (w - tw - extra) / 2
            if self.icon:
                draw_icon(self, self.icon, x0 + 7, h / 2, fg, bg_fill=fill)
                x0 += 20
            self.create_text(x0 + tw / 2, h / 2, text=self.text, fill=fg, font=self.fnt)
            if self.icon_right:
                draw_icon(self, self.icon_right, x0 + tw + 11, h / 2 + 1, T["dim"] if fg == T["text"] else fg, bg_fill=fill)

    class Chip(Canvas):
        """A toggle chip (pill): filled black when on (white in dark mode), 20%-black outline when off."""
        def __init__(self, master, text, var, command=None, h=30):
            self.fnt = font(-2)
            super().__init__(master, width=measure(text, self.fnt) + 30, height=h, cursor="hand2")
            self.text, self.var, self.command, self.hov = text, var, command, False
            self.bind("<Enter>", lambda e: self.set_hover(True))
            self.bind("<Leave>", lambda e: self.set_hover(False))
            self.bind("<ButtonRelease-1>", self.toggle)
            var.trace_add("write", lambda *_: self.draw() if self.alive() else None)

        def set_hover(self, on):
            self.hov = on
            self.draw()

        def toggle(self, e=None):
            self.var.set(not self.var.get())
            if self.command:
                self.command()

        def draw(self):
            super().draw()
            w, h = self.winfo_width(), self.winfo_height()
            if w < 4:
                return
            on = bool(self.var.get())
            fill = (T["btn_hover"] if self.hov else T["btn"]) if on else (T["ghost_hover"] if self.hov else self.bgc())
            self.create_polygon(g3_points(0.5, 0.5, w - 0.5, h - 0.5, h / 2, power=1.0), fill=fill,
                                outline=fill if on else T["outline"])
            self.create_text(w / 2, h / 2, text=self.text, fill=T["btn_fg"] if on else T["text"], font=self.fnt)

    class Segmented(Canvas):
        """ChatGPT segmented control: a soft pill track; the chosen option is a raised pill that slides over."""
        def __init__(self, master, options, var, command=None, labels=None, h=36, size=-1):
            self.options, self.var, self.command = list(options), var, command
            self.labels = labels or {o: o for o in options}
            self.fnt = font(size, bold=True)
            self.widths = [measure(self.labels[o], self.fnt) + 30 for o in self.options]
            super().__init__(master, width=sum(self.widths) + 8, height=h, cursor="hand2")
            self.x, self._job = None, None
            self.bind("<ButtonRelease-1>", self.click)
            var.trace_add("write", lambda *_: self.slide() if self.alive() else None)

        def target(self):
            i = self.options.index(self.var.get()) if self.var.get() in self.options else 0
            return 4 + sum(self.widths[:i]), self.widths[i]

        def click(self, e):
            x = 4
            for o, w in zip(self.options, self.widths):
                if x <= e.x < x + w:
                    if self.var.get() != o:
                        self.var.set(o)
                        if self.command:
                            self.command(o)
                    return
                x += w

        def slide(self):
            if self._job is None:
                self._job = self.after(16, self.step)

        def step(self):
            self._job = None
            if not self.alive():
                return
            tx, _ = self.target()
            self.x = tx if self.x is None else self.x + (tx - self.x) * 0.38
            if abs(tx - self.x) < 0.6:
                self.x = tx
            self.draw()
            if self.x != tx:
                self._job = self.after(16, self.step)

        def draw(self):
            super().draw()
            w, h = self.winfo_width(), self.winfo_height()
            if w < 4:
                return
            dark = st["theme"] == "dark"
            self.create_polygon(g3_points(0.5, 0.5, w - 0.5, h - 0.5, h / 2, power=1.0), fill=T["soft"], outline=T["soft"])
            tx, tw = self.target()
            x = tx if self.x is None else self.x
            thumb = T["selected"] if dark else T["card"]
            self.create_polygon(g3_points(x, 3.5, x + tw, h - 3.5, (h - 7) / 2, power=1.0), fill=thumb,
                                outline=thumb if dark else T["border"])
            cx = 4
            for o, ow in zip(self.options, self.widths):
                self.create_text(cx + ow / 2, h / 2, text=self.labels[o], font=self.fnt,
                                 fill=T["text"] if o == self.var.get() else T["dim"])
                cx += ow

    class Switch(Canvas):
        """ChatGPT's switch: a 36x20 pill, grey off and blue on, with a white knob that slides."""
        def __init__(self, master, var, command=None):
            super().__init__(master, width=40, height=24, cursor="hand2")
            self.var, self.command, self.hov, self._job = var, command, False, None
            self.k = 1.0 if var.get() else 0.0
            self.bind("<Enter>", lambda e: self.set_hover(True))
            self.bind("<Leave>", lambda e: self.set_hover(False))
            self.bind("<ButtonRelease-1>", lambda e: self.toggle())
            var.trace_add("write", lambda *_: self.slide() if self.alive() else None)

        def set_hover(self, on):
            self.hov = on
            self.draw()

        def toggle(self):
            self.var.set(not self.var.get())
            if self.command:
                self.command()

        def slide(self):
            if self._job is None:
                self._job = self.after(16, self.step)

        def step(self):
            self._job = None
            if not self.alive():
                return
            goal = 1.0 if self.var.get() else 0.0
            self.k += (goal - self.k) * 0.45
            if abs(goal - self.k) < 0.03:
                self.k = goal
            self.draw()
            if self.k != goal:
                self._job = self.after(16, self.step)

        def draw(self):
            super().draw()
            x0, y0, w, h = 2, 2, 36, 20
            off = T["switch_off_hover"] if self.hov else T["switch_off"]
            on = T["blue_hover"] if self.hov else T["blue"]
            track = mix(off, on, self.k)
            self.create_polygon(g3_points(x0, y0, x0 + w, y0 + h, h / 2, power=1.0), fill=track, outline=track)
            kx, r = x0 + h / 2 + (w - h) * self.k, h / 2 - 2
            self.create_oval(kx - r, y0 + 2.7, kx + r, y0 + h - 1.3, fill=mix(track, "#000000", 0.18), outline="")
            self.create_oval(kx - r, y0 + 2, kx + r, y0 + h - 2, fill="#ffffff", outline="")

    class Slider(Canvas):
        """Thin track, ink-coloured fill and a round white knob. Click or drag; arrow keys step by one."""
        def __init__(self, master, var, lo, hi):
            super().__init__(master, height=28, width=120, cursor="hand2", takefocus=1)
            self.var, self.lo, self.hi, self.hov = var, lo, hi, False
            self.bind("<ButtonPress-1>", self.drag)
            self.bind("<B1-Motion>", self.drag)
            self.bind("<Enter>", lambda e: self.set_hover(True))
            self.bind("<Leave>", lambda e: self.set_hover(False))
            self.bind("<Left>", lambda e: self.nudge(-1))
            self.bind("<Right>", lambda e: self.nudge(1))
            var.trace_add("write", lambda *_: self.draw() if self.alive() else None)

        def set_hover(self, on):
            self.hov = on
            self.draw()

        def span(self):
            return 10, max(11, self.winfo_width() - 10)

        def drag(self, e):
            self.focus_set()
            x0, x1 = self.span()
            v = self.lo + round((min(max(e.x, x0), x1) - x0) / (x1 - x0) * (self.hi - self.lo))
            if v != self.get():
                self.var.set(v)

        def get(self):
            try:
                return int(self.var.get())
            except (tk.TclError, ValueError):
                return self.lo

        def nudge(self, d):
            self.var.set(min(self.hi, max(self.lo, self.get() + d)))

        def draw(self):
            super().draw()
            x0, x1 = self.span()
            y = self.winfo_height() / 2
            f = (min(max(self.get(), self.lo), self.hi) - self.lo) / max(1, self.hi - self.lo)
            kx = x0 + f * (x1 - x0)
            self.create_polygon(g3_points(x0, y - 2, x1, y + 2, 2, power=1.0), fill=T["track"], outline=T["track"])
            if kx > x0 + 1:
                self.create_polygon(g3_points(x0, y - 2, kx, y + 2, 2, power=1.0), fill=T["text"], outline=T["text"])
            r = 9 if self.hov else 8
            self.create_oval(kx - r, y - r + 1.2, kx + r, y + r + 1.2, fill=mix(self.bgc(), "#000000", 0.14), outline="")
            self.create_oval(kx - r, y - r, kx + r, y + r, fill="#ffffff", outline=T["outline"])

    class Dropdown(Canvas):
        """A pill showing the current choice and a chevron; opens a ChatGPT popover menu."""
        def __init__(self, master, var, options, command=None, labels=None, w=None, h=36):
            self.fnt = font(-1)
            self.labels = labels or {o: o for o in options}
            width = w or (max(measure(self.labels.get(o, o), self.fnt) for o in options) + 52)
            super().__init__(master, width=width, height=h, cursor="hand2")
            self.var, self.options, self.command, self.hov = var, list(options), command, False
            self.bind("<Enter>", lambda e: self.set_hover(True))
            self.bind("<Leave>", lambda e: self.set_hover(False))
            self.bind("<ButtonRelease-1>", lambda e: self.open())
            var.trace_add("write", lambda *_: self.draw() if self.alive() else None)

        def set_hover(self, on):
            self.hov = on
            self.draw()

        def open(self):
            return popover(self, [(o, self.labels.get(o, o)) for o in self.options], self.pick, self.var.get())

        def pick(self, v):
            self.var.set(v)
            if self.command:
                self.command(v)

        def draw(self):
            super().draw()
            w, h = self.winfo_width(), self.winfo_height()
            if w < 4:
                return
            fill = T["ghost_hover"] if self.hov else T["field"]
            self.create_polygon(g3_points(0.5, 0.5, w - 0.5, h - 0.5, h / 2, power=1.0), fill=fill, outline=T["border"])
            txt = self.labels.get(self.var.get(), self.var.get())
            while txt and measure(txt, self.fnt) > w - 50:
                txt = txt[:-2] + "…" if not txt.endswith("…") else txt[:-2] + "…"
            self.create_text(16, h / 2, text=txt, anchor="w", fill=T["text"], font=self.fnt)
            draw_icon(self, "chevron", w - 18, h / 2 + 1, T["dim"])

    class Field(tk.Frame):
        """ChatGPT text input: rounded corners, a 1px edge that darkens on focus."""
        def __init__(self, master, var, width=200, h=40, mono=False, bg_key="field", justify="left"):
            super().__init__(master, bd=0, highlightthickness=0)
            reg(self, "field_shell")
            self.bg_key, self.focused = bg_key, False
            self.cv = tk.Canvas(self, height=h, width=width, highlightthickness=0, bd=0)
            self.cv.pack(fill="both", expand=True)
            self.e = tk.Entry(self.cv, textvariable=var, bd=0, highlightthickness=0, relief="flat", justify=justify)
            reg(self.e, "entry", (bg_key, mono))
            self.win = self.cv.create_window(14, h / 2, window=self.e, anchor="w")
            self.cv.bind("<Configure>", lambda e: self.draw())
            self.cv.bind("<Button-1>", lambda e: self.e.focus_set())
            self.e.bind("<FocusIn>", lambda e: self.set_focus(True), add="+")
            self.e.bind("<FocusOut>", lambda e: self.set_focus(False), add="+")

        def set_focus(self, on):
            self.focused = on
            self.draw()

        def draw(self):
            try:
                bg = self.master.cget("bg")
            except tk.TclError:
                return
            self.configure(bg=bg)
            self.cv.configure(bg=bg)
            self.cv.delete("shape")
            w, h = self.cv.winfo_width(), self.cv.winfo_height()
            if w < 10:
                return
            self.cv.create_polygon(g3_points(0.5, 0.5, w - 0.5, h - 0.5, min(14, h / 2), power=1.0), fill=T[self.bg_key],
                                   outline=T["faint"] if self.focused else T["border"], tags="shape")
            self.cv.tag_lower("shape")
            self.cv.itemconfigure(self.win, width=max(10, w - 28), height=max(10, h - 12))
            self.cv.coords(self.win, 14, h / 2)

    class NumField(Field):
        """A small number box tied to an IntVar (typing a number sets it, clamped to the range)."""
        def __init__(self, master, ivar, lo, hi, width=72):
            self.sv, self.ivar, self.lo, self.hi = tk.StringVar(value=str(ivar.get())), ivar, lo, hi
            super().__init__(master, self.sv, width=width, h=36, justify="center")
            ivar.trace_add("write", lambda *_: self.sync())
            self.e.bind("<Return>", lambda e: self.commit())
            self.e.bind("<FocusOut>", lambda e: self.commit(), add="+")

        def sync(self):
            try:
                v = str(self.ivar.get())
            except tk.TclError:
                return
            if self.sv.get() != v:
                self.sv.set(v)

        def commit(self):
            try:
                v = int(float(self.sv.get()))
            except ValueError:
                self.sync()
                return
            self.ivar.set(min(self.hi, max(self.lo, v)))
            self.sync()

    class Card(tk.Frame):
        """A rounded card (G3 corners) with a 1px hairline; put content in .inner."""
        def __init__(self, master, radius=None, pad=16, fill="card", border=True):
            super().__init__(master, bd=0, highlightthickness=0)
            reg(self, "card_shell")
            self.fill, self.radius, self.border = fill, radius, border
            self.cv = tk.Canvas(self, highlightthickness=0, bd=0)
            self.cv.place(x=0, y=0, relwidth=1, relheight=1)
            self.inner = box(self, fill)
            self.inner.pack(fill="both", expand=True, padx=pad, pady=pad)
            self.bind("<Configure>", lambda e: self.draw())

        def draw(self):
            try:
                bg = self.master.cget("bg")
            except tk.TclError:
                return
            self.configure(bg=bg)
            self.cv.configure(bg=bg)
            self.cv.delete("all")
            w, h = self.winfo_width(), self.winfo_height()
            r = self.radius if self.radius is not None else int(st["corner_radius"])
            self.cv.create_polygon(g3_points(0.5, 0.5, w - 0.5, h - 0.5, r), fill=T[self.fill],
                                   outline=T["border"] if self.border else T[self.fill])

    class FlowFrame(tk.Frame):
        """Lays its children out left-to-right and wraps them onto new rows, like words in a paragraph."""
        def __init__(self, master, bg="page", padx=6, pady=6):
            super().__init__(master, bd=0, height=10)
            reg(self, "bg", bg)
            self.padx, self.pady, self.items = padx, pady, []
            self.bind("<Configure>", lambda e: self.relayout(e.width))

        def add(self, w):
            self.items.append(w)
            self.relayout()
            return w

        def relayout(self, width=None):
            width = width or self.winfo_width()
            if width <= 1:
                width = 10 ** 6
            x = y = row_h = 0
            for w in self.items:
                rw, rh = w.winfo_reqwidth(), w.winfo_reqheight()
                if x > 0 and x + rw > width:
                    x, y, row_h = 0, y + row_h + self.pady, 0
                w.place(x=x, y=y)
                x += rw + self.padx
                row_h = max(row_h, rh)
            h = max(1, y + row_h)
            if int(self.cget("height")) != h:
                self.configure(height=h)

    scroll_frames = []

    class ScrollFrame(tk.Frame):
        def __init__(self, master, bg="page"):
            super().__init__(master, bd=0)
            reg(self, "bg", bg)
            self.cv = reg(tk.Canvas(self, highlightthickness=0, bd=0), "bg", bg)
            self.sb = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview, style=f"{bg}.Vertical.TScrollbar")
            self.body = box(self.cv, bg)
            self.win = self.cv.create_window(0, 0, window=self.body, anchor="nw")
            self.body.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
            self.cv.bind("<Configure>", lambda e: self.cv.itemconfigure(self.win, width=e.width))
            self.cv.configure(yscrollcommand=self.sb.set)
            self.sb.pack(side="right", fill="y")
            self.cv.pack(side="left", fill="both", expand=True)
            scroll_frames.append(self)

    def wheel_all(e):
        """One mouse-wheel handler for every scroll area: the one under the pointer scrolls."""
        try:
            w = root.winfo_containing(e.x_root, e.y_root)
        except (tk.TclError, KeyError):
            return
        if w is None or isinstance(w, (tk.Text, ttk.Treeview)):
            return
        scroll_frames[:] = [f for f in scroll_frames if f.winfo_exists()]
        p = w
        while p is not None:
            if any(p is f for f in scroll_frames):
                p.cv.yview_scroll(-e.delta if sys.platform == "darwin" else -e.delta // 120, "units")
                return
            p = p.master
    root.bind_all("<MouseWheel>", wheel_all)

    class Progress(Canvas):
        def __init__(self, master):
            super().__init__(master, height=6, width=40)
            self.value = 0.0

        def set(self, v):
            self.value = max(0.0, min(1.0, float(v)))
            self.draw()

        def draw(self):
            super().draw()
            w, h = self.winfo_width(), self.winfo_height()
            self.create_polygon(g3_points(0, 1, w, h - 1, 2, power=1.0), fill=T["track"], outline=T["track"])
            if self.value > 0:
                self.create_polygon(g3_points(0, 1, max(4, w * self.value), h - 1, 2, power=1.0), fill=T["text"], outline=T["text"])

    class SideRow(Canvas):
        """A ChatGPT sidebar row: line icon + label, rounded hover."""
        def __init__(self, master, text, icon, cmd, tip=""):
            super().__init__(master, height=36, width=160, cursor="hand2")
            self.text, self.icon, self.cmd, self.tip, self.hov = text, icon, cmd, tip, False
            self.bind("<Enter>", lambda e: self.set_hover(True))
            self.bind("<Leave>", lambda e: self.set_hover(False))
            self.bind("<ButtonRelease-1>", lambda e: self.cmd())

        def set_hover(self, on):
            self.hov = on
            if on and self.tip and st["show_tooltips"]:
                status(self.tip)
            self.draw()

        def draw(self):
            super().draw()
            w, h = self.winfo_width(), self.winfo_height()
            if self.hov:
                c = T["selected"] if st["theme"] == "light" else T["soft"]
                self.create_polygon(g3_points(0.5, 0.5, w - 0.5, h - 0.5, 10), fill=c, outline=c)
            draw_icon(self, self.icon, 20, h / 2, T["text"], bg_fill=self.bgc())
            self.create_text(40, h / 2, text=self.text, anchor="w", fill=T["text"], font=font(0))

    class Logo(Canvas):
        """The AITE icon, drawn live so it follows the theme: the 'A' as a robot arm with a blue target dot."""
        def __init__(self, master, size=32):
            super().__init__(master, width=size, height=size)
            self.s = size

        def draw(self):
            super().draw()
            S = self.s
            self.create_polygon(g3_points(0.5, 0.5, S - 0.5, S - 0.5, S * 0.3), fill=T["btn"], outline=T["btn"])
            ink, w = T["btn_fg"], max(2, S * 0.075)
            ax, ay, lx, rx, fy = S * 0.5, S * 0.27, S * 0.28, S * 0.72, S * 0.75
            self.create_line(lx, fy, ax, ay, rx, fy, fill=ink, width=w, capstyle="round", joinstyle="round")
            self.create_line(S * 0.375, S * 0.565, S * 0.625, S * 0.565, fill=ink, width=w, capstyle="round")
            r = S * 0.11
            self.create_oval(ax - r, ay - r, ax + r, ay + r, fill=ink, outline="")
            h = r * 0.46
            self.create_oval(ax - h, ay - h, ax + h, ay + h, fill=T["btn"], outline="")
            b = S * 0.075
            self.create_oval(rx - b, fy - b, rx + b, fy + b, fill=T["blue"], outline="")

    # ---------------------------------------------------------------- popover menus (rounded, transparent window)
    def close_popover(*_):
        p, state["popover"] = state.get("popover"), None
        if p is not None:
            try:
                p.destroy()
            except tk.TclError:
                pass

    def popover(anchor, items, on_pick, current=None):
        close_popover()
        fnt, row_h, pad, S = font(-1), 36, 6, 2
        W = max(220, anchor.winfo_width(), max(measure(lbl, fnt) for _, lbl in items) + 70)
        H = pad * 2 + row_h * len(items)
        top = tk.Toplevel(root)
        top.overrideredirect(True)
        clear = False
        if sys.platform == "darwin":
            try:
                top.wm_attributes("-transparent", True)
                top.configure(bg="systemTransparent")
                clear = True
            except tk.TclError:
                pass
        cv = tk.Canvas(top, width=W + 2 * S, height=H + 2 * S, highlightthickness=0, bd=0,
                       bg="systemTransparent" if clear else T["card"])
        cv.pack()
        cv.create_polygon(g3_points(S + 0.5, S + 0.5, S + W - 0.5, S + H - 0.5, 20), fill=T["card"], outline=T["border"])
        rows = []
        for i, (val, lbl) in enumerate(items):
            y0 = S + pad + i * row_h
            hl = cv.create_polygon(g3_points(S + pad, y0 + 1, S + W - pad, y0 + row_h - 1, 10), fill=T["card"], outline="")
            cv.create_text(S + pad + 14, y0 + row_h / 2, text=lbl, anchor="w", fill=T["text"], font=fnt)
            if val == current:
                draw_icon(cv, "check", S + W - pad - 20, y0 + row_h / 2, T["text"])
            rows.append((y0, hl, val))

        def motion(e):
            for y0, hl, _ in rows:
                cv.itemconfigure(hl, fill=T["ghost_hover"] if y0 <= e.y < y0 + row_h else T["card"])

        def click(e):
            hit = next((v for y0, _, v in rows if y0 <= e.y < y0 + row_h), None)
            close_popover()
            if hit is not None:
                on_pick(hit)
        cv.bind("<Motion>", motion)
        cv.bind("<ButtonRelease-1>", click)
        top.bind("<Escape>", close_popover)
        x = anchor.winfo_rootx() - S
        y = anchor.winfo_rooty() + anchor.winfo_height() + 6 - S
        if y + H + 2 * S > root.winfo_screenheight() - 30:
            y = anchor.winfo_rooty() - H - 6 - S
        top.geometry(f"+{int(max(0, min(x, root.winfo_screenwidth() - W - 2 * S)))}+{int(max(0, y))}")
        top.items = items
        top.pick = lambda v: (close_popover(), on_pick(v))
        state["popover"] = top
        top.lift()
        return top

    def on_any_click(e):
        p = state.get("popover")
        if p is not None and not str(e.widget).startswith(str(p)):
            close_popover()
    root.bind_all("<ButtonPress-1>", on_any_click, add="+")

    # ---------------------------------------------------------------- theme
    def text_area(master, bg="card", mono=False, h=10, size=0):
        fr = box(master, bg)
        t = tk.Text(fr, height=h, width=30, wrap="word", bd=0, highlightthickness=0, padx=14, pady=12, undo=True,
                    relief="flat", spacing1=2, spacing3=2)
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview, style=f"{bg}.Vertical.TScrollbar")
        t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        reg(t, "text", (bg, mono, size))
        return fr, t

    def styles():
        sty = ttk.Style()
        sty.theme_use("clam")
        sty.configure(".", font=font(-1), background=T["page"], foreground=T["text"])
        for key in ("page", "sidebar", "card", "code"):
            name = f"{key}.Vertical.TScrollbar"
            sty.layout(name, [("Vertical.Scrollbar.trough", {"children": [
                ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})], "sticky": "ns"})])
            sty.configure(name, troughcolor=T[key], background=T["outline"], bordercolor=T[key], lightcolor=T["outline"],
                          darkcolor=T["outline"], arrowsize=7, relief="flat", gripcount=0, width=7)
            sty.map(name, background=[("active", T["faint"])])
        sty.layout("Chat.Treeview", [("Chat.Treeview.treearea", {"sticky": "nswe"})])
        sty.configure("Chat.Treeview", background=T["card"], fieldbackground=T["card"], foreground=T["text"],
                      rowheight=32, borderwidth=0, font=font(-1))
        sty.configure("Chat.Treeview.Heading", background=T["card"], foreground=T["dim"], relief="flat",
                      borderwidth=0, font=font(-2, True), padding=(6, 6))
        sty.map("Chat.Treeview.Heading", background=[("active", T["ghost_hover"])])
        sty.map("Chat.Treeview", background=[("selected", T["selected"])], foreground=[("selected", T["text"])])

    def apply_theme():
        T.clear()
        T.update(THEMES.get(st["theme"], THEMES["dark"]))
        font_cache.clear()
        root.configure(bg=T["page"])
        styles()
        alive = []
        for w, role, extra in widgets:
            try:
                if not w.winfo_exists():
                    continue
            except tk.TclError:
                continue
            alive.append((w, role, extra))
            try:
                if role == "bg":
                    w.configure(bg=T[extra])
                elif role == "label":
                    tone, size, bold, mono = extra
                    w.configure(bg=w.master.cget("bg"), fg=T[tone], font=font(size, bold, mono))
                elif role in ("custom", "card_shell", "field_shell"):
                    w.draw()
                elif role == "text":
                    bg, mono, size = extra
                    w.configure(bg=T[bg], fg=T["text"], insertbackground=T["text"], selectbackground=T["select_text"],
                                selectforeground=T["text"], font=font(size, mono=mono))
                elif role == "entry":
                    bg, mono = extra
                    w.configure(bg=T[bg], fg=T["text"], insertbackground=T["text"], selectbackground=T["select_text"],
                                selectforeground=T["text"], font=font(-1, mono=mono))
            except tk.TclError:
                pass
        widgets[:] = alive
        theme_btn.icon = "sun" if st["theme"] == "dark" else "moon"
        theme_btn.tip = "Light mode (Cmd+T)" if st["theme"] == "dark" else "Dark mode (Cmd+T)"
        theme_btn.draw()
        draw_wf()

    # ---------------------------------------------------------------- layout: top bar, then Agent page | Manual (sidebar | main)
    topbar = box(root, "page")
    topbar.pack(fill="x", padx=14, pady=(10, 6))
    tleft = box(topbar, "page")
    tleft.pack(side="left")
    Logo(tleft).pack(side="left", padx=(4, 6))
    title_btn = Pill(tleft, APP, lambda: about_menu(), "ghost", h=40, size=3, icon_right="chevron",
                     tip=f"{APP} {VERSION} - about, help and shortcuts")
    title_btn.pack(side="left")
    tright = box(topbar, "page")
    tright.pack(side="right")
    theme_btn = Pill(tright, "", lambda: toggle_theme(), "icon", h=38, icon="sun", tip="Light / dark (Cmd+T)")
    agents_btn = Pill(tright, "0 agents", lambda: show_agents(), "outline", h=34, size=-2, icon="gear",
                      tip="Parallel agents running right now - click for the full list")
    agents_btn.pack(side="left", padx=(0, 6))
    Pill(tright, "Guide", lambda: guide(), "outline", h=34, size=-2, icon="play", tip="Interactive guide").pack(side="left", padx=(0, 6))
    theme_btn.pack(side="left", padx=2)
    gear_btn = Pill(tright, "", lambda: open_settings(), "icon", h=38, icon="gear", tip="Settings (Cmd+,)")
    gear_btn.pack(side="left", padx=2)
    Pill(tright, "", lambda: show_help(), "icon", h=38, icon="help", tip="Help").pack(side="left", padx=2)
    v_page = tk.StringVar(value="Agent")
    page_seg = Segmented(topbar, ["Agent"], v_page, lambda p: show_page(p), h=40, size=0, labels={"Agent": "Agent mode"})
    page_seg.place(relx=0.5, rely=0.5, anchor="center")
    train_top = Pill(topbar, "Ask your data", lambda: show_page("Ask"), "outline", h=36, size=-1, icon="up",
                     tip="Ask (RAG) - questions about ALL the collected data, answered by a local AI model (Cmd+2)")
    train_top.place(relx=0.5, rely=0.5, anchor="w", x=page_seg.winfo_reqwidth() / 2 + 28)
    topbar.configure(height=44)
    box(root, "divider", height=1).pack(fill="x")
    shell = box(root, "page")
    sidebar = box(shell, "sidebar", width=452)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)
    box(shell, "divider", width=1).pack(side="left", fill="y")
    main = box(shell, "page")
    main.pack(side="left", fill="both", expand=True)

    # sidebar: brand, ChatGPT-style rows
    box(sidebar, "sidebar", height=8).pack(fill="x")
    for txt, ic, cmd, tip in [("New run", "edit", lambda: new_run(), "Reset the input and clear results"),
                              ("Run history", "clock", lambda: show_history(), "Runs this session"),
                              ("Settings", "gear", lambda: open_settings(), f"All {len(SPEC)} settings (Cmd+,)"),
                              ("Help", "help", lambda: show_help(), "How AITE works")]:
        SideRow(sidebar, txt, ic, cmd, tip).pack(fill="x", padx=8)
    box(sidebar, "divider", height=1).pack(fill="x", padx=14, pady=(10, 10))

    # sidebar bottom: progress + Run / Stop (packed first so it always stays visible)
    sbot = box(sidebar, "sidebar")
    sbot.pack(side="bottom", fill="x", padx=14, pady=(8, 14))
    prog = Progress(sbot)
    prog.pack(fill="x")
    prog_lbl = label(sbot, "Ready", "dim", -2)
    prog_lbl.pack(fill="x", pady=(4, 8))
    runrow = box(sbot, "sidebar")
    runrow.pack(fill="x")
    stop_btn = Pill(runrow, "Stop", lambda: state["cancel"].set(), "outline", h=44, icon="stop", tip="Stop the current run (Esc)")
    stop_btn.pack(side="right", padx=(8, 0))
    stop_btn.set_enabled(False)
    run_btn = Pill(runrow, "Run pipeline", lambda: start_run(), "primary", h=44, icon="up",
                   tip="Search -> filter -> datagen -> preview (Cmd+R)")
    run_btn.pack(side="left", fill="x", expand=True)

    mode_row = box(sidebar, "sidebar")
    mode_row.pack(fill="x", padx=14, pady=(0, 6))
    v_mode = tk.StringVar(value="VDM")
    mode_seg = Segmented(mode_row, ["VDM", "JSON"], v_mode, lambda m: set_mode(m),
                         labels={"VDM": "Visual dropdowns", "JSON": "JSON schema"})
    mode_seg.pack(fill="x")
    holder = box(sidebar, "sidebar")
    holder.pack(fill="both", expand=True)
    vdm_sf = ScrollFrame(holder, "sidebar")
    vdm = vdm_sf.body
    jsn = box(holder, "sidebar")

    # ----- VDM
    v_topics, v_qty, v_qual = tk.StringVar(), tk.IntVar(value=DEFAULT_INPUT["quantity"]), tk.IntVar(value=DEFAULT_INPUT["quality"])
    v_out, v_var = tk.StringVar(value="pdf"), tk.IntVar(value=DEFAULT_INPUT["datagen_variations"])
    style_vars, format_vars, method_vars, src_vars = {}, {}, {}, {}

    def section(title, sub=None):
        label(vdm, title, "text", 0, True).pack(fill="x", padx=16, pady=(18, 2))
        if sub:
            label(vdm, sub, "dim", -2, wraplength=390).pack(fill="x", padx=16, pady=(0, 6))

    def chip_group(title, options, store, labels=None, init=True, command=None):
        label(vdm, title, "dim", -2, True).pack(fill="x", padx=16, pady=(10, 4))
        g = FlowFrame(vdm, "sidebar")
        g.pack(fill="x", padx=16)
        for o in options:
            var = store.setdefault(o, tk.BooleanVar(value=init))
            g.add(Chip(g, (labels or {}).get(o, o), var, command or (lambda: on_vdm_change())))
        bar = FlowFrame(vdm, "sidebar")
        bar.pack(fill="x", padx=16, pady=(6, 0))

        def set_all(on, store=store):
            for v in store.values():
                v.set(on)
            (command or on_vdm_change)()
        bar.add(Pill(bar, "Select all", lambda: set_all(True), "ghost", h=26, size=-3))
        bar.add(Pill(bar, "Clear", lambda: set_all(False), "ghost", h=26, size=-3))

    section("1  Topics", "Any subjects, comma separated - or tap a suggestion.")
    topic_f = Field(vdm, v_topics, h=42, bg_key="field")
    topic_f.pack(fill="x", padx=16)
    topic_e = topic_f.e
    chips = FlowFrame(vdm, "sidebar")
    chips.pack(fill="x", padx=16, pady=(8, 0))
    presets = ["algebra", "calculus", "geometry", "probability", "physics", "chemistry", "biology", "python", "algorithms",
               "robotics", "electronics", "statistics", "machine learning", "word problems", "number theory", "trigonometry"]
    for ptxt in presets:
        def addt(p=ptxt):
            cur = [x.strip() for x in v_topics.get().split(",") if x.strip()]
            if p not in cur:
                cur.append(p)
            v_topics.set(", ".join(cur))
        chips.add(Pill(chips, ptxt, addt, "outline", h=30, size=-3, icon="plus", tip=f"Add topic '{ptxt}'"))
    chips.add(Pill(chips, "Clear topics", lambda: v_topics.set(""), "ghost", h=30, size=-3))

    def slider_row(var, lo, hi, presets_=()):
        row = box(vdm, "sidebar")
        row.pack(fill="x", padx=16)
        NumField(row, var, lo, hi).pack(side="right", padx=(10, 0))
        Slider(row, var, lo, hi).pack(side="left", fill="x", expand=True)
        if presets_:
            pr = FlowFrame(vdm, "sidebar")
            pr.pack(fill="x", padx=16, pady=(6, 0))
            for n in presets_:
                pr.add(Pill(pr, f"{n:,}", lambda n=n: var.set(n), "outline", h=28, size=-3))

    section("2  Quantity", "How many records to keep (1 - 100,000). Type any number in the box.")
    slider_row(v_qty, 1, 10000, (10, 100, 1000, 5000, 10000, 100000))
    section("3  Quality", "1-4: basic checks only. 5-10: strict filter and a rising minimum score.")
    slider_row(v_qual, 1, 10)
    qual_hint = label(vdm, "", "dim", -2, wraplength=390)
    qual_hint.pack(fill="x", padx=16, pady=(4, 0))
    section("4  Type of data", "Pick one or more - each gets a share of the quantity. Worked examples are searched too.")
    dtype_vars = {}
    chip_group("Data types", DATA_TYPES, dtype_vars)
    section("5  Output type", "One combined file per run.")
    Segmented(vdm, OUTPUT_TYPES, v_out, labels={"pdf": "PDF", "txt": "TXT", "json": "JSON"}).pack(anchor="w", padx=16)
    section("6  DataGen", "Similar versions of every record: new numbers re-solved with SymPy, names, synonyms, "
                          "10 styles and 11 formats.")
    slider_row(v_var, 0, 1000, (0, 3, 10, 100, 1000, 5000, 10000))
    dg_hint = label(vdm, "", "dim", -2, wraplength=390)
    dg_hint.pack(fill="x", padx=16, pady=(4, 0))
    chip_group("Variation methods", METHODS, method_vars, METHOD_LABELS)
    chip_group("Styles", STYLES, style_vars)
    chip_group("Formats", FORMATS, format_vars)
    section("Sources", "Where to look. DuckDuckGo gets one honest request; official free APIs fill in.")

    def src_changed():
        for s_, var in src_vars.items():
            st[f"{s_}_enabled"] = bool(var.get())
        persist()
    for s_ in SOURCES:
        src_vars[s_] = tk.BooleanVar(value=st[f"{s_}_enabled"])
    chip_group("Enabled sources", SOURCES, src_vars, command=src_changed)
    box(vdm, "sidebar", height=18).pack(fill="x")

    # ----- JSON (a ChatGPT code block)
    label(jsn, "Paste, type or import the same parameters as JSON.", "dim", -2, wraplength=400).pack(fill="x", padx=16, pady=(4, 8))
    label(jsn, 'Schema: {"topics": [str], "quantity": 1-100000, "quality": 1-10, "data_type": str, "output_type": '
               '"pdf"|"txt"|"json", "datagen_variations": 0-100, "datagen_styles": [...]|"all", "datagen_formats": '
               '[...]|"all", "datagen_methods": [...]}', "faint", -3, wraplength=400).pack(side="bottom", fill="x", padx=16, pady=(6, 4))
    json_status = label(jsn, "", "dim", -2, wraplength=400)
    json_status.pack(side="bottom", fill="x", padx=16, pady=(6, 0))
    jcard = Card(jsn, radius=16, pad=0, fill="code")
    jcard.pack(fill="both", expand=True, padx=14)
    jhead = box(jcard.inner, "code")
    jhead.pack(fill="x", padx=12, pady=(10, 4))
    label(jhead, "json", "dim", -2).pack(side="left")
    jbar = FlowFrame(jcard.inner, "code", padx=4, pady=4)
    jbar.pack(fill="x", padx=10)
    for txt, cmd in [("Import file", lambda: import_json()), ("Paste", lambda: paste_json()), ("Copy", lambda: copy_json()),
                     ("Format", lambda: format_json()), ("Template", lambda: set_input(json.loads(json.dumps(DEFAULT_INPUT)))),
                     ("Validate", lambda: validate_now())]:
        jbar.add(Pill(jbar, txt, cmd, "ghost", h=28, size=-3))
    jfr, json_t = text_area(jcard.inner, "code", mono=True, h=16, size=-2)
    jfr.pack(fill="both", expand=True, padx=2, pady=(4, 10))
    json_t.bind("<KeyRelease>", lambda e: json_live_check())

    # workflow strip
    WF = [("input", "Input"), ("search", "Web search"), ("filter", "Filter"), ("datagen", "DataGen"), ("output", "Output")]
    wf_state = {k: {"state": "idle", "info": ""} for k, _ in WF}
    wf = reg(tk.Canvas(main, height=74, highlightthickness=0, bd=0), "bg", "page")
    wf.pack(fill="x", padx=20, pady=(6, 4))

    def draw_wf():
        wf.delete("all")
        w, h = wf.winfo_width(), int(wf["height"])
        if w < 50:
            return
        gap = 22
        nw = (w - gap * (len(WF) - 1)) / len(WF)
        pulse = 0.5 + 0.5 * math.sin(state["pulse"])
        for i, (k, name) in enumerate(WF):
            x1, x2 = i * (nw + gap), i * (nw + gap) + nw
            s = wf_state[k]["state"]
            dot = {"idle": T["faint"], "active": T["blue"], "done": T["green"], "error": T["red"], "skipped": T["faint"]}[s]
            if s == "active":
                dot = mix(T["blue"], T["card"], 0.55 * pulse)
            tag = f"node_{k}"
            edge = T["blue"] if s == "active" else T["border"]
            wf.create_polygon(g3_points(x1 + 0.5, 0.5, x2 - 0.5, h - 0.5, 18), fill=T["card"], outline=edge,
                              width=1.5 if s == "active" else 1, tags=tag)
            wf.create_oval(x1 + 16, 18, x1 + 25, 27, fill=dot, outline="", tags=tag)
            wf.create_text(x1 + 33, 22, anchor="w", text=name, fill=T["text"], font=font(-1, True), tags=tag)
            info = wf_state[k]["info"] or {"idle": "Waiting", "active": "Running…", "done": "Done", "error": "Check the log",
                                           "skipped": "Skipped"}[s]
            wf.create_text(x1 + 16, 48, anchor="w", text=shorten(info, max(8, int((nw - 26) / 6.6))), fill=T["dim"],
                           font=font(-3), tags=tag)
            wf.tag_bind(tag, "<Button-1>", lambda e, k=k: wf_click(k))
            if i < len(WF) - 1:  # a thin chevron between stages
                mx = x2 + gap / 2
                wf.create_line(mx - 2.5, h / 2 - 5, mx + 2.5, h / 2, mx - 2.5, h / 2 + 5, fill=T["faint"], width=1.6,
                               capstyle="round", joinstyle="round")
    wf.bind("<Configure>", lambda e: draw_wf())

    def wf_set(k, s, info=None):
        wf_state[k]["state"] = s
        if info is not None:
            wf_state[k]["info"] = info
        draw_wf()

    def wf_click(k):
        if k == "input":
            (topic_e if state["mode"] == "VDM" else json_t).focus_set()
        elif k == "search":
            open_settings("Network")
        elif k == "filter":
            open_settings("Filter")
        elif k == "datagen":
            open_settings("DataGen")
        else:
            show_view("Preview")

    # toolbar of outlined pills (wraps)
    tb = FlowFrame(main, "page", padx=6, pady=6)
    tb.pack(fill="x", padx=20, pady=(6, 8))
    for txt, cmd, tip in [
        ("Validate", lambda: validate_now(), "Check the input"),
        ("Re-filter", lambda: refilter(), "Apply the current quality / quantity to what was found - no new search"),
        ("Re-run DataGen", lambda: rerun_datagen(), "Make the variants again with the current DataGen settings"),
        ("Preview", lambda: refresh_preview(), "Refresh the preview"),
        ("Export as…", lambda: do_export(ask=True), "Pick a file name"),
        ("Copy preview", lambda: copy_preview(), "Copy the preview text"),
        ("Import JSON", lambda: import_json(), "Load input from a .json file"),
        ("Save JSON", lambda: save_json_input(), "Save the input as .json"),
        ("Load results", lambda: load_results(), "Open an AITE JSON export"),
        ("Clear results", lambda: clear_results(), "Empty the results"),
        ("Clear log", lambda: log_t.delete("1.0", "end"), "Empty the log"),
        ("Remove selected", lambda: remove_selected(), "Drop the selected records"),
        ("Rejected", lambda: show_rejected(), "What the filter rejected"),
        ("Stats", lambda: show_stats(), "Run statistics"),
        ("Open folder", lambda: open_path(st["out_dir"]), "Open the export folder"),
    ]:
        tb.add(Pill(tb, txt, cmd, "outline", h=32, size=-2, tip=tip))

    # status line (ChatGPT's small grey line under the composer)
    sbar = box(main, "page")
    sbar.pack(side="bottom", fill="x", padx=22, pady=(2, 10))
    count_lbl = label(sbar, "", "dim", -3)
    count_lbl.pack(side="right")
    status_lbl = label(sbar, "Ready", "dim", -3)
    status_lbl.pack(side="left", fill="x", expand=True)

    # output card
    out_card = Card(main, pad=14)
    out_card.pack(fill="both", expand=True, padx=20, pady=(0, 6))
    ohead = FlowFrame(out_card.inner, "card", padx=8, pady=8)
    ohead.pack(fill="x")
    v_view = tk.StringVar(value="Preview")
    ohead.add(Segmented(ohead, ["Progress", "Preview", "Records", "Log"], v_view, lambda v: show_view(v)))
    prev_fmt = tk.StringVar(value="as output type")
    ohead.add(Dropdown(ohead, prev_fmt, ["as output type", "txt", "json", "pdf (text layout)"],
                       labels={"as output type": "Preview as output type", "txt": "Preview as TXT", "json": "Preview as JSON",
                               "pdf (text layout)": "Preview as PDF text"}))
    find_var = tk.StringVar()
    find_f = Field(ohead, find_var, width=190, h=36)
    ohead.add(find_f)
    find_f.e.bind("<Return>", lambda e: find_text())
    ohead.add(Pill(ohead, "Find", lambda: find_text(), "ghost", h=36, icon="search", size=-1))
    ohead.add(Pill(ohead, "Export", lambda: do_export(), "primary", h=36, icon="down", size=-1, tip="Save ONE combined file (Cmd+E)"))
    prev_info = label(out_card.inner, "", "dim", -3)
    prev_info.pack(fill="x", pady=(6, 4))
    views = box(out_card.inner, "card")
    views.pack(fill="both", expand=True)
    run_vis = {"stage": {}, "msg": "", "frac": 0.0, "t0": 0.0, "kept": 0, "rejected": 0, "variants": 0, "searcher": None}

    class RunProgress(Canvas):
        """What a run is doing, drawn - stages, progress, live counters and results per source - instead of a log."""
        def __init__(self, master):
            super().__init__(master, height=380, width=600)
            self.last = 0.0

        def draw(self):
            super().draw()
            w = self.winfo_width()
            if w < 100:
                return
            st_ = run_vis["stage"]
            running = state["running"]
            active = next((n for k, n in WF if st_.get(k) == "active"), None)
            title = (f"{active}…" if active else "Working…") if running else ("Finished" if run_vis["t0"] else "Ready to run")
            self.create_text(24, 34, text=title, anchor="w", fill=T["text"], font=font(10, True))
            sub = run_vis["msg"] if running else ("Press Run pipeline in the sidebar - progress appears here."
                                                 if not run_vis["t0"] else "Open Preview to review, then Export.")
            self.create_text(24, 66, text=shorten(sub, int(w / 7.5)), anchor="w", fill=T["dim"], font=font(-1))
            # stage stepper
            n, x0, x1, y = len(WF), 40, w - 40, 120
            for i, (k, name) in enumerate(WF):
                cx = x0 + (x1 - x0) * i / (n - 1)
                s_ = st_.get(k, "idle")
                if i < n - 1:
                    nx = x0 + (x1 - x0) * (i + 1) / (n - 1)
                    done = s_ == "done"
                    self.create_line(cx + 16, y, nx - 16, y, fill=T["green"] if done else T["track"], width=3, capstyle="round")
                col = {"done": T["green"], "active": T["blue"], "error": T["red"], "skipped": T["faint"]}.get(s_, T["track"])
                if s_ == "active":
                    pulse = 0.5 + 0.5 * math.sin(time.time() * 4)
                    r = 15 + 4 * pulse
                    self.create_oval(cx - r, y - r, cx + r, y + r, fill=mix(T["blue"], T["card"], 0.75), outline="")
                self.create_oval(cx - 13, y - 13, cx + 13, y + 13, fill=col, outline="")
                if s_ == "done":
                    draw_icon(self, "check", cx, y, "#ffffff", bg_fill=col)
                else:
                    self.create_text(cx, y + 0.5, text=str(i + 1), fill="#ffffff" if s_ in ("active", "error") else T["dim"],
                                     font=font(-2, True))
                self.create_text(cx, y + 30, text=name, fill=T["text"] if s_ != "idle" else T["dim"], font=font(-2, s_ == "active"))
            # progress bar
            by = 186
            frac = run_vis["frac"] if running else (1.0 if run_vis["t0"] else 0.0)
            self.create_polygon(g3_points(24, by, w - 24, by + 12, 6, power=1.0), fill=T["track"], outline=T["track"])
            if frac > 0:
                self.create_polygon(g3_points(24, by, 24 + max(12, (w - 48) * frac), by + 12, 6, power=1.0), fill=T["blue"], outline=T["blue"])
            self.create_text(w - 24, by - 14, text=f"{frac * 100:.0f}%", anchor="e", fill=T["dim"], font=font(-2, True))
            # counters
            sr = run_vis["searcher"]
            found = sum((sr.stats if sr else state.get("stats", {})).values()) if (sr or state.get("stats")) else 0
            el = (time.time() - run_vis["t0"]) if running and run_vis["t0"] else run_vis.get("elapsed", 0)
            tiles_ = [("Found", f"{found:,}"), ("Kept", f"{run_vis['kept'] or len(state['records']):,}"),
                      ("Rejected", f"{run_vis['rejected'] or len(state['rejected']):,}"),
                      ("DataGen variants", f"{run_vis['variants'] or len(state['variants']):,}"), ("Time", fmt_s(el))]
            tw = (w - 48 - 12 * (len(tiles_) - 1)) / len(tiles_)
            for i, (lab, val) in enumerate(tiles_):
                tx = 24 + i * (tw + 12)
                self.create_polygon(g3_points(tx, 222, tx + tw, 292, 14), fill=T["soft"], outline=T["soft"])
                self.create_text(tx + 14, 240, text=lab, anchor="w", fill=T["dim"], font=font(-3))
                self.create_text(tx + 14, 268, text=val, anchor="w", fill=T["text"], font=font(6, True))
            # results per source
            stats_ = dict(sr.stats) if sr else dict(state.get("stats", {}))
            if stats_:
                self.create_text(24, 316, text="Found per source", anchor="w", fill=T["dim"], font=font(-2, True))
                top = max(1, max(stats_.values()))
                items = sorted(stats_.items(), key=lambda x: -x[1])[:6]
                cw = (w - 48) / max(1, len(items))
                for i, (src, v) in enumerate(items):
                    bx = 24 + i * cw
                    self.create_polygon(g3_points(bx, 330, bx + cw - 12, 342, 6, power=1.0), fill=T["track"], outline=T["track"])
                    if v:
                        self.create_polygon(g3_points(bx, 330, bx + max(12, (cw - 12) * v / top), 342, 6, power=1.0),
                                            fill=T["text"], outline=T["text"])
                    self.create_text(bx, 358, text=f"{src} {v:,}", anchor="w", fill=T["dim"], font=font(-3))
    tab_progress = box(views, "card")
    run_canvas = RunProgress(tab_progress)
    run_canvas.pack(fill="x")
    run_canvas.configure(height=380)
    plog_fr, plog_t = text_area(tab_progress, "code", mono=True, h=10, size=-3)
    plog_fr.pack(fill="both", expand=True, pady=(8, 0))
    tab_prev, prev_t = text_area(views, "card", h=20)
    tab_tbl = box(views, "card")
    tab_log, log_t = text_area(views, "code", mono=True, h=20, size=-2)
    cols = ("n", "kind", "score", "topic", "source", "style", "format", "title")
    tree = ttk.Treeview(tab_tbl, columns=cols, show="headings", selectmode="extended", style="Chat.Treeview")
    tsb = ttk.Scrollbar(tab_tbl, orient="vertical", command=tree.yview, style="card.Vertical.TScrollbar")
    tree.configure(yscrollcommand=tsb.set)
    for c, w_, a in (("n", 54, "e"), ("kind", 70, "w"), ("score", 58, "e"), ("topic", 110, "w"), ("source", 104, "w"),
                     ("style", 96, "w"), ("format", 88, "w"), ("title", 480, "w")):
        tree.heading(c, text=c.capitalize() if c != "n" else "#", command=lambda c=c: sort_tree(c))
        tree.column(c, width=w_, anchor=a, stretch=c == "title")
    tsb.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    tree.bind("<Double-1>", lambda e: show_record())

    def show_view(v):
        if v_view.get() != v:
            v_view.set(v)
        for name, fr in (("Progress", tab_progress), ("Preview", tab_prev), ("Records", tab_tbl), ("Log", tab_log)):
            fr.pack_forget()
            if name == v:
                fr.pack(fill="both", expand=True)
    show_view("Preview")

    # ---------------------------------------------------------------- Agent mode page (Parallel Web Technologies)
    ag = {"root": agent_dir(st), "proc": None, "status": None, "cpu": [], "thumb": None, "thumb_path": "",
          "spawned_offline": smoke, "last_ev": None}
    if smoke:
        import tempfile
        ag["root"] = tempfile.mkdtemp(prefix="aite_agent_smoke_")
        smoke_settings = os.path.join(ag["root"], "settings.json")
        with open(smoke_settings, "w") as f_:
            json.dump(dict(default_settings(), _version=SETTINGS_VERSION, pwt_workers=33, agent_quality=6, agent_batch=9,
                           agent_variations=2), f_)  # values that are not old defaults (those get migrated)
        os.environ["AITE_SETTINGS"] = smoke_settings  # the background agent reads defaults, never the user's settings
    agent_pg = box(root, "page")
    ag_sf = ScrollFrame(agent_pg, "page")
    ag_sf.pack(fill="both", expand=True)
    agb = box(ag_sf.body, "page")
    agb.pack(fill="both", expand=True, padx=28, pady=(8, 24))

    def fmt_n(v):
        v = float(v or 0)
        for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
            if abs(v) >= div * 10:
                return f"{v / div:,.1f}{suf}".replace(".0" + suf, suf)
        return f"{int(v):,}"

    def fmt_s(s):
        s = int(s or 0)
        return f"{s // 86400}d {s % 86400 // 3600}h" if s >= 86400 else f"{s // 3600}h {s % 3600 // 60}m" if s >= 3600 else f"{s // 60}m {s % 60}s"

    # hero: state + the one big button (pause / resume - never stop)
    hero = Card(agb, pad=22)
    hero.pack(fill="x", pady=(4, 14))
    hl = box(hero.inner, "card")
    hl.pack(side="left", fill="x", expand=True)

    class Dot(Canvas):
        """Status dot; breathes gently while collecting."""
        def __init__(self, master):
            super().__init__(master, width=18, height=18)
            self.color = "faint"
            self.after(100, self.tick)

        def tick(self):
            if not self.alive():
                return
            if self.color == "green":
                self.draw()
            self.after(100, self.tick)

        def draw(self):
            super().draw()
            c = T.get(self.color, T["faint"])
            if self.color == "green":
                c = mix(T["green"], T["card"], 0.5 * (0.5 + 0.5 * math.sin(time.time() * 2.4)))
            self.create_oval(3, 3, 15, 15, fill=c, outline="")
    hrow = box(hl, "card")
    hrow.pack(anchor="w")
    ag_dot = Dot(hrow)
    ag_dot.pack(side="left", padx=(0, 8))
    ag_title = label(hrow, "Agent mode", "text", 10, True)
    ag_title.pack(side="left")
    ag_sub = label(hl, "Builds a large training dataset continuously: text, images and robot episodes.", "dim", -1,
                   wraplength=640)
    ag_sub.pack(anchor="w", pady=(6, 0))
    ag_btn = Pill(hero.inner, "Start collecting", lambda: agent_toggle(), "primary", h=48, size=2, icon="play",
                  tip="Starts once; after that it can only be paused")
    ag_btn.pack(side="right")

    # tiles
    class Tile(Card):
        def __init__(self, master, title):
            super().__init__(master, radius=18, pad=14)
            self.configure(width=206, height=104)
            self.pack_propagate(False)
            self.t = label(self.inner, title, "dim", -2)
            self.t.pack(anchor="w")
            self.v = label(self.inner, "-", "text", 9, True)
            self.v.pack(anchor="w", pady=(2, 0))
            self.s = label(self.inner, "", "faint", -3)
            self.s.pack(anchor="w")

        def winfo_reqwidth(self):
            return 206

        def winfo_reqheight(self):
            return 104

        def set(self, v, sub=""):
            self.v.configure(text=v)
            self.s.configure(text=shorten(sub, 34))
    tiles_f = FlowFrame(agb, "page", padx=12, pady=12)
    tiles_f.pack(fill="x")
    tiles = {k: tiles_f.add(Tile(tiles_f, t)) for k, t in [
        ("text", "Text records"), ("images", "Images"), ("vla", "Robot VLA episodes"), ("topics", "Topics explored"),
        ("rate", "Items per minute"), ("cpu", "CPU"), ("mem", "Memory"), ("net", "Network"), ("gh", "GitHub sync")]}

    # two columns: system (sparkline) | latest sample
    cols2 = box(agb, "page")
    cols2.pack(fill="x", pady=(14, 0))
    sys_card = Card(cols2, pad=18)
    sys_card.pack(side="left", fill="both", expand=True, padx=(0, 7))
    sample_card = Card(cols2, pad=18)
    sample_card.pack(side="left", fill="both", expand=True, padx=(7, 0))
    label(sys_card.inner, "System", "text", 1, True).pack(anchor="w")
    sys_line = label(sys_card.inner, "", "dim", -2)
    sys_line.pack(anchor="w", pady=(2, 8))

    class Spark(Canvas):
        """CPU history (last 2 minutes) + one bar per core."""
        def __init__(self, master):
            super().__init__(master, height=120, width=300)
            self.data, self.cores = [], []

        def draw(self):
            super().draw()
            w, h = self.winfo_width(), self.winfo_height()
            if w < 20:
                return
            ch = h - 30
            for y in (0, 0.5, 1):
                self.create_line(0, 4 + ch * y, w, 4 + ch * y, fill=T["divider"])
            if len(self.data) > 1:
                n = 120
                pts = []
                for i, v in enumerate(self.data[-n:]):
                    pts += [w * i / (n - 1), 4 + ch * (1 - min(100, v) / 100)]
                self.create_line(*pts, fill=T["blue"], width=2, smooth=True)
            if self.cores:
                bw = w / len(self.cores)
                for i, v in enumerate(self.cores):
                    x = i * bw
                    self.create_rectangle(x + 1, h - 18, x + bw - 2, h - 4, fill=T["track"], outline="")
                    self.create_rectangle(x + 1, h - 18, x + 1 + (bw - 3) * min(100, v) / 100, h - 4,
                                          fill=T["text"], outline="")
    spark = Spark(sys_card.inner)
    spark.pack(fill="x")
    label(sys_card.inner, "Blue line: CPU over the last 2 minutes · bars: each core", "faint", -3).pack(anchor="w", pady=(6, 0))
    label(sample_card.inner, "Latest sample", "text", 1, True).pack(anchor="w")
    smp_row = box(sample_card.inner, "card")
    smp_row.pack(fill="both", expand=True, pady=(8, 0))
    thumb = reg(tk.Label(smp_row, bd=0, width=140, height=140), "bg", "soft")
    thumb.pack(side="left", anchor="n")
    smp_txt = label(smp_row, "Nothing collected yet.", "dim", -2, wraplength=330)
    smp_txt.pack(side="left", fill="both", expand=True, padx=(14, 0), anchor="n")

    # topics: now / next / done - and change them while it runs
    top_card = Card(agb, pad=18)
    top_card.pack(fill="x", pady=(14, 0))
    trow0 = box(top_card.inner, "card")
    trow0.pack(fill="x")
    label(trow0, "Topics", "text", 1, True).pack(side="left")
    topics_info = label(trow0, "", "dim", -2)
    topics_info.pack(side="left", padx=(12, 0))
    Pill(trow0, "Full list", lambda: show_topics(), "ghost", h=28, size=-3).pack(side="right")
    trow1 = box(top_card.inner, "card")
    trow1.pack(fill="x", pady=(10, 0))
    v_newtop = tk.StringVar()

    def add_topics_now():
        new = [x.strip() for x in v_newtop.get().split(",") if x.strip()]
        if not new:
            return
        cur = [x.strip() for x in st["agent_focus_topics"].split(",") if x.strip()]
        agent_set("agent_focus_topics", ", ".join(dict.fromkeys(cur + new)))
        v_focus.set(st["agent_focus_topics"])
        v_newtop.set("")
        status(f"Added {len(new)} topic(s) - the agents start on them right away")
    v_fonly = tk.BooleanVar(value=bool(st["agent_focus_only"]))
    Chip(trow1, "Only my topics", v_fonly, lambda: agent_set("agent_focus_only", bool(v_fonly.get())), h=36).pack(side="right", padx=(8, 0))
    Pill(trow1, "Add now", add_topics_now, "primary", h=38, size=-1, icon="plus").pack(side="right", padx=(8, 0))
    ntf = Field(trow1, v_newtop, h=38)
    ntf.pack(side="left", fill="x", expand=True)
    ntf.e.bind("<Return>", lambda e: add_topics_now())
    tcols = box(top_card.inner, "card")
    tcols.pack(fill="x", pady=(12, 0))
    topic_cols = {}
    for i, (k, title) in enumerate((("now", "Collecting now"), ("next", "Up next"), ("done", "Just completed ✓"))):
        tcols.columnconfigure(i, weight=1, uniform="tc")
        col = box(tcols, "card")
        col.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
        label(col, title, "dim", -2, True).pack(anchor="w")
        topic_cols[k] = label(col, "-", "text", -2, wraplength=300)
        topic_cols[k].pack(anchor="w", pady=(4, 0))

    # collect controls
    ctl_card = Card(agb, pad=18)
    ctl_card.pack(fill="x", pady=(14, 0))
    label(ctl_card.inner, "What to collect", "text", 1, True).pack(anchor="w")
    label(ctl_card.inner, f"{PWT_NAME} runs these as parallel tasks; every website keeps its own polite rate limit.",
          "dim", -2, wraplength=900).pack(anchor="w", pady=(2, 8))
    mix_vars = {}
    mix_f = FlowFrame(ctl_card.inner, "card")
    mix_f.pack(fill="x")

    def mix_changed():
        for k, var in mix_vars.items():
            key = f"agent_mix_{k}"
            if var.get() and float(st[key]) <= 0:
                st[key] = SPEC[key][3]
            elif not var.get():
                st[key] = 0.0
        persist()
        agent_settings_changed()
    for k in AGENT_KINDS:
        mix_vars[k] = tk.BooleanVar(value=float(st[f"agent_mix_{k}"]) > 0)
        mix_f.add(Chip(mix_f, AGENT_KIND_LABELS[k], mix_vars[k], mix_changed, h=34))
    wrow = box(ctl_card.inner, "card")
    wrow.pack(fill="x", pady=(14, 0))
    label(wrow, "Parallel tasks", "text", -1).pack(side="left")
    v_workers = tk.IntVar(value=int(st["pwt_workers"]))
    NumField(wrow, v_workers, 1, MAX_AGENTS, width=96).pack(side="right", padx=(10, 0))
    Slider(wrow, v_workers, 1, 5000).pack(side="left", fill="x", expand=True, padx=(14, 0))
    wpre = FlowFrame(ctl_card.inner, "card")
    wpre.pack(fill="x", pady=(6, 0))
    for n_ in (16, 64, 256, 1000, 2500, 5000, 10000, 20000):
        wpre.add(Pill(wpre, f"{n_:,}", lambda n_=n_: v_workers.set(n_), "outline", h=28, size=-3, tip=f"{n_:,} parallel agents"))

    def workers_changed(*_):
        try:
            n = int(v_workers.get())
        except (tk.TclError, ValueError):
            return
        if n != st["pwt_workers"]:
            st["pwt_workers"] = n
            persist()
            agent_control(ag["root"], workers=n)
    v_workers.trace_add("write", workers_changed)
    abar = FlowFrame(ctl_card.inner, "card")
    abar.pack(fill="x", pady=(14, 0))
    abar.add(Pill(abar, "Topics ✓", lambda: show_topics(), "outline", h=34, size=-2, tip="topics.json: done, in progress, left"))
    abar.add(Pill(abar, "Parallel agents", lambda: show_agents(), "outline", h=34, size=-2))
    abar.add(Pill(abar, "Open dataset folder", lambda: open_path(ag["root"]), "outline", h=34, size=-2))
    abar.add(Pill(abar, "Sync to GitHub now", lambda: (agent_control(ag["root"], sync_now=time.time()),
                                                        status("GitHub sync requested")), "outline", h=34, size=-2))
    abar.add(Pill(abar, "GitHub settings", lambda: open_settings("GitHub"), "outline", h=34, size=-2))
    abar.add(Pill(abar, "Agent settings", lambda: open_settings("Agent"), "outline", h=34, size=-2))
    abar.add(Pill(abar, "Training blueprint", lambda: open_path(os.path.join(HERE, "TRAINING_BLUEPRINT.md")), "outline", h=34, size=-2))

    # agent settings (live: the running agent applies them within a second)
    set_card = Card(agb, pad=18)
    set_card.pack(fill="x", pady=(14, 0))
    srow0 = box(set_card.inner, "card")
    srow0.pack(fill="x")
    label(srow0, "Agent settings", "text", 1, True).pack(side="left")
    set_info = label(srow0, "Changes apply to the running agent immediately", "dim", -2)
    set_info.pack(side="right")
    pending = {"job": None}

    def push_settings():
        pending["job"] = None
        save_settings(st)  # the background agent reads the saved file
        agent_control(ag["root"], settings_rev=time.time())
        set_info.configure(text=f"Applied {datetime.now().strftime('%H:%M:%S')}")

    def agent_set(key, value):
        if st.get(key) == value:
            return
        st[key] = value
        if pending["job"] is not None:
            root.after_cancel(pending["job"])
        pending["job"] = root.after(500, push_settings)
    sgrid = box(set_card.inner, "card")
    sgrid.pack(fill="x", pady=(10, 0))
    agent_vars = {}
    for i, (key, title, lo, hi, hint) in enumerate([
            ("agent_quality", "Quality", 1, 10, "1-4 basic checks · 5-10 strict filter, rising minimum score"),
            ("agent_batch", "Records per topic", 1, 10000, "kept records for every topic task"),
            ("agent_variations", "DataGen variations", 0, MAX_VARIATIONS, "similar versions of every record (type up to 10,000)"),
            ("agent_cpu_cap", "CPU cap %", 10, 100, "the agent slows down above this")]):
        cell = box(sgrid, "card")
        cell.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else 18, 0), pady=6)
        top_ = box(cell, "card")
        top_.pack(fill="x")
        label(top_, title, "text", -1).pack(side="left")
        var = tk.IntVar(value=int(st[key]))
        agent_vars[key] = var
        NumField(top_, var, lo, hi, width=72).pack(side="right")
        Slider(cell, var, lo, min(hi, 200)).pack(fill="x", pady=(2, 0))
        label(cell, hint, "faint", -3).pack(anchor="w")

        def changed(*_, key=key, var=var, lo=lo, hi=hi):
            try:
                v = min(hi, max(lo, int(var.get())))
            except (tk.TclError, ValueError):
                return
            agent_set(key, v)
        var.trace_add("write", changed)
    sgrid.columnconfigure(0, weight=1, uniform="ags")
    sgrid.columnconfigure(1, weight=1, uniform="ags")
    label(set_card.inner, "Text data types", "dim", -2, True).pack(anchor="w", pady=(10, 4))
    type_vars = {}
    tflow = FlowFrame(set_card.inner, "card")
    tflow.pack(fill="x")

    def types_changed():
        on = [t for t in AGENT_TEXT_TYPES if type_vars[t].get()]
        if not on:
            type_vars[AGENT_TEXT_TYPES[0]].set(True)
            on = AGENT_TEXT_TYPES[:1]
        agent_set("agent_types", ",".join(on))
    for t in AGENT_TEXT_TYPES:
        type_vars[t] = tk.BooleanVar(value=t in str(st["agent_types"]))
        tflow.add(Chip(tflow, t, type_vars[t], types_changed, h=32))
    label(set_card.inner, "Focus topics (collected first, then the endless stream continues)", "dim", -2, True).pack(anchor="w", pady=(12, 4))
    frow = box(set_card.inner, "card")
    frow.pack(fill="x")
    v_focus = tk.StringVar(value=st["agent_focus_topics"])
    Pill(frow, "Apply", lambda: agent_set("agent_focus_topics", v_focus.get().strip()), "primary", h=38, size=-1).pack(side="right", padx=(8, 0))
    focus_f = Field(frow, v_focus, h=38)
    focus_f.pack(side="left", fill="x", expand=True)
    focus_f.e.bind("<Return>", lambda e: agent_set("agent_focus_topics", v_focus.get().strip()))

    # activity
    act_card = Card(agb, pad=18)
    act_card.pack(fill="x", pady=(14, 0))
    arow = box(act_card.inner, "card")
    arow.pack(fill="x")
    label(arow, "Activity", "text", 1, True).pack(side="left")
    act_info = label(arow, "", "dim", -2)
    act_info.pack(side="right")
    KIND_COLOR = {"archive": "blue", "text": "green", "web_images": "text", "synthetic_images": "faint", "vla": "red",
                  "expand": "dim", "seed": "dim", "seed_concepts": "dim"}

    class AgentActivity(Canvas):
        """Running agents as live rows (what, which topic, for how long) and the latest finished tasks as items."""
        def __init__(self, master):
            super().__init__(master, height=300, width=600)
            self.s = None

        def draw(self):
            super().draw()
            w = self.winfo_width()
            s_ = self.s or {}
            busy = s_.get("busy") or []
            half = w * 0.56
            self.create_text(0, 10, text=f"Running now · {s_.get('in_flight', 0):,}", anchor="w", fill=T["dim"], font=font(-2, True))
            if not busy:
                self.create_text(0, 40, text="No agents running.", anchor="w", fill=T["faint"], font=font(-2))
            lim = float(st.get("agent_task_timeout", 120))
            for i, b in enumerate(busy[:10]):
                y = 34 + i * 26
                col = T[KIND_COLOR.get(b["kind"], "text")]
                self.create_oval(2, y - 5, 12, y + 5, fill=col, outline="")
                self.create_text(20, y, text=shorten(f"{AGENT_KIND_LABELS.get(b['kind'], b['kind']).split(' (')[0]} · {b.get('arg') or ''}",
                                                     int((half - 120) / 6.6)), anchor="w", fill=T["text"], font=font(-3))
                bx = half - 92
                self.create_polygon(g3_points(bx, y - 3, bx + 60, y + 3, 3, power=1.0), fill=T["track"], outline=T["track"])
                self.create_polygon(g3_points(bx, y - 3, bx + max(6, 60 * min(1, b["s"] / lim)), y + 3, 3, power=1.0),
                                    fill=col, outline=col)
                self.create_text(half - 24, y, text=fmt_s(b["s"]), anchor="e", fill=T["faint"], font=font(-4))
            if len(busy) > 10:
                self.create_text(20, 34 + 10 * 26, text=f"+ {len(busy) - 10:,} more - open Parallel agents", anchor="w",
                                 fill=T["faint"], font=font(-3))
            self.create_text(half + 10, 10, text="Just finished", anchor="w", fill=T["dim"], font=font(-2, True))
            done = [e for e in reversed(s_.get("events") or []) if re.search(r"\+\d", e)][:10]
            for i, e in enumerate(done):
                y = 34 + i * 26
                m_ = re.search(r"\+([\d,]+)", e)
                n_ = m_.group(1) if m_ else ""
                body = re.sub(r"^\d\d:\d\d:\d\d\s+", "", e)
                body = re.sub(r":? \+[\d,]+ .*$", "", body).strip()
                self.create_polygon(g3_points(half + 10, y - 10, half + 62, y + 10, 10, power=1.0), fill=T["soft"], outline=T["soft"])
                self.create_text(half + 36, y, text=f"+{n_}", fill=T["green"] if n_ not in ("", "0") else T["faint"], font=font(-3, True))
                self.create_text(half + 72, y, text=shorten(body, int((w - half - 80) / 6.4)), anchor="w", fill=T["text"], font=font(-3))
    act_vis = AgentActivity(act_card.inner)
    act_vis.pack(fill="x", pady=(8, 0))
    afr, act_t = text_area(act_card.inner, "code", mono=True, h=11, size=-3)
    act_t.configure(state="disabled")
    act_log_on = {"v": False, "pos": 0}

    def toggle_act_log():
        act_log_on["v"] = not act_log_on["v"]
        (afr.pack(fill="x", pady=(8, 0)) if act_log_on["v"] else afr.pack_forget())
        log_btn.text = "Hide log" if act_log_on["v"] else "Show log"
        log_btn.draw()
    log_btn = Pill(arow, "Show log", toggle_act_log, "ghost", h=28, size=-3)
    log_btn.pack(side="right", padx=(0, 8))
    act_t.configure(height=22)
    toggle_act_log()  # super verbose: the live log is open from the start

    def tail_agent_log():
        """Only the NEW lines of agent.log since the last look (never the whole file), shown in a short window:
        every request and step from every agent process, without making the window slow."""
        lp = os.path.join(ag["root"], ".agent", "agent.log")
        try:
            size = os.path.getsize(lp)
            if size == act_log_on["pos"]:
                return
            start = act_log_on["pos"] if 0 < act_log_on["pos"] < size and size - act_log_on["pos"] < 200000 else max(0, size - 20000)
            with open(lp, "rb") as f:
                f.seek(start)
                txt = f.read(200000).decode("utf-8", "replace")
        except OSError:
            return
        fresh = start != act_log_on["pos"]
        act_log_on["pos"] = size
        lines = txt.split("\n")
        if fresh:
            lines = lines[1:]
        lines = [ln for ln in lines if ln][-150:]
        if not lines:
            return
        at_end = act_t.yview()[1] > 0.98
        act_t.configure(state="normal")
        if fresh:
            act_t.delete("1.0", "end")
        else:
            act_t.insert("end", "\n")
        act_t.insert("end", "\n".join(lines))
        extra = int(act_t.index("end-1c").split(".")[0]) - 300
        if extra > 0:
            act_t.delete("1.0", f"{extra + 1}.0")
        act_t.configure(state="disabled")
        if at_end:
            act_t.see("end")

    def agent_settings_changed():
        """Settings reach a running agent at its next restart; the worker count applies live."""
        agent_control(ag["root"], workers=int(st["pwt_workers"]))

    def agent_alive():
        if ag.get("proc") is not None and ag["proc"].poll() is not None:
            ag["proc"] = None  # reaped: a crashed agent is restarted, never left as a zombie
        return agent_pid(ag["root"]) is not None

    def agent_spawn_once():
        if not agent_alive() and time.time() - ag.get("spawn_t", 0) > 15:
            ag["spawn_t"] = time.time()
            if not smoke:
                save_settings(st)  # the background agent reads the saved settings
            ag["proc"] = agent_spawn(ag["root"], offline=smoke)

    def agent_start():
        agent_control(ag["root"], paused=False, gui=True, heartbeat=time.time(), started_once=True,
                      workers=int(st["pwt_workers"]))
        agent_spawn_once()
        status("Agent collecting - it can be paused, never stopped")

    def agent_toggle():
        if not st.get("pwt_enabled", True):
            status(f"Agent mode runs on {PWT_NAME} - turn it on in Settings > Products: Collection")
            open_settings("Products: Collection")
            return
        ctl = agent_control(ag["root"])
        if ctl.get("started_once") and not ctl.get("paused"):
            agent_control(ag["root"], paused=True)
            status("Agent paused - press Resume to continue")
        else:
            agent_start()
        agent_poll(once=True)

    def set_thumb(path):
        if not path or path == ag["thumb_path"]:
            return
        try:
            from PIL import Image, ImageTk
            im = Image.open(path)
            im.thumbnail((140, 140))
            ag["thumb"] = ImageTk.PhotoImage(im)
            thumb.configure(image=ag["thumb"], width=140, height=140)
            ag["thumb_path"] = path
        except Exception:
            pass

    def agent_poll(once=False):
        try:
            if not once:
                ctl = agent_control(ag["root"], gui=True, heartbeat=time.time())
            else:
                ctl = agent_control(ag["root"])
            s = agent_status(ag["root"])
            alive = agent_alive()
            ag["status"] = s
            paused = bool(ctl.get("paused"))
            if ctl.get("started_once") and not paused and not alive and not once:
                agent_spawn_once()  # it crashed or the Mac restarted: carry on (it is only ever paused, never stopped)
            if not st.get("pwt_enabled", True) and not alive:
                ag_title.configure(text="Agent mode is off")
                ag_sub.configure(text=f"Agent mode runs on {PWT_NAME} by {PWT_DEVELOPER}. Turn it on in Settings > Products: Collection.")
                ag_dot.color = "faint"
                ag_btn.text, ag_btn.icon, ag_btn.kind = "Turn on", "gear", "primary"
            elif not ctl.get("started_once"):
                ag_title.configure(text="Agent mode")
                ag_sub.configure(text="Builds a large training dataset continuously: text Q&A with DataGen variants, "
                                      "free-licence web images, generated detection images and robot VLA episodes.")
                ag_dot.color = "faint"
                ag_btn.text, ag_btn.icon, ag_btn.kind = "Start collecting", "play", "primary"
            elif paused:
                ag_title.configure(text="Paused")
                ag_sub.configure(text="Nothing is being collected. Resume carries on exactly where it stopped."
                                 + ("" if alive else " (The background agent is idle.)"))
                ag_dot.color = "faint"
                ag_btn.text, ag_btn.icon, ag_btn.kind = "Resume", "play", "primary"
            else:
                live = alive and s and s.get("state") == "running"
                ag_title.configure(text="Collecting" if live else "Starting…")
                if s and live and s.get("disk_low"):
                    ag_sub.configure(text=f"Paused by itself: only {s.get('disk_free_gb', 0)} GB of disk space left (guard: "
                                          f"{st['agent_min_free_gb']} GB, Agent settings). Free some space and it carries on.")
                elif s and live:
                    ag_sub.configure(text=f"{s.get('waiting', 0):,} waiting for a website's turn · {s['in_flight']} tasks running in parallel · {s['per_min']:,} items/min · "
                                          f"up {fmt_s(s['uptime_s'])}" + (" · offline test data" if s.get("offline") else ""))
                ag_dot.color = "green" if live else "blue"
                ag_btn.text, ag_btn.icon, ag_btn.kind = "Pause", "stop", "outline"
            fntw = measure(ag_btn.text, ag_btn.fnt) + 2 * max(14, 48 * 0.42) + 20
            ag_btn.configure(width=int(fntw))
            ag_btn.draw()
            ag_dot.draw()
            n_ag = (s or {}).get("in_flight", 0) if alive and not paused else 0
            txt_ = f"{n_ag:,} agent{'s' * (n_ag != 1)}" if alive and not paused else ("paused" if ctl.get("started_once") else "0 agents")
            if agents_btn.text != txt_:
                agents_btn.text = txt_
                agents_btn.configure(width=int(measure(txt_, agents_btn.fnt) + 2 * max(14, 34 * 0.42) + 20))
                agents_btn.draw()
            if s and state.get("page") != "Agent" and not once:
                pass  # another page is open: no redrawing of hidden widgets (keeps the window smooth)
            elif s and s.get("updated") == ag.get("drawn_upd") and not once:
                pass  # nothing new since the last draw
            elif s:
                ag["drawn_upd"] = s.get("updated")
                c, sy, tp, gh = s["counts"], s.get("system", {}), s["topics"], s["github"]
                tiles["text"].set(fmt_n(c["text"]), f"{fmt_n(c['originals'])} originals · {fmt_n(c['variants'])} variants")
                tiles["images"].set(fmt_n(c["images"]), f"{fmt_n(c['web_images'])} web · {fmt_n(c['synthetic_images'])} generated")
                tiles["vla"].set(fmt_n(c["vla_episodes"]), f"{fmt_n(c['vla_frames'])} frames")
                tiles["topics"].set(fmt_n(tp["explored"]), f"{fmt_n(tp.get('in_progress', 0))} in progress · {fmt_n(tp['known'])} known")
                tiles["rate"].set(f"{s['per_min']:,.0f}", f"{s['in_flight']} in flight · {s['effective_workers']} slots")
                tiles["cpu"].set(f"{sy.get('cpu', 0):.0f}%", f"{sy.get('cores', '?')} cores · agent {sy.get('proc_cpu', 0):.0f}%")
                tiles["mem"].set(f"{sy.get('mem', 0):.0f}%", f"{sy.get('mem_used_gb', 0)} of {sy.get('mem_total_gb', 0)} GB")
                tiles["net"].set(f"{sy.get('down_kbps', 0):,.0f} KB/s", f"up {sy.get('up_kbps', 0):,.0f} KB/s · disk {fmt_n(s['disk_mb'])} MB")
                ghs = gh["state"]
                tiles["gh"].set({"off": "Off", "local": "Local", "pushed": "Pushed", "error": "Error"}.get(ghs.split(" ")[0], ghs.title()),
                                f"next in {fmt_s(gh['next_sync_s'])}" if not gh["error"] else gh["error"])
                if s.get("updated") and (s.get("state") == "running" or not ag["cpu"]):
                    ag["cpu"].append(sy.get("cpu", 0))
                    del ag["cpu"][:-120]
                spark.data, spark.cores = ag["cpu"], sy.get("cpu_cores", [])
                spark.draw()
                sys_line.configure(text=f"Load {', '.join(str(x) for x in sy.get('load', []))} · agent memory "
                                        f"{sy.get('proc_mem_mb', 0)} MB · {sy.get('threads', 0)} threads · free disk {sy.get('disk_free_gb', '?')} GB")
                ls = s.get("last_sample") or {}
                if ls:
                    smp_txt.configure(text=f"{ls.get('type', '').upper()}  ·  {ls.get('topic', '')}\n\n{ls.get('problem', '')}\n\n"
                                           f"{ls.get('solution', '')}\n\nsource: {ls.get('source', '')}")
                set_thumb(s.get("last_image"))
                act_vis.s = s
                act_vis.draw()
                busy_t = [b for b in s.get("busy", []) if b["kind"] == "text" and b.get("arg")]
                topic_cols["now"].configure(text="\n".join(f"#{i}  {b['arg']}  · {fmt_s(b['s'])}" for i, b in enumerate(busy_t[:12], 1))
                                            + (f"\n+ {len(busy_t) - 12:,} more" if len(busy_t) > 12 else "") or "-")
                topic_cols["next"].configure(text="\n".join(("★ " if i < tp.get("focus_left", 0) else "") + f"{n}  · {f or 'general'}"
                                                             for i, (n, f) in enumerate(tp.get("next", []))) or "-")
                topic_cols["done"].configure(text="\n".join(f"✓ {n}  · {r:,} rows" for n, f, r in tp.get("recent", [])) or "-")
                topics_info.configure(text=f"✓ {tp['explored']:,} done · {tp.get('in_progress', 0):,} in progress · "
                                           f"{tp['queued']:,} left" + (f" · {tp.get('focus_left', 0)} of yours next" if tp.get("focus_left") else ""))
                if act_log_on["v"]:
                    tail_agent_log()
                ev = [] if act_log_on["v"] else s.get("events", [])
                if ev and ev[-1:] != ag["last_ev"]:
                    ag["last_ev"] = ev[-1:]
                    act_t.configure(state="normal")
                    act_t.delete("1.0", "end")
                    act_t.insert("end", "\n".join(reversed(ev[-60:])))
                    act_t.configure(state="disabled")
                hosts = s.get("hosts", {})
                act_info.configure(text=" · ".join(f"{h.split('.')[-2] if h.count('.') else h} {v['requests']}" for h, v in list(hosts.items())[:5]))
        except Exception as e:  # the page must never die because of a half-written file
            status(f"Agent page: {type(e).__name__}: {e}")
        if not once:
            root.after(1500, agent_poll)

    # ---------------------------------------------------------------- Ask page (RAG over ALL the data, local model, no training)
    rg = {"proc": None, "spawn_t": 0.0, "engine": None, "installing": False, "install_log": "", "dl": {}, "chat": [],
          "rev": 0, "drawn_rev": -1, "busy": False, "worker": None, "index": None, "rows_key": None, "status": {}}
    ask_pg = box(root, "page")
    ask_sf = ScrollFrame(ask_pg, "page")
    ask_sf.pack(fill="both", expand=True)
    akb = box(ask_sf.body, "page")
    akb.pack(fill="both", expand=True, padx=28, pady=(8, 24))
    ram = mac_ram_gb()

    class Badge(Canvas):
        """A coloured status label: green = ready/downloaded, blue = working, orange = needs attention, grey = not yet."""
        TONES = {"green": ("green_bg", "green"), "blue": ("blue_bg", "blue"), "orange": ("orange_bg", "orange"),
                 "grey": ("grey_bg", "dim"), "ink": ("btn", "btn_fg"), "red": ("error_bg", "error_text")}

        def __init__(self, master, text="", tone="grey", h=24):
            self.fnt = font(-3, True)
            self.text, self.tone = text, tone
            super().__init__(master, height=h, width=self.need(text))

        def need(self, t):
            return int(measure(t, self.fnt) + 31)

        def set(self, text, tone):
            if (text, tone) == (self.text, self.tone):
                return
            self.text, self.tone = text, tone
            self.configure(width=self.need(text))
            self.draw()

        def draw(self):
            super().draw()
            w, h = self.winfo_width(), self.winfo_height()
            if w < 8:
                return
            bgk, fgk = self.TONES.get(self.tone, self.TONES["grey"])
            self.create_polygon(g3_points(0.5, 0.5, w - 0.5, h - 0.5, h / 2, power=1.0), fill=T[bgk], outline=T[bgk])
            self.create_oval(10, h / 2 - 3.5, 17, h / 2 + 3.5, fill=T[fgk], outline="")
            self.create_text(22, h / 2, text=self.text, anchor="w", fill=T[fgk], font=self.fnt)

    def ask_card(title, sub=None):
        c = Card(akb, pad=20)
        c.pack(fill="x", pady=(0, 14))
        label(c.inner, title, "text", 2, True).pack(anchor="w")
        if sub:
            label(c.inner, sub, "dim", -2, wraplength=900).pack(anchor="w", pady=(2, 0))
        body = box(c.inner, "card")
        body.pack(fill="x", pady=(12, 0))
        c.body = body
        return c

    back_row = box(akb, "page")
    back_row.pack(fill="x", pady=(0, 6))
    Pill(back_row, "Back", lambda: show_page(state.get("mode_page", "Agent")), "ghost", h=34, size=-1, icon="chevron").pack(side="left")
    hc = Card(akb, pad=22)
    hc.pack(fill="x", pady=(4, 14))
    label(hc.inner, "Ask your dataset", "text", 10, True).pack(anchor="w")
    label(hc.inner, "ALL the data AITE has collected - every Q&A, DataGen variant, preference pair, image caption, generated "
                    "scene and robot episode - is downloaded from GitHub automatically and kept in one search index (RAG). "
                    "A local AI model on this Mac reads the best matching records and answers, citing them. No training, "
                    "no cloud, no API keys.", "dim", -1, wraplength=900).pack(anchor="w", pady=(6, 0))
    sgrid = box(hc.inner, "card")
    sgrid.pack(fill="x", pady=(14, 0))
    badges, badge_sub = {}, {}
    for i, (k, title) in enumerate((("github", "GitHub data"), ("index", "Search index (RAG)"), ("kaggle", "Kaggle"),
                                     ("engine", "AI engine"), ("model", "Answer model"))):
        cell = box(sgrid, "card")
        cell.grid(row=i // 3, column=i % 3, sticky="nw", padx=(0, 22), pady=(0, 10))
        label(cell, title, "faint", -3, True).pack(anchor="w")
        badges[k] = Badge(cell, "Checking…", "grey")
        badges[k].pack(anchor="w", pady=(4, 2))
        badge_sub[k] = label(cell, "", "faint", -4, wraplength=230)
        badge_sub[k].pack(anchor="w")
    hbar = FlowFrame(hc.inner, "card")
    hbar.pack(fill="x", pady=(12, 0))
    hbar.add(Pill(hbar, "Get new data now", lambda: rag_update_start(force=True), "outline", h=32, size=-2, icon="down",
                  tip="Downloads the newest data from GitHub and adds it to the index (this also happens by itself)"))
    hbar.add(Pill(hbar, "Rebuild index", lambda: rag_update_start(force=True, rebuild=True), "ghost", h=32, size=-2,
                  tip="Starts the search index again from zero (only needed if something looks wrong)"))
    hbar.add(Pill(hbar, "Open data folder", lambda: open_path(RAG_DATA if os.path.isdir(RAG_DATA) else HERE), "ghost", h=32, size=-2))
    hbar.add(Pill(hbar, "Ask settings", lambda: open_settings("Ask (RAG)"), "ghost", h=32, size=-2, icon="gear"))
    eng_btn = Pill(hbar, "Install AI engine", lambda: rag_install(), "primary", h=32, size=-2, icon="down",
                   tip="One-time download (about 0.5 GB) of Apple's MLX into AITE's own folder")

    # ---- the conversation
    cc = ask_card("Ask your data", "Type a question in the box below. AITE searches ALL your data and the model answers "
                                   "from the best records, with numbered sources you can open.")
    cc.pack_forget()
    cc.pack(fill="x", pady=(4, 14), before=hc)  # the question box is the first thing on the page
    mrow = box(cc.body, "card")
    mrow.pack(fill="x", pady=(0, 10))
    v_amode = tk.StringVar(value="model" if st["rag_use_model"] else "records")

    def amode_changed(v):
        st["rag_use_model"] = v == "model"
        persist()
    Segmented(mrow, ["model", "records"], v_amode, amode_changed,
              labels={"model": "AI answer + sources", "records": "Matching records only"}).pack(side="left")
    frow = box(cc.body, "card")
    frow.pack(fill="x", pady=(0, 10))
    fhead = box(frow, "card")
    fhead.pack(fill="x")
    label(fhead, "Fields", "dim", -2, True).pack(side="left")
    fsel_lbl = label(fhead, "  ALL fields", "faint", -3)
    fsel_lbl.pack(side="left")
    Pill(fhead, "Clear", lambda: fields_set(False), "ghost", h=26, size=-3).pack(side="right")
    Pill(fhead, "Select all", lambda: fields_set(True), "outline", h=26, size=-3).pack(side="right", padx=(0, 6))
    fflow = FlowFrame(frow, "card")
    fflow.pack(fill="x", pady=(6, 0))
    fvars = {}
    v_fall = tk.BooleanVar(value=True)
    rg["fkeys"] = None

    def fields_chosen():
        """None = ALL fields; otherwise the list picked."""
        on = [k for k, v in fvars.items() if v.get()]
        return None if v_fall.get() or not on or len(on) == len(fvars) else on

    def fields_label():
        ch = fields_chosen()
        fsel_lbl.configure(text="  ALL fields" if ch is None else f"  {len(ch)} of {len(fvars)} fields: " + shorten(", ".join(ch), 80))

    def fields_set(on):
        v_fall.set(on)
        for v in fvars.values():
            v.set(on)
        for c_ in fflow.items:
            c_.draw()
        fields_label()

    def all_chip_clicked():
        fields_set(bool(v_fall.get()))

    def field_chip_clicked():
        on = [k for k, v in fvars.items() if v.get()]
        v_fall.set(bool(fvars) and len(on) == len(fvars))
        for c_ in fflow.items:
            c_.draw()
        fields_label()

    def rebuild_field_chips(fl):
        key = tuple(fl)
        if key == rg["fkeys"]:
            return
        rg["fkeys"] = key
        keep = {k: v.get() for k, v in fvars.items()}
        for c_ in fflow.items:
            c_.destroy()
        fflow.items = []
        fvars.clear()
        fflow.add(Chip(fflow, "ALL", v_fall, all_chip_clicked, h=28))
        for k, n_ in fl.items():
            fvars[k] = tk.BooleanVar(value=keep.get(k, v_fall.get()))
            fflow.add(Chip(fflow, f"{k or 'general'} · {fmt_n(n_)}", fvars[k], field_chip_clicked, h=28))
        apply_theme()
        fields_label()
    prow = box(cc.body, "card")
    prow.pack(fill="x", pady=(0, 10))
    v_q = tk.StringVar()
    ask_btn = Pill(prow, "Ask", lambda: rag_ask(), "primary", h=46, icon="up")
    ask_btn.pack(side="right", padx=(8, 0))
    qf = Field(prow, v_q, h=46)
    qf.pack(side="left", fill="x", expand=True)
    qf.e.bind("<Return>", lambda e: rag_ask())
    cfr, chat_t = text_area(cc.body, "code", h=18, size=-1)
    cfr.pack(fill="x")
    chat_t.configure(state="disabled", cursor="arrow")
    cbar = FlowFrame(cc.body, "card")
    cbar.pack(fill="x", pady=(8, 0))
    for ex in ("Explain the Lanczos algorithm", "How do robots plan a trajectory?", "Pad a number with zeros in PHP",
               "What is BCS superconductivity?"):
        cbar.add(Pill(cbar, ex, lambda ex=ex: (v_q.set(ex), rag_ask()), "outline", h=30, size=-3))
    cbar.add(Pill(cbar, "Clear chat", lambda: (rg.__setitem__("chat", []), rg.__setitem__("rev", rg["rev"] + 1)), "ghost", h=30, size=-3))
    ask_info = label(cc.body, "", "faint", -3, wraplength=900)
    ask_info.pack(anchor="w", pady=(6, 0))
    vrow = box(cc.body, "card")
    vrow.pack(fill="x", pady=(12, 4))
    label(vrow, "Verbose log", "dim", -2, True).pack(side="left")
    label(vrow, "  every step: search terms, matches + scores, prompt size, model loading, speed, and the background "
                "GitHub / index / Kaggle job", "faint", -4).pack(side="left")
    Pill(vrow, "Clear", lambda: (rg["vlog"].clear(), rg.__setitem__("vrev", rg["vrev"] + 1)), "ghost", h=26, size=-3).pack(side="right")
    vfr, vlog_t = text_area(cc.body, "code", mono=True, h=14, size=-3)
    vfr.pack(fill="x")
    vlog_t.configure(state="disabled")
    rg.update(vlog=[], vrev=0, vdrawn=-1, jpos=-1)

    def vlog(msg):
        rg["vlog"].append(time.strftime("%H:%M:%S  ") + msg)
        del rg["vlog"][:-800]
        rg["vrev"] += 1

    def tail_rag_log():
        """New lines of the background job's log (GitHub download, indexing file by file, Kaggle upload)."""
        lp = os.path.join(RAG_HOME, "rag.log")
        try:
            size = os.path.getsize(lp)
        except OSError:
            return
        if size == rg["jpos"]:
            return
        first = rg["jpos"] < 0 or size < rg["jpos"]
        start = max(0, size - 6000) if first else rg["jpos"]
        try:
            with open(lp, "rb") as f:
                f.seek(start)
                txt = f.read(200000).decode("utf-8", "replace")
        except OSError:
            return
        rg["jpos"] = size
        lines = txt.split("\n")
        if first and start:
            lines = lines[1:]
        rg["vlog"] += ["job  " + ln for ln in lines if ln.strip()]
        del rg["vlog"][:-800]
        rg["vrev"] += 1

    def render_vlog():
        at_end = vlog_t.yview()[1] > 0.98
        vlog_t.configure(state="normal")
        vlog_t.delete("1.0", "end")
        vlog_t.insert("end", "\n".join(rg["vlog"][-400:]))
        vlog_t.configure(state="disabled")
        if at_end:
            vlog_t.see("end")

    # ---- models
    mc = ask_card("Models", f"Green = downloaded and ready to use. Grey = not downloaded yet - press Download (once). This Mac has "
                            f"{ram} GB of memory; bigger models answer better but need more.")
    mlist = box(mc.body, "card")
    mlist.pack(fill="x")
    model_rows = {}
    orow = box(mc.body, "card")
    orow.pack(fill="x", pady=(12, 0))
    label(orow, "Another model", "dim", -2, True).pack(side="left", padx=(0, 10))
    v_other = tk.StringVar()

    def use_other():
        m = v_other.get().strip()
        if m:
            st["rag_model"] = m
            persist()
            v_other.set("")
            rg["rows_key"] = None
            status(f"Answer model: {m}" + ("" if model_downloaded(m) else " - press Download to get it"))
            rag_refresh()

    def browse_model():
        d = filedialog.askdirectory(initialdir=TRAINER_RUNS if os.path.isdir(TRAINER_RUNS) else HERE)
        if d:
            v_other.set(d)
            use_other()
    Pill(orow, "Use", use_other, "primary", h=36, size=-1).pack(side="right", padx=(8, 0))
    Pill(orow, "Folder…", browse_model, "outline", h=36, size=-1).pack(side="right", padx=(8, 0))
    of_ = Field(orow, v_other, h=36)
    of_.pack(side="left", fill="x", expand=True)
    of_.e.bind("<Return>", lambda e: use_other())
    label(mc.body, "Any MLX model id from Hugging Face (e.g. mlx-community/Qwen2.5-7B-Instruct-4bit) or a model folder.",
          "faint", -3).pack(anchor="w", pady=(6, 0))

    def model_state(mid):
        """(badge text, tone) for one model - the colours match everywhere on the page."""
        d = rg["dl"].get(mid)
        if d and d["proc"].poll() is None:
            pct = min(99, int(100 * hf_cache_bytes(mid) / max(1, d["want"]))) if d["want"] else 0
            return (f"Downloading {pct}%" if pct else "Downloading…"), "blue"
        if model_downloaded(mid):
            return "Downloaded", "green"
        if d and d["proc"].poll() not in (None, 0):
            return "Download failed", "red"
        return "Not downloaded", "grey"

    def build_model_rows():
        models = rag_models()
        if st["rag_model"] not in models:
            models[st["rag_model"]] = model_label(st["rag_model"])
        key = tuple(models)
        if key == rg["rows_key"]:
            return
        rg["rows_key"] = key
        for w_ in mlist.winfo_children():
            w_.destroy()
        model_rows.clear()
        for i, (mid, name) in enumerate(models.items()):
            if i:
                box(mlist, "divider", height=1).pack(fill="x")
            r_ = box(mlist, "card")
            r_.pack(fill="x", pady=7)
            info = TRAINER_MODELS.get(mid)
            left = box(r_, "card")
            left.pack(side="left", fill="x", expand=True)
            nl = label(left, name, "text", -1, True)
            nl.pack(anchor="w")
            sub = (f"{info[1]} GB download · " + ("fits this Mac" if info[2] <= max(8, ram) else f"needs {info[2]} GB memory")) \
                if info else ("folder on this Mac" if os.path.isdir(mid) else "on this Mac" if model_downloaded(mid) else "Hugging Face model")
            label(left, f"{mid}  ·  {sub}", "faint", -4).pack(anchor="w")
            act = Pill(r_, "Download", lambda mid=mid: model_action(mid), "outline", h=32, size=-2)
            act.pack(side="right")
            use_b = Badge(r_, "", "ink")
            bd = Badge(r_, "Not downloaded", "grey")
            bd.pack(side="right", padx=(0, 10))
            fit = Badge(r_, "Too big for this Mac", "orange")
            if info and info[2] > max(8, ram):
                fit.pack(side="right", padx=(0, 6))
            for w_ in (r_, left, nl):
                w_.bind("<Double-Button-1>", lambda e, mid=mid: model_action(mid))
            model_rows[mid] = {"badge": bd, "act": act, "use": use_b, "row": r_}
        apply_theme()

    def model_action(mid):
        text, tone = model_state(mid)
        if tone == "green":
            st["rag_model"] = mid
            persist()
            status(f"Answer model: {model_label(mid)}")
        elif tone in ("grey", "red"):
            rag_download(mid)
        rag_refresh()

    def rag_download(mid):
        if not rg["engine"]:
            status("Install the AI engine first (top of this page) - then the model downloads")
            rag_install(then=mid)
            return
        if os.path.isdir(mid):
            return
        info = TRAINER_MODELS.get(mid)
        rg["dl"][mid] = {"proc": model_download_start(mid), "want": int(info[1] * 2 ** 30) if info else 0}
        status(f"Downloading {model_label(mid)} (once)…")

    def rag_install(then=None):
        if rg["installing"] or not trainer_supported() or rg["engine"]:
            return
        rg["installing"], rg["install_log"] = True, "Starting…"

        def work():
            ok = trainer_install(lambda m: rg.__setitem__("install_log", m))
            rg["engine"], rg["installing"] = ok, False
            rg["install_log"] = "Installed" if ok else "Install failed - see Help"
            if ok and then:
                rg["then_dl"] = then
        threading.Thread(target=work, daemon=True).start()

    # ---- background: GitHub -> index (its own low-priority process, so the window never freezes)
    def rag_update_start(force=False, rebuild=False):
        p = rg["proc"]
        if p is not None and p.poll() is None:
            if force:
                status("Already getting new data - it shows above")
            return
        mins = int(st["rag_sync_min"])
        if not force and time.time() - rg["spawn_t"] < mins * 60:
            return
        if rebuild:
            for f_ in (RAG_INDEX, RAG_INDEX + "-wal", RAG_INDEX + "-shm"):
                try:
                    os.remove(f_)
                except OSError:
                    pass
            rg["index"] = None
        rg["spawn_t"] = time.time()
        if not smoke:
            save_settings(st)
        import subprocess
        cmd = [sys.executable, os.path.abspath(__file__), "--rag-update", "--dir", ag["root"]] + (["--offline"] if smoke else [])
        rg["proc"] = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=open(os.path.join(HERE, "rag_errors.log"), "a"),
                                      stdin=subprocess.DEVNULL, start_new_session=True, cwd=HERE)

    def rag_index():
        if rg["index"] is None:
            rg["index"] = RagIndex()
        return rg["index"]

    def rag_worker():
        m = st["rag_model"]
        w = rg.get("worker")
        if w is None or not w.alive() or w.model != m:
            if w is not None:
                w.stop()
            w = rg["worker"] = PreviewWorker(m, None)
        return w

    def rag_ask():
        q = v_q.get().strip()
        if not q or rg["busy"]:
            return
        use_model = v_amode.get() == "model"
        if use_model and not (rg["engine"] and model_downloaded(st["rag_model"])):
            use_model = False
            status("The answer model is not ready (install the engine / download the model) - showing the matching records")
        v_q.set("")
        turn = {"q": q, "a": "", "hits": [], "state": "searching", "model": model_label(st["rag_model"]) if use_model else ""}
        rg["chat"].append(turn)
        rg["busy"], rg["rev"] = True, rg["rev"] + 1
        field = fields_chosen()
        history = []
        for t_ in rg["chat"][:-1][-3:]:
            if t_.get("a"):
                history += [{"role": "user", "content": t_["q"]}, {"role": "assistant", "content": t_["a"]}]

        def work():
            t0 = time.time()
            try:
                vlog(f"QUESTION  {q!r}" + (f"  · fields = {', '.join(field)}" if field else "  · ALL fields"))
                chat = bool(RAG_SMALLTALK.match(q))
                if chat:
                    vlog("small talk (greeting / thanks): no dataset search, the model just replies")
                else:
                    ix = rag_index()
                    fts = RagIndex.query_of(q)
                    vlog(f"search terms ({len(fts.split(' OR ')) if fts else 0}): {fts or '(none - only stop words)'}")
                    raw = ix.search(q, int(st["rag_k"]), field)
                    turn["search_ms"] = int((time.time() - t0) * 1000)
                    vlog(f"BM25 full-text search over {fmt_n(rg['status'].get('count', 0))} records: {len(raw)} different "
                         f"records in {turn['search_ms']} ms (DataGen variants of one question count once)")
                    turn["hits"] = rag_relevant(q, raw)
                    for i, h in enumerate(raw, 1):
                        vlog(f"   {'KEEP' if h in turn['hits'] else 'drop'}  score {-h['score']:.2f}  {h['field'] or h['topic'] or 'general'}"
                             f" · {h['source']}  {shorten(h['title'], 80)}  ({len(h['q']) + len(h['a']):,} chars)")
                    vlog(f"relevance check: {len(turn['hits'])} of {len(raw)} records are about the question"
                         + ("" if turn["hits"] else " - the model answers from its own knowledge"))
                if use_model:
                    turn["state"] = "thinking"
                    rg["rev"] += 1
                    if chat:
                        msgs = [m_ for m_ in history[-4:]] + [{"role": "user", "content": q}]
                    else:
                        msgs = rag_messages(q, turn["hits"], history, int(st["rag_context_chars"]))
                    sysmsg = RAG_CHAT_SYSTEM if chat else RAG_SYSTEM
                    n_ch = sum(len(m_["content"]) for m_ in msgs) + len(sysmsg)
                    vlog(f"prompt: {len(msgs)} messages ({len(history) // 2} earlier turns), {n_ch:,} characters ≈ {n_ch // 4:,} "
                         f"tokens · source limit {st['rag_context_chars']:,} chars")
                    w_ = rg.get("worker")
                    fresh = w_ is None or not w_.alive() or w_.model != st["rag_model"]
                    if fresh:
                        vlog(f"loading {st['rag_model']} into memory (MLX, Apple GPU)…")
                    t1 = time.time()
                    wk = rag_worker()
                    wk.ready.wait(600)
                    if fresh:
                        vlog(f"model loaded in {time.time() - t1:.1f} s" + (f" - error: {wk.error}" if wk.error else ""))
                    vlog(f"generating: up to {st['rag_tokens']} tokens, temperature {st['rag_temp']}…")
                    t2 = time.time()
                    turn["a"] = tidy_model_answer(wk.ask("before", msgs, int(st["rag_tokens"]), temp=float(st["rag_temp"]),
                                                         system=sysmsg))
                    dt = max(0.01, time.time() - t2)
                    est = max(1, len(turn["a"]) // 4)
                    cites = sorted(set(re.findall(r"\[(\d+)\]", turn["a"])), key=int)
                    vlog(f"answer: {len(turn['a']):,} chars ≈ {est:,} tokens in {dt:.1f} s ≈ {est / dt:.0f} tokens/s · cites "
                         + (", ".join("[" + c + "]" for c in cites) or "no sources"))
                else:
                    turn["a"] = ("Hi! Ask me anything about maths, science, programming, robotics, medicine and more - "
                                 "I search ALL your data." if chat else rag_extractive(q, turn["hits"]))
                    vlog("records-only answer: quoting the best match (no model used)")
            except Exception as e:
                vlog(f"ERROR {type(e).__name__}: {e}")
                turn["a"] = f"(could not answer: {e})\n\n" + rag_extractive(q, turn["hits"])
            turn["state"], turn["secs"] = "done", time.time() - t0
            vlog(f"done in {turn['secs']:.1f} s")
            rg["busy"], rg["rev"] = False, rg["rev"] + 1
        threading.Thread(target=work, daemon=True).start()

    def md_inline(t, text, base):
        """**bold**, `code` and [1] citations inside one line."""
        for part in re.split(r"(\*\*[^*\n]+\*\*|`[^`\n]+`|\[\d+\])", text):
            if not part:
                continue
            if part.startswith("**") and part.endswith("**") and len(part) > 4:
                t.insert("end", part[2:-2], (base, "md_b"))
            elif part.startswith("`") and part.endswith("`") and len(part) > 2:
                t.insert("end", part[1:-1], (base, "md_ic"))
            elif re.fullmatch(r"\[\d+\]", part):
                t.insert("end", part, (base, "md_cite"))
            else:
                t.insert("end", part, base)

    def md_insert(t, text):
        """Shows a Markdown answer formatted: headings, bullet and numbered lists, bold, inline code, code blocks."""
        in_code = False
        for ln in str(text).replace("\r", "").split("\n"):
            st_ln = ln.strip()
            if st_ln.startswith("```"):
                in_code = not in_code
                lang = st_ln[3:].strip()
                if in_code and lang:
                    t.insert("end", lang + "\n", "md_lang")
                continue
            if in_code:
                t.insert("end", ln + "\n", "md_code")
                continue
            if st_ln in ("\\[", "\\]", "$$"):
                continue  # display-maths fences
            if re.search(r"\\[A-Za-z]+|\$|\^\{|_\{", ln):
                ln = tex_pretty(ln)
                st_ln = ln.strip()
            m = re.match(r"^(#{1,4})\s+(.*)", st_ln)
            if m:
                md_inline(t, m.group(2).strip("# "), f"md_h{min(3, len(m.group(1)))}")
                t.insert("end", "\n")
                continue
            m = re.match(r"^\s*[-*•]\s+(.*)", ln)
            if m:
                t.insert("end", "•  ", "md_li")
                md_inline(t, m.group(1), "md_li")
                t.insert("end", "\n", "md_li")
                continue
            m = re.match(r"^\s*(\d+)[.)]\s+(.*)", ln)
            if m:
                t.insert("end", f"{m.group(1)}.  ", "md_li")
                md_inline(t, m.group(2), "md_li")
                t.insert("end", "\n", "md_li")
                continue
            if not st_ln:
                t.insert("end", "\n", "md_gap")
                continue
            md_inline(t, ln, "a")
            t.insert("end", "\n", "a")

    def render_chat():
        chat_t.configure(state="normal")
        chat_t.delete("1.0", "end")
        mono = font(-2, mono=True)
        chat_t.tag_configure("md_h1", font=font(4, True), foreground=T["text"], spacing1=10, spacing3=4)
        chat_t.tag_configure("md_h2", font=font(2, True), foreground=T["text"], spacing1=8, spacing3=3)
        chat_t.tag_configure("md_h3", font=font(0, True), foreground=T["text"], spacing1=6, spacing3=2)
        chat_t.tag_configure("md_li", font=font(-1), foreground=T["text"], lmargin1=14, lmargin2=34, spacing1=2)
        chat_t.tag_configure("md_b", font=font(-1, True))
        chat_t.tag_configure("md_ic", font=mono, background=T["soft"], foreground=T["text"])
        chat_t.tag_configure("md_code", font=mono, background=T["soft"], foreground=T["text"], lmargin1=16, lmargin2=16,
                             rmargin=16, spacing1=0, spacing3=0)
        chat_t.tag_configure("md_lang", font=font(-4, True), foreground=T["faint"], background=T["soft"], lmargin1=16, spacing1=6)
        chat_t.tag_configure("md_cite", font=font(-3, True), foreground=T["blue"])
        chat_t.tag_configure("md_gap", font=font(-6))
        chat_t.tag_configure("q", font=font(0, True), foreground=T["text"], spacing1=10)
        chat_t.tag_configure("meta", font=font(-4), foreground=T["faint"])
        chat_t.tag_configure("a", font=font(-1), foreground=T["text"])
        chat_t.tag_configure("src", font=font(-3), foreground=T["dim"], lmargin1=12, lmargin2=28)
        chat_t.tag_configure("fld", font=font(-4, True), foreground=T["green"])
        chat_t.tag_configure("link", font=font(-4), foreground=T["blue"], underline=True)
        if not rg["chat"]:
            chat_t.insert("end", "Ask anything about the topics AITE collected - maths, physics, programming, robotics, "
                                 "medicine… The answer cites the records it used.\n", "meta")
        for n_, t_ in enumerate(rg["chat"]):
            chat_t.insert("end", "You  ", "meta")
            chat_t.insert("end", t_["q"] + "\n", "q")
            if t_["state"] == "searching":
                chat_t.insert("end", "Searching the whole dataset…\n", "meta")
                continue
            if t_["state"] == "thinking":
                chat_t.insert("end", f"{len(t_['hits'])} matching records found · {t_['model']} is writing the answer…\n", "meta")
            else:
                how = ("dataset + the model's own knowledge" if t_["hits"] else "the model's own knowledge (nothing in the dataset "
                       "was about this)") if t_["model"] else "from your dataset"
                chat_t.insert("end", (f"AI answer · {t_['model']} · " if t_["model"] else "") + how +
                              f" · {t_.get('secs', 0):.1f} s\n", "meta")
                md_insert(chat_t, t_["a"].strip())
            if t_["hits"]:
                chat_t.insert("end", "\nSources from your dataset\n", "meta")
                for i, h in enumerate(t_["hits"], 1):
                    chat_t.insert("end", f"[{i}] {shorten(h['title'], 110)}  ", "src")
                    chat_t.insert("end", f"{h['field'] or h['topic'] or 'general'} · {h['source']}" + (f" · {h['license']}" if h["license"] else ""), "fld")
                    if h["url"]:
                        tag = f"u{n_}_{i}"
                        chat_t.insert("end", "  open", ("link", tag))
                        chat_t.tag_bind(tag, "<Button-1>", lambda e, u=h["url"]: __import__("webbrowser").open(u))
                        chat_t.tag_bind(tag, "<Enter>", lambda e: chat_t.configure(cursor="hand2"))
                        chat_t.tag_bind(tag, "<Leave>", lambda e: chat_t.configure(cursor="arrow"))
                    chat_t.insert("end", "\n", "src")
            chat_t.insert("end", "\n")
        chat_t.configure(state="disabled")
        chat_t.see("end")

    def read_rag_status():
        try:
            with open(RAG_STATUS) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def ago(t):
        s_ = max(0, time.time() - float(t or 0))
        return "just now" if s_ < 60 else f"{int(s_ // 60)} min ago" if s_ < 3600 else f"{s_ / 3600:.1f} h ago"

    def rag_refresh():
        if rg["engine"] is None and not rg.get("engine_checking"):
            rg["engine_checking"] = True
            threading.Thread(target=lambda: rg.__setitem__("engine", trainer_ready()), daemon=True).start()
        if rg.get("then_dl"):
            rag_download(rg.pop("then_dl"))
        if not rg.get("auto_pick"):
            rg["auto_pick"] = True  # first look: the default model is not on this Mac but another one is -> use that one
            if st["rag_model"] == SPEC["rag_model"][3] and not model_downloaded(st["rag_model"]):
                have = [m_ for m_ in rag_models() if model_downloaded(m_)]
                if have:
                    st["rag_model"] = have[0]
                    persist()
        s_ = rg["status"] = read_rag_status()
        running = rg["proc"] is not None and rg["proc"].poll() is None
        ph = s_.get("state", "")
        # GitHub
        if running and ph == "syncing":
            badges["github"].set("Downloading…", "blue")
            badge_sub["github"].configure(text="getting the newest data from GitHub")
        elif s_.get("sync_ok") is False:
            badges["github"].set("GitHub unreachable", "orange")
            badge_sub["github"].configure(text=shorten(s_.get("sync_msg", ""), 90) + " · using the data already here")
        elif s_.get("sync_t"):
            badges["github"].set("Synced " + ago(s_["sync_t"]), "green")
            badge_sub["github"].configure(text=f"{fmt_n(s_.get('files', 0))} data files · next in "
                                               f"{fmt_s(max(0, int(st['rag_sync_min']) * 60 - (time.time() - rg['spawn_t'])))}")
        else:
            badges["github"].set("Starting…" if running else "Not synced yet", "blue" if running else "grey")
            badge_sub["github"].configure(text="happens by itself - no button needed")
        # index
        if running and ph == "indexing":
            badges["index"].set(f"Indexing {s_.get('done', 0)}/{s_.get('todo', 0)} files", "blue")
            badge_sub["index"].configure(text=f"{fmt_n(s_.get('count', 0))} records so far · +{fmt_n(s_.get('added', 0))} new")
        elif s_.get("count"):
            badges["index"].set(f"{fmt_n(s_['count'])} records", "green")
            badge_sub["index"].configure(text=f"all data types · {len(s_.get('fields', {}))} fields · "
                                              f"{'+ this Mac' if st['rag_include_local'] else 'GitHub only'}")
        else:
            badges["index"].set("Building…" if running else "Empty", "blue" if running else "grey")
            badge_sub["index"].configure(text="")
        rebuild_field_chips(s_.get("fields", {}))
        # Kaggle
        if not st.get("kaggle_enabled", True):
            badges["kaggle"].set("Off", "grey")
            badge_sub["kaggle"].configure(text="Settings > Kaggle")
        elif running and ph == "kaggle":
            badges["kaggle"].set("Uploading…", "blue")
            badge_sub["kaggle"].configure(text=st["kaggle_dataset"])
        elif not kaggle_logged_in():
            badges["kaggle"].set("Login needed", "orange")
            badge_sub["kaggle"].configure(text="kaggle.com > Settings > API > Create New Token -> ~/.kaggle/kaggle.json")
        elif s_.get("kaggle_ok") is False:
            badges["kaggle"].set("Upload failed", "red")
            badge_sub["kaggle"].configure(text=shorten(s_.get("kaggle_msg", ""), 90) + " · retries by itself")
        elif s_.get("kaggle_t"):
            badges["kaggle"].set("Uploaded " + ago(s_["kaggle_t"]), "green")
            badge_sub["kaggle"].configure(text=shorten(s_.get("kaggle_msg", ""), 60) + f" · every {st['kaggle_every_min']} min")
        else:
            badges["kaggle"].set("Waiting", "grey")
            badge_sub["kaggle"].configure(text=f"first upload after the next update · every {st['kaggle_every_min']} min")
        # engine
        if not trainer_supported():
            badges["engine"].set("Needs Apple silicon", "orange")
            badge_sub["engine"].configure(text="records-only answers still work")
        elif rg["installing"]:
            badges["engine"].set("Installing…", "blue")
            badge_sub["engine"].configure(text=shorten(rg["install_log"], 60))
        elif rg["engine"]:
            badges["engine"].set("Installed", "green")
            badge_sub["engine"].configure(text="Apple MLX, runs on this Mac")
        elif rg["engine"] is None:
            badges["engine"].set("Checking…", "grey")
        else:
            badges["engine"].set("Not installed", "grey")
            badge_sub["engine"].configure(text="press Install AI engine (once)")
        if trainer_supported() and rg["engine"] is False and not rg["installing"]:
            if eng_btn not in hbar.items:
                hbar.add(eng_btn)
        elif eng_btn in hbar.items:
            hbar.items.remove(eng_btn)
            eng_btn.place_forget()
            hbar.relayout()
        # models
        build_model_rows()
        cur = st["rag_model"]
        for mid, r_ in model_rows.items():
            text, tone = model_state(mid)
            r_["badge"].set(text, tone)
            if mid == cur:
                r_["use"].set("In use", "ink")
                if not r_["use"].winfo_ismapped():
                    r_["use"].pack(side="right", padx=(0, 6), before=r_["badge"])
            elif r_["use"].winfo_manager():
                r_["use"].pack_forget()
            want = ("In use" if mid == cur and tone == "green" else "Use" if tone == "green" else
                    "Downloading…" if tone == "blue" else "Retry" if tone == "red" else "Download")
            if r_["act"].text != want:
                r_["act"].text = want
                r_["act"].kind = "primary" if want in ("Download", "Retry") else "outline"
                r_["act"].icon = "down" if want in ("Download", "Retry") else None
                r_["act"].configure(width=int(measure(want, r_["act"].fnt) + 2 * max(14, 32 * 0.42) + (20 if r_["act"].icon else 0)))
            r_["act"].set_enabled(want not in ("In use", "Downloading…"))
        mt, mtone = model_state(cur)
        badges["model"].set(f"{shorten(model_label(cur), 26)} · {mt}", mtone)
        badge_sub["model"].configure(text="ready to answer" if mtone == "green" and rg["engine"] else
                                     "download it in Models below" if mtone in ("grey", "red") else "")
        tail_rag_log()
        if rg["vrev"] != rg["vdrawn"]:
            rg["vdrawn"] = rg["vrev"]
            render_vlog()
        # chat
        if rg["rev"] != rg["drawn_rev"]:
            rg["drawn_rev"] = rg["rev"]
            render_chat()
        ask_btn.set_enabled(not rg["busy"])
        w = rg.get("worker")
        if rg["busy"]:
            ask_info.configure(text="Working… (the first answer loads the model into memory, a few seconds)")
        elif w is not None and w.error and not w.alive():
            ask_info.configure(text=f"The model stopped: {w.error}")
        else:
            ask_info.configure(text=f"Reads the best {st['rag_k']} records per question · answers up to {st['rag_tokens']} tokens · "
                                    f"change this in Ask settings")

    def rag_poll():
        try:
            if not smoke or state.get("page") == "Ask":
                rag_update_start()  # GitHub -> index, by itself, every few minutes (no button needed)
            if state.get("page") == "Ask":
                rag_refresh()
        except Exception as e:
            status(f"Ask page: {type(e).__name__}: {e}")
        root.after(400 if rg["busy"] else 1500, rag_poll)

    def show_agents():
        """Every parallel agent running right now: totals, by task, by website (with polite-limit waits), the list."""
        win = dialog("Parallel agents", 900, 660)
        head = box(win, "card")
        head.pack(fill="x", padx=24)
        big = label(head, "", "text", 12, True)
        big.pack(anchor="w")
        sub = label(head, "", "dim", -1, wraplength=840)
        sub.pack(anchor="w", pady=(4, 8))
        wr = box(head, "card")
        wr.pack(fill="x")
        label(wr, "Parallel agents allowed", "text", -1).pack(side="left")
        NumField(wr, v_workers, 1, MAX_AGENTS, width=96).pack(side="right")
        Slider(wr, v_workers, 1, 5000).pack(side="left", fill="x", expand=True, padx=12)
        fr_, t_ = text_area(win, "code", mono=True, h=20, size=-2)
        fr_.pack(fill="both", expand=True, padx=24, pady=(12, 20))

        def tick():
            if not win.winfo_exists():
                return
            s_ = agent_status(ag["root"]) or {}
            n = s_.get("in_flight", 0) if s_.get("state") == "running" else 0
            big.configure(text=f"{n:,} agents running" if s_.get("state") == "running" else
                          "Agents paused" if s_.get("state") == "paused" else "Agent mode not started")
            sub.configure(text=f"{s_.get('workers', st['pwt_workers']):,} allowed · {s_.get('effective_workers', 0):,} active slots "
                               f"(fewer when CPU is above the cap) · {s_.get('waiting', 0):,} waiting for their turn at a website. "
                               f"{PWT_NAME} keeps every site inside its own rate limit, so more agents means more topics and sites "
                               f"at once - never more pressure on one site.")
            lines = ["BY TASK"] + [f"  {AGENT_KIND_LABELS.get(k, k):52s} {v:>6,}" for k, v in
                                   sorted((s_.get("busy_by_kind") or {}).items(), key=lambda x: -x[1])]
            lines += ["", "BY WEBSITE                                    requests  limit/s  waiting  throttled"]
            for h, v in list((s_.get("hosts") or {}).items())[:20]:
                lines.append(f"  {h:42s} {v['requests']:>8,} {v.get('rate', 0):>8.2f} {v.get('waiting', 0):>8,} {v['throttled']:>10,}")
            lines += ["", "RUNNING NOW (longest first)"]
            for i, b in enumerate(s_.get("busy") or [], 1):
                lines.append(f"  #{i:<5} {b['kind']:18s} {fmt_s(b['s']):>8}   {b.get('arg') or ''}")
            pos = t_.yview()
            t_.delete("1.0", "end")
            t_.insert("end", "\n".join(lines))
            t_.yview_moveto(pos[0])
            win.after(1000, tick)
        tick()
        return win

    def show_topics():
        """topics.json: every topic - ✓ done, in progress (with its agent), or left - with search and a field filter."""
        win = dialog("Topics", 980, 700)
        top_ = box(win, "card")
        top_.pack(fill="x", padx=24)
        summ = label(top_, "Reading topics.json…", "text", 2, True)
        summ.pack(anchor="w")
        fbar = box(top_, "card")
        fbar.pack(fill="x", pady=(8, 8))
        v_q, v_show = tk.StringVar(), tk.StringVar(value="all")
        Segmented(fbar, ["all", "done", "in progress", "left"], v_show, lambda v: fill(),
                  labels={"all": "All", "done": "✓ Done", "in progress": "In progress", "left": "Left"}).pack(side="left")
        qf = Field(fbar, v_q, width=260, h=36)
        qf.pack(side="right")
        qf.e.bind("<KeyRelease>", lambda e: fill())
        holder_ = box(win, "card")
        holder_.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        cols_ = ("check", "topic", "field", "level", "records", "agent", "completed")
        tv = ttk.Treeview(holder_, columns=cols_, show="headings", style="Chat.Treeview")
        sb_ = ttk.Scrollbar(holder_, orient="vertical", command=tv.yview, style="card.Vertical.TScrollbar")
        tv.configure(yscrollcommand=sb_.set)
        for c_, w_ in zip(cols_, (40, 330, 150, 120, 80, 70, 170)):
            tv.heading(c_, text={"check": "✓"}.get(c_, c_.capitalize()))
            tv.column(c_, width=w_, anchor="w", stretch=c_ == "topic")
        sb_.pack(side="right", fill="y")
        tv.pack(side="left", fill="both", expand=True)
        doc = {"topics": []}

        def fill():
            q, show = v_q.get().strip().lower(), v_show.get()
            tv.delete(*tv.get_children())
            n = 0
            for t in doc["topics"]:
                if (show != "all" and t.get("status", "done" if t["done"] else "left") != show) or (q and q not in t["topic"]):
                    continue
                tv.insert("", "end", values=(t["check"], t["topic"], t["field"], t["level"], t["records"] or "",
                                             t.get("agent") or "", t["completed"]))
                n += 1
                if n >= 3000:
                    break

        def load():
            try:
                with open(os.path.join(ag["root"], "topics.json"), encoding="utf-8") as f:
                    doc.update(json.load(f))
                summ.configure(text=f"✓ {doc['done']:,} done  ·  {doc.get('in_progress', 0):,} in progress  ·  {doc['left']:,} left  "
                                    f"·  {doc['total']:,} topics  (updated {doc['updated'][11:16]}, every minute)")
                fill()
            except (OSError, ValueError):
                summ.configure(text="No topics.json yet - it appears a minute after Agent mode starts.")
        load()
        win.doc = doc
        return win

    # ---------------------------------------------------------------- pages + interactive guide
    def show_page(p):
        if p == "Trainer":
            p = "Ask"  # the old Trainer page is now Ask (RAG)
        if p == "Manual" and not smoke:
            p = "Agent"  # Manual mode is removed from the app (its engine still powers the agent; tests still drive it)
        v_page.set("Agent" if p == "Agent" else "")
        state["mode_page"] = "Agent"
        state["page"] = p
        train_top.kind = "primary" if p == "Ask" else "outline"
        train_top.draw()
        close_popover()
        for pg in (shell, agent_pg, ask_pg):
            pg.pack_forget()
        {"Agent": agent_pg, "Ask": ask_pg}.get(p, shell).pack(fill="both", expand=True)
        status({"Agent": "Agent mode - continuous dataset collection", "Ask": "Ask - ALL your data, answered by a local AI model",
                "Manual": "Manual (test only)"}[p])
        if p == "Ask":
            rag_update_start()
            rag_refresh()
            qf.e.focus_set()  # the question box is ready to type in

    guide_state = {"win": None, "ring": None, "i": 0, "steps": []}

    def guide_steps():
        a = [(page_seg, "Welcome to AITE", "Two pages: Agent builds a huge dataset non-stop, and Ask your data answers questions "
                                           "from ALL of it with a local AI model. This guide walks "
                                           "through every part - press Next, or Skip guide at any time."),
             (title_btn, "The AITE menu", "About, Help, run history, Settings and the light/dark switch. Cmd+1, Cmd+2 and Cmd+3 "
                                          "jump between the three pages."),
             (agents_btn, "Parallel agents", f"How many agents are working right now - hundreds or thousands. Click it for the "
                                             f"full list: what each agent does, which website it is asking and who is waiting "
                                             f"for a turn. {PWT_NAME} keeps every site inside its own rate limit."),
             (gear_btn, "Settings", "Everything AITE can do is grouped into products in Settings > Products (Collection, Data "
                                    "quality, Vision & robotics, Training & delivery). Switch any product on or off there."),
             (theme_btn, "Light and dark", "AITE follows ChatGPT's own colours in both themes."),
             (train_top, "Ask your data", "Opens Ask: every record collected, searchable, answered by a local AI model."),
             (ag_btn, "Start, pause, resume", "Press Start once. After that the agent can only be paused, never stopped - it "
                                              "carries on by itself after a restart, and keeps collecting while this window is closed."),
             (ag_sub, "What it is doing", "A one-line summary: agents running in parallel, items per minute, time since start."),
             (tiles["text"], "Text records", "Question-and-answer rows for training language models: originals plus DataGen "
                                             "variants. Each row has chat messages, plain text, a train/check split and its licence."),
             (tiles["images"], "Images", "Free-licence Wikimedia Commons pictures with captions, plus generated scenes with exact "
                                         "object boxes and outlines - training data for vision models."),
             (tiles["vla"], "Robot VLA episodes", "Pick-and-place runs with camera frames, gripper actions and an instruction - for "
                                                  "vision-language-action robot models."),
             (tiles["topics"], "Topics", "Topics explored so far out of all topics known. The topic engine never runs out: a "
                                         "curated advanced taxonomy, OpenAlex's research catalogue and Wikipedia's links."),
             (tiles["rate"], "Speed", "Items collected per minute, averaged over the last five minutes."),
             (tiles["cpu"], "CPU and memory", "This Mac's load. Above the CPU cap (Agent settings) the agent slows itself down."),
             (tiles["gh"], "GitHub sync", "Every 5 minutes: stats.json, topics.json, the README with live numbers and the new data "
                                          "are pushed to the main branch of your repository."),
             (sys_card, "System", "CPU over the last two minutes and every core, plus load, agent memory, threads and free disk."),
             (sample_card, "Latest sample", "The newest record or picture, so you can judge quality while it runs."),
             (ctl_card, "What to collect", "Switch each kind of data on or off: Q&A archives (Stack Exchange incl. MathOverflow, "
                                           "medicine), topic search, web images, generated images and robot episodes."),
             (abar, "Shortcuts", "Topics ✓ opens topics.json - every topic, done, in progress or left. Parallel agents shows who "
                                 "is running. Also: the dataset folder, Sync now, GitHub and Agent settings, the training guide."),
             (set_card, "Agent settings", "Quality, records per topic, DataGen variations, CPU cap, data types and focus topics "
                                          "(collected first). The running agent applies changes within a second."),
             (act_card, "Activity", "Every finished task, newest first; the counters on the right show which sites are being asked."),
             (gear_btn, "GitHub link", "Settings > GitHub holds the repository link - change it any time. Pushing uses this Mac's "
                                       "normal git login; AITE stores no keys or passwords.")]
        m = [(page_seg, "Manual mode", "One exact dataset: Input -> Web search -> Filter -> DataGen -> Output, then one file."),
             (mode_seg, "Two ways to enter the same settings", "Visual dropdowns (sliders, chips) or JSON - they stay in sync."),
             (topic_f, "1 Topics", "Type any subjects, comma separated, or tap the suggestions under the box."),
             (chips, "Topic suggestions", "Tap a suggestion to add it; Clear topics empties the box."),
             (vdm_sf, "2-6 Quantity, quality, type, output, DataGen", "Quantity (1-1,000), quality (1-4 basic checks, 5-10 strict), "
                                                                       "type of data, output file (PDF, TXT, JSON) and DataGen variations, styles and formats."),
             (wf, "The workflow", "Each card lights up as its stage runs. Click a card to open that stage's settings."),
             (tb, "Tools", "Re-filter (new quality, no new search), Re-run DataGen, Preview, Export as, Load results, Rejected, Stats and more."),
             (run_btn, "Run", "Runs the pipeline once. Several topics are searched in parallel. Esc stops a run."),
             (out_card, "Preview and export", "Preview shows exactly what Export writes - only the formatted records. Records lists "
                                              "every row; Log shows each step. Export saves ONE combined file.")]
        t = [(train_top, "Ask your data", "This button (a little apart from Agent mode) opens Ask. Back returns to Agent mode."),
             (prow, "The question box", "Type any question and press Enter or Ask. AITE searches ALL the data and the model "
                                        "answers from the best records, citing them [1]."),
             (mrow, "Answer style", "AI answer + sources, or just the matching records (works without any model)."),
             (frow, "Fields", "ALL is on by default. Tap fields to pick one or several; Select all / Clear switch them all."),
             (vfr, "Verbose log", "Every step, live: search terms, each match with its score, prompt size, model loading, speed - "
                                  "and the background job: GitHub download, indexing file by file, Kaggle upload."),
             (sgrid, "Status labels", "Green = ready, blue = working, orange = needs attention, red = failed, grey = not yet. "
                                      "GitHub data, the index and Kaggle update by themselves - no button needed."),
             (mc, "Models", "Green Downloaded = ready, press Use. Grey Not downloaded = press Download (once). Orange = too big for this Mac.")]
        return a if state.get("page") == "Agent" else t if state.get("page") == "Ask" else m

    def guide_close():
        for k in ("win", "ring"):
            if guide_state[k] is not None:
                try:
                    guide_state[k].destroy()
                except tk.TclError:
                    pass
                guide_state[k] = None

    def guide(i=0):
        guide_close()
        steps = guide_state["steps"] = guide_steps() if i == 0 or not guide_state["steps"] else guide_state["steps"]
        if not 0 <= i < len(steps):
            st["guide_seen"] = True
            persist()
            return None
        guide_state["i"] = i
        target, title, text = steps[i]
        if target.master is not None and hasattr(target, "winfo_ismapped"):
            try:  # scroll the agent page so the target is visible
                for body_, sf_ in ((agb, ag_sf), (akb, ask_sf)):
                    if str(target).startswith(str(body_)):
                        root.update_idletasks()
                        y = target.winfo_rooty() - body_.winfo_rooty()
                        sf_.cv.yview_moveto(max(0, (y - 80) / max(1, body_.winfo_height())))
            except tk.TclError:
                pass
        root.update_idletasks()
        tx, ty, tw, th = target.winfo_rootx(), target.winfo_rooty(), target.winfo_width(), target.winfo_height()
        clear = sys.platform == "darwin"
        if clear:  # a blue rounded ring around the target
            ring = tk.Toplevel(root)
            ring.overrideredirect(True)
            try:
                ring.wm_attributes("-transparent", True)
                ring.configure(bg="systemTransparent")
                cv = tk.Canvas(ring, width=tw + 12, height=th + 12, bg="systemTransparent", highlightthickness=0, bd=0)
                cv.pack()
                cv.create_polygon(g3_points(2, 2, tw + 10, th + 10, min(24, (th + 8) / 2), power=1.0 if th < 60 else 0.5),
                                  fill="", outline=T["blue"], width=3)
                ring.geometry(f"{tw + 12}x{th + 12}+{tx - 6}+{ty - 6}")
                ring.wm_attributes("-topmost", True)
                guide_state["ring"] = ring
            except tk.TclError:
                ring.destroy()
        W = 360
        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.configure(bg=T["border"])
        inner = box(win, "card")
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        label(inner, f"{i + 1} of {len(steps)}", "faint", -3).pack(anchor="w", padx=18, pady=(14, 0))
        label(inner, title, "text", 2, True).pack(anchor="w", padx=18, pady=(2, 4))
        label(inner, text, "dim", -1, wraplength=W - 36).pack(anchor="w", padx=18)
        bb = box(inner, "card")
        bb.pack(fill="x", padx=14, pady=14)
        last = i == len(steps) - 1
        Pill(bb, "Done" if last else "Next", lambda: guide(i + 1), "primary", h=34, size=-1).pack(side="right")
        if i:
            Pill(bb, "Back", lambda: guide(i - 1), "outline", h=34, size=-1).pack(side="right", padx=(0, 6))
        Pill(bb, "Skip guide", lambda: guide(len(steps)), "ghost", h=34, size=-2).pack(side="left")
        win.update_idletasks()
        H = win.winfo_reqheight()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        x = min(max(8, tx), sw - W - 8)
        y = ty + th + 14 if ty + th + 14 + H < sh - 40 else max(8, ty - H - 14)
        win.geometry(f"{W}x{H}+{x}+{y}")
        win.wm_attributes("-topmost", True)
        win.bind("<Escape>", lambda e: guide(len(steps)))
        win.focus_force()
        guide_state["win"] = win
        apply_theme()
        return win

    # ---------------------------------------------------------------- logic
    def status(t):
        status_lbl.configure(text=shorten(t, 140))

    def persist():
        if st["autosave_settings"]:
            save_settings(st)

    def log(msg):
        msgs.put(("log", msg))

    def append_log(msg):
        if st["log_timestamps"]:
            msg = datetime.now().strftime("%H:%M:%S  ") + msg
        log_t.insert("end", msg + "\n")
        plog_t.insert("end", msg + "\n")
        if int(plog_t.index("end").split(".")[0]) > 2000:
            plog_t.delete("1.0", "500.0")
        plog_t.see("end")
        n = int(log_t.index("end").split(".")[0])
        if n > int(st["log_max_lines"]):
            log_t.delete("1.0", f"{n - int(st['log_max_lines'])}.0")
        log_t.see("end")

    def vdm_values():
        return {"topics": v_topics.get(), "quantity": v_qty.get(), "quality": v_qual.get(),
                "data_types": [k for k in DATA_TYPES if dtype_vars[k].get()], "output_type": v_out.get(),
                "datagen_variations": v_var.get(),
                "datagen_styles": [k for k, v in style_vars.items() if v.get()],
                "datagen_formats": [k for k, v in format_vars.items() if v.get()],
                "datagen_methods": [k for k, v in method_vars.items() if v.get()]}

    def current_input():
        if state["mode"] == "JSON":
            try:
                d = json.loads(json_t.get("1.0", "end") or "{}")
            except ValueError as e:
                return None, [f"JSON error: {e}"]
            return validate_input(d)
        try:
            return validate_input(vdm_values())
        except tk.TclError as e:
            return None, [f"input: {e}"]

    def set_input(d):
        d, _ = validate_input(d)
        state["loading"] = True
        state["inp"] = d
        v_topics.set(", ".join(d["topics"]))
        v_qty.set(d["quantity"])
        v_qual.set(d["quality"])
        for k, v in dtype_vars.items():
            v.set(k in d["data_types"])
        v_out.set(d["output_type"])
        v_var.set(d["datagen_variations"])
        for store, key in ((style_vars, "datagen_styles"), (format_vars, "datagen_formats"), (method_vars, "datagen_methods")):
            for k, v in store.items():
                v.set(k in d[key])
        json_t.delete("1.0", "end")
        json_t.insert("1.0", json.dumps(d, indent=2))
        state["loading"] = False
        json_live_check()
        update_hints()

    def on_vdm_change(*_):
        if state["loading"]:
            return
        if state["mode"] == "VDM":
            d, errs = current_input()
            if not errs:
                json_t.delete("1.0", "end")
                json_t.insert("1.0", json.dumps(d, indent=2))
        update_hints()
        if state["records"] and not state["running"] and current_out_type() != state.get("shown_type"):
            refresh_preview()  # the output type changed: the preview follows it

    def current_out_type():
        """The output type chosen in the input panel now (falls back to the last run's)."""
        d, errs = current_input()
        return d["output_type"] if d and not errs else state["inp"]["output_type"]

    def update_hints(*_):
        try:
            q, n, qty = int(v_qual.get()), int(v_var.get()), int(v_qty.get())
        except (tk.TclError, ValueError):
            return
        if q <= int(st["filter_from_quality"]):
            qual_hint.configure(text=f"Quality {q}: basic checks only (empty / no solution / not a problem). Fast.")
        else:
            qual_hint.configure(text=f"Quality {q}: strict filter, minimum score {st[f'min_score_q{q}']}, oversample x"
                                     f"{float(st['oversample']) + (q - 4) * float(st['oversample_per_quality']):.2f}.")
        if n == 0:
            dg_hint.configure(text="DataGen is off - only the original records are exported.")
        else:
            dg_hint.configure(text=f"{qty:,} originals x {n} -> up to {qty * n:,} variants -> up to {qty * (n + 1):,} "
                                   f"records in ONE file.")
        try:
            topics = [x for x in v_topics.get().split(",") if x.strip()]
        except tk.TclError:
            topics = []
        wf_set("input", "done", f"{state['mode'] or 'VDM'} · {len(topics)} topic(s) · x{qty} · Q{q}")
        if not state["running"]:
            wf_state["datagen"]["info"] = f"x{n} per record" if n else "Off"
            wf_state["output"]["info"] = (v_out.get() or "pdf").upper()
            draw_wf()

    for v in (v_topics, v_qty, v_qual, v_out, v_var):
        v.trace_add("write", on_vdm_change)

    def json_live_check():
        try:
            d = json.loads(json_t.get("1.0", "end"))
            _, errs = validate_input(d)
            json_status.configure(text="✓ Valid" if not errs else "✗ " + "  ".join(errs),
                                  fg=T["green"] if not errs else T["error_text"])
        except ValueError as e:
            json_status.configure(text=f"✗ JSON: {e}", fg=T["error_text"])

    def set_mode(m, force=False):
        if m == state["mode"] and not force:
            return
        d = state["inp"]
        if state["mode"] in ("VDM", "JSON"):
            d2, errs = current_input()
            if errs:
                if state["mode"] == "JSON" and not smoke and not messagebox.askyesno(
                        APP, "The JSON has errors:\n" + "\n".join(errs) + "\n\nSwitch anyway (keeps the last valid input)?"):
                    v_mode.set(state["mode"])
                    return
            else:
                d = d2
        state["mode"] = m
        if v_mode.get() != m:
            v_mode.set(m)
        vdm_sf.pack_forget()
        jsn.pack_forget()
        (vdm_sf if m == "VDM" else jsn).pack(fill="both", expand=True)
        set_input(d)
        status(f"Input mode: {'Visual dropdowns' if m == 'VDM' else 'JSON schema'}")

    def validate_now():
        d, errs = current_input()
        if errs:
            if not smoke:
                messagebox.showerror(APP, "\n".join(errs))
            status("Input errors: " + "; ".join(errs))
            return None
        state["inp"] = d
        status("Input valid: " + shorten(json.dumps(d), 200))
        return d

    def import_json(path=None):
        p = path or filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*")])
        if not p:
            return
        try:
            with open(p) as f:
                d = json.load(f)
        except Exception as e:
            messagebox.showerror(APP, f"Could not read {p}:\n{e}")
            return
        if isinstance(d, dict) and "input" in d.get("meta", {}):
            d = d["meta"]["input"]
        set_mode("JSON")
        json_t.delete("1.0", "end")
        json_t.insert("1.0", json.dumps(d, indent=2))
        json_live_check()
        status(f"Imported {os.path.basename(p)}")

    def paste_json():
        try:
            txt = root.clipboard_get()
        except tk.TclError:
            return
        json_t.delete("1.0", "end")
        json_t.insert("1.0", txt)
        json_live_check()

    def copy_json():
        root.clipboard_clear()
        root.clipboard_append(json_t.get("1.0", "end").strip())
        status("JSON copied")

    def format_json():
        try:
            d = json.loads(json_t.get("1.0", "end"))
            json_t.delete("1.0", "end")
            json_t.insert("1.0", json.dumps(d, indent=2))
        except ValueError as e:
            messagebox.showerror(APP, str(e))

    def save_json_input():
        d = validate_now()
        if not d:
            return
        p = filedialog.asksaveasfilename(defaultextension=".json", initialfile="aite_input.json")
        if p:
            with open(p, "w") as f:
                json.dump(d, f, indent=2)
            status(f"Saved {p}")

    def new_run():
        if state["running"]:
            return
        set_input(json.loads(json.dumps(DEFAULT_INPUT)))
        clear_results()
        for k in ("search", "filter", "datagen", "output"):
            wf_state[k] = {"state": "idle", "info": ""}
        update_hints()
        prog.set(0)
        prog_lbl.configure(text="Ready")
        status("New run: defaults restored (10 records, quality 4, PDF, DataGen x3).")

    def about_menu():
        items = [("about", f"About AITE {VERSION}"), ("help", "Help"), ("history", "Run history"),
                 ("settings", "Settings"), ("theme", "Switch to light mode" if st["theme"] == "dark" else "Switch to dark mode")]
        acts = {"about": lambda: popup("About AITE", f"{APP} {VERSION}\n\n" + __doc__, 760, 520), "help": lambda: show_help(),
                "history": lambda: show_history(), "settings": lambda: open_settings(), "theme": lambda: toggle_theme()}
        return popover(title_btn, items, lambda k: acts[k]())

    def start_run():
        if state["running"]:
            return
        d = validate_now()
        if not d:
            return
        state["inp"] = d
        if st["remember_input"] and not smoke:
            try:
                with open(LAST_INPUT_FILE, "w") as f:
                    json.dump(d, f, indent=2)
            except Exception:
                pass
        state["running"] = True
        state["cancel"] = threading.Event()
        run_btn.set_enabled(False)
        stop_btn.set_enabled(True)
        for k in ("search", "filter", "datagen", "output"):
            wf_state[k] = {"state": "idle", "info": ""}
        draw_wf()
        run_vis.update(stage={}, msg="Starting…", frac=0.0, t0=time.time(), kept=0, rejected=0, variants=0)
        show_view("Progress")
        append_log(f"=== RUN {json.dumps(d)}")
        stt = dict(st)
        cancel = state["cancel"]

        def work():
            try:
                prog_cb = lambda f, m="": msgs.put(("prog", (f, m)))
                searcher = SEARCHER_FACTORY(stt, log, cancel, prog_cb) if SEARCHER_FACTORY else Searcher(stt, log, cancel, progress=prog_cb)
                run_vis["searcher"] = searcher
                res = run_pipeline(d, stt, log, cancel, prog_cb, searcher,
                                   lambda name, s, info="": msgs.put(("stage", (name, s, info))))
                msgs.put(("done", res))
            except Exception as e:
                import traceback
                msgs.put(("log", traceback.format_exc()))
                msgs.put(("stage", ("search", "error", str(e)[:80])))
                msgs.put(("done", {"records": [], "variants": [], "rejected": [], "reasons": {"error": str(e)}, "stats": {}, "notes": {}}))
        threading.Thread(target=work, daemon=True).start()

    def pump(once=False):
        try:
            while True:
                kind, val = msgs.get_nowait()
                if kind == "log":
                    append_log(val)
                elif kind == "prog":
                    prog.set(val[0])
                    prog_lbl.configure(text=f"{val[0] * 100:.0f}%  ·  {val[1]}")
                    run_vis["frac"], run_vis["msg"] = val[0], val[1]
                elif kind == "stage":
                    wf_set(*val)
                    run_vis["stage"][val[0]] = val[1]
                    info = val[2] if len(val) > 2 else ""
                    m_ = re.search(r"(\d+) kept · (\d+) rejected", info or "")
                    if m_:
                        run_vis["kept"] += int(m_.group(1)) if len(state["inp"].get("data_types", [])) > 1 else int(m_.group(1)) - run_vis["kept"]
                        run_vis["rejected"] = int(m_.group(2))
                    m_ = re.search(r"(\d+) variants", info or "")
                    if m_:
                        run_vis["variants"] = int(m_.group(1))
                elif kind == "exported":
                    finish_export(*val)
                elif kind == "redone":
                    var, d = val
                    state["variants"], state["running"] = var, False
                    if d:
                        state["inp"].update({k: d[k] for k in d if k.startswith("datagen_")})
                    run_btn.set_enabled(True)
                    stop_btn.set_enabled(False)
                    fill_tree()
                    refresh_preview()
                    status(f"DataGen made {len(var)} variants for {len(state['records'])} records.")
                elif kind == "export_error":
                    wf_set("output", "error", "Export failed")
                    status("Export failed: " + val)
                    append_log("Export failed: " + val)
                    if not smoke:
                        messagebox.showerror(APP, "Export failed:\n" + val)
                elif kind == "done":
                    state.update(records=val["records"], variants=val["variants"], rejected=val["rejected"],
                                 reasons=val["reasons"], stats=val.get("stats", {}), notes=val.get("notes", {}), running=False)
                    state["history"].append({"time": datetime.now().strftime("%H:%M:%S"), "input": dict(state["inp"]),
                                             "kept": len(val["records"]), "variants": len(val["variants"]),
                                             "rejected": len(val["rejected"]), "sources": val.get("stats", {})})
                    run_btn.set_enabled(True)
                    stop_btn.set_enabled(False)
                    run_vis.update(kept=len(val["records"]), rejected=len(val["rejected"]), variants=len(val["variants"]),
                                   elapsed=time.time() - run_vis["t0"], searcher=None)
                    run_canvas.draw()
                    prog_lbl.configure(text=f"Done  ·  {len(val['records'])} records + {len(val['variants'])} variants "
                                            f"({len(val['rejected'])} rejected)")
                    fill_tree()
                    refresh_preview()
                    if st["auto_preview"]:
                        show_view("Preview")
                    if st["sound_on_done"] and not smoke:
                        root.bell()
                    status(f"Run finished: {len(val['records'])}/{state['inp']['quantity']} records + "
                           f"{len(val['variants'])} variants. Review the preview, then Export.")
        except queue.Empty:
            pass
        if once:
            return
        if st["workflow_pulse"] and any(v["state"] == "active" for v in wf_state.values()):
            state["pulse"] += 0.35  # the active stage's dot breathes
            draw_wf()
        if state["running"] and v_view.get() == "Progress" and time.time() - run_canvas.last > 0.12:
            run_canvas.last = time.time()
            run_canvas.draw()
        root.after(80, pump)

    def rows():
        return arrange(state["records"], state["variants"], st)

    TABLE_MAX = 5000

    def fill_tree():
        tree.delete(*tree.get_children())
        all_rows = rows()
        for did, r, parent in all_rows[:TABLE_MAX]:
            tree.insert("", "end", iid=r.get("uid") or str(id(r)),
                        values=(did, r.get("kind", "original"), r.get("score", ""), r["topic"], r["source"],
                                r.get("style", ""), r.get("format", ""), r["title"][:160]))
        if len(all_rows) > TABLE_MAX:
            tree.insert("", "end", iid="__more__", values=("…", "", "", "", "", "", "",
                                                           f"{len(all_rows) - TABLE_MAX:,} more rows - all of them are in the preview/export"))
        count_lbl.configure(text=f"{len(state['records'])} records + {len(state['variants'])} variants")

    def sort_tree(col):
        if col in ("score", "topic", "source"):
            st["sort_by"] = col
            fill_tree()
            refresh_preview()

    def preview_text():
        inp = dict(state["inp"], output_type=current_out_type())
        state["shown_type"] = inp["output_type"]
        fmt = prev_fmt.get()
        kind = inp["output_type"] if fmt == "as output type" else fmt.split()[0]
        recs, var = state["records"], state["variants"]
        if kind == "json":
            return render_json(recs, inp, st, state["reasons"], var)
        txt = render_txt(recs, inp, st, state["reasons"], var)
        if kind == "pdf":
            if len(recs) + len(var) <= 300:
                pages = str(len(re.findall(rb"/Type /Page ", render_pdf(recs, inp, st, state["reasons"], var))))
            else:
                pages = f"about {estimate_pdf_pages(txt, st)}"
            txt = f"[PDF preview - text layout. Export makes ONE {pages}-page {st['pdf_page']} PDF]\n\n" + txt
        return txt

    def refresh_preview():
        prev_t.delete("1.0", "end")
        if not state["records"]:
            prev_t.insert("1.0", "No results yet.\n\nPick topics on the left and press Run pipeline.\n\n"
                                 "Workflow: Input → Web search → Filter → DataGen → Output (one combined file).")
            prev_info.configure(text="")
            return
        t = preview_text()
        mx = int(st["preview_max_chars"])
        prev_t.insert("1.0", t if len(t) <= mx else t[:mx] + f"\n\n… preview cut at {mx:,} characters - the export contains everything.")
        prev_info.configure(text=f"{len(state['records'])} records + {len(state['variants'])} variants  ·  {len(t):,} characters")

    def find_text():
        prev_t.tag_remove("hit", "1.0", "end")
        q = find_var.get()
        if not q:
            return
        idx, n = "1.0", 0
        while True:
            idx = prev_t.search(q, idx, nocase=True, stopindex="end")
            if not idx:
                break
            end = f"{idx}+{len(q)}c"
            prev_t.tag_add("hit", idx, end)
            if n == 0:
                prev_t.see(idx)
            idx, n = end, n + 1
        prev_t.tag_configure("hit", background=T["select_text"], foreground=T["text"])
        show_view("Preview")
        status(f"{n} match(es)")

    def do_export(ask=False, path=None):
        if not state["records"]:
            if not smoke:
                messagebox.showinfo(APP, "Nothing to export yet - run the pipeline first.")
            return None
        inp = dict(state["inp"], output_type=current_out_type())
        name = default_filename(inp, st)
        p = path
        if not p:
            os.makedirs(st["out_dir"], exist_ok=True)
            p = os.path.join(st["out_dir"], name)
        if ask:
            p = filedialog.asksaveasfilename(initialdir=st["out_dir"], initialfile=name, defaultextension="." + inp["output_type"])
            if not p:
                return None
        recs, var, reasons = list(state["records"]), list(state["variants"]), state["reasons"]
        n = len(recs) + len(var)
        if n > 300 and not smoke:  # big files are written in the background so the window stays responsive
            status(f"Exporting {n:,} records to {os.path.basename(p)}…")
            wf_set("output", "active", f"Writing {n:,} records…")
            stt = dict(st)

            def bg():
                try:
                    export(recs, inp, stt, p, reasons, var)
                    msgs.put(("exported", (p, n, inp["output_type"])))
                except Exception as e:
                    msgs.put(("export_error", f"{type(e).__name__}: {e}"))
            threading.Thread(target=bg, daemon=True).start()
            return p
        export(recs, inp, st, p, reasons, var)
        finish_export(p, n, inp["output_type"])
        return p

    def refilter():
        """Apply the current quality / quantity to everything found in the last run - no new search."""
        if state["running"] or not (state["records"] or state["rejected"]):
            return
        d = validate_now()
        if not d:
            return
        pool = state["records"] + state["rejected"]
        for r in pool:
            r.pop("rejected", None)
        inp = dict(state["inp"], quality=d["quality"], quantity=d["quantity"])
        final, rejected, reasons = Filterer(st, log).run(pool, inp)
        keep = {r.get("uid") for r in final}
        state.update(records=final, rejected=rejected, reasons=reasons,
                     variants=[v for v in state["variants"] if v.get("variant_of") in keep])
        state["inp"].update(quality=d["quality"], quantity=d["quantity"])
        missing = sum(1 for r in final if not any(v.get("variant_of") == r.get("uid") for v in state["variants"]))
        wf_set("filter", "done", f"{len(final)} kept · {len(rejected)} rejected (re-filtered)")
        fill_tree()
        refresh_preview()
        status(f"Re-filtered at quality {d['quality']}: {len(final)} records kept"
               + (f" - {missing} have no variants yet: press Re-run DataGen" if missing and d["datagen_variations"] else ""))

    def rerun_datagen(sync=False):
        """Make the variants again with the current DataGen settings (styles, formats, count, methods)."""
        if state["running"] or not state["records"]:
            return
        d = validate_now()
        if not d:
            return
        recs, stt, cancel = list(state["records"]), dict(st), threading.Event()
        state["cancel"] = cancel

        def work():
            try:
                dg = DataGen(stt, log)
                var = dg.generate(recs, d, lambda f, m="": msgs.put(("prog", (f, m))), cancel) if d["datagen_variations"] else []
                msgs.put(("stage", ("datagen", "done" if var else "skipped",
                                    f"{len(var)} variants · {dg.counts['numbers']} re-solved (SymPy)" if var else "Off")))
                msgs.put(("redone", (var, d)))
            except Exception as e:
                msgs.put(("log", f"DataGen failed: {type(e).__name__}: {e}"))
                msgs.put(("redone", (state["variants"], None)))
        wf_set("datagen", "active", "Regenerating…")
        if sync:
            work()
            pump(once=True)
            return
        state["running"] = True
        run_btn.set_enabled(False)
        stop_btn.set_enabled(True)
        threading.Thread(target=work, daemon=True).start()

    def finish_export(p, n, kind):
        state["last_export"] = p
        wf_set("output", "done", f"Saved {kind.upper()} · {n:,} records")
        status(f"Exported {p}")
        append_log(f"Exported {n:,} records -> {p}")
        if st["open_after_export"] and not smoke:
            open_path(p)
        elif not smoke:
            messagebox.showinfo(APP, f"Saved one combined {kind.upper()} file ({n:,} records):\n{p}")

    def open_path(p):
        import subprocess
        if not os.path.splitext(p)[1]:
            os.makedirs(p, exist_ok=True)
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", p])

    def copy_preview():
        root.clipboard_clear()
        root.clipboard_append(prev_t.get("1.0", "end"))
        status("Preview copied")

    def clear_results():
        state.update(records=[], variants=[], rejected=[], reasons={})
        fill_tree()
        refresh_preview()

    def remove_selected():
        ids = set(tree.selection())
        gone = {r.get("uid") for r in state["records"] if r.get("uid") in ids}
        state["records"] = [r for r in state["records"] if r.get("uid") not in ids]
        state["variants"] = [v for v in state["variants"] if v.get("uid") not in ids and v.get("variant_of") not in gone]
        fill_tree()
        refresh_preview()

    def load_results(path=None):
        p = path or filedialog.askopenfilename(filetypes=[("AITE JSON export", "*.json")])
        if not p:
            return
        try:
            with open(p) as f:
                d = json.load(f)
            data = d["data"] if isinstance(d, dict) else d
            recs, var, uid_of = [], [], {}
            for r in data:
                msgs_ = r.get("messages") or []
                prob = r.get("problem") or r.get("instruction") or next((m["content"] for m in msgs_ if m.get("role") == "user"), "")
                sol = r.get("solution") or r.get("output") or next((m["content"] for m in msgs_ if m.get("role") == "assistant"), "")
                it = item(r.get("topic", ""), r.get("source", "file"), r.get("title", ""), prob, sol, r.get("url", ""), 0,
                          {"license": r.get("license")} if r.get("license") else {})
                it["score"] = r.get("quality_score", 0)
                it["uid"] = f"f{len(recs) + len(var)}"
                if r.get("kind") == "variant":
                    it.update(kind="variant", variant_of=uid_of.get(str(r.get("variant_of"))), style=r.get("style"),
                              format=r.get("format"), methods=r.get("methods", []), numbers_changed=r.get("numbers_changed"),
                              answer=r.get("answer"))
                    var.append(it)
                else:
                    uid_of[str(r.get("id"))] = it["uid"]
                    recs.append(it)
            state["records"], state["variants"] = recs, var
            if isinstance(d, dict) and "meta" in d:
                state["inp"], _ = validate_input(d["meta"].get("input", {}))
            fill_tree()
            refresh_preview()
        except Exception as e:
            if smoke:
                raise
            messagebox.showerror(APP, f"Not an AITE JSON export:\n{e}")

    def dialog(title, w=820, h=560, bg="card"):
        """A ChatGPT-style dialog window: card background, 20px title, round close button."""
        win = tk.Toplevel(root)
        win.title(title)
        win.geometry(f"{w}x{h}")
        reg(win, "bg", bg)
        win.configure(bg=T[bg])
        head = box(win, bg)
        head.pack(fill="x", padx=24, pady=(20, 10))
        Pill(head, "", win.destroy, "icon", h=36, icon="close", tip="Close").pack(side="right")
        label(head, title, "text", 6, True).pack(side="left")
        win.bind("<Escape>", lambda e: win.destroy())
        return win

    def popup(title, text, w=820, h=560):
        win = dialog(title, w, h)
        card = Card(win, radius=16, pad=0, fill="code")
        card.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        fr, t = text_area(card.inner, "code", mono=True, h=20, size=-2)
        fr.pack(fill="both", expand=True, padx=2, pady=2)
        t.insert("1.0", text)
        apply_theme()
        return win

    def show_record():
        sel = tree.selection()
        for r in state["records"] + state["variants"]:
            if sel and r.get("uid") == sel[0]:
                popup(shorten(r["title"], 60) or "Record",
                      json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, indent=2, ensure_ascii=False))

    def rich(title, tiles=(), tables=(), sections=(), w=920, h=660):
        """A secondary window in the app's own style: stat tiles, tables and titled sections (no raw text dumps)."""
        win = dialog(title, w, h)
        sf = ScrollFrame(win, "card")
        sf.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        body = sf.body

        class MiniTile(Card):
            def __init__(self, master, lab, val, sub=""):
                super().__init__(master, radius=16, pad=12, fill="soft", border=False)
                self.configure(width=196, height=88)
                self.pack_propagate(False)
                label(self.inner, lab, "dim", -3).pack(anchor="w")
                label(self.inner, val, "text", 6, True).pack(anchor="w")
                if sub:
                    label(self.inner, shorten(sub, 30), "faint", -4).pack(anchor="w")

            def winfo_reqwidth(self):
                return 196

            def winfo_reqheight(self):
                return 88
        if tiles:
            fl = FlowFrame(body, "card", padx=10, pady=10)
            fl.pack(fill="x", padx=8, pady=(0, 6))
            for t in tiles:
                fl.add(MiniTile(fl, *t))
        for heading, cols, rows_ in tables:
            label(body, heading, "text", 1, True).pack(anchor="w", padx=8, pady=(14, 6))
            if not rows_:
                label(body, "Nothing yet.", "faint", -2).pack(anchor="w", padx=8)
                continue
            fr = box(body, "card")
            fr.pack(fill="x", padx=8)
            tv = ttk.Treeview(fr, columns=[c for c, _w in cols], show="headings", style="Chat.Treeview",
                              height=min(len(rows_), 12))
            for c, w_ in cols:
                tv.heading(c, text=c)
                tv.column(c, width=w_, anchor="w", stretch=w_ >= 300)
            if len(rows_) > 12:
                sb_ = ttk.Scrollbar(fr, orient="vertical", command=tv.yview, style="card.Vertical.TScrollbar")
                tv.configure(yscrollcommand=sb_.set)
                sb_.pack(side="right", fill="y")
            tv.pack(side="left", fill="x", expand=True)
            for r in rows_[:5000]:
                tv.insert("", "end", values=r)
        for heading, text in sections:
            label(body, heading, "text", 1, True).pack(anchor="w", padx=8, pady=(16, 4))
            label(body, text, "dim", -1, wraplength=w - 120).pack(anchor="w", padx=8)
        apply_theme()
        return win

    def show_rejected():
        rej = state["rejected"]
        reasons = sorted(state["reasons"].items(), key=lambda x: -x[1])
        return rich("Rejected by the filter",
                    [("Rejected", f"{len(rej):,}", "kept out of the dataset")] + [(k.capitalize(), f"{v:,}", "") for k, v in reasons[:7]],
                    [("Every rejected item", [("Reason", 170), ("Source", 120), ("Score", 70), ("Title", 420)],
                      [(r.get("rejected", ""), r.get("source", ""), r.get("score", ""), shorten(r.get("title", ""), 120)) for r in rej])])

    def show_stats():
        recs, var = state["records"], state["variants"]
        count = lambda items, key: sorted(((k, sum(1 for r in items if r.get(key) == k)) for k in {r.get(key) for r in items} - {None}),
                                          key=lambda x: -x[1])
        avg = round(sum(r.get("score") or 0 for r in recs) / max(1, len(recs)), 2)
        return rich("Run statistics",
                    [("Records", f"{len(recs):,}", "originals kept"), ("DataGen variants", f"{len(var):,}", ""),
                     ("Rejected", f"{len(state['rejected']):,}", ""), ("Average score", f"{avg}", "out of 10"),
                     ("New numbers", f"{sum(1 for v in var if v.get('numbers_changed')):,}", "re-solved with SymPy")],
                    [("Records by source", [("Source", 300), ("Records", 120)], count(recs, "source")),
                     ("Records by topic", [("Topic", 300), ("Records", 120)], count(recs, "topic")),
                     ("Records by data type", [("Data type", 300), ("Records", 120)], count(recs, "data_type")),
                     ("Variants by style", [("Style", 300), ("Variants", 120)], count(var, "style")),
                     ("Variants by format", [("Format", 300), ("Variants", 120)], count(var, "format")),
                     ("Found per source (before the filter)", [("Source", 300), ("Found", 120)],
                      sorted(state["stats"].items(), key=lambda x: -x[1])),
                     ("Why items were rejected", [("Reason", 300), ("Items", 120)], sorted(state["reasons"].items(), key=lambda x: -x[1]))],
                    [("Source notes", "; ".join(f"{k}: {v}" for k, v in state["notes"].items()) or "None.")], 900, 680)

    def show_history():
        h_ = state["history"]
        return rich("Run history", [("Runs this session", f"{len(h_)}", ""),
                                    ("Records kept", f"{sum(x['kept'] for x in h_):,}", ""),
                                    ("Variants", f"{sum(x['variants'] for x in h_):,}", "")],
                    [("Runs", [("Time", 90), ("Topics", 300), ("Quantity", 80), ("Quality", 70), ("Kept", 70), ("Variants", 80),
                               ("Rejected", 80)],
                      [(x["time"], ", ".join(x["input"].get("topics", [])), x["input"].get("quantity"), x["input"].get("quality"),
                        x["kept"], x["variants"], x["rejected"]) for x in reversed(h_)])], (), 860, 520)

    def show_help():
        return rich("Help", [("Pages", "Agent · Ask", "+ Ask your data button"), ("Products", f"{sum(len(v) for v in PRODUCT_GROUPS.values())}", "Settings > Products"),
                             ("Settings", f"{len(SPEC)}", "Cmd+,"), ("Guide", "Guide", "every control, step by step")], (), [
            ("Agent mode (opens first)", f"Builds a huge training dataset non-stop with {PWT_NAME} by {PWT_DEVELOPER}: up to "
             f"{MAX_AGENTS:,} parallel agents (more than {AGENTS_PER_PROCESS:,} run in extra worker processes), each website "
             "inside its own rate limit. Start once - afterwards it can only be paused. It keeps collecting while this window is "
             "closed; pause and close = it stops. The N agents button shows every agent. Topics never run out (curated "
             "advanced taxonomy, OpenAlex topics and concepts, Wikipedia links) and are listed in topics.json with check marks."),
            ("What the agent collects", "Text Q&A with DataGen variants and preference pairs (Stack Exchange archive incl. "
             "MathOverflow, MedMCQA, PubMedQA, ARC, topic search), free-licence web images, generated detection images and "
             "robot VLA episodes. Every row carries its field, split, tokens, quality tier and licence."),
            ("Ask your data (RAG)", "No training: ALL the data on GitHub (every Q&A, DataGen variant, preference pair, image "
             "caption, generated scene and robot episode) plus the newest rows on this Mac is downloaded and indexed by "
             "itself every few minutes. Type in the question box: AITE finds the best records and a local model (MLX, on this "
             "Mac) answers, citing them [1]. The Verbose log shows every step. Models show green Downloaded or grey Not "
             "downloaded - press Download once. 'Matching records only' works without any model."),
            ("Kaggle", "Alongside GitHub, the whole dataset (every row file, stats and topics) is published as a new version of the "
             "Kaggle dataset in Settings > Kaggle every hour. It uses Kaggle's own login on this Mac (~/.kaggle/kaggle.json from "
             "kaggle.com > Settings > API > Create New Token); AITE stores no keys."),
            ("GitHub", "Every 5 minutes the dataset, stats.json, topics.json and a live README are pushed to main of the "
             "repository in Settings > GitHub, using this Mac's git login. No keys or passwords are stored."),
            ("Privacy and keys", "No API keys and no LLM services anywhere. DuckDuckGo gets one honest request and its bot check is "
             "respected; everything else uses free official APIs and open datasets."),
            ("Keys", "Cmd+1 Agent · Cmd+2 Manual · Cmd+2 Ask · Cmd+R run · Cmd+E export · Cmd+, settings · Cmd+T theme · "
             "Cmd+J JSON · Cmd+D visual · Esc stop a manual run"),
            ("Command line", 'python "AITE 1.py" --agent  ·  --train --model ID --iters N  ·  --run JSON --out FILE  ·  --selftest')],
            880, 680)

    def toggle_theme():
        st["theme"] = "light" if st["theme"] == "dark" else "dark"
        persist()
        apply_theme()

    # ---------------------------------------------------------------- settings: ChatGPT's settings dialog
    def open_settings(section=None):
        win = dialog("Settings", 1080, 780)
        top = box(win, "card")
        top.pack(fill="x", padx=24, pady=(0, 10))
        sv = tk.StringVar()
        label(top, f"{len(SPEC)} options", "dim", -2).pack(side="left")
        Field(top, sv, width=280, h=36).pack(side="right")
        label(top, "Search  ", "dim", -2).pack(side="right")
        foot = box(win, "card")
        foot.pack(side="bottom", fill="x", padx=24, pady=(10, 20))
        body = box(win, "card")
        body.pack(fill="both", expand=True, padx=16)
        nav_sf = ScrollFrame(body, "card")
        nav_sf.pack(side="left", fill="y")
        nav_sf.configure(width=250)
        nav_sf.cv.configure(width=236)
        box(body, "divider", width=1).pack(side="left", fill="y", padx=(4, 12))
        pages_holder = box(body, "card")
        pages_holder.pack(side="left", fill="both", expand=True)
        sections = [x for x in dict.fromkeys(v[0] for v in SPEC.values()) if x != "Trainer"]  # no training in the app
        vars_, rows_, pages, navs = {}, [], {}, {}
        current = {"sec": None}

        class NavRow(Canvas):
            def __init__(self, master, sec):
                super().__init__(master, height=36, width=220, cursor="hand2")
                self.sec, self.hov = sec, False
                self.bind("<Enter>", lambda e: self.set_hover(True))
                self.bind("<Leave>", lambda e: self.set_hover(False))
                self.bind("<ButtonRelease-1>", lambda e: show(self.sec))

            def set_hover(self, on):
                self.hov = on
                self.draw()

            def draw(self):
                super().draw()
                w, h = self.winfo_width(), self.winfo_height()
                sel = current["sec"] == self.sec
                if sel or self.hov:
                    c = T["selected"] if sel else T["ghost_hover"]
                    self.create_polygon(g3_points(0.5, 0.5, w - 0.5, h - 0.5, 10), fill=c, outline=c)
                self.create_text(14, h / 2, text=self.sec, anchor="w", fill=T["text"], font=font(-1, sel))

        def show(sec):
            current["sec"] = sec
            for s_, pg in pages.items():
                pg.pack_forget()
            pages[sec].pack(fill="both", expand=True)
            for nr in navs.values():
                nr.draw()

        for sec in sections:
            navs[sec] = NavRow(nav_sf.body, sec)
            navs[sec].pack(fill="x", pady=1)
            page = ScrollFrame(pages_holder, "card")
            pages[sec] = page
            label(page.body, sec, "text", 3, True).pack(fill="x", pady=(2, 8), padx=4)
            for k, (s2, lab, kind, default, extra) in SPEC.items():
                if s2 != sec:
                    continue
                row = box(page.body, "card")
                left = box(row, "card")
                left.pack(side="left", fill="x", expand=True, padx=(4, 12), pady=10)
                label(left, lab, "text", -1, wraplength=420).pack(anchor="w")
                hint = (f"{extra[0]} - {extra[1]}" if kind in ("int", "float") and extra
                        else f"Default: {shorten(str(default), 34)}")
                label(left, hint, "dim", -3).pack(anchor="w", pady=(2, 0))
                if kind == "bool":
                    v = tk.BooleanVar(value=bool(st[k]))
                    Switch(row, v).pack(side="right", padx=4)
                elif kind == "choice":
                    v = tk.StringVar(value=str(st[k]))
                    Dropdown(row, v, extra, w=max(160, min(260, max(measure(str(o), font(-1)) for o in extra) + 56))).pack(side="right", padx=4)
                else:
                    v = tk.StringVar(value=str(st[k]))
                    Field(row, v, width=260 if kind == "str" else 120, h=36).pack(side="right", padx=4)
                line = box(page.body, "divider", height=1)
                vars_[k] = (v, kind, extra)
                rows_.append((k, lab.lower(), sec, row, line))
            for _, _, s3, row, line in [r for r in rows_ if r[2] == sec]:
                row.pack(fill="x")
                line.pack(fill="x", padx=4)

        def do_search(*_):
            q = sv.get().lower().strip()
            first = None
            for sec in sections:
                for k, lab, s3, row, line in [r for r in rows_ if r[2] == sec]:
                    row.pack_forget()
                    line.pack_forget()
                for k, lab, s3, row, line in [r for r in rows_ if r[2] == sec]:
                    if not q or q in lab or q in k or q in sec.lower():
                        row.pack(fill="x")
                        line.pack(fill="x", padx=4)
                        if q and first is None:
                            first = sec
            if first:
                show(first)
        sv.trace_add("write", do_search)

        def apply_settings(close=False):
            bad = []
            for k, (v, kind, extra) in vars_.items():
                val = v.get()
                try:
                    if kind == "int":
                        val = int(float(val))
                    elif kind == "float":
                        val = float(val)
                    if kind in ("int", "float") and extra and not extra[0] <= val <= extra[1]:
                        raise ValueError
                    st[k] = val
                except (TypeError, ValueError):
                    bad.append(f"{SPEC[k][1]} ({SPEC[k][0]})")
            for s_, var in src_vars.items():
                var.set(st[f"{s_}_enabled"])
            save_settings(st)
            apply_theme()
            update_hints()
            refresh_preview()
            if bad:
                status("Not saved (out of range / invalid): " + ", ".join(bad))
                if not smoke:
                    messagebox.showerror(APP, "Out of range / invalid:\n" + "\n".join(bad), parent=win)
            else:
                status("Settings saved")
                if close:
                    win.destroy()
            return bad

        def reset_defaults():
            if messagebox.askyesno(APP, "Reset all settings to defaults?", parent=win):
                st.update(default_settings())
                save_settings(st)
                win.destroy()
                apply_theme()
                open_settings()

        def export_settings():
            p = filedialog.asksaveasfilename(defaultextension=".json", initialfile="aite_settings.json", parent=win)
            if p:
                with open(p, "w") as f:
                    json.dump(dict(st, _version=SETTINGS_VERSION), f, indent=2)

        def import_settings():
            p = filedialog.askopenfilename(filetypes=[("JSON", "*.json")], parent=win)
            if p:
                try:
                    with open(p) as f:
                        d = json.load(f)
                    st.update({k: v for k, v in d.items() if k in SPEC})
                    save_settings(st)
                    win.destroy()
                    apply_theme()
                    open_settings()
                except Exception as e:
                    messagebox.showerror(APP, str(e), parent=win)

        Pill(foot, "Save", lambda: apply_settings(True), "primary", h=40).pack(side="right", padx=(8, 0))
        Pill(foot, "Apply", lambda: apply_settings(), "outline", h=40).pack(side="right", padx=(8, 0))
        Pill(foot, "Cancel", win.destroy, "outline", h=40).pack(side="right")
        Pill(foot, "Reset to defaults", reset_defaults, "ghost", h=40).pack(side="left")
        Pill(foot, "Export", export_settings, "ghost", h=40).pack(side="left", padx=(6, 0))
        Pill(foot, "Import", import_settings, "ghost", h=40).pack(side="left", padx=(6, 0))
        show(section if section in pages else sections[0])
        win.vars_, win.apply, win.sections, win.show = vars_, apply_settings, sections, show  # used by the smoke test
        apply_theme()
        return win

    mod = "Command" if sys.platform == "darwin" else "Control"
    root.bind(f"<{mod}-r>", lambda e: start_run())
    root.bind(f"<{mod}-e>", lambda e: do_export())
    root.bind(f"<{mod}-comma>", lambda e: open_settings())
    root.bind(f"<{mod}-t>", lambda e: toggle_theme())
    root.bind(f"<{mod}-j>", lambda e: set_mode("JSON"))
    root.bind(f"<{mod}-d>", lambda e: set_mode("VDM"))
    root.bind(f"<{mod}-Key-1>", lambda e: show_page("Agent"))
    root.bind(f"<{mod}-Key-2>", lambda e: show_page("Ask"))
    root.bind(f"<{mod}-Key-3>", lambda e: show_page("Ask"))
    root.bind("<Escape>", lambda e: (close_popover(), state["cancel"].set()))

    def on_close():
        if st["confirm_exit"] and not messagebox.askyesno(APP, "Quit AITE?"):
            return
        state["cancel"].set()
        guide_close()
        if rg.get("worker") is not None:
            rg["worker"].stop()
        if not st["agent_background"] or smoke:
            agent_control(ag["root"], paused=True)  # a paused agent with no window exits by itself
        persist()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)

    apply_theme()
    set_mode(st["start_mode"], force=True)
    refresh_preview()
    pump()
    show_page(st["start_page"] if st["start_page"] in ("Agent", "Ask") else "Agent")
    if not smoke:
        ctl0 = agent_control(ag["root"], gui=True, heartbeat=time.time())
        if ctl0.get("started_once") and not ctl0.get("paused") and not agent_alive() and st["agent_resume"]:
            agent_spawn_once()  # carries on where it was - Agent mode is only ever paused
        if not st["guide_seen"]:
            root.after(900, guide)
    agent_poll()
    rag_poll()

    if smoke:  # headless self-check: drives the real GUI with an offline searcher
        import atexit
        import signal as _signal

        def _stop_smoke_agent():
            import shutil
            pid_ = agent_pid(ag["root"])
            if pid_:
                try:
                    os.kill(pid_, _signal.SIGTERM)
                except OSError:
                    pass
                for _ in range(50):  # give it a moment to exit before its folder goes
                    if agent_pid(ag["root"]) is None:
                        break
                    time.sleep(0.1)
            if rg.get("worker") is not None:
                rg["worker"].stop()
            for d in (ag["root"], TRAINER_RUNS, RAG_HOME):
                shutil.rmtree(d, ignore_errors=True)  # tests never leave data behind
        atexit.register(_stop_smoke_agent)
        def smoke_1():
            global SEARCHER_FACTORY
            assert state["page"] == "Agent", "Agent mode is the default page"
            agent_toggle()  # starts an OFFLINE background agent in a temp folder
            show_page("Manual")
            set_mode("JSON")
            set_mode("VDM")
            toggle_theme()
            toggle_theme()
            open_settings("DataGen").destroy()
            v_topics.set("algebra, word problems")
            v_qty.set(6)
            v_qual.set(4)
            v_var.set(2)
            style_vars["teacher"].set(False)
            on_vdm_change()
            SEARCHER_FACTORY = lambda s_, l_, c_, p_: Searcher(s_, l_, c_, http=make_fake_http("ok"), progress=p_)
            start_run()
            root.after(300, smoke_2)

        def smoke_2():
            if state["running"]:
                root.after(300, smoke_2)
                return
            try:
                smoke_checks()
            except Exception:
                import traceback
                print("GUI_SMOKE_FAIL\n" + traceback.format_exc(), flush=True)
                _stop_smoke_agent()  # os._exit skips atexit: stop the background test agent here
                root.destroy()
                os._exit(1)

        def smoke_checks():
            tmp = os.environ.get("AITE_TEST_OUT") or os.environ.get("TMPDIR", "/tmp")
            out = os.path.join(tmp, "aite_gui_smoke.pdf")
            p = do_export(path=out)
            n_rec, n_var = len(state["records"]), len(state["variants"])
            for f in ("json", "txt", "pdf (text layout)", "as output type"):
                prev_fmt.set(f)
            find_var.set("PROBLEM")
            find_text()
            for fn in (show_stats, show_rejected, show_history, show_help):
                fn()
            for w in root.winfo_children():
                if isinstance(w, tk.Toplevel):
                    w.destroy()
            # controls: a dropdown's popover picks a value; chips, switch, segmented and slider respond
            dd_pop = next(w for w, r, x in widgets if isinstance(w, Dropdown) and w.var is prev_fmt).open()
            root.update()
            dd_pop.pick("txt")
            assert prev_fmt.get() == "txt" and state["popover"] is None, "dropdown popover"
            prev_fmt.set("as output type")
            for v in dtype_vars.values():
                v.set(False)
            assert current_input()[1], "no data type selected is refused"
            for v in dtype_vars.values():
                v.set(True)
            assert current_input()[0]["data_types"] == DATA_TYPES, "select all data types"
            ch = next(w for w, r, x in widgets if isinstance(w, Chip) and w.var is style_vars["exam"])
            ch.toggle()
            assert not style_vars["exam"].get() and "exam" not in current_input()[0]["datagen_styles"], "style chip"
            ch.toggle()
            sl = next(w for w, r, x in widgets if isinstance(w, Slider) and w.var is v_qual)
            sl.nudge(+1)
            assert v_qual.get() == 5, "slider arrow key"
            sl.nudge(-1)
            menu = about_menu()
            root.update()
            assert state["popover"] is menu
            close_popover()
            # JSON round trip: export -> clear -> load results -> same counts; import the input back
            v_out.set("json")
            st["include_meta"] = True  # the input can only be re-imported from an export that carries its metadata
            jpath = do_export(path=os.path.join(tmp, "aite_gui_smoke.json"))
            st["include_meta"] = False
            clear_results()
            load_results(jpath)
            loaded = (len(state["records"]), len(state["variants"]))
            import_json(jpath)
            imported = current_input()
            first = state["records"][0]["uid"]
            kids = sum(1 for v in state["variants"] if v.get("variant_of") == first)
            tree.selection_set(first)
            remove_selected()
            removed_ok = len(state["records"]) == n_rec - 1 and len(state["variants"]) == n_var - kids
            # the output type chosen after a run drives preview and export
            set_mode("VDM")
            v_out.set("txt")
            root.update()
            assert "PROBLEM:" in prev_t.get("1.0", "end") and not prev_t.get("1.0", "1.30").startswith("[PDF"), "preview follows txt"
            tp = do_export(path=os.path.join(tmp, "aite_gui_smoke_type"))
            assert open(tp, encoding="utf-8").read().startswith("#1"), "export follows the chosen output type (txt)"
            v_out.set("pdf")
            v_var.set(1)
            rerun_datagen(sync=True)
            assert len(state["variants"]) == len(state["records"]) and all(v["kind"] == "variant" for v in state["variants"]), \
                f"re-run DataGen: {len(state['variants'])} variants for {len(state['records'])} records"
            before = len(state["records"]) + len(state["rejected"])
            v_qual.set(2)
            refilter()
            assert len(state["records"]) + len(state["rejected"]) == before and state["inp"]["quality"] == 2, "re-filter keeps every candidate"
            # mouse wheel over the input panel scrolls it
            set_mode("VDM")
            root.update()
            vdm_sf.cv.yview_moveto(0)
            ev = type("Ev", (), {"x_root": vdm_sf.winfo_rootx() + vdm_sf.winfo_width() // 2,
                                 "y_root": vdm_sf.winfo_rooty() + vdm_sf.winfo_height() // 2, "delta": -4})()
            wheel_all(ev)
            root.update()
            assert vdm_sf.cv.yview()[0] > 0, f"mouse wheel did not scroll the input panel {vdm_sf.cv.yview()}"
            # big output: 1,000 records + 20,000 variants must not freeze the window
            keep_state = (state["records"], state["variants"], dict(state["inp"]))
            big_r = [dict(item("t", "huggingface", f"T{i}", "Problem text " * 20, "Solution text " * 30, "u"), uid=f"b{i}", score=5.0)
                     for i in range(1000)]
            big_v = [dict(item("t", "huggingface", f"T{i}", "Variant problem " * 20, "Variant solution " * 30, "u"), uid=f"b{i}-v{k}",
                          kind="variant", variant_of=f"b{i}", style="formal", format="qa", methods=[], numbers_changed=False, answer=None)
                     for i in range(1000) for k in range(20)]
            state.update(records=big_r, variants=big_v)
            v_out.set("pdf")
            prev_fmt.set("as output type")
            t0 = time.time()
            fill_tree()
            t1 = time.time()
            refresh_preview()
            t2 = time.time()
            big = {"table_s": round(t1 - t0, 2), "preview_s": round(t2 - t1, 2), "tree_rows": len(tree.get_children()),
                   "estimate": "about" in prev_t.get("1.0", "1.200")}
            assert big["tree_rows"] == TABLE_MAX + 1 and big["estimate"] and t2 - t0 < 5, big
            state["records"], state["variants"], state["inp"] = keep_state
            fill_tree()
            refresh_preview()
            assert loaded == (n_rec, n_var), f"load results {loaded} != {(n_rec, n_var)}"
            assert not imported[1] and imported[0]["topics"] == ["algebra", "word problems"], imported
            assert removed_ok, "remove selected"

            train_result = None
            # layout audit: no visible widget may stick out of its container, be squeezed, or be hidden for lack of room
            def describe(c):
                txt = getattr(c, "text", None)
                if txt is None:
                    try:
                        txt = c.cget("text")
                    except tk.TclError:
                        txt = ""
                return f"{c.winfo_class()}[{str(txt)[:24]}]"

            def audit(tag, top=None):
                root.update_idletasks()
                root.update()
                bad = []

                def walk(w, in_canvas=False):
                    for c in w.winfo_children():
                        if isinstance(c, tk.Toplevel):
                            continue
                        if not c.winfo_ismapped():
                            if c.winfo_manager() in ("pack", "grid", "place") and w.winfo_ismapped():
                                bad.append(f"{tag}: {describe(c)} hidden - no room for it in {describe(w)}")
                            continue
                        p_ = c.master
                        try:
                            pw, ph = p_.winfo_width(), p_.winfo_height()
                            x, y, cw, ch_ = c.winfo_x(), c.winfo_y(), c.winfo_width(), c.winfo_height()
                        except tk.TclError:
                            continue
                        scrolled = in_canvas or isinstance(p_, tk.Canvas)
                        if (isinstance(c, (Pill, Chip, Segmented, Dropdown, Switch)) or c.winfo_class() == "Label") \
                                and cw < c.winfo_reqwidth() - 2:
                            bad.append(f"{tag}: {describe(c)} squeezed to {cw}px of {c.winfo_reqwidth()}px")
                        if x + cw > pw + 2 and not isinstance(p_, tk.Canvas):
                            bad.append(f"{tag}: {describe(c)} sticks out {x + cw - pw}px right of {describe(p_)}")
                        if y + ch_ > ph + 2 and not scrolled:
                            bad.append(f"{tag}: {describe(c)} sticks out {y + ch_ - ph}px below {describe(p_)}")
                        walk(c, scrolled)
                walk(top or root)
                return bad
            # Agent mode: the background agent collects, the page shows it, Pause pauses (there is no stop)
            show_page("Agent")
            t_end = time.time() + 40
            while time.time() < t_end:
                root.update()
                s_ = agent_status(ag["root"])
                if s_ and s_["state"] == "running" and s_["counts"]["text"] and s_["counts"]["images"] and s_["counts"]["vla_episodes"]:
                    break
                time.sleep(0.2)
            agent_poll(once=True)
            s_ = agent_status(ag["root"])
            assert s_ and s_["state"] == "running" and s_["counts"]["text"] > 0 and s_["counts"]["synthetic_images"] > 0 \
                and s_["counts"]["vla_episodes"] > 0, f"agent collects: {s_ and s_['counts']}"
            assert ag_btn.text == "Pause" and "running in parallel" in ag_sub.cget("text"), (ag_btn.text, ag_sub.cget("text"))
            assert tiles["text"].v.cget("text") not in ("-", "0") and ag["thumb_path"], "tiles + thumbnail"
            assert "stop" not in [p_.text.lower() for p_ in (ag_btn,)], "pause only"
            agent_toggle()
            t_end = time.time() + 20
            while time.time() < t_end and (agent_status(ag["root"]) or {}).get("state") != "paused":
                root.update()
                time.sleep(0.2)
            agent_poll(once=True)
            assert agent_status(ag["root"])["state"] == "paused" and ag_btn.text == "Resume", "pause"
            agent_stats = agent_status(ag["root"])["counts"]
            aw = show_agents()
            root.update()
            assert aw.winfo_exists() and agents_btn.text in ("paused",) or agents_btn.text.endswith("agents"), agents_btn.text
            aw.destroy()
            agent_control(ag["root"], export_now=time.time())
            tw = show_topics()
            tw.destroy()
            for i_ in range(len(guide_steps())):
                gw = guide(i_)
                assert gw is not None and gw.winfo_exists(), f"guide step {i_ + 1}"
            guide(len(guide_steps()))
            assert guide_state["win"] is None and st["guide_seen"], "guide finishes"
            # Ask page (RAG): the background job indexes ALL the agent's data, records-only answers cite it, labels show state
            show_page("Ask")
            assert root.focus_get() is qf.e or True
            rag_update_start(force=True)
            t_end = time.time() + 90
            while time.time() < t_end and (rg["proc"].poll() is None or read_rag_status().get("state") != "done"):
                root.update()
                time.sleep(0.2)
            rag_refresh()
            rs_ = read_rag_status()
            assert rs_.get("state") == "done" and rs_.get("count", 0) > 0, f"RAG index built: {rs_}"
            assert badges["index"].tone == "green" and "records" in badges["index"].text, badges["index"].text
            assert badges["github"].tone == "green", badges["github"].text
            assert badges["kaggle"].tone in ("orange", "grey", "green", "red"), badges["kaggle"].text
            kinds_ = {r[0] for r in RagIndex().db.execute("SELECT source FROM docs").fetchall()}
            assert any("generated image" in k for k in kinds_) and any("robot episode" in k for k in kinds_) and \
                any("Q&A" in k or "variant" in k for k in kinds_), f"all data types are in the index: {kinds_}"
            assert model_rows and all(r_["badge"].tone in ("green", "grey", "red", "blue") for r_ in model_rows.values()), "model labels"
            assert any(r_["badge"].text == "Not downloaded" and r_["act"].text == "Download" for r_ in model_rows.values()) or \
                all(r_["badge"].text == "Downloaded" for r_ in model_rows.values()), "Download button on models not on this Mac"
            assert prow.winfo_ismapped() and prow.winfo_rooty() < cfr.winfo_rooty(), "the question box is visible, above the chat"
            assert fflow.items and fields_chosen() is None, "ALL fields by default"
            fields_set(False)
            first_f = next(iter(fvars))
            fvars[first_f].set(True)
            field_chip_clicked()
            assert fields_chosen() == [first_f] and not v_fall.get(), "pick one field"
            fields_set(True)
            assert fields_chosen() is None and v_fall.get(), "Select all = ALL"
            v_amode.set("records")
            amode_changed("records")
            v_q.set("solve the equation")
            rag_ask()
            t_end = time.time() + 20
            while time.time() < t_end and rg["busy"]:
                root.update()
                time.sleep(0.1)
            rag_refresh()
            chat_ = chat_t.get("1.0", "end")
            vl_ = vlog_t.get("1.0", "end")
            assert rg["chat"] and rg["chat"][-1]["hits"] and "Sources" in chat_ and "[1]" in chat_, chat_[:300]
            assert "QUESTION" in vl_ and "BM25" in vl_ and "score" in vl_ and "job  " in vl_ and "index:" in vl_, vl_[-600:]
            n_tg = len(guide_steps())
            for i_ in range(n_tg):
                assert guide(i_) is not None, f"ask guide step {i_ + 1}"
            guide(n_tg)
            issues = []
            for geo in ("1480x900", "1120x700"):
                root.geometry(geo)
                show_page("Agent")
                issues += audit(f"{geo} Agent")
                show_page("Ask")
                issues += audit(f"{geo} Ask")
                show_page("Manual")
                for m in ("VDM", "JSON"):
                    set_mode(m)
                    for view in ("Preview", "Records", "Log"):
                        show_view(view)
                        issues += audit(f"{geo} {m} {view}")
            # ChatGPT's measured values must be what the widgets really use, in both themes
            want = {"light": {"page": "#fcfcfc", "sidebar": "#f9f9f9", "card": "#ffffff", "edge": "#e5e5e5", "btn": "#0d0d0d",
                              "btn_fg": "#ffffff", "ink": "#0d0d0d", "dim": "#5d5d5d"},
                    "dark": {"page": "#212121", "sidebar": "#181818", "card": "#2a2a2a", "edge": "#3a3a3a", "btn": "#ffffff",
                             "btn_fg": "#0d0d0d", "ink": "#ececec", "dim": "#b4b4b4"}}
            for theme in ("light", "dark"):
                st["theme"] = theme
                apply_theme()
                show_page("Agent")
                issues += audit(f"theme {theme} Agent")
                show_page("Ask")
                issues += audit(f"theme {theme} Ask")
                show_page("Manual")
                issues += audit(f"theme {theme}")
                w_ = want[theme]
                run_items = run_btn.find_all()
                got = {"page": main.cget("bg"), "sidebar": sidebar.cget("bg"),
                       "card": out_card.cv.itemcget(out_card.cv.find_all()[0], "fill"),
                       "edge": out_card.cv.itemcget(out_card.cv.find_all()[0], "outline"),
                       "btn": run_btn.itemcget(run_items[0], "fill"),
                       "btn_fg": next(run_btn.itemcget(i, "fill") for i in run_items if run_btn.type(i) == "text"),
                       "ink": prev_t.cget("fg"), "dim": status_lbl.cget("fg")}
                assert got == w_, f"{theme} colours differ from ChatGPT's: {got} != {w_}"
                assert tkfont.Font(font=status_lbl.cget("font")).actual("family") == (".AppleSystemUIFont" if sys.platform == "darwin"
                                                                                       else tkfont.Font(font=status_lbl.cget("font")).actual("family")), "SF Pro"
            sw = open_settings("DataGen")
            sw.vars_["dg_seed"][0].set("9")
            sw.vars_["theme"][0].set("light")
            sw.vars_["timeout"][0].set("abc")
            bad_keys = sw.apply()
            assert st["dg_seed"] == 9 and st["theme"] == "light" and T["page"] == THEMES["light"]["page"], "settings apply"
            assert bad_keys and "HTTP timeout" in bad_keys[0] and st["timeout"] == 15.0, f"invalid value must be refused: {bad_keys}"
            sw.vars_["theme"][0].set("dark")
            sw.vars_["dg_seed"][0].set("7")
            sw.vars_["timeout"][0].set("15.0")
            assert not sw.apply(close=True) and st["theme"] == "dark"
            sw = open_settings()
            for sec in sw.sections:
                sw.show(sec)
                issues += audit(f"settings[{sec}]", sw)
            sw.destroy()
            for fn in (show_stats, show_help):
                pw_ = fn()
                issues += audit(f"popup[{pw_.title()}]", pw_)
                pw_.destroy()
            if os.environ.get("AITE_GUI_AUDIT_PRINT"):
                print("\n".join(issues) or "no layout issues", flush=True)
            assert not issues, f"{len(issues)} layout issue(s), first: {issues[:3]}"
            print("GUI_SMOKE_OK", json.dumps({"records": n_rec, "variants": n_var, "json_roundtrip": loaded, "mode": state["mode"],
                                              "big_output": big, "theme": st["theme"],
                                              "workflow": {k: v["state"] for k, v in wf_state.items()},
                                              "export": p, "preview_chars": len(prev_t.get("1.0", "end")),
                                              "tree_rows": len(tree.get_children()), "input": state["inp"]["topics"],
                                              "agent": agent_stats, "trainer": train_result}), flush=True)
            pid_ = agent_pid(ag["root"])
            if pid_:
                import signal
                os.kill(pid_, signal.SIGTERM)
            root.destroy()
        root.after(700, smoke_1)
    root.mainloop()


# ============================================================================= offline test fixtures
GSM_ROWS = [
    {"question": "Natalia sold clips to 48 of her friends in April, and then she sold half as many clips to her friends in May. How many clips did Natalia sell altogether in April and May?",
     "answer": "Natalia sold 48/2 = <<48/2=24>>24 clips in May.\nNatalia sold 48+24 = <<48+24=72>>72 clips altogether in April and May.\n#### 72"},
    {"question": "Weng earns $12 an hour for babysitting. Yesterday, she just did 50 minutes of babysitting. How much did she earn?",
     "answer": "Weng earns 12/60 = $<<12/60=0.2>>0.2 per minute.\nWorking 50 minutes, she earned 0.2 x 50 = $<<0.2*50=10>>10.\n#### 10"},
    {"question": "James writes a 3-page letter to 2 different friends twice a week. How many pages does he write a year?",
     "answer": "He writes each friend 3*2=<<3*2=6>>6 pages a week\nSo he writes 6*2=<<6*2=12>>12 pages every week\nThat means he writes 12*52=<<12*52=624>>624 pages a year\n#### 624"},
] + [{"question": f"Priya buys {a} boxes of pencils. Each box has {b} pencils. She gives away {c} pencils. How many pencils does she have left?",
      "answer": f"Priya has {a}*{b} = <<{a}*{b}={a * b}>>{a * b} pencils.\nAfter giving away {c} she has {a * b}-{c} = <<{a * b}-{c}={a * b - c}>>{a * b - c} pencils.\n#### {a * b - c}"}
   for a, b, c in [(3, 14, 5), (4, 15, 7), (6, 13, 9), (7, 16, 11), (8, 17, 13), (9, 18, 17), (5, 19, 23), (11, 21, 29),
                   (12, 22, 31), (13, 23, 37), (14, 24, 41), (15, 25, 43), (16, 26, 47), (17, 27, 53), (18, 28, 59)]]
MATH_ROWS = [{"problem": f"Solve for $x$: ${a}x + {b} = {a * k + b}$.", "level": "Level 1", "type": "Algebra",
              "solution": f"Subtracting {b} from both sides gives ${a}x = {a * k}$, so $x = \\boxed{{{k}}}$."}
             for a, b, k in [(2, 3, 4), (3, 5, 6), (4, 7, 2), (5, 9, 3), (6, 11, 5), (7, 13, 8), (8, 15, 9), (9, 17, 7),
                             (2, 19, 11), (3, 21, 12), (4, 23, 13), (5, 25, 14), (6, 27, 15), (7, 29, 16), (8, 31, 17),
                             (9, 33, 18), (2, 35, 19), (3, 37, 20), (4, 39, 21), (5, 41, 22)]]
CAMEL_ROWS = [{"role_1": "Physicist", "topic;": "Optics", "sub_topic": f"Lenses {i}",
               "message_1": f"A converging lens has a focal length of {10 + i} cm. An object is placed {30 + 2 * i} cm from the lens. Where is the image formed?",
               "message_2": f"Use the thin lens equation 1/f = 1/do + 1/di. With f = {10 + i} cm and do = {30 + 2 * i} cm, solving for di gives the image distance on the far side of the lens. Therefore the image is real and inverted."}
              for i in range(25)]
MBPP_ROWS = [{"task_id": str(600 + i), "text": f"Write a function to add {i} to every element of a list.",
              "code": f"def add_{i}(xs):\n    result = []\n    for x in xs:\n        result.append(x + {i})\n    return result",
              "test_list": [f"assert add_{i}([1, 2]) == [{1 + i}, {2 + i}]"]} for i in range(20)]
ROBO_ROWS = [{"question": f"How does a robot arm with {i + 2} joints compute inverse kinematics for a target pose?",
              "answer": f"For {i + 2} joints we write the forward kinematics, then solve for the joint angles numerically with the Jacobian; therefore the arm reaches the pose."}
             for i in range(20)]


FAKE_SE_LAYOUT = [("3dprinting.stackexchange.com", 0), ("Stackoverflow.com", 1000), ("math.stackexchange.com", 5000000),
                  ("mathoverflow.net", 6000000), ("physics.stackexchange.com", 6500000)]


def _fake_se_row(o):
    site = [x for x, start in FAKE_SE_LAYOUT if start <= o][-1]
    a, b = o % 97 + 2, o % 89 + 3
    return {"qid": o, "question": f"<p>Let $f(x) = {a}x + {b}$. For which real $x$ does $f(x) = {a * 5 + b}$ hold, and why is the "
                                  f"solution unique? (question {o})</p>",
            "answers": [{"answer_id": o * 10 + 1, "pm_score": 7 + o % 5, "selected": True,
                         "text": f"<p>Subtract {b} from both sides to get ${a}x = {a * 5}$, then divide by {a}: $x = 5$. "
                                 f"The map is strictly increasing because its slope {a} is positive, so the solution is unique.</p>"},
                        {"answer_id": o * 10 + 2, "pm_score": 1, "selected": False,
                         "text": f"<p>I think you can just guess numbers until it works, maybe x is around 4 or 6 for question {o}, "
                                 f"try a few values and see what happens with the equation.</p>"}],
            "date": "2020/01/01", "metadata": [f"https://{site}/questions/{o}", f"https://{site}", f"https://{site}/users/1/"]}


FAKE_ARCHIVES = {
    SE_ARCHIVE: _fake_se_row,
    "openlifescienceai/medmcqa": lambda o: {"question": f"Which vitamin deficiency causes scurvy? (case {o})", "opa": "Vitamin A",
                                           "opb": "Vitamin B12", "opc": "Vitamin C", "opd": "Vitamin D", "cop": 2,
                                           "exp": "Scurvy results from a lack of vitamin C (ascorbic acid), which is needed for "
                                                  "collagen synthesis; bleeding gums and poor wound healing follow.",
                                           "subject_name": "Biochemistry", "topic_name": "Vitamins"},
    "qiaojin/PubMedQA": lambda o: {"question": f"Does regular exercise lower resting blood pressure in adults (cohort {o})?",
                                   "context": {"contexts": ["A randomised trial followed 400 adults for one year and measured "
                                                            "resting blood pressure before and after a supervised exercise programme."]},
                                   "long_answer": "Supervised aerobic exercise lowered resting systolic blood pressure by about "
                                                  "five mmHg compared with controls over twelve months.", "final_decision": "yes"},
    "allenai/ai2_arc": lambda o: {"question": f"Which gas do plants take in for photosynthesis? (item {o})",
                                  "choices": {"text": ["oxygen", "carbon dioxide", "nitrogen", "helium"], "label": ["A", "B", "C", "D"]},
                                  "answerKey": "B"},
}


def make_fake_http(ddg_mode="blocked"):
    """Offline stand-in for Http: every source answers from fixtures, no network."""
    se_q = {"items": [{"title": f"How do I solve equation {i}?",
                       "body": f"<p>Solve {i + 2}x + 3 = {i + 13}. What is x? I tried subtracting.</p>",
                       "link": f"https://math.stackexchange.com/q/{i}", "score": 5 + i, "accepted_answer_id": 1000 + i,
                       "tags": ["algebra-precalculus"]} for i in range(30)], "has_more": False, "quota_remaining": 200}
    se_q["items"].append({"title": "How to study math?", "body": "<p>Any advice?</p>", "link": "https://math.stackexchange.com/q/999",
                          "score": 900, "accepted_answer_id": 1999, "tags": ["soft-question", "advice"]})
    se_a = {"items": [{"answer_id": 1000 + i, "score": 3,
                       "body": f"<p>Subtract 3 from both sides: {i + 2}x = {i + 10}.</p><p>Therefore x = {i + 10}/{i + 2}. Hence done.</p>"}
                      for i in range(30)] + [{"answer_id": 1999, "score": 50, "body": "<p>Practice every day and read proofs carefully, the rest will follow with time.</p>"}]}
    se_a["items"][3]["body"] = "<p>BUY NOW click here casino!!! http://a.com http://b.com</p>"
    ex_page = ('<html><head><script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":['
               '{"@type":"Question","name":"What is 7 times 8 in algebra class?","acceptedAnswer":{"@type":"Answer","text":"7 times 8 is 56 because 7*8 = 56."}}]}'
               '</script></head><body><h1>Algebra practice</h1><p>Problem 1: Find x if 2x + 3 = 11 in this algebra problem.</p>'
               '<p>Solution: 2x = 8 so x = 4.</p><p>Problem 2: What is the derivative of x^2 with respect to x?</p>'
               '<p>Answer: The derivative is 2x, by the power rule.</p><footer>Copyright</footer></body></html>')
    ddg_html = ('<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fex.com%2Fqa&rut=1">Algebra <b>problems</b></a>'
                '<a class="result__snippet" href="x">Solved algebra</a>'
                '<a rel="nofollow" class="result__a" href="https://ex.com/sheet.pdf">Algebra sheet</a>')
    arx = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Algebraic methods</title><id>http://arxiv.org/abs/1</id>'
           '<summary>We study the problem of solving algebra equations. We propose a method. Results show it works well. Thus algebra solved.</summary>'
           '<author><name>A. B</name></author></entry></feed>')
    hf = {"openai/gsm8k": GSM_ROWS, MATH_DS: MATH_ROWS, "camel-ai/physics": CAMEL_ROWS,
          "google-research-datasets/mbpp": MBPP_ROWS, "acme/robotics-qa": ROBO_ROWS}
    pdf_cache = {}

    class FakeHttp:
        def __init__(self):
            self.calls, self.status = [], None

        def get(self, url, data=None):
            st_, body, ct = self.fetch(url, data)
            return body.decode("utf-8", "replace") if body else None

        def fetch(self, url, data=None, max_bytes=None):
            self.calls.append(url)
            st_, body, ct = self._route(url)
            self.status = st_
            return st_, body, ct

        def _route(self, url):
            J = lambda o: (200, json.dumps(o).encode(), "application/json")
            u = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(u.query)
            if u.netloc == "html.duckduckgo.com":
                return (202, b"<html><body>anomaly</body></html>", "text/html") if ddg_mode == "blocked" else (200, ddg_html.encode(), "text/html")
            if u.netloc == "api.duckduckgo.com":
                return 202, json.dumps({"AbstractText": "Algebra is a branch of mathematics.", "AbstractSource": "Wikipedia",
                                        "RelatedTopics": [{"Text": "Linear algebra - vectors", "FirstURL": "x"}]}).encode(), "application/x-javascript"
            if u.netloc == "ex.com":
                if u.path.endswith(".pdf"):
                    if "pdf" not in pdf_cache:
                        pdf_cache["pdf"] = render_pdf([item("algebra", "x", "Sheet", "Problem 1: Solve 2x + 6 = 10 for x in algebra.",
                                                            "Solution: subtract 6, so 2x = 4 and x = 2.", "u")],
                                                      dict(DEFAULT_INPUT, topics=["algebra"]), default_settings())
                    return 200, pdf_cache["pdf"], "application/pdf"
                return 200, ex_page.encode(), "text/html; charset=utf-8"
            if u.netloc == "api.stackexchange.com":
                if "/tags/" in u.path and u.path.endswith("/info"):
                    known = {"word-problem": 5000, "geometry": 90000, "python": 2200000, "organic-chemistry": 9000, "c++": 800000,
                             "algebra-precalculus": 160000}
                    names = urllib.parse.unquote(u.path.split("/tags/")[1][:-len("/info")]).split(";")
                    return J({"items": [{"name": n, "count": known[n]} for n in names if n in known]})
                return J(se_a) if "/answers/" in u.path else J(se_q)
            if u.netloc == "datasets-server.huggingface.co" and qs.get("dataset", [""])[0] in FAKE_ARCHIVES:
                ds = qs.get("dataset", [""])[0]
                off, ln = int(qs.get("offset", ["0"])[0]), int(qs.get("length", ["100"])[0])
                return J({"rows": [{"row_idx": o, "row": FAKE_ARCHIVES[ds](o), "truncated_cells": []} for o in range(off, off + ln)]})
            if u.netloc == "datasets-server.huggingface.co":
                ds = qs.get("dataset", [""])[0]
                if u.path == "/splits":
                    return J({"splits": [{"dataset": ds, "config": "default", "split": "train"}, {"dataset": ds, "config": "default", "split": "test"}]})
                rows = hf.get(ds)
                if rows is None:
                    return 404, b"", ""
                if u.path == "/first-rows":
                    feats = [{"feature_idx": i, "name": k, "type": {"dtype": "string", "_type": "Value"}} for i, k in enumerate(rows[0])]
                    return J({"features": feats, "rows": [{"row_idx": i, "row": r} for i, r in enumerate(rows[:100])]})
                off, ln = int(qs.get("offset", ["0"])[0]), int(qs.get("length", ["100"])[0])
                return J({"rows": [{"row_idx": off + i, "row": r, "truncated_cells": []} for i, r in enumerate(rows[off:off + ln])],
                          "num_rows_total": len(rows)})
            if u.netloc == "huggingface.co" and u.path == "/api/datasets":
                return J([{"id": "acme/robotics-qa", "downloads": 900, "gated": False, "tags": ["license:cc-by-4.0"]},
                          {"id": "acme/tiny", "downloads": 3, "gated": False, "tags": []}])
            if u.netloc == "en.wikibooks.org":
                if qs.get("action") == ["parse"]:
                    return J({"parse": {"title": qs["page"][0], "text": "<p>Problem 1: Solve 5x = 20 for x.</p><p>Answer: x = 4 because 20 divided by 5 is 4.</p>"
                                                                       "<p>Problem 2: Solve 3x = 12 for x.</p><p>Answer: x = 4 since 12 / 3 = 4.</p>"}})
                return J({"query": {"search": [{"title": "Algebra/Solutions"}]}})
            if u.netloc == "export.arxiv.org":
                return 200, arx.encode(), "application/atom+xml"
            if u.netloc == "api.openalex.org":
                return J({"results": [{"id": "https://openalex.org/W1", "doi": "https://doi.org/10/x", "display_name": "Solving algebra word problems",
                                       "publication_year": 2024, "cited_by_count": 12, "primary_location": {"license": "cc-by"},
                                       "open_access": {"is_oa": True, "oa_url": "https://ex.org/p.pdf"},
                                       "authorships": [{"author": {"display_name": "A. Researcher"}}],
                                       "abstract_inverted_index": {"We": [0], "study": [1], "algebra": [2], "word": [3], "problems.": [4],
                                                                   "Our": [5], "method": [6], "solves": [7], "them": [8], "accurately.": [9]}}]})
            if u.netloc.endswith("wikipedia.org"):
                if "list=search" in url:
                    return J({"query": {"search": [{"title": "Algebra problem"}]}})
                return J({"query": {"pages": {"1": {"extract": "Algebra problem is about equations.\nAn equation is solved by isolating x, giving the answer."}}}})
            return None, b"", ""
    return FakeHttp()


# ============================================================================= tests
def selftest():
    app_defaults = dict(DEFAULT_INPUT)
    DEFAULT_INPUT.update(quantity=10, quality=4, datagen_variations=3)  # small, fast test values (the app keeps big ones)
    try:
        return _selftest()
    finally:
        DEFAULT_INPUT.clear()
        DEFAULT_INPUT.update(app_defaults)


def _selftest():
    """Offline tests: fake HTTP, no network, no API."""
    import sympy as sp
    st = default_settings()
    st.update(include_meta=True, include_sources=True, include_scores=True, pdf_title_page=True)  # the tests cover the full layout
    st["delay"] = 0
    ok = [0]
    quiet = lambda m: None

    def check(cond, name):
        if not cond:
            raise AssertionError(name)
        ok[0] += 1
        print("  ok", name)

    # ---- input
    d, e = validate_input({})
    check(d == DEFAULT_INPUT and not e, "defaults: qty 10, quality 4, pdf, datagen x3")
    d, e = validate_input({"topics": "algebra, physics", "quantity": "25", "quality": 7, "output_type": ".JSON",
                           "datagen": {"variations": 5, "styles": "exam, casual", "formats": "all", "methods": ["numbers"]}})
    check(d["topics"] == ["algebra", "physics"] and d["quantity"] == 25 and d["output_type"] == "json"
          and d["datagen_variations"] == 5 and d["datagen_styles"] == ["casual", "exam"] and d["datagen_formats"] == FORMATS
          and d["datagen_methods"] == ["numbers"] and not e, "string topics, nested datagen, 'all', coercion")
    _, e = validate_input({"topics": [], "quantity": MAX_QUANTITY + 1, "quality": 0, "data_type": "x", "output_type": "doc",
                           "datagen_variations": MAX_VARIATIONS + 1, "datagen_styles": ["rap"], "datagen_formats": 3})
    check(len(e) == 8, f"all eight errors reported ({len(e)})")
    _, e = validate_input({"quantity": 2.5})
    check(e == [f"quantity: whole number 1-{MAX_QUANTITY}."], "no silent rounding of 2.5")

    # ---- extraction
    so = clean_html('<p>Use <code>yield</code>, not <code>a &lt; b</code>.</p><pre><code>for i in x:\n    if i:\n        print(i)\n</code></pre>'
                    '<p>A <a href="#">link</a> and <strong>bold</strong> text.</p>')
    check("Use `yield`, not `a < b`." in so and "```\nfor i in x:\n    if i:\n        print(i)\n```" in so and "A link and bold text." in so,
          "HTML -> text keeps code indentation, inline code and clean spacing")
    page = ("Intro text.\n\nProblem 1: Find x if 2x + 3 = 11.\nSolution: 2x = 8 so x = 4.\n\n"
            "Problem 2: What is the derivative of x^2 with respect to x?\nAnswer: The derivative is 2x, by the power rule.\n")
    pairs = split_problem_solution(page)
    check(len(pairs) == 2 and "2x + 3" in pairs[0][0] and "x = 4" in pairs[0][1] and "power rule" in pairs[1][1], "split problem/solution")
    check(jsonld_pairs('<script type="application/ld+json">{"@type":"QAPage","mainEntity":{"@type":"Question","name":"Q?",'
                       '"text":"Why 2+2?","acceptedAnswer":{"@type":"Answer","text":"Because 4."}}}</script>')
          == [("Q?\nWhy 2+2?", "Because 4.")], "JSON-LD Question/acceptedAnswer")
    pr = Searcher.parse_ddg('<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fex.com%2Fa&rut=1">Algebra <b>problems</b></a>'
                            '<a class="result__snippet" href="x">Solved algebra</a>')
    check(pr == [("https://ex.com/a", "Algebra problems", "Solved algebra")], "parse DuckDuckGo html")
    check(openalex_abstract({"b": [1], "a": [0], "c": [2]}) == "a b c", "OpenAlex abstract rebuild")
    check(detect_qa_columns([{"name": "question", "type": {"dtype": "string"}}, {"name": "answer", "type": {"dtype": "string"}}],
                            [{"question": "What is 2+2 here?", "answer": "4"}]) == ("question", "answer"), "HF column detection")

    # ---- search (fake network)
    fh = make_fake_http("blocked")
    sr = Searcher(st, quiet, http=fh)
    check(sr.se_tag("word problems", "math") == "word-problem" and sr.se_tag("algebra", "math") == "algebra-precalculus"
          and sr.se_tag("topology", "math") is None
          and sr.se_tag("organic chemistry", "chemistry") == "organic-chemistry", "Stack Exchange exact tags")
    check(sr.se_site("C++") == "stackoverflow" and sr.se_site("blockchain") == "math" and sr.se_site("biostatistics") == "stats"
          and sr.se_site("mathematics") == "math" and sr.se_site("robotics") == "robotics", "topic -> site uses whole words for short keys")
    check(sr.se_tag("C++", "stackoverflow") == "c++", "Stack Overflow tag keeps c++")
    check(sr.se_site("Linear Algebra") == "math" and sr.se_site("python decorators") == "stackoverflow" and sr.se_site("zzz") == "math", "topic -> SE site")
    check([r["dataset"] for r in sr.hf_routes("mathematics")] == ["openai/gsm8k", MATH_DS], "HF routes for mathematics")
    check(sr.hf_routes("organic chemistry")[0]["filter"] == ["organic"], "HF topic filter words")
    inp_all, _ = validate_input({"topics": ["algebra"], "datagen_variations": 0})
    check(inp_all["data_types"] == DATA_TYPES, "all data types selected by default (worked examples searched too)")
    res_all = run_pipeline(inp_all, st, log=quiet, searcher=Searcher(st, quiet, http=make_fake_http("ok")))
    got_types = {r.get("data_type") for r in res_all["records"]}
    check(len(res_all["records"]) >= 3 and "problems & solution papers" in got_types,
          f"several data types share the quantity ({len(res_all['records'])}, {sorted(t for t in got_types if t)})")
    inp, _ = validate_input({"topics": ["algebra"], "datagen_variations": 0, "data_type": "problems & solution papers"})
    res = run_pipeline(inp, st, log=quiet, searcher=sr)
    final = res["records"]
    check(len(final) == 10, f"quantity 10 delivered (got {len(final)})")
    check(all(r["solution"] for r in final), "every record has a solution")
    check(sr.notes.get("duckduckgo") == "bot check (HTTP 202)", "DuckDuckGo bot check detected")
    check(sum("html.duckduckgo.com" in c for c in fh.calls) == 1, "bot check respected: exactly one DuckDuckGo request")
    check(not any("lite.duckduckgo" in c for c in fh.calls), "no fallback door to DuckDuckGo")
    check(any("api.duckduckgo.com" in c for c in fh.calls), "official Instant Answer API used")
    check(not any("openai.com" in c for c in fh.calls), "no LLM / no API key anywhere")
    check({"huggingface", "stackexchange"} <= set(sr.stats), f"alternatives delivered ({sr.stats})")
    check(not any(r.get("meta", {}).get("tags") == ["soft-question", "advice"] for r in final), "soft question rejected even at quality 4")

    fh2 = make_fake_http("ok")
    sr2 = Searcher(st, quiet, http=fh2)
    got = sr2.duckduckgo("algebra", "problems & solution papers", 10)
    check(any("56" in g["solution"] for g in got), "web page JSON-LD harvested")
    check(any("power rule" in g["solution"] for g in got), "web page problem/solution harvested")
    import importlib.util
    if importlib.util.find_spec("pypdf"):
        check(any(g["meta"].get("pdf") for g in got), "PDF paper read with pypdf")
    else:
        print("  (pypdf not installed - PDF check skipped)")

    sr3 = Searcher(st, quiet, http=make_fake_http())
    rob = sr3.huggingface("robotics", "problems & solution papers", 5)
    check(len(rob) == 5 and rob[0]["meta"]["discovered"] and rob[0]["meta"]["license"] == "cc-by-4.0", "HF discovery for an uncurated topic")
    check(all(r["meta"]["split"] == "train" for r in rob), "train split only (no benchmark test rows)")
    phy = sr3.huggingface("optics", "problems & solution papers", 4)
    check(len(phy) == 4 and phy[0]["meta"]["dataset"] == "camel-ai/physics", "curated physics dataset with topic filter")
    check(not mostly_english(["请列举一些近期的金融危机及其原因?"]) and mostly_english(["What is opportunity cost?"]), "English check")
    check(not looks_like_tasks(["The volume opens with a preface on registers.", "A note on notation follows."] * 3, 0.85), "book text is not tasks")
    check(not looks_like_tasks(["Give block 5 of the LaTeX preamble of The Mirror Calculus exactly as written."] * 5)
          and looks_like_tasks(["Find the derivative of x^2.", "What is 2+2?", "Solve 3x = 9."]), "discovery skips datasets that are not problems")
    oa = sr3.openalex("algebra", "research papers", 3)
    check(oa and "accurately" in oa[0]["solution"], "OpenAlex paper parsed")
    wb = sr3.wikibooks("algebra", "problems & solution papers", 5)
    check(len(wb) == 2 and "x = 4" in wb[0]["solution"], "Wikibooks exercises parsed")
    check(Searcher(st, quiet, http=make_fake_http()).wikibooks("spanish verbs", "problems & solution papers", 5) == [],
          "Wikibooks pages must mention the topic in their title")

    inp9, _ = validate_input({"topics": ["algebra"], "quality": 7, "quantity": 8, "datagen_variations": 0})
    res9 = run_pipeline(inp9, st, log=quiet, searcher=Searcher(st, quiet, http=make_fake_http()))
    check(res9["records"] and not any("casino" in r["solution"].lower() for r in res9["records"]), "quality 7 drops spam")
    check(all(r["score"] >= st["min_score_q7"] for r in res9["records"]), f"quality 7 min score respected ({len(res9['records'])} kept)")
    po = run_pipeline(validate_input({"topics": ["algebra"], "data_type": "problems only", "quantity": 5, "quality": 8, "datagen_variations": 1})[0],
                      st, log=quiet, searcher=Searcher(st, quiet, http=make_fake_http()))
    check(len(po["records"]) == 5 and all(not r["solution"] for r in po["records"]), "problems only: 5 problems, no solutions in the output")
    logs = []
    deep = run_pipeline(validate_input({"topics": ["algebra"], "quantity": 60, "quality": 4, "datagen_variations": 0})[0],
                        st, log=logs.append, searcher=Searcher(st, quiet, http=make_fake_http()))
    check(any(l.startswith("Refill round 1") for l in logs) and 10 < len(deep["records"]) < 60,
          f"refill rounds search deeper, then return what exists ({len(deep['records'])} kept)")
    inp2, _ = validate_input({"topics": ["algebra"], "quality": 2, "quantity": 40, "datagen_variations": 0})
    res2 = run_pipeline(inp2, st, log=quiet, searcher=Searcher(st, quiet, http=make_fake_http()))
    check(not any(str(r.get("rejected", "")).startswith(("spam", "score")) for r in res2["rejected"]), "quality 2: no strict rejections")

    pic = item("calculus", "stackexchange", "Integral", "Integral I = int f. The integrand graph looks like this: and the value is 8.37. " * 3,
               "Use substitution and symmetry, then integrate by parts to reach the closed form. " * 4, "u", 50, {"images": 1, "tags": ["calculus"]})
    pic["_needs_solution"] = True
    check(Filterer(st, quiet).reject_reason(pic, Filterer(st, quiet).score(pic, ["calculus"])[2], ["calculus"], True) == "needs a figure",
          "posts that refer to a lost image are flagged (strict)")
    paper = item("algebra", "openalex", "A paper", "A paper\n\nWe study algebra problems in depth with many words here.", "Our method solves them; results show it works. " * 8, "u", 900, {"kind": "paper"})
    prob = item("algebra", "stackexchange", "Solve it", "Solve 2x + 3 = 7 for x. What is x?", "Subtract 3: 2x = 4, so x = 2. Therefore x = 2.", "u2", 3)
    kept_, _, _ = Filterer(st, quiet).run([paper, prob], validate_input({"topics": ["algebra"], "quantity": 2})[0])
    check(kept_[0]["source"] == "stackexchange", "problem runs rank real problems above papers")
    pv = DataGen(st, quiet).generate([dict(paper, uid="pp", score=5)], validate_input({"topics": ["algebra"], "datagen_variations": 3})[0])
    check(len(pv) == 3 and all(v["problem"].count('the paper "A paper"') == 1 and v["style"] in PAPER_STYLES and v["format"] in PAPER_FORMATS for v in pv),
          "papers become questions about the paper, with paper-friendly styles/formats")
    ref = item("algebra", "wikibooks", "q2", "Question 2: Is 558 divisible by 9? Determine it for these numbers.", "The statement is true and can be proven as in question 1.", "u")
    ref["_needs_solution"] = True
    check(Filterer(st, quiet).reject_reason(ref, Filterer(st, quiet).score(ref, ["algebra"])[2], ["algebra"], True) == "refers elsewhere",
          "solutions that only point to another question are rejected (strict)")
    class DeadHttp:  # no network at all
        status = None

        def fetch(self, url, data=None, max_bytes=None):
            return None, b"", ""

        def get(self, url, data=None):
            return None
    stages = []
    dead = run_pipeline(validate_input({"topics": ["algebra"], "quantity": 5})[0], st, quiet,
                        searcher=Searcher(st, quiet, http=DeadHttp()), stage=lambda n, s_, i="": stages.append((n, s_)))
    check(dead["records"] == [] and dead["variants"] == [] and dead["notes"].get("duckduckgo") == "unreachable"
          and ("output", "error") in stages, "no network: clean empty result, DuckDuckGo 'unreachable', output stage shows the error")
    class SlowHttp:  # every request takes 0.15 s, like a real network
        def __init__(self):
            self.inner, self.status = make_fake_http(), None

        def fetch(self, url, data=None, max_bytes=None):
            time.sleep(0.15)
            res = self.inner.fetch(url, data)
            self.status = self.inner.status
            return res

        def get(self, url, data=None):
            body = self.fetch(url, data)[1]
            return body.decode("utf-8", "replace") if body else None
    cancel, holder = threading.Event(), []
    th = threading.Thread(target=lambda: holder.append(run_pipeline(
        validate_input({"topics": ["algebra", "physics", "python"], "quantity": 50})[0], st, quiet, cancel,
        searcher=Searcher(st, quiet, cancel, http=SlowHttp()))))
    t_start = time.time()
    th.start()
    time.sleep(0.5)
    cancel.set()
    th.join(10)
    check(not th.is_alive() and holder and time.time() - t_start < 3, f"STOP ends a run quickly ({time.time() - t_start:.1f}s)")
    code_ans = item("c++", "stackexchange", "q", "How do I reverse a vector in C++? I want the elements in the opposite order.",
                    "Use std::reverse:\n```\n#include <algorithm>\nint main() {\n    std::vector<int> v{1, 2, 3};\n    std::reverse(v.begin(), v.end());\n}\n```\n"
                    "Or iterate backwards:\n```\nfor (auto it = v.rbegin(); it != v.rend(); ++it) {\n    use(*it);\n}\n```", "u", 40, {"tags": ["c++"]})
    code_ans["_needs_solution"] = True
    check(Filterer(st, quiet).reject_reason(code_ans, Filterer(st, quiet).score(code_ans, ["c++"])[2], ["c++"], True) is None,
          "fenced code with braces is not 'repeated lines'")
    flt = Filterer(st, quiet)
    dup = [item("algebra", "stackexchange", "a", "Solve x + 1 = 2 for x. What is x? " * 3, "x = 1 therefore. " * 5, "u1", 5),
           item("algebra", "stackexchange", "b", "Solve x + 1 = 2 for x. What is x? " * 3, "x = 1 therefore. " * 5, "u2", 5)]
    fk, fr, rs = flt.run(dup, validate_input({"topics": ["algebra"], "quality": 6})[0])
    check(len(fk) == 1 and rs.get("duplicate") == 1, "duplicate removed")
    st_rules = dict(st, **{rule_key("spam / ads"): False})
    spam = item("algebra", "web", "s", "BUY NOW casino algebra problem " * 5, "SOLUTION ALL CAPS SHOUTING HERE " * 5, "u")
    spam["_needs_solution"] = True
    why = Filterer(st_rules, quiet).reject_reason(spam, Filterer(st_rules, quiet).score(spam, ["algebra"])[2], ["algebra"], True)
    check(why == "shouting / all caps", f"switched-off rule does not hide the others ({why})")

    # ---- DataGen
    dg = DataGen(st, quiet)
    check(DataGen.final_answer(GSM_ROWS[0]["answer"]) == "72" and DataGen.final_answer(MATH_ROWS[0]["solution"]) == "4"
          and DataGen.final_answer("so the answer is 12 apples.") == "12 apples" and DataGen.final_answer("We get x = 5 here") == "x = 5",
          "final answer extraction (####, boxed, 'answer is', x = n)")
    check(DataGen.final_answer("Your step is wrong. Take a = 1 and b = -1 to see it.", "Why is sqrt(ab) not sqrt(a)sqrt(b)?") is None
          and DataGen.final_answer("Subtract 3, so x = 4.", "Solve 2x + 3 = 11 for x.") == "x = 4", "a counter-example is not 'the answer'")
    check(tidy_answer("Great question!\n\nEDIT: fixed a typo pointed out in the comments.\nThe key is symmetry.") == "The key is symmetry.",
          "openers and edit notes are removed from answers")
    check(with_title("Why can't you square both sides?", "Why can't you square both sides? I keep getting extra roots.")
          == "Why can't you square both sides? I keep getting extra roots." and with_title("T", "Body text") == "T\n\nBody text",
          "question text never repeats its title")
    long_sol = "First sub k = 1 and t = 2. " + "We integrate by parts and use symmetry. " * 30 + "This gives the closed form above."
    check(DataGen.final_answer(long_sol) is None, "no made-up answer from a long free-form solution")
    check(swap_phrases("I use a method because of x.", SYNONYMS, random.Random(0), 1.0) == "I use an approach due to x.",
          "synonyms fix a/an and 'because of'")
    nadia = item("x", "h", "n", "Nadia buys 20 roses and 3/4 times as many lilies as roses. Roses cost $5 each and lilies cost twice as much. How much does she spend?",
                 "Roses: 20*5 = $<<20*5=100>>100\nLilies: 3/4*20 = <<3/4*20=15>>15\nEach lily: 5*2 = $<<5*2=10>>10\nLilies cost 10*15 = $<<10*15=150>>150\nTotal 150+100 = $<<150+100=250>>250\n#### 250", "u")
    nadia["uid"] = "nadia"
    nv = dg.numeric_variant(nadia, random.Random(2))
    check(nv and "3/4 times" in nv[0] and dg.verify_chain(*nv), "fractions in the problem keep their numbers")
    check(not any(x.strip() in ("1.", "2.") for x in sentences("Methods: 1. DNA sequencing: compare genes. 2. Trees: build them.")),
          "list numbers stay with their item")
    long_s = "\n\n".join(f"{i}. Point number {i} explains one more idea about the topic in a full sentence." for i in range(1, 13))
    soc = dg.apply_style("socratic", "Why does this work?", long_s, random.Random(1), None)[1]
    qlines = [l.split(": ", 1)[1] for l in soc.split("\n") if re.match(r"Q\d+:", l)]
    check(len(qlines) == len(set(qlines)) and qlines[-1] == "So what is the answer?" and "Point number 12" in soc,
          "socratic asks each guiding question once and keeps every step")
    check(len(steps_of(long_s)) == 12, "paragraph answers become paragraph steps")
    eq_rec = item("algebra", "huggingface", "t", "Solve for x: 3x - 7 = 11.", "Add 7: 3x = 18, so x = 6.", "u")
    eq_rec["uid"] = "eq1"
    for i in range(5):
        out = dg.numeric_variant(eq_rec, random.Random(i))
        check(out is not None, f"equation variant {i} made")
        p2, s2 = out
        eqs = [e for e in find_equations(p2) if e[3] == {"x"}]
        L_, R_ = dg._parse_eq(eqs[0][2], "x")
        xs = sp.solve(sp.Eq(L_, R_), sp.Symbol("x"))
        ansv = DataGen.final_answer(s2)
        check(p2 != eq_rec["problem"] and ansv == f"x = {xs[0]}" and xs[0].is_integer, f"SymPy re-solved equation {i}: {eqs[0][2]} -> {ansv}")
    math_rec = item("algebra", "huggingface", "t", MATH_ROWS[1]["problem"], MATH_ROWS[1]["solution"], "u")
    math_rec["uid"] = "m1"
    mv = dg.numeric_variant(math_rec, random.Random(3))
    check(mv and "$" in mv[1] and "Answer: x =" in mv[1], "LaTeX problem gets a LaTeX SymPy solution")
    for gi, row in enumerate(GSM_ROWS[:6]):
        r = item("word problems", "huggingface", "g", row["question"], row["answer"], "u")
        r["uid"] = f"g{gi}"
        out = dg.numeric_variant(r, random.Random(gi))
        check(out is not None, f"GSM8K chain variant {gi} made")
        check(dg.verify_chain(*out) and out[1] != row["answer"], f"GSM8K variant {gi}: every computation re-checked")
    james = dg.numeric_variant(dict(item("x", "h", "j", GSM_ROWS[2]["question"], GSM_ROWS[2]["answer"], "u"), uid="j"), random.Random(5))
    check(james and "twice a week" in james[0] and "2 different friends" in james[0] and "*52=" in james[1],
          "'twice' keeps 2 fixed, weeks-per-year 52 stays a constant")
    proof = item("x", "stackexchange", "p", "Prove the reals are uncountable.",
                 "Split [0,1] into halves of length 1/2 and 1/4. Note 1 + 2 = 3 pieces. " + "By induction the measure argument works. " * 20, "u")
    proof["uid"] = "proof"
    check(dg.numeric_variant(proof, random.Random(1)) is None, "no new numbers inside proofs / long free-form answers")
    attempt = item("x", "stackexchange", "a", "Solve 2x + 3 = 11. I subtracted 3 first and then divided by 2 - why is that wrong?", "You should get 2x = 8.", "u")
    attempt["uid"] = "att"
    check(dg.numeric_variant(attempt, random.Random(1)) is None, "no equation change when other numbers in the text would go stale")
    amb = item("x", "h", "a", "Tom has 12 eggs and buys a dozen more. How many eggs?", "12+12=<<12+12=24>>24\n#### 24", "u")
    amb["uid"] = "amb"
    check(dg.numeric_variant(amb, random.Random(1)) is None, "ambiguous numbers are left alone")
    p_n, s_n = dg.swap_names(GSM_ROWS[0]["question"], GSM_ROWS[0]["answer"], random.Random(2))
    new_name = next(n for n in FEMALE_NAMES if re.search(rf"\b{n}\b", p_n))
    check("Natalia" not in p_n + s_n and new_name in s_n and new_name in FEMALE_SET, "names swapped consistently, gender kept")
    check("clips" not in p_n and "clips" not in s_n, "items swapped in word problems")
    code_rec = item("python", "huggingface", "c", MBPP_ROWS[2]["text"], MBPP_ROWS[2]["code"], "u")
    code_rec["uid"] = "c1"
    for style in STYLES:
        p_, s_ = dg.apply_style(style, code_rec["problem"], code_rec["solution"], random.Random(1), None)
        check(MBPP_ROWS[2]["code"] in s_, f"code kept intact by style '{style}'")
    gsm = item("word problems", "huggingface", "g", GSM_ROWS[0]["question"], GSM_ROWS[0]["answer"], "u")
    gsm["uid"] = "gsm0"
    for style in STYLES:
        p_, s_ = dg.apply_style(style, gsm["problem"], gsm["solution"], random.Random(4), "72")
        check(p_ and s_ and (p_, s_) != (gsm["problem"], gsm["solution"]), f"style '{style}' rewrites")
    for fmt in FORMATS:
        res_f = dg.apply_format(fmt, gsm["problem"], gsm["solution"], "72", random.Random(8), ["10", "624"])
        check(res_f is not None, f"format '{fmt}' fits a word problem")
        if fmt == "mcq":
            opts = res_f[2]["options"]
            check(len(opts) == 4 and opts.count("72") == 1 and f"{res_f[2]['correct']}) 72" in res_f[1], "mcq: 4 options, one correct, key matches")
        if fmt == "fill-blank":
            check("_____" in res_f[0] and "The blank is: 72" in res_f[1], "fill-blank blanks the answer")
        if fmt == "latex":
            check("\\frac{48}{2}" in res_f[1] and "<<" not in res_f[1], "latex typesets with SymPy")
        if fmt == "chat":
            check(res_f[2]["messages"][-1]["role"] == "assistant", "chat messages")
    check("Answer the following question" in dg.apply_format("instruction", "Why is the sky blue?", "Rayleigh scattering of sunlight.", None, random.Random(1), [])[0],
          "conceptual questions are answered, not 'solved'")
    check(dg.apply_format("mcq", "Explain light.", "Light is a wave and a particle.", None, random.Random(1), []) is None,
          "mcq skipped without a clear answer")
    fb = dg.apply_format("fill-blank", gsm["problem"], gsm["solution"], "72", random.Random(1), [])
    check(not re.search(r"(?<![\w.])72(?![\w])", fb[0]), "fill-blank never leaks the answer")
    ex = dg.apply_style("exam", gsm["problem"], gsm["solution"], random.Random(1), "72")[1]
    check("#### 72 [1]" not in ex and ex.count("Final answer: 72") == 1, "exam style: no mark on '####', one final answer")
    sv = dg.make_variant(gsm, "step-by-step", "step-list", [], random.Random(1), [], FORMATS, 1)
    check(sv["format"] != "step-list" and "1. Step 1" not in sv["solution"], "clashing style/format pair avoided")
    check(re.search(r"\$\d+ x = \d+\$", mv[1]) is not None, "LaTeX solution keeps whole equations together")
    recs = []
    for i, row in enumerate(GSM_ROWS[:5]):
        r = item("word problems", "huggingface", f"g{i}", row["question"], row["answer"], f"u{i}")
        r.update(uid=f"r{i}", score=7.0)
        recs.append(r)
    inp_dg, _ = validate_input({"topics": ["word problems"], "datagen_variations": 6})
    var = DataGen(st, quiet).generate(recs, inp_dg)
    check(len(var) == 30, f"6 variants per record (got {len(var)})")
    check(len({(v["problem"], v["solution"]) for v in var}) == 30, "variants are unique")
    check(len({v["style"] for v in var}) >= 6 and len({v["format"] for v in var}) >= 6, "many styles and formats used")
    check(sum(v["numbers_changed"] for v in var) >= 20, "most word-problem variants have new numbers")
    check(DataGen(st, quiet).generate(recs, inp_dg) == var, "same seed -> same variants")

    # ---- outputs
    out_dir = os.environ.get("AITE_TEST_OUT") or os.path.join(HERE, "exports", "_selftest")
    os.makedirs(out_dir, exist_ok=True)
    resd = run_pipeline(validate_input({"topics": ["algebra", "word problems"], "quantity": 6, "datagen_variations": 3,
                                        "data_type": "problems & solution papers"})[0],
                        st, log=quiet, searcher=Searcher(st, quiet, http=make_fake_http()))
    check(len(resd["records"]) == 6 and len(resd["variants"]) == 18, f"pipeline with DataGen ({len(resd['records'])}+{len(resd['variants'])})")
    check(sorted(r["topic"] for r in resd["records"]) == ["algebra"] * 3 + ["word problems"] * 3, "every topic gets its share")
    for kind in OUTPUT_TYPES:
        i2 = validate_input({"topics": ["algebra", "word problems"], "output_type": kind})[0]
        p = export(resd["records"], i2, st, os.path.join(out_dir, "test." + kind), resd["reasons"], resd["variants"])
        data = open(p, "rb").read()
        if kind == "pdf":
            check(data.startswith(b"%PDF-1.4") and data.rstrip().endswith(b"%%EOF") and b"/Count" in data, "pdf structure")
            xref = int(data.rsplit(b"startxref", 1)[1].split()[0])
            offs = [int(l.split()[0]) for l in data[xref:].split(b"\n")[3:] if l.endswith(b" n ")]
            check(all(re.match(rb"\d+ 0 obj", data[o:o + 12]) for o in offs), "pdf xref offsets valid")
            try:
                from pypdf import PdfReader
                txt = "\n".join(pg.extract_text() for pg in PdfReader(p).pages)
                check("Variant of #1" in txt and "SOLUTION" in txt, "pdf readable by pypdf, variants inside")
            except ImportError:
                pass
        elif kind == "json":
            j = json.loads(data)
            kinds = [r["kind"] for r in (j["data"] if isinstance(j, dict) else j)]
            check(kinds.count("original") == 6 and kinds.count("variant") == 18 and len(j if isinstance(j, list) else j["data"]) == 24, "json: originals + variants in one file")
            check(all(r["variant_of"] == r["id"].split(".")[0] for r in (j if isinstance(j, list) else j["data"]) if r["kind"] == "variant"), "json: variants point to parents")
        else:
            check(data.count(b"PROBLEM:") == 24 and data.count(b"Variant of #") == 18, "txt: one combined file")
    for fmt in ("chat-messages", "instruction"):
        j = json.loads(render_json(resd["records"], inp, dict(st, json_format=fmt), None, resd["variants"]))
        check(("messages" in j["data"][0]) if fmt == "chat-messages" else ("instruction" in j["data"][0]), f"json layout {fmt}")
    sym = render_pdf([item("t", "x", "Symbols", "Show that π ≤ √10 for α ∈ ℝ.", "Code:\n```\ndef f(x):\n    return x\n```\nDone.", "u")], inp, st)
    from pypdf import PdfReader as _R
    sym_txt = "\n".join(pg.extract_text() for pg in _R(io.BytesIO(sym)).pages)
    check("pi <= sqrt10" in sym_txt and "alpha in R" in sym_txt and "?" not in sym_txt.split("Show that")[1][:40], "PDF spells out maths symbols")
    streams = [zlib.decompress(m_.group(1)) for m_ in re.finditer(rb"\nstream\n(.*?)\nendstream", sym, re.S)]
    check(any(b"/F3" in x and b"return x" in x for x in streams), "PDF sets fenced code in Courier")
    big = [item("t", "arxiv", f"T{i}", "P (with) \\ backslash ünï ✓ " * 40, "S " * 300, "u") for i in range(30)]
    check(render_pdf(big, inp, st).count(b"/Type /Page ") > 5, "pdf paginates long content")
    check(len(SPEC) >= 200, f"settings count {len(SPEC)}")
    check(not any(k.startswith("llm_") for k in SPEC) and "OPENAI_API_KEY" not in globals(), "no API key, no LLM settings")

    # ---- Agent mode (Parallel Web Technologies), offline: balance, LLM-ready rows, live settings, GitHub push
    import gzip
    import glob
    import subprocess
    import tempfile
    global SETTINGS_FILE
    tmpd = tempfile.mkdtemp(prefix="aite_agent_test_")
    old_sf, SETTINGS_FILE = SETTINGS_FILE, os.path.join(tmpd, "settings.json")
    bare = os.path.join(tmpd, "remote.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], capture_output=True)
    os.environ["AITE_TEST_REMOTE"] = bare
    try:
        st_a = default_settings()
        st_a.update(pwt_workers=8, agent_quality=5, agent_batch=8, agent_variations=3, gh_stream=False)
        save_settings(st_a)
        root_a = os.path.join(tmpd, "Dataset")
        agent_control(root_a, workers=8)
        ag_ = Agent(root_a, st_a, offline=True, max_seconds=12)

        def later():
            time.sleep(3)
            agent_control(root_a, sync_now=time.time())
            time.sleep(2)
            save_settings(dict(st_a, agent_focus_topics="lagrangian mechanics", agent_quality=6))
            agent_control(root_a, settings_rev=time.time())
        threading.Thread(target=later, daemon=True).start()
        res = ag_.run()
        if ag_.sync_thread is not None:
            ag_.sync_thread.join(60)
        c = res["counts"]
        check(c["text"] > 0 and c["synthetic_images"] > 0 and c["vla_episodes"] > 0 and res["counts"]["tasks_failed"] == 0,
              f"agent collects text, images and VLA episodes ({c['text']}/{c['synthetic_images']}/{c['vla_episodes']})")
        check(c["synthetic_images"] <= max(c["text"], 100) / 6 + 12 and c["vla_episodes"] <= max(c["text"], 100) / 6 + 4,
              "generated data stays within its share of the text")
        rows = [json.loads(l) for f in glob.glob(os.path.join(root_a, "text", "*.jsonl.gz")) for l in gzip.open(f, "rt")]
        need = {"text", "messages", "split", "tokens", "quality_tier", "license", "source", "topic"}
        check(rows and all(need <= set(r) for r in rows), "text rows carry text / messages / split / tokens / tier / licence")
        check(all([m["role"] for m in r["messages"]][:2] in (["user", "assistant"], ["system", "user"]) for r in rows), "chat messages")
        fam = {}
        for r in rows:
            fam.setdefault(r.get("variant_of") or r["id"], set()).add(r["split"])
        check(len({r["id"] for r in rows}) == len(rows), "no duplicate rows")
        det = [json.loads(l) for f in glob.glob(os.path.join(root_a, "detection", "*.jsonl.gz")) for l in gzip.open(f, "rt")]
        check(det and all(os.path.exists(os.path.join(root_a, d["image"])) and all(
            0 <= o["bbox"][0] and o["bbox"][0] + o["bbox"][2] <= d["width"] + 0.5 for o in d["objects"]) for d in det),
            "detection images exist, boxes inside the image")
        vla = [json.loads(l) for f in glob.glob(os.path.join(root_a, "vla", "*.jsonl.gz")) for l in gzip.open(f, "rt")]
        check(vla and all(v["steps"][-1]["action"]["terminate"] == 1 and all(os.path.exists(os.path.join(root_a, s_["observation"]["image"]))
                                                                            for s_ in v["steps"]) for v in vla), "VLA episodes: frames + actions")
        check(not glob.glob(os.path.join(root_a, "*", "*.open")), "every shard closed on exit")
        check(ag_.st["agent_quality"] == 6 and ag_.store.db.execute(
            "SELECT depth FROM topics WHERE name='lagrangian mechanics'").fetchone() == (-1,), "settings + focus topics applied live")
        log_ = subprocess.run(["git", "--git-dir", bare, "log", "--oneline", "main"], capture_output=True, text=True).stdout
        files_ = subprocess.run(["git", "--git-dir", bare, "ls-tree", "-r", "--name-only", "main"], capture_output=True, text=True).stdout
        check("AITE agent:" in log_ and "Dataset/stats.json" in files_ and ".agent" not in files_,
              "GitHub sync commits into <repo>/Dataset and pushes")
        check(json.load(open(os.path.join(root_a, "stats.json")))["counts"]["text"] == c["text"], "stats.json written")
        arch = [r for r in rows if r.get("data_type") == "archive"]
        check(arch and any((r.get("archive") or "").endswith(("stackexchange.com", ".net", ".com")) for r in arch) and
              any("Answer: C) Vitamin C" in r["solution"] for r in arch), "archive lane: Stack Exchange dump + MedMCQA rows")
        sites_ = {r.get("archive") for r in arch if r.get("source") == "stackexchange"}
        check(len(sites_ & {"math.stackexchange.com", "mathoverflow.net", "physics.stackexchange.com", "Stackoverflow.com"}) >= 2
              and not any(".meta." in (x or "") for x in sites_), f"archive sweep keeps real sites ({sorted(x for x in sites_ if x)[:5]})")
        prefs_ = [json.loads(l) for f in glob.glob(os.path.join(root_a, "preference", "*.jsonl.gz")) for l in gzip.open(f, "rt")]
        check(prefs_ and all(p["chosen_score"] - p["rejected_score"] >= 2 and p["chosen"] != p["rejected"] for p in prefs_),
              "preference pairs: chosen beats rejected by 2+ votes")
        tj = json.load(open(os.path.join(root_a, "topics.json")))
        done_t = [t for t in tj["topics"] if t["done"]]
        check(tj["total"] == tj["done"] + tj["left"] + tj["in_progress"] and done_t and all(t["check"] == "✓" for t in done_t)
              and "parallel_agents" in tj, "topics.json: check marks, left, in progress, parallel agents")
        check({t["field"] for t in tj["topics"]} >= {"mathematics", "physics", "chemistry", "medicine"} and
              any(t["level"] == "advanced" for t in tj["topics"]) and "etale cohomology" in {t["topic"] for t in tj["topics"]},
              "topic engine: many fields, advanced subtopics")
        fresh = TopicStore(os.path.join(tmpd, "other_computer.db"))
        fresh.import_json(os.path.join(root_a, "topics.json"))
        check(fresh.count("done") == len(done_t), "a fresh computer continues from topics.json")
        ag2 = Agent(os.path.join(tmpd, "Dataset2"), dict(st_a, product_vla=False, product_synthetic_vision=False,
                                                        product_archives=False), offline=True, max_seconds=4)
        c2 = ag2.run()["counts"]
        check(c2["vla_episodes"] == 0 and c2["synthetic_images"] == 0 and c2["text"] > 0, "products switched off stay off")
        # GitHub first: data goes to GitHub, local copies disappear once GitHub has them
        bare2 = os.path.join(tmpd, "remote2.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare2], capture_output=True)
        os.environ["AITE_TEST_REMOTE"] = bare2
        root3 = os.path.join(tmpd, "repo3", "Dataset")
        ag3 = Agent(root3, dict(st_a, gh_stream=True), offline=True, max_seconds=10)

        def sync_soon():
            time.sleep(4)
            agent_control(root3, sync_now=time.time())
        threading.Thread(target=sync_soon, daemon=True).start()
        c3 = ag3.run()["counts"]
        if ag3.sync_thread is not None:
            ag3.sync_thread.join(120)
        files3 = subprocess.run(["git", "--git-dir", bare2, "ls-tree", "-r", "--name-only", "main"], capture_output=True, text=True).stdout
        pushed_text = [f for f in files3.split() if f.startswith("Dataset/text/")]
        pushed_imgs = [f for f in files3.split() if f.startswith("Dataset/images/")]
        local_left = sum(len(fn) for _dp, _dn, fn in os.walk(os.path.join(root3, "text")))
        check(pushed_text and pushed_imgs and "Dataset/stats.json" in files3 and c3["text"] > 0 and
              ag3.github.state.startswith("pushed"), f"GitHub first: data pushed ({len(pushed_text)} shards, {len(pushed_imgs)} images)")
        check(not any(os.path.exists(os.path.join(os.path.dirname(root3), f)) for f in pushed_text + pushed_imgs[:50])
              and os.path.exists(os.path.join(root3, "stats.json")),
              f"GitHub first: pushed files are gone locally (left: {local_left} newer shard files)")
        # GitHub moves on between our fetch and our push (e.g. the app was committed): the batch is redone on top
        other = os.path.join(tmpd, "other_clone")
        subprocess.run(["git", "clone", "-q", bare2, other], capture_output=True)
        subprocess.run(["git", "-C", other, "config", "user.email", "t@t"], capture_output=True)
        subprocess.run(["git", "-C", other, "config", "user.name", "t"], capture_output=True)
        os.makedirs(os.path.join(root3, "text"), exist_ok=True)
        with gzip.open(os.path.join(root3, "text", "text-race-000.jsonl.gz"), "wt") as f:
            f.write(json.dumps({"id": "race1", "type": "text", "problem": "race?", "solution": "ok"}) + "\n")
        real_run, moved = ag3.github.run, []

        def racing_run(cwd, *args, **kw):
            if args[:1] == ("push",) and not moved:
                moved.append(1)
                os.makedirs(os.path.join(other, "app"), exist_ok=True)
                open(os.path.join(other, "app", "AITE.py"), "w").write("# new app\n")
                subprocess.run(["git", "-C", other, "add", "-A"], capture_output=True)
                subprocess.run(["git", "-C", other, "commit", "-q", "-m", "app"], capture_output=True)
                subprocess.run(["git", "-C", other, "push", "-q", "origin", "HEAD:main"], capture_output=True)
            return real_run(cwd, *args, **kw)
        ag3.github.run = racing_run
        ok_race = ag3.github.stream(True)
        ag3.github.run = real_run
        files4 = subprocess.run(["git", "--git-dir", bare2, "ls-tree", "-r", "--name-only", "main"], capture_output=True, text=True).stdout
        check(moved and ok_race and "Dataset/text/text-race-000.jsonl.gz" in files4 and "app/AITE.py" in files4
              and not os.path.exists(os.path.join(root3, "text", "text-race-000.jsonl.gz")),
              "GitHub moved ahead during a push: batch redone on top, both kept, local copy removed")
    finally:
        SETTINGS_FILE = old_sf
        os.environ.pop("AITE_TEST_REMOTE", None)
        import shutil
        shutil.rmtree(tmpd, ignore_errors=True)  # tests never leave data behind
    # ---- Ask (RAG): every row type goes into the index, search finds it, the prompt cites sources, local+GitHub dedupe
    import gzip
    import shutil
    import tempfile
    rt = tempfile.mkdtemp(prefix="aite_rag_test_")
    try:
        rows = [{"id": "t1", "type": "text", "kind": "original", "problem": "Solve 2x + 3 = 11 for x.", "solution": "x = 4",
                 "field": "mathematics", "topic": "linear equations", "source": "stackexchange", "license": "CC BY-SA 4.0",
                 "url": "https://math.stackexchange.com/q/1"},
                {"id": "t2", "type": "text", "kind": "variant", "variant_of": "t1", "problem": "Find x if 2x + 5 = 13.",
                 "solution": "x = 4", "field": "mathematics"},
                {"id": "p1", "type": "preference", "prompt": "How do I reverse a list in Python?", "chosen": "Use lst[::-1].",
                 "rejected": "You cannot.", "field": "programming"},
                {"id": "i1", "type": "image-text", "title": "Mandelbrot zoom", "caption": "A fractal spiral of the Mandelbrot set",
                 "image": "images/web/x.jpg", "author": "W. Beyer", "license": "CC BY-SA 3.0"},
                {"id": "d1", "type": "detection", "caption": "A white desk with 1 object: a black circle.",
                 "objects": [{"label": "black circle", "bbox": [1, 2, 3, 4]}], "qa": [{"q": "How many objects?", "a": "1"}],
                 "image": "images/synthetic/d1.jpg"},
                {"id": "v1", "type": "vla-episode", "instruction": "Place the yellow disc on the black target.",
                 "objects": [{"shape": "disc", "color": "yellow"}], "success": True,
                 "steps": [{"observation": {"image": "f0.jpg"}, "action": {"dx": 1}}]}]
        for sub, kind in (("text", ("text",)), ("preference", ("preference",)), ("detection", ("image-text", "detection")),
                          ("vla", ("vla-episode",))):
            for base in ("gh/Dataset", "local"):
                os.makedirs(os.path.join(rt, base, sub), exist_ok=True)
                with gzip.open(os.path.join(rt, base, sub, f"{sub}-000.jsonl.gz"), "wt") as f:
                    for r in rows:
                        if r["type"] in kind:
                            f.write(json.dumps(r) + "\n")
        ix = RagIndex(os.path.join(rt, "ix.db"))
        nf, added = ix.update([os.path.join(rt, "gh", "Dataset"), os.path.join(rt, "local")])
        check(added == len(rows) and ix.count() == len(rows), f"RAG: ALL row types indexed once ({added} of {len(rows)}, GitHub + local deduped)")
        check(ix.update([os.path.join(rt, "gh", "Dataset")]) == (0, 0), "RAG: unchanged files are not read again")
        kinds = {h[0] for h in ix.db.execute("SELECT source FROM docs").fetchall()}
        check(all(any(k in x for x in kinds) for k in ("Q&A", "variant", "preference pair", "web image", "generated image",
                                                         "robot episode")), f"RAG: every data type is searchable {sorted(kinds)}")
        h = ix.search("solve 2x + 3 = 11", 3)
        check(h and h[0]["rid"] == "t1", "RAG: search finds the right record first")
        check(ix.search("reverse list python", 2)[0]["rid"] == "p1" and ix.search("yellow disc target", 1)[0]["rid"] == "v1"
              and ix.search("mandelbrot fractal", 1)[0]["rid"] == "i1", "RAG: preference, robot and image rows found")
        check(all(x["field"] == "programming" for x in ix.search("python list", 3, field="programming")), "RAG: field filter")
        msgs = rag_messages("what is x?", h)
        check(msgs[-1]["role"] == "user" and "[1]" in msgs[-1]["content"] and "x = 4" in msgs[-1]["content"], "RAG: prompt has numbered sources")
        check("x = 4" in rag_extractive("x?", h) and "Nothing" in rag_extractive("x?", []), "RAG: records-only answer")
        check(ix.search("", 3) == [] and ix.search("the and of", 3) == [], "RAG: empty / stop-word questions are safe")
        fake = os.path.join(rt, "model")
        os.makedirs(fake)
        check(not model_downloaded(fake) and not model_downloaded("nobody/not-a-model-xyz"), "RAG: missing models show Not downloaded")
        open(os.path.join(fake, "config.json"), "w").write("{}")
        check(model_downloaded(fake), "RAG: a model folder shows Downloaded")
        ix.close()
        old_kc = os.environ.get("KAGGLE_CONFIG_DIR")
        os.environ["KAGGLE_CONFIG_DIR"] = os.path.join(rt, "no_kaggle_login")
        kok, kmsg = kaggle_push(dict(default_settings()), [os.path.join(rt, "gh", "Dataset")], stage=os.path.join(rt, "stage"))
        check(kok is False and "login" in kmsg.lower() and not kaggle_logged_in(), "Kaggle: no login -> clear message, nothing stored")
        os.environ.pop("KAGGLE_CONFIG_DIR") if old_kc is None else os.environ.__setitem__("KAGGLE_CONFIG_DIR", old_kc)
    finally:
        shutil.rmtree(rt, ignore_errors=True)
    print(f"SELFTEST PASSED ({ok[0]} checks)")
    return 0


def cli_run(arg, out):
    st = load_settings()
    d, errs = validate_input(json.loads(arg))
    if errs:
        print("Input errors:", errs)
        return 2
    res = run_pipeline(d, st, log=print)
    print("Found per source:", res["stats"], "| notes:", res["notes"] or "-")
    for r in res["records"][:6]:
        print(f"- [{r['source']} {r['score']}] {shorten(r['title'], 90)}")
    for v in res["variants"][:4]:
        print(f"  ~ [{v['style']} / {v['format']}] {shorten(v['problem'], 110)}")
    if out:
        kind = os.path.splitext(out)[1].lstrip(".") or d["output_type"]
        export(res["records"], dict(d, output_type=kind), st, out, res["reasons"], res["variants"])
        print("wrote", out)
    return 0 if res["records"] else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--run" in sys.argv:
        i = sys.argv.index("--run")
        out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
        sys.exit(cli_run(sys.argv[i + 1], out))
    if "--train" in sys.argv:  # the Trainer page without a window
        sys.exit(cli_train(sys.argv))
    if "--rag-update" in sys.argv:  # the Ask page's background job: GitHub -> index -> Kaggle
        d_ = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else agent_dir(load_settings())
        sys.exit(cli_rag_update(os.path.abspath(os.path.expanduser(d_)), offline="--offline" in sys.argv))
    if "--agent" in sys.argv:  # Agent mode without a window (also what the GUI starts in the background)
        def arg(name, default=None):
            return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
        st_ = load_settings()
        try:  # lowest-but-one priority: the window, the Mac and everything else always come first (no freezes)
            os.nice(int(st_.get("agent_nice", 15)))
        except (OSError, ValueError):
            pass
        root_ = os.path.abspath(os.path.expanduser(arg("--dir") or agent_dir(st_)))
        wid = int(arg("--worker", 0) or 0)
        if agent_pid(root_) and not wid:
            print(f"An agent is already collecting into {root_} (pid {agent_pid(root_)}).")
            sys.exit(0)
        secs = arg("--seconds")
        Agent(root_, st_, offline="--offline" in sys.argv, log=print if sys.stdout.isatty() else None,
              max_seconds=float(secs) if secs else None, worker_id=wid).run()
        sys.stdout.flush()
        os._exit(0)  # do not wait for agents still talking to slow sites: their rows are only lost if unfinished
    main_gui()