from django.db import models
from django.contrib.postgres.indexes import GinIndex

class Project(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    excel_source_path = models.CharField(max_length=1024, blank=True, default="")
    # e.g. {"en": "/audio/en", "ja": "/audio/ja"}
    audio_roots = models.JSONField(default=dict, blank=True)
    # column in Excel used to match audio filenames (stem)
    filename_column = models.CharField(max_length=200, blank=True, default="")
    # persist detected header order so UI can render in a stable order
    column_headers = models.JSONField(default=list, blank=True)

    users = models.ManyToManyField("auth.User", related_name="projects", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class DataRow(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="rows")
    # stable identifier from Excel (can be the row number or a column value)
    row_id = models.CharField(max_length=255)
    # entire row as JSON (auto-detected columns → values)
    data = models.JSONField(default=dict)
    # {"en": "/media/audio/en/file.wav", "ja": "/media/audio/ja/file.wav"}
    audio = models.JSONField(default=dict, blank=True)

    indexed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "row_id"]),
            GinIndex(fields=["data"]),  # JSONB GIN for keyword search
        ]


class AudioIndex(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="audio_files")
    language = models.CharField(max_length=16)        # e.g. "en", "ja"
    filename_stem = models.CharField(max_length=255)  # stem used for matching
    file_path = models.CharField(max_length=1024)     # absolute path inside container
    mtime = models.DateTimeField()                    # last modified time

    class Meta:
        unique_together = ("project", "language", "filename_stem")
        indexes = [
            models.Index(fields=["project", "language", "filename_stem"]),
        ]

    def __str__(self):
        return f"{self.project.slug}:{self.language}:{self.filename_stem}"
