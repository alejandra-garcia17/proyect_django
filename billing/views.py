from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth import login
from .models import *
# ACTUALIZADO: Se añaden InvoiceForm e InvoiceDetailFormSet a los imports de formularios
from .forms import SignUpForm, BrandForm, InvoiceForm, InvoiceDetailFormSet
from shared.mixins import StaffRequiredMixin
from shared.decorators import audit_action
from shared.mixins import ExportFieldsMixin
from .forms import ProductForm
from .models import Product

# === REGISTRO ===
class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('billing:brand_list')
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

@login_required
def home(request):
    """Vista principal del sistema. Muestra resumen general."""
    context = {
        'total_brands': Brand.objects.count(),
        'total_products': Product.objects.count(),
        'total_customers': Customer.objects.count(),
        'total_invoices': Invoice.objects.count(),
        'recent_invoices': Invoice.objects.all()[:5],  # Últimas 5
        'low_stock': Product.objects.filter(stock__lte=5, is_active=True),
    }
    return render(request, 'billing/home.html', context)

# === BRAND (FBV) ===
@login_required
@audit_action('LIST_BRANDS')
def brand_list(request):
    brands = Brand.objects.all()
    return render(request, 'billing/brand_list.html', {'brands': brands})

@login_required
@audit_action('CREATE_BRAND')
def brand_create(request):
    if request.method == 'POST':
        form = BrandForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Brand created!')
            return redirect('billing:brand_list')
    else: form = BrandForm()
    return render(request, 'billing/brand_form.html', {'form':form, 'title':'Create Brand'})

@login_required
@audit_action('UPDATE_BRAND')
def brand_update(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, 'Brand updated!')
            return redirect('billing:brand_list')
    else: form = BrandForm(instance=brand)
    return render(request, 'billing/brand_form.html', {'form':form, 'title':'Edit Brand'})

