# Output

## Print or save

| Option | Result |
|--------|--------|
| no `-o` | The result is printed, with syntax highlighting |
| `-o, --output <file>` | The result is saved as UTF-8, and `Saved to: <path>` is printed. Missing folders are created. |

If the `-o` file exists, schemify asks before the questions start:

```text
? 'rama.json' already exists, overwrite it? [y/N]
```

**No** (the default) stops right away, so you never answer questions for nothing.

## Formats

`-f, --format` picks the output of `fill` and `list` (`generate` always writes JSON):

=== "json (default)"

    ```text
    schemify fill person.schema.json -o rama.json
    ```

    ```json
    {
      "first": "Rama",
      "last": "Hasan",
      "age": 25
    }
    ```

    Indented with 2 spaces. Arabic and other non-ASCII text is kept as it is, not
    escaped to `م...`.

=== "python"

    ```text
    schemify fill person.schema.json -f python
    ```

    ```python
    {'first': 'Rama', 'last': 'Hasan', 'age': 25}
    ```

    A Python literal: `True`, `False` and `None` instead of `true`, `false`, `null`.
    Keys keep the schema order. Paste it into a test or a script.

=== "javascript"

    ```text
    schemify fill person.schema.json -f javascript -o rama.js
    ```

    ```javascript
    {
      first: "Rama",
      last: "Hasan",
      age: 25
    }
    ```

    A JavaScript object literal: keys are quoted only when they need it
    (`"unit price": 3`). Paste it into a frontend test, a Storybook story, or a mock.

An unknown format is refused before any question:

```text
Invalid value for '-f' / '--format': Format 'yaml' is not supported, supported: javascript, json, python
```

## Saving rather than redirecting

Use `-o` to save the result. The questions need an interactive terminal, so
redirecting the command's output (`> file`) is not a reliable way to keep only the
result.
