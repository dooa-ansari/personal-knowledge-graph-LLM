"""
RDF converter for the specific resume markdown format.

This module parses the "All Details Resume.md" format and converts it
into an RDF graph serialized as Turtle (.ttl) in the same directory
as the source file.
"""

import re
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import FOAF, RDF, XSD

# Custom namespace for resume-specific concepts
RESUME = Namespace("http://example.org/resume#")
SCHEMA = Namespace("https://schema.org/")

# Section headers that appear in the resume markdown
SECTION_HEADERS = [
    "PROFESSIONAL EXPERIENCE",
    "SKILLS",
    "EDUCATION",
    "LANGUAGES",
    "ACADEMIC EXPERIENCE",
    "SKILL DETAILS",
    "PROJECTS",
]


def _clean_text(text: str) -> str:
    """Clean and normalize text extracted from markdown."""
    return re.sub(r"\s+", " ", text).strip()


def _extract_name_and_title(lines: list[str]) -> tuple[str, str]:
    """Extract the person's name and title from the header."""
    name = ""
    title = ""
    for line in lines:
        cleaned = _clean_text(line.replace("#", "").replace("*", ""))
        if cleaned and not name:
            name = cleaned
        elif cleaned and not title:
            title = cleaned
            break
    return name, title


def _extract_table_cell_content(content: str) -> str:
    """
    Extract the content of the main table row (line 5) which contains
    the PROFESSIONAL EXPERIENCE, SKILLS, EDUCATION, and LANGUAGES sections.
    """
    # Find the table row that starts with "| Frontend-focused" and ends at the line end
    match = re.search(r"\| Frontend-focused.*$", content, re.MULTILINE)
    if match:
        return match.group(0).strip("|")
    return ""


def _split_table_sections(table_content: str) -> dict[str, str]:
    """
    Split the table cell content into sections.

    The table row has cells separated by '|' characters. Each cell may
    contain multiple section headers (e.g., "SKILLS Core Languages: ... EDUCATION ... LANGUAGES ...").
    """
    sections: dict[str, str] = {}

    # Split the table content by '|' to get individual cells
    cells = table_content.split("|")

    for cell in cells:
        cell = cell.strip()
        if not cell:
            continue

        # Find ALL section headers in this cell (case-sensitive since headers are uppercase)
        positions = []
        for header in SECTION_HEADERS:
            pattern = re.compile(r"\b" + re.escape(header) + r"\b")
            for match in pattern.finditer(cell):
                positions.append((match.start(), header))

        # Sort by position
        positions.sort(key=lambda x: x[0])

        # Extract content between headers
        for i, (pos, header) in enumerate(positions):
            end = positions[i + 1][0] if i + 1 < len(positions) else len(cell)
            section_content = cell[pos + len(header):end].strip()
            sections[header] = section_content

    return sections


def _split_standalone_sections(content: str) -> dict[str, str]:
    """
    Split the standalone sections (ACADEMIC EXPERIENCE, SKILL DETAILS, PROJECTS)
    from the main content.
    """
    sections: dict[str, str] = {}

    # Find positions of standalone section headers
    standalone_headers = ["ACADEMIC EXPERIENCE", "SKILL DETAILS", "PROJECTS"]
    positions = []
    for header in standalone_headers:
        for match in re.finditer(re.escape(header), content, re.IGNORECASE):
            positions.append((match.start(), header))

    # Sort by position
    positions.sort(key=lambda x: x[0])

    # Extract content between headers
    for i, (pos, header) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(content)
        section_content = content[pos + len(header):end]
        sections[header] = section_content.strip()

    return sections


