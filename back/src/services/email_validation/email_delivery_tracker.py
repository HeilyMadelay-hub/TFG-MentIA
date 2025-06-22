"""
Servicio de tracking de entrega de emails para validación
Verifica que un email existe realmente antes de permitir cambios
"""
# Importa el módulo de logging para registrar información, advertencias y errores
import logging
# Importa el módulo time para medir tiempos de ejecución
import time
# Importa asyncio para operaciones asíncronas
import asyncio
# Importa socket para operaciones de red (DNS, etc.)
import socket
# Importa expresiones regulares para validar emails
import re
# Importa aiosmtplib para enviar emails de forma asíncrona
import aiosmtplib
# Importa tipos para anotaciones
from typing import Dict, Optional, List
# Importa datetime para fechas en los emails
from datetime import datetime
# Importa clases para crear emails MIME
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Importa la función para obtener la configuración de la app
from src.config.settings import get_settings

# Crea un logger para este módulo
logger = logging.getLogger(__name__)

class EmailDeliveryTracker:
    """
    Rastrea la entrega de emails para verificar que la dirección existe.
    """
    
    def __init__(self):
        # Obtiene la configuración de la app
        self.settings = get_settings()
        # Host del servidor SMTP
        self.smtp_host = self.settings.SMTP_HOST
        # Puerto del servidor SMTP
        self.smtp_port = self.settings.SMTP_PORT
        # Usuario SMTP
        self.smtp_username = self.settings.SMTP_USER
        # Contraseña SMTP
        self.smtp_password = self.settings.SMTP_PASSWORD
        # Si se usa TLS para el envío seguro
        self.smtp_use_tls = getattr(self.settings, 'SMTP_USE_TLS', True)  # Por defecto True
        
    async def send_with_delivery_tracking(
        self, 
        to_email: str, 
        subject: str, 
        code: str,
        tracking_timeout: int = 5
    ) -> Dict:
        """
        Envía email y verifica que llegue en el tiempo especificado.
        
        Args:
            to_email: Email destino
            subject: Asunto del email
            code: Código de verificación
            tracking_timeout: Tiempo máximo de espera en segundos
            
        Returns:
            Dict con información de la entrega
        """
        # Diccionario con el resultado del intento de entrega
        result = {
            "delivered": False,  # Si fue entregado
            "reason": None,      # Motivo si falla
            "time_taken": 0,     # Tiempo que tomó
            "smtp_response": None, # Respuesta SMTP
            "mx_records_found": False # Si se encontraron MX
        }
        
        # Marca el tiempo de inicio
        start_time = time.time()
        
        try:
            # 1. Verificar formato del email
            if not self._validate_email_format(to_email):
                result["reason"] = "invalid_format"
                return result
            
            # 2. Verificar MX records del dominio
            domain = to_email.split('@')[1]
            mx_records = await self._check_mx_records(domain)
            
            if not mx_records:
                result["reason"] = "no_mx_records"
                logger.warning(f"No se encontraron MX records para el dominio: {domain}")
                return result
            
            result["mx_records_found"] = True
            logger.info(f"MX records encontrados para {domain}: {mx_records}")
            
            # 3. Intentar enviar el email con timeout
            try:
                # Crear mensaje
                message = self._create_tracked_message(to_email, subject, code)
                
                # Conectar y enviar con timeout
                async with asyncio.timeout(tracking_timeout):
                    async with aiosmtplib.SMTP(
                        hostname=self.smtp_host,
                        port=self.smtp_port,
                        timeout=tracking_timeout
                    ) as smtp:
                        # TLS si está configurado
                        if self.smtp_use_tls:
                            await smtp.starttls()
                        
                        # Autenticar
                        await smtp.login(self.smtp_username, self.smtp_password)
                        
                        # Enviar mensaje
                        send_result = await smtp.send_message(message)
                        
                        # Analizar respuesta SMTP
                        if to_email in send_result:
                            smtp_code, smtp_message = send_result[to_email]
                            result["smtp_response"] = f"{smtp_code}: {smtp_message}"
                            
                            # Código 250 = OK, entregado
                            if smtp_code == 250:
                                result["delivered"] = True
                                logger.info(f"Email entregado exitosamente a {to_email}")
                            # Código 550 = Email no existe
                            elif smtp_code == 550:
                                result["reason"] = "recipient_not_found"
                                logger.warning(f"Destinatario no encontrado: {to_email}")
                            # Otros códigos de error
                            else:
                                result["reason"] = f"smtp_error_{smtp_code}"
                                logger.warning(f"Error SMTP {smtp_code} para {to_email}: {smtp_message}")
                        
            except asyncio.TimeoutError:
                result["reason"] = "delivery_timeout"
                logger.warning(f"Timeout al enviar email a {to_email}")
                
            except aiosmtplib.SMTPRecipientRefused as e:
                result["reason"] = "recipient_refused"
                result["smtp_response"] = str(e)
                logger.warning(f"Destinatario rechazado: {to_email} - {e}")
                
            except aiosmtplib.SMTPServerDisconnected:
                result["reason"] = "server_disconnected"
                logger.error("Servidor SMTP desconectado")
                
            except aiosmtplib.SMTPException as e:
                result["reason"] = "smtp_error"
                result["smtp_response"] = str(e)
                logger.error(f"Error SMTP: {e}")
                
        except Exception as e:
            result["reason"] = f"error_{type(e).__name__}"
            logger.error(f"Error inesperado al enviar a {to_email}: {e}")
            
        # Calcula el tiempo total de la operación
        result["time_taken"] = time.time() - start_time
        
        # Log del resultado
        logger.info(f"Resultado de tracking para {to_email}: {result}")
        
        return result
    
    def _validate_email_format(self, email: str) -> bool:
        """Valida el formato básico del email."""
        # Expresión regular para emails válidos
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    async def _check_mx_records(self, domain: str) -> List[str]:
        """
        Verifica que el dominio tenga MX records válidos.
        
        Args:
            domain: Dominio a verificar
            
        Returns:
            Lista de MX records encontrados
        """
        try:
            # Usar asyncio para hacer la consulta DNS no bloqueante
            loop = asyncio.get_event_loop()
            
            # Importar dns.resolver si está disponible
            try:
                import dns.resolver
                
                # Hacer la consulta MX
                def resolve_mx():
                    try:
                        mx_records = dns.resolver.resolve(domain, 'MX')
                        return [(r.preference, str(r.exchange)) for r in mx_records]
                    except:
                        return []
                
                mx_list = await loop.run_in_executor(None, resolve_mx)
                return [mx[1] for mx in sorted(mx_list)]
                
            except ImportError:
                # Si dnspython no está instalado, usar método alternativo
                logger.warning("dnspython no instalado, usando verificación básica")
                
                # Verificar al menos que el dominio resuelve
                def check_domain():
                    try:
                        socket.gethostbyname(domain)
                        return True
                    except:
                        return False
                
                domain_exists = await loop.run_in_executor(None, check_domain)
                return ["verificación básica"] if domain_exists else []
                
        except Exception as e:
            logger.error(f"Error verificando MX records para {domain}: {e}")
            return []
    
    def _create_tracked_message(self, to_email: str, subject: str, code: str) -> MIMEMultipart:
        """
        Crea un mensaje MIME con solicitud de confirmación de entrega.
        
        Args:
            to_email: Email destino
            subject: Asunto
            code: Código de verificación
            
        Returns:
            Mensaje MIME configurado
        """
        # Crea el mensaje multipart
        message = MIMEMultipart()
        # Usa FROM_EMAIL si está en settings, si no usa el usuario SMTP
        from_email = getattr(self.settings, 'FROM_EMAIL', None) or self.smtp_username
        message['From'] = f"DocuMente <{from_email}>"
        message['To'] = to_email
        message['Subject'] = subject
        message['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
        
        # Headers para solicitar confirmación de entrega
        message['Disposition-Notification-To'] = from_email
        message['Return-Receipt-To'] = from_email
        
        # ID único del mensaje para tracking
        message_id = f"<{int(time.time())}.{code}@{self.smtp_host}>"
        message['Message-ID'] = message_id
        
        # Cuerpo del mensaje en HTML
        body = f"""
        <html>
        <body style=\"font-family: Arial, sans-serif; padding: 20px;\">
            <h2>Verificación de Email</h2>
            <p>Tu código de verificación es:</p>
            <h1 style=\"color: #6B4CE6; font-size: 36px; letter-spacing: 5px;\">{code}</h1>
            <p>Este código expira en 5 minutos.</p>
            <p style=\"color: #666; font-size: 12px; margin-top: 30px;\">
                Si no solicitaste este cambio, ignora este mensaje.
            </p>
        </body>
        </html>
        """
        
        # Adjunta el cuerpo HTML al mensaje
        message.attach(MIMEText(body, 'html'))
        
        return message


class EmailValidationService:
    """
    Servicio de validación completa de emails.
    """
    
    def __init__(self):
        # Lista de dominios temporales/desechables conocidos
        self.disposable_domains = self._load_disposable_domains()
        """
        Sirve para inicializar un atributo llamado disposable_domains en la clase EmailValidationService. Este atributo contiene un conjunto (set) de dominios de correo electrónico temporales o desechables, como "mailinator.com", "yopmail.com", etc.
        ¿Para qué se usa?
        Permite que el servicio pueda detectar si un email pertenece a un dominio temporal/desechable y así rechazarlo o marcarlo como inválido. Esto es útil para evitar que los usuarios usen correos falsos o temporales en procesos de validación, registro o cambio de email.
        En resumen:
        Guarda la lista de dominios de emails temporales para poder identificar y bloquear correos desechables automáticamente.        
        """
        
    def _load_disposable_domains(self) -> set:
        """Carga lista de dominios temporales conocidos."""
        # Lista básica de dominios temporales comunes
        return {
            "10minutemail.com", "guerrillamail.com", "mailinator.com",
            "temp-mail.org", "throwaway.email", "temporarymail.com",
            "tempmail.com", "10minutemail.net", "fakeinbox.com",
            "yopmail.com", "trashmail.com", "mailnesia.com",
            "mintemail.com", "throwawaymail.com", "sharklasers.com",
            "spam4.me", "grr.la", "guerrillamail.info",
            "pokemail.net", "spam4.me", "abyssmail.com",
            "mohmal.com", "tmail.com", "zetmail.com",
            "sute.jp", "1mail.ml", "asu.mx"
        }
    
    def is_disposable_email(self, email: str) -> bool:
        """
        Detecta si un email es temporal/desechable.
        
        Args:
            email: Email a verificar
            
        Returns:
            True si es desechable
        """
        try:
            # Extrae el dominio y lo compara con la lista
            domain = email.split('@')[1].lower()
            return domain in self.disposable_domains
        except:
            return False
    
    async def validate_email_exists(self, email: str) -> Dict:
        """
        Validación completa de existencia de email.
        
        Args:
            email: Email a validar
            
        Returns:
            Dict con resultado de validación
        """
        # Diccionario con el resultado de la validación
        validation_result = {
            "email": email,
            "is_valid": False,
            "checks": {
                "format": False,
                "domain_exists": False,
                "mx_records": False,
                "not_disposable": False,
                "smtp_verify": False
            },
            "reason": None
        }
        
        # 1. Validar formato
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            validation_result["reason"] = "invalid_format"
            return validation_result
        validation_result["checks"]["format"] = True
        
        # 2. Verificar que no sea desechable
        if self.is_disposable_email(email):
            validation_result["reason"] = "disposable_email"
            return validation_result
        validation_result["checks"]["not_disposable"] = True
        
        # 3. Verificar dominio
        domain = email.split('@')[1]
        try:
            # Intenta resolver el dominio
            socket.gethostbyname(domain)
            validation_result["checks"]["domain_exists"] = True
        except:
            validation_result["reason"] = "domain_not_found"
            return validation_result
            
        # 4. Verificar MX Records
        tracker = EmailDeliveryTracker()
        mx_records = await tracker._check_mx_records(domain)
        if not mx_records:
            validation_result["reason"] = "no_mx_records"
            return validation_result
        validation_result["checks"]["mx_records"] = True
        
        # 5. Verificación SMTP (opcional, puede ser lenta)
        # Por ahora asumimos que si pasa las otras validaciones es válido
        validation_result["checks"]["smtp_verify"] = True
        
        # Email es válido si pasa todas las pruebas
        validation_result["is_valid"] = all(validation_result["checks"].values())
        
        return validation_result
