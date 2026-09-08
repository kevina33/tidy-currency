# tidy-currency

Currency amounts that come from CSV exports, pasted spreadsheets, or free-text
form fields are rarely consistent. The same value shows up as `$1,234.50`,
`1.234,50`, `EUR 1234.5`, `(42.00)` for a negative, or `1_000.00` copied out
of some other tool. Comparing or summing these directly is a bug waiting to
happen.

`tidy_currency` parses that mess into one canonical shape - a `Decimal`
value plus an optional ISO currency code - and can render it back out as a
clean, consistent string.

## Usage

```python
from tidy_currency import normalize, format_amount

normalize("$1,234.50")
# NormalizedAmount(value=Decimal('1234.50'), currency='USD')

normalize("1.234,50 EUR")
# NormalizedAmount(value=Decimal('1234.50'), currency='EUR')

normalize("(42.00)")
# NormalizedAmount(value=Decimal('-42.00'), currency=None)

amount = normalize("1234.5", default_currency="USD")
format_amount(amount)
# '$1,234.50'
```

`normalize()` and `format_amount()` are plain pure functions: given the same
input they always return the same output, and neither touches the
filesystem, the clock, or any global state. That's deliberate - it's what
lets the whole parser be tested with a table of (input, expected) pairs,
and what makes it safe to run over untrusted user input.

## What it currently handles

- Currency symbols (`$`, `€`, `£`, `¥`, `₹`, `₩`, `₽`, `₺`, `₴`, `₫`, `₪`,
  `₦`, `₱`, `฿`, `₡`, `₲`, `₵`, `₸`) and around 60 three-letter ISO codes, as
  a prefix or a suffix
- Comma or dot as the decimal separator, detected from context
- Thousands grouping in either style (`1,234.50` and `1.234,50`)
- Negative amounts written as `-42`, `42-`, or accounting-style `(42.00)`
- Stray whitespace and underscore digit separators (`1_000.00`)

Amounts that can't be read as a number raise `tidy_currency.ParseError`
rather than guessing.

## Status

Early skeleton. The separator-detection heuristics cover the common cases
but haven't been checked against a large real-world sample yet, and
formatting doesn't yet know that some currencies (like JPY) aren't normally
written with decimal places. See the roadmap in the project notes for
what's planned next.

## License

MIT, see [LICENSE](LICENSE).
