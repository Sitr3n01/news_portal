from django.urls import path

from . import views

app_name = 'hiring'

urlpatterns = [
    path('', views.job_list, name='list'),
    path('application/<int:application_id>/resume/', views.download_resume, name='download_resume'),
    path('<slug:slug>/', views.job_detail, name='job_detail'),
]
