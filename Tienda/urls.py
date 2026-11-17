from django.contrib import admin
from django.urls import path, include
from productos import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticación
    path('accounts/', include('django.contrib.auth.urls')),

    # Inicio
    path('', views.inicio, name='inicio'),

    # Productos
    path('productos/', views.producto_list, name='producto_list'),
    path('productos/crear/', views.producto_create, name='producto_create'),
    path('productos/editar/<int:pk>/', views.producto_edit, name='producto_edit'),
    path('productos/eliminar/<int:pk>/', views.producto_delete, name='producto_delete'),

    # Ofertas
    path('ofertas/crear/', views.descuento_create, name='descuento_create'),
    path('ofertas/editar/<int:pk>/', views.descuento_edit, name='descuento_edit'),
    path('ofertas/activar/<int:pk>/', views.descuento_toggle, name='descuento_toggle'),
    path('ofertas/eliminar/<int:pk>/', views.descuento_delete, name='descuento_delete'),

    # Caja y carrito
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/buscar/', views.buscar_productos_carrito, name='buscar_productos_carrito'),
    path('carrito/buscar/ajax/', views.buscar_productos_carrito_ajax, name='buscar_productos_carrito_ajax'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/modificar/<int:producto_id>/', views.modificar_cantidad_carrito, name='modificar_cantidad_carrito'),
    path('carrito/eliminar/<int:producto_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('carrito/finalizar/', views.finalizar_venta, name='finalizar_venta'),

    # Boletas
    path('boleta/<int:boleta_id>/', views.ver_boleta, name='ver_boleta'),
    path('ventas/historial/', views.historial_boletas, name='historial_boletas'),

    # Gastos
    path('gastos/', views.gasto_list, name='gasto_list'),
    path('gastos/crear/', views.gasto_create, name='gasto_create'),
    path('gastos/editar/<int:pk>/', views.gasto_edit, name='gasto_edit'),
    path('gastos/eliminar/<int:pk>/', views.gasto_delete, name='gasto_delete'),

    # Balance
    path('finanzas/resumen/', views.resumen_financiero, name='resumen_financiero'),

    # Exportar e importar csv
    path('exportar/<str:tipo>/', views.exportar_excel, name='exportar_excel'),
    path('productos/importar/', views.importar_productos_csv, name='importar_productos_csv'),

    # Condiciones de uso
    path('condiciones-uso/', views.seguridad_ley21459, name='seguridad_ley21459'),
]
