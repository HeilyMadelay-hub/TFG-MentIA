"""
Script para probar la conexión con la API de OpenAI
Verifica que el conector funciona correctamente.
"""
import sys
import os

# Añadir el directorio raíz del proyecto al path de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.ai_connector import get_openai_connector

def test_openai_connection():
    """Prueba la conexión con OpenAI"""
    print("Probando conexión con OpenAI...")
    
    # Verificar que la API key existe
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: No se encontró la variable de entorno OPENAI_API_KEY")
        print("Asegúrate de configurar esta variable en tu archivo .env")
        return False
        
    # Obtener el conector
    openai = get_openai_connector()
    
    try:
        # Prueba 1: Generar embeddings
        print("\n1. Probando generación de embeddings...")
        test_text = "Este es un texto de prueba para generar embeddings"
        embeddings = openai.create_embeddings([test_text])
        
        if embeddings and len(embeddings) > 0:
            print(f"✅ Embeddings generados correctamente")
            print(f"   Dimensionalidad: {len(embeddings[0])}")
        else:
            print("❌ Error al generar embeddings")
            return False
            
        # Prueba 2: Generar respuesta simple
        print("\n2. Probando generación de respuesta simple...")
        messages = [
            {"role": "system", "content": "Eres un asistente útil y conciso."},
            {"role": "user", "content": "Saluda en una sola frase."}
        ]
        response = openai.generate_chat_completion(messages, max_tokens=50)
        
        if response:
            print(f"✅ Respuesta generada correctamente:")
            print(f"   \"{response}\"")
        else:
            print("❌ Error al generar respuesta")
            return False
            
        # Prueba 3: Generar respuesta RAG
        print("\n3. Probando generación de respuesta RAG...")
        context = [
            "Madrid es la capital de España y tiene aproximadamente 3.3 millones de habitantes.",
            "Barcelona es la segunda ciudad más grande de España y un importante centro turístico."
        ]
        query = "¿Cuál es la segunda ciudad mas grande de España?"
        
        rag_response = openai.generate_rag_response(query=query, context=context)
        
        if rag_response:
            print(f"✅ Respuesta RAG generada correctamente:")
            print(f"   \"{rag_response}\"")
        else:
            print("❌ Error al generar respuesta RAG")
            return False
            
        print("\n✅ Todas las pruebas completadas exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error durante las pruebas: {str(e)}")
        return False

if __name__ == "__main__":
    test_openai_connection()