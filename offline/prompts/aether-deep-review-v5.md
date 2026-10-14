# Aether deep review

Find every defect this pull request introduces or exposes, and publish each one once with a concrete trigger. A missed real defect costs far more than an extra comment, so this review is built for recall: the diff is split into slices that each get one reviewer's undivided attention, every changed function is executed with hostile inputs rather than only read, and findings are merged and published without a confidence cutoff.

## 1. Scope

Review the pull request's changes from its merge base to its head, reading whatever repository context is needed to reason about them.

In scope: defects in or adjacent to the changed code. Wrong behavior, security and authorization gaps, races and non-atomic updates, data loss or corruption, broken API and type contracts, material performance regressions, newly required behavior with no test, and comments, docs or error messages the change made untrue. Every severity counts, including low: dead code, a misleading name or message, a missing cleanup. Test files, fixtures, migrations, stylesheets and scripts are changed code and get the same scrutiny as application code.

Out of scope: style, naming and refactoring preferences; speculation without a concrete trigger; pre-existing problems the change does not touch; anything about the environment the review ran in.

## 2. Brief and slices

Write a brief: the changed files, each hunk in one line, and the contracts, callers, tests and schemas the change touches. Then split the hunks into slices of at most eight hunks each, keeping hunks of one file together and keeping a changed function together with its tests. A small diff is one slice.

## 3. Reviewers

Run one **slice reviewer** per slice plus the five lane reviewers below. Every reviewer receives the diff, the brief and read access to the repository, and never sees another reviewer's output. Use the agent's subagent mechanism when it has one, running at most four at a time; otherwise run them sequentially, each from a fresh start with only the brief, and keep their results in separate files so no pass reads another's notes.

**Slice reviewer** (one per slice): you own these hunks and nothing else. For every hunk in your slice, write a record with one line per item below, each line saying either what you checked and why it holds or the defect you found. Do not skip a hunk and do not skip an item.
- Null, undefined and empty-collection paths, including every lookup whose result can be absent and every function path with no return value.
- Inverted or incomplete conditions and boundary errors.
- Wrong comparison operators, or reference equality where value equality was meant.
- Promises created but not awaited, including inside forEach or map callbacks.
- Hardcoded literals where a variable or field was meant.
- Case, normalization and regex-anchoring mistakes when matching strings.
- A query or filter whose new condition applies more widely than the sibling conditions around it.
- Error handling that changes the response status or swallows failures.
- Resources never released; branches the change makes unreachable; loops whose exit condition reads a value that does not change.
- **Probe it.** For every function, method or handler the diff adds or changes in your slice, write one probe script under /tmp/probes/ that imports the function from the checkout or copies its body verbatim, stubs every external dependency (database, network, filesystem, clock) with fakes that record their calls, and calls the function once per line with each of the following: null, nil or undefined for every parameter and field that can be absent; an empty collection or empty string for every list, map or string input; a string that differs from a valid value only in case, and one with surrounding whitespace; a value exactly at each boundary the code compares against, and one just past it; the same call twice, and two interleaved calls, whenever the function reads then writes shared state; a response or record with a field the code reads missing or of the wrong type. Write one line per call in your record: the input, and whether the call returned, threw, panicked or produced a wrong value, with the value. For every block the diff rewrote or moved, put the base version of the function in the same probe and run both on the same inputs; report every difference in return value, raised error, logged field or side effect. Compile or type-check the changed package first when a compiler exists. Running the repository's existing test suite does not satisfy this step: those tests passed when the change was merged with its defects in. Install a missing toolchain with sudo apt-get or run one from a Docker image; if it cannot be made to work, say so in the record and continue with reading. Your output must list the probe scripts you wrote; a slice that contains changed functions and lists no probes is incomplete.

**Literals and definitions**: for every identifier, key, parameter name, HTTP verb, property, enum value, vendor-prefixed CSS property and numeric constant the diff introduces, open the thing it refers to (the route table, the schema, the type, the framework or browser documentation, the value before the change) and confirm it exists and means what the code assumes. Check that each changed file's contents match its name and purpose, that a test calls the route with the verb the router declares, and that every edit mirrored from one place to another preserves the original values.

**Contracts**: for every changed signature, return shape, schema, query or type, trace every caller and implementation across the repository and report each place that now disagrees with the change, including implementations of a changed interface that still declare the old shape. When a synchronous function became asynchronous, list every caller that still uses its result synchronously.

**State and failure paths**: read-modify-write sequences that are not atomic under concurrent requests, lazily initialized shared state read from several threads, stale reads, missing transactions, partial updates, retry and idempotency gaps, cancellation and resource lifecycle; migrations whose new columns leave existing rows null or without the default the code assumes; sibling code paths that handle the same event asymmetrically, where one path persists or cleans up and the other does not; then construct concrete edge inputs and operational sequences for the changed behavior and trace each through the code until it produces a wrong result.

**Security**: for every changed path, ask who controls each input and what it reaches. Network requests to a URL that comes from configuration, a setting or a request; origin, host and referer checks done with substring or prefix matching instead of exact comparison of scheme, host and port; security headers added, removed or weakened; values interpolated into HTML, JavaScript, SQL, shell commands or templates without escaping or binding; state-changing GET routes and other requests without CSRF protection; authorization checks skipped on one branch, bypassed by a cache or a fallback value, or that trust a cached grant while ignoring a cached denial; secrets, tokens or private fields exposed by a new serializer field, log line or response.

**Refactor fidelity**: for every block the diff replaces, moves, extracts or rewrites, list what the old code did, including nil and empty checks, logged fields and identifiers, error handling and the errors returned, blocking versus asynchronous behavior, ordering and retries, and confirm each behavior survives in the new code; a refactor that drops one of them is a defect even when the new code reads cleaner. Also check that error messages and returned error types describe the condition that actually occurred, that newly required behavior has a test and that the test exercises the new arguments, and that changed comments, docs and messages are still true.

Each reviewer returns atomic items, one defect per item: file and changed line, root cause, trigger (the input, state or sequence), observable bad outcome, evidence from the repository or the script that showed it, suggested fix, severity (critical, high, medium, low). A reviewer reports every defect it has a concrete trigger for and nothing it does not.

## 4. Merge

If a slice reviewer returned no probe list for a slice with changed functions, run that slice again before merging. Cluster the reviewers' items by underlying defect, not by wording or line. Keep the strongest trigger and evidence for each cluster, and record how many of the independent reviewers reported it. One item per defect. Merging removes duplicates only; it never removes a finding.

## 5. Publish

Post every merged item unless the repository shows its trigger is unreachable. Do not drop a finding because it depends on a particular input or state; that is what a trigger is.

Write each finding as mechanism, then consequence, in one or two sentences, followed by the trigger and the fix, anchored to the changed line. Say when a script reproduced it, and end every finding with how many reviewers found it, in the form `(found by 2 of 9 reviewers)`. Severity: p1 only when you would block the merge yourself; other critical, high and medium findings are p2; low is nit. Post once, as a single review with all inline findings and a short summary. When nothing survives, say so in one sentence rather than inventing findings.
