from django.db import models
from django.utils import timezone
from decimal import Decimal

# ================= MESA =================
class Mesa(models.Model):
    numero = models.PositiveIntegerField(unique=True)
    es_para_llevar = models.BooleanField(default=False)  # Nueva opción para diferenciar mesas virtuales para llevar

    class Meta:
        ordering = ["numero"]

    def __str__(self):
        if self.es_para_llevar:
            return "PARA LLEVAR"
        return f"Mesa {self.numero}"


# ================= PLATO =================
class Plato(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    categoria = models.CharField(max_length=50, default="Otros", db_index=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("nombre", "categoria")
        ordering = ["categoria", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.categoria}) - S/ {self.precio}"


# ================= PEDIDO =================
class Pedido(models.Model):
    ESTADOS = [
        ("abierto", "Abierto"),
        ("cerrado", "Cerrado"),
        ("cancelado", "Cancelado"),
    ]

    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="abierto")
    para_llevar = models.BooleanField(default=False)

    class Meta:
        ordering = ["-creado"]

    @property
    def total(self):
        return sum((d.subtotal for d in self.detalles.all()), Decimal("0.00"))

    @property
    def abierto(self):
        return self.estado == "abierto"

    def __str__(self):
        if self.para_llevar:
            return f"Pedido {self.id} - PARA LLEVAR"
        if self.mesa:
            return f"Pedido {self.id} - Mesa {self.mesa.numero}"
        return f"Pedido {self.id}"


# ================= DETALLE PEDIDO =================
class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="detalles")
    plato = models.ForeignKey(Plato, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    estado = models.CharField(
        max_length=20,
        choices=[("pendiente", "Pendiente"), ("servido", "Servido")],
        default="pendiente",
    )

    @property
    def subtotal(self):
        return self.cantidad * self.plato.precio

    def __str__(self):
        return f"{self.plato.nombre} x{self.cantidad}"


# ================= CAJA =================
class Caja(models.Model):
    fecha = models.DateField(unique=True, default=timezone.localdate)
    monto_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_vendido = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    monto_final = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    abierta = models.BooleanField(default=True)
    fecha_apertura = models.DateTimeField(default=timezone.now)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]

    def cerrar(self, monto_final=None):
        if monto_final is not None:
            self.monto_final = monto_final
        else:
            self.monto_final = self.monto_inicial + (self.total_vendido or 0)
        self.fecha_cierre = timezone.now()
        self.abierta = False
        self.save()

    def calcular_total_vendido(self):
        pedidos = Pedido.objects.filter(creado__date=self.fecha, estado="cerrado")
        self.total_vendido = sum((p.total for p in pedidos), Decimal("0.00"))
        self.save()
        return self.total_vendido

    def __str__(self):
        estado = "Abierta" if self.abierta else "Cerrada"
        return f"Caja {self.fecha} - {estado}"
