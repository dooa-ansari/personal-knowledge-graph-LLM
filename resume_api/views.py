import uuid
from pathlib import Path

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import PromptSerializer, RagSearchSerializer
from .services.langgraph_service import search_with_context
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

search_success_response = openapi.Response(
    description="Knowledge graph search completed with natural language answer",
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "prompt": openapi.Schema(type=openapi.TYPE_STRING, description="The user prompt"),
            "session_id": openapi.Schema(type=openapi.TYPE_STRING, description="The session ID for conversation context"),
            "model": openapi.Schema(type=openapi.TYPE_STRING, description="The model used"),
            "sparql_query": openapi.Schema(type=openapi.TYPE_STRING, description="The generated SPARQL query"),
            "query_results": openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description="The raw SPARQL query results from the knowledge graph",
                properties={
                    "columns": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_STRING),
                        description="Column names from the query result",
                    ),
                    "rows": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT),
                        description="Data rows from the query result",
                    ),
                    "row_count": openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of rows returned"),
                },
            ),
            "answer": openapi.Schema(type=openapi.TYPE_STRING, description="The natural language answer"),
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
    operation_description="Takes a user prompt, generates a SPARQL query via LangGraph/OpenRouter, executes it against the knowledge graph, and converts results to natural language. Conversation context is maintained across requests using a session ID.",
    operation_summary="Search knowledge graph with AI and conversation context",
    request_body=PromptSerializer,
    responses={
        200: search_success_response,
        400: error_response,
        500: error_response,
    },
)
@api_view(["POST"])
def search_knowledge_graph(request):
    """
    Endpoint that:
    1. Takes a user prompt and optional session ID
    2. Uses LangGraph to maintain conversation context
    3. Generates a SPARQL query from the prompt (with conversation history)
    4. Executes the SPARQL query against the RDF knowledge graph
    5. Converts the query results into natural language (with conversation history)
    6. Returns the natural language answer

    If no session_id is provided, a new one is generated and returned so the
    client can reuse it for follow-up questions.
    """
    prompt = request.data.get("prompt", "").strip()
    session_id = request.data.get("session_id", "").strip()

    if not prompt:
        return Response(
            {"error": "Prompt is required."},
            status=400,
        )

    # Generate a new session ID if none was provided
    # or if the Swagger UI placeholder value was sent
    if not session_id or session_id == "string":
        session_id = str(uuid.uuid4())

    try:
        result = search_with_context(session_id, prompt)
        return Response(result, status=200)
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=500,
        )
    except FileNotFoundError as e:
        return Response(
            {"error": str(e)},
            status=500,
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to query knowledge graph: {str(e)}"},
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
