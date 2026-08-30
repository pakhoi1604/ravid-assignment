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


class ChatQuerySerializer(serializers.Serializer):
    query = StrictUTF8CharField(required=True, allow_blank=False, max_length=2_000)


class ChatAnswerSerializer(serializers.Serializer):
    answer = serializers.CharField()


class ChatErrorSerializer(serializers.Serializer):
    error = serializers.CharField()


def first_error(serializer: serializers.Serializer) -> str:
    errors = serializer.errors
    query_errors = errors.get("query")
    if isinstance(query_errors, list) and query_errors:
        return str(query_errors[0])
    return "Invalid chat query request."
