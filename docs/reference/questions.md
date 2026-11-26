# Questions and keywords

Every question `schemify generate` asks, in order, and the JSON Schema keyword its answer
writes. Empty answers to optional questions write nothing.

## Each property

| Question | Answer | Writes |
|----------|--------|--------|
| `Property name (empty to finish):` | text; empty finishes once there is one property | a key in `properties` |
| `Type of '<name>':` | `array`, `boolean`, `integer`, `number`, `object`, `string` | `type`, then the [type's questions](#by-type) |
| `Label shown instead of '<name>' when filling (optional):` | text | `title` |
| `Description of '<name>' (optional):` | text | `description` |
| `Default value of '<name>' (optional):` | JSON or text, checked against the property | `default` |
| `Is '<name>' required?` | Yes / No (default Yes) | the name in `required` |

After the last property:

| Question | Answer | Writes |
|----------|--------|--------|
| `Allow extra properties?` | Yes / No (default No) | `"additionalProperties": false` when **No** |

## By type

### string

| Question | Answer | Writes |
|----------|--------|--------|
| `Format:` | `none`, `date`, `date-time`, `email`, `uuid` | `format` and its `pattern`; a format ends the string questions |
| `Add validators?` | Yes / No (default No) | |
| `Limit to choices?` | Yes / No (default No) | |
| `Choice (empty to finish):` | text, unique, one per prompt | `enum`; choices end the string questions |
| `Digits only?` | Yes / No (default No) | `"pattern": "^[0-9]+$"` (and skips the pattern question) |
| `Minimum length (optional):` | an integer ≥ 0 | `minLength` |
| `Maximum length (optional):` | an integer ≥ 0, not below the minimum | `maxLength` |
| `Regular expression pattern (optional):` | a regular expression that compiles | `pattern` |
| `Blocked values, comma separated (optional):` | `a, b, c`, unique | `"not": {"enum": [...]}` |

The patterns written for each format:

| Format | `pattern` |
|--------|-----------|
| `date` | `^[0-9]{4}-(0[1-9]\|1[0-2])-(0[1-9]\|[12][0-9]\|3[01])$` |
| `date-time` | the date, then `[Tt]`, a 24-hour time with optional fraction, and `Z` or an offset |
| `email` | `^[^@\s]+@[^@\s]+\.[^@\s]+$` |
| `uuid` | `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$` |

### integer and number

| Question | Answer | Writes |
|----------|--------|--------|
| `Add validators?` | Yes / No (default No) | |
| `Limit to choices?` | Yes / No (default No) | |
| `Choice (empty to finish):` | an integer (or number), unique | `enum`; choices end the questions |
| `Greater than (optional):` | a number | `exclusiveMinimum` |
| `Greater than or equal to (optional):` | a number | `minimum` |
| `Less than (optional):` | a number | `exclusiveMaximum` |
| `Less than or equal to (optional):` | a number | `maximum` |
| `Multiple of (optional):` | a number > 0 | `multipleOf` |

A bound that leaves no possible value is refused:
`minimum (10) must be less than maximum (5)`.

### boolean

No questions: `{"type": "boolean"}`.

### array

| Question | Answer | Writes |
|----------|--------|--------|
| `Items type:` | any type, then that type's questions | `items` |
| `Add validators?` | Yes / No (default No) | |
| `Minimum items (optional):` | an integer ≥ 0 | `minItems` |
| `Maximum items (optional):` | an integer ≥ 0, not below the minimum | `maxItems` |
| `Unique items?` | Yes / No (default No) | `"uniqueItems": true` |

### object

The [property questions](#each-property) again, for the object's own properties, ending
with its own `Allow extra properties?`.

## The top level

The schema is always an object, with:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "<the -t title, when given>",
  "type": "object",
  "properties": { ... },
  "required": [ ... ],
  "additionalProperties": false
}
```

`required` is left out when no property is required, and `additionalProperties` when
extra properties are allowed.
