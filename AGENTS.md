# Working agreements

## Authority

The spec in `docs/spec/` is the authority. An implementation follows
it.

## Language

Write all lasting text in ASD-STE100 Simplified Technical English.
This covers code comments, docstrings, commit messages, and rule
messages. Use the active voice. Use short sentences with a maximum of
25 words. Do not use semicolons. Do not use em dashes. Code comments
are one sentence, two at most.

A rule message names the problem and the fix. It uses two short
sentences, never a semicolon.

## Commits

A mechanical rename goes in its own commit before the change that
needs it. Every commit builds, passes `pytest`, `ruff check`, and
`mypy` on its own. Lint cleanup of touched files goes in a separate
commit that lands first.

## Tests

Work test-driven. Write the test from the spec, watch it fail, then
write the code. A rule test uses `tests/helpers.py`:

```python
assert run(source, "justifyswallow") == ["3:AS110"]
```

Every rule test covers: the rejected shape, the accepted shape, the
justification comment escape where the rule has one, and one edge the
spec names.

## Rule conventions

One rule is one module in `src/antislop/rules/` that defines a class
with `code`, `name`, `default_on`, and `check(ctx)`. Register it in
`src/antislop/rules/__init__.py`. The justification test comes from
`ctx.justified(lines)`. Do not re-implement comment parsing in a rule.
