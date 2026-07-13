# from django.contrib import admin

# from .models import HomeContent, SelectSizeContent


# class SingletonAdmin(admin.ModelAdmin):
#     """Always edit the one row — no add/delete, just change."""

#     def has_add_permission(self, request):
#         return not self.model.objects.exists()

#     def has_delete_permission(self, request, obj=None):
#         return False

#     def changelist_view(self, request, extra_context=None):
#         obj = self.model.load()
#         from django.shortcuts import redirect

#         return redirect("admin:%s_%s_change" % (self.model._meta.app_label, self.model._meta.model_name), obj.pk)


# @admin.register(HomeContent)
# class HomeContentAdmin(SingletonAdmin):
#     pass


# @admin.register(SelectSizeContent)
# class SelectSizeContentAdmin(SingletonAdmin):
#     pass
