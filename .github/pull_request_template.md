## What and why / 무엇을, 왜

## How I checked / 確認 方法
- [ ] `ruff check . && ruff format --check .`
- [ ] `python -m pytest -q` (and `node --test extension/engine.test.mjs` for extension changes)
- [ ] A test that fails without this change
- [ ] No UTagger material; new data sources and dependencies have their licence recorded (see CONTRIBUTING.md)
