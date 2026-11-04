# CLAUDE.md — schemify

## Linked project: the schemify editor

`../../web/schemify` (`C:\Users\aaltt\dev\published\web\schemify`) is a React + TypeScript
editor mirroring `schemify generate`. Its `CLAUDE.md` lists which file mirrors which.

- **A feature added to `generate` (a type, a constraint, a computer, a question) is added to
  the editor too**, and a feature added to the editor is added here. Never ship it in one only.
- After changing `generators.py`, `validators.py` or `computers.py`, run in the editor:
  `pnpm sync && pnpm check`. `sync` regenerates its `src/core/meta.json` from this package
  (type names, constraint questions, computer signatures and options examples), and its tests
  fail until the editor handles what was added.
- `scripts/export_meta.py` in the editor reads `SCHEMA_DIALECT`, `generators`, the
  `*_CONSTRAINTS` lists, `computers`, `groups` and `_options_example` from here: keep them, or
  update the exporter when renaming one.
