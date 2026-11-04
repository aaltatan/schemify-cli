# schemify-cli

Build JSON Schemas interactively, and fill JSON data from them, from the command line.

Source: [github.com/aaltatan/schemify-cli](https://github.com/aaltatan/schemify-cli)

A web version runs at [schemify.surge.sh](https://schemify.surge.sh)
([source](https://github.com/aaltatan/schemify-web)): the same questions as fields, with the
schema updating as you type.

## Install

```bash
uv tool install git+https://github.com/aaltatan/schemify-cli
```

## Usage

```bash
schemify generate -t Person -o person.schema.json   # ask for the properties, write the schema
schemify fill person.schema.json -o person.json     # ask for one object matching it
schemify list person.schema.json -f python          # ask for a list of them
```

| Command | Alias | Does |
|---|---|---|
| `generate` | `g` | Asks for the properties of an object and builds its JSON Schema (Draft 2020-12) |
| `fill` | `f` | Asks for data matching a schema file, checked against it |
| `list` | `l` | Asks for a list of items, each matching the schema |

- `-o, --output` saves to a file (asks before overwriting); without it the result is printed.
- `-f, --format` picks the output of `fill` and `list`: `json`, `python` or `javascript`.

Types: `string`, `integer`, `number`, `boolean`, `date`, `datetime`, `enum`, `array`, `object`,
each with its constraints (length, pattern, format, range, items, ...) and an optional default.

## Computed properties

A property with `x-compute` is not asked in `fill`, it is computed from the other values:

```json
"full_name": {"type": "string", "x-compute": {"fn": "join", "from": ["first", "middle?", "last"]}}
```

- `fn`: the computer, `from`: source paths (a list, or an `{alias: path}` object for `template`
  and `expr`), `options`: extra arguments, `default`: the value when a source is missing.
- Paths are relative to the owning object (`address.city`, `items[0]`), or to the root
  (`$.company`). `items[*].price` gives every price; a trailing `?` makes a source optional.

Built-in computers:

- **Text**: join, concat, template, upper, lower, title, capitalize, trim, replace, slice,
  initials, slug, length, pad, mask
- **Numbers**: sum, subtract, multiply, divide, average, min, max, abs, round, percent,
  percent_of, expr
- **Dates**: today, now, add_days, add_months, add_years, days_between, age, year, month, day,
  weekday, format_date, start_of_month, end_of_month
- **Number to words**: words
- **Logic, lookup and misc**: coalesce, if_else, equals, lookup, constant, count, count_if,
  unique, uuid

## Reusing it in a typer app

`schemify.cli.dependencies.schema` exposes typer-di dependencies that load a schema file and ask
for its data: `FilledDataArgumentDI` and `FilledListArgumentDI` take the path as an argument,
`FilledDataOptionDI` and `FilledListOptionDI` as `--js`.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run mypy src
```

After changing `generators.py`, `validators.py` or `computers.py`, run `pnpm sync && pnpm check`
in [schemify-web](https://github.com/aaltatan/schemify-web) so it stays in step.
