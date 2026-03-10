from django.urls import path
from . import views

urlpatterns = [
    path('panel/', views.admin_dashboard_view, name='admin_panel'),
    path('panel/users/', views.user_list_view, name='admin_user_list'),
    path('panel/users/<int:user_id>/', views.user_detail_view, name='admin_user_detail'),
]