def _parse_professional_experience(content: str) -> list[dict]:
    """Parse the professional experience section."""
    experiences = []
    # Match company patterns: "Company \- Location \- StartDate \- EndDate *Role*"
    # Use \w+ to handle Unicode characters (e.g., Köln)
    # Company names are typically 1-4 words
    # Pattern: Company \- Location \- StartDate \- EndDate *Role*
    pattern = re.compile(
        r"([A-Z][\w]+(?:\s+[\w&]+){0,3})\s*\\-\s*([\w\s()]+?)\s*\\-\s*([0-9/]+)\s*\\-\s*([0-9/]+|[A-Za-z]+)\s*\*([^*]+)\*"
    )
    matches = list(pattern.finditer(content))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        exp_text = content[match.end():end]
        exp = {
            "company": _clean_text(match.group(1)),
            "location": _clean_text(match.group(2)),
            "dates": f"{_clean_text(match.group(3))} - {_clean_text(match.group(4))}",
            "role": _clean_text(match.group(5)),
            "bullets": [],
        }
        # Extract bullet points from the remaining text
        bullets_text = exp_text
        # Split on periods followed by capital letters
        bullet_parts = re.split(r"(?<=\.)\s+(?=[A-Z])", bullets_text)
        for part in bullet_parts:
            part = _clean_text(part)
            if part and len(part) > 5:
                exp["bullets"].append(part)
        experiences.append(exp)
    return experiences


def _parse_skills(content: str) -> list[dict]:
    """Parse the skills section."""
    skills = []
    # Skills are formatted as: "Category:  item1, item2, item3"
    pattern = re.compile(r"([A-Z][^:]+):\s*([^|]+)")
    for match in pattern.finditer(content):
        category = _clean_text(match.group(1))
        items_text = _clean_text(match.group(2))
        items = [item.strip() for item in items_text.split(",") if item.strip()]
        skills.append({"category": category, "items": items})
    return skills


def _parse_education(content: str) -> list[dict]:
    """Parse the education section."""
    education = []
    # Education entries: "University *dates, location* Degree"
    pattern = re.compile(
        r"([A-Z][A-Za-z\s&]+?)\s*\*([^*]+?)\*\s*([A-Z][A-Za-z\s]+)"
    )
    for match in pattern.finditer(content):
        education.append({
            "institution": _clean_text(match.group(1)),
            "dates": _clean_text(match.group(2)),
            "degree": _clean_text(match.group(3)),
        })
    return education


def _parse_languages(content: str) -> list[dict]:
    """Parse the languages section."""
    languages = []
    # Languages: "English \- Full Professional Proficiency (C1)"
    pattern = re.compile(r"([A-Za-z]+)\s*\\?-\s*([^*|]+)")
    for match in pattern.finditer(content):
        lang = _clean_text(match.group(1))
        proficiency = _clean_text(match.group(2))
        if lang and proficiency:
            languages.append({"language": lang, "proficiency": proficiency})
    return languages


def _parse_academic_experience(content: str) -> list[dict]:
    """Parse academic experience entries."""
    entries = []
    # Match: "**Title Year \-** *Location*"
    # The \- separator is inside the ** markers
    pattern = re.compile(
        r"\*\*(.+?)\s*(\d{4})\s*\\-\*\*\s*\*([^*]+)\*"
    )
    matches = list(pattern.finditer(content))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        entry_text = content[match.end():end]
        entry = {
            "title": _clean_text(match.group(1)),
            "year": match.group(2),
            "location": _clean_text(match.group(3)),
            "challenge": "",
            "stack": "",
            "outcome": "",
            "link": "",
        }
        # Extract details from entry text
        for line in entry_text.split("\n"):
            line = line.strip()
            if line.startswith("*"):
                bullet = line.lstrip("*").strip()
                if bullet.startswith("Technology stack") or bullet.startswith("Technology Stack"):
                    entry["stack"] = bullet
                elif bullet.startswith("The thesis") or bullet.startswith("The team"):
                    entry["outcome"] = bullet
                elif bullet.startswith("Deployment"):
                    entry["outcome"] = f"{entry['outcome']} {bullet}".strip()
                elif bullet.startswith("http"):
                    entry["link"] = bullet
            elif line.startswith("**Challenge:**") or line.startswith("Challenge:"):
                entry["challenge"] = line.split(":", 1)[1].strip()
        entries.append(entry)
    return entries


