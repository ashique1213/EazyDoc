import json
import logging
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.subscriptions.services.billing import SubscriptionBillingService

logger = logging.getLogger("apps.subscriptions")


@method_decorator(csrf_exempt, name="dispatch")
class RazorpaySubscriptionWebhookView(View):
    """
    HTTP POST Webhook ingestion endpoint for Razorpay subscription and order callbacks.
    Validates HMAC signature and idempotently reconciles payment status.
    """

    def post(self, request, *args, **kwargs):
        signature = request.headers.get("X-Razorpay-Signature", "")
        raw_body = request.body

        if not SubscriptionBillingService.verify_webhook_signature(raw_body, signature):
            logger.warning("Rejected Razorpay webhook with invalid signature.")
            return JsonResponse({"error": "Invalid signature"}, status=400)

        try:
            event_data = json.loads(raw_body.decode("utf-8"))
        except Exception as exc:
            logger.error("Failed to parse webhook JSON payload: %s", exc)
            return JsonResponse({"error": "Malformed JSON payload"}, status=400)

        success, message = SubscriptionBillingService.process_webhook_event(event_data)
        logger.info("Processed subscription webhook event %s: %s", event_data.get("event"), message)

        return JsonResponse({"status": "received", "detail": message}, status=200)