@login_required
@audit_action('DELETE_BRAND')
def brand_delete(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        brand.delete()
        messages.success(request, 'Brand deleted!')
        return redirect('billing:brand_list')
    return render(request, 'billing/brand_confirm_delete.html', {'object': brand})

# === PRODUCTGROUP (CBV) ===
class ProductGroupListView(LoginRequiredMixin, ListView):
    model = ProductGroup; template_name = 'billing/productgroup_list.html'; context_object_name = 'items'
class ProductGroupCreateView(LoginRequiredMixin, CreateView):
    model = ProductGroup; fields = ['name','is_active']; template_name = 'billing/productgroup_form.html'; success_url = reverse_lazy('billing:productgroup_list')
class ProductGroupUpdateView(LoginRequiredMixin, UpdateView):
    model = ProductGroup; fields = ['name','is_active']; template_name = 'billing/productgroup_form.html'; success_url = reverse_lazy('billing:productgroup_list')

# NUEVO REEMPLAZO: ProductGroupDeleteView
class ProductGroupDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = ProductGroup
    template_name = 'billing/productgroup_confirm_delete.html'
    success_url = reverse_lazy('billing:productgroup_list')
    staff_redirect_url = '/groups/'

# === SUPPLIER (CBV) ===
class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier; template_name = 'billing/supplier_list.html'; context_object_name = 'items'
class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier; fields = ['name','contact_name','email','phone','address','is_active']; template_name = 'billing/supplier_form.html'; success_url = reverse_lazy('billing:supplier_list')
class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier; fields = ['name','contact_name','email','phone','address','is_active']; template_name = 'billing/supplier_form.html'; success_url = reverse_lazy('billing:supplier_list')

# NUEVO REEMPLAZO: SupplierDeleteView
class SupplierDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Supplier
    template_name = 'billing/supplier_confirm_delete.html'
    success_url = reverse_lazy('billing:supplier_list')
    staff_redirect_url = '/suppliers/'

# === PRODUCT (CBV) ===
class ProductListView(LoginRequiredMixin, ExportFieldsMixin, ListView):
    model = Product
    template_name = 'billing/product_list.html'
    context_object_name = 'items'
    paginate_by = 10
    export_filename = 'listado_productos'
    
    # Mapeo maestro e inmutable para mapear campos HTML vs Atributos del Modelo Django/Propiedades
    MASTER_COLUMNS = {
        'imagen': ('image', 'Imagen'),
        'name': ('name', 'Nombre del Producto'),
        'brand': ('brand__name', 'Marca'),
        'group': ('group__name', 'Grupo'),
        'price': ('unit_price', 'Precio Unitario'),
        'stock': ('stock', 'Existencias'),
        'balance': ('balance', 'Balance Total'),
        'status': ('is_active', 'Estado'),
    }

    def dispatch(self, request, *args, **kwargs):
        # Capturamos los campos visibles pasados dinámicamente por la URL/GET
        visible_cols_html = request.GET.getlist('visible_columns')
        
        if visible_cols_html:
            dynamic_fields = []
            dynamic_headers = []
            # Garantizamos mantener estrictamente el orden lógico definido en MASTER_COLUMNS
            for key, (field, header) in self.MASTER_COLUMNS.items():
                if key in visible_cols_html:
                    dynamic_fields.append(field)
                    dynamic_headers.append(header)
            
            if dynamic_fields:
                self.export_fields = dynamic_fields
                self.export_headers = dynamic_headers
        else:
            # Configuración por defecto si no viaja ningún parámetro
            self.export_fields = [v[0] for v in self.MASTER_COLUMNS.values()]
            self.export_headers = [v[1] for v in self.MASTER_COLUMNS.values()]
            
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Product.objects.select_related('brand', 'group').all().order_by('name')
        name_query = self.request.GET.get('search_name')
        if name_query: queryset = queryset.filter(name__icontains=name_query)

        brand_query = self.request.GET.get('search_brand')
        if brand_query and brand_query.isdigit(): queryset = queryset.filter(brand_id=brand_query)

        group_query = self.request.GET.get('search_group')
        if group_query and group_query.isdigit(): queryset = queryset.filter(group_id=group_query)

        price_min = self.request.GET.get('search_price_min')
        price_max = self.request.GET.get('search_price_max')
        if price_min: queryset = queryset.filter(unit_price__gte=price_min)
        if price_max: queryset = queryset.filter(unit_price__lte=price_max)

        stock_min = self.request.GET.get('search_stock_min')
        if stock_min and stock_min.isdigit(): queryset = queryset.filter(stock__gte=stock_min)

        active_query = self.request.GET.get('search_active')
        if active_query in ['true', 'false']: queryset = queryset.filter(is_active=(active_query == 'true'))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['brands'] = Brand.objects.all()
        context['groups'] = ProductGroup.objects.all()
        context['filters'] = self.request.GET
        return context

class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm  # 1. Enlazado al Formulario personalizado centralizado
    template_name = 'billing/product_form.html'
    success_url = reverse_lazy('billing:product_list')

    def form_valid(self, form):
        form.instance = form.save(commit=False)
        if self.request.FILES.get('image'):
            form.instance.image = self.request.FILES['image']
        return super().form_valid(form)

class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm  # 1. Enlazado al Formulario personalizado centralizado
    template_name = 'billing/product_form.html'
    success_url = reverse_lazy('billing:product_list')

    def form_valid(self, form):
        form.instance = form.save(commit=False)
        if self.request.FILES.get('image'):
            form.instance.image = self.request.FILES['image']
        return super().form_valid(form)

# NUEVA VISTA: Detalle del Producto
class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'billing/product_detail.html'
    context_object_name = 'product'

# NUEVO REEMPLAZO: ProductDeleteView
class ProductDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Product
    template_name = 'billing/product_confirm_delete.html'
    success_url = reverse_lazy('billing:product_list')
    staff_redirect_url = '/products/'

# === CUSTOMER (CBV) ===
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer; template_name = 'billing/customer_list.html'; context_object_name = 'items'
class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer; fields = ['dni','first_name','last_name','email','phone','address','is_active']; template_name = 'billing/customer_form.html'; success_url = reverse_lazy('billing:customer_list')
class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer; fields = ['dni','first_name','last_name','email','phone','address','is_active']; template_name = 'billing/customer_form.html'; success_url = reverse_lazy('billing:customer_list')

# NUEVO REEMPLAZO: CustomerDeleteView
class CustomerDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Customer
    template_name = 'billing/customer_confirm_delete.html'
    success_url = reverse_lazy('billing:customer_list')
    staff_redirect_url = '/customers/'

# =============================================
# CRUD DE INVOICE - VISTAS BASADAS EN FUNCIONES
# (Reemplazado el antiguo bloque CBV de Invoice)
# =============================================

@login_required
def invoice_list(request):
    """Lista todas las facturas con sus totales."""
    invoices = Invoice.objects.select_related('customer').all()
    return render(request, 'billing/invoice_list.html', {'items': invoices})


@login_required
def invoice_create(request):
    """Crea factura con sus líneas de detalle."""
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        formset = InvoiceDetailFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # Guardar factura (sin commit para asignar totales)
            invoice = form.save(commit=False)
            invoice.save()

            # Asignar la factura al formset y guardar detalles
            formset.instance = invoice
            details = formset.save()

            # Calcular totales
            subtotal = sum(d.subtotal for d in invoice.details.all())
            invoice.subtotal = subtotal
            invoice.tax = subtotal * Decimal('0.15')  # IVA 15%
            invoice.total = invoice.subtotal + invoice.tax
            invoice.save()

            messages.success(request, f'Invoice #{invoice.id} created! Total: ${invoice.total}')
            return redirect('billing:invoice_list')
    else:
        form = InvoiceForm()
        formset = InvoiceDetailFormSet()

    return render(request, 'billing/invoice_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Create Invoice',
    })


