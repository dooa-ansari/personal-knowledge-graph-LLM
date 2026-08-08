"""
SPARQL execution service for querying the RDF knowledge graph.
"""

from pathlib import Path

from rdflib import Graph


def validate_sparql_query(query: str) -> None:
    """Validate SPARQL syntax without executing the query.

    Raises the parser exception when the query is invalid.
    """
    Graph().query(query)


def execute_sparql_query(query: str, rdf_file_path: str = None) -> dict:
    """
    Execute a SPARQL query against the RDF knowledge graph (.ttl file).

    Args:
        query: The SPARQL query to execute
        rdf_file_path: Path to the RDF file. Defaults to the generated resume RDF file.

    Returns:
        A dict containing the query results with column names and rows.

    Raises:
        FileNotFoundError: If the RDF file doesn't exist
        Exception: If the SPARQL query execution fails
    """
    # Determine RDF file path (default to project root's "All Details Resume.ttl")
    if rdf_file_path is None:
        rdf_file_path = (
            Path(__file__).resolve().parent.parent.parent / "All Details Resume.ttl"
        )

    if not Path(rdf_file_path).exists():
        raise FileNotFoundError(f"RDF file not found at: {rdf_file_path}")

    # Load the RDF graph
    graph = Graph()
    graph.parse(str(rdf_file_path), format="turtle")

    # Execute the SPARQL query
    results = graph.query(query)

    # Extract column names
    columns = [str(var) for var in results.vars]

    # Extract rows (convert rdflib terms to JSON-serializable values)
    rows = []
    for row in results:
        row_data = {}
        for i, var in enumerate(results.vars):
            value = row[i]
            row_data[str(var)] = _serialize_rdf_term(value)
        rows.append(row_data)

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


def _serialize_rdf_term(term) -> str:
    """Convert an rdflib term to a JSON-serializable string."""
    from rdflib import Literal, URIRef, BNode

    if isinstance(term, Literal):
        return str(term)
    elif isinstance(term, URIRef):
        return str(term)
    elif isinstance(term, BNode):
        return str(term)
    elif term is None:
        return None
    return str(term)