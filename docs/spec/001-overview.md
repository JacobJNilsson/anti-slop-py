# anti-slop-py 001: The rule set

## Problem

AI agents produce Python that runs but carries no evidence. The agent
does not know an invariant, so it guards instead. Typical moves:

- A `try/except` around a whole body, with a silent default on failure.
- An `isinstance` check on a value whose type the annotation states.
- Data passed as `dict[str, Any]` where named fields exist.
- A `cast()` with no stated reason.

Each move transfers a proof obligation from the author to the reader.
The reader cannot tell a checked invariant from a guess.

## Philosophy

The rules enforce one discipline: **evidence at the boundary, concrete
types inside**.

1. Decode external input at its I/O boundary into named domain types:
   dataclasses, TypedDicts, or validated models.
2. Do not widen a known type and then narrow it again.
3. Where an unchecked narrowing is the correct tool, state the
   invariant in a comment directly above it.
4. Where a dynamic check is the correct tool, put it in one named
   function with a clear contract.
5. Where code discards an error or stops the process, state why.

The rules assume a typed codebase with mypy or pyright in CI.
Unannotated code is the type checker's problem. The rules judge what
the author wrote, such as an explicit `Any`, not what inference
produces.

## The justification comment contract

A rule with a comment escape accepts any comment that owns its line,
directly above the flagged statement or above the statement that
contains it. A comment beside code justifies the code beside it, never
the line below. No marker word exists: Python documentation lives in
docstrings inside the body, so an own-line `#` comment above a
statement is deliberate. The analyzer cannot judge the text of the
comment. Review must.

Each rule section below states whether the rule grants the escape.

## Suppression and configuration

Each rule carries one code, AS101 to AS114 without AS105. A `# noqa`
comment on the flagged logical line suppresses, blanket or with a code
list, as in flake8 and ruff.

Configuration lives in `[tool.antislop]` of pyproject.toml. `enable`
turns an opt-in rule on, `disable` turns a rule off, and a per-rule
table holds the settings of one rule. A `boundary-modules` setting is
a list of path globs. A glob matches the path as the command receives
it, the absolute path, and the path below the working directory.

A test file is a file named `test_*.py` or `*_test.py`, a
`conftest.py`, or any file below a `tests` directory.

The `antislop` command exits 0 on a clean run, 1 on a report, and 2 on
a path it cannot read.

## Rule catalogue

Severity `error` is on by default. `opt-in` rules ship off.

| Code | Name | Severity |
|------|------|----------|
| AS101 | `justifycast` | error |
| AS102 | `nountypeddict` | error |
| AS103 | `noanyparam` | opt-in |
| AS104 | `noanyreturn` | error |
| AS106 | `noadhocisinstance` | error |
| AS107 | `noreflection` | error |
| AS108 | `nomonkeypatch` | error |
| AS109 | `justifyexit` | opt-in |
| AS110 | `justifyswallow` | error |
| AS111 | `noredundantguard` | opt-in |
| AS112 | `fullobjectcomp` | opt-in |
| AS113 | `errsemantics` | opt-in |
| AS114 | `noanydecl` | error |

AS105 `nolaundering` is reserved for the type-aware tier, see Phases.

Rules AS102, AS103, AS104, and AS114 resolve type aliases of the same
file, in all three forms: a plain assignment, a `TypeAlias`
annotation, and a `type` statement. String annotations count as their
parsed form. An alias such as `Payload = dict[str, Any]` carries the
same absence of information as the type it names, so it is no
loophole. A cross module alias is out of scope for phase 1.

### AS101 `justifycast`: require a comment for `typing.cast`

`cast()` is a no-op at runtime. It tells the checker to believe the
author without evidence. The rule flags a `cast()` call without a
justification comment. Narrow with a checked construct instead:
`isinstance`, a TypeGuard, or a match statement.

A chained cast, `cast(B, cast(A, x))`, fabricates evidence twice. The
inner cast manufactures the fact that the outer cast consumes. The
rule rejects a chain outright, one report at the chain, and no comment
clears it.

Escape: a justification comment above the call or its statement.
Blanket `# type: ignore` stays with ruff `PGH003` and mypy
`ignore-without-code`.

