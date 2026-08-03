from rest_framework import serializers


class PromptSerializer(serializers.Serializer):
    """Request body for the search-knowledge-graph endpoint."""

    prompt = serializers.CharField(
        help_text="User prompt to search the knowledge graph",
        required=True,
    )