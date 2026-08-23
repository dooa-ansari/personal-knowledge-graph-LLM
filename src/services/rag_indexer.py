"""Build and persist fine-grained vector chunks from the resume graph."""

import logging
from pathlib import Path
from typing import TypedDict

from rdflib import Graph, Literal, RDF

from src import config
from src.utils import create_embeddings, get_chroma_client, require_api_key

logger = logging.getLogger(__name__)

DEFAULT_RDF_PATH = config.PROJECT_ROOT / "All Details Resume.ttl"


class ResumeChunk(TypedDict):
    id: str
    document: str
    metadata: dict[str, str]


def _local_name(value) -> str:
    return str(value).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _literal_by_name(graph, subject, name: str) -> str:
    for predicate, value in graph.predicate_objects(subject):
        if _local_name(predicate) == name and isinstance(value, Literal):
            return str(value)
    return ""


def build_resume_chunks(rdf_file_path: str | None = None) -> list[ResumeChunk]:
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
                {key: value for key, value in parent.items() if value}
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
    require_api_key()

    chunks = build_resume_chunks(rdf_file_path)
    logger.info("Built %d chunks from RDF graph", len(chunks))

    client = get_chroma_client()
    try:
        client.delete_collection(config.RAG_COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(config.RAG_COLLECTION_NAME)

    response = create_embeddings([chunk["document"] for chunk in chunks])
    collection.add(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["document"] for chunk in chunks],
        metadatas=[chunk["metadata"] for chunk in chunks],
        embeddings=[item.embedding for item in response.data],
    )
    logger.info("Indexed %d chunks into Chroma collection '%s'", len(chunks), config.RAG_COLLECTION_NAME)
    return len(chunks)