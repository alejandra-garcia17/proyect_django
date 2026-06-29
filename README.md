<<<<<<< HEAD
# TecnoStock S.A. — Sales & Purchasing System

## Cómo la app `purchasing` reutiliza `Supplier` y `Product` de `billing`

La app **purchasing** no define sus propios modelos de proveedor ni de producto.
En cambio, importa directamente los ya existentes en la app `billing`:

```python
# purchasing/models.py
from billing.models import Supplier, Product
```

Esto significa que:

- **`Purchase`** enlaza a `Supplier` (de billing) mediante `ForeignKey` con `on_delete=PROTECT`,
  garantizando que no se pueda borrar un proveedor que tenga compras registradas.
- **`PurchaseDetail`** enlaza a `Product` (de billing) mediante `ForeignKey` con `on_delete=PROTECT`,
  de modo que los mismos productos del catálogo de ventas se usan para registrar
  adquisiciones sin duplicar datos.
- Cuando se confirma una compra, el campo `stock` de cada `Product` se incrementa
  automáticamente (reto 1), complementando la lógica inversa que hace `InvoiceDetail`
  al vender.

Esta reutilización evita duplicación de código, mantiene una única fuente de verdad
para proveedores y productos, y demuestra cómo Django permite relaciones entre apps
con una simple línea de importación.

## Estructura del proyecto

```
config/          — Configuración y URL raíz
billing/         — Ventas: Brand, ProductGroup, Supplier, Product, Customer, Invoice
purchasing/      — Compras: Purchase, PurchaseDetail (FK a billing)
```

## Ejecución

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Accede a `/purchases/` para gestionar el módulo de compras.
=======
### Instrucciones de Configuración

1. **Crear el entorno virtual:**
```bash
python -m venv env
env\Scripts\activate

pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate
python manage.py runserver

