from rest_framework import serializers


class RagSearchSerializer(serializers.Serializer):
    """Request body for the semantic RAG search endpoint.

    Session is cookie-based (HttpOnly, SameSite=Strict).
    The client does not need to send any session identifier.
    """

    prompt = serializers.CharField(
        required=True,
        help_text="Question to ask about the resume",
    )
