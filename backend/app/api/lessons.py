"""Lesson flow: start a skill, submit answers, advance through KPs."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import KP, Attempt, Problem, Skill, UserSkillState
from app.services import generator, grader

router = APIRouter(prefix="/api/lessons", tags=["lessons"])

# Mastery threshold: consecutive correct answers required to advance a KP.
KP_MASTERY_STREAK = 2
# How many recent problems to show the generator to avoid repetition.
RECENT_PROBLEM_WINDOW = 5


class StartRequest(BaseModel):
    skill_id: int


class ProblemOut(BaseModel):
    id: int
    statement: str
    answer_format: str
    choices: list[str] | None = None


class KPOut(BaseModel):
    id: int
    index: int
    name: str
    intro: str
    worked_example: str


class StartResponse(BaseModel):
    skill_id: int
    skill_name: str
    kp: KPOut
    problem: ProblemOut


class SubmitRequest(BaseModel):
    problem_id: int
    user_answer: str
    time_spent_seconds: float = 0.0


class NextAction(BaseModel):
    type: str  # "next_problem" | "next_kp" | "lesson_complete"
    problem: ProblemOut | None = None
    kp: KPOut | None = None


class SubmitResponse(BaseModel):
    correct: bool
    normalized_user_answer: str
    solution_steps: str
    reason: str = ""
    next: NextAction


def _ensure_kps(skill: Skill, db: Session) -> list[KP]:
    """If the skill has no KPs yet, generate them via LLM and persist."""
    if skill.kps:
        return skill.kps
    generated = generator.generate_kps(
        skill_name=skill.name,
        skill_description=skill.description,
        unit_path=skill.unit_path,
    )
    for i, g in enumerate(generated):
        db.add(
            KP(
                skill_id=skill.id,
                index=i,
                name=g.name,
                intro=g.intro,
                worked_example=g.worked_example,
                problem_spec={"notes": g.problem_generation_notes},
            )
        )
    db.commit()
    db.refresh(skill)
    return skill.kps


def _recent_problem_statements(kp_id: int, db: Session, limit: int) -> list[str]:
    rows = (
        db.query(Problem.statement)
        .filter(Problem.kp_id == kp_id)
        .order_by(Problem.id.desc())
        .limit(limit)
        .all()
    )
    return [r[0] for r in rows]


def _generate_problem_for_kp(skill: Skill, kp: KP, db: Session) -> Problem:
    notes = (kp.problem_spec or {}).get("notes", "")
    recent = _recent_problem_statements(kp.id, db, RECENT_PROBLEM_WINDOW)
    gen = generator.generate_problem(
        skill_name=skill.name,
        kp_name=kp.name,
        kp_intro=kp.intro,
        worked_example=kp.worked_example,
        problem_generation_notes=notes,
        recent_statements=recent,
    )
    problem = Problem(
        kp_id=kp.id,
        statement=gen.statement,
        answer=gen.answer,
        answer_format=gen.answer_format,
        choices=gen.choices,
        solution_steps=gen.solution_steps,
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem


def _get_or_create_state(skill_id: int, db: Session) -> UserSkillState:
    state = (
        db.query(UserSkillState)
        .filter(UserSkillState.skill_id == skill_id)
        .one_or_none()
    )
    if state is None:
        state = UserSkillState(skill_id=skill_id, mastery_state="in_progress")
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def _kp_out(kp: KP) -> KPOut:
    return KPOut(
        id=kp.id,
        index=kp.index,
        name=kp.name,
        intro=kp.intro,
        worked_example=kp.worked_example,
    )


def _problem_out(p: Problem) -> ProblemOut:
    return ProblemOut(
        id=p.id,
        statement=p.statement,
        answer_format=p.answer_format,
        choices=p.choices,
    )


@router.post("/start", response_model=StartResponse)
def start_lesson(req: StartRequest, db: Session = Depends(get_db)):
    skill = db.get(Skill, req.skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    kps = _ensure_kps(skill, db)
    if not kps:
        raise HTTPException(500, "No KPs generated for this skill")
    state = _get_or_create_state(skill.id, db)
    if state.current_kp_index >= len(kps):
        state.current_kp_index = 0
        state.kp_correct_streak = 0
        db.commit()
    current_kp = kps[state.current_kp_index]
    problem = _generate_problem_for_kp(skill, current_kp, db)
    return StartResponse(
        skill_id=skill.id,
        skill_name=skill.name,
        kp=_kp_out(current_kp),
        problem=_problem_out(problem),
    )


@router.post("/submit", response_model=SubmitResponse)
def submit_answer(req: SubmitRequest, db: Session = Depends(get_db)):
    problem = db.get(Problem, req.problem_id)
    if not problem:
        raise HTTPException(404, "Problem not found")
    kp = db.get(KP, problem.kp_id)
    skill = db.get(Skill, kp.skill_id)
    state = _get_or_create_state(skill.id, db)

    result = grader.grade(problem.answer_format, problem.answer, req.user_answer)

    attempt = Attempt(
        problem_id=problem.id,
        kp_id=kp.id,
        skill_id=skill.id,
        user_answer=req.user_answer,
        correct=result.correct,
        time_spent_seconds=req.time_spent_seconds,
        xp_awarded=max(int(req.time_spent_seconds // 60), 1) if result.correct else 0,
    )
    db.add(attempt)

    state.kp_attempts_in_current_kp += 1
    if result.correct:
        state.kp_correct_streak += 1
    else:
        state.kp_correct_streak = 0

    # Decide next action.
    kps = skill.kps
    next_action: NextAction
    if state.kp_correct_streak >= KP_MASTERY_STREAK:
        # Advance past this KP.
        state.current_kp_index += 1
        state.kp_correct_streak = 0
        state.kp_attempts_in_current_kp = 0
        if state.current_kp_index >= len(kps):
            state.mastery_state = "mastered"
            state.last_review_at = datetime.utcnow()
            state.reps += 1
            next_action = NextAction(type="lesson_complete")
        else:
            new_kp = kps[state.current_kp_index]
            new_problem = _generate_problem_for_kp(skill, new_kp, db)
            next_action = NextAction(
                type="next_kp", kp=_kp_out(new_kp), problem=_problem_out(new_problem)
            )
    else:
        # Stay in current KP, generate another problem.
        current_kp = kps[state.current_kp_index]
        new_problem = _generate_problem_for_kp(skill, current_kp, db)
        next_action = NextAction(type="next_problem", problem=_problem_out(new_problem))

    db.commit()
    return SubmitResponse(
        correct=result.correct,
        normalized_user_answer=result.normalized_user_answer,
        solution_steps=problem.solution_steps,
        reason=result.reason,
        next=next_action,
    )
