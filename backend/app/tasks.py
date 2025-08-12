import os
import pathlib
from datetime import datetime, timezone

import pandas as pd
from celery import shared_task
from django.db import transaction

from .models import Project, DataRow, AudioIndex


@shared_task
def ping():
    return "pong"


@shared_task
def import_excel(project_id: int):
    """Read Excel, auto-detect headers, store rows as JSON."""
    project = Project.objects.get(id=project_id)
    xls = project.excel_source_path
    if not xls or not os.path.exists(xls):
        return {"status": "missing_excel", "path": xls}

    df = pd.read_excel(xls, dtype=str).fillna("")
    headers = list(df.columns)

    # Save detected header order for UI
    Project.objects.filter(id=project_id).update(column_headers=headers)

    filename_col = project.filename_column or (headers[0] if headers else "")
    now = datetime.now(timezone.utc)

    with transaction.atomic():
        # Simple replace strategy for now
        DataRow.objects.filter(project=project).delete()

        bulk = []
        for i, row in df.iterrows():
            row_id = str(row.get("id", "")) or str(i + 1)
            data = {h: str(row[h]) for h in headers}
            bulk.append(
                DataRow(
                    project=project,
                    row_id=row_id,
                    data=data,
                    audio={},  # will be filled by index_audio
                    indexed_at=now,
                )
            )
        if bulk:
            DataRow.objects.bulk_create(bulk, batch_size=2000)

    # After import, link audio
    index_audio.delay(project_id)
    return {"status": "ok", "rows": len(df), "filename_column": filename_col}


@shared_task
def index_audio(project_id: int):
    """Scan audio dirs, refresh AudioIndex, and attach URLs to matching rows."""
    project = Project.objects.get(id=project_id)
    roots = project.audio_roots or {}
    AudioIndex.objects.filter(project=project).delete()

    found = 0
    for lang, root in roots.items():
        if not root or not os.path.isdir(root):
            continue
        for p in pathlib.Path(root).glob("**/*"):
            if not p.is_file():
                continue
            stem = p.stem
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            AudioIndex.objects.create(
                project=project,
                language=lang,
                filename_stem=stem,
                file_path=str(p),
                mtime=mtime,
            )
            found += 1

    filename_col = project.filename_column or (
        project.column_headers[0] if project.column_headers else ""
    )
    if not filename_col:
        return {"status": "ok", "audio_files_indexed": found, "note": "no filename_col"}

    # Build (lang, stem) -> URL map. Nginx serves /media/audio/<lang>/ -> /srv/audio/<lang>/
    media_urls = {}
    for ai in AudioIndex.objects.filter(project=project).iterator():
        lang = ai.language
        filename = os.path.basename(ai.file_path)  # served name
        media_urls.setdefault(lang, {})
        media_urls[lang][ai.filename_stem] = f"/media/audio/{lang}/{filename}"

    updates = []
    for r in DataRow.objects.filter(project=project).iterator():
        key = str(r.data.get(filename_col, "")).strip()
        if not key:
            continue
        audio_map = {}
        for lang, table in media_urls.items():
            url = table.get(key)
            if url:
                audio_map[lang] = url
        if audio_map:
            r.audio = audio_map
            updates.append(r)

    if updates:
        DataRow.objects.bulk_update(updates, ["audio"], batch_size=2000)

    return {"status": "ok", "audio_files_indexed": found}
