from django.contrib import admin
from .models import Producto, Descuento, Boleta, DetalleBoleta, Gasto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'categoria', 'precio_costo', 'precio', 'stock', 'stock_minimo', 'es_stock_critico')
    list_filter = ('categoria',)
    search_fields = ('nombre', 'codigo')


@admin.register(Descuento)
class DescuentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'porcentaje', 'lleve_a', 'pague_b', 'activo')
    list_filter = ('tipo', 'activo')


class DetalleBoletaInline(admin.TabularInline):
    model = DetalleBoleta
    extra = 0


@admin.register(Boleta)
class BoletaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'usuario', 'medio_pago', 'subtotal', 'ahorro', 'total')
    list_filter = ('medio_pago', 'fecha')
    inlines = [DetalleBoletaInline]


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'motivo', 'categoria', 'tipo_comprobante', 'monto', 'usuario')
    list_filter = ('categoria', 'tipo_comprobante', 'fecha')
    search_fields = ('motivo', 'nro_comprobante')
