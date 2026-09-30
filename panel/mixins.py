from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied


class StaffRequiredMixin(AccessMixin):
    """Solo usuarios staff. Anónimo -> login del panel; logueado sin staff -> 403."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
