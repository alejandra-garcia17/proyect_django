"""
============================================================
  orm.py  —  Referencia de consultas ORM del proyecto
             TecnoStock S.A. (billing + purchasing)
============================================================

Este archivo NO se ejecuta directamente con `python orm.py`.
Está pensado para leerlo, copiarlo al shell interactivo de Django:

    python manage.py shell

...y pegarlo sentencia por sentencia para ver los resultados.

Todas las importaciones necesarias están al inicio de cada sección.
============================================================
"""

# ============================================================
# 0. IMPORTACIONES  (copiar al inicio del shell)
# ============================================================
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from decimal import Decimal
from django.db.models import F, Avg, Sum, Count, Q

from billing.models import (
    Brand, ProductGroup, Supplier, Product,
    Customer, CustomerProfile, Invoice, InvoiceDetail,
)
from purchasing.models import Purchase, PurchaseDetail


# ============================================================
# 1. OPERACIONES BÁSICAS  —  all(), count(), create()
# ============================================================

# --- 1.1  all() ---
# Trae TODOS los registros de la tabla.
# Devuelve un QuerySet; no ejecuta la SQL hasta que se itera o se evalúa.
brands = Brand.objects.all()

# --- 1.2  count() ---
# Ejecuta  SELECT COUNT(*) FROM billing_brand
# Devuelve un entero, no un QuerySet.
total_brands    = Brand.objects.count()
total_products  = Product.objects.count()
total_customers = Customer.objects.count()
total_invoices  = Invoice.objects.count()

# --- 1.3  create() ---
# Inserta UNA fila en la tabla y devuelve el objeto creado.
# Equivale a:  obj = Model(); obj.campo = valor; obj.save()
inv = Invoice.objects.create(
    customer_id=1,      # FK: se puede pasar el id directamente
    subtotal=Decimal('100.00'),
    tax=Decimal('15.00'),
    total=Decimal('115.00'),
)

InvoiceDetail.objects.create(
    invoice=inv,        # FK: se puede pasar el objeto completo
    product_id=1,
    quantity=2,
    unit_price=Decimal('50.00'),
)


# ============================================================
# 2. FILTROS  —  filter(), exclude()
# ============================================================

# --- 2.1  filter() con campo exacto ---
# WHERE is_active = TRUE
active_suppliers = Supplier.objects.filter(is_active=True)

# --- 2.2  filter() con lookup  __lte  (less than or equal) ---
# WHERE stock <= 5  AND  is_active = TRUE
# Los dos argumentos dentro de filter() se unen con AND automáticamente.
low_stock = Product.objects.filter(stock__lte=5, is_active=True)

# --- 2.3  filter() con lookup  __gte  (greater than or equal) ---
# WHERE unit_price >= 100
products_expensive = Product.objects.filter(unit_price__gte=Decimal('100'))

# --- 2.4  filter() con lookup  __icontains  (LIKE %valor% sin case-sensitive) ---
# WHERE LOWER(name) LIKE '%galaxy%'
products_search = Product.objects.filter(name__icontains='galaxy')

# --- 2.5  filter() por FK usando el id directamente  (brand_id=2) ---
# WHERE brand_id = 2
# Django genera el campo brand_id automáticamente al definir la FK brand.
products_by_brand = Product.objects.filter(brand_id=2)

# --- 2.6  filter() por año usando lookup  __year ---
# WHERE EXTRACT(year FROM purchase_date) = 2025
purchases_2025 = Purchase.objects.filter(purchase_date__year=2025)

# --- 2.7  filter() con lookup  __range  (BETWEEN) ---
# WHERE purchase_date BETWEEN '2025-01-01' AND '2025-06-30'
from datetime import date
purchases_range = Purchase.objects.filter(
    purchase_date__range=(date(2025, 1, 1), date(2025, 6, 30))
)

# --- 2.8  exclude() ---
# Inverso de filter(): trae todo lo que NO cumpla la condición.
# WHERE is_active != FALSE  →  trae solo los activos
inactive_products = Product.objects.exclude(is_active=True)


# ============================================================
# 3. SLICING  —  limitar resultados como paginación
# ============================================================

# Trae solo las primeras 5 facturas.
# Equivale a  SELECT … LIMIT 5
# El Meta ordering = ['-invoice_date'] garantiza que sean las más recientes.
recent_invoices = Invoice.objects.all()[:5]

# Trae registros del 6 al 10 (offset 5, limit 5)
# SELECT … LIMIT 5 OFFSET 5
page_2 = Invoice.objects.all()[5:10]


# ============================================================
# 4. ORDENAMIENTO  —  order_by()
# ============================================================

# Orden ascendente por nombre (el prefijo '-' indica descendente)
products_asc  = Product.objects.all().order_by('name')
products_desc = Product.objects.all().order_by('-unit_price')

# Orden múltiple: primero por proveedor, luego fecha más reciente
purchases_ordered = Purchase.objects.all().order_by('supplier__name', '-purchase_date')


# ============================================================
# 5. OPTIMIZACIÓN DE CONSULTAS  —  select_related / prefetch_related
# ============================================================

