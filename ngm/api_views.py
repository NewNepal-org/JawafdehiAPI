from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from ngm.serializers import NGMQuerySerializer
from ngm.services import execute_select_query, validate_query


class NGMQueryRateThrottle(SimpleRateThrottle):
    scope = "ngm_token"
    rate = "60/hour"

    def get_cache_key(self, request, view):
        token = getattr(request, "auth", None)
        token_key = getattr(token, "key", None)
        if not token_key:
            return None

        return self.cache_format % {"scope": self.scope, "ident": token_key}


@extend_schema(
    summary="Run read-only query against NGM judicial database",
    description="""
    Executes validated SELECT queries against NGM judicial tables.

    Security controls:
    - Requires DRF token authentication
    - Rate limited to 60 requests/hour per token
    - Only SELECT queries are allowed
    - Only allowlisted judicial tables may be referenced
    - Server enforces statement timeout and row cap
    """,
    request=NGMQuerySerializer,
)
class NGMJudicialQueryView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [NGMQueryRateThrottle]

    def post(self, request):
        serializer = NGMQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data["query"]
        timeout = serializer.validated_data["timeout"]

        is_valid, error_msg = validate_query(query)
        if not is_valid:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "query_time_ms": 0,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = execute_select_query(query, timeout)
        except ValueError as exc:
            message = str(exc)
            status_code = (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if "not configured" in message.lower()
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": message,
                    "query_time_ms": 0,
                },
                status=status_code,
            )

        return Response(
            {
                "success": True,
                "data": {
                    "columns": result["columns"],
                    "rows": result["rows"],
                    "row_count": result["row_count"],
                    "max_rows": result["max_rows"],
                },
                "error": None,
                "query_time_ms": result["query_time_ms"],
            },
            status=status.HTTP_200_OK,
        )
