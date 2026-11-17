from decimal import Decimal
import csv
import io
import unicodedata

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Sum, Count, F, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse, HttpResponse

from .models import Producto, Descuento, Boleta, DetalleBoleta, Gasto
from .forms import ProductoForm, DescuentoForm, GastoForm
from .cart import Carrito


# ----------------------------------------------------
# VERIFICACIÓN DE PERMISOS
# ----------------------------------------------------

def es_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


# ----------------------------------------------------
# INICIO
# ----------------------------------------------------

def inicio(request):
    total_productos = Producto.objects.count()
    productos_criticos = Producto.objects.filter(stock__lte=F('stock_minimo')).count()
    ofertas_activas = Descuento.objects.filter(activo=True).count()
    total_ventas = Boleta.objects.aggregate(s=Sum('total'))['s'] or Decimal('0.00')
    total_gastos = Gasto.objects.aggregate(s=Sum('monto'))['s'] or Decimal('0.00')
    margen_neto = total_ventas - total_gastos

    return render(request, 'inicio.html', {
        'total_productos': total_productos,
        'productos_criticos': productos_criticos,
        'ofertas_activas': ofertas_activas,
        'total_ventas': total_ventas,
        'total_gastos': total_gastos,
        'margen_neto': margen_neto,
    })


# ----------------------------------------------------
# CRUD DE PRODUCTOS Y OFERTAS
# ----------------------------------------------------

@login_required
@user_passes_test(es_admin, login_url='inicio')
def producto_list(request):
    return render_gestion_productos(request)


