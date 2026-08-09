"""Build and persist fine-grained vector chunks from the resume graph."""

import os
from pathlib import Path

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.config import Settings as ChromaSettings
from django.conf import settings
from openai import OpenAI
from rdflib import Graph, Literal, RDF


DEFAULT_RDF_PATH = Path(__file__).resolve().parents[2] / "All Details Resume.ttl"



def _local_name(value) -> str:
    return str(value).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _literal_by_name(graph, subject, name: str) -> str:
    for predicate, value in graph.predicate_objects(subject):
        if _local_name(predicate) == name and isinstance(value, Literal):
            return str(value)
    return ""


def build_resume_chunks(rdf_file_path: str | None = None) -> list[dict]:
    """Create one contextual chunk per meaningful RDF entity or bullet point."""
    path = Path(rdf_file_path) if rdf_file_path else DEFAULT_RDF_PATH
    graph = Graph()
    graph.parse(str(path), format="turtle")
    chunks = []

    parent_context = {}
    for parent, predicate, child in graph.triples((None, None, None)):
        parent_type = graph.value(parent, RDF.type)
        child_type = graph.value(child, RDF.type)
        if parent_type and child_type and _local_name(child_type) == "BulletPoint":
            parent_context[child] = {
                "parent_entity": str(parent),
                "company": _literal_by_name(graph, parent, "company"),
                "role": _literal_by_name(graph, parent, "role"),
                "dates": _literal_by_name(graph, parent, "dates"),
                "location": _literal_by_name(graph, parent, "location"),
            }

    for subject, _, entity_type in graph.triples((None, RDF.type, None)):
        entity_name = _local_name(entity_type)
        if entity_name == "Person":
            continue
        values = []
        for _, predicate, value in graph.triples((subject, None, None)):
            if predicate == RDF.type or not isinstance(value, Literal):
                continue
            values.append(f"{_local_name(predicate)}: {value}")
        if not values:
            continue

        parent = ""
        for parent_subject, predicate, _ in graph.triples((None, None, subject)):
            if predicate != RDF.type:
                parent = _local_name(parent_subject)
                break
        context = f"{entity_name}"
        metadata = {"entity_type": entity_name, "entity_uri": str(subject)}
        if subject in parent_context:
            parent = parent_context[subject]
            parent_label = ", ".join(
                value for value in [
                    parent["company"],
                    parent["role"],
                    parent["dates"],
                    parent["location"],
                ] if value
            )
            context += f" at {parent_label}"
            metadata.update(
                {
                    key: value
                    for key, value in parent.items()
                    if value
                }
            )
            parent = parent["parent_entity"]
        if parent:
            context += f" (related to {parent})"
        chunks.append(
            {
                "id": str(subject),
                "document": context + ": " + "; ".join(values),
                "metadata": metadata,
            }
        )
    return chunks


def reindex_rag(rdf_file_path: str | None = None) -> int:
    """Rebuild the configured Chroma collection using OpenAI embeddings."""
    api_key = settings.OPENROUTER_API_KEY
    if not api_key or api_key == "your-openrouter-api-key-here":
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    chunks = build_resume_chunks(rdf_file_path)
    client = chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_PATH,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    try:
        client.delete_collection(settings.RAG_COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(settings.RAG_COLLECTION_NAME)
    embedding_client = OpenAI(
        api_key=api_key,
        base_url=settings.OPENROUTER_BASE_URL,
    )
    response = embedding_client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=[chunk["document"] for chunk in chunks],
    )
    collection.add(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["document"] for chunk in chunks],
        metadatas=[chunk["metadata"] for chunk in chunks],
        embeddings=[item.embedding for item in response.data],
    )
    return len(chunks)