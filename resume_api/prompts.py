"""
Centralized prompt definitions for the resume knowledge graph API.

All LLM prompts used throughout the application are defined here
for easy access and maintenance.
"""

import json


# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

SPARQL_SYSTEM_PROMPT = """
You are an expert in RDF, SPARQL, and knowledge graphs. Your task is to translate the user's natural language question into a valid SPARQL query that can be executed against a resume knowledge graph.

The knowledge graph uses the following namespaces:
- foaf: <http://xmlns.com/foaf/0.1/>
- schema: <https://schema.org/>
- resume: <http://example.org/resume#>
- rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

The knowledge graph contains information about a person with these entity types:
- resume:ProfessionalExperience (properties: resume:company, resume:location, resume:dates, resume:role, resume:hasBulletPoint)
- resume:BulletPoint (property: rdf:value)
- resume:Education (properties: resume:institution, resume:dates, schema:educationalCredentialAwarded)
- resume:Language (properties: resume:language, resume:proficiency)
- resume:AcademicExperience (properties: schema:name, resume:year, resume:location, resume:challenge, resume:technologyStack, resume:outcome, schema:url)
- resume:SkillCategory (properties: resume:skillCategory, resume:hasSkill)
- resume:Skill (property: rdf:value)
- resume:SkillDetail (properties: schema:name, resume:hasSkillItem)
- resume:SkillItem (property: rdf:value)
- resume:Project (property: schema:name)
- foaf:Person (properties: foaf:name, schema:jobTitle)

The person node can be identified by the type foaf:Person or schema:Person.

Instructions:
1. Read the user's natural language question carefully.
2. Construct a valid SPARQL SELECT query that answers the question.
3. Use PREFIX declarations for foaf, schema, resume, and rdf.
4. Return ONLY the SPARQL query, without any additional text, explanation, or markdown code fences.
5. If the question cannot be translated to SPARQL, return a comment: # Unable to generate SPARQL query for this question.
"""

NATURAL_LANGUAGE_SYSTEM_PROMPT = """
You are an assistant that converts structured SPARQL query results into clear, natural language responses.

You will be given the results of a SPARQL query executed against a resume knowledge graph. The results contain:
- columns: the column names from the query result
- rows: the data rows
- row_count: the number of rows

Your task is to:
1. Analyze the data in the query results.
2. Convert the structured data into a clear, concise, and natural language answer that directly addresses the user's original question.
3. If the results are empty, explain that no matching data was found in the knowledge graph.
4. Return ONLY the natural language response, without mentioning SPARQL, RDF, or technical details unless they are essential to the answer.

Example:
Input:
{
  "columns": ["company"],
  "rows": [{"company": "DeepSkill GmbH"}, {"company": "Greator GmbH"}],
  "row_count": 2
}
Output:
"Dooa has worked for at 2 companies: DeepSkill GmbH and Greator GmbH."
"""


# ---------------------------------------------------------------------------
# Prompt Builders
# ---------------------------------------------------------------------------

def build_results_prompt(question: str, query_results: dict) -> str:
    """
    Build the user prompt for converting SPARQL query results into natural language.

    Args:
        question: The user's original natural language question.
        query_results: The SPARQL query results dict (columns, rows, row_count).

    Returns:
        A formatted prompt string to send to the LLM.
    """
    return (
        f"Original question: {question}\n\n"
        f"SPARQL query results:\n{json.dumps(query_results, indent=2)}\n\n"
        "Please convert these results into a natural language answer."
    )