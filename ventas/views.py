# ventas/views.py
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
    """Página de inicio: muestra resumen de mesas y pedidos activos."""
    total_mesas = Mesa.objects.count()
    mesas_ocupadas = Pedido.objects.filter(estado="abierto").values_list("mesa_id", flat=True).distinct().count()
    mesas_libres = max(total_mesas - mesas_ocupadas, 0)
    pedidos_activos = Pedido.objects.filter(estado="abierto").count()

    return render(request, "ventas/inicio.html", {
        "total_mesas": total_mesas,
        "mesas_ocupadas": mesas_ocupadas,
        "mesas_libres": mesas_libres,
        "pedidos_activos": pedidos_activos
    })


# ================= MESAS ==================
def lista_mesas(request):
    """Lista todas las mesas y su estado (ocupada/libre)."""
    mesas = Mesa.objects.all().order_by("numero")
    mesas_info = []
    for mesa in mesas:
        pedido_activo = Pedido.objects.filter(mesa=mesa, estado="abierto").first()
        mesas_info.append({
            "mesa": mesa,
            "ocupada": bool(pedido_activo) or mesa.esta_ocupada,
            "pedido_id": pedido_activo.id if pedido_activo else None,
        })
    return render(request, "ventas/lista_mesas.html", {"mesas_info": mesas_info})


def abrir_mesa(request, mesa_id):
    """Abre un pedido en la mesa seleccionada (marca mesa como ocupada)."""
    mesa = get_object_or_404(Mesa, id=mesa_id)
    # Si ya hay un pedido abierto, redirigimos
    pedido_existente = Pedido.objects.filter(mesa=mesa, estado="abierto").first()
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
    # opcional: marcar pedidos abiertos asociados como cancelados o cerrados? Aquí los dejamos cerrados:
    Pedido.objects.filter(mesa=mesa, estado="abierto").update(estado="cancelado")
    messages.info(request, f"✅ Mesa {mesa.numero} liberada.")
    return redirect("lista_mesas")


# ================= CARTA ==================
def carta(request, pedido_id=None):
    """Muestra la carta de platos, con filtro opcional por categoría."""
    categoria = request.GET.get("categoria")
    platos_qs = Plato.objects.filter(activo=True)
    if categoria:
        platos_qs = platos_qs.filter(categoria=categoria)

    # opciones para filtrar
    categorias = Plato.objects.values_list("categoria", flat=True).distinct().order_by("categoria")
    platos = platos_qs.order_by("categoria", "nombre")
    pedido = get_object_or_404(Pedido, id=pedido_id) if pedido_id else None

    return render(request, "ventas/carta.html", {
        "platos": platos,
        "categorias": categorias,
        "categoria_seleccionada": categoria,
        "pedido": pedido
    })


def importar_carta(request):
    """Importa la carta desde un archivo Excel (por categorías)."""
    if request.method == "POST" and request.FILES.get("archivo"):
        archivo = request.FILES["archivo"]
        fs = FileSystemStorage()
        filename = fs.save(archivo.name, archivo)
        filepath = fs.path(filename)
        try:
            xls = pd.ExcelFile(filepath)
            for hoja in xls.sheet_names:
                df = pd.read_excel(filepath, sheet_name=hoja)
                df.columns = df.columns.str.strip().str.lower()
                for _, row in df.iterrows():
                    nombre = str(row.get("producto", "")).strip()
                    try:
                        precio = float(row.get("precio", 0))
                    except Exception:
                        precio = 0
                    if nombre and precio > 0:
                        Plato.objects.update_or_create(
                            nombre=nombre,
                            defaults={"precio": precio, "categoria": hoja},
                        )
            messages.success(request, "✅ Carta actualizada correctamente desde Excel")
        except Exception as e:
            messages.error(request, f"❌ Error al importar carta: {str(e)}")
        return redirect("lista_mesas")
    return render(request, "ventas/importar_carta.html")


# ================= PEDIDOS ==================
def detalle_pedido(request, pedido_id):
    """Detalle del pedido: lista platos agregados y calcula total."""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    detalles = pedido.detalles.all()
    total = detalles.aggregate(total=Sum(F("cantidad") * F("plato__precio")))["total"] or Decimal("0.00")
    platos = Plato.objects.filter(activo=True).order_by("categoria", "nombre")
    return render(request, "ventas/detalle_pedido.html", {
        "pedido": pedido,
        "detalles": detalles,
        "platos": platos,
        "total": total
    })


