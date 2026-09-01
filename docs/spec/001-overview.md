# anti-slop-py 001: Overview and rule catalogue (draft)

Status: draft for review, 2026-08-31.
Parent projects: [anti-slop-go](https://github.com/JacobJNilsson/anti-slop-go) and
[dmmulroy/anti-slop](https://github.com/dmmulroy/anti-slop) (TypeScript).

## Problem

AI code generators produce Python that runs but carries no evidence.
The generator does not know an invariant, so it guards instead. It
wraps a function body in `try/except`, returns a silent default, checks
`isinstance` on a value whose type the annotation already states, and
passes data as `dict[str, Any]`. Each move transfers a proof obligation
from the author to the reader.

The scale of the problem is measured. GitClear read 623M changed lines
and found error-masking constructs up 47% and copy-paste code up 41%
since AI assistance became common. Academic studies find 42-85% more
code smells in LLM output than in reference solutions.

## Philosophy

The rules enforce the same discipline as the Go project: **evidence at
the boundary, concrete types inside**.

1. Decode external input at its I/O boundary into named domain types:
   dataclasses, TypedDicts, or validated models.
2. Do not widen a known type and then narrow it again.
3. Where an unchecked narrowing is the correct tool, state the
   invariant in a comment directly above it.
4. Where a dynamic check is the correct tool, put it in one named
   function with a clear contract.
5. Where code discards an error or stops the process, state why.

The justification comment contract carries over from the Go project in
its final form: any comment that owns its line, directly above the
flagged statement, justifies it. No marker word. The Go project needed
a `CONTRACT:` marker for signature rules because Go doc comments sit on
the same line a justification would use. Python documentation lives in
docstrings inside the body, so a `#` comment above a statement is
almost always deliberate. Python needs no marker at all.

## What changes from Go

Three properties of Python reshape the catalogue:

- **Annotations are optional.** The rules assume a typed codebase with
  mypy or pyright in CI. Unannotated code is the type checker's
  problem, not this linter's. The rules judge what the author wrote,
  such as an explicit `Any`, not what inference produced.
- **Monkeypatching flips.** Go bans test-time patching because the seam
  belongs in the design. Python's test ecosystem blesses `mock.patch`
  and pytest `monkeypatch`, which restore state automatically. The
  Python rule therefore bans patching in production code and leaves
  tests alone.
- **No interface returns.** Go's G09 (return concrete types) has no
  Python analogue worth building. Protocols are structural and duck
  typing is the idiom. Dropped.

## Rule catalogue

Severity `error` is on by default. `opt-in` rules ship off.

| # | Name | Go parent | Severity |
|---|------|-----------|----------|
| P01 | `justifycast` | G01 `safetyassert` | error |
| P02 | `nountypeddict` | G02 `nountypedmap` | error |
| P03 | `noanyparam` | G03 `noanyparam` | opt-in |
| P04 | `noanyreturn` | G04 `noanyreturn` | error |
| P05 | `nolaundering` | G05 `nolaundering` | opt-in, type-aware |
| P06 | `noadhocisinstance` | G06 `noadhoctypeswitch` | error |
| P07 | `noreflection` | G07 `noreflect` | error |
| P08 | `nomonkeypatch` | G08 `nomonkeypatch` (inverted) | error |
| P09 | `justifyexit` | G11 `justifypanic` | opt-in |
| P10 | `justifyswallow` | new, from AI-slop data | error |
| P11 | `noredundantguard` | new, from AI-slop data | opt-in, type-aware |
| P12 | `fullobjectcomp` | G12 `fullstructcomp` | opt-in |
| P13 | `errsemantics` | G13 `errsemantics` + G10 | opt-in |
| P14 | `noanydecl` | upstream `no-known-value-widening` | error |

Not translated: G09 `nointerfacereturn` (duck typing), G10
`noerrorassert` as a separate rule (Python has no wrap chain, the test
half folds into P13).

Rules P02, P03, P04, and P14 resolve type aliases. An alias such as
`Payload = dict[str, Any]` carries the same absence of information as
the type it names, so it is no loophole.

### P01 `justifycast`: require a comment for `typing.cast` (error)

`cast()` is a no-op at runtime. It tells the checker to believe the
author without evidence. The author must state the invariant in a
comment directly above the statement, or narrow with a checked
construct (`isinstance`, a TypeGuard, a match statement).

A chained cast, `cast(B, cast(A, x))`, fabricates evidence twice and
no comment justifies it. The inner cast manufactures the fact that the
outer cast consumes. The rule rejects the chain outright.

Blanket `# type: ignore` without an error code is the same move. Ruff
`PGH003` and mypy `ignore-without-code` already cover it. Enable those,
this rule does not duplicate them.

### P02 `nountypeddict`: no untyped dicts in signatures and fields (error)

`dict[str, Any]`, `dict[str, object]`, and bare `dict` describe
nothing. Data with known keys belongs in a dataclass, a TypedDict, or a
validated model. The rule flags parameters, returns, class attributes,
and dataclass fields. A boundary-modules setting exempts the modules
that decode raw JSON. A comment directly above the definition, naming
the source that fixes the shape, is the escape. No mainstream linter
has this rule (`ANN401`
comes closest and only sees `Any` itself).

### P03 `noanyparam`: no `Any` or `object` parameters (opt-in)

An `Any` parameter moves parsing from the boundary into the callee. An
`object` parameter forces an `isinstance` on the callee for the same
reason, so the rule treats both as the same absence of a contract.
Accept a named domain type. TypeVars and Protocols carry evidence and
are fine. `**kwargs: Any` forwarded verbatim to one callee is the
decorator idiom and is exempt. A justification comment naming the API
that fixes the signature is the escape. This rule supersedes ruff
`ANN401` by adding the escape and the forwarding exemption. Use one,
not both.

### P04 `noanyreturn`: no `Any` or `object` returns (error)

A declared `-> Any` or `-> object` forces every caller to guess. Return the
concrete type, a Protocol the caller consumes, or a TypeVar. A comment
directly above the definition, naming the API that fixes the
signature, is the escape. mypy
`--warn-return-any` covers inferred `Any` leaking out. This rule covers
the declared half.

### P05 `nolaundering`: no widen-then-narrow (opt-in, type-aware)

A value must not pass through `Any` or `object` and come back through
`cast` or `isinstance`. The widening throws away evidence the program
had. Needs resolved types, so it ships in the type-aware tier.

### P06 `noadhocisinstance`: no isinstance dispatch chains (error)

An `if isinstance(x, A) ... elif isinstance(x, B) ...` chain re-parses
a value away from its boundary, and every new case grows the reader's
burden. Branch on a domain value instead: a kind field, a match on a
sealed union, `functools.singledispatch`, or one handler per type. The
AST rule flags a chain of two or more isinstance branches on one name.
A boundary-modules setting exempts decode modules. A two-branch check
against one union at a boundary stays legal there. Existing linters
only catch this indirectly through complexity thresholds.

### P07 `noreflection`: no dynamic reflection outside boundaries (error)

`getattr`, `setattr`, and `delattr` with a computed name, `vars()`,
`globals()` subscripts, and `__dict__` writes erase every static
guarantee. Serialization and plugin-loading modules need them,
application code does not. A boundary-modules setting allowlists the
exceptions. `eval`/`exec` stay with bandit (`S307`, `S102`), and the
constant-name inverse stays with `B009`/`B010`. No overlap.

### P08 `nomonkeypatch`: no runtime patching in production code (error)

Production code must not assign attributes onto imported modules or
foreign classes. That mutation is invisible at the call site and
ordering-dependent. Inject the dependency instead. Test files are
exempt: `mock.patch` and pytest `monkeypatch` restore state and are the
sanctioned seam there. This inverts Go's G08 deliberately, because the
ecosystems bless opposite sides. A compatibility shim for a known
upstream bug earns a justification comment.

### P09 `justifyexit`: require a comment for exit in library code (opt-in)

`sys.exit()`, `os._exit()`, and a raised `SystemExit` outside an entry
point stop somebody else's process. The author must state why the
process cannot continue, in a comment directly above the call, or raise
an ordinary exception. Exempt: `main()` functions, `__main__` blocks,
functions under CLI decorators (`click`, `typer`, configurable), and
test files. No mainstream linter has this rule.

### P10 `justifyswallow`: require a comment to discard an exception (error)

An except handler that swallows (body is only `pass`, `...`,
`continue`, `break`, or `return <constant>`) hides a failure and returns a
guess. This is the single most measured AI pattern (error masking
up 47% in GitClear's data). The author must state why ignoring the
error is correct, in a comment directly above or as the first line of
the handler. The rule fires on any exception type, unlike ruff `S110`,
which only checks broad ones. Bare `except:` and `except Exception`
stay with `E722` and `BLE001`. Enable all three.

### P11 `noredundantguard`: no guards against the type system (opt-in, type-aware)

`isinstance(x, T)` or `hasattr(x, "name")` where the declared type of
`x` already answers the question is defensiveness without evidence. It
tells the reader the author did not trust the annotation, and it keeps
dead branches alive. Phase 1 catches the AST-visible core: a guard on a
parameter tested against its own annotation in the same function. The
full rule resolves types through the checker bridge. No comment
clears a report. Delete the guard, or fix the annotation. This is the
flagship anti-AI rule. No existing linter has it.

### P12 `fullobjectcomp`: compare the whole object (opt-in)

A test that asserts attribute after attribute of one object states no
claim about the rest of the value. Compare the whole object against an
expected instance. Dataclasses and attrs classes give `==` for free.
The rule counts per-attribute assertions on one subject across a test,
above a small threshold. Test files only.

### P13 `errsemantics`: assert the identity of an error, not its text (opt-in)

A test that matches on the message decides from prose that no API
promises. `pytest.raises(Error, match="...")` on wording, `str(e) ==`,
and `"..." in str(e)` all break on a reword. Assert the exception type
and its attributes instead. A match on a stable, owned message format
stays possible through a justification comment.

### P14 `noanydecl`: no widened declarations of known values (error)

A variable or attribute annotated `Any` or `object` whose initializer
has a concrete type throws away evidence at the declaration:
`x: Any = Config()`. Delete the annotation and keep the inferred type,
or name the concrete type. A comment directly above the statement,
naming the API that needs the wide type, is the escape. Phase 1 catches initializers whose type is
syntactically evident (a literal, a constructor call). The type bridge
extends the check to every initializer. This translates the upstream
rule `no-known-value-widening`, which the Go project folded into a
rule that Python drops.

## Upstream coverage

All 16 rules of [dmmulroy/anti-slop](https://github.com/dmmulroy/anti-slop):

| Upstream rule | Python translation |
| --- | --- |
| `require-safety-comment-for-type-assertion` | P01 `justifycast` |
| `no-chained-type-assertions` | P01, the chain clause |
| `no-unsafe-dictionary-type` | P02 `nountypeddict` |
| `no-unknown-parameters`, `no-object-parameters` | P03 `noanyparam` |
| `no-unknown-returns` | P04 `noanyreturn` |
| `no-unknown-type-aliases` | Alias resolution in P02-P04, P14 |
| `no-widen-then-assert` | P05 `nolaundering` |
| `no-runtime-typeof` | P06 `noadhocisinstance` |
| `no-reflect-apply`, `no-reflect-get` | P07 `noreflection` |
| `no-module-mocking` | P08 `nomonkeypatch`, inverted for Python |
| `no-known-value-widening` | P14 `noanydecl` |
| `no-conditional-empty-object-spread` | Not translated. The dict-spread analogue `{**(d or {})}` exists, and P02 removes the untyped dict itself. |
| `no-shape-in-symbol-names` | Not translated. Zod-specific. |
| `no-service-constructor-imports` | Not translated. Effect-specific. |

## Non-goals

- **Surface slop.** Emoji, TODO stubs, narrative comments, hedging
  language, placeholder names. sloppylint, aislop, and similar tools
  own this ground and compose with this project.
- **Security.** bandit owns `eval`, `exec`, injection, and secrets.
- **Style, formatting, complexity.** ruff owns them.
- **Type correctness.** mypy or pyright strict is the assumed baseline,
  not something this linter re-implements.
- **Duplication metrics and hallucinated imports.** CI resolves imports
  at install time, clone detection is a metrics problem.
- **Detection of AI authorship.** The rules judge the code, not its
  author.

## Related work to enable alongside

ruff with `B006` (mutable defaults), `E722`, `BLE001`, `S110`,
`PGH003`, `B009`/`B010`, `RET50x`, bandit rules, and mypy strict flags
(`--disallow-any-generics`, `--warn-return-any`,
`--warn-redundant-casts`, `ignore-without-code`). The catalogue above
deliberately avoids duplicating any of them.

## Implementation vehicle

Research conclusion, verified against primary sources in August 2026:

- **ruff has no plugin system** (FAQ, issue #283, maintainer statements
  through late 2025). Upstreaming rules means ceding control and
  passing Astral's acceptance bar. Not a vehicle.
- **flake8** plugins are AST-only and the ecosystem is migrating away.
- **pylint** checkers get astroid inference but carry a documented
  performance ceiling on large codebases.
- **fixit (LibCST)** is the proven scaffold for a standalone,
  pip-installed rule set with config, per-rule codes, and safe
  autofixes. Type info is not built in.

**Decision: a standalone tool, `antislop`, on stdlib `ast` for the
AST rules, with per-rule codes (AS101...), config in
`[tool.antislop]` in pyproject.toml, a pre-commit hook, and `# noqa`
compatible suppression.** The two type-aware rules (P05, full P11) ship
behind an optional bridge that queries a running mypy daemon
(`dmypy inspect`) per candidate node, so the common path needs no type
checker at lint time. LibCST/fixit stays the fallback if autofix
becomes a goal.

## Phases

1. **Phase 1, AST rules.** P01, P02, P03, P04, P06, P07, P08, P09,
   P10, P12, P13, P14, and the AST subset of P11. Ships alone and
   fast.
2. **Phase 2, type bridge.** P05 and full P11 through `dmypy inspect`.
3. **Phase 3, autofix.** Move to LibCST where a fix is mechanical
   (P01 comment insertion has none, P02 has none, some P06 rewrites do).