# --- 5.1  select_related()  —  para relaciones FK y OneToOne ---
# Hace un SQL JOIN en una sola consulta en lugar de N+1 consultas.
# Úsalo cuando vas a acceder a campos del objeto relacionado (ej. invoice.customer.first_name).
invoices = Invoice.objects.select_related('customer').all()

# También puedes encadenar varias FK:
products = Product.objects.select_related('brand', 'group').all().order_by('name')

# --- 5.2  prefetch_related()  —  para relaciones ManyToMany y FK inversas ---
# Hace consultas separadas y las une en Python (más eficiente que N+1 para M2M).
# Útil para recorrer   invoice.details.all()  sin golpear la BD en cada iteración.
invoice_with_details = (
    Invoice.objects
    .select_related('customer')            # JOIN con customer (FK directa)
    .prefetch_related('details__product')  # prefetch detalle y su producto (FK inversa + FK)
    .get(pk=1)
)

# Versión de purchasing:
purchase_with_details = (
    Purchase.objects
    .select_related('supplier')
    .prefetch_related('details__product')
    .get(pk=1)
)


# ============================================================
# 6. OBTENER UN SOLO OBJETO  —  get(), get_or_404
# ============================================================

# get() lanza DoesNotExist si no encuentra nada, o MultipleObjectsReturned si hay más de uno.
brand = Brand.objects.get(pk=1)
brand_by_name = Brand.objects.get(name='Samsung')

# En las vistas usamos get_object_or_404() que devuelve HTTP 404 en lugar de excepción:
# purchase = get_object_or_404(Purchase, pk=pk)


# ============================================================
# 7. GET OR CREATE  —  get_or_create()
# ============================================================

# Busca un registro; si no existe, lo crea.
# Devuelve una TUPLA: (objeto, created)
#   created = True  → se creó ahora
#   created = False → ya existía y se devolvió el existente

samsung, created = Brand.objects.get_or_create(
    name='Samsung',                          # campo de búsqueda
    defaults={'description': 'Electronics'} # valores solo si se VA A CREAR
)

# Si 'Samsung' ya existía, 'defaults' se ignora; no se sobreescriben datos.
supplier, _ = Supplier.objects.get_or_create(name='TechDist', defaults={'email': 'info@tech.com'})

# El guión bajo (_) descarta el booleano 'created' cuando no nos interesa.


# ============================================================
# 8. EXISTS()  —  verificar existencia sin traer datos
# ============================================================

# Ejecuta  SELECT 1 FROM … LIMIT 1  (muy rápido, no hidrata objetos Python).
# Retorna True o False.
has_profile = CustomerProfile.objects.filter(customer_id=1).exists()

if not has_profile:
    CustomerProfile.objects.create(
        customer_id=1,
        taxpayer_type='ruc',
        payment_terms='credit_30',
        credit_limit=Decimal('5000.00'),
    )


# ============================================================
# 9. UPDATE ATÓMICO  —  update() con F()
# ============================================================

# --- 9.1  update() básico ---
# Actualiza directamente en la BD sin traer el objeto a Python.
# Útil para actualizar muchos registros a la vez.
# Devuelve el número de filas afectadas.
Brand.objects.filter(name='Apple').update(is_active=False)

# --- 9.2  F()  —  referencias a campos en el mismo UPDATE ---
# F('stock') refiere al valor ACTUAL en la BD, no al que Python tiene en memoria.
# Esto evita condiciones de carrera: la operación es atómica en la BD.
# Equivale a:  UPDATE billing_product SET stock = stock + 10 WHERE id = 1
Product.objects.filter(pk=1).update(stock=F('stock') + 10)

# En el reto de compras: al confirmar una compra sumamos la cantidad de cada línea:
# Product.objects.filter(pk=detail.product_id).update(stock=F('stock') + detail.quantity)


# ============================================================
# 10. AGREGACIONES  —  aggregate() y annotate()
# ============================================================

# aggregate() retorna un diccionario con el resultado; NO un QuerySet.

# --- 10.1  Avg  (promedio) ---
# Costo promedio de todas las líneas de una compra específica
avg_cost = PurchaseDetail.objects.filter(purchase_id=1).aggregate(avg=Avg('unit_cost'))
# {'avg': Decimal('45.50')}

# Accedemos al valor así:
valor = avg_cost['avg']

# --- 10.2  Sum  (suma total) ---
# Suma de todos los subtotales de las líneas de una compra
total_subtotal = PurchaseDetail.objects.filter(purchase_id=1).aggregate(total=Sum('subtotal'))

# También lo usamos al calcular el total de una factura:
# subtotal = sum(d.subtotal for d in invoice.details.all())   ← Python puro
# subtotal = invoice.details.aggregate(total=Sum('subtotal'))['total']  ← SQL

# --- 10.3  Count  (conteo) ---
total_compras = Purchase.objects.aggregate(total=Count('id'))

# --- 10.4  annotate()  —  agrega un campo calculado a CADA fila del QuerySet ---
# Devuelve un QuerySet enriquecido; útil para listas.
from django.db.models import Count
suppliers_with_count = Supplier.objects.annotate(
    num_purchases=Count('purchases')  # 'purchases' viene del related_name en Purchase.supplier
)
# Ahora cada objeto supplier tiene el atributo .num_purchases


