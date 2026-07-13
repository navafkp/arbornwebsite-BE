from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path


class DuplicateAdminMixin:
    """Adds a 'Duplicate' button to the change page. Subclasses must implement duplicate_object()."""

    change_form_template = "admin/common/duplicate_change_form.html"
    duplicate_success_message = "Duplicated successfully."

    def duplicate_object(self, obj):
        raise NotImplementedError("Subclasses must implement duplicate_object()")

    def get_urls(self):
        opts = self.model._meta
        custom_urls = [
            path(
                "<path:object_id>/duplicate/",
                self.admin_site.admin_view(self.duplicate_view),
                name=f"{opts.app_label}_{opts.model_name}_duplicate",
            ),
        ]
        return custom_urls + super().get_urls()

    def duplicate_view(self, request, object_id):
        opts = self.model._meta
        obj = self.get_object(request, object_id)
        if obj is None:
            messages.error(request, f"{opts.verbose_name} not found.")
            return redirect(f"admin:{opts.app_label}_{opts.model_name}_changelist")

        new_obj = self.duplicate_object(obj)
        messages.success(request, self.duplicate_success_message)
        return redirect(f"admin:{opts.app_label}_{opts.model_name}_change", new_obj.pk)
