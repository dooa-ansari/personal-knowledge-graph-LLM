from pathlib import Path

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .prompts import (
    NATURAL_LANGUAGE_SYSTEM_PROMPT,
    SPARQL_SYSTEM_PROMPT,
    build_results_prompt,
)
from .serializers import PromptSerializer
from .services.openrouter_service import query_openrouter
from .services.rdf_converter import convert_resume_to_rdf
from .services.sparql_service import execute_sparql_query

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

search_success_response = openapi.Response(
    description="Knowledge graph search completed with natural language answer",
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "prompt": openapi.Schema(type=openapi.TYPE_STRING, description="The user prompt"),
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
    operation_description="Takes a user prompt, generates a SPARQL query via OpenRouter, executes it against the knowledge graph, and converts results to natural language.",
    operation_summary="Search knowledge graph with AI and get natural language answer",
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
    1. Takes a user prompt
    2. Uses OpenRouter to convert it into a SPARQL query
    3. Executes the SPARQL query against the RDF knowledge graph
    4. Sends the query results back to OpenRouter to convert into natural language
    5. Returns the natural language answer
    """
    prompt = request.data.get("prompt", "").strip()

    if not prompt:
        return Response(
            {"error": "Prompt is required."},
            status=400,
        )

    try:
        model = "nvidia/nemotron-3-ultra-550b-a55b:free"

        # Step 1: Generate SPARQL query from the user prompt
        sparql_query = query_openrouter(
            prompt,
            model=model,
            system_prompt=SPARQL_SYSTEM_PROMPT,
        )

        # Step 2: Execute the SPARQL query against the RDF knowledge graph
        query_results = execute_sparql_query(sparql_query)

        # Step 3: Convert the query results into natural language
        results_prompt = build_results_prompt(prompt, query_results)
        natural_language_answer = query_openrouter(
            results_prompt,
            model=model,
            system_prompt=NATURAL_LANGUAGE_SYSTEM_PROMPT,
        )

        return Response(
            {
                "prompt": prompt,
                "model": model,
                "sparql_query": sparql_query,
                "query_results": query_results,
                "answer": natural_language_answer,
            },
            status=200,
        )
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