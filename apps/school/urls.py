from django.urls import path

from . import views

app_name = 'school'

urlpatterns = [
    path('', views.home, name='home'),
    path('team/', views.team_list, name='team_list'),
    path('sobre/', views.about, name='about'),
    path('privacidade/', views.privacy, name='privacy'),
    path('<slug:slug>/', views.page_detail, name='page_detail'),
]
