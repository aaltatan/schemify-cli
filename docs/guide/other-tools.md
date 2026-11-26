# With other tools

## templify

[templify](https://github.com/aaltatan/templify) fills Word, text, Markdown, HTML and JSON
templates. Its `-s` option uses schemify to ask for the data instead of reading a file:

```text
templify render --object -t certificate.docx -s person.schema.json        # one record: fill
templify render --each -t letter.docx -s person.schema.json -n first      # many: list
```

With `--store`, templify also keeps the answers in SQLite, Excel or JSON, to re-render
them later. A schema written with `generate` works as it is.

## qrbar-cli

[qrbar-cli](https://github.com/aaltatan/qrbar-cli) prints barcode and QR labels. Its
`-s` option asks for the label records with schemify:

```text
qrbar render -t small.zpl -s item.schema.json
```

Give the quantity property the label `Copies` and a `minimum` of 0, and the person at
the counter types the number of labels for each item.

## The web editor

[schemify.surge.sh](https://schemify.surge.sh) ([source](https://github.com/aaltatan/schemify))
asks the same questions as form fields, with the schema updating as you type. Use it to
design a schema in the browser, save the JSON, then `schemify fill` it in a terminal.
Both follow the same rules, so a schema from one works in the other.

## Validating elsewhere

The schemas are standard Draft 2020-12, so the same file checks data in any language:

=== "Python"

    ```python
    import json

    from jsonschema import Draft202012Validator

    schema = json.load(open("person.schema.json", encoding="utf-8"))
    Draft202012Validator(schema).validate({"first": "Rama", "last": "Hasan", "age": 25})
    ```

=== "JavaScript"

    ```javascript
    import Ajv2020 from "ajv/dist/2020.js";
    import schema from "./person.schema.json" with { type: "json" };

    const validate = new Ajv2020().compile(schema);
    validate({ first: "Rama", last: "Hasan", age: 25 }); // true
    ```

=== "VS Code"

    Point JSON files at the schema in `.vscode/settings.json`, and the editor
    autocompletes and underlines mistakes as you type:

    ```json
    {
      "json.schemas": [
        { "fileMatch": ["people/*.json"], "url": "./person.schema.json" }
      ]
    }
    ```

!!! tip "Formats get patterns"
    `generate` adds a `pattern` next to every `format`, because most validators
    (Ajv without `ajv-formats`, for example) skip `format`. The checks then hold
    everywhere, not only in schemify.
