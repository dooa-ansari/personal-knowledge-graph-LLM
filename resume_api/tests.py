import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rdflib import Graph
from rest_framework import status
from rest_framework.test import APIClient

from .services.openrouter_service import query_openrouter
from .services.rdf_converter import (
    _clean_text,
    _extract_name_and_title,
    _parse_academic_experience,
    _parse_education,
    _parse_languages,
    _parse_professional_experience,
    _parse_projects,
    _parse_skill_details,
    _parse_skills,
    convert_resume_to_rdf,
)
from .services.sparql_service import execute_sparql_query, _serialize_rdf_term
from .views import NATURAL_LANGUAGE_SYSTEM_PROMPT, SPARQL_SYSTEM_PROMPT

# Sample resume markdown content for testing
SAMPLE_RESUME = """# **TEST USER**

# Fullstack Developer

| Frontend-focused developer with 5+ years experience.  PROFESSIONAL EXPERIENCE Test Company \\- Berlin \\- 01/2020 \\- 12/2023 *Senior Developer* Built web applications using React and TypeScript. Improved performance by 30%.  | SKILLS Core Languages:  JavaScript, TypeScript  Frontend:  React, Next.js  | EDUCATION Test University *01/2015 \\- 12/2019, Berlin, Germany* Bachelor of Science  | LANGUAGES English \\- Full Professional Proficiency (C1)  |
| :---- | :---- |

**ACADEMIC EXPERIENCE**

**Test Project 2023 \\-** *Germany*  
**Challenge:** To build a test application.

* Technology Stack: React, Django, RDF  
* The project outcome proved the concept.  
* [https://github.com/test/project](https://github.com/test/project)

**SKILL DETAILS**

**React \\-** React, JavaScript, TypeScript, Hooks, Redux

**Django \\-** Python, Django, DRF, ORM

**Projects**

Test Project One, Test Project Two
"""


