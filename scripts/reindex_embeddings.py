"""Rebuild the ChromaDB RAG index from the Turtle resume graph."""

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.services.rag_indexer import reindex_rag

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    try:
        count = reindex_rag()
        print(f"Indexed {count} resume chunks.")
    except Exception as exc:
        logger.error("Reindex failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()