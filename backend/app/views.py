import json
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage
from django.db.models.expressions import RawSQL
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from .models import Project, DataRow

def health(request):
    return HttpResponse("OK: voicetable is alive")

@login_required
def dashboard(request):
    projects = Project.objects.filter(users=request.user).order_by("name")
    return render(request, "app/dashboard.html", {"projects": projects})

@login_required
def project_view(request, slug):
    project = get_object_or_404(Project, slug=slug, users=request.user)
    return render(request, "app/project.html", {"project": project})

@login_required
def api_project_rows(request, slug):
    project = get_object_or_404(Project, slug=slug, users=request.user)

    # Query params
    page = int(request.GET.get("page", 1))
    page_size = min(int(request.GET.get("page_size", 100)), 1000)  # cap page size
    search = (request.GET.get("search") or "").strip()

    qs = DataRow.objects.filter(project=project).only("id", "row_id", "data", "audio")

    # Simple search: WHERE data::text ILIKE %search%
    if search:
        qs = qs.extra(  # safe enough for param binding here
            where=["data::text ILIKE %s"], params=[f"%{search}%"]
        )

    qs = qs.order_by("row_id")  # stable order

    paginator = Paginator(qs, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages or 1)

    # Prepare rows
    rows = []
    for r in page_obj.object_list.iterator():
        rows.append({
            "row_id": r.row_id,
            "data": r.data,    # full JSON row (columns are auto-detected)
            "audio": r.audio,  # {"en": "/media/audio/en/...", "ja": "..."}
        })

    return JsonResponse({
        "page": page_obj.number,
        "pages": paginator.num_pages,
        "total": paginator.count,
        "page_size": page_size,
        "rows": rows,
        "columns": project.column_headers,
    })
