from django.urls import path

from . import views
from .feeds import CategoryFeed, LatestArticlesFeed

app_name = 'news'

urlpatterns = [
    path('', views.article_list, name='list'),
    path('search/', views.article_search, name='search'),
    path('feed/', LatestArticlesFeed(), name='feed'),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('category/<slug:slug>/feed/', CategoryFeed(), name='category_feed'),
    path('tag/<slug:slug>/', views.tag_detail, name='tag_detail'),
    path('author/<str:username>/', views.author_detail, name='author_detail'),
    path('archive/<int:year>/', views.article_archive, name='archive_year'),
    path('archive/<int:year>/<int:month>/', views.article_archive, name='archive_month'),
    path('htmx/articles/', views.article_list_page, name='article_list_page'),

    # User Account & Actions
    path('account/', views.user_dashboard, name='user_dashboard'),
    path('toggle-bookmark/<int:article_id>/', views.toggle_bookmark, name='toggle_bookmark'),
    path('toggle-like/<int:article_id>/', views.toggle_like, name='toggle_like'),
    path('comment/<int:article_id>/', views.add_comment, name='add_comment'),
    path('delete-comment/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('newsletter/preview/<int:article_id>/', views.newsletter_preview, name='newsletter_preview'),

    # SLUG CATCH-ALL — deve ser SEMPRE a ultima rota
    path('<slug:slug>/', views.article_detail, name='article_detail'),
]
