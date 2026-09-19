## Summary

<!-- Explain the research or engineering motivation and the resulting change. -->

## Research-safety declaration

| Question | Answer |
|---|---|
| Files and protocol versions affected | <!-- List them, or `None`. --> |
| Model-visible evidence changed? | <!-- Yes/No; explain if Yes. --> |
| Prompt, taxonomy, scorer, generator, transformation, or config hashes changed? | <!-- List before/after hashes, or `None`. --> |
| Seeds generated or inspected | <!-- List ranges/IDs, or `None`. --> |
| Validation or held-out data touched? | <!-- Yes/No; approval link if Yes. --> |
| Provider calls made? | <!-- Yes/No; approved config and result path if Yes. --> |
| Result artifacts changed? | <!-- List files, or `None`. --> |
| Historical comparisons affected? | <!-- Yes/No; explain if Yes. --> |

## Verification

- [ ] Full test suite: `uv run pytest`
- [ ] Whitespace check: `git diff --check`
- [ ] Redacted secret scan: `uv run python .github/scripts/check_tracked_secrets.py`
- [ ] No credentials, authorization headers, private keys, or unapproved results are included

## Unresolved methodology decisions

<!-- List decisions requiring research approval, or `None`. -->
