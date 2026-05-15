from django.urls import path

from . import views

app_name = 'hiring'

urlpatterns = [
    path('', views.job_list, name='list'),
    path('<slug:slug>/', views.job_detail, name='job_detail'),
]
