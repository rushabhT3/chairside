from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from chairside_agent.core.models import Extraction, Plan, QuarantineVerdict

INSTRUCTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore (all )?previous",
        r"disregard",
        r"approve all",
        r"sign (this|all|now)",
        r"you are an? (ai|assistant|agent)",
        r"system prompt",
        r"override",
    )
)
IMPERATIVE_VERBS = re.compile(
    r"\b(approve|sign|ignore|disregard|override|execute|transfer)\b", re.IGNORECASE
)
IMPERATIVE_DENSITY_THRESHOLD = 2
SENTENCE_SPLIT = re.compile(r"[.!?;\n]+")

CENT = Decimal("0.01")
TOLERANCE = Decimal("0.01")
LINE_FIELD = re.compile(r"^line_(\d+)_(description|qty|unit_price|amount)$")

REASON_DUPLICATE = "duplicate_invoice_number"
REASON_MULTI_FACE = "multi_face_scan"
REASON_NO_FACE = "no_face"


class UnparseableAmountError(ValueError):
    pass


def parse_amount(raw: str) -> Decimal:
    cleaned = re.sub(r"[^\d,.\-]", "", raw.replace(" ", ""))
    if "," in cleaned and "." in cleaned:
        decimal_sep = "," if cleaned.rfind(",") > cleaned.rfind(".") else "."
        cleaned = cleaned.replace("." if decimal_sep == "," else ",", "").replace(",", ".")
    elif "," in cleaned:
        head, _, tail = cleaned.rpartition(",")
        cleaned = f"{head}.{tail}" if len(tail) == 2 else cleaned.replace(",", "")
    try:
        return Decimal(cleaned).quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise UnparseableAmountError(raw) from exc


def _instruction_reasons(texts: list[str]) -> list[str]:
    reasons: list[str] = []
    for text in texts:
        for pattern in INSTRUCTION_PATTERNS:
            match = pattern.search(text)
            if match:
                reasons.append(f"instruction_like_text: {match.group(0).lower()}")
        for sentence in SENTENCE_SPLIT.split(text):
            if len(IMPERATIVE_VERBS.findall(sentence)) >= IMPERATIVE_DENSITY_THRESHOLD:
                reasons.append(f"instruction_like_text: {sentence.strip().lower()}")
    return reasons


def _lines(fields: dict[str, str]) -> dict[int, dict[str, str]]:
    lines: dict[int, dict[str, str]] = {}
    for name, value in fields.items():
        match = LINE_FIELD.match(name)
        if match:
            lines.setdefault(int(match.group(1)), {})[match.group(2)] = value
    return lines


def _differs(left: Decimal, right: Decimal) -> bool:
    return abs(left - right) > TOLERANCE


def _line_reasons(lines: dict[int, dict[str, str]]) -> tuple[list[str], Decimal]:
    reasons: list[str] = []
    line_sum = Decimal("0.00")
    for number in sorted(lines):
        line = lines[number]
        if not {"qty", "unit_price", "amount"} <= line.keys():
            continue
        amount = parse_amount(line["amount"])
        expected = (parse_amount(line["qty"]) * parse_amount(line["unit_price"])).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        if _differs(amount, expected):
            reasons.append(f"arithmetic_mismatch: line {number} qty*unit_price != amount")
        line_sum += amount
    return reasons, line_sum


def _total_reasons(fields: dict[str, str], line_sum: Decimal, has_lines: bool) -> list[str]:
    reasons: list[str] = []
    subtotal = parse_amount(fields["subtotal"])
    if has_lines and _differs(line_sum, subtotal):
        reasons.append("arithmetic_mismatch: line amounts != subtotal")
    vat_rate = parse_amount(fields["vat_rate"]) / Decimal(100)
    vat_amount = parse_amount(fields["vat_amount"])
    expected_vat = (subtotal * vat_rate).quantize(CENT, rounding=ROUND_HALF_UP)
    if _differs(vat_amount, expected_vat):
        reasons.append("arithmetic_mismatch: subtotal*vat_rate != vat_amount")
    if _differs(subtotal + vat_amount, parse_amount(fields["total"])):
        reasons.append("arithmetic_mismatch: subtotal+vat_amount != total")
    return reasons


def _invoice_reasons(fields: dict[str, str]) -> list[str]:
    if not {"subtotal", "vat_rate", "vat_amount", "total"} <= fields.keys():
        return []
    lines = _lines(fields)
    reasons, line_sum = _line_reasons(lines)
    return reasons + _total_reasons(fields, line_sum, bool(lines))


def _consent_reasons(plan: Plan | None, consented: set[str]) -> list[str]:
    if plan is None:
        return []
    required = sorted({cls for cls in plan.treatment_classes if cls != "none"})
    return [f"missing_consent: {cls}" for cls in required if cls not in consented]


def _face_reasons(face_count: int) -> list[str]:
    if face_count == 1:
        return []
    return [REASON_NO_FACE if face_count == 0 else REASON_MULTI_FACE]


def quarantine_policy(
    extraction: Extraction,
    *,
    known_invoice_numbers: set[tuple[str, str]] = frozenset(),
    face_count: int = 1,
    plan: Plan | None = None,
    consented_classes: set[str] = frozenset(),
) -> QuarantineVerdict:
    fields = {f.name: f.value for f in extraction.fields}
    reasons = _instruction_reasons([extraction.text, *fields.values()])
    reasons += _invoice_reasons(fields)
    key = (fields.get("supplier_name", ""), fields.get("invoice_number", ""))
    if all(key) and key in known_invoice_numbers:
        reasons.append(REASON_DUPLICATE)
    reasons += _face_reasons(face_count)
    reasons += _consent_reasons(plan, set(consented_classes))
    return QuarantineVerdict(quarantined=bool(reasons), reasons=reasons)
