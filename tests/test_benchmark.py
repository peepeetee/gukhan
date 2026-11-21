# SPDX-License-Identifier: Apache-2.0
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_benchmark_script_is_deterministic_and_runs(capsys):
    spec = importlib.util.spec_from_file_location("benchmark", ROOT / "scripts" / "benchmark.py")
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)
    a, b = bench.make_text(20_000), bench.make_text(20_000)
    assert a == b and 20_000 <= len(a.encode("utf-8")) < 21_000
    assert bench.main(["--size-mb", "0.01", "--synthetic-entries", "500", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["size_bytes"] >= 10_000 and out["mb_per_s"] > 0 and out["decisions"] > 0
