from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt
@require_http_methods(["GET"])
def ping(request):
    """Simple ping endpoint to test if server is running."""
    return JsonResponse({"message": "Bang"})