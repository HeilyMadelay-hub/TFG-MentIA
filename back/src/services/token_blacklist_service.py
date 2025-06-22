"""
Servicio de caché en memoria para tokens revocados.
En producción, esto debería usar Redis o una base de datos.
"""
from typing import Set, Optional
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

class TokenBlacklist:
    """
    Administrador de tokens revocados con limpieza automática
    """
    
    def __init__(self):
        self._revoked_tokens: Set[str] = set()
        self._token_expiry: dict[str, datetime] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Inicia la tarea de limpieza periódica"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("TokenBlacklist: Servicio de limpieza iniciado")
    
    async def stop(self):
        """Detiene la tarea de limpieza"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("TokenBlacklist: Servicio de limpieza detenido")
    
    def add_token(self, token_jti: str, expiry: datetime):
        """
        Agrega un token a la lista de revocados
        
        Args:
            token_jti: JTI (ID único) del token
            expiry: Fecha de expiración del token
        """
        self._revoked_tokens.add(token_jti)
        self._token_expiry[token_jti] = expiry
        logger.debug(f"Token agregado a blacklist: {token_jti}")
    
    def is_revoked(self, token_jti: str) -> bool:
        """Verifica si un token está revocado"""
        return token_jti in self._revoked_tokens
    
    async def _cleanup_loop(self):
        """Limpia tokens expirados cada hora"""
        while True:
            try:
                await asyncio.sleep(3600)  # Ejecutar cada hora
                self._cleanup_expired_tokens()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en limpieza de tokens: {str(e)}")
    
    def _cleanup_expired_tokens(self):
        """Elimina tokens que ya han expirado"""
        now = datetime.utcnow()
        expired_tokens = []
        
        for jti, expiry in self._token_expiry.items():
            if expiry < now:
                expired_tokens.append(jti)
        
        for jti in expired_tokens:
            self._revoked_tokens.discard(jti)
            del self._token_expiry[jti]
        
        if expired_tokens:
            logger.info(f"TokenBlacklist: {len(expired_tokens)} tokens expirados eliminados")
    
    def clear_all(self):
        """Limpia toda la blacklist (usar con cuidado)"""
        count = len(self._revoked_tokens)
        self._revoked_tokens.clear()
        self._token_expiry.clear()
        logger.warning(f"TokenBlacklist: Todos los tokens ({count}) fueron eliminados de la blacklist")
    
    async def is_blacklisted(self, token: str) -> bool:
        """
        Verifica si un token está en la blacklist extrayendo su JTI.
        
        Args:
            token: Token JWT completo
            
        Returns:
            bool: True si el token está en la blacklist
        """
        try:
            import jwt
            # Decodificar sin verificación para obtener JTI
            payload = jwt.decode(token, options={"verify_signature": False})
            jti = payload.get('jti')
            
            if not jti:
                return False
                
            return self.is_revoked(jti)
        except Exception:
            # Si hay cualquier error, asumir que el token no está en blacklist
            return False

# Instancia global
token_blacklist = TokenBlacklist()
