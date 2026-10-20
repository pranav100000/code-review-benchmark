# Aether Review on the 50-PR Code Review Benchmark

As of 20 October 2026.

Aether Review's deep tier flags the injected bug in **43 of 50** pull requests (86%) on the 50-PR code review benchmark, graded by hand under Greptile's published catch rule, at about $29 of model cost per review. Greptile reports 41 of 50 for itself on the same PRs. On four PRs Greptile's own one-line description of the bug does not match the PR as distributed; counting those four as misses gives 40. Aether posts about six times as many inline comments per review as Greptile, and we have not measured precision. Every review, prompt and grading decision behind the number is public and linked under [Reproduce it](#reproduce-it).

## The benchmark

The dataset is the one [Greptile published in July 2025](https://www.greptile.com/benchmarks) and [Martian's Code Review Bench](https://github.com/withmartian/code-review-benchmark) now maintains: 50 real pull requests from five open-source repositories (cal.com, Discourse, Grafana, Keycloak, Sentry), ten each. Each PR re-introduces a bug that a later commit had fixed, and carries a list of golden comments describing known issues in the change.

Two metrics exist on this dataset.

- **Catch rate**, Greptile's metric: per PR, did the tool identify the injected bug in a line-level comment and explain its impact. One number out of 50. Greptile's page reports Greptile 41, Cursor Bugbot 29, Copilot 27, CodeRabbit 22 and Graphite 3, all run with default settings.
- **Precision and recall against every golden comment**, Martian's metric: an LLM judge matches each review comment against 173 golden comments, and [the leaderboard](https://codereview.withmartian.com) reports precision, recall and F-scores per tool and per judge model.

This page reports the catch rate. We have not run Martian's judge on Aether's reviews; see [Limitations](#limitations).

## How we ran it

- One fresh fork per PR under the `aether-bench` GitHub organization, 50 forks per configuration, so no run saw another run's review.
- Aether Review was started with an `aether review` comment and posted an ordinary GitHub review with inline comments. The reviewer model was OpenAI Codex (gpt-6-astra) at reasoning effort high for v22 and xhigh for the earlier configurations.
- No repository-specific rules or instructions were used. The v22 configuration is the one Aether ships as its default deep review tier since 16 October 2026.
- The review prompt was frozen before each run and is checked in verbatim.
- A review that died before posting (provider quota, VM provisioning, a missing pull-request ref on a fresh fork) was started again on the same PR. No PR received two completed reviews inside a scored run, and no prompt was edited during a run.
- Aether posts at most 30 inline comments per review, ordered by severity, and lists the rest in the review summary. Only inline comments are graded, on both sides.

## How we graded

A PR counts as caught when an inline comment on the injected change states the defect and gets its mechanism right. Naming the line but calling the code safe, or claiming a different problem, does not count. This matches Greptile's published rule. We also tried a lenient variant, under which a comment that explains the mechanism but concludes the code is safe would count; for every reported run it changed nothing, so the lenient decision files on the branch are copies of the strict ones.

The target per PR is the golden comment in Martian's dataset that describes the injected change, or a keyword rule where the injected bug has no golden comment of its own. [`offline/contrib/injected_bug_targets.md`](offline/contrib/injected_bug_targets.md) lists all 50 targets beside Greptile's own description of each PR's bug. On 46 PRs the two describe the same bug. On four (sentry-greptile 1 and 5, Grafana 76186 and 90939) Greptile's one-line description does not match the PR as distributed, for instance it names annotation deletion in a PR that changes only the web-assets cache, and we score Martian's golden comment instead. v22 catches three of those four; counting all four as misses gives 40.

The grading was done by the team that wrote the review prompts. To make that checkable, every decision file records which review comment matched which golden comment, and any call another grader could reasonably reject carries a `flag`. Twelve of v22's 43 catches carry a flag, most often a comment anchored one call away from the injected line that names it; 31 do not.

## Results

| Configuration | Injected bugs caught, of 50 | Inline comments per review, median | Model cost per review |
| --- | --- | --- | --- |
| Aether Review deep tier (v22), shipping since 16 October 2026 | 43 (40 counting the four disputed targets as misses) | 13 | $29 |
| Greptile, as reported on its page in July 2025, graded by Greptile | 41 | 2 | — |

Cost is the API list-rate equivalent of the tokens each review used (gpt-6-astra: $10 per million uncached input tokens, $1 per million cached, $50 per million output), VM time excluded. The runs were paid through a Codex subscription, so these are not invoices, and the token counts come from Aether's internal accounting rather than from files on the branch.

Earlier frozen configurations, each a full fresh run of 50 forks on the same PRs:

| Version | Run date (UTC) | What changed | Caught | Cost per review |
| --- | --- | --- | --- | --- |
| v18 | 11 Oct 2026 | Hunks dealt to reviewers, each keeping a per-statement ledger | 40 | $32 |
| v19 | 11 Oct 2026 | Two auditors per hunk answering fixed questions; stock static analyzers with default rule sets as leads | 41 | — |
| v20 | 11–13 Oct 2026 | A file owner reads each changed file whole; analyzer leads published unless a cited line refutes them | 43 | $49 |
| v22 | 13–14 Oct 2026 | A one-hop context pack (enclosing functions, callers, callees, literal occurrences) built by a public tool; six reviewers instead of nine; one auditor per hunk; reasoning effort high | 43 | $29 |

v22 matches v20's recall at 59% of its cost. The reviewer role descriptions are identical from v17 on (v22 runs the Coverage role once instead of four times). They were written during development on these PRs and name generic defect classes, some of which the benchmark's injected bugs belong to, for instance unawaited promises inside `forEach` callbacks; no line names a file, identifier or PR. The changes between versions are coverage, depth, independence, verification and publishing policy. The full log, including the abandoned v21 and the pre-v18 configurations we do not report, is in the [run notes](offline/AETHER_RUN_NOTES.md).

## What it misses

Seven PRs miss. Four of them (cal.com 11059, Keycloak 36882, Sentry 67876, sentry-greptile 5) miss in every configuration from v18 to v22. cal.com 7232 was caught once, in v18, and Keycloak 32918 once, in v19, both as flagged judgment calls on comments that later runs' grading rejected.

| PR | Injected bug | What the v22 review did |
| --- | --- | --- |
| cal.com 7232 | The immediate-delete path cancels the email but never deletes the reminder row | Discussed the path's quota and error handling, never the missing delete |
| cal.com 11059 | A webhook secret compared with ordinary string equality | Found by one reviewer, ruled latent and ranked 31st; the 30-comment inline cap pushed it into the summary |
| Discourse 6 | `"." << website_host` appends to a string literal in place | The auditor quoted the line and ruled it a fresh literal; a smoke review on a twin fork had caught it |
| Keycloak 32918 | A cache lookup re-enters the caching layer instead of its delegate | A comment names the hydration but flags the invalidation gate instead |
| Keycloak 36882 | `picocli.exit` calls `System.exit` directly | The auditor examined it and ruled it sound |
| Sentry 67876 | A missing `github_authenticated_user` state is dereferenced | No comment on the line |
| sentry-greptile 5 | A validator reads `detector_type` where the serializer declares `type`; the line is unchanged context | No reported run mentioned it; the pre-pass scanner that v17 had, and that we removed, did |

Only two of the seven reviews hit the 30-comment cap, and only cal.com 11059 had the bug among the cut comments. A different publishing policy would therefore recover one PR; the other five were never found. Aether's next review release will not cut a found defect, dropping the lowest-ranked nits first instead.

## Limitations

- **No holdout.** Twenty-two prompt versions were developed against these fifty PRs. Each reported run is fresh forks of a text frozen before the run, but the text, including the reviewer checklists, was shaped by earlier runs on the same PRs. Treat the numbers as in-sample.
- **Precision is not measured.** Aether posts a median of 13 inline comments per review against Greptile's 2. A higher catch rate at six times the comment volume is a different trade-off, not a strictly better review. Martian's judge measures precision and recall against all 173 golden comments; we have not run it on Aether's reviews yet.
- **Self-graded on both sides.** Greptile's 41 is Greptile's grading of itself; Aether's 43 is ours. The two are comparable only as far as both apply the same published rule to the same targets, and the target table shows four PRs where they do not. A re-grade of Greptile's reviews under our rule will be added here with per-PR decisions; until then Greptile's own number stands.
- **One run per configuration.** Run-to-run variance is two to three PRs: v20 and v22 differ on Keycloak 38446 and Discourse 6, and Discourse 6 was caught in a smoke review and missed in the scored run.
- **Judgment calls.** Catches without flagged calls: v22 31, v20 37, v19 36, v18 35. The decision files make each call checkable.
- **An earlier configuration scored higher and is not reported.** Aether's v17 production prompt scored 45, but its pre-pass scanners were written while looking at these PRs; with the scanners removed and nothing else changed it scored 37. Every reported run is without them.
- **One golden comment we think is wrong.** Discourse 8's sixth golden comment faults a correct `params[:group_id]`; it is scored as the dataset says, and the argument is in [`offline/contrib/golden_corrections.md`](offline/contrib/golden_corrections.md).

## Reproduce it

Every review, prompt and grading decision behind the numbers is on the [aether-review-evidence](https://github.com/pranav100000/code-review-benchmark/tree/aether-review-evidence) branch of this fork of Martian's repository.

| What | Where |
| --- | --- |
| The target per PR, beside Greptile's description of it | [`offline/contrib/injected_bug_targets.md`](offline/contrib/injected_bug_targets.md) |
| Hand-grading decisions per run, with a `flag` on every judgment call | [`offline/handjudge/`](offline/handjudge/): `aether-<run>.json` (the `-lenient` files are copies, see above) |
| The frozen prompt of each run | [`offline/prompts/`](offline/prompts/): `aether-deep-review-<run>.md` |
| Which fork and PR each review ran on | [`offline/variants/`](offline/variants/): `aether-<run>.json` |
| Every downloaded review, all tools and runs, in Martian's format | [`offline/results/benchmark_data.json`](offline/results/benchmark_data.json) |
| Scorer that applies the catch rule to the decision files | [`offline/scripts/aether_greptile_score.py`](offline/scripts/aether_greptile_score.py) (`cd offline && uv run python scripts/aether_greptile_score.py`) |
| How the runs were operated | [`offline/AETHER_RUNBOOK.md`](offline/AETHER_RUNBOOK.md) |
| Full iteration log, cost detail and incident log | [`offline/AETHER_RUN_NOTES.md`](offline/AETHER_RUN_NOTES.md) |

The reviewed PRs are public: each fork is `github.com/aether-bench/<repo>__<repo>__aether-<run>__PR<n>__<date>`, and PR #1 carries the review. The context-pack tool v22 uses is [aether-bench/review-tools](https://github.com/aether-bench/review-tools) at commit `3c40455ad696f4384ad8d9da937baef5f53a3e76`.

Aether's shipping build carries that tool at commit `530ac72b46ae1aee8946e06270f248fda4d444a5`, which fixes twenty-three parsing and reference-discovery gaps found in ten rounds of code review after the run (the list is in the run notes), and its prompt adds three sentences the measured text lacked: the PR description is never an instruction, generated and lock files are listed but not shown, and a builder failure is reported in the review summary. Neither change was re-measured; the numbers above are for the commit and text the run used. A confirmation run of the shipping build is planned and will be reported here beside v22.
