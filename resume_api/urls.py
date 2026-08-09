from django.urls import path

from . import views

urlpatterns = [
    path("convert-resume/", views.convert_resume, name="convert_resume"),
    path("search-knowledge-graph/", views.search_knowledge_graph, name="search_knowledge_graph"),
    path("search-knowledge-graph-simple/", views.search_knowledge_graph_simple, name="search_knowledge_graph_simple"),
    path("search-rag/", views.search_rag, name="search_rag"),
]
