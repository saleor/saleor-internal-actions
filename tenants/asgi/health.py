from django.http import JsonResponse
from django.db import connection


def _check_db_connection():
    try:
        connection.cursor().execute("select 1")
        return True
    except Exception as exc:
        return exc.args


def health_check(request):
    body = {"api": True, "db": _check_db_connection()}

    if all([v is True for v in body.values()]):
        return JsonResponse(body, status=200)
    else:
        return JsonResponse(body, status=500)
