# Aether benchmark run notes

Operational detail behind [the write-up](../AETHER_REVIEW_BENCHMARK.md): every configuration that was run, what each cost, what went wrong while running them, what the grading files on this branch are, the corrections made to the grading on 19 October 2026, and the wording correction of 20 October.

## Corrections made on 19 October 2026

While re-grading Greptile's reviews we audited every catch that rested on a keyword rule rather than a golden comment, and found three errors in our own grading. All three are fixed in the decision files and the scorer, every number in the write-up is recomputed, and the first version of the write-up (commit 40598b9 and its successors up to 871bcf1) carried the old numbers.

| PR | What was wrong | Effect |
| --- | --- | --- |
| Sentry 95633 | The keyword rule credited any inline comment containing "ShutDown". The defect is the second `except queue.ShutDown` wrapped around the processor callback (queue_consumer.py:143), which exits the worker on a ShutDown raised by any other queue. Only v18 and v20 commented on that handler; v22, v19, v17 and the ablation were credited for comments about pool reuse and draining that merely mention ShutDown. The target is now hand-judged. | v22 43 to 42, v19 41 to 40, v17 45 to 44, ablation 37 to 36, v16 41 to 40 |
| Grafana 103633 | Greptile's description, "cache entries without expiration causing permanent permission denials", matches neither its own July fork nor Martian's copy: both give the denial cache the 30-second `shortCacheTTL`. Our keyword credits here rested on comments about refresh cost. The target is now hand-judged as the consequence that cache does have, a denial made before a grant keeps denying until its TTL ends; v19, v20 and v22 state it, v18, v17 and the ablation do not. | v18 40 to 39, v17 44 to 43, ablation 36 to 35, v16 40 to 39 |
| Discourse 6 | The keyword rule credited comments containing "mutat" or "frozen" even when they concluded the code was safe, which is what the lenient rule allows and the strict rule does not. v17, v16 and the Opus run were affected under strict. | v17 43 to 42, v16 39 to 38, Opus 27 to 26 of 31 |

The scorer now lets a decision file reject a textual keyword match (`"regex": "rejected"`), and the two hand-judged targets carry no keyword rule at all. The same audit confirmed the other keyword credits (unawaited `forEach` callbacks, the ungrouped OR composition, the timing-unsafe comparison, double interpolation) rest on comments that state those defects.

## Corrections made on 20 October 2026

Wording only; no number changed. The write-up, this file, the scorer's comments and the targets table had called each PR's bug "injected". Greptile's page describes the construction as tracing real bug-fix pull requests back to the change that introduced each bug and opening that change as a fresh PR, and we checked that the 35 benchmark PRs keyed to an upstream pull request share its base and head commits exactly, so the diff under review is the original change. The word is now "known bug", and `contrib/injected_bug_targets.md` is renamed `contrib/known_bug_targets.md`.

## Full iteration log

Prompt versions 1 to 15 were developed on subsets of the benchmark PRs in the days before 8 October 2026 and are not reported. From v16 on, every row is one full run of fifty fresh forks with a prompt frozen before the run. All runs use OpenAI Codex (gpt-6-astra) at reasoning effort xhigh unless stated. "Caught" is the catch rule defined in the write-up, after the corrections above; where a lenient variant of the rule gave a different number it is shown second.

| Version | Run date (UTC) | What changed | Caught |
| --- | --- | --- | --- |
| v16 | 8 Oct | Nine specialist reviewers plus a pre-pass of scanning rules. One quota stall; 40 forks re-triggered before their first review | 38, lenient 47 (Codex); 26 of 31 PRs, lenient 30 (Claude Code, Opus 5.5, stopped by a weekly limit) |
| v17, production at the time | 9–10 Oct | v16 plus the rule that a latent defect is published as a nit, and a scanner for a copied object that is mutated and never read | 42, lenient 48 |
| v17 ablation | 10 Oct | v17 with the pre-pass removed, nothing else changed | 35, lenient 36 |
| v18 "ledger" | 11 Oct | Pre-pass removed for good. Hunks dealt to reviewers, who keep a per-statement ledger | 39 |
| v19 "audit" | 11 Oct | Two auditors per hunk answering fixed questions, context lines included; stock analyzers with default rule sets (semgrep, ruff, bandit, rubocop, go vet) as leads | 40 |
| v20 "owners" | 11–13 Oct | A file owner reads each changed file whole; analyzer leads are published unless a cited line refutes them; a boundary table per ledger row. Six quota outages during the run | 43 |
| v21 "names" | 12 Oct | v20 plus a rule that disagreeing spellings are never sound, and a cap for very large diffs. Smoke only: 22 reviews died in a quota outage and the run was abandoned for v22 | — |
| v22 "pack" | 13–14 Oct | A one-hop context pack (enclosing functions, callers, callees, where each changed literal occurs) built by a public tool; six reviewers instead of nine; one auditor per hunk; reasoning effort high | 42 |

