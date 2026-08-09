import uuid
from pathlib import Path

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import RagSearchSerializer
from .services.rdf_converter import convert_resume_to_rdf
from .services.rag_langgraph_service import search_rag_with_context

# Swagger response schema
success_response = openapi.Response(
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

error_response = openapi.Response(
    description="Error occurred",
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "error": openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
        },
    ),
)

rag_chunk_schema = openapi.Schema(
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

rag_success_response = openapi.Response(
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
                items=rag_chunk_schema,
            ),
        },
    ),
)


@swagger_auto_schema(
    method="post",
    operation_description="Reads the 'All Details Resume.md' file, converts it to RDF, and writes the .ttl file in the same directory as the source file.",
    operation_summary="Convert resume markdown to RDF",
    responses={
        200: success_response,
        404: error_response,
        500: error_response,
    },
)
@api_view(["POST"])
def convert_resume(request):
    """
    Endpoint that reads the 'All Details Resume.md' file, converts it to RDF,
    and writes the .ttl file in the same directory as the source file.
    """
    # Path to the resume markdown file (project root)
    md_path = Path(__file__).resolve().parent.parent / "All Details Resume.md"

    if not md_path.exists():
        return Response(
            {"error": f"Resume file not found at: {md_path}"},
            status=404,
        )

    try:
        output_path = convert_resume_to_rdf(str(md_path))
        return Response(
            {
                "message": "RDF file generated successfully.",
                "source_file": str(md_path),
                "rdf_file": output_path,
            },
            status=200,
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to convert resume to RDF: {str(e)}"},
            status=500,
        )


@swagger_auto_schema(
    method="post",
    operation_description=(
        "Performs session-aware semantic RAG search over indexed resume chunks. "
        "Pass the returned session_id to continue the conversation."
    ),
    operation_summary="Session-aware semantic RAG resume search",
    request_body=RagSearchSerializer,
    responses={
        200: rag_success_response,
        400: error_response,
        500: error_response,
    },
)
@api_view(["POST"])
def search_rag(request):
    """Run semantic retrieval and grounded answer generation."""
    serializer = RagSearchSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=400)

    data = serializer.validated_data
    session_id = data.get("session_id", "").strip()
    if not session_id or session_id == "string":
        session_id = str(uuid.uuid4())
    try:
        result = search_rag_with_context(session_id, data["prompt"])
        return Response(result, status=200)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)
    except Exception as exc:
        return Response({"error": f"Failed to perform RAG search: {exc}"}, status=500)
