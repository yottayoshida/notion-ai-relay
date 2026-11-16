"""Two pure implementations checked against explicit decimal/text boundary vectors."""
from decimal import Decimal
from fractions import Fraction


def source_compare(amounts, threshold, label, expected_label):
    return sum((Decimal(value) for value in amounts), Decimal(0)) > Decimal(threshold) and label == expected_label


def equivalent_compare(amounts, threshold, label, expected_label):
    return sum((Fraction(value) for value in amounts), Fraction(0)) > Fraction(threshold) and label == expected_label


VECTORS = [
    {"amounts": ["0.1", "0.2"], "threshold": "0.3", "label": "x", "expected_label": "x"},
    {"amounts": ["0.1", "0.2000001"], "threshold": "0.3", "label": "x", "expected_label": "x"},
    {"amounts": [], "threshold": "0", "label": "x", "expected_label": "x"},
    {"amounts": ["-0.1", "-0.2"], "threshold": "-0.3", "label": "x", "expected_label": "x"},
    {"amounts": ["1"], "threshold": "0", "label": "e\u0301", "expected_label": "é"},
    {"amounts": ["1"], "threshold": "0", "label": "é", "expected_label": "é"},
]
EXPECTED = [False, True, False, False, False, True]
