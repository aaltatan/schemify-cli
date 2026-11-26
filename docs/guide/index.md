# User guide

| Page | You will learn |
|------|----------------|
| [Your first schema](first-schema.md) | Build a `Person` schema with `generate`, question by question |
| [Types and constraints](types.md) | Every type, the questions it asks, and the keywords they write |
| [Filling data](fill.md) | How `fill` asks for each kind of value, and checks it |
| [Lists](list.md) | Several items in one go with `list` |
| [Output](output.md) | JSON, Python or JavaScript; printing or saving |
| [Writing schemas by hand](hand-written.md) | Which keywords `fill` understands, and which it does not |
| [With other tools](other-tools.md) | templify, qrbar-cli, the web editor, and validating elsewhere |

## The three commands

| Command | Alias | Does |
|---------|-------|------|
| `generate` | `g` | Asks for the properties of an object and builds its JSON Schema (Draft 2020-12) |
| `fill` | `f` | Asks for data matching a schema file, checked against it |
| `list` | `l` | Asks for a list of items, each matching the schema |

```text
 generate ──► person.schema.json ──► fill ──► person.json
  (questions about fields)            (questions from the schema)
                                 └──► list ──► people.json
```

`generate` is for **designing** a schema. `fill` and `list` are for **using** one,
whether schemify wrote it or you did.

## How the questions look

- **Text prompts** take typed answers. A wrong answer is refused on the spot, with the
  reason under the prompt, and you type again.
- **Yes/No prompts** take ++y++ or ++n++, or ++enter++ for the default.
- **Choice prompts** take the arrow keys and ++enter++.
- ++ctrl+c++ at any point stops without writing anything.

In this guide, a session is shown as `? Question: answer`, with a refused answer
followed by the reason:

```text
? Age (In whole years): -3
  >> -3 is less than the minimum of 0
? Age (In whole years): 25
```
