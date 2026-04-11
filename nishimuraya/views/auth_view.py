from django.urls import reverse
from django.views.generic.base import RedirectView
from django.contrib.auth.views import LoginView, LogoutView


class StaffLoginView(LoginView):
    template_name = "nishimuraya/staff_login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        redirect_url = self.get_redirect_url()
        if self.request.user.is_staff:
            return redirect_url or reverse("news_drafts")
        return reverse("home")


class StaffLogoutView(LogoutView):
    next_page = "home"


class StaffLoginRedirectView(RedirectView):
    permanent = False
    pattern_name = "staff_login"
