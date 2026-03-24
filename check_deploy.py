import os
import sys
import django

def debug_railway():
    print("\n--- 🔍 DIAGNÓSTICO DE ORANGE TRAVEL ---")
    
    # 1. Ruta actual y Archivos
    print(f"📍 Directorio actual: {os.getcwd()}")
    print(f"📂 Archivos en raíz: {os.listdir('.')}")
    
    # 2. Verificación de Carpeta Config
    if os.path.exists('config/wsgi.py'):
        print("✅ Carpeta 'config' y 'wsgi.py' detectados.")
    else:
        print("❌ ERROR: No se encuentra 'config/wsgi.py'. Revisa el nombre de la carpeta.")

    # 3. Verificación de Librerías
    try:
        import gunicorn
        print(f"✅ Gunicorn instalado (Versión: {gunicorn.__version__})")
        import whitenoise
        print("✅ Whitenoise instalado.")
    except ImportError as e:
        print(f"❌ ERROR DE LIBRERÍA: {e}")

    # 4. Verificación de Variables de Entorno
    db_url = os.getenv('DATABASE_URL')
    port = os.getenv('PORT')
    print(f"🛢️ DATABASE_URL configurada: {'SÍ' if db_url else 'NO'}")
    print(f"🔌 PORT configurado: {port if port else '8000 (Default)'}")

    # 5. Intento de Importar WSGI (Lo que hace Gunicorn)
    try:
        sys.path.append(os.getcwd())
        from config.wsgi import application
        print("✅ WSGI Application cargada correctamente.")
    except Exception as e:
        print(f"❌ ERROR AL CARGAR WSGI: {e}")

if __name__ == "__main__":
    debug_railway()