@login_required
def invoice_detail(request, pk):
    """Muestra el detalle completo de una factura."""
    invoice = get_object_or_404(
        Invoice.objects.select_related('customer')
                       .prefetch_related('details__product'),
        pk=pk
    )
    return render(request, 'billing/invoice_detail.html', {'invoice': invoice})


@login_required
def invoice_delete(request, pk):
    """Elimina una factura y todos sus detalles (CASCADE)."""
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        invoice_id = invoice.id
        invoice.delete()
        messages.success(request, f'Invoice #{invoice_id} deleted!')
        return redirect('billing:invoice_list')
    return render(request, 'billing/invoice_confirm_delete.html', {'object': invoice})


# === VISTA AUXILIAR PARA GENERAR DATOS DE PRUEBA ===
@login_required
def populate_database(request):
    try:
        # 1. Crear marcas y grupos
        samsung, _ = Brand.objects.get_or_create(name='Samsung', defaults={'description': 'Electronics'})
        apple, _ = Brand.objects.get_or_create(name='Apple')
        electronics, _ = ProductGroup.objects.get_or_create(name='Electronics')
        
        # 2. Crear proveedores
        dist, _ = Supplier.objects.get_or_create(name='TechDist', defaults={'email': 'info@tech.com'})
        global_s, _ = Supplier.objects.get_or_create(name='GlobalSupply')
        
        # 3. Crear producto y añadir proveedores
        phone, created = Product.objects.get_or_create(
            name='Galaxy S24', 
            brand=samsung, 
            group=electronics, 
            defaults={'unit_price': 999.99, 'stock': 50}
        )
        if created:
            phone.suppliers.add(dist, global_s)
        
        # 4. Crear cliente y su perfil
        client, _ = Customer.objects.get_or_create(
            dni='0912345678', 
            defaults={'first_name': 'Juan', 'last_name': 'Perez'}
        )
        
        if not CustomerProfile.objects.filter(customer=client).exists():
            CustomerProfile.objects.create(
                customer=client, 
                taxpayer_type='ruc', 
                payment_terms='credit_30', 
                credit_limit=5000
            )
        
        # 5. Factura y detalle
        inv = Invoice.objects.create(customer=client, subtotal=999.99, tax=120, total=1119.99)
        InvoiceDetail.objects.create(invoice=inv, product=phone, quantity=1, unit_price=phone.unit_price)
        
        messages.success(request, '¡Datos de prueba creados con éxito en la base de datos!')
    except Exception as e:
        messages.error(request, f'Hubo un problema al crear los datos: {e}')
        
    return redirect('billing:product_list')