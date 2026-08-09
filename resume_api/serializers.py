from rest_framework import serializers


class RagSearchSerializer(serializers.Serializer):
    """Request body for the semantic RAG search endpoint."""

    prompt = serializers.CharField(required=True, help_text="Question to ask about the resume")
    session_id = serializers.CharField(required=False, allow_blank=True)