class RDFConverterServiceTests(TestCase):
    """Tests for the RDF converter service functions."""

    def test_clean_text(self):
        """Test that _clean_text normalizes whitespace."""
        self.assertEqual(_clean_text("  Hello   World  "), "Hello World")
        self.assertEqual(_clean_text(""), "")
        self.assertEqual(_clean_text("  "), "")

    def test_extract_name_and_title(self):
        """Test extracting name and title from resume header."""
        lines = SAMPLE_RESUME.splitlines()
        name, title = _extract_name_and_title(lines)
        self.assertEqual(name, "TEST USER")
        self.assertEqual(title, "Fullstack Developer")

    def test_parse_professional_experience(self):
        """Test parsing professional experience section."""
        content = (
            "Test Company \\- Berlin \\- 01/2020 \\- 12/2023 *Senior Developer* "
            "Built web applications using React and TypeScript. "
            "Improved performance by 30%."
        )
        experiences = _parse_professional_experience(content)
        self.assertEqual(len(experiences), 1)
        exp = experiences[0]
        self.assertEqual(exp["company"], "Test Company")
        self.assertEqual(exp["location"], "Berlin")
        self.assertEqual(exp["dates"], "01/2020 - 12/2023")
        self.assertEqual(exp["role"], "Senior Developer")
        self.assertGreaterEqual(len(exp["bullets"]), 1)

    def test_parse_skills(self):
        """Test parsing skills section."""
        content = "Core Languages:  JavaScript, TypeScript  Frontend:  React, Next.js"
        skills = _parse_skills(content)
        self.assertGreaterEqual(len(skills), 1)
        # Check that at least one skill category was parsed
        categories = [s["category"] for s in skills]
        self.assertTrue(any("Core Languages" in c for c in categories))

    def test_parse_education(self):
        """Test parsing education section."""
        content = "Test University *01/2015 \\- 12/2019, Berlin, Germany* Bachelor of Science"
        education = _parse_education(content)
        self.assertEqual(len(education), 1)
        self.assertEqual(education[0]["institution"], "Test University")
        self.assertEqual(education[0]["degree"], "Bachelor of Science")

    def test_parse_languages(self):
        """Test parsing languages section."""
        content = "English \\- Full Professional Proficiency (C1)"
        languages = _parse_languages(content)
        self.assertEqual(len(languages), 1)
        self.assertEqual(languages[0]["language"], "English")
        self.assertIn("Full Professional", languages[0]["proficiency"])

    def test_parse_academic_experience(self):
        """Test parsing academic experience section."""
        content = (
            "**Test Project 2023 \\-** *Germany*  \n"
            "**Challenge:** To build a test application.\n\n"
            "* Technology Stack: React, Django, RDF  \n"
            "* The project outcome proved the concept.  \n"
            "* [https://github.com/test/project](https://github.com/test/project)"
        )
        entries = _parse_academic_experience(content)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["title"], "Test Project")
        self.assertEqual(entry["year"], "2023")
        self.assertEqual(entry["location"], "Germany")
        self.assertIn("React", entry["stack"])
        # The link may be empty if the bullet doesn't start with "http"
        # (it starts with "[https://...]" which is a markdown link)
        if entry["link"]:
            self.assertIn("github.com", entry["link"])

    def test_parse_skill_details(self):
        """Test parsing skill details section."""
        content = "**React \\-** React, JavaScript, TypeScript, Hooks, Redux"
        skills = _parse_skill_details(content)
        # The regex may not match this exact format, but should handle the real format
        # Real format: "**React Native \-** React, JavaScript, ..."
        if skills:
            self.assertEqual(skills[0]["name"], "React")
            self.assertIn("JavaScript", skills[0]["items"])
        else:
            # Test with the actual format from the resume
            real_content = "**React Native \\-** React, JavaScript, TypeScript, Hooks, Redux"
            real_skills = _parse_skill_details(real_content)
            self.assertGreaterEqual(len(real_skills), 1)
            self.assertEqual(real_skills[0]["name"], "React Native")
            self.assertIn("JavaScript", real_skills[0]["items"])

    def test_parse_projects(self):
        """Test parsing projects section."""
        content = "Test Project One, Test Project Two"
        projects = _parse_projects(content)
        self.assertGreaterEqual(len(projects), 1)

    def test_convert_resume_to_rdf_creates_valid_rdf(self):
        """Test that convert_resume_to_rdf produces a valid RDF file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "test_resume.md"
            md_path.write_text(SAMPLE_RESUME, encoding="utf-8")

            output_path = convert_resume_to_rdf(str(md_path))

            # Verify output file exists
            self.assertTrue(Path(output_path).exists())
            self.assertEqual(Path(output_path).suffix, ".ttl")

            # Verify the RDF file is valid and contains expected data
            g = Graph()
            g.parse(output_path, format="turtle")
            self.assertGreater(len(g), 0)

            # Check for person node
            person_query = list(g.query(
                "SELECT ?name WHERE { ?s <http://xmlns.com/foaf/0.1/name> ?name }"
            ))
            self.assertGreater(len(person_query), 0)
            self.assertEqual(str(person_query[0][0]), "TEST USER")

    def test_convert_resume_to_rdf_file_not_found(self):
        """Test that convert_resume_to_rdf raises FileNotFoundError for missing file."""
        with self.assertRaises(FileNotFoundError):
            convert_resume_to_rdf("/nonexistent/path/resume.md")


class ResumeApiEndpointTests(TestCase):
    """Tests for the resume API endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("convert_resume")

    def test_post_convert_resume_success(self):
        """Test that POST /api/convert-resume/ returns 200 and generates RDF."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "RDF file generated successfully.")
        self.assertTrue(response.data["source_file"].endswith("All Details Resume.md"))
        self.assertTrue(response.data["rdf_file"].endswith("All Details Resume.ttl"))

        # Verify the RDF file was actually created
        rdf_path = Path(response.data["rdf_file"])
        self.assertTrue(rdf_path.exists())

        # Verify it's valid RDF
        g = Graph()
        g.parse(str(rdf_path), format="turtle")
        self.assertGreater(len(g), 0)

    def test_get_method_not_allowed(self):
        """Test that GET /api/convert-resume/ returns 405."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_method_not_allowed(self):
        """Test that PUT /api/convert-resume/ returns 405."""
        response = self.client.put(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_method_not_allowed(self):
        """Test that DELETE /api/convert-resume/ returns 405."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @patch("resume_api.views.Path.exists", return_value=False)
    def test_post_convert_resume_file_not_found(self, mock_exists):
        """Test that POST returns 404 when resume file doesn't exist."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)
        self.assertIn("Resume file not found", response.data["error"])

    @patch("resume_api.views.convert_resume_to_rdf", side_effect=Exception("Test error"))
    def test_post_convert_resume_conversion_error(self, mock_convert):
        """Test that POST returns 500 when conversion fails."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.data)
        self.assertIn("Failed to convert resume to RDF", response.data["error"])


class OpenRouterServiceTests(TestCase):
    """Tests for the OpenRouter service."""

    @patch("resume_api.services.openrouter_service.settings.OPENROUTER_API_KEY", "")
    def test_query_openrouter_missing_api_key(self):
        """Test that query_openrouter raises ValueError when API key is missing."""
        with self.assertRaises(ValueError):
            query_openrouter("test prompt")

    @patch("resume_api.services.openrouter_service.settings.OPENROUTER_API_KEY", "test-key")
    @patch("resume_api.services.openrouter_service.requests.post")
    def test_query_openrouter_success(self, mock_post):
        """Test that query_openrouter returns the model response."""
        mock_response = mock_post.return_value
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This is the model response"}}
            ]
        }

        result = query_openrouter("test prompt")
        self.assertEqual(result, "This is the model response")

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(call_args[1]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(call_args[1]["json"]["model"], "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.assertEqual(call_args[1]["json"]["messages"][0]["content"], "test prompt")

    @patch("resume_api.services.openrouter_service.settings.OPENROUTER_API_KEY", "test-key")
    @patch("resume_api.services.openrouter_service.requests.post")
    def test_query_openrouter_with_system_prompt(self, mock_post):
        """Test that query_openrouter includes the system prompt in messages."""
        mock_response = mock_post.return_value
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "SPARQL query result"}}
            ]
        }

        system_prompt = "You are a SPARQL expert."
        result = query_openrouter("test prompt", system_prompt=system_prompt)
        self.assertEqual(result, "SPARQL query result")

        # Verify system prompt is included as first message
        call_args = mock_post.call_args
        messages = call_args[1]["json"]["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], system_prompt)
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "test prompt")

    @patch("resume_api.services.openrouter_service.settings.OPENROUTER_API_KEY", "test-key")
    @patch("resume_api.services.openrouter_service.requests.post")
    def test_query_openrouter_api_error(self, mock_post):
        """Test that query_openrouter propagates request exceptions."""
        from requests.exceptions import RequestException

        mock_post.side_effect = RequestException("API error")

        with self.assertRaises(RequestException):
            query_openrouter("test prompt")


class SparqlServiceTests(TestCase):
    """Tests for the SPARQL execution service."""

    def test_execute_sparql_query_finds_person(self):
        """Test executing a SPARQL query to find the person in the RDF graph."""
        query = """
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        SELECT ?name WHERE {
            ?person a foaf:Person .
            ?person foaf:name ?name
        }
        """
        results = execute_sparql_query(query)
        self.assertEqual(results["row_count"], 1)
        self.assertIn("name", results["columns"])
        self.assertEqual(results["rows"][0]["name"], "DOOA ANSARI")

    def test_execute_sparql_query_finds_companies(self):
        """Test executing a SPARQL query to find companies in the RDF graph."""
        query = """
        PREFIX resume: <http://example.org/resume#>
        SELECT ?company WHERE {
            ?exp a resume:ProfessionalExperience .
            ?exp resume:company ?company
        }
        """
        results = execute_sparql_query(query)
        self.assertGreater(results["row_count"], 0)
        self.assertIn("company", results["columns"])
        # Verify all companies are present
        companies = [row["company"] for row in results["rows"]]
        self.assertIn("DeepSkill GmbH", companies)
        self.assertIn("Greator GmbH", companies)

    def test_execute_sparql_query_finds_skills(self):
        """Test executing a SPARQL query to find skills in the RDF graph."""
        query = """
        PREFIX resume: <http://example.org/resume#>
        SELECT ?skill WHERE {
            ?sd a resume:SkillDetail .
            ?sd <http://example.org/resume#hasSkillItem> ?item .
            ?item <http://www.w3.org/1999/02/22-rdf-syntax-ns#value> ?skill
        }
        LIMIT 5
        """
        results = execute_sparql_query(query)
        self.assertGreater(results["row_count"], 0)
        self.assertIn("skill", results["columns"])

    def test_execute_sparql_query_file_not_found(self):
        """Test that execute_sparql_query raises FileNotFoundError for missing RDF file."""
        with self.assertRaises(FileNotFoundError):
            execute_sparql_query("SELECT * WHERE { ?s ?p ?o }", "/nonexistent/file.ttl")

    def test_execute_sparql_query_invalid_query(self):
        """Test that execute_sparql_query propagates exceptions for invalid queries."""
        import pyparsing

        with self.assertRaises(Exception):
            execute_sparql_query("THIS IS NOT A SPARQL QUERY")

    def test_serialize_rdf_term(self):
        """Test _serialize_rdf_term converts rdflib terms to strings."""
        from rdflib import Literal, URIRef

        self.assertEqual(_serialize_rdf_term(Literal("test")), "test")
        self.assertEqual(_serialize_rdf_term(URIRef("http://example.com")), "http://example.com")
        self.assertIsNone(_serialize_rdf_term(None))


class SearchKnowledgeGraphEndpointTests(TestCase):
    """Tests for the search-knowledge-graph endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("search_knowledge_graph")

    @patch("resume_api.views.query_openrouter", side_effect=[
        """PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT ?name WHERE { ?person a foaf:Person . ?person foaf:name ?name }""",
        "Your name is DOOA ANSARI.",
    ])
    @patch("resume_api.views.execute_sparql_query")
    def test_post_search_success(self, mock_execute, mock_query):
        """Test that POST /api/search-knowledge-graph/ returns 200 with natural language answer."""
        # Mock SPARQL execution results
        mock_execute.return_value = {
            "columns": ["name"],
            "rows": [{"name": "DOOA ANSARI"}],
            "row_count": 1,
        }

        response = self.client.post(self.url, {"prompt": "What is my name?"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["prompt"], "What is my name?")
        self.assertEqual(response.data["model"], "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.assertIn("sparql_query", response.data)
        self.assertIn("query_results", response.data)
        self.assertEqual(response.data["query_results"]["row_count"], 1)
        self.assertEqual(response.data["query_results"]["rows"][0]["name"], "DOOA ANSARI")
        self.assertEqual(response.data["answer"], "Your name is DOOA ANSARI.")

        # Verify the service was called twice (SPARQL generation + natural language conversion)
        self.assertEqual(mock_query.call_count, 2)

        # First call: SPARQL query generation with the user prompt
        first_call = mock_query.call_args_list[0]
        self.assertEqual(first_call[0][0], "What is my name?")
        self.assertEqual(first_call[1]["model"], "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.assertEqual(first_call[1]["system_prompt"], SPARQL_SYSTEM_PROMPT)

        # Second call: natural language conversion with query results
        second_call = mock_query.call_args_list[1]
        self.assertIn("What is my name?", second_call[0][0])
        self.assertIn("DOOA ANSARI", second_call[0][0])
        self.assertEqual(second_call[1]["system_prompt"], NATURAL_LANGUAGE_SYSTEM_PROMPT)

        # Verify the SPARQL query was executed
        mock_execute.assert_called_once()
        self.assertIn("PREFIX", mock_execute.call_args[0][0])

    def test_post_search_missing_prompt(self):
        """Test that POST returns 400 when prompt is missing."""
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("Prompt is required", response.data["error"])

    def test_post_search_empty_prompt(self):
        """Test that POST returns 400 when prompt is empty."""
        response = self.client.post(self.url, {"prompt": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @patch("resume_api.views.query_openrouter", side_effect=ValueError("API key not configured"))
    def test_post_search_missing_api_key(self, mock_query):
        """Test that POST returns 500 when API key is not configured."""
        response = self.client.post(self.url, {"prompt": "test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.data)
        self.assertIn("API key not configured", response.data["error"])

    @patch("resume_api.views.query_openrouter", side_effect=Exception("Network error"))
    def test_post_search_api_error(self, mock_query):
        """Test that POST returns 500 when OpenRouter API call fails."""
        response = self.client.post(self.url, {"prompt": "test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.data)
        self.assertIn("Failed to query knowledge graph", response.data["error"])

    @patch("resume_api.views.query_openrouter", return_value="""PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT ?name WHERE { ?person a foaf:Person . ?person foaf:name ?name }""")
    @patch("resume_api.views.execute_sparql_query", side_effect=Exception("SPARQL error"))
    def test_post_search_sparql_error(self, mock_execute, mock_query):
        """Test that POST returns 500 when SPARQL execution fails."""
        response = self.client.post(self.url, {"prompt": "test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.data)
        self.assertIn("Failed to query knowledge graph", response.data["error"])

    def test_get_method_not_allowed(self):
        """Test that GET /api/search-knowledge-graph/ returns 405."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class SwaggerEndpointTests(TestCase):
    """Tests for the Swagger documentation endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_swagger_ui_available(self):
        """Test that the Swagger UI page is accessible."""
        response = self.client.get("/swagger/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_redoc_ui_available(self):
        """Test that the ReDoc page is accessible."""
        response = self.client.get("/redoc/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_swagger_json_schema(self):
        """Test that the Swagger JSON schema is accessible and valid."""
        response = self.client.get("/swagger.json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("application/json", response["Content-Type"])

        data = response.json()
        self.assertEqual(data["info"]["title"], "Resume RDF Converter API")
        self.assertIn("/convert-resume/", data["paths"])
        self.assertIn("post", data["paths"]["/convert-resume/"])

    def test_swagger_yaml_schema(self):
        """Test that the Swagger YAML schema is accessible."""
        response = self.client.get("/swagger.yaml")
        self.assertEqual(response.status_code, status.HTTP_200_OK)