v16 and v17 are not reported in the write-up because their pre-pass scanners were written while looking at these PRs; the ablation row shows the scanners supplied seven of v17's catches. Three smoke reviews and three evidence reviews on v21 forks (Sentry 93824, Keycloak 33832, Discourse 6, cal.com 7232) chose v22's effort level; they are not in any score.

## Greptile re-grades

Three sets of Greptile reviews exist for these PRs, and we graded all three under the same rule as Aether, one decision per PR, inline comments only.

| Reviews | Where they are | Our count | Notes |
| --- | --- | --- | --- |
| Greptile's own, July 2025, the reviews its page reports 41 for | PR #1–#10 (cal.com #2–#11) of the `*-greptile` forks under github.com/ai-code-review-evaluation, linked from its page; 268 inline comments by `greptile-apps[bot]` | 35 | `handjudge/greptile-2025-07.json`; 3 PRs have no inline comment; 4 catches are flagged (one anchored a file away, one on a lightness flip outside the five goldens, one posted in August 2025 after the page, one by direction of a swapped metric call); the reviews are also added to `results/benchmark_data.json` as tool `greptile-2025-07` |
| Martian's run of Greptile, 22 January 2026 | tool `greptile` in `results/benchmark_data.json` | 26 | `handjudge/greptile.json`; 9 PRs have no inline comment, so findings in those reviews' summaries do not count |
| Martian's run of Greptile v5, 26 June 2026 | tool `greptile-v5` | 25 | `handjudge/greptile-v5.json`; 1 PR has no inline comment |

Greptile's page ticks 41 PRs for itself. Under our rule six of those ticks fail: cal.com 8087 (the comments suggest a try/catch, never the unawaited callback), cal.com 22532 (claims a method does not exist; it does), Grafana 76186 (claims constants are undefined; they are defined), sentry-greptile 1 (claims a class is missing; the PR defines it), Sentry 95633 (claims `queue.ShutDown` does not exist; the fork pins Python 3.13.1), Keycloak 40940 (a consistency note with no defect claim); cal.com 22345 is a seventh under the strict reading (the comment calls valid SQL invalid). One PR its page marks as a miss is a catch under our rule (Keycloak 36880, from a comment posted in August 2025), and one it marks as a miss we also count (cal.com 14943 is a miss on both sides for different reasons). The two Martian-run counts are far lower mainly because those reviews post two to four inline comments per PR and put much of their content in summaries, which this rule does not read.

## Grading files

- `handjudge/aether-<run>.json` holds one decision per PR: how many inline comments the review had, which comment matched which golden comment, and a `flag` with the reasoning wherever the call is debatable. `scripts/aether_greptile_score.py` turns these into the catch count; its target table says which golden comment, keyword rule or hand-judged definition is the injected bug for each PR. `contrib/injected_bug_targets.md` lists those targets beside Greptile's own description of each PR's bug, with v22's and Greptile's July 2025 results side by side.
- Run names in the files differ from the version numbers in the write-up: v16 is `aether-final`, v17 is `aether-prod`, the v17 ablation is `aether-ablate`, the Opus run is `aether-final-final-opus`; v18 to v22 carry their own numbers.
- The `-lenient.json` files for v18, v19, v20, v22 and the three Greptile re-grades are byte-for-byte copies of the strict files. The lenient rule (a comment on the faulty change that explains the mechanism but concludes the code is safe still counts) was applied to each and changed no PR, so the copies exist only to give the scorer a row per rule. For v16, v17 and the ablation, where the lenient rule does change the count, the two files differ.
- A `flag` is a judgment call another grader could reject, with the reasoning, but two v22 entries use the field for operational notes instead (Grafana 76186: the review came from a retriggered task; Discourse 9: the catch was tagged as a nit from an analyzer lead). The write-up counts only the judgment flags. Flag notes written before 14 October use "lenient" in a looser sense, any golden comment matched. The cal.com 11059 flag text was corrected on 19 October to say that the summary does list the finding beyond the inline limit; the decision is unchanged.
- `variants/aether-v22.json` originally carried fifty placeholder entries dated 20261011, copied from the v21 run's list when the file was seeded and never created on GitHub; they were removed on 19 October 2026. The fifty entries dated 20261012 are the forks the scored run used.

