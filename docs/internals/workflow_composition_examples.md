# Workflow Composition Examples

This note shows what workflow composition looks like with the current interface design.

The examples use simple arithmetic so the composition boundary is easy to see. A child workflow behaves like a grouped expression. Moving that boundary changes the result, just like moving parentheses in a formula.

These examples assume the current design choices:

- workflows compose through `Node(run=child_workflow)`
- a workflow exposes its outward value through a reserved `result` node
- `Workflow.run(...)` returns `WorkflowRun`
- a parent node that runs a child workflow receives the child workflow's exported `result`

## Shared Building Blocks

```python
import elan as el
from elan import Context, Input, Join, Node, Upstream, Workflow
from pydantic import BaseModel


@el.task
def add(left: int, right: int) -> int:
    return left + right


@el.task
def multiply(left: int, right: int) -> int:
    return left * right


@el.task
def divide(numerator: int, denominator: int) -> float:
    return numerator / denominator


@el.task
def identity(value: int | float) -> int | float:
    return value
```

## 1. One Child Workflow As One Parenthesized Operation

This child workflow computes `(a + b)`.

```python
sum_ab = Workflow(
    "sum_ab",
    start=Node(
        run=add,
        input={
            "left": Input.a,
            "right": Input.b,
        },
        next="result",
    ),
    result=Node(
        run=identity,
        output="value",
    ),
)
```

Now the parent uses that child workflow as a node, then multiplies by `c`.

```python
expr = Workflow(
    "expr",
    start=Node(
        run=sum_ab,
        input={
            "a": Input.a,
            "b": Input.b,
        },
        next="result",
    ),
    result=Node(
        run=multiply,
        input={
            "left": Upstream.value,
            "right": Input.c,
        },
    ),
)
```

For `a=2, b=3, c=4`, that reads as:

```text
(a + b) * c
(2 + 3) * 4 = 20
```

The point of the example is the boundary itself. The child workflow groups one part of the computation and exports one value back to the parent.

## 2. Moving The Boundary Changes The Result

This child workflow computes `(b * c)` instead.

```python
product_bc = Workflow(
    "product_bc",
    start=Node(
        run=multiply,
        input={
            "left": Input.b,
            "right": Input.c,
        },
        next="result",
    ),
    result=Node(
        run=identity,
        output="value",
    ),
)
```

The parent now adds `a` after the child returns.

```python
expr = Workflow(
    "expr",
    start=Node(
        run=product_bc,
        input={
            "b": Input.b,
            "c": Input.c,
        },
        next="result",
    ),
    result=Node(
        run=add,
        input={
            "left": Input.a,
            "right": Upstream.value,
        },
    ),
)
```

With the same inputs:

```text
a + (b * c)
2 + (3 * 4) = 14
```

The operators did not change. Only the composition boundary changed.

## 3. Nesting Child Workflows Gives Nested Parentheses

First define `(a + b)`.

```python
sum_ab = Workflow(
    "sum_ab",
    start=Node(
        run=add,
        input={
            "left": Input.a,
            "right": Input.b,
        },
        next="result",
    ),
    result=Node(
        run=identity,
        output="value",
    ),
)
```

Then reuse it inside another child workflow that computes `((a + b) * c)`.

```python
scaled_sum = Workflow(
    "scaled_sum",
    start=Node(
        run=sum_ab,
        input={
            "a": Input.a,
            "b": Input.b,
        },
        next="result",
    ),
    result=Node(
        run=multiply,
        input={
            "left": Upstream.value,
            "right": Input.c,
        },
        output="value",
    ),
)
```

Then the parent divides by `d`.

```python
expr = Workflow(
    "expr",
    start=Node(
        run=scaled_sum,
        input={
            "a": Input.a,
            "b": Input.b,
            "c": Input.c,
        },
        next="result",
    ),
    result=Node(
        run=divide,
        input={
            "numerator": Upstream.value,
            "denominator": Input.d,
        },
    ),
)
```

For `a=2, b=3, c=4, d=5`:

```text
((a + b) * c) / d
((2 + 3) * 4) / 5 = 4.0
```

This is the main composition model in one line: child workflows let you factor a graph into reusable grouped computations.

## 4. Natural Boundary Passing

When the child workflow's interface already matches what the parent is holding, no explicit `input` mapping is needed.

```python
@el.ref
class Pair(BaseModel):
    left: int
    right: int


@el.task
def build_pair(a: int, b: int) -> Pair:
    return Pair(left=a, right=b)


@el.task
def add_pair(pair: Pair) -> int:
    return pair.left + pair.right


sum_pair = Workflow(
    "sum_pair",
    start="result",
    result=Node(run=add_pair),
)


expr = Workflow(
    "expr",
    start=Node(
        run=build_pair,
        next="result",
    ),
    result=Node(run=sum_pair),
)
```

`build_pair` returns a structured payload.

That payload becomes the current packet, and the child workflow consumes it directly through its own normal binding rules.

This is the low-friction case. Composition should not require extra syntax when the interfaces already line up.

## 5. Explicit Boundary Adaptation

`Node.input` matters when the child workflow exposes a different interface from the parent.

This child workflow expects `left` and `right`.

