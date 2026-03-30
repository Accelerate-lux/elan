# Baseline Workflow

This page defines the shared comparison scenario used throughout the tool assessment set. It is the common reference point for the dedicated tool pages and the summary report.

## Workflow shape

```text
start
  -> load_items
  -> process_each(item)    fan-out
  -> collect_results       join / reduce
  -> decide
      -> notify            conditional branch
      -> store             conditional branch
  -> result
```

## Shared semantics

Use the same simple numeric behavior in every comparison so the workflow structure stays in focus:

- `load_items() -> [1, 2, 3]`
- `process_each(x) -> x * 2`
- `collect_results(values) -> sum(values)`
- `decide(total) -> total > 10`
- `notify(total)` runs only when the decision is true
- `store(total)` always runs
- `result -> total`

Expected outcome:

```text
[1, 2, 3]
-> [2, 4, 6]
-> 12
-> notify + store
-> result = 12
```

## Why this workflow

This baseline is small enough to stay readable, but it still forces each tool to show how it handles the workflow behaviors that matter most for Elan's positioning:

- linear execution
- fan-out
- join / reduction
- conditional routing
- explicit final result

That makes it a useful shared test for both `Capabilities` and `Usage`. It is not meant to benchmark runtime, deployment, or observability.

## Provenance

This public comparison set builds on the internal working notes in:

- [tool_comparison_plan.md](../internals/tool_comparison_plan.md)
- [baseline_syntax_comparison.md](../internals/baseline_syntax_comparison.md)

Those internal notes remain source material. This page is the stable public reference for the comparison docs in `docs/comparison/`.
