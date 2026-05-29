from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView

from ..models import ContactInquiry


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy("staff_login")

    def test_func(self):
        return self.request.user.is_staff


class PaginationWindowMixin:
    page_window = 3

    def get_visible_page_numbers(self, page_obj):
        start_page = max(1, page_obj.number - self.page_window)
        end_page = min(page_obj.paginator.num_pages, page_obj.number + self.page_window)
        return list(range(start_page, end_page + 1))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context.get("page_obj")
        visible_page_numbers = (
            self.get_visible_page_numbers(page_obj) if page_obj and context.get("is_paginated") else []
        )
        if visible_page_numbers:
            first_visible_page = visible_page_numbers[0]
            last_visible_page = visible_page_numbers[-1]
            context["show_first_page_link"] = first_visible_page > 1
            context["show_leading_ellipsis"] = first_visible_page > 2
            context["show_last_page_link"] = last_visible_page < page_obj.paginator.num_pages
            context["show_trailing_ellipsis"] = last_visible_page < page_obj.paginator.num_pages - 1
        else:
            context["show_first_page_link"] = False
            context["show_leading_ellipsis"] = False
            context["show_last_page_link"] = False
            context["show_trailing_ellipsis"] = False
        context["visible_page_numbers"] = visible_page_numbers
        return context


class ContactInquiryListView(StaffRequiredMixin, PaginationWindowMixin, ListView):
    model = ContactInquiry
    template_name = "nishimuraya/contact_inquiry_list.html"
    context_object_name = "inquiries"
    paginate_by = 5

    def get_status_filter(self):
        status = self.request.GET.get("status", "pending")
        return status if status in {"all", "pending", "handled"} else "pending"

    def get_queryset(self):
        queryset = ContactInquiry.objects.all()
        status = self.get_status_filter()
        if status == "pending":
            return queryset.filter(is_handled=False)
        if status == "handled":
            return queryset.filter(is_handled=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filter"] = self.get_status_filter()
        context["status_query"] = f"status={context['status_filter']}&"
        context["pending_count"] = ContactInquiry.objects.filter(is_handled=False).count()
        context["handled_count"] = ContactInquiry.objects.filter(is_handled=True).count()
        context["total_count"] = ContactInquiry.objects.count()
        return context


class ContactInquiryDetailView(StaffRequiredMixin, DetailView):
    model = ContactInquiry
    template_name = "nishimuraya/contact_inquiry_detail.html"
    context_object_name = "inquiry"


class ContactInquiryToggleHandledView(StaffRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        inquiry = get_object_or_404(ContactInquiry, pk=pk)
        inquiry.set_handled(not inquiry.is_handled)
        messages.success(request, f"問い合わせを{inquiry.status_label}に変更しました。")
        return redirect(inquiry.get_absolute_url())


class ContactInquiryStatusView(StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        latest_inquiry = ContactInquiry.objects.order_by("-id").first()
        return JsonResponse(
            {
                "pending_count": ContactInquiry.objects.filter(is_handled=False).count(),
                "total_count": ContactInquiry.objects.count(),
                "latest_id": latest_inquiry.pk if latest_inquiry else 0,
            }
        )
