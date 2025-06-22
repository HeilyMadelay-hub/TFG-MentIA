#!/usr/bin/env python3
"""
Script simple para verificar si ChromaDB está corriendo
"""

import requests
import sys

def check_chromadb():
    try:
        # Intentar conectar a ChromaDB
        response = requests.get("http://localhost:8050/api/v1/heartbeat", timeout=5)
        if response.status_code == 200:
            print("✅ ChromaDB está ejecutándose correctamente en puerto 8050")
            return True
        else:
            print(f"❌ ChromaDB responde pero con código {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
            # Probar endpoint alternativo
            print("\n🔄 Probando endpoint alternativo...")
            alt_response = requests.get("http://localhost:8050/api/v1", timeout=5)
            print(f"   Código: {alt_response.status_code}")
            if alt_response.status_code == 200:
                print("   ✅ ChromaDB está activo en endpoint alternativo")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar a ChromaDB en puerto 8050")
        print("   ¿Está ChromaDB ejecutándose?")
        return False
    except requests.exceptions.Timeout:
        print("❌ Timeout conectando a ChromaDB")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    check_chromadb()