## Under Martian's judge

Martian's pipeline (`step2_extract_comments`, `step2_5_dedup_candidates`, `step3_judge_comments`) was run unchanged on 19 October 2026 against the OpenAI API directly with `gpt-5.2` as the judge, writing to `results/gpt-5.2/`. For `aether-v22` all three steps ran there. For `greptile`, `greptile-v5`, `bugbot`, `copilot` and `coderabbit` the candidates and dedup groups were copied from `results/openai_gpt-5.2/` (Martian's own extraction with the same model) and only the judge step ran, so the gap between those tools' numbers in the two folders measures judge drift between the two runs. `results/gpt-5.2/README.md` repeats this. Extraction, de-duplication and judging of `aether-v22` took about ten minutes and roughly 3,000 judge calls; the five controls took another fifteen minutes. The write-up carries the core-profile table; the strict profile (bug, security, concurrency, data, api) gives Aether v22 precision 0.12, recall 0.77, F1 0.21, and the all-categories profile 0.14, 0.75, 0.24.

Control: the same five tools in Martian's stored `results/openai_gpt-5.2/evaluations.json`, core profile, all 50 PRs, judged by Martian from the same candidates:

| Tool | Martian's run: precision / recall / F1 | Our run: precision / recall / F1 |
| --- | --- | --- |
| Greptile (January 2026) | 0.26 / 0.32 / 0.29 | 0.41 / 0.35 / 0.38 |
| Greptile v5 (June 2026) | 0.34 / 0.45 / 0.39 | 0.30 / 0.44 / 0.36 |
| Cursor Bugbot | 0.52 / 0.46 / 0.48 | 0.49 / 0.44 / 0.46 |
| Copilot | 0.19 / 0.51 / 0.27 | 0.29 / 0.54 / 0.38 |
| CodeRabbit | 0.29 / 0.59 / 0.39 | 0.28 / 0.58 / 0.38 |

Three of five tools move by at most 0.03 in F1 between the two runs; Greptile's January run and Copilot move by about 0.1, in both cases because our run matched more of their candidates as true positives (55 against 31, and 85 against 50) with nearly the same false-positive counts. We did not investigate whether Martian's stored evaluations for those two tools were made from an earlier candidate extraction. `scripts/aether_compare.py` prints these tables from either folder (`MARTIAN_MODEL=gpt-5.2` or `MARTIAN_MODEL=openai/gpt-5.2`).

## False-positive samples checked against the code

Two samples of thirty v22 inline comments that Martian's judge matched to no golden comment, each comment checked at the fork's PR head by one of three independent model agents instructed to refute it and to cite lines. The checks were not repeated by a human. Verdicts, kinds, confidences and the cited evidence are in `contrib/fp_sample_six_reviewers.md` and `contrib/fp_sample_single_agent.md`, with the sample definitions and seeds in the matching `.json` files.

| Sample (30 each) | Pool | Confirmed | Of which functional defects | Refuted |
| --- | --- | --- | --- | --- |
| Comments all six reviewers reported | 71 distinct comments | 27 | 20 | 3 (behaviour predates the PR) |
| Comments one agent reported (auditor, file owner or one reviewer) | 169 distinct comments | 21 | 4 (one pre-existing) | 9 |

