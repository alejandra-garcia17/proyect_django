### Instrucciones de Configuración

1. **Crear el entorno virtual:**
```bash
python -m venv env
env\Scripts\activate

pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate
python manage.py runserver
