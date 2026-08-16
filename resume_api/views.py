"""Thin views that call services directly — no DI container, no use case wrappers."""

import logging
from pathlib import Path

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.permissions import IsSessionValid
from .serializers import RagSearchSerializer
from .services.rdf_converter import convert_resume_to_rdf
from .services.rag_service import search_rag

logger = logging.getLogger(__name__)

# --- OpenAPI response schemas (inlined — no separate schemas file needed) ---

_success_response = openapi.Response(
    description="RDF file generated successfully",
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "message": openapi.Schema(type=openapi.TYPE_STRING, description="Success message"),
            "source_file": openapi.Schema(type=openapi.TYPE_STRING, description="Path to source markdown file"),
            "rdf_file": openapi.Schema(type=openapi.TYPE_STRING, description="Path to generated RDF file"),
        },
    ),
)

_error_response = openapi.Response(
    description="Error occurred",
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "error": openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
        },
    ),
)

_rag_chunk_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "document": openapi.Schema(type=openapi.TYPE_STRING),
        "metadata": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            additional_properties=openapi.Schema(type=openapi.TYPE_STRING),
        ),
        "distance": openapi.Schema(type=openapi.TYPE_NUMBER, format="double"),
        "score": openapi.Schema(type=openapi.TYPE_NUMBER, format="double"),
    },
)

_rag_success_response = openapi.Response(
    description="Grounded RAG answer",
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "prompt": openapi.Schema(type=openapi.TYPE_STRING),
            "session_id": openapi.Schema(type=openapi.TYPE_STRING),
            "model": openapi.Schema(type=openapi.TYPE_STRING),
            "retrieval_query": openapi.Schema(type=openapi.TYPE_STRING),
            "answer": openapi.Schema(type=openapi.TYPE_STRING),
            "retrieved_chunks": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=_rag_chunk_schema,
            ),
        },
    ),
)


@swagger_auto_schema(
    method="post",
    operation_description=(
        "Reads the 'All Details Resume.md' file, converts it to RDF, "
        "and writes the .ttl file in the same directory as the source file. "
        "Requires an anonymous session cookie (auto-created on first visit)."
    ),
    operation_summary="Convert resume markdown to RDF",
    responses={
        200: _success_response,
        403: _error_response,
        404: _error_response,
        500: _error_response,
    },
)
@api_view(["POST"])
@permission_classes([IsSessionValid])
def convert_resume(request):
    """
    Endpoint that reads the 'All Details Resume.md' file, converts it to RDF,
    and writes the .ttl file in the same directory as the source file.
    """
    md_path = Path(__file__).resolve().parent.parent / "All Details Resume.md"

    try:
        logger.info(
            "Converting resume to RDF from %s [session=%s]",
            md_path,
            request.session.session_key,
        )
        output_path = convert_resume_to_rdf(str(md_path))
        logger.info("RDF file generated at %s", output_path)
        return Response(
            {
                "message": "RDF file generated successfully.",
                "source_file": str(md_path),
                "rdf_file": output_path,
            },
            status=200,
        )
    except FileNotFoundError as e:
        logger.warning("Resume file not found: %s", e)
        return Response({"error": str(e)}, status=404)
    except Exception as e:
        logger.exception("Failed to convert resume to RDF")
        return Response(
            {"error": f"Failed to convert resume to RDF: {str(e)}"},
            status=500,
        )


@swagger_auto_schema(
    method="post",
    operation_description=(
        "Performs session-aware semantic RAG search over indexed resume chunks. "
        "Session is cookie-based (HttpOnly, SameSite=Strict) — no session_id "
        "in the request body. The session is auto-created on first visit."
    ),
    operation_summary="Semantic RAG resume search",
    request_body=RagSearchSerializer,
    responses={
        200: _rag_success_response,
        400: _error_response,
        403: _error_response,
        500: _error_response,
    },
)
@api_view(["POST"])
@permission_classes([IsSessionValid])
def search_rag(request):
    """Run semantic retrieval and grounded answer generation."""
    serializer = RagSearchSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    data = serializer.validated_data
    prompt = data["prompt"]
    session_id = request.session.session_key

    if not session_id:
        return Response(
            {"error": "No valid session found. Please refresh the page."},
            status=403,
        )

    try:
        logger.info("RAG search session=%s prompt=%.60s", session_id, prompt)
        result = search_rag(session_id, prompt)
        return Response(result, status=200)
    except ValueError as exc:
        logger.warning("RAG validation error: %s", exc)
        return Response({"error": str(exc)}, status=400)
    except Exception as exc:
        logger.exception("RAG search failed")
        return Response(
            {"error": f"Failed to perform RAG search: {exc}"}, status=500
        )