# ============================================================
# 11. RELACIONES M2M  —  Many-to-Many (Product ↔ Supplier)
# ============================================================

product = Product.objects.get(pk=1)

# Agregar proveedores al producto
supplier1 = Supplier.objects.get(pk=1)
supplier2 = Supplier.objects.get(pk=2)
product.suppliers.add(supplier1, supplier2)

# Consultar los proveedores de un producto
proveedores = product.suppliers.all()

# Relación inversa: productos de un proveedor
productos_del_proveedor = supplier1.products.all()

# Eliminar una relación M2M (no borra los objetos, solo el vínculo)
product.suppliers.remove(supplier1)

# Reemplazar todos los proveedores de una vez
product.suppliers.set([supplier2])


# ============================================================
# 12. RECORRIDO POR RELACIONES INVERSAS  (related_name)
# ============================================================

# related_name='details' en InvoiceDetail.invoice
# Permite acceder desde la cabecera a sus líneas sin consulta extra (si usamos prefetch).
invoice = Invoice.objects.prefetch_related('details__product').get(pk=1)
for detail in invoice.details.all():
    print(detail.product.name, detail.quantity, detail.subtotal)

# related_name='purchases' en Purchase.supplier
# Permite ver todas las compras de un proveedor desde el objeto supplier
supplier = Supplier.objects.prefetch_related('purchases').get(pk=1)
for compra in supplier.purchases.all():
    print(compra.document_number, compra.total)


# ============================================================
# 13. FILTROS ENCADENADOS  (QuerySet es lazy)
# ============================================================

# Los QuerySets se pueden encadenar; la SQL se construye pero NO se ejecuta
# hasta que se itera, se llama len(), se convierte a lista, etc.
# Esto se llama "evaluación perezosa" (lazy evaluation).

qs = Purchase.objects.select_related('supplier').all()   # aún no va a la BD

qs = qs.filter(supplier_id=1)      # agrega WHERE
qs = qs.filter(purchase_date__year=2025)   # agrega AND

# Ahora SÍ se ejecuta la SQL (al iterar en el template o en un for):
for p in qs:
    print(p.id, p.total)


# ============================================================
# 14. CONSULTAS CON  Q()  —  condiciones OR / NOT
# ============================================================

# Q() permite combinar condiciones con OR (|) o NOT (~)
# filter() normal solo hace AND.

# Productos de la marca 1 O con stock mayor a 100
from django.db.models import Q
productos_q = Product.objects.filter(
    Q(brand_id=1) | Q(stock__gt=100)
)

# Proveedores activos con email O con teléfono (alguno de los dos)
proveedores_con_contacto = Supplier.objects.filter(
    Q(email__isnull=False) | Q(phone__isnull=False),
    is_active=True
)


# ============================================================
# 15. RESUMEN  —  Tabla de lookups de campo usados en el proyecto
# ============================================================
#
#  Lookup          SQL equivalente           Ejemplo
# ─────────────────────────────────────────────────────────────
#  __exact         =  (default)             filter(name='Samsung')
#  __iexact        = LOWER(…)              filter(name__iexact='samsung')
#  __icontains     LIKE %…% (sin case)     filter(name__icontains='gal')
#  __lte           <=                       filter(stock__lte=5)
#  __gte           >=                       filter(unit_price__gte=100)
#  __lt            <                        filter(stock__lt=1)
#  __gt            >                        filter(stock__gt=100)
#  __year          EXTRACT(year FROM …)     filter(purchase_date__year=2025)
#  __range         BETWEEN … AND …          filter(date__range=(d1, d2))
#  __isnull        IS NULL / IS NOT NULL    filter(email__isnull=False)
#  __in            IN (…)                   filter(pk__in=[1, 2, 3])
# ─────────────────────────────────────────────────────────────
#
#  Método          Qué hace                         Devuelve
# ─────────────────────────────────────────────────────────────
#  .all()          todos los registros              QuerySet
#  .filter(…)      filas que cumplen condición      QuerySet
#  .exclude(…)     filas que NO cumplen             QuerySet
#  .order_by(…)    ordena (- = desc)                QuerySet
#  .select_related FK/O2O en un JOIN                QuerySet
#  .prefetch_rel.  M2M / FK inversas                QuerySet
#  .get(…)         un solo objeto (lanza exc)       Objeto
#  .get_or_create  obtiene o crea                   (Objeto, bool)
#  .create(…)      inserta y devuelve               Objeto
#  .update(…)      UPDATE masivo                    int (filas)
#  .delete()       DELETE                           (int, dict)
#  .count()        SELECT COUNT(*)                  int
#  .exists()       SELECT 1 LIMIT 1                 bool
#  .aggregate(…)   función agregada global           dict
#  .annotate(…)    función agregada por fila        QuerySet
#  [:n]            LIMIT n                          QuerySet
#  [n:m]           LIMIT (m-n) OFFSET n             QuerySet
# ─────────────────────────────────────────────────────────────
