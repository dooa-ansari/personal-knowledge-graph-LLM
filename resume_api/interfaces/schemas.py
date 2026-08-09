"""Swagger/OpenAPI response schemas for the resume API."""

from drf_yasg import openapi


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