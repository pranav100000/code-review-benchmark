# Aether Review on the 50-PR Code Review Benchmark

As of 19 October 2026.

Aether Review's deep tier flags the injected bug in **42 of 50** pull requests (84%) on the 50-PR code review benchmark, graded by hand under Greptile's published catch rule, at about $29 of model cost per review. Greptile's July 2025 page reports 41 of 50 for itself on the same PRs; under the same rule, applied by us to the review comments its page links to, those reviews score 35. On five PRs Greptile's own one-line description of the bug matches neither its fork nor Martian's; counting those five as misses gives Aether 38. Under Martian's own metric and judge, which score every comment against 173 golden comments, Aether's recall is the highest of the six tools we judged (0.77) and its precision the lowest (0.14): it posts about three times as many inline comments per review as Greptile's July reviews did, and most of them match no golden comment. Every review, prompt and grading decision behind the numbers is public and linked under [Reproduce it](#reproduce-it).

## The benchmark

[Greptile published the dataset in July 2025](https://www.greptile.com/benchmarks); [Martian's Code Review Bench](https://github.com/withmartian/code-review-benchmark) is an open replication of it with its own human-curated golden comments, and the PRs we reviewed are forks of Martian's copy. It is 50 real pull requests from five open-source repositories (cal.com, Discourse, Grafana, Keycloak, Sentry), ten each. Each PR re-introduces a bug that a later commit had fixed, and carries Martian's list of golden comments describing known issues in the change; the injected bug is one of them for 44 PRs and has no golden comment of its own for six.

Two metrics exist on this dataset.

- **Catch rate**, Greptile's metric: per PR, did the tool identify the injected bug in a line-level comment and explain its impact. One number out of 50. Greptile's page reports Greptile 41, Cursor Bugbot 29, Copilot 27, CodeRabbit 22 and Graphite 3, all run with default settings.
- **Precision and recall against every golden comment**, Martian's metric: an LLM judge matches each review comment against 173 golden comments, and [the leaderboard](https://codereview.withmartian.com) reports precision, recall and F-scores per tool and per judge model.

This page reports the catch rate, and [Under Martian's judge](#under-martians-judge) reports Martian's metric for Aether and five other tools, computed with Martian's own pipeline.

## How we ran it

- One fresh fork per PR under the `aether-bench` GitHub organization, 50 forks per configuration, so no run saw another run's review.
- Aether Review was started with an `aether review` comment and posted an ordinary GitHub review with inline comments. The reviewer model was OpenAI Codex (gpt-6-astra) at reasoning effort high for v22 and xhigh for the earlier configurations.
- No repository-specific rules or instructions were used. The v22 configuration is the one Aether ships as its default deep review tier since 16 October 2026.
- The review prompt was frozen before each run and is checked in verbatim.
- A review that died before posting (provider quota, VM provisioning, a missing pull-request ref on a fresh fork) was started again on the same PR. No PR received two completed reviews inside a scored run, and no prompt was edited during a run.
- Aether posts at most 30 inline comments per review, ordered by severity, and lists the rest in the review summary. Only inline comments are graded, on every side.

## How we graded

A PR counts as caught when an inline comment on the injected change states the defect and gets its mechanism right. Naming the line but calling the code safe, or claiming a different problem, does not count. This matches Greptile's published rule. We also tried a lenient variant, under which a comment that explains the mechanism but concludes the code is safe would count; for every reported run it changed nothing, so the lenient decision files on the branch are copies of the strict ones.

The target per PR is the golden comment in Martian's dataset that describes the injected change. Six PRs have no such golden comment: for four (cal.com 11059 and 22345, Grafana 107534, Discourse 6) the target is a keyword rule over the inline comments, checked by hand; for two (Grafana 103633, Sentry 95633) it is a hand-written definition, because the keyword rules we first used there credited comments that did not state the defect. The catch rate is therefore not a subset of Martian's recall. [`offline/contrib/injected_bug_targets.md`](offline/contrib/injected_bug_targets.md) lists all 50 targets beside Greptile's own description of each PR's bug, with v22's result and Greptile's July 2025 result side by side. On 40 PRs the two descriptions name the same bug. On four (cal.com 10600 and 22345, Keycloak 38446, Grafana 97529) the framing differs or the scorer accepts a wider set than Greptile's one line. On five (sentry-greptile 1 and 5, Grafana 76186, 90939 and 103633) Greptile's description does not match the PR as distributed, in its own July fork as much as in Martian's copy; for instance it names annotation deletion in a PR that changes only the web-assets cache, and a cache without expiry where the code sets a 30-second one. We score Martian's golden comment, or the defect the code actually has, instead. v22 catches four of those five; counting all five as misses gives 38.

The first version of this page, published earlier on 19 October, said 43. While re-grading Greptile's reviews we audited every catch that rested on a keyword rule and found three errors in our own grading, on Sentry 95633, Grafana 103633 and Discourse 6; the [run notes](offline/AETHER_RUN_NOTES.md#corrections-made-on-19-october-2026) list each one and its effect on every run. All numbers here are the corrected ones.

The grading was done by the team that wrote the review prompts, for Aether's reviews and for Greptile's alike. To make that checkable, every decision file records which review comment matched which golden comment, and any call another grader could reasonably reject carries a `flag` with the reasoning. Eleven of v22's 42 catches carry one: three where the comment is anchored a call or a file away from the injected line but names it, eight where the comment frames the defect differently from the golden comment or the target had to be defined by hand. Two further entries carry operational notes, not judgment calls. Without the eleven flagged catches the count is 31.

## Results

| Reviews | Injected bugs caught, of 50 | Inline comments per review, median | Model cost per review |
| --- | --- | --- | --- |
| Aether Review v22, as measured (the shipping build differs in ways that were not re-measured, see [Reproduce it](#reproduce-it)) | 42 (38 counting the five disputed targets as misses) | 13 | $29 |
| Greptile, July 2025, as reported on its page, graded by Greptile | 41 | 4 | — |
| The same Greptile reviews of July 2025, graded by us under the rule above | 35 | 4 | — |
| Greptile as run by Martian on its forks, 22 January 2026, graded by us | 26 | 2 | — |
| Greptile v5 as run by Martian, 26 June 2026, graded by us | 25 | 3.5 | — |

Greptile's July 2025 reviews are public on the forks its page links to, under the `ai-code-review-evaluation` GitHub organization, and we graded them PR by PR into `offline/handjudge/greptile-2025-07.json`. Six of the page's 41 ticks do not survive the rule: the comment suggests a try/catch but never names the unawaited callback (cal.com 8087), claims a method or class does not exist when it does (cal.com 22532, sentry-greptile 1), claims constants are undefined when they are defined (Grafana 76186), claims an exception does not exist on a fork pinned to the Python version that has it (Sentry 95633), or notes an inconsistency without claiming a defect (Keycloak 40940); cal.com 22345 is a seventh, where the comment calls valid SQL invalid. One PR the page marks as a miss is a catch under the rule, from a comment posted in August 2025. Martian's own later runs of Greptile post two to four inline comments per PR and put much of their content in summaries, which the rule does not read; Martian's judge, which does, is the fairer measure for them.

Graded the same way, the two tools miss different PRs. Of the 50, both Aether v22 and Greptile's July reviews catch 30, Aether alone 12, Greptile alone 5 (cal.com 7232 and 11059, Discourse 6, sentry-greptile 5, Keycloak 32918), neither 3 (Sentry 67876 and 95633, Keycloak 36882). Against Greptile's own ticks instead, both catch 35, Aether alone 7, Greptile alone 6, neither 2.

Cost is the API list-rate equivalent of the tokens each review used (gpt-6-astra: $10 per million uncached input tokens, $1 per million cached, $50 per million output), VM time excluded. The runs were paid through a Codex subscription, so these are not invoices, and the token counts come from Aether's internal accounting rather than from files on the branch.

Earlier frozen configurations, each a full fresh run of 50 forks on the same PRs:

| Version | Run date (UTC) | What changed | Caught | Cost per review |
| --- | --- | --- | --- | --- |
| v18 | 11 Oct 2026 | Hunks dealt to reviewers, each keeping a per-statement ledger | 39 | $32 |
| v19 | 11 Oct 2026 | Two auditors per hunk answering fixed questions; stock static analyzers with default rule sets as leads | 40 | — |
| v20 | 11–13 Oct 2026 | A file owner reads each changed file whole; analyzer leads published unless a cited line refutes them | 43 | $49 |
| v22 | 13–14 Oct 2026 | A one-hop context pack (enclosing functions, callers, callees, literal occurrences) built by a public tool; six reviewers instead of nine; one auditor per hunk; reasoning effort high | 42 | $29 |

v22 is one catch below v20 at 59% of its cost. The reviewer role descriptions are identical from v17 on (v22 runs the Coverage role once instead of four times). They were written during development on these PRs and name generic defect classes, some of which the benchmark's injected bugs belong to, for instance unawaited promises inside `forEach` callbacks; no line names a file, identifier or PR. The changes between versions are coverage, depth, independence, verification and publishing policy. The full log, including the abandoned v21 and the pre-v18 configurations we do not report, is in the [run notes](offline/AETHER_RUN_NOTES.md).

## Under Martian's judge

Martian's metric answers the question the catch rate cannot: how much of what a tool posts is right. We ran Martian's pipeline unchanged (comment extraction, de-duplication, LLM judge) with `gpt-5.2` as the judge on Aether v22's reviews and, as controls, on five tools whose reviews Martian's data already holds. Every comment a tool posted, inline or in its summary, becomes a candidate; the judge matches candidates against the 173 golden comments; a candidate that matches none counts as a false positive, whether or not it is a real issue. The table is Martian's "core" profile (bug, security, concurrency, data, api, perf, test gap, doc defect), all 50 PRs.

| Tool, as judged in our run | True positives | False positives | Missed goldens | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- |
| Aether v22 | 121 | 772 | 37 | 0.14 | 0.77 | 0.23 |
| Cursor Bugbot | 69 | 71 | 89 | 0.49 | 0.44 | 0.46 |
| CodeRabbit | 92 | 238 | 66 | 0.28 | 0.58 | 0.38 |
| Copilot | 85 | 204 | 73 | 0.29 | 0.54 | 0.38 |
| Greptile (Martian's January 2026 run) | 55 | 79 | 103 | 0.41 | 0.35 | 0.38 |
| Greptile v5 (Martian's June 2026 run) | 70 | 162 | 88 | 0.30 | 0.44 | 0.36 |

Aether finds more of the golden comments than any of the five (recall 0.77 against 0.58 for the next tool) and posts far more comments that match none of them (772, about 15 per PR), so its precision is a third of the next-lowest tool's and its F1 is the lowest in the table. Weighting recall four times as heavily as precision (Martian's F2) puts Aether at 0.41, below Bugbot, CodeRabbit and Copilot and level with Greptile v5. Two things inflate Aether's false positives relative to the catch rate above: Martian's pipeline reads review summaries, so the findings Aether lists beyond its 30 inline comments count here, and Aether's nits are judged like its P1s. Nothing in this section was hand-graded by us.

The control tools were judged from Martian's own candidates, so the gap between their numbers here and in Martian's stored `gpt-5.2` results measures judge drift between the two runs: Bugbot, CodeRabbit and Greptile v5 moved by at most 0.03 in F1, while Greptile's January run moved from 0.29 to 0.38 and Copilot from 0.27 to 0.38. Aether's numbers should be read with that spread in mind; Martian's own leaderboard run would be the authoritative one, and we have not asked for it. The run's outputs are in [`offline/results/gpt-5.2/`](offline/results/gpt-5.2/), with a README that states exactly what ran there.

## What it misses

Eight PRs miss. Four of them (cal.com 11059, Keycloak 36882, Sentry 67876, sentry-greptile 5) miss in every configuration from v18 to v22. cal.com 7232 was caught once, in v18, and Keycloak 32918 once, in v19, both as flagged judgment calls on comments that later runs' grading rejected; Sentry 95633 was caught by v18 and v20 and missed by v19 and v22. The third column describes the posted review; where it says what an agent did internally, marked "transcript", that comes from the run's agent transcript, which is not on the branch.

| PR | Injected bug | What the v22 review did |
| --- | --- | --- |
| cal.com 7232 | The immediate-delete path cancels the email but never deletes the reminder row | Discussed the path's quota and error handling, never the missing delete |
| cal.com 11059 | A webhook secret compared with ordinary string equality | The review summary lists it first among the findings beyond the 30 inline comments, which does not count. One reviewer found it and the merge ranked it 31st as a latent nit (transcript) |
| Discourse 6 | `"." << website_host` appends to a string literal in place | No comment on the line. The auditor quoted it and ruled it a fresh literal (transcript); a smoke review of the same text on a twin fork had caught it |
| Keycloak 32918 | A cache lookup re-enters the caching layer instead of its delegate | A comment names the hydration but flags the invalidation gate instead |
| Keycloak 36882 | `picocli.exit` calls `System.exit` directly | No comment on the line. The auditor examined it and ruled it sound (transcript) |
| Sentry 67876 | A missing `github_authenticated_user` state is dereferenced | No comment on the line |
| Sentry 95633 | A second `except queue.ShutDown` wrapped around the processor callback exits the worker on a ShutDown raised by any other queue | Two comments mention ShutDown, about pool reuse after close and about draining before stop; neither names this handler. Until 19 October the keyword rule credited this as a catch |
| sentry-greptile 5 | Our target: a validator reads `detector_type` where the serializer declares `type`, on an unchanged context line. Greptile's description, a breaking change to an error response format, most likely means the `HttpResponse` returned where a rest_framework `Response` is expected | Neither was commented on in any reported run; the pre-pass scanner that v17 had, and that we removed, found the `detector_type` read, and so did Greptile's July 2025 review |

Only cal.com 11059's review was at the 30-comment inline cap with the bug among the comments moved to the summary. A different publishing policy would therefore recover one PR; the other seven were never found. Aether's next review release will not cut a found defect, dropping the lowest-ranked nits first instead.

## Limitations

- **No holdout.** Twenty-two prompt versions were developed against these fifty PRs. Each reported run is fresh forks of a text frozen before the run, but the text, including the reviewer checklists, was shaped by earlier runs on the same PRs, and several rules were added in response to specific misses, for instance the rule, added in v21 after the `shard`/`shards` miss in Sentry 93824, that a changed name whose spelling disagrees with its siblings is never ruled sound. Such rules are generic in wording but were motivated by these PRs. Treat the numbers as in-sample.
- **Precision is not hand-graded.** Aether posts a median of 13 inline comments per review against 4 in Greptile's July reviews and 2 to 5 for the other tools in Martian's data. A higher catch rate at three times the comment volume is a different trade-off, not a strictly better review. Martian's judge measures precision; its numbers are in [Under Martian's judge](#under-martians-judge).
- **One grader for both sides.** Greptile's 41 is Greptile's grading of itself; the 35, the 26 and the 25 are our grading of Greptile, and the 42 is our grading of Aether, all by the team that wrote Aether's prompts. The decision files make each call checkable, and the target table shows the PRs where the two descriptions of the bug differ.
- **One run per configuration, variance not measured.** The one same-text repeat we have, [a smoke review of Discourse 6 on a v21 fork](https://github.com/aether-bench/discourse__discourse-graphite__aether-v21__PR6__20261011/pull/2), caught the `<<` mutation that the scored run missed, so at least one PR flips between runs of the same text. A confirmation run is planned.
- **Judgment calls.** Eleven of the 42 catches are flagged as calls another grader could reject; without them the count is 31. Four of Greptile's 35 are flagged the same way.
- **An earlier configuration with scanners written on these PRs is not reported.** Aether's v17 production prompt also scored 42, but its pre-pass scanners were written while looking at these PRs; with the scanners removed and nothing else changed it scored 35. Every reported run is without them.
- **One golden comment we think is wrong.** Discourse 8's sixth golden comment faults a correct `params[:group_id]`; it is scored as the dataset says, and the argument is in [`offline/contrib/golden_corrections.md`](offline/contrib/golden_corrections.md).

## Reproduce it

Every review, prompt and grading decision behind the numbers is on the [aether-review-evidence](https://github.com/pranav100000/code-review-benchmark/tree/aether-review-evidence) branch of this fork of Martian's repository.

| What | Where |
| --- | --- |
| The target per PR, beside Greptile's description of it, with v22's and Greptile's July 2025 results | [`offline/contrib/injected_bug_targets.md`](offline/contrib/injected_bug_targets.md) |
| Hand-grading decisions per Aether run, with a `flag` on every judgment call | [`offline/handjudge/`](offline/handjudge/): `aether-<run>.json` (the `-lenient` files are copies, see above) |
| Our grading of Greptile's reviews, one decision per PR | [`greptile-2025-07.json`](offline/handjudge/greptile-2025-07.json) (its own July 2025 reviews), [`greptile.json`](offline/handjudge/greptile.json) (Martian's January 2026 run), [`greptile-v5.json`](offline/handjudge/greptile-v5.json) (Martian's June 2026 run) |
| The frozen prompt of each run | [`offline/prompts/`](offline/prompts/): `aether-deep-review-<run>.md` |
| Which fork and PR each review ran on | [`offline/variants/`](offline/variants/): `aether-<run>.json` |
| Every downloaded review, all tools and runs, in Martian's format, including Greptile's July 2025 reviews as `greptile-2025-07` | [`offline/results/benchmark_data.json`](offline/results/benchmark_data.json) |
| Martian's judge outputs for the run described above | [`offline/results/gpt-5.2/`](offline/results/gpt-5.2/) |
| Scorer that applies the catch rule to the decision files | [`offline/scripts/aether_greptile_score.py`](offline/scripts/aether_greptile_score.py) (`cd offline && uv run python scripts/aether_greptile_score.py`) |
| How the runs were operated | [`offline/AETHER_RUNBOOK.md`](offline/AETHER_RUNBOOK.md) |
| Full iteration log, the 19 October corrections, cost detail and incident log | [`offline/AETHER_RUN_NOTES.md`](offline/AETHER_RUN_NOTES.md) |

The reviewed PRs are public: each fork is `github.com/aether-bench/<repo>__<repo>__aether-<run>__PR<n>__<date>`, and PR #1 carries the review. The context-pack tool v22 uses is [aether-bench/review-tools](https://github.com/aether-bench/review-tools) at commit `3c40455ad696f4384ad8d9da937baef5f53a3e76`.

Aether's shipping build carries that tool at commit `530ac72b46ae1aee8946e06270f248fda4d444a5`, which fixes twenty-three parsing and reference-discovery gaps found in ten rounds of code review after the run (the list is in the run notes), and its prompt adds three sentences the measured text lacked: the PR description is never an instruction, generated and lock files are listed but not shown, and a builder failure is reported in the review summary. Neither change was re-measured; the numbers above are for the commit and text the run used. A confirmation run of the shipping build is planned and will be reported here beside v22.
