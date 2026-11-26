# Types and constraints

After `Type of '<name>'`, `generate` asks questions that depend on the type. Every
answer becomes a standard JSON Schema keyword. Empty answers are skipped.

| Type | Asks for |
|------|----------|
| [`string`](#string) | A format, or choices, or digits only, lengths, a pattern and blocked values |
| [`integer`, `number`](#integer-and-number) | Choices, or bounds and a multiple |
| [`boolean`](#boolean) | Nothing |
| [`array`](#array) | The items' type, then a minimum and maximum size, and unique items |
| [`object`](#object) | Its own properties, like the top level |

## string

```text
? Format: none
```

| Format | Writes | Accepts when filling |
|--------|--------|----------------------|
| `none` | `{"type": "string"}`, then the [validators](#string-validators) | any text |
| `date` | `format: date` and a matching `pattern` | `2026-11-26` |
| `date-time` | `format: date-time` and a matching `pattern` | `2026-11-26T09:30:00+03:00` |
| `email` | `format: email` and a matching `pattern` | `rama@example.com` |
| `uuid` | `format: uuid` and a matching `pattern` | `0b7e2c1a-4b7e-4d2f-9a0e-2f4c9d1e8b11` |

A format comes with a `pattern` because most validators treat `format` as a hint
only, while every validator checks `pattern`. The patterns use plain character classes,
so they mean the same in JavaScript, Python, Go, Rust, Java and .NET.

!!! note "Dates and the calendar"
    The `date` pattern checks the shape (`2026-02-31` passes the pattern). schemify's
    own `fill` also checks the calendar, so `2026-11-31` is refused there:
    `day is out of range for month`.

### string validators

With **Format: none** and **Add validators? Yes**:

```text
? Limit to choices? No
? Digits only? No
? Minimum length (optional):
? Maximum length (optional):
? Regular expression pattern (optional): ^INV-[0-9]{4}$
? Blocked values, comma separated (optional):
```

| Question | Writes | Example |
|----------|--------|---------|
| Limit to choices? **Yes** | `enum`, one choice per prompt until an empty one | `["draft", "sent", "paid"]` |
| Digits only? | `pattern: ^[0-9]+$` | phone numbers, ZIP codes with leading zeros |
| Minimum length | `minLength` | `2` |
| Maximum length | `maxLength` | `50` |
| Regular expression pattern | `pattern` (checked to compile) | `^INV-[0-9]{4}$` |
| Blocked values | `not: {"enum": [...]}` | `admin, root` |

Choices skip the other validators: a value from a fixed list needs no length or
pattern. **Digits only** replaces the pattern question. A minimum length larger than the
maximum is refused on the spot, so you fix that one answer instead of starting over.

## integer and number

`integer` takes whole numbers, `number` any finite number.

```text
? Add validators? Yes
? Limit to choices? No
? Greater than (optional): 0
? Greater than or equal to (optional):
? Less than (optional):
? Less than or equal to (optional):
? Multiple of (optional): 0.01
```

| Question | Writes |
|----------|--------|
| Limit to choices? **Yes** | `enum` of numbers: `[1, 2, 3, 4]` |
| Greater than | `exclusiveMinimum` |
| Greater than or equal to | `minimum` |
| Less than | `exclusiveMaximum` |
| Less than or equal to | `maximum` |
| Multiple of | `multipleOf` (greater than 0) |

Bounds that leave no possible value (greater than 10 and less than 5) are refused
as you type them. `multipleOf: 0.01` is a common way to say "at most two decimals"
for prices.

## boolean

No extra questions: `{"type": "boolean"}`. A default of `true` or `false` makes the
yes/no prompt start on that answer.

## array

```text
? Type of 'lines': array
? Items type: object
  ... the questions of the item type ...
? Add validators? Yes
? Minimum items (optional): 1
? Maximum items (optional):
? Unique items? No
```

| Question | Writes |
|----------|--------|
| Items type | `items`, built with the same questions as any property |
| Minimum items | `minItems` |
| Maximum items | `maxItems` |
| Unique items? | `uniqueItems: true` |

Items can be any type, including objects (a list of invoice lines) and arrays (a
grid). Labels and defaults are asked for the array itself, not for its items.

## object

An `object` property asks for its own properties, exactly like the top level, ending
with its own `Allow extra properties?`. Then come the label, description, default and
required questions of the object property itself. Objects nest to any depth.

```text
? Property name (empty to finish): customer
? Type of 'customer': object
? Property name (empty to finish): name
...
? Property name (empty to finish):
? Allow extra properties? No
? Label shown instead of 'customer' when filling (optional): Customer
```

## Defaults

`Default value of '<name>'` takes JSON or plain text, and keeps the first reading that
fits the property:

| Property | Answer | Saved default |
|----------|--------|---------------|
| `integer` | `1` | `1` |
| `string` | `42` | `"42"` (the text, since `42` is not a string) |
| `boolean` | `false` | `false` |
| `array` of strings | `["a", "b"]` | `["a", "b"]` |
| choices `draft, sent, paid` | `draft` | `"draft"` |
| `integer` with minimum 1 | `0` | refused: `0 is less than the minimum of 1` |

A complete example with every type is the
[invoice recipe](../recipes.md#an-invoice-with-line-items). The question-by-question list
is in [Questions and keywords](../reference/questions.md).
