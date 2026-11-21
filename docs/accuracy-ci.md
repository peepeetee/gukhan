# Accuracy check in CI / CI 正確度 檢査

Every pull request that touches the code, the regression sets or this check is scored twice, with the change and with
the base branch, and the **difference** goes to the job summary. 變更이 正確度를 올렸는지 떨어뜨렸는지 PR마다 봅니다.

## What it does / 하는 일

1. Fetches the NIKL dumps (標準國語大辭典 and 우리말샘) from the public mirror
   `spellcheck-ko/korean-dict-nikl` at a **pinned commit** (`NIKL_COMMIT` in `.github/workflows/accuracy.yml`), a sparse
   checkout of the two folders, only when no cached lexicon exists.
2. Builds a lexicon with `gukhan-lexicon-build` (about 700,000 entries, under two minutes) and caches it by the mirror
   commit and a hash of the builder's code, so most pull requests reuse it.
3. Scores every set of `tests/regression/` with default settings (`scripts/accuracy.py score`), once with the change and
   once with the base branch's code on the same items, and prints right / wrong / flagged / partial / over for each set
   with the change from the base in brackets (`scripts/accuracy.py compare`).
4. **Fails** when a held-out set (a file name containing `heldout`) has more than `MAX_WRONG_INCREASE` (2) more wrong
   words than the base. Other sets are shown but never fail the job: the tuning sets may move while rules are fitted.
   保留 標本에서 誤變換이 2개보다 많이 늘면 실패합니다.

## What the numbers mean / 수치의 뜻

The lexicon here comes from the NIKL dumps alone (no Wiktionary, no learner list), so the figures are lower or
different from the README's table, which is scored on the full lexicon. They are for comparing two versions of the
code on the same lexicon, never for quoting. README의 수치는 全體 辭典으로 잰 것이고 이 表는 變更 前後 比較用입니다.
A pull request that changes the builder is compared with a base lexicon built by the base's own builder (both are built and cached).

## Data / 資料

The dumps are CC BY-SA 2.0 KR (國立國語院). They are fetched in the job and are **never committed, uploaded as an
artifact or shipped**; the job's artifact holds only the JSON scores, and the built lexicon lives in the repository's
private Actions cache. The raw dumps stay out of the repository and the packages as in `docs/data-distribution.md`.
原資料는 CI 안에서만 받으며 저장소·패키지·산출물에 넣지 않습니다.

## Running it yourself / 직접 돌리기

```
git clone --depth 1 https://github.com/spellcheck-ko/korean-dict-nikl nikl       # 3 GB
gukhan-lexicon-build --stdict nikl/stdict --opendict nikl/opendict -o lexicon
python scripts/accuracy.py score lexicon -o head.json
git stash; python scripts/accuracy.py score lexicon -o base.json; git stash pop     # or PYTHONPATH=<base checkout>/src
python scripts/accuracy.py compare base.json head.json
```

To change the pinned mirror commit, edit `NIKL_COMMIT`, which also changes the cache key; the first run then rebuilds the
lexicon. 미러 commit을 바꾸면 cache 열쇠도 바뀌어 辭典을 새로 만듭니다.
