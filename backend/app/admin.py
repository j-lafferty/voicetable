from django.contrib import admin, messages
from .models import Project, DataRow, AudioIndex
from .tasks import import_excel, index_audio

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "updated_at")
    search_fields = ("name", "slug")
    filter_horizontal = ("users",)
    actions = ["import_excel_and_index_audio"]

    def import_excel_and_index_audio(self, request, queryset):
        count = 0
        for p in queryset:
            import_excel.delay(p.id)
            index_audio.delay(p.id)
            count += 1
        self.message_user(request, f"Queued import + index for {count} project(s).", messages.INFO)
    import_excel_and_index_audio.short_description = "Import Excel + Index Audio"
