---
hide:
  - navigation
---

# schemify

**Build JSON Schemas by answering questions, then fill JSON data from them.**

schemify asks you about the fields of an object (their names, types, limits and
defaults) and writes a [JSON Schema](https://json-schema.org) (Draft 2020-12). Then it
turns any schema into a questionnaire. Every answer is checked as you type, and the
result comes out as JSON, Python or JavaScript.

```bash
schemify generate -t Person -o person.schema.json   # ask for the properties, write the schema
schemify fill person.schema.json -o person.json     # ask for one object matching it
schemify list person.schema.json -f python          # ask for a list of them
```

![schemify generate: a Person with first, last and an optional age](demo/generate.gif)

## Why schemify

<div class="grid cards" markdown>

-   :material-chat-question-outline: **No JSON Schema to learn**

    ---

    Answer "Type of 'age'?", "Greater than or equal to?", "Is 'age' required?", and get a
    valid Draft 2020-12 schema.

-   :material-form-textbox: **Any schema becomes a form**

    ---

    `fill` asks for each property in order: a text prompt, a yes/no, a list to pick
    from, or a loop of items.

-   :material-check-decagram-outline: **Checked as you type**

    ---

    Lengths, patterns, ranges, formats and choices are checked on every answer, and the
    whole result against the whole schema.

-   :material-code-braces: **JSON, Python or JavaScript**

    ---

    Print or save the data as JSON, a Python literal or a JavaScript object, ready to
    paste into code or tests.

-   :material-puzzle-outline: **Reusable**

    ---

    [templify](https://github.com/aaltatan/templify) and
    [qrbar-cli](https://github.com/aaltatan/qrbar-cli) use schemify for `--schema`, and
    your own typer app can too.

-   :material-web: **Also on the web**

    ---

    [schemify.surge.sh](https://schemify.surge.sh) asks the same questions as form
    fields, with the schema updating as you type.

</div>

## A taste

=== "Build a schema"

    ```text
    $ schemify generate -t Person -o person.schema.json
    ? Property name (empty to finish): first
    ? Type of 'first': string
    ? Format: none
    ? Add validators? No
    ? Label shown instead of 'first' when filling (optional): First name
    ...
    Saved to: .../person.schema.json
    ```

=== "Fill it"

    ```text
    $ schemify fill person.schema.json
    ? First name: Rama
    ? Last name: Hasan
    ? Age (In whole years): 25
    {
      "first": "Rama",
      "last": "Hasan",
      "age": 25
    }
    ```

=== "Fill a list, as Python"

    ```text
    $ schemify list person.schema.json -f python
    Item 1
    ? First name: Rama
    ...
    ? Add another item? (2 so far) No
    [{'first': 'Rama', 'last': 'Hasan', 'age': 25},
     {'first': 'Omar', 'last': 'Ali'}]
    ```

## Where to go next

- New here? [Install it](install.md), then follow the [user guide](guide/index.md),
  starting with [your first schema](guide/first-schema.md).
- Have a job to do? See the [recipes](recipes.md): an invoice with line items, an event
  registration form, test fixtures, seed data, and questions for templify and qrbar.
- Writing Python? See the [Python API](python.md).
- Looking something up? The [reference](reference/index.md) lists every command, every
  question and the keyword it writes, and every error.
