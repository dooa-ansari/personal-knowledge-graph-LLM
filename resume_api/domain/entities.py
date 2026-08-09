"""Domain entities representing resume concepts."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Person:
    name: str
    title: str


@dataclass
class BulletPoint:
    text: str


@dataclass
class ProfessionalExperience:
    company: str
    location: str
    dates: str
    role: str
    bullets: list[BulletPoint] = field(default_factory=list)


@dataclass
class Skill:
    name: str


@dataclass
class SkillCategory:
    category: str
    skills: list[Skill] = field(default_factory=list)


@dataclass
class Education:
    institution: str
    dates: str
    degree: str


@dataclass
class Language:
    language: str
    proficiency: str


@dataclass
class AcademicExperience:
    title: str
    year: str
    location: str
    challenge: str = ""
    stack: str = ""
    outcome: str = ""
    link: str = ""


@dataclass
class SkillDetail:
    name: str
    items: list[str] = field(default_factory=list)


@dataclass
class Project:
    name: str


@dataclass
class Resume:
    person: Person
    experiences: list[ProfessionalExperience] = field(default_factory=list)
    skill_categories: list[SkillCategory] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    languages: list[Language] = field(default_factory=list)
    academic_experiences: list[AcademicExperience] = field(default_factory=list)
    skill_details: list[SkillDetail] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)


@dataclass
class RagChunk:
    id: str
    document: str
    metadata: dict


@dataclass
class RagResult:
    prompt: str
    session_id: str
    model: str
    retrieval_query: str
    answer: str
    retrieved_chunks: list[RagChunk]