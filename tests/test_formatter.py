import unittest
from decimal import Decimal

from tidy_currency import NormalizedAmount, ParseError, format_amount, normalize


class NormalizeTests(unittest.TestCase):
    def test_plain_symbol_prefix(self):
        self.assertEqual(normalize("$1,234.50"), NormalizedAmount(Decimal("1234.50"), "USD"))

    def test_iso_code_suffix(self):
        self.assertEqual(normalize("1234.50 EUR"), NormalizedAmount(Decimal("1234.50"), "EUR"))

    def test_european_style_separators(self):
        self.assertEqual(normalize("1.234,50"), NormalizedAmount(Decimal("1234.50"), None))

    def test_accounting_negative(self):
        self.assertEqual(normalize("($42.00)"), NormalizedAmount(Decimal("-42.00"), "USD"))

    def test_trailing_minus(self):
        self.assertEqual(normalize("42.00-"), NormalizedAmount(Decimal("-42.00"), None))

    def test_default_currency_only_fills_gaps(self):
        result = normalize("EUR 10", default_currency="USD")
        self.assertEqual(result.currency, "EUR")

    def test_default_currency_applies_when_absent(self):
        result = normalize("10.00", default_currency="USD")
        self.assertEqual(result.currency, "USD")

    def test_whitespace_and_underscores(self):
        self.assertEqual(normalize(" 1_000.00 "), NormalizedAmount(Decimal("1000.00"), None))

    def test_rupee_symbol(self):
        self.assertEqual(normalize("₹1,234.50"), NormalizedAmount(Decimal("1234.50"), "INR"))

    def test_won_symbol(self):
        self.assertEqual(normalize("50000₩"), NormalizedAmount(Decimal("50000"), "KRW"))

    def test_newer_iso_code(self):
        result = normalize("1500 ZAR")
        self.assertEqual(result.currency, "ZAR")

    def test_ambiguous_dollar_disambiguated_by_code(self):
        # "$" alone can't tell CAD from USD; a following ISO code should win.
        result = normalize("CAD 10.00")
        self.assertEqual(result.currency, "CAD")

    def test_empty_string_raises(self):
        with self.assertRaises(ParseError):
            normalize("   ")

    def test_garbage_raises(self):
        with self.assertRaises(ParseError):
            normalize("not a number")

    def test_ambiguous_dot_defaults_to_thousands(self):
        # Three digits after a single separator reads as grouping by
        # default: "1.234" is one thousand two hundred thirty-four.
        self.assertEqual(normalize("1.234"), NormalizedAmount(Decimal("1234"), None))

    def test_decimal_separator_hint_overrides_default(self):
        result = normalize("1.234", decimal_separator=".")
        self.assertEqual(result.value, Decimal("1.234"))

    def test_decimal_separator_hint_confirms_thousands(self):
        result = normalize("1,234", decimal_separator=".")
        self.assertEqual(result.value, Decimal("1234"))

    def test_decimal_separator_hint_ignored_with_repeated_group(self):
        # Two commas can't both be decimal points, so the hint doesn't
        # change anything here - it's still thousands grouping.
        result = normalize("1,234,567", decimal_separator=",")
        self.assertEqual(result.value, Decimal("1234567"))

    def test_decimal_separator_hint_ignored_when_both_separators_present(self):
        result = normalize("1.234,50", decimal_separator=".")
        self.assertEqual(result.value, Decimal("1234.50"))

    def test_invalid_decimal_separator_raises(self):
        with self.assertRaises(ValueError):
            normalize("1.234", decimal_separator=";")


class FormatAmountTests(unittest.TestCase):
    def test_formats_with_symbol(self):
        amount = NormalizedAmount(Decimal("1234.5"), "USD")
        self.assertEqual(format_amount(amount), "$1,234.50")

    def test_formats_negative(self):
        amount = NormalizedAmount(Decimal("-42"), "USD")
        self.assertEqual(format_amount(amount), "-$42.00")

    def test_formats_unknown_code_without_symbol(self):
        amount = NormalizedAmount(Decimal("10"), "INR")
        self.assertEqual(format_amount(amount), "INR 10.00")

    def test_can_omit_currency(self):
        amount = NormalizedAmount(Decimal("10"), "USD")
        self.assertEqual(format_amount(amount, include_currency=False), "10.00")


if __name__ == "__main__":
    unittest.main()