def agregar_plato(request, pedido_id, plato_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    if pedido.estado != "abierto":
        messages.error(request, "No se puede modificar un pedido cerrado o cancelado.")
        return redirect("detalle_pedido", pedido_id=pedido.id)
    plato = get_object_or_404(Plato, id=plato_id)
    detalle, created = DetallePedido.objects.get_or_create(pedido=pedido, plato=plato)
    detalle.cantidad += 1
    detalle.save()
    return redirect("detalle_pedido", pedido_id=pedido.id)



def quitar_plato(request, pedido_id, plato_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    if pedido.estado != "abierto":
        messages.error(request, "No se puede modificar un pedido cerrado o cancelado.")
        return redirect("detalle_pedido", pedido_id=pedido.id)
    detalle = get_object_or_404(DetallePedido, pedido=pedido, plato_id=plato_id)
    detalle.cantidad -= 1
    if detalle.cantidad <= 0:
        detalle.delete()
    else:
        detalle.save()
    return redirect("detalle_pedido", pedido_id=pedido.id)

def cerrar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    if pedido.estado != "abierto":
        return redirect("detalle_pedido", pedido_id=pedido.id)
    pedido.cerrar_pedido()
    return redirect("detalle_pedido", pedido_id=pedido.id)


# ================= DASHBOARD ==================
def dashboard(request):
    """Dashboard principal con caja, pedidos y gráficos."""
    hoy = timezone.localdate()

    caja = Caja.objects.filter(fecha=hoy, abierta=True).first()
    ultima_caja = Caja.objects.filter(fecha__lt=hoy).order_by("-fecha").first()

    pedidos = Pedido.objects.filter(creado__date=hoy)
    total_pedidos = pedidos.count()
    total_ingresos = DetallePedido.objects.filter(pedido__in=pedidos)\
        .aggregate(total=Sum(F("cantidad") * F("plato__precio")))["total"] or Decimal("0.00")

    platos_mas_vendidos = DetallePedido.objects.filter(pedido__creado__date=hoy)\
        .values("plato__nombre")\
        .annotate(total=Sum("cantidad"))\
        .order_by("-total")[:5]

    siete_dias = hoy - timedelta(days=6)
    ventas_por_dia_qs = DetallePedido.objects.filter(pedido__creado__date__gte=siete_dias)\
        .values("pedido__creado__date")\
        .annotate(total=Sum(F("cantidad") * F("plato__precio")))\
        .order_by("pedido__creado__date")

    ventas_data = []
    for i in range(7):
        fecha = siete_dias + timedelta(days=i)
        item = next((v for v in ventas_por_dia_qs if v["pedido__creado__date"] == fecha), None)
        ventas_data.append({
            "fecha": fecha.strftime("%Y-%m-%d"),
            "total": item["total"] if item else 0
        })

    return render(request, "ventas/dashboard.html", {
        "caja": caja,
        "ultima_caja": ultima_caja,
        "total_pedidos": total_pedidos,
        "total_ingresos": total_ingresos,
        "platos_mas_vendidos": list(platos_mas_vendidos),
        "ventas_por_dia": ventas_data
    })


# ================= CAJA ==================
def abrir_caja(request):
    """Abre la caja del día con monto inicial."""
    hoy = timezone.localdate()

    if Caja.objects.filter(fecha=hoy).exists():
        messages.info(request, "ℹ️ Ya existe una caja para hoy, no puedes abrir otra.")
        return redirect("dashboard")

    if request.method == "POST":
        try:
            monto_inicial = float(request.POST.get("monto_inicial", 0))
        except Exception:
            monto_inicial = 0

        Caja.objects.create(
            fecha=hoy,
            fecha_apertura=timezone.now(),
            monto_inicial=monto_inicial,
            monto_final=monto_inicial,
            abierta=True
        )
        messages.success(request, "✅ Caja abierta correctamente.")
        return redirect("dashboard")

    return render(request, "ventas/abrir_caja.html")


def cerrar_caja(request, pk):
    """Cierra la caja y calcula el monto final."""
    caja = get_object_or_404(Caja, pk=pk)
    if caja.abierta:
        hoy = caja.fecha
        pedidos = Pedido.objects.filter(creado__date=hoy)
        total_vendido = DetallePedido.objects.filter(pedido__in=pedidos)\
            .aggregate(total=Sum(F("cantidad") * F("plato__precio")))["total"] or Decimal("0.00")

        caja.total_vendido = total_vendido
        caja.monto_final = caja.monto_inicial + total_vendido
        caja.abierta = False
        caja.save()
        messages.success(request, "✅ Caja cerrada correctamente.")
    else:
        messages.warning(request, "La caja ya estaba cerrada.")

    return redirect("dashboard")


def lista_cajas(request):
    """Lista de todas las cajas (historial)."""
    cajas = Caja.objects.all().order_by("-fecha")
    return render(request, "ventas/lista_cajas.html", {"cajas": cajas})


def detalle_caja(request, caja_id):
    """Muestra el detalle de una caja en particular."""
    caja = get_object_or_404(Caja, id=caja_id)
    pedidos = Pedido.objects.filter(creado__date=caja.fecha)

    top_platos = (
        DetallePedido.objects.filter(pedido__in=pedidos)
        .values(nombre=F("plato__nombre"))
        .annotate(total=Sum("cantidad"))
        .order_by("-total")[:5]
    )

    return render(request, "ventas/detalle_caja.html", {
        "caja": caja,
        "top_platos": json.dumps(list(top_platos), default=str)
    })


# ================= TICKET ==================
def imprimir_ticket(request, pedido_id, tipo="cliente"):
    """Genera ticket de un pedido para impresión."""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, "ventas/ticket.html", {"pedido": pedido, "tipo": tipo})


# ================= PEDIDOS ACTIVOS ==================
def pedidos_activos(request):
    """Lista de pedidos activos (no cerrados)."""
    pedidos = Pedido.objects.filter(estado="abierto")
    return render(request, "ventas/pedidos_activos.html", {"pedidos": pedidos})
