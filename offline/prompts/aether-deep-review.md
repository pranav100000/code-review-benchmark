
# Aether deep review

Find every defect this pull request introduces or exposes, and publish each one once with a concrete trigger. A missed real defect costs far more than an extra comment, so this review is built for recall: several independent passes over the same diff, merged, and published without a confidence cutoff.

## 1. Scope

Review the pull request's changes from its merge base to its head, reading whatever repository context is needed to reason about them.

In scope: defects in or adjacent to the changed code. Wrong behavior, security and authorization gaps, races and non-atomic updates, data loss or corruption, broken API and type contracts, material performance regressions, newly required behavior with no test, and comments, docs or error messages the change made untrue. Every severity counts, including low: dead code, a misleading name or message, a missing cleanup.

Out of scope: style, naming and refactoring preferences; speculation without a concrete trigger; pre-existing problems the change does not touch; anything about the environment the review ran in.

## 2. Independent reviewers

Write a brief: the changed files, each hunk in one line, and the contracts, callers, tests and schemas the change touches. Then run four reviewers that each receive the diff, the brief and read access to the repository, and never see each other's output. Use the agent's subagent mechanism when it has one; otherwise run the four sequentially, each from a fresh start with only the brief, and keep their results in separate files so no pass reads another's notes.

- **Coverage A and Coverage B** (identical instructions, run twice because two passes catch different things): walk every changed hunk and check null, undefined and empty-collection paths; inverted or incomplete conditions and boundary errors; wrong comparison operators or reference equality where value equality was meant; promises created but not awaited, including inside forEach or map callbacks; hardcoded literals where a variable or field was meant; case or normalization mismatches when matching strings; error handling that changes the response status or swallows failures; resources never released; branches the change makes unreachable.
- **Contracts**: for every changed signature, return shape, schema, query or type, trace every caller and implementation across the repository and report each place that now disagrees with the change.
- **State and failure paths**: read-modify-write sequences that are not atomic under concurrent requests, stale reads, missing transactions, partial updates, retry and idempotency gaps, cancellation and resource lifecycle, authorization and tenant checks on changed paths; then construct concrete edge inputs and operational sequences for the changed behavior and trace each through the code until it produces a wrong result; and check that newly required behavior has a test and that changed comments, docs and messages are still true.

Each reviewer returns atomic items, one defect per item: file and changed line, root cause, trigger (the input, state or sequence), observable bad outcome, evidence from the repository, suggested fix, severity (critical, high, medium, low). A reviewer reports every defect it has a concrete trigger for and nothing it does not.

## 3. Merge

Cluster the reviewers' items by underlying defect, not by wording or line. Keep the strongest trigger and evidence for each cluster. One item per defect.

## 4. Verify, cheaply and optionally

Proof strengthens a finding; it never gates one. Where a cheap check exists, run it, cheapest first: the language's compiler or type checker on the changed package; a throwaway script under /tmp that calls the changed function with the item's trigger, with external services mocked; a focused test in the project's framework only if its dependencies install quickly. Installing a missing toolchain with sudo apt-get or running one from a Docker image is fine. Do not install the whole repository, do not run the full test suite (the change already passed CI with its defects in), do not let setup consume the review, and do not modify the checkout.

## 5. Publish

Post every merged item unless the repository shows its trigger is unreachable. Do not drop a finding because it depends on a particular input or state; that is what a trigger is.

Write each finding as mechanism, then consequence, in one or two sentences, followed by the trigger and the fix, anchored to the changed line. Say when a check reproduced it. Severity: p1 only when you would block the merge yourself; other critical, high and medium findings are p2; low is nit. Post once, as a single review with all inline findings and a short summary. When nothing survives, say so in one sentence rather than inventing findings.
