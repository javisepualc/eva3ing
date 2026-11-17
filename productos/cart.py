
from decimal import Decimal, ROUND_HALF_UP

from .models import Producto, Descuento


class Carrito:

    def __init__(self, request):

        self.session = request.session

        carrito = self.session.get('carrito')

        if carrito is None:
            carrito = self.session['carrito'] = {}

        self.carrito = carrito

    # ====================================================
    # GUARDAR CAMBIOS EN LA SESIÓN
    # ====================================================

    def guardar(self):

        self.session['carrito'] = self.carrito
        self.session.modified = True

    # ====================================================
    # OBTENER CANTIDAD ACTUAL
    # ====================================================

    def obtener_cantidad(self, producto):

        producto_id = str(producto.id)

        if producto_id in self.carrito:
            return self.carrito[producto_id]['cantidad']

        return 0

    # ====================================================
    # AGREGAR PRODUCTO
    # ====================================================

    def agregar(self, producto, cantidad=1):

        if cantidad < 1:
            raise ValueError(
                'La cantidad debe ser mayor a cero.'
            )

        if producto.stock <= 0:
            raise ValueError(
                'Este producto no tiene unidades disponibles.'
            )

        producto_id = str(producto.id)

        cantidad_actual = self.obtener_cantidad(producto)

        nueva_cantidad = cantidad_actual + cantidad

        if nueva_cantidad > producto.stock:
            raise ValueError(
                f'Solo quedan {producto.stock} unidades disponibles.'
            )

        self.carrito[producto_id] = {
            'cantidad': nueva_cantidad
        }

        self.guardar()

    # ====================================================
    # MODIFICAR CANTIDAD
    # ====================================================

    def modificar_cantidad(self, producto, cantidad):

        if cantidad < 1:
            raise ValueError(
                'La cantidad debe ser mayor a cero.'
            )

        if cantidad > producto.stock:
            raise ValueError(
                f'Solo quedan {producto.stock} unidades disponibles.'
            )

        producto_id = str(producto.id)

        if producto_id in self.carrito:

            self.carrito[producto_id] = {
                'cantidad': cantidad
            }

            self.guardar()

    # ====================================================
    # ELIMINAR PRODUCTO
    # ====================================================

    def eliminar(self, producto):

        producto_id = str(producto.id)

        if producto_id in self.carrito:

            del self.carrito[producto_id]

            self.guardar()

    # ====================================================
    # CALCULAR DESCUENTOS DE TODO EL CARRITO
    # ====================================================

    def calcular_descuentos(self, productos_cantidad):

        # Cada unidad física tiene un identificador propio.
        unidades = {}

        for producto in productos_cantidad:

            producto_id = str(producto.id)

            precio = Decimal(str(producto.precio))

            for numero in range(productos_cantidad[producto]):

                identificador = (producto_id, numero)

                unidades[identificador] = {
                    'producto': producto,
                    'precio': precio
                }

        # Candidatos a promociones.
        candidatos = []

        descuentos = Descuento.objects.filter(
            activo=True
        ).prefetch_related('productos')

        # ====================================================
        # GENERAR CANDIDATOS
        # ====================================================

        for descuento in descuentos:

            productos_oferta = {
                str(producto.id)
                for producto in descuento.productos.all()
            }

            unidades_elegibles = [
                identificador
                for identificador, datos in unidades.items()
                if identificador[0] in productos_oferta
            ]

            # ------------------------------------------------
            # DESCUENTO PORCENTUAL
            # ------------------------------------------------

            if descuento.tipo == 'porcentaje':

                porcentaje = descuento.porcentaje

                if porcentaje is None:
                    continue

                if porcentaje <= 0 or porcentaje > 100:
                    continue

                for identificador in unidades_elegibles:

                    precio = unidades[identificador]['precio']

                    ahorro = (
                        precio *
                        porcentaje /
                        Decimal('100')
                    ).quantize(
                        Decimal('0.01'),
                        rounding=ROUND_HALF_UP
                    )

                    if ahorro > 0:

                        candidatos.append({
                            'unidades': [identificador],
                            'ahorro': ahorro,
                            'descuentos': {
                                identificador: ahorro
                            }
                        })

            # ------------------------------------------------
            # OFERTA AXB
            # ------------------------------------------------

            elif descuento.tipo == 'axb':

                a = descuento.lleve_a
                b = descuento.pague_b

                if (
                    a is None
                    or b is None
                    or a <= b
                    or b < 0
                ):
                    continue

                # Ordenamos las unidades por precio.
                # Las más caras se agrupan primero.
                unidades_ordenadas = sorted(
                    unidades_elegibles,
                    key=lambda identificador: (
                        -unidades[identificador]['precio'],
                        identificador
                    )
                )

                # Solo se consideran grupos completos.
                cantidad_grupos = len(unidades_ordenadas) // a

                for numero_grupo in range(cantidad_grupos):

                    inicio = numero_grupo * a
                    fin = inicio + a

                    grupo = unidades_ordenadas[inicio:fin]

                    # Dentro del grupo, las unidades más
                    # baratas son las que quedan gratis.
                    grupo_barato = sorted(
                        grupo,
                        key=lambda identificador: (
                            unidades[identificador]['precio'],
                            identificador
                        )
                    )

                    cantidad_gratis = a - b

                    unidades_gratis = grupo_barato[:cantidad_gratis]

                    descuentos_grupo = {}

                    ahorro_grupo = Decimal('0.00')

                    for identificador in unidades_gratis:

                        precio = unidades[identificador]['precio']

                        descuentos_grupo[identificador] = precio

                        ahorro_grupo += precio

                    if ahorro_grupo > 0:

                        candidatos.append({
                            'unidades': grupo,
                            'ahorro': ahorro_grupo,
                            'descuentos': descuentos_grupo
                        })

        # ====================================================
        # APLICAR PROMOCIONES SIN SUPERPOSICIÓN
        # ====================================================

        candidatos.sort(
            key=lambda candidato: candidato['ahorro'],
            reverse=True
        )

        unidades_utilizadas = set()

        descuentos_aplicados = {}

        for candidato in candidatos:

            grupo = set(candidato['unidades'])

            # No permitimos que una unidad participe
            # en más de una promoción.
            if grupo & unidades_utilizadas:
                continue

            unidades_utilizadas.update(grupo)

            for identificador, ahorro in candidato['descuentos'].items():

                descuentos_aplicados[identificador] = ahorro

        # ====================================================
        # AGRUPAR DESCUENTOS POR PRODUCTO
        # ====================================================

        ahorro_por_producto = {}

        for identificador, ahorro in descuentos_aplicados.items():

            producto_id = identificador[0]

            ahorro_por_producto[producto_id] = (
                ahorro_por_producto.get(
                    producto_id,
                    Decimal('0.00')
                ) + ahorro
            )

        return ahorro_por_producto

    # ====================================================
    # OBTENER PRODUCTOS DEL CARRITO
    # ====================================================

    def obtener_items(self):

        items = []

        productos = Producto.objects.filter(
            id__in=self.carrito.keys()
        )

        productos_dict = {
            str(producto.id): producto
            for producto in productos
        }

        productos_cantidad = {}

        # Primero validamos todos los productos.
        for producto_id, datos in list(self.carrito.items()):

            producto = productos_dict.get(producto_id)

            if producto is None:

                del self.carrito[producto_id]

                continue

            cantidad = datos['cantidad']

            if cantidad > producto.stock:
                cantidad = producto.stock

            if cantidad <= 0:

                del self.carrito[producto_id]

                continue

            if cantidad != datos['cantidad']:

                self.carrito[producto_id] = {
                    'cantidad': cantidad
                }

            productos_cantidad[producto] = cantidad

        # Calculamos las promociones considerando
        # todos los productos simultáneamente.
        ahorro_por_producto = self.calcular_descuentos(
            productos_cantidad
        )

        # Construimos los elementos finales.
        for producto, cantidad in productos_cantidad.items():

            producto_id = str(producto.id)

            precio = Decimal(str(producto.precio))

            subtotal_original = precio * cantidad

            ahorro = ahorro_por_producto.get(
                producto_id,
                Decimal('0.00')
            )

            subtotal = subtotal_original - ahorro

            items.append({

                'producto': producto,

                'cantidad': cantidad,

                'precio_unitario': precio,

                'subtotal_original': subtotal_original,

                'subtotal': subtotal,

                'ahorro': ahorro

            })

        self.guardar()

        return items

    # ====================================================
    # CALCULAR TOTAL
    # ====================================================

    def obtener_total(self):

        total = Decimal('0.00')

        for item in self.obtener_items():

            total += item['subtotal']

        return total.quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )

    # ====================================================
    # CALCULAR AHORRO TOTAL
    # ====================================================

    def obtener_ahorro_total(self):

        ahorro = Decimal('0.00')

        for item in self.obtener_items():

            ahorro += item['ahorro']

        return ahorro.quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )

    # ====================================================
    # VACIAR CARRITO
    # ====================================================

    def vaciar(self):

        self.carrito = {}

        self.guardar()
