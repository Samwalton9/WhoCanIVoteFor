from django import forms
from django.contrib import admin

from .models import Husting


class HustingAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "starts", "ends", "url"]
    list_filter = ("starts", "status")
    search_fields = ("post_election__ballot_paper_id",)
    autocomplete_fields = ["post_election"]
    date_hierarchy = "starts"

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ["title", "url", "location", "postevent_url"]:
            kwargs["widget"] = forms.Textarea
        if db_field.name == "status":
            kwargs["widget"] = forms.RadioSelect
        return super().formfield_for_dbfield(db_field, request, **kwargs)


admin.site.register(Husting, HustingAdmin)
