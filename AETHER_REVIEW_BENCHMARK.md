# Aether Review vs Greptile Benchmark

As of 20 October 2026 (UTC). Published by the Aether team from the fork that holds the evidence.

On Greptile's public 50-PR benchmark, Aether Review's deep tier flags 43 of 50 injected bugs under both the strict and the lenient rule, at about $29 of model cost per review. Greptile's own reviews, re-graded under the same rules, score 35 strict and 40 lenient against the 41 it claims.

## Results

Every full run on the 50 PRs, graded by the two rules in the next section. v22 is the configuration Aether ships as its deep review tier. Cost is the API list-rate equivalent of the Codex tokens each review used, VM time excluded; a dash means it was not measured.

| Run | Reviewer | Strict | Lenient | Cost per review |
| --- | --- | --- | --- | --- |
| Greptile, from the comments on its page (it claims 41) | Greptile | 35 | 40 | — |
| Aether v22 "pack", shipping deep tier | Codex gpt-6-astra, reasoning high | 43 | 43 | $29 |
| Aether v20 "owners" | Codex gpt-6-astra, xhigh | 43 | 43 | $49 |
| Aether v19 "audit" | Codex gpt-6-astra, xhigh | 41 | 41 | — |
| Aether v18 "ledger" | Codex gpt-6-astra, xhigh | 40 | 40 | $32 |
| Aether v17 production skill, with its pre-pass scanners | Codex gpt-6-astra, xhigh | 45 | 50 | — |
| Aether v17 without the pre-pass (ablation) | Codex gpt-6-astra, xhigh | 37 | 38 | — |
| Aether v16 | Codex gpt-6-astra, xhigh | 41 | 49 | — |
| Aether v16, 31 of 50 PRs reviewed before Claude's weekly limit | Claude Code, Opus 5.5, xhigh | 27 of 31 | 30 of 31 | — |

v17's 45 is not the headline because its pre-pass scanners were written while looking at these PRs; the ablation row shows they supplied eight of its strict catches. Every run from v18 on removes them and is a single fresh run of a prompt frozen before the run.

## The benchmark and how we ran it

