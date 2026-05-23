# Composition

Workflow composition lets a node run another workflow:

```python
child = Workflow("double_value", start=double)

parent = Workflow(
    "parent",
    start=Node(run=load_value, next="double"),
    double=Node(run=child),
)
```

The parent receives the child workflow's exported `result`, not the child's full
`WorkflowRun`.

## Boundary Behavior

The child workflow consumes the parent packet through its own normal start-node
binding rules.

If the interfaces already match, no adapter is needed:

```python
double=Node(run=child)
```

If the child needs a different input shape, use the parent node's `bind_input`:

```python
double=Node(
    run=child,
    bind_input={
        "value": Upstream.amount,
    },
)
```

`Node.context` still runs before the child workflow starts. A child workflow
inherits the current branch context. If the child declares its own context model
and a parent context exists, the model must match.

## Composition With Join

A child workflow can use its own terminal `Join(...)`:

```python
child = Workflow(
    "score_item",
    start=Node(run=prepare, next=["quality", "risk"]),
    quality=Node(run=score_quality, next="result"),
    risk=Node(run=score_risk, next="result"),
    result=Join(run=merge_scores),
)
```

The parent sees the merged score as one node output.

## Runtime Semantics

- parent outputs record one value for the child workflow node
- child internal outputs are not merged into the parent `WorkflowRun.outputs`
- child workflows may be used after yield fan-out
- child workflow failures fail the parent activation

For exact result behavior, see [Runtime Behavior](../reference/runtime-behavior.md).
