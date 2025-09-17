from django.urls import path
from . import views

urlpatterns = [
    # ========== INICIO / DASHBOARD ==========
    path("", views.inicio, name="inicio"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # ========== MESAS ==========
    path("mesas/", views.lista_mesas, name="lista_mesas"),
    path("mesa/<int:mesa_id>/abrir/", views.abrir_mesa, name="abrir_mesa"),

    # ========== PEDIDOS ==========
    path("pedido/<int:pedido_id>/", views.detalle_pedido, name="detalle_pedido"),
    path("pedido/<int:pedido_id>/agregar/<int:plato_id>/", views.agregar_plato, name="agregar_plato"),
    path("pedido/<int:pedido_id>/quitar/<int:plato_id>/", views.quitar_plato, name="quitar_plato"),
    path("pedido/<int:pedido_id>/cerrar/", views.cerrar_pedido, name="cerrar_pedido"),
    path("pedido/<int:pedido_id>/ticket/<str:tipo>/", views.imprimir_ticket, name="imprimir_ticket"),
    path("pedidos/activos/", views.pedidos_activos, name="pedidos_activos"),

    # ========== CARTA ==========
    path("carta/", views.carta, name="carta"),
    path("importar-carta/", views.importar_carta, name="importar_carta"),

    # ========== CAJA ==========
    path("caja/abrir/", views.abrir_caja, name="abrir_caja"),
    path("caja/<int:caja_id>/", views.detalle_caja, name="detalle_caja"),
    path("caja/<int:pk>/cerrar/", views.cerrar_caja, name="cerrar_caja"),
    path("cajas/", views.lista_cajas, name="lista_cajas"),

    path('mesas/liberar/<int:pk>/', views.liberar_mesa, name='liberar_mesa'),
]
