# antislop

Evidence rules for Python. The linter targets the moves AI code
generators make when they do not know an invariant: silent except
handlers, casts without a stated reason, `Any` where a domain type
exists, and guards against the type system.

Sibling of [anti-slop-go](https://github.com/JacobJNilsson/anti-slop-go).
The rule catalogue and the philosophy live in
[docs/spec/001-overview.md](docs/spec/001-overview.md).

## Use

```sh
uv run antislop src/
```

A finding names a file, a line, a rule code, and the fix:

```
src/app.py:41:8: AS110 justifyswallow: the except handler discards the error. ...
```

Configure rules in `pyproject.toml` under `[tool.antislop]`.

## Development

```sh
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```