def _parse_skill_details(content: str) -> list[dict]:
    """Parse skill detail sections like '**React Native \-**' or '**React Native** \-'."""
    skills = []
    # Match: "**Skill Name \-**" (dash inside markers) or "**Skill Name** \-" (dash outside)
    pattern = re.compile(r"\*\*(.+?)\s*\\-\*\*\s*([^*]+)")
    for match in pattern.finditer(content):
        name = _clean_text(match.group(1))
        items_text = _clean_text(match.group(2))
        items = [item.strip() for item in items_text.split(",") if item.strip()]
        skills.append({"name": name, "items": items})
    return skills


def _parse_projects(content: str) -> list[str]:
    """Parse the projects list."""
    projects = []
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            projects.append(_clean_text(line))
    return projects


def convert_resume_to_rdf(md_path: str) -> str:
    """
    Convert a resume markdown file (specific format) to RDF Turtle.

    The output RDF file is written to the same directory as the source file
    with a .ttl extension.

    Returns the path to the generated RDF file.
    """
    md_path = Path(md_path)
    if not md_path.exists():
        raise FileNotFoundError(f"File not found: {md_path}")

    content = md_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Extract name and title
    name, title = _extract_name_and_title(lines)

    # Extract the table cell content (contains main sections)
    table_content = _extract_table_cell_content(content)
    table_sections = _split_table_sections(table_content)

    # Extract standalone sections
    standalone_sections = _split_standalone_sections(content)

    # Merge all sections
    sections = {**table_sections, **standalone_sections}

    # Build RDF graph
    g = Graph()
    g.bind("foaf", FOAF)
    g.bind("schema", SCHEMA)
    g.bind("resume", RESUME)

    # Person node
    person_uri = URIRef(f"https://example.org/resume/{name.lower().replace(' ', '-')}")
    g.add((person_uri, RDF.type, FOAF.Person))
    g.add((person_uri, RDF.type, SCHEMA.Person))
    if name:
        g.add((person_uri, FOAF.name, Literal(name)))
        g.add((person_uri, SCHEMA.name, Literal(name)))
    if title:
        g.add((person_uri, SCHEMA.jobTitle, Literal(title)))

    # --- Professional Experience ---
    if "PROFESSIONAL EXPERIENCE" in sections:
        experiences = _parse_professional_experience(sections["PROFESSIONAL EXPERIENCE"])
        for i, exp in enumerate(experiences):
            exp_uri = URIRef(f"{person_uri}/experience/{i}")
            g.add((exp_uri, RDF.type, RESUME.ProfessionalExperience))
            g.add((person_uri, RESUME.hasProfessionalExperience, exp_uri))
            if exp.get("company"):
                g.add((exp_uri, SCHEMA.worksFor, Literal(exp["company"])))
                g.add((exp_uri, RESUME.company, Literal(exp["company"])))
            if exp.get("location"):
                g.add((exp_uri, RESUME.location, Literal(exp["location"])))
            if exp.get("dates"):
                g.add((exp_uri, RESUME.dates, Literal(exp["dates"])))
            if exp.get("role"):
                g.add((exp_uri, SCHEMA.jobTitle, Literal(exp["role"])))
                g.add((exp_uri, RESUME.role, Literal(exp["role"])))
            for j, bullet in enumerate(exp.get("bullets", [])):
                bullet_uri = URIRef(f"{exp_uri}/bullet/{j}")
                g.add((bullet_uri, RDF.type, RESUME.BulletPoint))
                g.add((exp_uri, RESUME.hasBulletPoint, bullet_uri))
                g.add((bullet_uri, RDF.value, Literal(bullet)))

    # --- Skills ---
    if "SKILLS" in sections:
        skill_categories = _parse_skills(sections["SKILLS"])
        for i, skill_cat in enumerate(skill_categories):
            cat_uri = URIRef(f"{person_uri}/skill-category/{i}")
            g.add((cat_uri, RDF.type, RESUME.SkillCategory))
            g.add((person_uri, RESUME.hasSkillCategory, cat_uri))
            if skill_cat.get("category"):
                g.add((cat_uri, RESUME.skillCategory, Literal(skill_cat["category"])))
            for j, item in enumerate(skill_cat.get("items", [])):
                skill_uri = URIRef(f"{cat_uri}/skill/{j}")
                g.add((skill_uri, RDF.type, RESUME.Skill))
                g.add((cat_uri, RESUME.hasSkill, skill_uri))
                g.add((skill_uri, RDF.value, Literal(item)))

    # --- Education ---
    if "EDUCATION" in sections:
        education = _parse_education(sections["EDUCATION"])
        for i, edu in enumerate(education):
            edu_uri = URIRef(f"{person_uri}/education/{i}")
            g.add((edu_uri, RDF.type, RESUME.Education))
            g.add((person_uri, RESUME.hasEducation, edu_uri))
            if edu.get("institution"):
                g.add((edu_uri, RESUME.institution, Literal(edu["institution"])))
            if edu.get("dates"):
                g.add((edu_uri, RESUME.dates, Literal(edu["dates"])))
            if edu.get("degree"):
                g.add((edu_uri, SCHEMA.educationalCredentialAwarded, Literal(edu["degree"])))

    # --- Languages ---
    if "LANGUAGES" in sections:
        languages = _parse_languages(sections["LANGUAGES"])
        for i, lang in enumerate(languages):
            lang_uri = URIRef(f"{person_uri}/language/{i}")
            g.add((lang_uri, RDF.type, RESUME.Language))
            g.add((person_uri, RESUME.hasLanguage, lang_uri))
            if lang.get("language"):
                g.add((lang_uri, RESUME.language, Literal(lang["language"])))
            if lang.get("proficiency"):
                g.add((lang_uri, RESUME.proficiency, Literal(lang["proficiency"])))

    # --- Academic Experience ---
    if "ACADEMIC EXPERIENCE" in sections:
        academic = _parse_academic_experience(sections["ACADEMIC EXPERIENCE"])
        for i, entry in enumerate(academic):
            acad_uri = URIRef(f"{person_uri}/academic/{i}")
            g.add((acad_uri, RDF.type, RESUME.AcademicExperience))
            g.add((person_uri, RESUME.hasAcademicExperience, acad_uri))
            if entry.get("title"):
                g.add((acad_uri, SCHEMA.name, Literal(entry["title"])))
            if entry.get("year"):
                g.add((acad_uri, RESUME.year, Literal(entry["year"], datatype=XSD.gYear)))
            if entry.get("location"):
                g.add((acad_uri, RESUME.location, Literal(entry["location"])))
            if entry.get("challenge"):
                g.add((acad_uri, RESUME.challenge, Literal(entry["challenge"])))
            if entry.get("stack"):
                g.add((acad_uri, RESUME.technologyStack, Literal(entry["stack"])))
            if entry.get("outcome"):
                g.add((acad_uri, RESUME.outcome, Literal(entry["outcome"])))
            if entry.get("link"):
                g.add((acad_uri, SCHEMA.url, URIRef(entry["link"])))

    # --- Skill Details ---
    if "SKILL DETAILS" in sections:
        skill_details = _parse_skill_details(sections["SKILL DETAILS"])
        for i, skill in enumerate(skill_details):
            skill_uri = URIRef(f"{person_uri}/skill-detail/{i}")
            g.add((skill_uri, RDF.type, RESUME.SkillDetail))
            g.add((person_uri, RESUME.hasSkillDetail, skill_uri))
            if skill.get("name"):
                g.add((skill_uri, SCHEMA.name, Literal(skill["name"])))
            for j, item in enumerate(skill.get("items", [])):
                item_uri = URIRef(f"{skill_uri}/item/{j}")
                g.add((item_uri, RDF.type, RESUME.SkillItem))
                g.add((skill_uri, RESUME.hasSkillItem, item_uri))
                g.add((item_uri, RDF.value, Literal(item)))

    # --- Projects ---
    if "PROJECTS" in sections:
        projects = _parse_projects(sections["PROJECTS"])
        for i, project in enumerate(projects):
            proj_uri = URIRef(f"{person_uri}/project/{i}")
            g.add((proj_uri, RDF.type, RESUME.Project))
            g.add((person_uri, RESUME.hasProject, proj_uri))
            g.add((proj_uri, SCHEMA.name, Literal(project)))

    # Write RDF file to same location as source file
    output_path = md_path.with_suffix(".ttl")
    g.serialize(destination=str(output_path), format="turtle")

    return str(output_path)