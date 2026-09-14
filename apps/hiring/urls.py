from django.urls import path

from . import views

app_name = 'hiring'

# As vagas saíram do site público em 14/09/2026. Resta o download protegido de currículos, usado pelo admin.
urlpatterns = [
    path('application/<int:application_id>/resume/', views.download_resume, name='download_resume'),
]
