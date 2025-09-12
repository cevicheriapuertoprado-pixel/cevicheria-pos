from django.contrib import admin
from django.urls import path, include
from ventas import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.inicio, name="inicio"),
    path("ventas/", include("ventas.urls")),  # 👈 Esto conecta las URLs de ventas
]
