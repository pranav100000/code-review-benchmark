# Running Code Review Bench against Aether Review

Everything runs from this directory (`offline/`) on a Mac that has `gh` (logged in as an
aether-bench org admin) and the `aether` CLI (logged in to the Aether account that owns the
aether-bench GitHub App installation).

Fixed facts for this org:

| Item | Value |
|---|---|
| GitHub org | `aether-bench` |
| GitHub App installation id | `168675679` (`aether-agent`, all repos) |
| Reviews post as | `aether-agent[bot]` (type Bot, so the downloader keeps them with no code change) |
| Tool slug per run | `aether-r1`, `aether-r2`, ... (one slug = one leaderboard row) |

## Why the extra link step exists

Aether Review only fires for a repo that has a linked Aether project with a review trigger
on; the database default for every project is off. `step0_fork_prs` creates each repo and
opens its PR in the same breath, so the `opened` event arrives before any project exists.
`scripts/aether_link_and_trigger.py` therefore creates one project per fork, imports the repo
into it, enables the `aether review` comment trigger, pins the review agent, and posts the
`aether review` comment on PR #1. It is idempotent; rerun it after any failure.

## 1. Fork the PRs

```bash
export GITHUB_TOKEN=$(gh auth token)      # step0 reads only the env var, never .env
for f in cal_dot_com discourse grafana keycloak sentry; do
  uv run python -m code_review_benchmark.step0_fork_prs \
    --file golden_comments/$f.json --org aether-bench --name aether-r1
done
```

- Always pass `--file`. Single-URL mode names repos with four segments and step 1 never
  recognises them.
- Each PR is a full clone and full push of a 0.5 to 2 GB repo. Expect hours; disk use is a
  few GB at a time because each temp clone is deleted after its push.
- Failures are printed as `Error processing ...` and the loop continues. A failed PR can leave
  a half-made repo; delete it (`gh repo delete aether-bench/<name>`, needs the `delete_repo`
  scope: `gh auth refresh -h github.com -s delete_repo`) and rerun that file.

## 2. Link projects and trigger the reviews

```bash
uv run python scripts/aether_link_and_trigger.py --tool aether-r1 --installation-id 168675679 \
  --agent-type codex --model gpt-6-astra
```

Add `--dry-run` first to see which forks still lack a project. The agent and model are pinned
on every project so the run is reproducible. Forks whose PR #1 is not open yet are skipped, so
the script can run on a timer while step 1 is still forking (r1 used a 10-minute loop that
exits after the fork log prints `=== ALL DONE`; see `link_r1.log`).

Projects land in whichever Aether org the CLI key is pinned to. The r1 projects are in
pranav's personal org on purpose: team-org PR reviews are created with no creator and cannot
start until the owner decides whose credentials they run on
(`apps/api/github/pr_review_task_dispatcher.go`). To target a team org later, create an API key
while switched to that org in the web app and run the script with it in `AETHER_TOKEN`.

Wait until every PR has a review from `aether-agent[bot]`:

```bash
gh repo list aether-bench --limit 1000 --json name --jq '.[].name | select(contains("__aether-r1__"))' |
  while read r; do
    n=$(gh api repos/aether-bench/$r/pulls/1/reviews --jq '[.[] | select(.user.login=="aether-agent[bot]")] | length')
    echo "$n  $r"
  done
```

## 3. Download and judge

Judging needs an OpenAI-compatible endpoint in `.env`. To compare against the published
leaderboard rows, use the same judge model as the existing results folder:

```
MARTIAN_API_KEY=...
MARTIAN_BASE_URL=https://api.withmartian.com/v1
MARTIAN_MODEL=anthropic/claude-opus-4-5-20251101
```

```bash
uv run python -m code_review_benchmark.step1_download_prs --org aether-bench --output results/benchmark_data.json --tool aether-r1
uv run python -m code_review_benchmark.step2_extract_comments --tool aether-r1
uv run python -m code_review_benchmark.step2_5_dedup_candidates --tool aether-r1
uv run python -m code_review_benchmark.step3_judge_comments --tool aether-r1
uv run python analysis/benchmark_dashboard.py
open analysis/benchmark_dashboard.html
uv run python -m code_review_benchmark.step_speed_analysis --org aether-bench --tool aether-r1 --output results/speed_analysis.json
```

The dashboard shows the raw slug for tools missing from `TOOL_DISPLAY_NAMES` in
`analysis/benchmark_dashboard.py`; add `"aether-r1": "Aether Review"` there if you want a label.

## 4. Prompt iteration (reuses the r1 forks)

A comment-triggered review is keyed by the comment id, so every new `aether review` comment
starts a fresh task. Each variant opens a new PR per repo from the same branches (so the
reviewer sees no earlier bot comments), sets the project prompt and config, triggers, and
records the PR numbers in `variants/<slug>-<variant>.json`:

```bash
uv run python scripts/aether_variant_run.py --tool aether-r1 --variant v2 --prompt-file prompts/v2-coverage.md
# wait for the reviews, then
uv run python -m code_review_benchmark.step1_download_prs --org aether-bench --output results/benchmark_data.json \
  --tool aether-r1 --variants-file variants/aether-r1-v2.json
uv run python -m code_review_benchmark.step2_extract_comments --tool aether-r1-v2
uv run python -m code_review_benchmark.step2_5_dedup_candidates --tool aether-r1-v2
uv run python -m code_review_benchmark.step3_judge_comments --tool aether-r1-v2
uv run python scripts/aether_compare.py --tools aether-r1 aether-r1-v2 augment --profile core --by-repo
```

Pick variants on the TUNE half and confirm on HOLDOUT (every second PR per repo) so the
shipped prompt is not fitted to the 50 PRs. Only start a variant after the previous one's
reviews are downloaded: closing a PR while its review task is still running is untested.
The final publishable number for the winning prompt is a fresh fork run under a new slug
(section 1), with that prompt shipped as the product default.

## 5. Scoring without the paid judge

Until the final confirmation run, variants are scored by hand with the same rule the LLM judge
uses (does the candidate describe the same underlying issue as the golden comment?):

```bash
uv run python -m code_review_benchmark.step1_download_prs --org aether-bench --output results/benchmark_data.json \
  --tool aether-r1 [--variants-file variants/aether-r1-<variant>.json]
uv run python scripts/aether_hand_judge.py worksheet --tool <tool name> [--repo discourse]
# write decisions to handjudge/<tool name>.json, then
uv run python scripts/aether_hand_judge.py score --tool aether-r1 --tool <tool name>
```

Decisions record, per PR, which golden matched which inline finding and the number of distinct
findings; the summary body is not counted as a candidate because the real pipeline dedups it
against the inline comments. Re-run step 1 with `--force --tool <tool>` after late reviews post.

Fork integrity: a fork's PR #1 must have head branch `pr-<n>`. Dependabot opens PRs in forks, and
if step0 dies between pushing and creating the PR, Dependabot's PR becomes #1. All three scripts
refuse such a repo; delete it and re-fork that golden file.

## Notes

- This is a self-run result. Leaderboard inclusion additionally needs 600 to 1,000 public
  reviewed PRs across many orgs.
- Each review is a fresh Aether task on one PR. There is no cross-repo memory to reset.
- Reviews spend Aether credits: each one boots a VM and clones the PR's repo. If the org is
  out of credits the delivery is set aside and no review is posted.
- `aether-review-bench` in the org is an empty repo from an earlier probe; the pipeline
  ignores it because its name does not match the fork pattern.
