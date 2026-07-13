from django.db import models


# class SingletonModel(models.Model):
#     """
#     Base for content that only ever has one row (Home hero, Select Size
#     copy) — editable from Django Admin without a redeploy.
#     """

#     class Meta:
#         abstract = True

#     def save(self, *args, **kwargs):
#         self.pk = 1
#         super().save(*args, **kwargs)

#     def delete(self, *args, **kwargs):
#         pass  # singleton rows are never deleted, only edited

#     @classmethod
#     def load(cls):
#         obj, _ = cls.objects.get_or_create(pk=1)
#         return obj





# class SelectSizeContent(SingletonModel):
#     heading = models.CharField(max_length=200, default="What's your bust size?")
#     subheading = models.CharField(
#         max_length=255, default="Choose your bust size for the best fit"
#     )
#     illustration_image = models.ImageField(upload_to="content/", blank=True, null=True)
#     size_tip_text = models.CharField(
#         max_length=255, default="If your lower body is heavier, choose one size bigger."
#     )
#     whatsapp_help_text = models.CharField(
#         max_length=255,
#         default="Not sure about your size or buying for someone else?",
#     )
#     important_note = models.TextField(
#         default="This is a loose-fit model. Sizes are for bust/bra size reference "
#         "only, not exact dress measurements."
#     )

#     def __str__(self):
#         return "Select Size page content"
