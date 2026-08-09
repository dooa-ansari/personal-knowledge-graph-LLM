from django.urls import path

from . import views

urlpatterns = [
    path("convert-resume/", views.convert_resume, name="convert_resume"),
    path("search-rag/", views.search_rag, name="search_rag"),
]
