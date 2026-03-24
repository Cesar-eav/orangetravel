import os
import sys

def force_debug():
    # Usamos flush=True para obligar a que aparezca en la consola de Railway
    print("\n" + "="*50, flush=True)
    print("🚀 MENSAJE DE CONSOLA: INICIANDO ORANGE TRAVEL", flush=True)
    print("="*50, flush=True)
    
    print(f"📂 Directorio: {os.getcwd()}", flush=True)
    print(f"🔌 Puerto Railway: {os.getenv('PORT')}", flush=True)
    
    if os.path.exists('config/wsgi.py'):
        print("✅ ARCHIVO WSGI ENCONTRADO", flush=True)
    else:
        print("❌ ERROR: NO SE ENCUENTRA config/wsgi.py", flush=True)
    
    print("="*50 + "\n", flush=True)

if __name__ == "__main__":
    force_debug()