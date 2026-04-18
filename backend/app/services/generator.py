"""Generators for knowledge points and practice problems via Claude.

Both generators use `messages.parse()` with Pydantic schemas for structured
outputs, and share a cached system prompt (see `llm.py`).
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.config import settings
from app.services.llm import cached_system, client


class KnowledgePoint(BaseModel):
    """One knowledge point in a skill's lesson."""

    name: str = Field(description="Short descriptive name, e.g. 'Monic quadratics with positive roots'")
    intro: str = Field(description="1-3 sentence framing of this KP (markdown+LaTeX)")
    worked_example: str = Field(
        description="Complete worked example with subgoal labels (markdown+LaTeX)"
    )
    problem_generation_notes: str = Field(
        description=(
            "Free-form guidance for the problem generator: what to parameterize, "
            "answer format, difficulty calibration, special cases to emphasize."
        )
    )


class KPListOutput(BaseModel):
    kps: list[KnowledgePoint] = Field(
        description="Ordered list of 3-4 KPs of increasing difficulty"
    )


class PracticeProblem(BaseModel):
    statement: str = Field(description="Problem statement (markdown+LaTeX)")
    answer: str = Field(
        description=(
            "Canonical answer string. For symbolic: SymPy syntax (use ** not ^, "
            "use sqrt(), pi, etc.). For numeric: plain number or simple fraction. "
            "For mcq: single uppercase letter."
        )
    )
    answer_format: Literal["symbolic", "numeric", "mcq"]
    choices: list[str] | None = Field(
        default=None,
        description="List of 4-5 choice strings if mcq, otherwise null",
    )
    solution_steps: str = Field(
        description="Full step-by-step solution (markdown+LaTeX)"
    )


def generate_kps(
    skill_name: str,
    skill_description: str,
    unit_path: str,
) -> list[KnowledgePoint]:
    """Produce 3-4 knowledge points for a skill."""
    user_prompt = (
        f"Generate knowledge points for this atomic skill.\n\n"
        f"Unit: {unit_path}\n"
        f"Skill name: {skill_name}\n"
        f"Skill description: {skill_description or '(none)'}\n\n"
        f"Produce 3-4 KPs of increasing difficulty. Each KP needs a concise name, "
        f"a 1-3 sentence intro, a complete worked example with subgoal labels, and "
        f"problem-generation notes for downstream use."
    )

    response = client().messages.parse(
        model=settings.model_generation,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=cached_system(),
        messages=[{"role": "user", "content": user_prompt}],
        output_format=KPListOutput,
    )
    parsed = response.parsed_output
    if parsed is None:
        raise RuntimeError("KP generation returned no parsed output")
    return parsed.kps


def generate_problem(
    skill_name: str,
    kp_name: str,
    kp_intro: str,
    worked_example: str,
    problem_generation_notes: str,
    recent_statements: list[str] | None = None,
) -> PracticeProblem:
    """Produce one practice problem for the given KP."""
    recent_section = ""
    if recent_statements:
        recent_section = (
            "\n\nAvoid problems similar to these recent ones:\n"
            + "\n".join(f"- {s}" for s in recent_statements[-5:])
        )

    user_prompt = (
        f"Generate ONE practice problem for this knowledge point.\n\n"
        f"Skill: {skill_name}\n"
        f"KP: {kp_name}\n"
        f"Intro: {kp_intro}\n\n"
        f"Worked example (use the SAME technique):\n{worked_example}\n\n"
        f"Problem generation notes: {problem_generation_notes}"
        f"{recent_section}\n\n"
        f"Requirements: the answer must be uniquely machine-checkable. Choose "
        f"parameters that produce a clean answer. The problem must be solvable "
        f"using only the technique in the worked example."
    )

    response = client().messages.parse(
        model=settings.model_generation,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=cached_system(),
        messages=[{"role": "user", "content": user_prompt}],
        output_format=PracticeProblem,
    )
    parsed = response.parsed_output
    if parsed is None:
        raise RuntimeError("Problem generation returned no parsed output")
    return parsed
