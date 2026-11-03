"""Budget guard for Claude API calls.

Every Claude call logs its token usage to results/api_usage.csv and adds its cost to a
running total. Before each call we check the total; past the hard stop we raise
BudgetExceeded so nothing else gets spent.

Prices: US$ per million tokens, Claude API first-party rates as listed in Anthropic's
model table (cached 2026-10-06). Cache writes (5-minute TTL) cost 1.25x input; cache reads
are listed separately. Batch API requests cost 50% of these rates.
Thinking tokens are billed as output tokens and are included in usage.output_tokens.
"""
import csv
import datetime
import contextlib
import os
import threading
import time
from pathlib import Path

_LOCK = threading.Lock()


@contextlib.contextmanager
def _file_lock():
    """Lock shared by threads AND separate processes (two scripts can run at once and share the log).
    Uses an exclusive lock file: create-or-wait."""
    lock = LOG.with_suffix(".lock")
    with _LOCK:
        for _ in range(2000):
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                with contextlib.suppress(FileNotFoundError):  # the holder may release it between our checks
                    if time.time() - lock.stat().st_mtime > 30:  # stale lock from a killed process
                        lock.unlink()
                time.sleep(0.01)
        else:
            raise TimeoutError("could not lock the cost log")
        try:
            yield
        finally:
            os.close(fd)
            with contextlib.suppress(FileNotFoundError):
                lock.unlink()

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "results" / "api_usage.csv"
HARD_STOP_USD = 32.00

PRICES = {  # model: (input, output, cache_read) per 1M tokens
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),  # cache read not listed; assumed 0.1x input
}
CACHE_WRITE_MULT = 1.25
BATCH_MULT = 0.50
FIELDS = ["time", "phase", "model", "input", "output", "cache_write", "cache_read", "batch", "usd"]


class BudgetExceeded(RuntimeError):
    """Total API spend has passed the hard stop."""


def price(model, input_tokens, output_tokens, cache_write=0, cache_read=0, batch=False) -> float:
    p_in, p_out, p_cr = PRICES[model]
    usd = (input_tokens * p_in + output_tokens * p_out
           + cache_write * p_in * CACHE_WRITE_MULT + cache_read * p_cr) / 1e6
    return usd * (BATCH_MULT if batch else 1.0)


def spent() -> float:
    if not LOG.exists():
        return 0.0
    total = 0.0
    with _file_lock(), LOG.open(newline="") as f:
        for r in csv.DictReader(f):
            try:
                total += float(r["usd"])
            except (TypeError, ValueError):  # a malformed line; never let it crash a run
                continue
    return total


def check(projected: float = 0.0):
    """Raise if we're already past the hard stop, or this next step would take us past it."""
    total = spent()
    if total + projected > HARD_STOP_USD:
        raise BudgetExceeded(
            f"Spent ${total:.2f}; next step projected ${projected:.2f}; hard stop ${HARD_STOP_USD:.2f}.")


def log(model, usage, phase="", batch=False) -> float:
    """Record one response's usage. `usage` is response.usage from the Anthropic SDK."""
    cw = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cr = getattr(usage, "cache_read_input_tokens", 0) or 0
    usd = price(model, usage.input_tokens, usage.output_tokens, cw, cr, batch)
    LOG.parent.mkdir(exist_ok=True)
    with _file_lock():  # threads and separate scripts may write at the same moment
        new = not LOG.exists()
        with LOG.open("a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(FIELDS)
            w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), phase, model,
                        usage.input_tokens, usage.output_tokens, cw, cr, int(batch), f"{usd:.6f}"])
    return usd


def projection(n_calls, avg_in, avg_out, model, cached_in=0, batch=False) -> float:
    """Rough cost of a phase: n calls x average tokens. cached_in = tokens read from cache per call."""
    return n_calls * price(model, avg_in, avg_out, 0, cached_in, batch)


if __name__ == "__main__":
    print(f"Spent so far: ${spent():.4f} of ${HARD_STOP_USD:.2f} hard stop")
