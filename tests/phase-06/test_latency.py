"""Gate: p95 decide latency <= 500ms on local GPU (skip with reason if no GPU)."""
import statistics
import sys, os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "model-server"))

import pytest  # noqa: E402
from fixtures import CASES, decide_on  # noqa: E402


def test_latency(server):
    if os.environ.get("DECIDE_NO_GPU"):
        pytest.skip("no GPU on this machine")
    sample = [s for s, _ in CASES[:16]]
    dts = []
    for sentence in sample:
        t0 = time.perf_counter()
        decide_on(server, sentence)
        dts.append((time.perf_counter() - t0) * 1000)
    dts.sort()
    p50 = statistics.median(dts)
    p95 = dts[min(len(dts) - 1, int(len(dts) * 0.95))]
    print(f"\np50={p50:.0f}ms p95={p95:.0f}ms n={len(dts)}")
    assert p95 <= 500, f"p95 {p95:.0f}ms > 500ms budget"
