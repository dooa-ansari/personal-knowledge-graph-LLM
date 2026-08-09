"""Dependency injection container for wiring up the Clean Architecture layers."""

from resume_api.adapters.llm_provider import OpenRouterLLMProvider
from resume_api.adapters.vector_repository import ChromaVectorRepository
from resume_api.adapters.rdf_repository import RdfConverterRepository
from resume_api.ports.repositories import LLMProvider, VectorRepository, RDFRepository
from resume_api.use_cases.convert_resume import ConvertResumeUseCase
from resume_api.use_cases.search_rag import SearchRagUseCase


class Container:
    """Simple dependency injection container.

    Provides singleton instances of all adapters and use cases.
    To swap implementations (e.g., ChromaDB → Pinecone), replace the
    adapter class wired here without changing any use case or view code.
    """

    def __init__(self):
        self._llm_provider: LLMProvider | None = None
        self._vector_repository: VectorRepository | None = None
        self._rdf_repository: RDFRepository | None = None
        self._convert_resume_use_case: ConvertResumeUseCase | None = None
        self._search_rag_use_case: SearchRagUseCase | None = None

    @property
    def llm_provider(self) -> LLMProvider:
        if self._llm_provider is None:
            self._llm_provider = OpenRouterLLMProvider()
        return self._llm_provider

    @property
    def vector_repository(self) -> VectorRepository:
        if self._vector_repository is None:
            self._vector_repository = ChromaVectorRepository()
        return self._vector_repository

    @property
    def rdf_repository(self) -> RDFRepository:
        if self._rdf_repository is None:
            self._rdf_repository = RdfConverterRepository()
        return self._rdf_repository

    @property
    def convert_resume_use_case(self) -> ConvertResumeUseCase:
        if self._convert_resume_use_case is None:
            self._convert_resume_use_case = ConvertResumeUseCase(
                rdf_repository=self.rdf_repository,
            )
        return self._convert_resume_use_case

    @property
    def search_rag_use_case(self) -> SearchRagUseCase:
        if self._search_rag_use_case is None:
            self._search_rag_use_case = SearchRagUseCase(
                llm_provider=self.llm_provider,
                vector_repository=self.vector_repository,
            )
        return self._search_rag_use_case


# Global container instance for the application
container = Container()