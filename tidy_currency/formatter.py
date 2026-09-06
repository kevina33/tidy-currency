"""Turn messy currency amount strings into a canonical (value, currency) pair.

Every public function here is pure: same input always gives the same output,
nothing is read from the environment, nothing is mutated in place. That's
what makes normalize() and format_amount() cheap to unit test with plain
tables of (input, expected) pairs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_SYMBOL_TO_CURRENCY = {
    "$": "USD",
    "€": "EUR",  # €
    "£": "GBP",  # £
    "¥": "JPY",  # ¥
}

_CURRENCY_TO_SYMBOL = {code: symbol for symbol, code in _SYMBOL_TO_CURRENCY.items()}

# Codes we recognize when they show up as a bare three-letter token next to
# the number (e.g. "USD 12.50" or "12.50 EUR"). Extend as new formats show up.
_KNOWN_CODES = {
    "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "INR", "MXN",
}

_CODE_PREFIX = re.compile(r"^([A-Za-z]{3})\b")
_CODE_SUFFIX = re.compile(r"\b([A-Za-z]{3})$")


class ParseError(ValueError):
    """Raised when a string can't be read as a currency amount."""


@dataclass(frozen=True)
class NormalizedAmount:
    """A parsed amount: an exact decimal value plus an optional ISO code."""

    value: Decimal
    currency: str | None


def normalize(raw: str, *, default_currency: str | None = None) -> NormalizedAmount:
    """Parse a messy amount string into a NormalizedAmount.

    Handles: leading/trailing currency symbols and ISO codes, thousands
    separators in either comma or dot style, accounting-style negatives
    written as "(12.50)", and stray whitespace.

    `default_currency` is used only when the string itself carries no
    currency marker, so callers can supply one without it silently
    overriding an explicit "EUR 12.50" in the input.
    """
    if raw is None:
        raise ParseError("input is None")

    text = raw.strip()
    if not text:
        raise ParseError("empty input")

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    if text.startswith("-"):
        negative = True
        text = text[1:].strip()
    elif text.startswith("+"):
        text = text[1:].strip()
    if text.endswith("-"):
        negative = True
        text = text[:-1].strip()

    text, found_currency = _extract_currency(text)
    currency = found_currency or default_currency

    if not text:
        raise ParseError(f"no numeric value found in {raw!r}")

    digits = _to_decimal_string(text, raw)

    try:
        value = Decimal(digits)
    except InvalidOperation as exc:
        raise ParseError(f"could not parse a number from {raw!r}") from exc

    if negative:
        value = -value

    return NormalizedAmount(value=value, currency=currency)


def format_amount(amount: NormalizedAmount, *, include_currency: bool = True) -> str:
    """Render a NormalizedAmount as "$1,234.50" style text.

    Always shows exactly two decimal places and comma thousands grouping,
    regardless of how the original input was written.
    """
    quantized = amount.value.quantize(Decimal("0.01"))
    negative = quantized < 0
    quantized = abs(quantized)

    integer_part, _, fraction_part = f"{quantized:f}".partition(".")
    fraction_part = (fraction_part + "00")[:2]
    number = f"{_group_thousands(integer_part)}.{fraction_part}"
    if negative:
        number = f"-{number}"

    if include_currency and amount.currency:
        symbol = _CURRENCY_TO_SYMBOL.get(amount.currency)
        if symbol:
            return f"{symbol}{number}"
        return f"{amount.currency} {number}"

    return number


def _extract_currency(text: str) -> tuple[str, str | None]:
    if not text:
        return text, None

    first, last = text[0], text[-1]
    if first in _SYMBOL_TO_CURRENCY:
        return text[1:].strip(), _SYMBOL_TO_CURRENCY[first]
    if last in _SYMBOL_TO_CURRENCY:
        return text[:-1].strip(), _SYMBOL_TO_CURRENCY[last]

    prefix = _CODE_PREFIX.match(text)
    if prefix and prefix.group(1).upper() in _KNOWN_CODES:
        return text[prefix.end():].strip(), prefix.group(1).upper()

    suffix = _CODE_SUFFIX.search(text)
    if suffix and suffix.group(1).upper() in _KNOWN_CODES:
        return text[:suffix.start()].strip(), suffix.group(1).upper()

    return text, None


def _to_decimal_string(text: str, raw: str) -> str:
    text = text.replace(" ", "").replace("_", "")
    if not text:
        raise ParseError(f"no digits found in {raw!r}")

    has_comma = "," in text
    has_dot = "." in text

    if has_comma and has_dot:
        # Whichever separator appears last is the decimal point; the other
        # one is thousands grouping. Covers both "1,234.50" and "1.234,50".
        if text.rfind(",") > text.rfind("."):
            decimal_sep, thousands_sep = ",", "."
        else:
            decimal_sep, thousands_sep = ".", ","
        text = text.replace(thousands_sep, "").replace(decimal_sep, ".")
    elif has_comma:
        text = _resolve_single_separator(text, ",")
    elif has_dot:
        text = _resolve_single_separator(text, ".")

    if not re.fullmatch(r"-?\d+(\.\d+)?", text):
        raise ParseError(f"could not parse a number from {raw!r}")

    return text


def _resolve_single_separator(text: str, sep: str) -> str:
    parts = text.split(sep)
    if len(parts) == 2 and len(parts[1]) in (1, 2):
        # "12,5" or "12.50" - reads as a decimal point.
        return parts[0] + "." + parts[1]
    # "1,234,567" or "1.234.567" - reads as thousands grouping.
    return "".join(parts)


def _group_thousands(digits: str) -> str:
    groups = []
    while len(digits) > 3:
        groups.append(digits[-3:])
        digits = digits[:-3]
    groups.append(digits)
    return ",".join(reversed(groups))
