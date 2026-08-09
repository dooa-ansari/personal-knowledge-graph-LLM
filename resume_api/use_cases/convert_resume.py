"""Use case for converting a resume markdown file to RDF."""

from pathlib import Path

from resume_api.ports.repositories import RDFRepository


class ConvertResumeUseCase:
    """Converts a resume markdown file to RDF Turtle format."""

    def __init__(self, rdf_repository: RDFRepository):
        self._rdf_repository = rdf_repository

    def execute(self, md_path: str) -> str:
        """Execute the conversion and return the output RDF file path."""
        path = Path(md_path)
        if not path.exists():
            raise FileNotFoundError(f"Resume file not found at: {md_path}")
        return self._rdf_repository.convert_resume_to_rdf(md_path)