"""Telegram views."""

import json

from django.contrib.auth.decorators import login_not_required  # type: ignore[reportAttributeAccessIssue]
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.telegram import models
from apps.telegram.bot.core import Bot


@csrf_exempt
@login_not_required
def webhook(request: HttpRequest) -> JsonResponse:
    """Handle incoming messages."""
    if not Bot.validate_token(request.headers.get("X-Telegram-Bot-Api-Secret-Token")):
        return JsonResponse({"status": "error", "message": "Invalid token."}, status=403)
    update = json.loads(request.body)
    message = models.Message(raw_message=update)
    status = "ok"
    try:
        Bot.handle(update)
    except Exception as exc:
        message.error = str(exc)
        status = "error"
    finally:
        message.save()
    return JsonResponse({"status": status, "message": "Message received."})
