from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.admin_login_view, name='admin_login'),
    path('panel/', views.admin_dashboard_view, name='admin_panel'),
    path('panel/users/', views.user_list_view, name='admin_user_list'),
    path('panel/users/create/', views.create_user_view, name='admin_create_user'),
    path('panel/users/<int:user_id>/', views.user_detail_view, name='admin_user_detail'),
    path('panel/users/<int:user_id>/delete/', views.delete_user_view, name='admin_delete_user'),
    path('panel/manage-funds/', views.manage_funds_view, name='admin_manage_funds'),
]
