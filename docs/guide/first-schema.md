# Your first schema

We will build the schema of a **Person** with a first name, a last name, and an
optional age between 0 and 150.

```text
schemify generate -t Person -o person.schema.json
```

- `-t Person` is the schema's `title`. Tools such as templify use it to name tables.
- `-o person.schema.json` saves the schema. Without it, the schema is printed.

![schemify generate](../demo/generate.gif)

## The session

schemify asks about one property at a time, until you leave the name empty:

```text
? Property name (empty to finish): first
? Type of 'first': string
? Format: none
? Add validators? No
? Label shown instead of 'first' when filling (optional): First name
? Description of 'first' (optional):
? Default value of 'first' (optional):
? Is 'first' required? Yes

? Property name (empty to finish): last
? Type of 'last': string
? Format: none
? Add validators? No
? Label shown instead of 'last' when filling (optional): Last name
? Description of 'last' (optional):
? Default value of 'last' (optional):
? Is 'last' required? Yes

? Property name (empty to finish): age
? Type of 'age': integer
? Add validators? Yes
? Limit to choices? No
? Greater than (optional):
? Greater than or equal to (optional): 0
? Less than (optional):
? Less than or equal to (optional): 150
? Multiple of (optional):
? Label shown instead of 'age' when filling (optional): Age
? Description of 'age' (optional): In whole years
? Default value of 'age' (optional):
? Is 'age' required? No

? Property name (empty to finish):
? Allow extra properties? No
Saved to: .../person.schema.json
```

## What each question does

| Question | Writes | Notes |
|----------|--------|-------|
| Property name | a key in `properties` | Empty finishes the object (after at least one property). A name already used is refused. |
| Type | `type` | `string`, `integer`, `number`, `boolean`, `array` or `object` |
| Format, validators, choices | `format`, `minimum`, `pattern`, `enum`, ... | Depends on the type: see [Types and constraints](types.md) |
| Label | `title` | Shown instead of the property name when filling: `First name:` instead of `first:` |
| Description | `description` | Shown after the label when filling: `Age (In whole years):` |
| Default value | `default` | Pre-filled when filling. Checked against the property's own rules. |
| Is it required? | `required` | An optional property can be skipped when filling |
| Allow extra properties? | `additionalProperties: false` when **No** | No keeps the data to exactly these fields |

Empty optional answers write nothing, so the schema stays small.

## The result

[`examples/person.schema.json`](https://github.com/aaltatan/schemify-cli/blob/main/examples/person.schema.json):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Person",
  "type": "object",
  "properties": {
    "first": {
      "title": "First name",
      "type": "string"
    },
    "last": {
      "title": "Last name",
      "type": "string"
    },
    "age": {
      "title": "Age",
      "description": "In whole years",
      "type": "integer",
      "minimum": 0,
      "maximum": 150
    }
  },
  "required": [
    "first",
    "last"
  ],
  "additionalProperties": false
}
```

It is a standard JSON Schema: any validator in any language reads it, and editors such
as VS Code use it for autocompletion of JSON files.

## Fill it

```text
$ schemify fill person.schema.json -o rama.json
? First name: Rama
? Last name: Hasan
? Age (In whole years): -3
  >> -3 is less than the minimum of 0
? Age (In whole years): 25
Saved to: .../rama.json
```

```json
{
  "first": "Rama",
  "last": "Hasan",
  "age": 25
}
```

The `-3` was refused by the `minimum` you set in `generate`. Next, see everything each
type can ask in [Types and constraints](types.md), or how filling works in
[Filling data](fill.md).

## When the file exists

If the `-o` file already exists, schemify asks **before** the questions start, not
after you have answered them all:

```text
? 'person.schema.json' already exists, overwrite it? [y/N]
```