### AS102 `nountypeddict`: no untyped dicts in signatures and fields

`dict[str, Any]`, `dict[str, object]`, and bare `dict` describe
nothing. Data with known keys belongs in a dataclass, a TypedDict, or
a validated model. The rule flags parameters, returns, class
attributes, and dataclass fields. It reads a `Mapping` and a
`MutableMapping` with Any or object values the same way, and it reads
the same types inside a generic argument, such as
`list[dict[str, Any]]`.

Escape: a justification comment above the definition. Setting:
`boundary-modules` exempts the files that decode raw data.

### AS103 `noanyparam`: no `Any` or `object` parameters

An `Any` parameter moves parsing from the boundary into the callee. An
`object` parameter forces an `isinstance` on the callee. The rule
treats both as the same absence of a contract. Accept a named domain
type. TypeVars and Protocols carry evidence and are fine.

A function that forwards its `*args` and `**kwargs` verbatim to one
callee is the decorator idiom, and both parameters are exempt there. A
lone forwarded parameter reports.

Escape: a justification comment above the definition, naming the API
that fixes the signature.

### AS104 `noanyreturn`: no `Any` or `object` returns

A declared `-> Any` or `-> object` forces every caller to guess.
Return the concrete type, a Protocol the caller consumes, or a
TypeVar. mypy `--warn-return-any` covers inferred `Any`. This rule
covers the declared half.

Escape: a justification comment above the definition, naming the API
that fixes the signature.

### AS106 `noadhocisinstance`: no isinstance dispatch chains

An if chain with two or more `isinstance` tests on one value re-parses
the value away from its boundary, and every new case grows the
reader's burden. Branch on a domain value instead: a kind field, a
match on a sealed union, `functools.singledispatch`, or one handler
per type.

The value is one name or one dotted path. A test inside a boolean
operator or under a `not` counts. The report anchors at the first
branch that tests isinstance, one report per chain. A single
`isinstance` check is legal, and a `match` statement is the
recommended fix and never reports.

No comment clears a report. Setting: `boundary-modules` exempts the
files that decode raw formats. This repository names its own AST
decoders there.

### AS107 `noreflection`: no dynamic reflection outside boundaries

`getattr`, `setattr`, and `delattr` with a computed name, `vars()`,
`globals()` subscripts, and `__dict__` writes erase every static
guarantee. Serialization and plugin loaders need them, application
code does not.

The constant-name forms stay with ruff `B009` and `B010`, and `eval`
and `exec` stay with bandit. No overlap.

No comment clears a report. Setting: `boundary-modules` exempts the
modules that need reflection.

### AS108 `nomonkeypatch`: no runtime patching in production code

Production code must not assign attributes onto imported modules or
imported classes. The mutation is invisible at the call site and
ordering dependent. Inject the dependency instead. The rule reads the
imports of the file and flags every assignment form, unpacking, `for`,
and with-as targets included, and `setattr` with a constant name.

Test files are exempt: `mock.patch` and the pytest `monkeypatch`
fixture restore state and are the sanctioned seam there.

Escape: a justification comment above the statement, for a shim over a
known upstream bug.

### AS109 `justifyexit`: require a comment for exit in library code

`sys.exit()`, `os._exit()`, and a raised `SystemExit` outside an entry
point stop the process of the caller. State why the process cannot
continue, or raise an ordinary exception.

Exempt: `main()` functions, `__main__` blocks, functions under CLI
decorators, and test files. Setting: `entry-decorators` holds the
decorator patterns, with `click` and `typer` in the default.

Escape: a justification comment above the call or its statement.

### AS110 `justifyswallow`: require a comment to discard an exception

An except handler that swallows hides a failure and returns a guess.
A handler swallows when its body is only `pass`, `...`, `continue`,
`break`, or `return <constant>`. The rule fires on any exception type.
Bare `except:` stays with `E722` and broad handlers with `BLE001`.
Enable all three.

Escape: a justification comment above the handler or first in its
body.

### AS111 `noredundantguard`: no guards against the type system

A guard that repeats the annotation of a parameter tells the reader
that the author did not trust the annotation, and it keeps dead
branches alive. The rule flags `isinstance(p, T)` where `p` is a
parameter of the function annotated exactly `T`, a plain name or
dotted path without a union, an Optional, or a subscript.

