# Recipes

Complete, real-world jobs. The schemas and the scripted answers of every session here
are in [`examples/`](https://github.com/aaltatan/schemify-cli/tree/main/examples), and
the test suite replays each session to check that this page stays true.

## An invoice with line items

**Job:** a schema for invoices: a number in a fixed shape, an issue date, a status from a
list, a customer, at least one line with a quantity and a price, and a paid flag.

```text
schemify generate -t Invoice -o invoice.schema.json
```

??? example "The full session (112 answers)"

    ```text
    ? Property name (empty to finish): number
    ? Type of 'number': string
    ? Format: none
    ? Add validators? Yes
    ? Limit to choices? No
    ? Digits only? No
    ? Minimum length (optional):
    ? Maximum length (optional):
    ? Regular expression pattern (optional): ^INV-[0-9]{4}$
    ? Blocked values, comma separated (optional):
    ? Label shown instead of 'number' when filling (optional): Invoice number
    ? Description of 'number' (optional): INV- and 4 digits
    ? Default value of 'number' (optional):
    ? Is 'number' required? Yes

    ? Property name (empty to finish): issued
    ? Type of 'issued': string
    ? Format: date
    ? Label shown instead of 'issued' when filling (optional): Issue date
    ? Description of 'issued' (optional):
    ? Default value of 'issued' (optional):
    ? Is 'issued' required? Yes

    ? Property name (empty to finish): status
    ? Type of 'status': string
    ? Format: none
    ? Add validators? Yes
    ? Limit to choices? Yes
    ? Choice (empty to finish): draft
    ? Choice (empty to finish): sent
    ? Choice (empty to finish): paid
    ? Choice (empty to finish):
    ? Label shown instead of 'status' when filling (optional): Status
    ? Description of 'status' (optional):
    ? Default value of 'status' (optional): draft
    ? Is 'status' required? Yes

    ? Property name (empty to finish): customer
    ? Type of 'customer': object
    ? Property name (empty to finish): name
    ? Type of 'name': string
    ? Format: none
    ? Add validators? No
    ? Label shown instead of 'name' when filling (optional): Customer name
    ? Description of 'name' (optional):
    ? Default value of 'name' (optional):
    ? Is 'name' required? Yes

    ? Property name (empty to finish): email
    ? Type of 'email': string
    ? Format: email
    ? Label shown instead of 'email' when filling (optional): Email
    ? Description of 'email' (optional):
    ? Default value of 'email' (optional):
    ? Is 'email' required? No

    ? Property name (empty to finish):
    ? Allow extra properties? No
    ? Label shown instead of 'customer' when filling (optional): Customer
    ? Description of 'customer' (optional):
    ? Default value of 'customer' (optional):
    ? Is 'customer' required? Yes

    ? Property name (empty to finish): lines
    ? Type of 'lines': array
    ? Items type: object
    ? Property name (empty to finish): product
    ? Type of 'product': string
    ? Format: none
    ? Add validators? No
    ? Label shown instead of 'product' when filling (optional): Product
    ? Description of 'product' (optional):
    ? Default value of 'product' (optional):
    ? Is 'product' required? Yes

    ? Property name (empty to finish): qty
    ? Type of 'qty': integer
    ? Add validators? Yes
    ? Limit to choices? No
    ? Greater than (optional):
    ? Greater than or equal to (optional): 1
    ? Less than (optional):
    ? Less than or equal to (optional):
    ? Multiple of (optional):
    ? Label shown instead of 'qty' when filling (optional): Quantity
    ? Description of 'qty' (optional):
    ? Default value of 'qty' (optional): 1
    ? Is 'qty' required? Yes

    ? Property name (empty to finish): price
    ? Type of 'price': number
    ? Add validators? Yes
    ? Limit to choices? No
    ? Greater than (optional): 0
    ? Greater than or equal to (optional):
    ? Less than (optional):
    ? Less than or equal to (optional):
    ? Multiple of (optional): 0.01
    ? Label shown instead of 'price' when filling (optional): Unit price
    ? Description of 'price' (optional): USD
    ? Default value of 'price' (optional):
    ? Is 'price' required? Yes

    ? Property name (empty to finish):
    ? Allow extra properties? No
    ? Add validators? Yes
    ? Minimum items (optional): 1
    ? Maximum items (optional):
    ? Unique items? No
    ? Label shown instead of 'lines' when filling (optional): Lines
    ? Description of 'lines' (optional):
    ? Default value of 'lines' (optional):
    ? Is 'lines' required? Yes

    ? Property name (empty to finish): paid
    ? Type of 'paid': boolean
    ? Label shown instead of 'paid' when filling (optional): Paid
    ? Description of 'paid' (optional):
    ? Default value of 'paid' (optional): false
    ? Is 'paid' required? No

    ? Property name (empty to finish):
    ? Allow extra properties? No
    ```

The result is
[`examples/invoice.schema.json`](https://github.com/aaltatan/schemify-cli/blob/main/examples/invoice.schema.json).
Its key parts:

| Property | Schema |
|----------|--------|
| `number` | `"pattern": "^INV-[0-9]{4}$"` |
| `issued` | `"format": "date"` and a date `pattern` |
| `status` | `"enum": ["draft", "sent", "paid"], "default": "draft"` |
| `customer` | an object with a required `name` and an optional `email` |
| `lines` | an array of `{product, qty, price}` objects, `"minItems": 1` |
| `lines[].qty` | `"minimum": 1, "default": 1` |
| `lines[].price` | `"exclusiveMinimum": 0, "multipleOf": 0.01` |
| `paid` | an optional boolean, `"default": false` |

Now fill one invoice:

```text
$ schemify fill invoice.schema.json -o invoice.json
? Invoice number (INV- and 4 digits): INV-12
  >> 'INV-12' does not match '^INV-[0-9]{4}$'
? Invoice number (INV- and 4 digits): INV-0042
? Issue date: 2026-11-31
  >> day is out of range for month
? Issue date: 2026-11-26
? Status: sent
? Customer name: Example Co.
? Email: billing@example
  >> 'billing@example' does not match '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'
? Email: billing@example.com
? Product: Desk lamp
? Quantity: 3
? Unit price (USD): 24.5
? Add an item to 'Lines'? Yes
? Product: LED bulb
? Quantity: 10
? Unit price (USD): 3.999
  >> 3.999 is not a multiple of 0.01
? Unit price (USD): 3.75
? Add an item to 'Lines'? No
? Add 'Paid'? Yes
? Paid: No
Saved to: .../invoice.json
```

```json
{
  "number": "INV-0042",
  "issued": "2026-11-26",
  "status": "sent",
  "customer": {
    "name": "Example Co.",
    "email": "billing@example.com"
  },
  "lines": [
    {
      "product": "Desk lamp",
      "qty": 3,
      "price": 24.5
    },
    {
      "product": "LED bulb",
      "qty": 10,
      "price": 3.75
    }
  ],
  "paid": false
}
```

- The first line was asked without "Add an item?", because of `minItems: 1`.
- `Quantity` started at `1` (its default), and `Status` on `draft`.
- The email error shows the `pattern`, since `generate` adds one to every format.

## An event registration form

**Job:** collect registrations at a desk: a uuid, a name, an email, a ticket type, a
number of seats from 1 to 4, an arrival time, up to 3 unique topics, and a newsletter
opt-in that defaults to yes. This one is written by hand, to use number choices and
`uuid`; see [Writing schemas by hand](guide/hand-written.md).

```text
schemify fill registration.schema.json -o registration.json
```

To collect a whole day's registrations into one file, use `list`:

```text
schemify list registration.schema.json -o registrations.json
```

## Test fixtures for a frontend

**Job:** a few realistic objects for a component test, as JavaScript, without writing
them by hand.

```text
$ schemify list person.schema.json -f javascript -o people.fixture.js
```

```javascript
[
  {
    first: "Rama",
    last: "Hasan",
    age: 25
  },
  {
    first: "Omar",
    last: "Ali"
  }
]
```

Add `export default` in front, and import it in the test. Every fixture is valid for
the schema, so it is also valid for the API that uses the same schema.

## Seed data for a Python project

```text
$ schemify list person.schema.json -f python -o seed_people.py
```

```python
[{'first': 'Rama', 'last': 'Hasan', 'age': 25},
 {'first': 'Omar', 'last': 'Ali'}]
```

Put `PEOPLE = ` in front, and load it in a Django fixture command, a pytest fixture or a
script.

## A config file people can fill

**Job:** a tool needs a JSON config, and the people setting it up should not have to
learn its keys. Ship a schema with labels, descriptions and defaults, and let them
answer questions:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Printer settings",
  "type": "object",
  "properties": {
    "host": { "title": "Printer address", "description": "IP or host name", "type": "string", "default": "192.168.1.50" },
    "port": { "title": "Port", "type": "integer", "minimum": 1, "maximum": 65535, "default": 9100 },
    "dpi": { "title": "Resolution", "enum": [203, 300, 600], "default": 203 },
    "darkness": { "title": "Darkness", "description": "0 to 30", "type": "integer", "minimum": 0, "maximum": 30, "default": 15 },
    "cut": { "title": "Cut after each label", "type": "boolean", "default": false }
  },
  "required": ["host", "port", "dpi"],
  "additionalProperties": false
}
```

```text
schemify fill printer.schema.json -o printer.json
```

Every question starts on the default, so ++enter++ ++enter++ ++enter++ accepts a standard
setup, and only the different values are typed.

## Questions for templify and qrbar-cli

**Job:** HR issues employment certificates at the desk with
[templify](https://github.com/aaltatan/templify), and the person issuing them should
answer questions, not edit Excel.

1. Build the schema:

    ```text
    schemify generate -t Person -o person.schema.json
    ```

2. Check the questions by filling one record:

    ```text
    schemify fill person.schema.json
    ```

3. Use it with templify, keeping every answer in a register:

    ```text
    templify render --object -t certificate.docx -s person.schema.json --store people.sqlite
    ```

The same works for label quantities with
[qrbar-cli](https://github.com/aaltatan/qrbar-cli): `qrbar render -t small.zpl -s item.schema.json`.
