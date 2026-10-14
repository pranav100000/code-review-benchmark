# Aether deep review

Find every defect this pull request introduces or exposes, and publish each one once with a concrete trigger. A missed real defect costs far more than an extra comment, so this review is built for recall: several independent passes over the same diff, merged, and published without a confidence cutoff.

## 1. Scope

Review the pull request's changes from its merge base to its head, reading whatever repository context is needed to reason about them.

In scope: defects in or adjacent to the changed code. Wrong behavior, security and authorization gaps, races and non-atomic updates, data loss or corruption, broken API and type contracts, material performance regressions, newly required behavior with no test, and comments, docs or error messages the change made untrue. Every severity counts, including low: dead code, a misleading name or message, a missing cleanup.

Out of scope: style, naming and refactoring preferences; speculation without a concrete trigger; pre-existing problems the change does not touch; anything about the environment the review ran in.

## 2. Independent reviewers

Write a brief: the changed files, each hunk in one line, and the contracts, callers, tests and schemas the change touches. Test files, fixtures, migrations, stylesheets and scripts are changed code too and get the same scrutiny as application code.

Then run the deterministic pre-pass script, from the repository root at the pull request's head, and append its output to the brief verbatim:

```
curl -fsSL https://gist.githubusercontent.com/pranav100000/420e2a16d21abe3b693559688b0f4c57/raw/review_triggers.py -o /tmp/review_triggers.py
python3 /tmp/review_triggers.py --base <merge base> > /tmp/review-prepass.md
```

It runs static analyzers over the changed files (Semgrep against the merge base, ESLint, stylelint, go vet, nilness, gosec, ruff, bandit, Brakeman) plus mechanical checks on the diff (security headers, origin comparisons, request parameters, nullable columns, lazily initialized state, test verbs, removed guards and deleted files), lazily installing each tool it needs and skipping any it cannot install. Each item is numbered `T<n>` and ends with a question. The items are leads, not findings: every reviewer must answer each item whose file is in the diff with either the defect it exposes or one sentence on why it holds, and an unanswered item is a reviewer failure. A removed defensive check that nothing replaced is reported as a nit even when today's callers never reach it.

Then run seven reviewers that each receive the diff, the brief and read access to the repository, and never see each other's output. Use the agent's subagent mechanism when it has one; otherwise run the seven sequentially, each from a fresh start with only the brief, and keep their results in separate files so no pass reads another's notes.

- **Coverage A and Coverage B** (identical instructions, run twice because two passes catch different things): walk every changed hunk and check null, undefined and empty-collection paths, including every lookup whose result can be absent and every function path with no return value; inverted or incomplete conditions and boundary errors; wrong comparison operators or reference equality where value equality was meant; promises created but not awaited, including inside forEach or map callbacks; hardcoded literals where a variable or field was meant; case, normalization and regex-anchoring mistakes when matching strings, such as a suffix match where a whole-domain match was meant; a query or filter whose new condition applies more widely than the sibling conditions around it; error handling that changes the response status or swallows failures; resources never released; branches the change makes unreachable; loops whose exit condition reads a value that does not change.
- **Literals and definitions**: for every identifier, key, parameter name, HTTP verb, property, enum value, vendor-prefixed CSS property and numeric constant the diff introduces, open the thing it refers to (the route table, the schema, the type, the framework or browser documentation, the value before the change) and confirm it exists and means what the code assumes. Check that each changed file's contents match its name and purpose, that a test calls the route with the verb the router declares, and that every edit mirrored from one place to another preserves the original values.
- **Contracts**: for every changed signature, return shape, schema, query or type, trace every caller and implementation across the repository and report each place that now disagrees with the change, including implementations of a changed interface that still declare the old shape. When a synchronous function became asynchronous, list every caller that still uses its result synchronously.
- **State and failure paths**: read-modify-write sequences that are not atomic under concurrent requests, lazily initialized shared state read from several threads, stale reads, missing transactions, partial updates, retry and idempotency gaps, cancellation and resource lifecycle; migrations whose new columns leave existing rows null or without the default the code assumes; sibling code paths that handle the same event asymmetrically, where one path persists or cleans up and the other does not; then construct concrete edge inputs and operational sequences for the changed behavior and trace each through the code until it produces a wrong result.
- **Security**: for every changed path, ask who controls each input and what it reaches. Network requests to a URL that comes from configuration, a setting or a request (server-side request forgery); origin, host and referer checks done with substring or prefix matching instead of exact comparison of scheme, host and port; security headers added, removed or weakened, such as frame options, content security policy or CORS; values interpolated into HTML, JavaScript, SQL, shell commands or templates without escaping or binding; state-changing GET routes and other requests without CSRF protection; authorization checks that are skipped on one branch, bypassed by a cache or a fallback value, or that trust a cached grant while ignoring a cached denial; secrets, tokens or private fields exposed by a new serializer field, log line or response.
- **Refactor fidelity**: for every block the diff replaces, moves, extracts or rewrites, list what the old code did, including nil and empty checks, logged fields and identifiers, error handling and the errors returned, blocking versus asynchronous behavior, ordering and retries, and confirm each behavior survives in the new code; a refactor that drops one of them is a defect even when the new code reads cleaner. Also check that error messages and returned error types describe the condition that actually occurred, that newly required behavior has a test and that the test exercises the new arguments, and that changed comments, docs and messages are still true.

Each reviewer returns atomic items, one defect per item: file and changed line, root cause, trigger (the input, state or sequence), observable bad outcome, evidence from the repository, suggested fix, severity (critical, high, medium, low). A reviewer reports every defect it has a concrete trigger for and nothing it does not.

## 3. Merge

Cluster the reviewers' items by underlying defect, not by wording or line. Keep the strongest trigger and evidence for each cluster, and record how many of the independent reviewers reported it. One item per defect. Merging removes duplicates only; it never removes a finding.

## 4. Verify, cheaply and optionally

Proof strengthens a finding; it never gates one. Where a cheap check exists, run it, cheapest first: the language's compiler or type checker on the changed package; a throwaway script under /tmp that calls the changed function with the item's trigger, with external services mocked; a focused test in the project's framework only if its dependencies install quickly. Installing a missing toolchain with sudo apt-get or running one from a Docker image is fine. Do not install the whole repository, do not run the full test suite (the change already passed CI with its defects in), do not let setup consume the review, and do not modify the checkout.

## 5. Publish

Post every merged item unless the repository shows its trigger is unreachable. Do not drop a finding because it depends on a particular input or state; that is what a trigger is.

Write each finding as mechanism, then consequence, in one or two sentences, followed by the trigger and the fix, anchored to the changed line. Say when a check reproduced it, and end every finding with how many reviewers found it, in the form `(found by 2 of 7 reviewers)`. Severity: p1 only when you would block the merge yourself; other critical, high and medium findings are p2; low is nit. Post once, as a single review with all inline findings and a short summary. When nothing survives, say so in one sentence rather than inventing findings.
