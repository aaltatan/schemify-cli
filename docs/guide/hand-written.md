# Writing schemas by hand

`fill` and `list` work with **any** valid JSON Schema object, not only the ones
`generate` writes. Hand-written schemas can use keywords `generate` never asks about,
like number choices, `uuid`, or `allOf`.

[`examples/registration.schema.json`](https://github.com/aaltatan/schemify-cli/blob/main/examples/registration.schema.json)
is an event registration form, written by hand:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Registration",
  "type": "object",
  "properties": {
    "id": { "title": "Registration id", "type": "string", "format": "uuid" },
    "attendee": { "title": "Full name", "type": "string", "minLength": 2 },
    "email": { "title": "Email", "type": "string", "format": "email" },
    "ticket": { "title": "Ticket", "enum": ["standard", "vip", "student"], "default": "standard" },
    "seats": { "title": "Seats", "type": "integer", "enum": [1, 2, 3, 4], "default": 1 },
    "arrival": { "title": "Arrival", "description": "ISO date and time", "type": "string", "format": "date-time" },
    "topics": {
      "title": "Topics",
      "type": "array",
      "items": { "title": "Topic", "type": "string" },
      "maxItems": 3,
      "uniqueItems": true
    },
    "newsletter": { "title": "Subscribe to the newsletter", "type": "boolean", "default": true }
  },
  "required": ["id", "attendee", "email", "ticket", "seats"],
  "additionalProperties": false
}
```

```text
$ schemify fill registration.schema.json -o registration.json
? Registration id: 1234
  >> '1234' is not a 'uuid'
? Registration id: 0b7e2c1a-4b7e-4d2f-9a0e-2f4c9d1e8b11
? Full name: R
  >> 'R' is too short
? Full name: Rama Hasan
? Email: rama@example.com
? Ticket: vip
? Seats: 2
? Arrival (ISO date and time): 2026-12-01T09:30:00+03:00
? Add 'Topics'? Yes
? Add an item to 'Topics'? Yes
? Topic: lighting
? Add an item to 'Topics'? Yes
? Topic: lighting
  'lighting' is already in 'Topics'
? Add an item to 'Topics'? Yes
? Topic: design
? Add an item to 'Topics'? No
? Add 'Subscribe to the newsletter'? Yes
? Subscribe to the newsletter: Yes
Saved to: .../registration.json
```

```json
{
  "id": "0b7e2c1a-4b7e-4d2f-9a0e-2f4c9d1e8b11",
  "attendee": "Rama Hasan",
  "email": "rama@example.com",
  "ticket": "vip",
  "seats": 2,
  "arrival": "2026-12-01T09:30:00+03:00",
  "topics": [
    "lighting",
    "design"
  ],
  "newsletter": true
}
```

- `"seats"` is a choice of **numbers**: the list shows `1` to `4`, and the saved value
  is the number `2`, not the text `"2"`. Choices can be any JSON value.
- `"ticket"` has no `type`: an `enum` is enough.
- `"email"` and `"id"` have a `format` but no `pattern`: schemify checks formats itself.

## What `fill` understands

| Keyword | Used for |
|---------|----------|
| `type` | `string`, `integer`, `number`, `boolean`, `array`, `object` |
| `enum` | A list to pick from (any JSON values) |
| `format` | `date` and `date-time` get their own prompts; `email`, `uuid`, `ipv4`, `ipv6`, `time` and `regex` are checked |
| `properties`, `required` | The questions, in order, and which can be skipped |
| `items`, `minItems`, `maxItems`, `uniqueItems` | The item loop |
| `title`, `description` | The question text |
| `default` | The starting answer |
| everything else that applies to one value | Checked on each answer: `minLength`, `pattern`, `minimum`, `multipleOf`, `not`, `const`, ... |
| keywords about the whole value | Checked once at the end: `allOf`, `dependentRequired`, `if` / `then`, ... |

A value that passes every prompt but fails a whole-value rule stops `fill` with that
rule's message, and nothing is saved.

## What it does not understand

A property needs a `type`, an `enum`, or a `format` that schemify knows. These have
none of them, so `fill` cannot pick a prompt:

| Keyword | Instead |
|---------|---------|
| `$ref` / `$defs` | Copy the referenced schema in place |
| `oneOf`, `anyOf` | Pick one shape, or use an `enum` of choices |
| `type: ["string", "null"]` | Make the property optional |

`fill` stops with this error when it reaches such a property, and nothing is saved:

```text
Invalid value: Can not fill 'x': Schema kind 'None' is not supported, supported: array, boolean, date, date-time, enum, integer, number, object, string
```

`'x'` is the path of the property. A custom prompt for such a kind can be added in
Python: see [Python API](../python.md#a-new-kind-of-prompt).

## A valid schema first

The file must be a JSON object and a valid Draft 2020-12 schema:

```text
Invalid value: Could not read schema file 'broken.json': Expecting property name enclosed in double quotes: line 2 column 1 (char 2)
Invalid value: Invalid schema file 'bad.schema.json': 'nope' is not valid under any of the given schemas
Invalid value: Invalid schema file 'list.json': A schema must be a JSON object
```
