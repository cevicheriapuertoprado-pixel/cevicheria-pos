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
    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)
    cerrado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-creado"]

    @property
    def total(self):
        """Retorna el total del pedido sumando los subtotales de cada detalle."""
        return sum((d.subtotal for d in self.detalles.all()), Decimal("0.00"))

    def __str__(self):
        return f"Pedido {self.id} - Mesa {self.mesa.numero}"


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
        """Calcula subtotal de este detalle (cantidad x precio del plato)."""
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
        """Cierra la caja calculando monto final si no se especifica."""
        if monto_final is not None:
            self.monto_final = monto_final
        else:
            self.monto_final = self.monto_inicial + (self.total_vendido or 0)
        self.fecha_cierre = timezone.now()
        self.abierta = False
        self.save()

    def calcular_total_vendido(self):
        """Suma todos los pedidos cerrados del día."""
        pedidos = Pedido.objects.filter(creado__date=self.fecha, cerrado=True)
        self.total_vendido = sum((p.total for p in pedidos), Decimal("0.00"))
        self.save()
        return self.total_vendido

    def __str__(self):
        estado = "Abierta" if self.abierta else "Cerrada"
        return f"Caja {self.fecha} - {estado}"
