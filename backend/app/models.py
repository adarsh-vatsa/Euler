from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_path: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    kps: Mapped[list["KP"]] = relationship(
        back_populates="skill",
        cascade="all, delete-orphan",
        order_by="KP.index",
    )


class KP(Base):
    __tablename__ = "kps"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), index=True)
    index: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255))
    intro: Mapped[str] = mapped_column(Text, default="")
    worked_example: Mapped[str] = mapped_column(Text, default="")
    problem_spec: Mapped[dict] = mapped_column(JSON, default=dict)

    skill: Mapped[Skill] = relationship(back_populates="kps")


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    kp_id: Mapped[int] = mapped_column(ForeignKey("kps.id"), index=True)
    statement: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(String(512))
    answer_format: Mapped[str] = mapped_column(String(32))  # symbolic | numeric | mcq
    choices: Mapped[list | None] = mapped_column(JSON, nullable=True)
    solution_steps: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserSkillState(Base):
    """Per-skill state for the single user (v1 is single-user)."""

    __tablename__ = "user_skill_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), unique=True, index=True)
    mastery_state: Mapped[str] = mapped_column(
        String(32), default="not_started"
    )  # not_started | in_progress | mastered
    current_kp_index: Mapped[int] = mapped_column(Integer, default=0)
    kp_correct_streak: Mapped[int] = mapped_column(Integer, default=0)
    kp_attempts_in_current_kp: Mapped[int] = mapped_column(Integer, default=0)

    # FSRS state (populated after first review)
    stability: Mapped[float] = mapped_column(Float, default=0.0)
    difficulty: Mapped[float] = mapped_column(Float, default=0.0)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    kp_id: Mapped[int] = mapped_column(ForeignKey("kps.id"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), index=True)
    user_answer: Mapped[str] = mapped_column(Text)
    correct: Mapped[bool] = mapped_column(Boolean)
    time_spent_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
