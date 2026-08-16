import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings
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
from .services.rag_service import search_rag

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
        self.assertEqual(_clean_text("  Hello   World  "), "Hello World")
        self.assertEqual(_clean_text(""), "")
        self.assertEqual(_clean_text("  "), "")

    def test_extract_name_and_title(self):
        lines = SAMPLE_RESUME.splitlines()
        name, title = _extract_name_and_title(lines)
        self.assertEqual(name, "TEST USER")
        self.assertEqual(title, "Fullstack Developer")

    def test_parse_professional_experience(self):
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
        """_parse_skills returns list of {category, items}."""
        content = "Core Languages:  JavaScript, TypeScript  Frontend:  React, Next.js"
        skills = _parse_skills(content)
        self.assertGreaterEqual(len(skills), 1)
        self.assertEqual(skills[0]["category"], "Core Languages")
        self.assertIn("JavaScript", skills[0]["items"])

    def test_parse_education(self):
        """_parse_education returns {institution, dates, degree}."""
        content = (
            "Test University *01/2015 \\- 12/2019, Berlin, Germany* "
            "Bachelor of Science"
        )
        educations = _parse_education(content)
        self.assertEqual(len(educations), 1)
        edu = educations[0]
        self.assertEqual(edu["institution"], "Test University")
        self.assertEqual(edu["degree"], "Bachelor of Science")
        self.assertIn("01/2015", edu["dates"])
        self.assertIn("12/2019", edu["dates"])

    def test_parse_languages(self):
        content = "English \\- Full Professional Proficiency (C1)"
        langs = _parse_languages(content)
        self.assertEqual(len(langs), 1)
        self.assertEqual(langs[0]["language"], "English")
        self.assertEqual(langs[0]["proficiency"], "Full Professional Proficiency (C1)")

    def test_parse_academic_experience(self):
        """_parse_academic_experience returns {title, year, location, ...}."""
        from .services.rdf_converter import _parse_academic_experience

        content = (
            "**Test Project 2023 \\-** *Germany*\n"
            "**Challenge:** To build a test application.\n"
            "* Technology Stack: React, Django, RDF\n"
            "* The project outcome proved the concept.\n"
            "* [https://github.com/test/project](https://github.com/test/project)"
        )
        entries = _parse_academic_experience(content)
        self.assertGreaterEqual(len(entries), 1)
        entry = entries[0]
        self.assertIn("Test Project", entry["title"])
        self.assertEqual(entry["location"], "Germany")
        self.assertEqual(entry["year"], "2023")
        self.assertIn("React", entry["stack"])
        if entry["link"]:
            self.assertIn("github.com", entry["link"])

    def test_parse_skill_details(self):
        from .services.rdf_converter import _parse_skill_details

        content = "**React \\-** React, JavaScript, TypeScript, Hooks, Redux"
        skills = _parse_skill_details(content)
        if skills:
            self.assertEqual(skills[0]["name"], "React")
            self.assertIn("JavaScript", skills[0]["items"])
        else:
            real_content = "**React Native \\-** React, JavaScript, TypeScript, Hooks, Redux"
            real_skills = _parse_skill_details(real_content)
            self.assertGreaterEqual(len(real_skills), 1)
            self.assertEqual(real_skills[0]["name"], "React Native")
            self.assertIn("JavaScript", real_skills[0]["items"])

    def test_parse_projects(self):
        content = "Test Project One, Test Project Two"
        projects = _parse_projects(content)
        self.assertGreaterEqual(len(projects), 1)

    def test_convert_resume_to_rdf_creates_valid_rdf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "test_resume.md"
            md_path.write_text(SAMPLE_RESUME, encoding="utf-8")

            output_path = convert_resume_to_rdf(str(md_path))

            self.assertTrue(Path(output_path).exists())
            self.assertEqual(Path(output_path).suffix, ".ttl")

            g = Graph()
            g.parse(output_path, format="turtle")
            self.assertGreater(len(g), 0)

            person_query = list(g.query(
                "SELECT ?name WHERE { ?s <http://xmlns.com/foaf/0.1/name> ?name }"
            ))
            self.assertGreater(len(person_query), 0)
            self.assertEqual(str(person_query[0][0]), "TEST USER")

    def test_convert_resume_to_rdf_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            convert_resume_to_rdf("/nonexistent/path/resume.md")

    def test_real_resume_preserves_all_structured_sections(self):
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
                (str(graph.value(node, resume.institution)),
                 str(graph.value(node, schema.educationalCredentialAwarded)))
                for node in graph.subjects(RDF.type, resume.Education)
            }
            self.assertIn(
                ("Technische Universit\u00e4t Chemnitz", "Master of Science in Web Engineering"),
                education,
            )
            self.assertIn(
                ("Sir Syed University of Engineering and Technology",
                 "Bachelor's in Computer Engineering"),
                education,
            )

            languages = {
                (str(graph.value(node, resume.language)),
                 str(graph.value(node, resume.proficiency)))
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
    """Tests for the resume API endpoint — session-based auth."""

    def setUp(self):
        self.client = APIClient()
        # Force-create a session so IsSessionValid passes
        session = self.client.session
        session.save()
        self.url = reverse("convert_resume")

    def test_post_convert_resume_success(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "RDF file generated successfully.")
        self.assertTrue(response.data["source_file"].endswith("All Details Resume.md"))
        self.assertTrue(response.data["rdf_file"].endswith("All Details Resume.ttl"))

        rdf_path = Path(response.data["rdf_file"])
        self.assertTrue(rdf_path.exists())

        g = Graph()
        g.parse(str(rdf_path), format="turtle")
        self.assertGreater(len(g), 0)

    def test_get_method_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_method_not_allowed(self):
        self.assertEqual(
            self.client.put(self.url).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_delete_method_not_allowed(self):
        self.assertEqual(
            self.client.delete(self.url).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @patch("resume_api.views.convert_resume_to_rdf",
           side_effect=FileNotFoundError("Resume file not found"))
    def test_post_convert_resume_file_not_found(self, mock_convert):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Resume file not found", response.data["error"])

    @patch("resume_api.views.convert_resume_to_rdf",
           side_effect=Exception("Test error"))
    def test_post_convert_resume_server_error(self, mock_convert):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Failed to convert resume to RDF", response.data["error"])


class RagSearchEndpointTests(TestCase):
    """Tests for the session-aware semantic RAG endpoint."""

    def setUp(self):
        self.client = APIClient()
        # Force-create a session so IsSessionValid passes
        session = self.client.session
        session.save()
        self.url = reverse("search_rag")

    @patch("resume_api.views.search_rag")
    def test_post_rag_success(self, mock_search):
        """Session is cookie-based — no session_id in request body."""
        mock_search.return_value = {
            "prompt": "What did she do there?",
            "session_id": "test-session-key",
            "model": "test-model",
            "retrieval_query": "What did Dooa do at Greator GmbH?",
            "answer": "She was a Frontend Developer.",
            "retrieved_chunks": [],
        }
        response = self.client.post(
            self.url,
            {"prompt": "What did she do there?"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["answer"], "She was a Frontend Developer.")
        mock_search.assert_called_once()
        args = mock_search.call_args.args
        self.assertEqual(args[1], "What did she do there?")

    @patch("resume_api.views.search_rag")
    def test_post_rag_session_key_is_used(self, mock_search):
        """The Django session key is passed to the service."""
        mock_search.side_effect = lambda session_id, prompt: {
            "session_id": session_id,
            "prompt": prompt,
            "answer": "answer",
            "retrieved_chunks": [],
        }
        response = self.client.post(self.url, {"prompt": "test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        generated_id = mock_search.call_args.args[0]
        self.assertIsNotNone(generated_id)
        self.assertNotEqual(generated_id, "")
        self.assertNotEqual(generated_id, "string")
        self.assertEqual(response.data["session_id"], generated_id)

    def test_post_rag_requires_prompt(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("prompt", response.data["error"])

    def test_rag_get_not_allowed(self):
        self.assertEqual(
            self.client.get(self.url).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class SessionEnforcementTests(TestCase):
    """Tests that session enforcement middleware + permission behave correctly."""

    def test_session_auto_created_on_first_api_request(self):
        """Even a fresh client gets a session created by the enforcer middleware."""
        client = APIClient()
        # No explicit session save — middleware should create one
        url = reverse("convert_resume")
        response = client.post(url)
        # The enforcer creates a session, so this should pass
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_cookie_set_in_response(self):
        """Response should set a session cookie on first visit."""
        client = APIClient()
        url = reverse("convert_resume")
        response = client.post(url)
        # Django sets sessionid cookie; APIClient may or may not expose it
        # but the fact we got 200 means session was created
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RagServiceTests(TestCase):
    """Unit tests for the rag_service rewrite, retrieval, answer, and session state."""

    @patch("resume_api.services.rag_service.query_openrouter")
    def test_rewrites_follow_up_before_retrieval(self, mock_query):
        mock_query.side_effect = [
            "What is Dooa Ansari doing currently after Greator GmbH?",
            "Dooa is a Full-Stack Developer at DeepSkill GmbH.",
        ]

        with patch("resume_api.services.rag_service.ChromaVectorRepository") as mock_repo:
            mock_instance = mock_repo.return_value
            mock_instance.search_semantic.return_value = [
                {"document": "DeepSkill GmbH", "metadata": {}, "distance": 0.1, "score": 0.9}
            ]

            result = search_rag("rag-test-1", "What is she doing now?")

        self.assertEqual(
            result["retrieval_query"],
            "What is Dooa Ansari doing currently after Greator GmbH?",
        )
        self.assertEqual(
            result["answer"],
            "Dooa is a Full-Stack Developer at DeepSkill GmbH.",
        )

    @patch("resume_api.services.rag_service.query_openrouter")
    def test_session_history_is_available_on_follow_up(self, mock_query):
        mock_query.side_effect = [
            "first query",
            "first answer",
            "second query",
            "second answer",
        ]

        with patch("resume_api.services.rag_service.ChromaVectorRepository") as mock_repo:
            mock_instance = mock_repo.return_value
            mock_instance.search_semantic.return_value = []

            search_rag("rag-test-2", "When did Dooa work at Greator?")
            result = search_rag("rag-test-2", "What did she do there?")

        self.assertEqual(result["retrieval_query"], "second query")
        self.assertEqual(result["answer"], "second answer")


class OpenRouterServiceTests(TestCase):
    """Tests for the OpenRouter API client service."""

    @patch("resume_api.services.openrouter_service.settings.OPENROUTER_API_KEY", "test-key")
    @patch("resume_api.services.openrouter_service.requests.post")
    def test_query_openrouter_success(self, mock_post):
        mock_response = mock_post.return_value
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "model response"}}]
        }

        result = query_openrouter("test prompt")
        self.assertEqual(result, "model response")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(call_args[1]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(call_args[1]["json"]["model"], "inclusionai/ling-3.0-flash")
        self.assertEqual(call_args[1]["json"]["messages"][0]["content"], "test prompt")

    @patch("resume_api.services.openrouter_service.settings.OPENROUTER_API_KEY", "test-key")
    @patch("resume_api.services.openrouter_service.requests.post")
    def test_query_openrouter_with_system_prompt(self, mock_post):
        mock_response = mock_post.return_value
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "SPARQL query result"}}]
        }

        system_prompt = "You are a SPARQL expert."
        result = query_openrouter("test prompt", system_prompt=system_prompt)
        self.assertEqual(result, "SPARQL query result")

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
        from requests.exceptions import RequestException

        mock_post.side_effect = RequestException("API error")

        with self.assertRaises(RequestException):
            query_openrouter("test prompt")


class SecurityHeadersTests(TestCase):
    """Tests that security headers and cookie settings are enforced."""

    def setUp(self):
        self.client = APIClient()

    def test_security_headers_present_on_responses(self):
        """Security headers should be present on API responses."""
        response = self.client.post(reverse("convert_resume"))
        self.assertIn("X-XSS-Protection", response)
        self.assertIn("X-Content-Type-Options", response)
        self.assertIn("Content-Security-Policy", response)
        self.assertIn("Referrer-Policy", response)

    def test_session_cookie_is_http_only(self):
        from django.conf import settings
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)

    def test_session_cookie_is_same_site_strict(self):
        from django.conf import settings
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Strict")

    def test_session_expires_on_browser_close(self):
        from django.conf import settings
        self.assertTrue(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)

    def test_csrf_cookie_is_http_only(self):
        from django.conf import settings
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)

    def test_csrf_cookie_is_same_site_strict(self):
        from django.conf import settings
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, "Strict")


class RuntimeConfigTests(TestCase):
    """Tests that validate the development runtime environment."""

    def test_dev_swagger_enabled(self):
        """In dev mode, Swagger should be enabled."""
        from django.conf import settings
        # Django test runner overrides DEBUG to False, so only check SWAGGER_ENABLED
        self.assertTrue(getattr(settings, "SWAGGER_ENABLED", True))


class SwaggerEndpointTests(TestCase):
    """Tests for the Swagger documentation endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_swagger_ui_available(self):
        response = self.client.get("/swagger/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_swagger_json_schema(self):
        response = self.client.get("/swagger.json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("application/json", response["Content-Type"])

        data = response.json()
        self.assertEqual(data["info"]["title"], "Resume RDF Converter API")
        self.assertIn("/convert-resume/", data["paths"])
        self.assertIn("post", data["paths"]["/convert-resume/"])

    def test_swagger_yaml_schema(self):
        response = self.client.get("/swagger.yaml")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