def render_gestion_productos(
    request,
    producto_form=None,
    producto_editar=None,
    producto_edit_form=None,
    descuento_form=None,
    descuento_editar=None,
    form_editar=None,
    modal_activo=None,
):
    q = request.GET.get('q', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    solo_critico = request.GET.get('critico', '').strip() == '1'

    productos_qs = Producto.objects.all().order_by('-id')

    if q:
        productos_qs = productos_qs.filter(
            Q(nombre__icontains=q) |
            Q(codigo__icontains=q) |
            Q(descripcion__icontains=q)
        )
    if categoria:
        productos_qs = productos_qs.filter(categoria=categoria)
    if solo_critico:
        productos_qs = productos_qs.filter(stock__lte=F('stock_minimo'))

    todos_productos = Producto.objects.all()
    total_criticos = todos_productos.filter(stock__lte=F('stock_minimo')).count()
    total_filtrados = productos_qs.count()

    paginator = Paginator(productos_qs, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    descuentos = Descuento.objects.prefetch_related('productos').all().order_by('-id')

    if form_editar is None and descuento_editar is not None:
        form_editar = DescuentoForm(instance=descuento_editar, prefix='editar')

    return render(request, 'productos/list.html', {
        'productos': page_obj,
        'page_obj': page_obj,
        'total_filtrados': total_filtrados,
        'total_productos_catalogo': todos_productos.count(),
        'total_criticos': total_criticos,
        'q': q,
        'categoria_sel': categoria,
        'solo_critico': solo_critico,
        'categorias': Producto.CATEGORIA_CHOICES,
        'form': producto_form or ProductoForm(),
        'producto_editar': producto_editar,
        'producto_edit_form': producto_edit_form,
        'descuento_form': descuento_form or DescuentoForm(),
        'descuentos': descuentos,
        'descuento_editar': descuento_editar,
        'form_editar': form_editar,
        'modal_activo': modal_activo,
    })


@login_required
@user_passes_test(es_admin, login_url='inicio')
def producto_create(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            prod = form.save()
            messages.success(
                request,
                f'Producto "{prod.nombre}" creado correctamente.'
            )
            return redirect('producto_list')
        else:
            messages.error(
                request,
                'No se pudo crear el producto. Verifica los datos ingresados.'
            )
            return render_gestion_productos(
                request,
                producto_form=form,
                modal_activo='crearProducto'
            )
    return redirect('producto_list')


@login_required
@user_passes_test(es_admin, login_url='inicio')
def producto_edit(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            prod = form.save()
            messages.success(
                request,
                f'Producto "{prod.nombre}" actualizado correctamente.'
            )
            return redirect('producto_list')
        else:
            messages.error(
                request,
                'No se pudo actualizar el producto. Verifica los datos.'
            )
            return render_gestion_productos(
                request,
                producto_editar=producto,
                producto_edit_form=form,
                modal_activo=f'editarProducto{producto.id}'
            )
    return redirect('producto_list')


@login_required
@user_passes_test(es_admin, login_url='inicio')
@require_POST
def producto_delete(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    nombre = producto.nombre
    producto.delete()
    messages.success(
        request,
        f'El producto "{nombre}" fue eliminado correctamente.'
    )
    return redirect('producto_list')


# ----------------------------------------------------
# OFERTAS Y DESCUENTOS
# ----------------------------------------------------

@login_required
@user_passes_test(es_admin, login_url='inicio')
@require_POST
def descuento_create(request):
    form = DescuentoForm(request.POST)
    if form.is_valid():
        descuento = form.save()
        messages.success(
            request,
            f'Oferta "{descuento.nombre}" creada correctamente.'
        )
        return redirect('producto_list')

    messages.error(
        request,
        'No se pudo crear la oferta. Revisa los datos ingresados.'
    )
    return render_gestion_productos(
        request,
        descuento_form=form,
        modal_activo='crearOferta'
    )


@login_required
@user_passes_test(es_admin, login_url='inicio')
def descuento_edit(request, pk):
    descuento = get_object_or_404(Descuento, pk=pk)
    if request.method == 'POST':
        form = DescuentoForm(request.POST, instance=descuento, prefix='editar')
        if form.is_valid():
            form.save()
            messages.success(request, 'Oferta actualizada correctamente.')
            return redirect('producto_list')
        else:
            messages.error(request, 'No se pudo actualizar la oferta. Revisa los campos.')
    else:
        form = DescuentoForm(instance=descuento, prefix='editar')

    return render_gestion_productos(
        request,
        descuento_editar=descuento,
        form_editar=form
    )


@login_required
@user_passes_test(es_admin, login_url='inicio')
@require_POST
def descuento_toggle(request, pk):
    descuento = get_object_or_404(Descuento, pk=pk)
    descuento.activo = not descuento.activo
    descuento.save(update_fields=['activo'])
    estado = 'activada' if descuento.activo else 'desactivada'
    messages.success(request, f'La oferta "{descuento.nombre}" fue {estado}.')
    return redirect('producto_list')


@login_required
@user_passes_test(es_admin, login_url='inicio')
@require_POST
def descuento_delete(request, pk):
    descuento = get_object_or_404(Descuento, pk=pk)
    nombre = descuento.nombre
    descuento.delete()
    messages.success(request, f'La oferta "{nombre}" fue eliminada correctamente.')
    return redirect('producto_list')


# ----------------------------------------------------
# CARRITO DE VENTA
# ----------------------------------------------------

@login_required
def ver_carrito(request):
    carrito = Carrito(request)
    items = carrito.obtener_items()
    total = sum((item['subtotal'] for item in items), Decimal('0.00'))
    ahorro_total = sum((item['ahorro'] for item in items), Decimal('0.00'))
    productos_rapidos = Producto.objects.filter(stock__gt=0).order_by('nombre')[:12]

    return render(request, 'carrito/ver.html', {
        'items': items,
        'total': total,
        'ahorro_total': ahorro_total,
        'productos_rapidos': productos_rapidos,
        'medios_pago': Boleta.MEDIO_PAGO_CHOICES,
    })


@login_required
@require_POST
def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    carrito = Carrito(request)
    try:
        carrito.agregar(producto)
        messages.success(request, f'{producto.nombre} agregado al carrito.')
    except ValueError as error:
        messages.error(request, str(error))
    return redirect('ver_carrito')


@login_required
@require_POST
def modificar_cantidad_carrito(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    carrito = Carrito(request)
    try:
        cantidad = int(request.POST.get('cantidad', 1))
        carrito.modificar_cantidad(producto, cantidad)
        messages.success(request, 'Cantidad actualizada correctamente.')
    except ValueError:
        messages.error(request, 'La cantidad ingresada no es válida o supera el stock disponible.')
    return redirect('ver_carrito')


@login_required
@require_POST
def eliminar_del_carrito(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    carrito = Carrito(request)
    carrito.eliminar(producto)
    messages.success(request, f'{producto.nombre} eliminado del carrito.')
    return redirect('ver_carrito')


@login_required
def buscar_productos_carrito(request):
    busqueda = request.GET.get('q', '').strip()
    productos = Producto.objects.none()
    if busqueda:
        productos = Producto.objects.filter(
            Q(nombre__icontains=busqueda) | Q(codigo__icontains=busqueda),
            stock__gt=0
        ).order_by('nombre')
    return render(request, 'carrito/buscar.html', {
        'productos': productos,
        'busqueda': busqueda
    })


@login_required
def buscar_productos_carrito_ajax(request):
    busqueda = request.GET.get('q', '').strip()

    def normalizar(texto):
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
        return texto.casefold()

    resultados = []
    if busqueda:
        busqueda_normalizada = normalizar(busqueda)
        productos = Producto.objects.filter(stock__gt=0).order_by('nombre')
        for producto in productos:
            nombre_norm = normalizar(producto.nombre)
            desc_norm = normalizar(producto.descripcion or '')
            cod_norm = normalizar(producto.codigo or '')
            if (
                busqueda_normalizada in nombre_norm
                or busqueda_normalizada in desc_norm
                or busqueda_normalizada in cod_norm
            ):
                resultados.append({
                    'id': producto.id,
                    'codigo': producto.codigo or '',
                    'nombre': producto.nombre,
                    'descripcion': producto.descripcion or '',
                    'precio': str(producto.precio),
                    'stock': producto.stock,
                })

    return JsonResponse({'productos': resultados})


@login_required
@require_POST
def finalizar_venta(request):
    carrito = Carrito(request)
    items = carrito.obtener_items()

    if not items:
        messages.error(request, 'No hay productos para registrar la venta.')
        return redirect('ver_carrito')

    medio_pago = request.POST.get('medio_pago', 'efectivo')
    monto_pagado_raw = request.POST.get('monto_pagado', '').strip()

    try:
        with transaction.atomic():
            productos_bloqueados = {}
            for item in items:
                producto = Producto.objects.select_for_update().get(pk=item['producto'].pk)
                if item['cantidad'] > producto.stock:
                    raise ValueError(f'Stock insuficiente para {producto.nombre}.')
                productos_bloqueados[producto.id] = producto

            subtotal = sum((item['subtotal_original'] for item in items), Decimal('0.00'))
            total = sum((item['subtotal'] for item in items), Decimal('0.00'))
            ahorro = subtotal - total

            if monto_pagado_raw:
                monto_pagado = Decimal(monto_pagado_raw)
            else:
                monto_pagado = total

            if medio_pago == 'efectivo' and monto_pagado < total:
                raise ValueError(f'El monto recibido (${monto_pagado}) es menor al total (${total}).')

            vuelto = max(Decimal('0.00'), monto_pagado - total) if medio_pago == 'efectivo' else Decimal('0.00')

            boleta = Boleta.objects.create(
                usuario=request.user,
                medio_pago=medio_pago,
                subtotal=subtotal,
                ahorro=ahorro,
                total=total,
                monto_pagado=monto_pagado,
                vuelto=vuelto,
            )

            for item in items:
                producto = productos_bloqueados[item['producto'].id]
                DetalleBoleta.objects.create(
                    boleta=boleta,
                    producto=producto,
                    nombre_producto=producto.nombre,
                    precio_unitario=item['precio_unitario'],
                    cantidad=item['cantidad'],
                    subtotal_original=item['subtotal_original'],
                    descuento=item['ahorro'],
                    subtotal_final=item['subtotal'],
                )
                producto.stock -= item['cantidad']
                producto.save(update_fields=['stock'])

            carrito.vaciar()

        messages.success(request, 'Venta registrada correctamente.')
        return redirect('ver_boleta', boleta_id=boleta.id)

    except Producto.DoesNotExist:
        messages.error(request, 'Uno de los productos ya no existe.')
        return redirect('ver_carrito')
    except ValueError as error:
        messages.error(request, str(error))
        return redirect('ver_carrito')


@login_required
def ver_boleta(request, boleta_id):
    boleta = get_object_or_404(Boleta.objects.prefetch_related('detalles'), pk=boleta_id)
    return render(request, 'carrito/boleta.html', {'boleta': boleta})


# ----------------------------------------------------
# HISTORIAL DE BOLETAS
# ----------------------------------------------------

@login_required
def historial_boletas(request):
    desde = request.GET.get('desde', '').strip()
    hasta = request.GET.get('hasta', '').strip()
    medio_pago = request.GET.get('medio_pago', '').strip()

    boletas = Boleta.objects.select_related('usuario').prefetch_related('detalles').order_by('-fecha')

    if desde:
        boletas = boletas.filter(fecha__date__gte=desde)
    if hasta:
        boletas = boletas.filter(fecha__date__lte=hasta)
    if medio_pago:
        boletas = boletas.filter(medio_pago=medio_pago)

    total_periodo = boletas.aggregate(s=Sum('total'))['s'] or Decimal('0.00')
    ahorro_periodo = boletas.aggregate(s=Sum('ahorro'))['s'] or Decimal('0.00')

    return render(request, 'ventas/historial.html', {
        'boletas': boletas,
        'desde': desde,
        'hasta': hasta,
        'medio_pago_sel': medio_pago,
        'medios_pago': Boleta.MEDIO_PAGO_CHOICES,
        'total_periodo': total_periodo,
        'ahorro_periodo': ahorro_periodo,
    })


# ----------------------------------------------------
# GASTOS
# ----------------------------------------------------

@login_required
@user_passes_test(es_admin, login_url='inicio')
def gasto_list(request, gasto_form=None, gasto_editar=None, gasto_edit_form=None, modal_activo=None):
    q = request.GET.get('q', '').strip()
    categoria = request.GET.get('categoria', '').strip()

    gastos = Gasto.objects.select_related('usuario').order_by('-fecha', '-id')
    if q:
        gastos = gastos.filter(Q(motivo__icontains=q) | Q(nro_comprobante__icontains=q))
    if categoria:
        gastos = gastos.filter(categoria=categoria)

    total_gastos = gastos.aggregate(s=Sum('monto'))['s'] or Decimal('0.00')

    if gasto_form is None:
        gasto_form = GastoForm(initial={'fecha': timezone.localdate()})

    return render(request, 'gastos/list.html', {
        'gastos': gastos,
        'total_gastos': total_gastos,
        'q': q,
        'categoria_sel': categoria,
        'categorias_gasto': Gasto.CATEGORIA_GASTO_CHOICES,
        'form': gasto_form,
        'gasto_editar': gasto_editar,
        'gasto_edit_form': gasto_edit_form,
        'modal_activo': modal_activo,
    })


@login_required
@user_passes_test(es_admin, login_url='inicio')
@require_POST
def gasto_create(request):
    form = GastoForm(request.POST)
    if form.is_valid():
        gasto = form.save(commit=False)
        gasto.usuario = request.user
        gasto.save()
        messages.success(request, f'Gasto "{gasto.motivo}" registrado correctamente.')
        return redirect('gasto_list')
    messages.error(request, 'No se pudo registrar el gasto. Revisa los datos.')
    return gasto_list(request, gasto_form=form, modal_activo='crearGasto')


@login_required
@user_passes_test(es_admin, login_url='inicio')
@require_POST
def gasto_edit(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk)
    form = GastoForm(request.POST, instance=gasto)
    if form.is_valid():
        gasto = form.save()
        messages.success(request, f'Gasto "{gasto.motivo}" actualizado correctamente.')
        return redirect('gasto_list')
    messages.error(request, 'No se pudo actualizar el gasto. Verifica los campos.')
    return gasto_list(
        request,
        gasto_editar=gasto,
        gasto_edit_form=form,
        modal_activo=f'editarGasto{gasto.id}'
    )


@login_required
@user_passes_test(es_admin, login_url='inicio')
@require_POST
def gasto_delete(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk)
    motivo = gasto.motivo
    gasto.delete()
    messages.success(request, f'El gasto "{motivo}" fue eliminado correctamente.')
    return redirect('gasto_list')


# ----------------------------------------------------
# BALANCE Y RESUMEN FINANCIERO
# ----------------------------------------------------

@login_required
@user_passes_test(es_admin, login_url='inicio')
def resumen_financiero(request):
    ventas_totales = Boleta.objects.aggregate(s=Sum('total'))['s'] or Decimal('0.00')
    descuentos_otorgados = Boleta.objects.aggregate(s=Sum('ahorro'))['s'] or Decimal('0.00')
    gastos_totales = Gasto.objects.aggregate(s=Sum('monto'))['s'] or Decimal('0.00')
    margen_neto = ventas_totales - gastos_totales

    cantidad_boletas = Boleta.objects.count()
    cantidad_gastos = Gasto.objects.count()
    productos_criticos = Producto.objects.filter(stock__lte=F('stock_minimo')).order_by('stock')

    ventas_por_medio = (
        Boleta.objects.values('medio_pago')
        .annotate(total=Sum('total'), cantidad=Count('id'))
        .order_by('-total')
    )
    gastos_por_categoria = (
        Gasto.objects.values('categoria')
        .annotate(total=Sum('monto'), cantidad=Count('id'))
        .order_by('-total')
    )
    top_productos = (
        DetalleBoleta.objects.values('nombre_producto')
        .annotate(unidades=Sum('cantidad'), recaudado=Sum('subtotal_final'))
        .order_by('-unidades')[:8]
    )

    return render(request, 'finanzas/resumen.html', {
        'ventas_totales': ventas_totales,
        'descuentos_otorgados': descuentos_otorgados,
        'gastos_totales': gastos_totales,
        'margen_neto': margen_neto,
        'cantidad_boletas': cantidad_boletas,
        'cantidad_gastos': cantidad_gastos,
        'productos_criticos': productos_criticos,
        'ventas_por_medio': ventas_por_medio,
        'gastos_por_categoria': gastos_por_categoria,
        'top_productos': top_productos,
    })


# ----------------------------------------------------
# EXPORTACIÓN E IMPORTACIÓN CSV / EXCEL
# ----------------------------------------------------

@login_required
@user_passes_test(es_admin, login_url='inicio')
def exportar_excel(request, tipo):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    fecha_str = timezone.localdate().strftime('%Y%m%d')
    response['Content-Disposition'] = f'attachment; filename="reporte_{tipo}_{fecha_str}.csv"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')

    if tipo == 'productos':
        writer.writerow(['Código', 'Nombre', 'Categoría', 'Precio Costo ($)', 'Precio Venta ($)', 'Stock Actual', 'Stock Mínimo', 'Estado Stock'])
        for p in Producto.objects.all().order_by('nombre'):
            estado = 'CRÍTICO' if p.es_stock_critico else 'NORMAL'
            writer.writerow([p.codigo, p.nombre, p.get_categoria_display(), p.precio_costo, p.precio, p.stock, p.stock_minimo, estado])

    elif tipo == 'ventas':
        writer.writerow(['N° Boleta', 'Fecha y Hora', 'Cajero/Usuario', 'Medio de Pago', 'Subtotal ($)', 'Descuento ($)', 'Total Pagado ($)'])
        for b in Boleta.objects.select_related('usuario').order_by('-fecha'):
            writer.writerow([
                b.id,
                timezone.localtime(b.fecha).strftime('%d/%m/%Y %H:%M'),
                b.usuario.username if b.usuario else 'Sistema',
                b.get_medio_pago_display(),
                b.subtotal,
                b.ahorro,
                b.total,
            ])

    elif tipo == 'gastos':
        writer.writerow(['ID', 'Fecha', 'Categoría', 'Comprobante', 'N° Comprobante', 'Motivo', 'Monto ($)', 'Registrado por'])
        for g in Gasto.objects.select_related('usuario').order_by('-fecha'):
            writer.writerow([
                g.id,
                g.fecha.strftime('%d/%m/%Y'),
                g.get_categoria_display(),
                g.get_tipo_comprobante_display(),
                g.nro_comprobante,
                g.motivo,
                g.monto,
                g.usuario.username if g.usuario else 'Admin',
            ])

    return response


@login_required
@user_passes_test(es_admin, login_url='inicio')
@require_POST
def importar_productos_csv(request):
    archivo = request.FILES.get('archivo_csv')
    if not archivo:
        messages.error(request, 'Seleccione un archivo CSV para importar.')
        return redirect('producto_list')

    try:
        contenido = archivo.read().decode('utf-8-sig')
        lector = csv.DictReader(io.StringIO(contenido), delimiter=';')
        creados = 0
        actualizados = 0
        for fila in lector:
            nombre = (fila.get('Nombre') or fila.get('nombre') or '').strip()
            precio_raw = (fila.get('Precio Venta ($)') or fila.get('precio') or '0').strip()
            stock_raw = (fila.get('Stock Actual') or fila.get('stock') or '0').strip()
            codigo = (fila.get('Código') or fila.get('codigo') or '').strip()
            if not nombre:
                continue
            precio = Decimal(precio_raw.replace('$', '').replace('.', '').replace(',', '.') or '1000')
            stock = max(0, int(float(stock_raw or 0)))

            prod, created = Producto.objects.update_or_create(
                nombre=nombre,
                defaults={
                    'codigo': codigo,
                    'precio': max(Decimal('1'), precio),
                    'stock': stock,
                }
            )
            if created:
                creados += 1
            else:
                actualizados += 1

        messages.success(
            request,
            f'Importación completada: {creados} productos nuevos y {actualizados} actualizados.'
        )
    except Exception:
        messages.error(request, 'Error al procesar el archivo. Verifica el formato CSV.')

    return redirect('producto_list')


# ----------------------------------------------------
# CONDICIONES DE USO Y SEGURIDAD
# ----------------------------------------------------

def seguridad_ley21459(request):
    return render(request, 'seguridad/ley21459.html')
