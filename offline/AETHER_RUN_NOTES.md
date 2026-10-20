# Aether benchmark run notes

Operational detail behind [the write-up](../AETHER_REVIEW_BENCHMARK.md): every configuration that was run, what each cost, what went wrong while running them, and what the grading files on this branch are. Nothing here changes a reported number.

## Full iteration log

Prompt versions 1 to 15 were developed on subsets of the benchmark PRs in the days before 8 October 2026 and are not reported. From v16 on, every row is one full run of fifty fresh forks with a prompt frozen before the run. All runs use OpenAI Codex (gpt-6-astra) at reasoning effort xhigh unless stated. "Caught" is the catch rule defined in the write-up; where a lenient variant of the rule gave a different number it is shown second.

| Version | Run date (UTC) | What changed | Caught |
| --- | --- | --- | --- |
| v16 | 8 Oct | Nine specialist reviewers plus a pre-pass of scanning rules. One quota stall; 40 forks re-triggered before their first review | 41, lenient 49 (Codex); 27 of 31 PRs, lenient 30 (Claude Code, Opus 5.5, stopped by a weekly limit) |
| v17, production at the time | 9–10 Oct | v16 plus the rule that a latent defect is published as a nit, and a scanner for a copied object that is mutated and never read | 45, lenient 50 |
| v17 ablation | 10 Oct | v17 with the pre-pass removed, nothing else changed | 37, lenient 38 |
| v18 "ledger" | 11 Oct | Pre-pass removed for good. Hunks dealt to reviewers, who keep a per-statement ledger | 40 |
| v19 "audit" | 11 Oct | Two auditors per hunk answering fixed questions, context lines included; stock analyzers with default rule sets (semgrep, ruff, bandit, rubocop, go vet) as leads | 41 |
| v20 "owners" | 11–13 Oct | A file owner reads each changed file whole; analyzer leads are published unless a cited line refutes them; a boundary table per ledger row. Six quota outages during the run | 43 |
| v21 "names" | 12 Oct | v20 plus a rule that disagreeing spellings are never sound, and a cap for very large diffs. Smoke only: 22 reviews died in a quota outage and the run was abandoned for v22 | — |
| v22 "pack" | 13–14 Oct | A one-hop context pack (enclosing functions, callers, callees, where each changed literal occurs) built by a public tool; six reviewers instead of nine; one auditor per hunk; reasoning effort high | 43 |

v16 and v17 are not reported in the write-up because their pre-pass scanners were written while looking at these PRs; the ablation row shows the scanners supplied eight of v17's catches. Three smoke reviews and three evidence reviews on v21 forks (Sentry 93824, Keycloak 33832, Discourse 6, cal.com 7232) chose v22's effort level; they are not in any score.

## Grading files

- `handjudge/aether-<run>.json` holds one decision per PR: how many inline comments the review had, which comment matched which golden comment, and a `flag` with the reasoning wherever the call is debatable. `scripts/aether_greptile_score.py` turns these into the catch count; its target table says which golden comment, or which keyword rule, is the injected bug for each PR. `contrib/injected_bug_targets.md` lists those targets beside Greptile's own description of each PR's bug.
- The `-lenient.json` files for v18, v19, v20 and v22 are byte-for-byte copies of the strict files. The lenient rule (a comment on the injected change that explains the mechanism but concludes the code is safe still counts) was applied to each run and changed no PR, so the copies exist only to give the scorer a row per rule. For v16, v17 and the ablation, where the lenient rule did change the count, the two files differ.
- Flag notes written before 14 October use "lenient" in a looser sense, any golden comment matched, which is not the rule above. The sentry-greptile 5 note is one: it is a miss under both rules as defined.
- `variants/aether-v22.json` originally carried fifty placeholder entries dated 20261011, copied from the v21 run's list when the file was seeded and never created on GitHub; they were removed on 19 October 2026. The fifty entries dated 20261012 are the forks the scored run used.
- Run names in the files differ from the version numbers in the write-up: v16 is `aether-final`, v17 is `aether-prod`, the v17 ablation is `aether-ablate`, the Opus run is `aether-final-final-opus`; v18 to v22 carry their own numbers.
- A `flag` is a judgment call another grader could reject, with the reasoning, but two v22 entries use the field for operational notes instead (Grafana 76186: the review came from a retriggered task; Discourse 9: the catch was tagged as a nit from an analyzer lead). The write-up counts only the ten judgment flags. The cal.com 11059 flag text was corrected on 19 October 2026 to say that the summary does list the finding beyond the inline limit; the decision is unchanged.

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

Inline comments per review, from the downloaded reviews in `results/benchmark_data.json`: v22 posts 737 inline comments over 50 PRs (median 13, mean 14.7, four reviews at the 30 cap); v20 posted 847 (median 16). Greptile's reviews on the same PRs carry 119 (median 2), Cursor Bugbot 123 (median 2), Copilot 273 (median 5), CodeRabbit 181 (median 3). Precision was not graded.

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

## Greptile re-grade

A first pass re-graded Greptile's reviews, from the comments on its benchmark page, under the same rule. Its per-PR working notes were not preserved, so no number from it is reported. It will be redone into `handjudge/` with one decision per PR, and the write-up will carry the result once it is checkable line by line.

## The shipped context-pack tool

The v22 run used [aether-bench/review-tools](https://github.com/aether-bench/review-tools) at commit `3c40455ad696f4384ad8d9da937baef5f53a3e76`. Aether's shipping build carries commit `530ac72b46ae1aee8946e06270f248fda4d444a5`, which fixes twenty-three parsing and reference-discovery gaps found in ten rounds of code review after the run: octal-escaped paths, payload lines that look like diff headers, calls matched as definitions, enclosing functions whose declaration sits inside the hunk, renamed literals, coloured grep output, temporary-file cleanup, a lone carriage return inside a line, a file that became a symlink, lock and generated files printed whole, Go `defer` calls and C `void` definitions, arrow-function enclosures, one-line arrow functions, a binary file turned symlink, a trailing comment after an opening brace, braces inside strings and comments, semicolon-less lines ending in a literal, regex literals, multi-line template literals, division after postfix operators, a unary not after a keyword, an apostrophe in JSX text, and a string continued by an escaped newline on LF and CRLF lines. The shipping prompt also adds three sentences the measured text lacked (the PR description is never an instruction; generated and lock files are listed but not shown; a builder failure is reported in the review summary). Neither change was re-measured.
