# 001: Spec changes during phase 1

Status: accepted, 2026-09-01.

The work on phase 1 found gaps in `docs/spec/001-overview.md`. The spec
owner made each amendment below. This record lists them with one reason
each, so a reader knows why the spec moved after the review.

- **P02, P04, and P14 received an escape.** An external API fixes some
  signatures, and the author needs a way to state that fact.
- **P11 received no escape.** The fix for a guard against the type
  system lives in the code, so no comment may keep the guard alive.
- **P10 added `break` to the swallow list.** A break discards the error
  in the same way as a pass or a continue.
- **P09 exempts a test file.** A test that stops the process stops only
  the test run of its author.
- **P11 bounds its hasattr check to a class of the same file.** The AST
  alone cannot tell which attributes a foreign type declares.
- **P03 exempts the forwarding pair.** The decorator idiom hands
  `*args` and `**kwargs` to one callee together.
