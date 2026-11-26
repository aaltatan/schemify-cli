# Development

```text
git clone https://github.com/aaltatan/schemify-cli
cd schemify-cli
uv sync
uv run pytest
uv run ruff check . && uv run mypy src
```

## Project structure

```text
src/schemify/
├── generators.py        # `generate`: the questions per type, SCHEMA_DIALECT, format patterns
├── validators.py        # parsers, prompt validators, the *_CONSTRAINTS lists, check_schema/value
├── fillers.py           # `fill` / `list`: a prompt per schema kind, ask_data, ask_list
├── formatters.py        # json, python, javascript output
├── registry.py          # the Registry behind generators, fillers and formatters
└── cli/
    ├── main.py          # the commands
    └── dependencies/
        ├── schema.py    # load_schema, ask_or_abort and the reusable typer-di dependencies
        └── console.py   # rich console
examples/
├── *.schema.json        # the schemas used in the docs
├── *.json, *.js, *.py   # the data the documented sessions produce
└── sessions/            # the scripted answers of every documented session
tests/
└── test_docs.py         # replays every session and compares with examples/
```

## The web editor

[The schemify editor](https://github.com/aaltatan/schemify) mirrors `generate` in the
browser. A type, constraint or question added here is added there too. After changing
`generators.py` or `validators.py`, run in the editor:

```text
pnpm sync && pnpm check
```

## Documentation

This site is built with [MkDocs](https://www.mkdocs.org) and
[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/). The pages are in
`docs/`, and the navigation in `mkdocs.yml`.

```text
uv run --group docs mkdocs serve          # live preview on http://127.0.0.1:8000
uv run --group docs mkdocs build --strict # what CI runs: broken links fail the build
```

Every push to `main` builds the site and publishes it to GitHub Pages
(`.github/workflows/docs.yml`).

### The sessions are tested

Every session in the docs is a file in `examples/sessions/`: the command, the answers in
order, and the file it writes. `tests/test_docs.py` replays each one with scripted
answers against a copy of `examples/`, and checks that:

- every answer was used, and the command succeeded;
- the written file is exactly the one in `examples/` (`person.schema.json`, `rama.json`,
  ...);
- every `examples/*.schema.json` is a valid schema.

A change to a question, a default or an output format then fails the test until the
docs and examples are updated. Answers are JSON values: text for text prompts and
choices, `true` / `false` for yes/no prompts.

### Demo GIFs

The GIFs in `docs/demo/` are recorded with [VHS](https://github.com/charmbracelet/vhs)
(`scoop install vhs` or `brew install vhs`) and PowerShell (`pwsh`), from the repository
root, `generate` first since the others use its schema:

```text
vhs docs/demo/generate.tape && vhs docs/demo/fill.tape && vhs docs/demo/list.tape
```

## Releasing

Push a `v*` tag. The release workflow builds the package, publishes it to PyPI with
trusted publishing, and creates a GitHub release.
