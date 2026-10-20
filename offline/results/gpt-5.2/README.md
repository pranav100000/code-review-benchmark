# results/gpt-5.2

Judge run made on 19 October 2026 (UTC 20 October) with Martian's pipeline unchanged, against the OpenAI API directly
(MARTIAN_BASE_URL=https://api.openai.com/v1, MARTIAN_MODEL=gpt-5.2), not through Martian's gateway.

- `aether-v22`: extraction (step 2), dedup (step 2.5) and judge (step 3) all ran here.
- `greptile`, `greptile-v5`, `bugbot`, `copilot`, `coderabbit`: candidates and dedup groups were copied from
  `results/openai_gpt-5.2/` (Martian's own extraction with the same model) and only the judge (step 3) ran here,
  so the difference between these tools' numbers here and in `results/openai_gpt-5.2/` measures judge drift
  between the two runs.