```python
sum_pair = Workflow(
    "sum_pair",
    start=Node(
        run=add,
        input={
            "left": Input.left,
            "right": Input.right,
        },
        next="result",
    ),
    result=Node(
        run=identity,
        output="value",
    ),
)
```

The parent may still want to expose `a` and `b`.

```python
expr = Workflow(
    "expr",
    start=Node(
        run=sum_pair,
        input={
            "left": Input.a,
            "right": Input.b,
        },
        next="result",
    ),
    result=Node(
        run=multiply,
        input={
            "left": Upstream.value,
            "right": Input.c,
        },
    ),
)
```

This is where the composition boundary becomes an adapter:

- the child keeps its own contract
- the parent decides how to feed it

## 6. Context Can Cross The Composition Boundary

A child workflow inherits the current branch scope.

```python
@el.ref
class RunContext(BaseModel):
    factor: int = 1
```

This child workflow computes `(a + b) * factor`.

```python
scaled_sum = Workflow(
    "scaled_sum",
    context=RunContext,
    start=Node(
        run=add,
        input={
            "left": Input.a,
            "right": Input.b,
        },
        output="value",
        next="result",
    ),
    result=Node(
        run=multiply,
        input={
            "left": Upstream.value,
            "right": Context.factor,
        },
    ),
)
```

The parent prepares the context before entering the child workflow.

```python
expr = Workflow(
    "expr",
    context=RunContext,
    start="result",
    result=Node(
        run=scaled_sum,
        input={
            "a": Input.a,
            "b": Input.b,
        },
        context={
            "factor": Input.c,
        },
    ),
)
```

With `a=2, b=3, c=4`, this still computes:

```text
(a + b) * c
(2 + 3) * 4 = 20
```

The interesting part is the boundary behavior:

- `input` prepares task arguments
- `context` prepares branch-local state
- the child workflow inherits both

## 7. Internal Yield Plus Terminal Join

This is the first expression that needs a join:

```text
(a * b) + (c * d)
```

One workflow needs to:

- create several internal branches
- let each branch compute one value
- wait for all of them
- reduce those values into one exported result

```python
@el.task
def pair_inputs(a: int, b: int, c: int, d: int):
    yield a, b
    yield c, d


@el.task
def multiply_pair(left: int, right: int) -> int:
    return left * right


@el.task
def sum_values(values: list[int]) -> int:
    return sum(values)


workflow = Workflow(
    "sum_products",
    start=Node(
        run=pair_inputs,
        next="multiply",
    ),
    multiply=Node(
        run=multiply_pair,
        next="result",
    ),
    result=Join(run=sum_values),
)
```

For `a=2, b=3, c=4, d=5`:

```text
(2 * 3) + (4 * 5) = 26
```

The key point is where the `yield` lives:

- the `yield` is inside the workflow
- so the branches belong to the same workflow scope
- `Join` can wait for that scope and reduce its contributions

## 8. Side-Effect Branches Can Be Awaited Without Contributing

Not every branch needs to contribute a value to the final result.

Some branches may exist only for side effects.

```python
@el.task
def audit_pair(left: int, right: int) -> None:
    ...


workflow = Workflow(
    "sum_products_with_audit",
    start=Node(
        run=pair_inputs,
        next=["multiply", "audit"],
    ),
    multiply=Node(
        run=multiply_pair,
        next="result",
    ),
    audit=Node(
        run=audit_pair,
    ),
    result=Join(run=sum_values),
)
```

The join still waits for the whole workflow scope to complete.

That means:

- `multiply` branches contribute values because they route to `result`
- `audit` branches are still awaited
- `audit` branches do not contribute values because they never route to `result`

This is important because it keeps synchronization and contribution separate.

## 9. Yield Placement Controls Independence Versus Coupling

These two shapes look similar, but they mean different things.

### Yield Outside The Child Workflow

```python
child = Workflow(
    "product",
    start=Node(run=multiply_pair, next="result"),
    result=Node(run=identity, output="value"),
)


parent = Workflow(
    "parent",
    start=Node(run=pair_inputs, next="product"),
    product=Node(run=child),
)
```

Here:

- `pair_inputs` yields in the parent
- each yielded item starts one child workflow execution
- those child workflows are independent

If they need to meet again, that happens in the parent, not in the child.

### Yield Inside The Child Workflow

```python
child = Workflow(
    "sum_products",
    start=Node(run=pair_inputs, next="multiply"),
    multiply=Node(run=multiply_pair, next="result"),
    result=Join(run=sum_values),
)


parent = Workflow(
    "parent",
    start=Node(run=child, next="result"),
    result=Node(run=identity),
)
```

Here:

- the `yield` is inside the child workflow
- the branches are coupled inside one workflow scope
- the child joins them before exporting its `result`

That is the structural rule behind Elan's join model.

## 10. Composition And Joins Work Together

This expression still fits composition cleanly:

```text
((a + b) * c) / d
```

This one now does too:

```text
(a + b) + (c * d)
```

It simply needs a child workflow with internal branching and a terminal join.

Composition and joins play different roles:

- composition defines boundaries
- `yield` defines expansion
- `Join` closes a workflow scope and reduces the contributed branch results
- the reduced value becomes the exported `result`

That is the first complete model for workflow composition in Elan.
