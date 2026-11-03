"""One function, ask(), that sends a prompt to either Claude or Gemini.

Which provider is used depends on the model name ("claude-..." or "gemini-...").
If you don't name a model, it picks based on which API key you've set:
  ANTHROPIC_API_KEY -> Claude (paid)
  GEMINI_API_KEY    -> Gemini (free tier from aistudio.google.com)

Keys can be set as environment variables or put in a file called .env in the
project folder (one per line, e.g. GEMINI_API_KEY=...). .env is git-ignored.
"""
import os
import re
import time
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_DEFAULT = "claude-sonnet-5-5"
CLAUDE_JUDGE = "claude-opus-5-5"


class QuotaExhausted(RuntimeError):
    """Gemini's free daily limit is used up. Finished work is cached; re-run tomorrow."""


def _load_dotenv():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip().strip('"').strip("'")
                # .env wins over the system environment for API keys: CLAUDE.md says keys live in
                # .env only, and a stale Windows-level ANTHROPIC_API_KEY once shadowed the real one.
                if key.endswith("_API_KEY"):
                    os.environ[key] = value
                else:
                    os.environ.setdefault(key, value)


_load_dotenv()


def has_claude() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def has_gemini() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


# ---------- choosing models ----------

@lru_cache
def gemini_models() -> list[str]:
    """Text models this API key can use, newest first."""
    names = []
    for m in _gemini().models.list():
        name = m.name.removeprefix("models/")
        actions = getattr(m, "supported_actions", None) or []
        if "generateContent" not in actions or not name.startswith("gemini"):
            continue
        if re.search(r"image|tts|audio|live|embed|vision|robotics|computer|banana|transcribe", name):
            continue
        names.append(name)

    def version(n):
        match = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return float(match.group(1)) if match else 0.0

    return sorted(set(names), key=version, reverse=True)


def _responds(model: str) -> bool:
    """Quick ping: free-tier models are sometimes overloaded (503) or not free (429)."""
    from google.genai import types

    try:
        _gemini().models.generate_content(
            model=model, contents="Reply with: OK",
            config=types.GenerateContentConfig(http_options=types.HttpOptions(timeout=30_000)))
        return True
    except Exception:
        return False


@lru_cache
def _pick_gemini(lite: bool) -> str:
    """Newest stable Flash (or Flash-Lite) model that actually responds right now.
    The choice is saved for the day in .gemini_models.json, because each test ping uses
    one of the free tier's ~20 daily requests."""
    import datetime, json

    cache, kind, today = ROOT / ".gemini_models.json", ("lite" if lite else "flash"), str(datetime.date.today())
    saved = json.loads(cache.read_text()) if cache.exists() else {}
    if saved.get("date") == today and saved.get(kind):
        return saved[kind]
    models = gemini_models()
    candidates = [
        n for n in models
        if "flash" in n and ("lite" in n) == lite and not re.search(r"preview|exp|latest|omni", n)
    ]
    for name in candidates:
        if _responds(name):
            saved = saved if saved.get("date") == today else {"date": today}
            saved[kind] = name
            cache.write_text(json.dumps(saved))
            return name
    raise SystemExit(f"No free Gemini {'Flash-Lite' if lite else 'Flash'} model is responding "
                     "right now. Try again in a few minutes, or set LLM_MODEL=<model name>.")


def default_model() -> str:
    """Model that writes the answers."""
    if os.getenv("LLM_MODEL"):
        return os.environ["LLM_MODEL"]
    if has_claude():
        return CLAUDE_DEFAULT
    if has_gemini():
        return _pick_gemini(lite=False)
    raise SystemExit(
        "No API key found. Put GEMINI_API_KEY=... (free, from aistudio.google.com) "
        "or ANTHROPIC_API_KEY=... in a .env file in the project folder."
    )


def default_judge() -> str:
    """Model that grades answers. A different model from the answerer, to limit self-preference."""
    if os.getenv("JUDGE_MODEL"):
        return os.environ["JUDGE_MODEL"]
    if has_claude():
        return CLAUDE_JUDGE
    return _pick_gemini(lite=True)  # also spreads the free daily quota across two models


# ---------- calling models ----------

def ask(system: str, user: str, model: str, **kw) -> str:
    """kw (Claude only): phase= label for the cost log; cache_system=True to prompt-cache the
    system prompt; effort= "low"|"medium"|"high"; max_tokens=."""
    if model.startswith("gemini"):
        return _ask_gemini(system, user, model)
    return _ask_claude(system, user, model, **kw)


@lru_cache
def _anthropic():
    from anthropic import Anthropic

    return Anthropic(max_retries=4)


def claude_create(phase="", **params):
    """messages.create with the budget guard: refuses past the hard stop, logs every call's cost."""
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src import costs

    costs.check()
    msg = _anthropic().messages.create(**params)
    costs.log(params["model"], msg.usage, phase)
    return msg


def text_of(msg) -> str:
    # With thinking on (default on current models), content can start with a thinking block,
    # so join the text blocks instead of reading content[0].
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def _ask_claude(system, user, model, phase="", cache_system=False, effort=None, max_tokens=4000):
    sys_param = ([{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
                 if cache_system else system)
    params = dict(model=model, max_tokens=max_tokens, messages=[{"role": "user", "content": user}])
    if system:  # empty system = no system prompt at all (e.g. Wang 2025's "native" condition)
        params["system"] = sys_param
    if effort:
        params["output_config"] = {"effort": effort}
    msg = claude_create(phase=phase, **params)
    if msg.stop_reason == "refusal":
        return "[REFUSED BY MODEL]"
    return text_of(msg)


@lru_cache
def _gemini():
    from google import genai

    return genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


_last_call = [0.0]


def _ask_gemini(system, user, model, max_retries=6):
    from google.genai import errors, types

    # Free tier allows only a few requests per minute, so space calls out.
    gap = 60.0 / float(os.getenv("GEMINI_RPM", "8"))
    for attempt in range(max_retries):
        wait = _last_call[0] + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.time()
        try:
            resp = _gemini().models.generate_content(
                model=model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system, temperature=0,
                    http_options=types.HttpOptions(timeout=120_000)),
            )
            return resp.text or ""
        except errors.APIError as e:
            if e.code in (500, 503, 504):  # Google-side overload; usually clears in seconds
                print(f"  (Gemini busy [{e.code}], retrying in {10 * (attempt + 1)}s)")
                time.sleep(10 * (attempt + 1))
                continue
            if e.code != 429:
                raise
            text = str(e)
            if re.search(r"PerDay|per day|daily", text, re.I):
                raise QuotaExhausted(f"Daily free quota used up for {model}.") from e
            delay = re.search(r"retry(?:Delay)?['\"]?\s*[:=]?\s*['\"]?(\d+(?:\.\d+)?)s", text, re.I)
            sleep_for = float(delay.group(1)) + 1 if delay else 15 * (attempt + 1)
            print(f"  (Gemini rate limit, waiting {sleep_for:.0f}s)")
            time.sleep(sleep_for)
    raise QuotaExhausted(f"Gemini kept failing for {model} (rate limit or overload); try again later.")


if __name__ == "__main__":
    # `python src/llm.py` shows which models will be used.
    if has_gemini():
        print("Gemini models available to your key:\n  " + "\n  ".join(gemini_models()))
    print(f"\nAnswer model: {default_model()}\nJudge model:  {default_judge()}")
    print("\nTest call:", ask("Reply with exactly: OK", "Say OK.", default_model()))
