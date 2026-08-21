"""Rebuild the ChromaDB RAG index from the Turtle resume graph."""

import argparse
import logging
import sys

from src.services.rag_indexer import reindex_rag

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Rebuild the ChromaDB RAG index.")
    parser.add_argument("--rdf-file", help="Optional path to a Turtle file.")
    args = parser.parse_args()

    try:
        count = reindex_rag(args.rdf_file)
        print(f"Indexed {count} resume chunks.")
    except Exception as exc:
        logger.error("Reindex failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()