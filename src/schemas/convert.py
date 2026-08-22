"""Response schemas for the RDF convert endpoint."""

from pydantic import BaseModel


class ConvertResponse(BaseModel):
    message: str
    source_file: str
    rdf_file: str


class ErrorResponse(BaseModel):
    error: str