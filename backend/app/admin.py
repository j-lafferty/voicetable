from django.contrib import admin
from .models import Project, DataRow, AudioIndex

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "updated_at")
    search_fields = ("name", "slug")
    filter_horizontal = ("users",)

@admin.register(DataRow)
class DataRowAdmin(admin.ModelAdmin):
    list_display = ("project", "row_id", "updated_at")
    search_fields = ("row_id",)
    list_filter = ("project",)

@admin.register(AudioIndex)
class AudioIndexAdmin(admin.ModelAdmin):
    list_display = ("project", "language", "filename_stem")
    search_fields = ("filename_stem", "language")
    list_filter = ("project", "language")
