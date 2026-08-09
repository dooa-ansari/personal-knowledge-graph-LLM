"""Concrete RDF repository adapter wrapping the existing converter service."""

from resume_api.ports.repositories import RDFRepository
from resume_api.services.rdf_converter import convert_resume_to_rdf as _convert


class RdfConverterRepository(RDFRepository):
    """Adapter that wraps the existing RDF converter service as an RDFRepository."""

    def convert_resume_to_rdf(self, md_path: str) -> str:
        return _convert(md_path)