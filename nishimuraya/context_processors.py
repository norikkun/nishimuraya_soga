from django.db import OperationalError, ProgrammingError

from .models import ContactInquiry


def contact_inquiry_status(request):
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated and user.is_staff):
        return {}

    try:
        latest_inquiry = ContactInquiry.objects.order_by("-id").first()
        return {
            "pending_contact_inquiry_count": ContactInquiry.objects.filter(is_handled=False).count(),
            "contact_inquiry_total_count": ContactInquiry.objects.count(),
            "latest_contact_inquiry_id": latest_inquiry.pk if latest_inquiry else 0,
        }
    except (OperationalError, ProgrammingError):
        return {}
