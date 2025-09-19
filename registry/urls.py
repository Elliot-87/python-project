from django.urls import path
from . import views

urlpatterns = [
    path('', views.registry_list, name='registry_list'),
    path('add/', views.registry_create, name='registry_create'),
    path('edit/<int:pk>/', views.registry_update, name='registry_update'),
    path('delete/<int:pk>/', views.registry_delete, name='registry_delete'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard-data/', views.dashboard_data, name='dashboard_data'),
    path('admin/export-pdf/', views.export_pdf, name='export_pdf'),

]
