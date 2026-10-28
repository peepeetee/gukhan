# 진행 상황 / Status — 2026-10-28

PR #6 was already merged; PR #7 was merged as `f14d8fd` after resolving the test
fixture count conflict. 49 tests passed at merge time.

통합 사전 / Combined build:

- stdict: 435,000 items, 301,408 Sino-Korean candidates, 277,078 accepted, 24,330 rejected.
- Wiktionary: 64,457 lines, 30,599 accepted pairs, 356 rejected.
- Final: 278,253 entries, including 1,043 native homograph markers.
- Deduplicated rejects: 24,468 (20,739 alignment; 1,910 missing readings; 1,819 reading mismatch).
- Ranking: 28,684 vocabulary-level matches; 2,281 learner-rank matches.

Mirror commit: `42c0d01889f34536e9cf94fe57f62bd2055b1bde`.
All input/output hashes are in the separate lexicon manifest. Ranking columns do not
alter conversion decisions or the `--min-weight` threshold. Ties without signals still
use deterministic Hanja ordering. This is ordering, not inferred disambiguation.

한국어: 빈도 자료는 동점 후보 순서에만 사용합니다. 근거가 없는 동점은 문자 순서로
안정적으로 표시하며 자동으로 뜻을 선택하지 않습니다. 오류·보류 수치는 회귀 README를 보세요.

Milestone 4 adds three scan-linked 韓龍雲 items. Original-edition verification for
李光洙, 玄鎭健, 蔡萬植 remains pending; modernized pages are not valid historical gold.
Milestone 5 has an MV3 preview with separate local data import; browser integration
validation remains pending. The downloaded Chromium failed to start on this Windows
installation (side-by-side configuration error); the Edge fallback exited at launch.
The proposed browser CI workflow is retained locally at `.github/workflows/extension.yml`:
GitHub rejected its push because the saved OAuth credential lacks `workflow` scope.
The draft PR includes the browser test harness, but not that workflow.
Milestone 6 font guidance is in `fonts.md`. A stable milestone 7 release is not ready
until the browser checks and literature provenance review are complete.

한국어: 나머지 세 작가의 원문 판본 확인과 브라우저 통합 검증이 남아 있습니다.
현재 확장 프로그램은 시험판이며 안정판 출시 완료로 표시하지 않습니다.

Names: `gukhan` is used by this repository. `國漢混用` is a descriptive phrase.
`dahlia/gukhanmun` is a distinct reverse-direction project; none of its code was used.
PyPI and npm returned HTTP 404 for `gukhan` on 2026-10-28. GitHub also has
`SGukhan/gukhan`, `gukhan1/gukhan`, and a separate `Gukhanmun-Reader` project.
Search results or an unused package name do not establish trademark clearance.
