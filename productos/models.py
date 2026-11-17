from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


# ====================================================
# PRODUCTOS
# ====================================================

class Producto(models.Model):
    CATEGORIA_CHOICES = [
        ('abarrotes', 'Abarrotes y Despensa'),
        ('lacteos', 'Lácteos y Refrigerados'),
        ('bebidas', 'Bebidas, Aguas y Jugos'),
        ('panaderia', 'Panadería y Bollería'),
        ('aseo', 'Aseo y Hogar'),
        ('confites', 'Confites y Snacks'),
        ('otros', 'Otros'),
    ]

    codigo = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Código de barras o código interno"
    )
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(
        max_length=30,
        choices=CATEGORIA_CHOICES,
        default='abarrotes'
    )
    descripcion = models.TextField(blank=True)
    precio_costo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1)]
    )
    stock = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5)

    @property
    def es_stock_critico(self):
        return self.stock <= self.stock_minimo

    @property
    def margen_unitario(self):
        if self.precio and self.precio_costo:
            return self.precio - self.precio_costo
        return self.precio

    def clean(self):
        errores = {}
        if self.nombre and len(self.nombre.strip()) < 2:
            errores['nombre'] = 'El nombre del producto debe tener al menos 2 caracteres.'
        if self.precio is not None and self.precio <= 0:
            errores['precio'] = 'El precio de venta debe ser mayor a $0.'
        if self.precio_costo is not None and self.precio_costo < 0:
            errores['precio_costo'] = 'El precio de costo no puede ser negativo.'
        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return self.nombre


# ====================================================
# DESCUENTOS
# ====================================================

class Descuento(models.Model):
    TIPO_CHOICES = [
        ('porcentaje', 'Porcentaje (%)'),
        ('axb', 'Lleve A y pague B (AxB)'),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    productos = models.ManyToManyField(
        Producto,
        blank=True,
        related_name='descuentos'
    )
    porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Ejemplo: 15.00 para un descuento del 15%"
    )
    lleve_a = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cantidad de productos que debe llevar el cliente"
    )
    pague_b = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cantidad de productos que debe pagar el cliente"
    )
    activo = models.BooleanField(default=True)

    def clean(self):
        errores = {}
        if self.tipo == 'porcentaje':
            if self.porcentaje is None:
                errores['porcentaje'] = 'Debe indicar el porcentaje del descuento.'
            elif self.porcentaje <= 0 or self.porcentaje > 100:
                errores['porcentaje'] = 'El descuento debe ser mayor a 0 y máximo 100%.'
            if self.lleve_a is not None or self.pague_b is not None:
                errores['lleve_a'] = 'Un descuento porcentual no debe utilizar cantidades AxB.'
        elif self.tipo == 'axb':
            if self.lleve_a is None:
                errores['lleve_a'] = 'Debe indicar cuántos productos debe llevar el cliente.'
            if self.pague_b is None:
                errores['pague_b'] = 'Debe indicar cuántos productos debe pagar el cliente.'
            if (
                self.lleve_a is not None
                and self.pague_b is not None
                and self.lleve_a <= self.pague_b
            ):
                errores['lleve_a'] = 'La cantidad que lleva debe ser mayor a la que paga.'
            if self.porcentaje is not None:
                errores['porcentaje'] = 'Un descuento AxB no debe utilizar porcentajes.'
        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


# ====================================================
# BOLETAS
# ====================================================

class Boleta(models.Model):
    MEDIO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('debito', 'Tarjeta Débito / Redcompra'),
        ('credito', 'Tarjeta Crédito'),
        ('transferencia', 'Transferencia Bancaria'),
    ]

    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    medio_pago = models.CharField(
        max_length=20,
        choices=MEDIO_PAGO_CHOICES,
        default='efectivo'
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    ahorro = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vuelto = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Boleta #{self.id} - {self.fecha:%d/%m/%Y}"


class DetalleBoleta(models.Model):
    boleta = models.ForeignKey(
        Boleta,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    nombre_producto = models.CharField(max_length=100)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField()
    subtotal_original = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal_final = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.nombre_producto} x{self.cantidad} (Boleta #{self.boleta.id})"


# ====================================================
# GASTOS
# ====================================================

class Gasto(models.Model):
    CATEGORIA_GASTO_CHOICES = [
        ('proveedores', 'Pago a Proveedores / Mercadería'),
        ('servicios', 'Servicios Básicos (Luz, Agua, Internet)'),
        ('insumos', 'Insumos de Almacén (Bolsas, Rollos térmicos, Aseo)'),
        ('mantencion', 'Mantención y Reparaciones'),
        ('otros', 'Otros Gastos Operativos'),
    ]

    COMPROBANTE_CHOICES = [
        ('boleta', 'Boleta'),
        ('factura', 'Factura'),
        ('recibo', 'Comprobante Interno / Recibo'),
    ]

    fecha = models.DateField()
    categoria = models.CharField(
        max_length=30,
        choices=CATEGORIA_GASTO_CHOICES,
        default='proveedores'
    )
    tipo_comprobante = models.CharField(
        max_length=20,
        choices=COMPROBANTE_CHOICES,
        default='boleta'
    )
    nro_comprobante = models.CharField(max_length=50, blank=True, default='')
    motivo = models.CharField(max_length=150)
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(1)]
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    def clean(self):
        errores = {}
        if self.motivo and len(self.motivo.strip()) < 3:
            errores['motivo'] = 'Describa el motivo del gasto con al menos 3 caracteres.'
        if self.monto is not None and self.monto <= 0:
            errores['monto'] = 'El monto del gasto debe ser mayor a $0.'
        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return f"{self.motivo} - ${self.monto} ({self.fecha:%d/%m/%Y})"
