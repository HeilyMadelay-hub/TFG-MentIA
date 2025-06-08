"""
Utilidades para validación de permisos administrativos.
Contiene funciones que simplifican la verificación de roles y permisos.
"""
from src.models.domain import User
from typing import Optional

def has_admin_privileges(user: User) -> bool:
    """
    Verifica si un usuario tiene privilegios de administrador.
    Considera tanto el flag is_admin como si es el usuario HEILY.
    
    Args:
        user: Usuario a verificar
        
    Returns:
        bool: True si tiene privilegios de administrador
    """
    if user is None:
        return False
        
    # Ivan siempre debe tener privilegios de admin
    if user.username and user.username.upper() == "Ivan":
        return True
        
    # Otros usuarios solo si tienen el flag is_admin
    return user.is_admin

def ensure_admin_status(user: User) -> User:
    """
    Asegura que Ivan tenga siempre estatus de administrador.
    Modifica el objeto user si es necesario.
    
    Args:
        user: Usuario a verificar/modificar
        
    Returns:
        User: Usuario con estatus actualizado si corresponde
    """
    if user and user.username and user.username.upper() == "Ivan":
        user.is_admin = True
        
    return user

is_administrator = has_admin_privileges