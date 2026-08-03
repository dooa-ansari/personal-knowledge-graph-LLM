from django.http import HttpResponse


def home(request):
    return HttpResponse("<h1>Welcome to Django 5.2</h1><p>Your basic Django project is running successfully.</p>")