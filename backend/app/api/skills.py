"""Skills CRUD and a dogfood seed endpoint for milestone 1."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Skill

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillOut(BaseModel):
    id: int
    unit_path: str
    name: str
    description: str
    kp_count: int


class SeedResponse(BaseModel):
    created: list[SkillOut]
    already_existed: list[SkillOut]


# Hardcoded seed skills from curriculum.md chosen for dogfooding: procedural,
# clean symbolic answers, tight scope (truly atomic).
SEED_SKILLS = [
    {
        "unit_path": "3.9.6",
        "name": "Solving 2x2 Systems of Equations Using Gaussian Elimination",
        "description": (
            "Given a 2x2 linear system of equations, use elementary row operations "
            "on the augmented matrix to reach row echelon form, then back-substitute "
            "to find the unique solution (x, y)."
        ),
    },
    {
        "unit_path": "3.10.1",
        "name": "Finding the Inverse of a 2x2 Matrix Using Row Operations",
        "description": (
            "Given an invertible 2x2 matrix A, form the augmented matrix [A | I] and "
            "apply row operations to reach [I | A^-1]. The right half is the inverse."
        ),
    },
    {
        "unit_path": "5.16.2",
        "name": "Calculating the Eigenvalues of a 2x2 Matrix",
        "description": (
            "Given a 2x2 matrix A, find its eigenvalues by solving the characteristic "
            "equation det(A - λI) = 0, which is a quadratic in λ."
        ),
    },
]


def _to_out(s: Skill) -> SkillOut:
    return SkillOut(
        id=s.id,
        unit_path=s.unit_path,
        name=s.name,
        description=s.description,
        kp_count=len(s.kps),
    )


@router.get("", response_model=list[SkillOut])
def list_skills(db: Session = Depends(get_db)):
    rows = db.query(Skill).order_by(Skill.unit_path).all()
    return [_to_out(s) for s in rows]


@router.get("/{skill_id}", response_model=SkillOut)
def get_skill(skill_id: int, db: Session = Depends(get_db)):
    s = db.get(Skill, skill_id)
    if not s:
        from fastapi import HTTPException

        raise HTTPException(404, "Skill not found")
    return _to_out(s)


@router.post("/seed", response_model=SeedResponse)
def seed_skills(db: Session = Depends(get_db)):
    created, existed = [], []
    for spec in SEED_SKILLS:
        existing = (
            db.query(Skill)
            .filter(Skill.unit_path == spec["unit_path"], Skill.name == spec["name"])
            .one_or_none()
        )
        if existing:
            existed.append(_to_out(existing))
            continue
        s = Skill(**spec)
        db.add(s)
        db.commit()
        db.refresh(s)
        created.append(_to_out(s))
    return SeedResponse(created=created, already_existed=existed)
