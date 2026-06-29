from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Avg

from .models import Purchase, PurchaseDetail
from .forms import PurchaseForm, PurchaseDetailFormSet
from billing.models import Product


# ============================================================
# CRUD DE PURCHASE  — Vistas Basadas en Funciones (FBV)
# Patrón análogo al de Invoice en la app billing.
# ============================================================

@login_required
def purchase_list(request):
    """Lista todas las compras.  Filtra opcionalmente por proveedor o año."""
    purchases = Purchase.objects.select_related('supplier').all()

    # --- Reto 3: filtros por proveedor y por año ---
    supplier_id = request.GET.get('supplier')
    if supplier_id and supplier_id.isdigit():
        purchases = purchases.filter(supplier_id=supplier_id)

    year = request.GET.get('year')
    if year and year.isdigit():
        purchases = purchases.filter(purchase_date__year=year)

    # Para el selector de proveedores en el filtro
    from billing.models import Supplier
    suppliers = Supplier.objects.filter(is_active=True)

    return render(request, 'purchasing/purchase_list.html', {
        'items': purchases,
        'suppliers': suppliers,
        'filters': request.GET,
    })


@login_required
def purchase_create(request):
    """Crea una compra con sus líneas de detalle y calcula subtotal / IVA / total."""
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        formset = PurchaseDetailFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # Guardar cabecera
            purchase = form.save(commit=False)
            purchase.save()

            # Asignar la compra al formset y guardar líneas
            formset.instance = purchase
            formset.save()

            # Calcular totales sobre las líneas guardadas
            subtotal = sum(d.subtotal for d in purchase.details.all())
            purchase.subtotal = subtotal
            purchase.tax = subtotal * Decimal('0.15')   # IVA 15%
            purchase.total = purchase.subtotal + purchase.tax
            purchase.save()

            # --- Reto 1: actualizar stock al confirmar la compra ---
            for detail in purchase.details.all():
                Product.objects.filter(pk=detail.product_id).update(
                    stock=F('stock') + detail.quantity
                )

            messages.success(
                request,
                f'Purchase #{purchase.id} created! Total: ${purchase.total}'
            )
            return redirect('purchasing:purchase_list')
    else:
        form = PurchaseForm()
        formset = PurchaseDetailFormSet()

    return render(request, 'purchasing/purchase_form.html', {
        'form': form,
        'formset': formset,
        'title': 'New Purchase',
    })


@login_required
def purchase_detail(request, pk):
    """Muestra el detalle completo de una compra."""
    purchase = get_object_or_404(
        Purchase.objects.select_related('supplier')
                        .prefetch_related('details__product'),
        pk=pk
    )

    # --- Reto 4: costo promedio por producto en esta compra ---
    avg_cost = purchase.details.aggregate(avg=Avg('unit_cost'))['avg']

    return render(request, 'purchasing/purchase_detail.html', {
        'purchase': purchase,
        'avg_cost': avg_cost,
    })


@login_required
def purchase_delete(request, pk):
    """Elimina una compra y todas sus líneas (CASCADE)."""
    purchase = get_object_or_404(Purchase, pk=pk)
    if request.method == 'POST':
        purchase_id = purchase.id
        purchase.delete()
        messages.success(request, f'Purchase #{purchase_id} deleted!')
        return redirect('purchasing:purchase_list')
    return render(request, 'purchasing/purchase_confirm_delete.html', {'object': purchase})
