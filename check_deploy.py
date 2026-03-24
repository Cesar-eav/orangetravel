import os
import sys

def debug():
    # El flush=True obliga a Railway a mostrar el texto de inmediato
    print("\n" + "*"*50, flush=True)
    print("🚀 HOLA CESAR! EL DIAGNÓSTICO ESTÁ CORRIENDO", flush=True)
    print("*"*50, flush=True)
    
    print(f"📁 Directorio actual: {os.getcwd()}", flush=True)
    print(f"🔌 Puerto asignado: {os.getenv('PORT')}", flush=True)
    
    # Verificamos si Django puede ver la base de datos
    db = os.getenv('DATABASE_URL')
    print(f"🛢️ DATABASE_URL detectada: {'SÍ' if db else 'NO'}", flush=True)

    print("*"*50 + "\n", flush=True)
    sys.stdout.flush() # Doble seguridad para que aparezca en el log

if __name__ == "__main__":
    debug()