The `hasattr` half fires only when the annotation names a class of the
same module that declares the attribute: a class body assignment or
annotation, a method, or a `self` attribute assigned in `__init__`. A
parameter that the body rebinds is out, because the guard tests
another binding.

No comment clears a report. Delete the guard, or fix the annotation.

### AS112 `fullobjectcomp`: compare the whole object

A test that asserts attribute after attribute of one object states no
claim about the rest of the value. Compare the whole object against an
expected instance. Dataclasses and attrs classes give `==` for free.

The subject of an assertion is the dotted path without the final
attribute, and `self` never counts as a subject. Three or more
assertions on one subject in one function report once, at the first.
Test files only. Setting: `threshold` moves the count at which the
rule reports.

No comment clears a report.

### AS113 `errsemantics`: assert the identity of an error, not its text

A test that matches on the message decides from prose that no API
promises. The rule flags `pytest.raises` with a `match` argument and a
`str` comparison of a bound error name. A bound error name is a name
that `except ... as` or `pytest.raises(...) as` binds, scoped to the
function that binds it. Assert the exception type and its attributes
instead. Test files only.

Escape: a justification comment, for a match on a stable owned message
format.

### AS114 `noanydecl`: no widened declarations of known values

A variable or attribute annotated `Any` or `object` whose initializer
has an evident type throws away evidence at the declaration:
`x: Any = Config()`. Delete the annotation and keep the inferred type,
or name the concrete type. An evident initializer is a literal, a
unary operator over a literal, a display or a comprehension, an
f-string, or a call of a name that starts with a capital letter.

Escape: a justification comment above the statement, naming the API
that needs the wide type.

## Non-goals

- **Surface slop.** Emoji, TODO stubs, narrative comments, hedging
  language. Surface-pattern tools own this ground and compose with
  this project.
- **Security.** bandit owns `eval`, `exec`, injection, and secrets.
- **Style, formatting, complexity.** ruff owns them.
- **Type correctness.** mypy or pyright strict is the assumed
  baseline.
- **Duplication metrics and import resolution.** CI resolves imports
  at install time. Clone detection is a metrics problem.
- **Detection of AI authorship.** The rules judge the code, not its
  author.

Enable alongside: ruff `B006`, `E722`, `BLE001`, `S110`, `PGH003`,
`B009`, `B010`, `RET50x`, bandit, and the mypy strict flags
`--disallow-any-generics`, `--warn-return-any`,
`--warn-redundant-casts`, and `ignore-without-code`. The catalogue
duplicates none of them.

## Relation to the sibling projects

[anti-slop-go](https://github.com/JacobJNilsson/anti-slop-go) defines
the discipline for Go, and
[dmmulroy/anti-slop](https://github.com/dmmulroy/anti-slop) defines it
for TypeScript. The catalogue differs where the languages differ:

- Go bans test-time monkeypatching because the seam belongs in the
  design. Python's test ecosystem blesses restoring patches, so AS108
  inverts the rule and bans patching in production code.
- Go's G09, return concrete types, has no Python analogue. Protocols
  are structural and duck typing is the idiom.
- Go needs a `CONTRACT:` marker because Go doc comments sit on the
  line a justification would use. Python needs no marker.
- The upstream rules `no-conditional-empty-object-spread`,
  `no-shape-in-symbol-names`, and `no-service-constructor-imports` are
  TypeScript specific and have no translation.

## Implementation

`antislop` is a standalone command on the stdlib `ast` module, with no
runtime dependencies. One rule is one module that yields reports
through one engine. The engine parses each file once and hands every
rule the tree, the comment index, and the settings of the rule. A
pre-commit hook ships with the package.

The linter runs on its own source with the default rule set.

## Phases

1. **Phase 1, AST rules.** The thirteen rules above. Ships alone and
   fast.
2. **Phase 2, the type bridge.** AS105 `nolaundering`, no
   widen-then-narrow through `Any` or `object`, and the full AS111,
   both resolved through a mypy daemon with `dmypy inspect`. The
   common path needs no type checker at lint time.
3. **Phase 3, autofix.** Move to LibCST where a fix is mechanical.
