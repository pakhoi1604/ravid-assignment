from rest_framework import serializers


class StrictUTF8CharField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        value = super().to_internal_value(data)
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise serializers.ValidationError("Query must be valid UTF-8 text.") from exc
        return value


class StrictBooleanField(serializers.BooleanField):
    def to_internal_value(self, data):
        if type(data) is not bool:
            self.fail("invalid")
        return super().to_internal_value(data)


class ChatQuerySerializer(serializers.Serializer):
    query = StrictUTF8CharField(required=True, allow_blank=False, max_length=2_000)
    use_hyde = StrictBooleanField(required=False, default=False)


class RetrievalMetadataSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["standard", "hyde"])
    hypothetical_passage = serializers.CharField(allow_null=True)
    fallback_reason = serializers.ChoiceField(choices=["hyde_unavailable"], allow_null=True)
    retrieved_chunks_count = serializers.IntegerField(min_value=0)
    retrieved_chunks = serializers.ListField(child=serializers.CharField())


class ChatAnswerSerializer(serializers.Serializer):
    answer = serializers.CharField()
    retrieval_metadata = RetrievalMetadataSerializer()


class ChatErrorSerializer(serializers.Serializer):
    error = serializers.CharField()


def first_error(serializer: serializers.Serializer) -> str:
    errors = serializer.errors
    query_errors = errors.get("query")
    if isinstance(query_errors, list) and query_errors:
        return str(query_errors[0])
    use_hyde_errors = errors.get("use_hyde")
    if isinstance(use_hyde_errors, list) and use_hyde_errors:
        return str(use_hyde_errors[0])
    return "Invalid chat query request."
