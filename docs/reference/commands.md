# Commands and options

```text
schemify [--help] <command> [options]
```

| Command | Alias | Does |
|---------|-------|------|
| [`generate`](#generate) | `g` | Ask for the properties of an object and build its JSON Schema |
| [`fill`](#fill) | `f` | Ask for data matching a JSON Schema |
| [`list`](#list) | `l` | Ask for a list of items, each matching a JSON Schema |

| Global option | Meaning |
|---------------|---------|
| `--install-completion` | Install tab completion for the current shell |
| `--show-completion` | Print the completion script, to install it yourself |
| `--help` | Show help; also after a command: `schemify fill --help` |

## `generate`

```text
schemify generate [-t TITLE] [-o FILE]
```

| Option | Default | Meaning |
|--------|---------|---------|
| `-t, --title` | none | The schema's `title` |
| `-o, --output` | printed | File to save the schema to. If it exists, asks before the questions start. |

The schema is always JSON, Draft 2020-12, with `"$schema"` set. The questions are listed
in [Questions and keywords](questions.md).

## `fill`

```text
schemify fill PATH [-o FILE] [-f FORMAT]
```

| Argument / option | Default | Meaning |
|-------------------|---------|---------|
| `PATH` | required | The JSON Schema file |
| `-o, --output` | printed | File to save the data to. If it exists, asks before the questions start. |
| `-f, --format` | `json` | `json`, `python` or `javascript` |

## `list`

```text
schemify list PATH [-o FILE] [-f FORMAT]
```

The same arguments and options as `fill`. Asks for items until you answer **No** to
`Add another item?`, at least one.

## Exit codes

| Exit | Meaning |
|------|---------|
| `0` | Done |
| `1` | Stopped: ++ctrl+c++, or **No** to overwriting the output file |
| `2` | Bad input: a missing or invalid schema file, a schema `fill` cannot handle, an unknown format |
