# Milestone 2 Checklist (due 2 Nov 2026)

| Component | Marks | Where it lives | Done |
|---|---|---|---|
| Design description + diagrams | 2 | README "Design" section | [ ] |
| Running build | 3 | `app.py`, `resumeiq/` | [ ] |
| Demo / pilot run | 2 | `eval/results/<run>/` + video | [ ] |
| Git repo | 2 | this repo (check the link opens for outsiders) | [ ] |
| Synopsis / BMC / report | 1 | `docs/synopsis.pdf` (from `synopsis_template.md`) | [ ] |
| 90–150 s video | 2 | link in README | [ ] |

## Before submitting
- [ ] Ran `python eval/run_eval.py --runs 3` and committed the results folder
- [ ] Filled `human_rating_1to5` in results.csv for at least V0 and V3
- [ ] Added 2 anonymised test cases of your own (`eval/cases/09_*.json`, `10_*.json`)
- [ ] Screenshots of the app in `docs/`
- [ ] `CONTRIBUTIONS.md` updated, with dates
- [ ] No API key anywhere in the repo (`git grep -n "sk-"` returns nothing)

## Video outline (about 2 minutes)
| Time | Show |
|---|---|
| 0:00–0:15 | The problem + one statistic |
| 0:15–0:35 | Architecture diagram (4 steps) |
| 0:35–1:20 | Live demo: load a test case, run V3, walk through score, gaps, bullets |
| 1:20–1:45 | Case 03 on V0 (C++ wrongly listed as a match) vs V3; case 08 (prompt injection ignored) |
| 1:45–2:00 | Results table + Milestone 3 plan |
