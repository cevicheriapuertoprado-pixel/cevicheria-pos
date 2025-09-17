from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, F
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from datetime import timedelta
import pandas as pd
import json
from decimal import Decimal

from .models import Mesa, Plato, Pedido, DetallePedido, Caja

# ================= INICIO ==================
def inicio(request):
    total_mesas = Mesa.objects.count()
    mesas_ocupadas = Mesa.objects.filter(esta_ocupada=True).count()
    mesas_libres = max(total_mesas - mesas_ocupadas, 0)
    pedidos_activos = Pedido.objects.filter(cerrado=False).count()

    return render(request, "ventas/inicio.html", {
        "total_mesas": total_mesas,
        "mesas_ocupadas": mesas_ocupadas,
        "mesas_libres": mesas_libres,
        "pedidos_activos": pedidos_activos
    })

# ================= MESAS ==================
def lista_mesas(request):
    mesas = Mesa.objects.all().order_by("numero")
    mesas_info = []
    for mesa in mesas:
        pedido_activo = Pedido.objects.filter(mesa=mesa, cerrado=False).first()
        mesas_info.append({
            "mesa": mesa,
            "ocupada": mesa.esta_ocupada,
            "pedido_id": pedido_activo.id if pedido_activo else None,
        })
    return render(request, "ventas/lista_mesas.html", {"mesas_info": mesas_info})

def abrir_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id)
    pedido_existente = Pedido.objects.filter(mesa=mesa, cerrado=False).first()
    if pedido_existente:
        return redirect("detalle_pedido", pedido_id=pedido_existente.id)

    # Crear pedido y marcar mesa ocupada
    pedido = Pedido.objects.create(mesa=mesa)
    mesa.esta_ocupada = True
    mesa.save()

    return redirect("detalle_pedido", pedido_id=pedido.id)

def liberar_mesa(request, mesa_id):
    """Libera una mesa sin borrar pedidos (por ejemplo, si cliente se retira)."""
    mesa = get_object_or_404(Mesa, id=mesa_id)
    mesa.esta_ocupada = False
    mesa.save()
    # Cerramos pedidos abiertos asociados a esta mesa
    Pedido.objects.filter(mesa=mesa, cerrado=False).update(cerrado=True)
    messages.info(request, f"✅ Mesa {mesa.numero} liberada.")
    return redirect("lista_mesas")

# ================= CARTA ==================
def carta(request, pedido_id=None):
    categoria_filtro = request.GET.get("categoria")
    platos_qs = Plato.objects.filter(activo=True)
    if categoria_filtro:
        platos_qs = platos_qs.filter(categoria=categoria_filtro)

    platos = platos_qs.order_by("categoria", "nombre")
    categorias = Plato.objects.values_list("categoria", flat=True).distinct()

    pedido = get_object_or_404(Pedido, id=pedido_id) if pedido_id else None
    return render(request, "ventas/carta.html", {
        "platos": platos,
        "categorias": categorias,
        "categoria_seleccionada": categoria_filtro,
        "pedido": pedido
    })

# ================= PEDIDOS ==================
def detalle_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    detalles = pedido.detalles.all()
    total = detalles.aggregate(total=Sum(F("cantidad") * F("plato__precio")))["total"] or 0
    platos = Plato.objects.filter(activo=True).order_by("categoria", "nombre")

    return render(request, "ventas/detalle_pedido.html", {
        "pedido": pedido,
        "detalles": detalles,
        "platos": platos,
        "total": total
    })

def agregar_plato(request, pedido_id, plato_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    plato = get_object_or_404(Plato, id=plato_id)
    detalle, creado = DetallePedido.objects.get_or_create(
        pedido=pedido,
        plato=plato,
        defaults={"cantidad": 1}
    )
    if not creado:
        detalle.cantidad += 1
        detalle.save()
    return redirect("detalle_pedido", pedido_id=pedido.id)

def quitar_plato(request, pedido_id, plato_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    plato = get_object_or_404(Plato, id=plato_id)
    detalle = get_object_or_404(DetallePedido, pedido=pedido, plato=plato)
    if detalle.cantidad > 1:
        detalle.cantidad -= 1
        detalle.save()
    else:
        detalle.delete()
    return redirect("detalle_pedido", pedido_id=pedido.id)

def cerrar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    if pedido.cerrado:
        return redirect("detalle_pedido", pedido_id=pedido.id)

    pedido.cerrado = True
    pedido.save()

    if pedido.mesa:
        pedido.mesa.esta_ocupada = False
        pedido.mesa.save()

    hoy = timezone.localdate()
    caja = Caja.objects.filter(fecha=hoy, abierta=True).first()
    if caja:
        caja.calcular_total_vendido()

    return redirect("lista_mesas")
