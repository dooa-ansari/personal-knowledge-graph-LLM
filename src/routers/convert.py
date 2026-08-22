"""POST /api/convert-resume — convert resume markdown to RDF."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from src.dependencies import get_session_id
from src.schemas.convert import ConvertResponse, ErrorResponse
from src.services.rdf_converter import convert_resume_to_rdf

logger = logging.getLogger(__name__)

router = APIRouter(tags=["convert"])

# Path to the resume markdown file (in project root)
MD_PATH = Path(__file__).resolve().parent.parent.parent / "All Details Resume.md"


@router.post(
    "/convert-resume",
    response_model=ConvertResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Convert resume markdown to RDF",
)
def convert_resume(session_id: str = Depends(get_session_id)):
    """Reads 'All Details Resume.md', converts it to RDF Turtle, writes .ttl alongside it."""
    try:
        logger.info("Converting resume to RDF from %s [session=%s]", MD_PATH, session_id)
        output_path = convert_resume_to_rdf(str(MD_PATH))
        logger.info("RDF file generated at %s", output_path)
        return ConvertResponse(
            message="RDF file generated successfully.",
            source_file=str(MD_PATH),
            rdf_file=output_path,
        )
    except FileNotFoundError as e:
        logger.warning("Resume file not found: %s", e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to convert resume to RDF")
        raise HTTPException(status_code=500, detail=f"Failed to convert resume to RDF: {e}")