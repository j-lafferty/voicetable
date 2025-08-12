from django.shortcuts import render
from django.http import HttpResponse

def health(request):
    return HttpResponse("OK: voicetable is alive")

# Create your views here.
