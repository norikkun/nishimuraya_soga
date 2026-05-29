from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from ..forms import ContactForm
from ..models import ContactInquiry


class ContactView(FormView):
    template_name = "nishimuraya/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("contact_thanks")

    def form_valid(self, form):
        ContactInquiry.objects.create(**form.cleaned_data)
        return super().form_valid(form)
