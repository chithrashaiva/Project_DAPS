from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('goals/create/', views.create_goal, name='create_goal'),
    path('goals/', views.goal_list, name='goal_list'),
    path('goals/<int:goal_id>/', views.update_goal, name='goal_detail'),
    path('partners/find/', views.find_partners, name='find_partners'),
    path('partners/request/<int:user_id>/', views.send_partner_request, name='send_partner_request'),
    path('partners/requests/', views.partner_requests, name='partner_requests'),
    path('partners/requests/<int:request_id>/<str:action>/', views.handle_partner_request, name='handle_partner_request'),
    path('partners/progress/', views.partner_progress, name='partner_progress'),
]
