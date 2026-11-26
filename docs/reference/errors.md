# Errors and exit codes

| Exit | Meaning |
|------|---------|
| `0` | Done |
| `1` | Stopped: ++ctrl+c++ (`Aborted.`), or **No** to overwriting the output file |
| `2` | Bad input: a missing or invalid schema file, a schema `fill` cannot handle, an unknown format |

Nothing is written when a command stops or fails.

## Answers refused while typing

These appear under the prompt. Type the answer again: nothing is lost.

### In `generate`

| Message | Means |
|---------|-------|
| `Add at least one property` | An object needs one property before the name can be left empty |
| `Property 'a' already exists` | Property names are unique within an object |
| `Add at least one choice` | A choice list needs one choice before an empty answer finishes it |
| `Choice 'x' already exists` | Choices are unique |
| `'abc' is not an integer` / `'abc' is not a number` | A bound, length or choice of the wrong type |
| `'-1' must be 0 or more` | Lengths and item counts are 0 or more |
| `'0' must be greater than 0` | `Multiple of` |
| `minimum (10) must be less than maximum (5)` | The bounds leave no possible value |
| `Invalid regular expression: unterminated character set at position 0` | The pattern does not compile |
| `Choices must be unique` / `Enter at least one choice` | Blocked values |
| a schema message, e.g. `0 is less than the minimum of 1` | A default that breaks the property's own rules |

### In `fill` and `list`

| Message | Means |
|---------|-------|
| `This value is required` | A required text answer was left empty |
| `'abc' is not an integer` / `'abc' is not a number` | Numbers are parsed first |
| `day is out of range for month`, `Invalid isoformat string: ...` | Not a real ISO date or date-time |
| `-3 is less than the minimum of 0` | `minimum` (also `maximum`, `exclusiveMinimum`, ...) |
| `3.999 is not a multiple of 0.01` | `multipleOf` |
| `'R' is too short` / `... is too long` | `minLength` / `maxLength` |
| `'INV-12' does not match '^INV-[0-9]{4}$'` | `pattern` |
| `'1234' is not a 'uuid'` | `format` |
| `'lighting' is already in 'Topics'` | `uniqueItems`: the repeated item is not added |

## Errors that stop the command

| Message | Exit | Fix |
|---------|------|-----|
| `Invalid value for 'path': file 'nope.json' does not exist.` | 2 | Check the path |
| `Could not read schema file 'broken.json': Expecting property name enclosed in double quotes: ...` | 2 | The file is not valid JSON |
| `Invalid schema file 'list.json': A schema must be a JSON object` | 2 | The top level must be `{...}` |
| `Invalid schema file 'bad.schema.json': 'nope' is not valid under any of the given schemas` | 2 | Not a valid Draft 2020-12 schema; here `"type": "nope"` |
| `Can not fill 'x': Schema kind 'None' is not supported, supported: array, boolean, date, date-time, enum, integer, number, object, string` | 2 | Property `x` has no `type`, `enum` or known `format` (for example a `$ref` or `oneOf`). See [Writing schemas by hand](../guide/hand-written.md#what-it-does-not-understand) |
| a schema message after the last question, e.g. `'b' is a dependency of 'a'` | 2 | The whole value breaks a rule no prompt asks about (`dependentRequired`, `allOf`, ...) |
| `Invalid value for '-f' / '--format': Format 'yaml' is not supported, supported: javascript, json, python` | 2 | Use a supported format |
| `'rama.json' already exists, overwrite it?` answered **No** | 1 | Pick another `-o`, or answer **Yes** |
| `Aborted.` | 1 | ++ctrl+c++ was pressed |
