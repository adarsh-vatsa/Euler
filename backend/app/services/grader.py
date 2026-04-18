"""Answer grading per answer format.

symbolic: parse both answers with SymPy and check equivalence via simplify.
numeric:  parse both as Rational/Float, compare with small tolerance for floats.
mcq:      exact match on the choice letter (case-insensitive, whitespace-trimmed).
"""

from dataclasses import dataclass

import sympy
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

_SYMPY_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)


@dataclass
class GradeResult:
    correct: bool
    normalized_user_answer: str
    reason: str = ""  # brief explanation, useful for debugging


def _parse_symbolic(s: str) -> sympy.Expr:
    # Translate common user conveniences to SymPy.
    s = s.strip()
    # Caret → power (SymPy uses ** but users type ^).
    s = s.replace("^", "**")
    return parse_expr(s, transformations=_SYMPY_TRANSFORMS, evaluate=True)


def grade_symbolic(expected: str, user: str) -> GradeResult:
    try:
        u = _parse_symbolic(user)
    except Exception as e:
        return GradeResult(False, user, f"Could not parse your answer: {e}")
    try:
        e = _parse_symbolic(expected)
    except Exception as ex:
        # If expected fails to parse, treat as a content bug; fall back to string match.
        return GradeResult(
            user.strip() == expected.strip(),
            str(u),
            f"Expected-answer parse failed ({ex}); compared as strings.",
        )
    try:
        diff = sympy.simplify(u - e)
    except Exception:
        diff = None
    if diff == 0:
        return GradeResult(True, str(u))
    # Fall back to equality with Eq for boolean relations where diff is ill-defined.
    try:
        if sympy.simplify(sympy.Eq(u, e)) is sympy.true:
            return GradeResult(True, str(u))
    except Exception:
        pass
    return GradeResult(False, str(u))


def grade_numeric(expected: str, user: str, tol: float = 1e-6) -> GradeResult:
    u_raw = user.strip()
    try:
        u = sympy.Rational(u_raw) if "/" in u_raw else sympy.sympify(u_raw)
    except Exception as ex:
        return GradeResult(False, u_raw, f"Could not parse your answer: {ex}")
    try:
        e = sympy.Rational(expected.strip()) if "/" in expected else sympy.sympify(expected)
    except Exception:
        return GradeResult(False, str(u), "Expected-answer parse failed")
    try:
        diff = sympy.simplify(u - e)
    except Exception:
        diff = None
    if diff == 0:
        return GradeResult(True, str(u))
    # Decimal tolerance fallback.
    try:
        if abs(float(u) - float(e)) <= tol:
            return GradeResult(True, str(u))
    except Exception:
        pass
    return GradeResult(False, str(u))


def grade_mcq(expected: str, user: str) -> GradeResult:
    u = user.strip().upper()
    e = expected.strip().upper()
    return GradeResult(u == e, u)


def grade(answer_format: str, expected: str, user: str) -> GradeResult:
    if answer_format == "symbolic":
        return grade_symbolic(expected, user)
    if answer_format == "numeric":
        return grade_numeric(expected, user)
    if answer_format == "mcq":
        return grade_mcq(expected, user)
    raise ValueError(f"Unknown answer_format: {answer_format}")
