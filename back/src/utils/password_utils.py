import hashlib
import os
import base64
import logging

# Para compatibilidad con hashes bcrypt antiguos
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

def hash_password(password: str) -> str:
    """Genera un hash PBKDF2 para la contraseña."""
    # Generar un salt aleatorio
    salt = os.urandom(16)
    
    # Generar el hash
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000  # Número de iteraciones
    )
    
    # Combinar salt y hash y convertir a formato legible
    storage = salt + key
    # Añadir prefijo para identificar el formato
    return "$pbkdf2$" + base64.b64encode(storage).decode('utf-8')

def verify_password(plain_password: str, stored_password: str) -> bool:
    """Verifica si la contraseña coincide con el hash almacenado."""
    
    # Comprobamos si es nuestro formato PBKDF2
    if stored_password.startswith("$pbkdf2$"):
        # Quitar el prefijo
        encoded = stored_password[8:]
        try:
            # Decodificar para obtener salt y key original
            storage = base64.b64decode(encoded.encode('utf-8'))
            salt = storage[:16]
            original_key = storage[16:]
            
            # Generar clave con mismos parámetros
            key = hashlib.pbkdf2_hmac(
                'sha256',
                plain_password.encode('utf-8'),
                salt,
                100000
            )
            
            # Comparar claves
            return key == original_key
        except Exception as e:
            logging.error(f"Error al verificar contraseña PBKDF2: {str(e)}")
            return False
    
    # Si es bcrypt (para compatibilidad con hashes existentes)
    elif stored_password.startswith('$2b$'):
        try:
            import bcrypt
            return bcrypt.checkpw(
                plain_password.encode('utf-8'), 
                stored_password.encode('utf-8')
            )
        except Exception as e:
            logging.error(f"Error al verificar contraseña bcrypt: {str(e)}")
            return False
            
    # Si no reconocemos el formato
    else:
        logging.warning(f"Formato de hash desconocido: {stored_password[:10]}...")
        return False