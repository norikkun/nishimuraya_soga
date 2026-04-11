from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from ..forms import ContactForm


class ContactView(FormView):
    template_name = "nishimuraya/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("contact_thanks")

    def build_message_body(self, cleaned_data):
        phone = cleaned_data["phone"] or "未入力"
        return "\n".join(
            [
                "Nishimurayaサイトからお問い合わせが届きました。",
                "",
                f"お名前: {cleaned_data['name']}",
                f"メールアドレス: {cleaned_data['email']}",
                f"電話番号: {phone}",
                "",
                "お問い合わせ内容:",
                cleaned_data["message"],
            ]
        )

    def send_contact_email(self, cleaned_data):
        email = EmailMessage(
            subject=f"[Nishimuraya] お問い合わせ / {cleaned_data['name']}",
            body=self.build_message_body(cleaned_data),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.CONTACT_RECIPIENT_EMAIL],
            reply_to=[cleaned_data["email"]],
        )
        email.send(fail_silently=False)

    def form_valid(self, form):
        self.send_contact_email(form.cleaned_data)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["uses_console_email_backend"] = (
            settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend"
        )
        return context
