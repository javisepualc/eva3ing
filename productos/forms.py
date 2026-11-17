from django import forms
from .models import Producto, Descuento, Gasto


# ====================================================
# FORMULARIO DE PRODUCTOS
# ====================================================

class ProductoForm(forms.ModelForm):

    class Meta:
        model = Producto
        fields = [
            'codigo',
            'nombre',
            'categoria',
            'descripcion',
            'precio_costo',
            'precio',
            'stock',
            'stock_minimo',
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 7801234567890'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del producto'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Descripción del producto'
            }),
            'precio_costo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': '0'
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1',
                'placeholder': '0'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'stock_minimo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
        }

    def clean_nombre(self):
        nombre = (self.cleaned_data.get('nombre') or '').strip()
        if len(nombre) < 2:
            raise forms.ValidationError('El nombre debe tener al menos 2 caracteres.')
        qs = Producto.objects.filter(nombre__iexact=nombre)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe un producto registrado con este nombre.')
        return nombre

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is None or precio <= 0:
            raise forms.ValidationError('El precio de venta debe ser mayor a $0.')
        return precio


# ====================================================
# FORMULARIO DE DESCUENTOS
# ====================================================

class DescuentoForm(forms.ModelForm):

    class Meta:
        model = Descuento
        fields = [
            'nombre',
            'tipo',
            'productos',
            'porcentaje',
            'lleve_a',
            'pague_b',
            'activo'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la promoción'
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'productos': forms.CheckboxSelectMultiple(),
            'porcentaje': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.01',
                'max': '100',
                'step': '0.01',
                'placeholder': 'Ej: 15'
            }),
            'lleve_a': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Ej: 3'
            }),
            'pague_b': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Ej: 2'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_productos(self):
        productos = self.cleaned_data.get('productos')
        if not productos or not productos.exists():
            raise forms.ValidationError(
                'Debes seleccionar al menos un producto para la oferta.'
            )
        return productos


# ====================================================
# FORMULARIO DE GASTOS
# ====================================================

class GastoForm(forms.ModelForm):

    class Meta:
        model = Gasto
        fields = [
            'fecha',
            'categoria',
            'tipo_comprobante',
            'nro_comprobante',
            'motivo',
            'monto',
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select'
            }),
            'tipo_comprobante': forms.Select(attrs={
                'class': 'form-select'
            }),
            'nro_comprobante': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Factura #45920'
            }),
            'motivo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción del gasto'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1',
                'placeholder': 'Ej: 25000'
            }),
        }

    def clean_motivo(self):
        motivo = (self.cleaned_data.get('motivo') or '').strip()
        if len(motivo) < 3:
            raise forms.ValidationError('Ingrese un motivo válido (mínimo 3 caracteres).')
        return motivo

    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        if monto is None or monto <= 0:
            raise forms.ValidationError('El monto del gasto debe ser mayor a $0.')
        return monto