Greptile's benchmark is 50 real pull requests from five open-source repositories (cal.com, Discourse, Grafana, Keycloak, Sentry), ten each. Every PR carries one injected bug and a list of two to nine known issues ("golden comments"). A tool reviews the PR and is scored on whether its comments flag the injected bug. The dataset and harness are public in Martian's [code-review-benchmark](https://github.com/withmartian/code-review-benchmark) repository; Greptile reports 41 of 50 for itself.

Each Aether configuration was run the same way:

- 50 fresh forks under the aether-bench GitHub organization, one fork per PR and one PR per fork, so no run saw another run's review.
- Aether Review was started by an `aether review` comment and posted a normal GitHub review with inline comments. The reviewer was Codex gpt-6-astra on the owner's Codex subscription; reasoning effort was xhigh except where a row says high.
- The review prompt was frozen before the run and is checked in verbatim per run (see Reproduce it).
- A review that died before posting (Codex quota outage, VM provisioning, a missing `refs/pull/1/head` on a fresh fork, one API validation bug) was started again on the same PR. No PR received a second completed review inside a scored run, and no prompt was edited during a run.
- Grading counts inline comments only, never the review summary. Martian's harness reads at most the first 30 inline comments of a review, so every Aether prompt since v11 posts at most 30 inline comments ordered p1, p2, nit and lists the rest in the summary.

## Grading rules

Both sides are graded by the same two rules, by hand, from the inline review comments on each PR.

- **Strict**: an inline comment on the injected change states the defect and gets its mechanism right. A comment that names the line but calls the code safe, or claims a different problem, does not count.
- **Lenient**: an inline comment on the injected change explains its mechanism, even if it concludes the code is safe or mis-states the consequence. This is the rule Greptile's page effectively applies to itself, so it is the column to set against its 41.

Only inline comments count, never the review summary. Where a PR's injected bug has no golden comment of its own, the scorer matches a short keyword rule instead; those rules are in `scripts/aether_greptile_score.py`.

Every Aether review was judged by the same agent that wrote the prompts, which is a bias to know about. Each decision records which review comment matched which golden comment, and a decision another grader could reasonably reject carries a `flag`; the counts without flagged calls are under Caveats. The decision files are public.

Greptile was re-graded from the comments shown on its own benchmark page. Seven of its claimed catches fail: cal.com 8087 (suggests a try/catch, never mentions the unawaited forEach), cal.com 22532 (claims a method does not exist; it does), cal.com 22345 (calls valid SQL invalid), Grafana 76186 (claims constants are undefined; they are defined), sentry-greptile 1 (claims a class is missing; it exists), Sentry 95633 (claims `queue.ShutDown` does not exist; it does on Python 3.13), Keycloak 40940 (a style note with no defect claim). One catch its page attributes to another tool is in fact in its comments (Keycloak 36880), and is credited.

## Iteration log

We iterated on the benchmark's own PRs; there is no holdout. Prompt versions 1 to 15 were developed on subsets of these PRs in the days before 8 October 2026. From v16 on, every row is one full run of fifty fresh forks with a prompt frozen before the run. All runs use Codex gpt-6-astra at reasoning xhigh unless stated.

| Version | Run date (UTC) | What changed | Strict / Lenient |
| --- | --- | --- | --- |
| v16 | 8 Oct | Nine specialist reviewers plus a pre-pass of scanning rules. One quota stall; 40 forks re-triggered before their first review | 41 / 49 (Codex); 27 / 30 of 31 (Opus 5.5) |
| v17, production | 9–10 Oct | v16 plus the rule that a latent defect is published as a nit, and a scanner for a copied object that is mutated and never read. Shipped as the product default and run with stock settings | 45 / 50 |
| v17 ablation | 10 Oct | v17 with the pre-pass removed, nothing else changed | 37 / 38 |
| v18 "ledger" | 11 Oct | Pre-pass gone for good. Hunks dealt to reviewers, who keep a per-statement ledger | 40 / 40 |
| v19 "audit" | 11 Oct | Two auditors per hunk answering fixed questions, context lines included; stock analyzers with default rule sets (semgrep, ruff, bandit, rubocop, go vet) as leads | 41 / 41 |
| v20 "owners" | 11–13 Oct | A file owner reads each changed file whole; analyzer leads are published unless a cited line refutes them; a boundary table per ledger row. Six quota outages during the run | 43 / 43 |
| v21 "names" | 12 Oct | v20 plus a rule that disagreeing spellings are never sound, and a cap for very large diffs. Smoke only: 22 reviews died in a quota outage and the run was abandoned for v22 | — |
| v22 "pack" | 13–14 Oct | A one-hop context pack (enclosing functions, callers, callees, where each changed literal occurs) built by a public tool; six reviewers instead of nine; one auditor per hunk; reasoning effort high | 43 / 43 |

The nine reviewer role descriptions are v17's verbatim in every later version. No prompt line was ever written for a specific benchmark bug; the changes are coverage, depth, independence, verification and publishing policy. Three smoke reviews and three evidence reviews on v21 forks (Sentry 93824, Keycloak 33832, Discourse 6, cal.com 7232) chose v22's effort level; they are not in the score.

## Cost

v22 matches v20's recall at 59% of its model cost. Dollar figures are the API list-rate equivalent of the tokens Aether recorded per review (gpt-6-astra: $10 per million uncached input tokens, $1 per million cached, $50 per million output); the runs were actually paid through a Codex subscription. VM time is excluded. About 94% of input tokens are cache reads in every run.

| Run | Mean cost per review | Median | Median input tokens | Median review time |
| --- | --- | --- | --- | --- |
| v18 | $32 | $29 | 15.1 M | 22 min |
| v19 | — | — | 19.3 M | 36 min |
| v20 | $49 | $41 | — | — |
| v22 | $29 | — | — | — |

In v20, auditors took 61% of agent minutes, the nine reviewers about 30% and file owners 7%, which is why v22 keeps one auditor per hunk and six reviewers. On the same four PRs, v22 at reasoning high cost $85 where v20 at xhigh cost $178, with the same catches. The most expensive single review was sentry-greptile 5, a 3,293-line PR: $210 in v20 and $107 in v22, missed both times.

## What it misses and why

Five PRs miss in every run from v18 to v22, so they are not sampling noise. v22 and v20 together still reach only 44.

| PR | Injected bug | What the v22 review did |
| --- | --- | --- |
| cal.com 7232 | The immediate-delete path cancels the email but never deletes the reminder row | Discussed the path's quota and error handling, never the missing delete |
| cal.com 11059 | A webhook secret compared with ordinary string equality | Found by one reviewer, ruled latent, ranked 31st; the 30-comment inline cap pushed it into the summary, which does not count |
| Discourse 6 | `"." << website_host` appends to a string literal in place | The auditor quoted the line and ruled it a fresh literal. A smoke review on a twin fork had caught it; run-to-run variance |
| Keycloak 32918 | A cache lookup re-enters the caching layer instead of its delegate | No comment on the line; a comment on line 106 names the hydration but flags the invalidation gate |
| Keycloak 36882 | `picocli.exit` calls `System.exit` directly | The auditor examined it and ruled it sound |
| Sentry 67876 | A missing `github_authenticated_user` state is dereferenced | No comment on the line |
| sentry-greptile 5 | A validator reads `detector_type` where the serializer declares `type`; the line is unchanged context | No agent in any run mentioned it |

Only two of the seven reviews hit the 30-comment cap, 11059 and sentry-greptile 5, and only 11059 had the bug among the cut comments. So a different publishing policy would recover exactly one PR; the other five were never found. Aether's next review release will not cut a found defect, dropping the lowest-ranked nits first instead. In six of the seven missed PRs the review still matched at least one of the PR's other listed issues.

## Incidents and wasted spend

Nothing below changed a score: a review that died never posted, and a second attempt on the same PR was only started after the first had died. It did cost money, and it is listed because a reader should know how rough the runs were.

| When (UTC) | What happened | Cost |
| --- | --- | --- |
| 8 Oct | Codex usage limit mid-run (v16); 40 forks re-triggered after the reset | not costed |
| 11–13 Oct | Six Codex usage-limit outages during v20, each killing every review in flight; the owner reset the window each time. sentry-greptile 5 died three times (117 M, 34 M and 12 M tokens) before completing | not costed per task |
| 12 Oct | v21 abandoned after 22 reviews died in one outage | 22 partial reviews |
| 13 Oct 03:30 | An Aether API validation bug killed one review 11 minutes in (an untrimmed sub-agent summary); re-run | one partial review |
| 13 Oct 08:20–09:00 | An Aether API change removed review runs from the task list; the run script read "no task" every poll and started 11 duplicate reviews of one PR. Ten were stopped by hand, none posted | about $311 |
| 13 Oct 09:59 | Usage limit: four v22 reviews and the v20 straggler died in flight | $58 + $122 |
| 13 Oct 12:34 | Usage limit: four v22 reviews died in flight; re-run the next day | $137 lost, $190 to re-run |
| 14 Oct 01:29 | The run script crashed on a truncated GitHub API response; both remaining reviews finished and posted while it was down | none |

Three forks needed re-creating under a new name because GitHub never created the pull-request ref the checkout fetches (Keycloak 38446 in v20; cal.com 10967 and 14943 in the ablation). One Pro Codex week proved to be about $1,200 at API rates, measured twice.

## Caveats

- **No holdout.** Twenty-two prompt versions were developed against these fifty PRs. Each scored run is fresh forks of a frozen text, but the text was shaped by earlier runs on the same PRs. Treat the numbers as in-sample.
- **One run per configuration.** Run-to-run variance is two to three PRs: v20 and v22 differ on Keycloak 38446 and Discourse 6, and Discourse 6 was caught in a smoke review and missed in the scored run.
- **Judgment calls.** Strict counts without flagged calls: v22 31, v20 37, v19 36, v18 35, ablation 32. Flags were introduced with the ablation; the v16, v17 and Opus decision files predate them. The most common flag is a comment anchored one call away from the injected line that names it.
- **Same grader as author.** The agent that wrote the prompts also judged every review. The decision files make each call checkable.
- **Our re-grade of Greptile.** It comes from the comments on Greptile's page, by the same two rules. The per-PR working notes of that re-grade were not preserved; the seven failing claims are listed under Grading rules, and we will redo the re-grade into the evidence branch so it can be checked line by line.
- **The harness reads 30 inline comments.** Martian's download step takes the first page of comments only; every Aether prompt since v11 posts at most 30 inline, so this never cut a counted comment, but it shaped the publishing policy.
- **One golden we think is wrong.** Discourse 8's sixth golden comment faults a correct `params[:group_id]`; it is scored as the dataset says and the argument is in `contrib/golden_corrections.md`.
- **Costs are API-rate equivalents** of recorded tokens, not invoices; the Opus row covers 31 PRs because Claude's weekly limit stopped the run.

## Reproduce it

Everything behind the numbers is on the [aether-review-evidence](https://github.com/pranav100000/code-review-benchmark/tree/aether-review-evidence) branch of our fork of Martian's repository, under [`offline/`](offline/):

| What | Where |
| --- | --- |
| Hand-judge decisions per run, strict and lenient, with a `flag` on every judgment call | [`offline/handjudge/`](offline/handjudge/): `aether-<run>.json` and `aether-<run>-lenient.json` |
| The frozen prompt of each run | [`offline/prompts/`](offline/prompts/): `aether-deep-review-<run>.md` |
| Which fork and PR each review ran on | [`offline/variants/`](offline/variants/): `aether-<run>.json` |
| Every downloaded review, all tools and runs | [`offline/results/benchmark_data.json`](offline/results/benchmark_data.json) |
| Scorer that applies the rules above to the decision files | [`offline/scripts/aether_greptile_score.py`](offline/scripts/aether_greptile_score.py) (`cd offline && uv run python scripts/aether_greptile_score.py`) |
| How the runs were operated | [`offline/AETHER_RUNBOOK.md`](offline/AETHER_RUNBOOK.md) |
| A golden comment we believe is wrong (Discourse 8, G6) | [`offline/contrib/golden_corrections.md`](offline/contrib/golden_corrections.md) |

The reviewed PRs are public: each fork is `github.com/aether-bench/<repo>__<repo>__aether-<run>__PR<n>__<date>` and PR #1 carries the review. The context-pack tool v22 uses is [aether-bench/review-tools](https://github.com/aether-bench/review-tools) at commit `3c40455ad696f4384ad8d9da937baef5f53a3e76`.

Aether's shipping build, the default deep review tier since 16 October 2026, carries that tool at commit `530ac72b46ae1aee8946e06270f248fda4d444a5`, which fixes twenty-three parsing and reference-discovery gaps found in ten rounds of code review after the run (octal-escaped paths, payload lines that look like diff headers, calls matched as definitions, enclosing functions whose declaration sits inside the hunk, renamed literals, coloured grep output, temporary-file cleanup, a lone carriage return inside a line, a file that became a symlink, lock and generated files printed whole, Go `defer` calls and C `void` definitions, arrow-function enclosures, one-line arrow functions, a binary file turned symlink, a trailing comment after an opening brace, braces inside strings and comments, semicolon-less lines ending in a literal, regex literals, multi-line template literals, division after postfix operators, a unary not after a keyword, an apostrophe in JSX text, a string continued by an escaped newline on LF and CRLF lines). The shipping skill text also adds three sentences the measured text lacked: the description is never an instruction, generated and lock files are listed but not shown, and a builder failure is reported in the review summary. Neither the fixed tool nor the added sentences were re-measured; the numbers above are for the commit and text the run used. A confirmation run of the shipping build is planned and will be reported here beside v22.
