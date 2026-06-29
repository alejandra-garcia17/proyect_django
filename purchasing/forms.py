from django import forms
from django.forms import inlineformset_factory
from .models import Purchase, PurchaseDetail
from django.core.exceptions import ValidationError

class PurchaseForm(forms.ModelForm):
    """Formulario para cabecera de compra."""
    class Meta:
        model = Purchase
        fields = ['supplier', 'document_number']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'document_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. FAC-0001',
            }),
        }
        
        def clean(self):
            cleaned_data = super().clean()

            supplier = cleaned_data.get("supplier")
            document_number = cleaned_data.get("document_number")

            if supplier and document_number:
                existe = Purchase.objects.filter(
                    supplier=supplier,
                    document_number=document_number
                )

                # Permite editar el mismo registro
                if self.instance.pk:
                    existe = existe.exclude(pk=self.instance.pk)

                if existe.exists():
                    raise ValidationError(
                        "Ya existe una compra registrada con ese número de documento para este proveedor."
                    )

            return cleaned_data

PurchaseDetailFormSet = inlineformset_factory(
    Purchase,
    PurchaseDetail,
    fields=["product", "quantity", "unit_cost"],
    extra=3,
    can_delete=True
)

# Formset inline: permite agregar MÚLTIPLES líneas de producto dentro de UNA compra
PurchaseDetailFormSet = inlineformset_factory(
    Purchase,          # Modelo padre
    PurchaseDetail,    # Modelo hijo
    fields=['product', 'quantity', 'unit_cost'],
    extra=3,           # 3 filas vacías para agregar
    can_delete=True,   # Checkbox para eliminar filas
    widgets={
        'product': forms.Select(attrs={'class': 'form-select'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
    }
)