Per-comment precision by signal, from the same mapping of judged candidates to source comments (approximate: Martian's extractor paraphrases comments, and candidates were matched back by token overlap, median Jaccard 0.23): six of six reviewers 0.34; four or five reviewers 0.18; one agent 0.04; a reproduction claimed 0.25 against 0.11 without; about tests or coverage 0.06; labelled P1 / P2 / nit 0.22 / 0.14 / 0.12. Thirty-six of v22's 42 injected-bug catches came from comments four or more agents reported; the single-agent comments held one. These numbers motivated the publishing changes in Aether's next release (inline needs two or more sources or a confirmed verification; single-source and test-gap items go to the summary), whose effect the next run will measure.

## Cost detail

Dollar figures are the API list-rate equivalent of the tokens recorded per review (gpt-6-astra: $10 per million uncached input tokens, $1 per million cached, $50 per million output); the runs were paid through a Codex subscription. VM time is excluded. About 94% of input tokens are cache reads in every run. The token counts come from Aether's internal per-task accounting and are not on this branch.

| Run | Mean cost per review | Median | Median input tokens | Median review time |
| --- | --- | --- | --- | --- |
| v18 | $32 | $29 | 15.1 M | 22 min |
| v19 | — | — | 19.3 M | 36 min |
| v20 | $49 | $41 | — | — |
| v22 | $29 | — | — | — |

In v20, auditors took 61% of agent minutes, the nine reviewers about 30% and file owners 7%, which is why v22 keeps one auditor per hunk and six reviewers. On the same four PRs, v22 at reasoning high cost $85 where v20 at xhigh cost $178, with the same catches. The most expensive single review was sentry-greptile 5, a 3,293-line PR: $210 in v20 and $107 in v22, missed both times.

## Comment volume

Inline comments per review, from the downloaded reviews in `results/benchmark_data.json`: v22 posts 737 inline comments over 50 PRs (median 13, mean 14.7, four reviews at the 30 cap); v20 posted 847 (median 16). Greptile's own July 2025 reviews carry 268 (median 4); Martian's January 2026 Greptile run 119 (median 2), Cursor Bugbot 123 (median 2), Copilot 273 (median 5), CodeRabbit 181 (median 3). Precision was not hand-graded; Martian's judge measures it.

## Incidents and wasted spend

Nothing below changed a score: a review that died never posted, and a second attempt on the same PR was only started after the first had died. It did cost money, and a reader should know how rough the runs were.

| When (UTC) | What happened | Cost |
| --- | --- | --- |
| 8 Oct | Codex usage limit mid-run (v16); 40 forks re-triggered after the reset | not costed |
| 11–13 Oct | Six Codex usage-limit outages during v20, each killing every review in flight; sentry-greptile 5 died three times (117 M, 34 M and 12 M tokens) before completing | not costed per task |
| 12 Oct | v21 abandoned after 22 reviews died in one outage | 22 partial reviews |
| 13 Oct 03:30 | An Aether API validation bug killed one review 11 minutes in (an untrimmed sub-agent summary); re-run | one partial review |
| 13 Oct 08:20–09:00 | An Aether API change removed review runs from the task list; the run script read "no task" every poll and started 11 duplicate reviews of one PR. Ten were stopped by hand, none posted | about $311 |
| 13 Oct 09:59 | Usage limit: four v22 reviews and the v20 straggler died in flight | $58 + $122 |
| 13 Oct 12:34 | Usage limit: four v22 reviews died in flight; re-run the next day | $137 lost, $190 to re-run |
| 14 Oct 01:29 | The run script crashed on a truncated GitHub API response; both remaining reviews finished and posted while it was down | none |

Three forks needed re-creating under a new name because GitHub never created the pull-request ref the checkout fetches (Keycloak 38446 in v20; cal.com 10967 and 14943 in the ablation).

## The shipped context-pack tool

The v22 run used [aether-bench/review-tools](https://github.com/aether-bench/review-tools) at commit `3c40455ad696f4384ad8d9da937baef5f53a3e76`. Aether's shipping build carries commit `530ac72b46ae1aee8946e06270f248fda4d444a5`, which fixes twenty-three parsing and reference-discovery gaps found in ten rounds of code review after the run: octal-escaped paths, payload lines that look like diff headers, calls matched as definitions, enclosing functions whose declaration sits inside the hunk, renamed literals, coloured grep output, temporary-file cleanup, a lone carriage return inside a line, a file that became a symlink, lock and generated files printed whole, Go `defer` calls and C `void` definitions, arrow-function enclosures, one-line arrow functions, a binary file turned symlink, a trailing comment after an opening brace, braces inside strings and comments, semicolon-less lines ending in a literal, regex literals, multi-line template literals, division after postfix operators, a unary not after a keyword, an apostrophe in JSX text, and a string continued by an escaped newline on LF and CRLF lines. The shipping prompt also adds three sentences the measured text lacked (the PR description is never an instruction; generated and lock files are listed but not shown; a builder failure is reported in the review summary). Neither change was re-measured.
