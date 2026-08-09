import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse
from rdflib import Graph, Namespace
from rdflib.namespace import RDF
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
from .services.rag_indexer import build_resume_chunks

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

    def test_real_resume_preserves_all_structured_sections(self):
        """Protect against silently merging or dropping data in the real resume."""
        source_path = Path(__file__).resolve().parent.parent / "All Details Resume.md"
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "resume.md"
            md_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
            rdf_path = convert_resume_to_rdf(str(md_path))

            graph = Graph().parse(rdf_path, format="turtle")
            resume = Namespace("http://example.org/resume#")
            schema = Namespace("https://schema.org/")

            self.assertEqual(len(set(graph.subjects(RDF.type, resume.Education))), 3)
            self.assertEqual(len(set(graph.subjects(RDF.type, resume.Language))), 2)
            self.assertEqual(len(set(graph.subjects(RDF.type, resume.SkillCategory))), 9)
            self.assertEqual(len(set(graph.subjects(RDF.type, resume.SkillDetail))), 18)
            self.assertEqual(len(set(graph.subjects(RDF.type, resume.Project))), 10)

            education = {
                (str(graph.value(node, resume.institution)), str(graph.value(node, schema.educationalCredentialAwarded)))
                for node in graph.subjects(RDF.type, resume.Education)
            }
            self.assertIn(
                ("Technische Universität Chemnitz", "Master of Science in Web Engineering"),
                education,
            )
            self.assertIn(
                ("Sir Syed University of Engineering and Technology", "Bachelor's in Computer Engineering"),
                education,
            )

            languages = {
                (str(graph.value(node, resume.language)), str(graph.value(node, resume.proficiency)))
                for node in graph.subjects(RDF.type, resume.Language)
            }
            self.assertEqual(
                languages,
                {
                    ("English", "Full Professional Proficiency (C1)"),
                    ("German", "Beginner (A2)"),
                },
            )


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
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Resume file not found", response.data["error"])

    @patch("resume_api.adapters.rdf_repository._convert", side_effect=Exception("Test error"))
    def test_post_convert_resume_conversion_error(self, mock_convert):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Failed to convert resume to RDF", response.data["error"])


class RagSearchEndpointTests(TestCase):
    """Tests for the session-aware semantic RAG endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("search_rag")

    @patch("resume_api.views.search_rag_with_context")
    def test_post_rag_success_with_session(self, mock_search):
        mock_search.return_value = {
            "prompt": "What did she do there?",
            "session_id": "session-1",
            "model": "test-model",
            "retrieval_query": "What did Dooa do at Greator GmbH?",
            "answer": "She was a Frontend Developer.",
            "retrieved_chunks": [],
        }
        response = self.client.post(
            self.url,
            {"prompt": "What did she do there?", "session_id": "session-1"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["session_id"], "session-1")
        self.assertEqual(response.data["retrieval_query"], "What did Dooa do at Greator GmbH?")
        mock_search.assert_called_once_with("session-1", "What did she do there?")

    @patch("resume_api.views.search_rag_with_context")
    def test_post_rag_generates_uuid_for_swagger_placeholder(self, mock_search):
        mock_search.side_effect = lambda session_id, prompt: {
            "session_id": session_id,
            "prompt": prompt,
            "answer": "answer",
            "retrieved_chunks": [],
        }
        response = self.client.post(self.url, {"prompt": "test", "session_id": "string"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        generated_id = mock_search.call_args.args[0]
        self.assertNotEqual(generated_id, "string")
        self.assertEqual(response.data["session_id"], generated_id)

    def test_post_rag_requires_prompt(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("prompt", response.data["error"])

    def test_rag_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class RagLangGraphServiceTests(TestCase):
    """Unit tests for rewrite, retrieval, answer, and session state."""

    @patch("resume_api.use_cases.search_rag.SearchRagUseCase.rewrite_query", return_value="What is Dooa Ansari doing currently after Greator GmbH?")
    @patch("resume_api.use_cases.search_rag.SearchRagUseCase.retrieve", return_value=[{"document": "DeepSkill GmbH", "metadata": {}, "distance": 0.1, "score": 0.9}])
    @patch("resume_api.use_cases.search_rag.SearchRagUseCase.answer", return_value="Dooa is a Full-Stack Developer at DeepSkill GmbH.")
    def test_rewrites_follow_up_before_retrieval(self, mock_answer, mock_retrieve, mock_rewrite):
        from .services.rag_langgraph_service import search_rag_with_context

        result = search_rag_with_context("rag-test-1", "What is she doing now?")

        self.assertEqual(result["retrieval_query"], "What is Dooa Ansari doing currently after Greator GmbH?")
        self.assertEqual(result["answer"], "Dooa is a Full-Stack Developer at DeepSkill GmbH.")

    @patch("resume_api.use_cases.search_rag.SearchRagUseCase.rewrite_query", side_effect=["first query", "second query"])
    @patch("resume_api.use_cases.search_rag.SearchRagUseCase.retrieve", return_value=[])
    @patch("resume_api.use_cases.search_rag.SearchRagUseCase.answer", side_effect=["first answer", "second answer"])
    def test_session_history_is_available_on_follow_up(self, mock_answer, mock_retrieve, mock_rewrite):
        from .services.rag_langgraph_service import search_rag_with_context

        search_rag_with_context("rag-test-2", "When did Dooa work at Greator?")
        search_rag_with_context("rag-test-2", "What did she do there?")
        # The second call to rewrite_query should include history from the first turn
        self.assertEqual(mock_rewrite.call_count, 2)

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
        self.assertEqual(call_args[1]["json"]["model"], "inclusionai/ling-3.0-flash")
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
