# tests/conftest.py
import os
import sys
from pathlib import Path

# Obtener la ruta absoluta a la raíz del proyecto
root_dir = Path(__file__).parent.parent

# Añadir la raíz del proyecto al path de Python
sys.path.insert(0, str(root_dir))

# Esto ayuda a depurar problemas de importación
print(f"Python path configurado: {sys.path}")
print(f"Directorio actual: {os.getcwd()}")