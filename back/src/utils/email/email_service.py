"""
Servicio de email para envío de notificaciones.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class EmailService:
    """Servicio para envío de emails usando SMTP."""
    
    def __init__(self):
        # Configuración SMTP (Gmail example)
        self.smtp_host = settings.SMTP_HOST or "smtp.gmail.com"
        self.smtp_port = settings.SMTP_PORT or 587
        self.smtp_user = settings.SMTP_USER  # tu-email@gmail.com
        self.smtp_password = settings.SMTP_PASSWORD  # contraseña de aplicación
        self.from_email = settings.FROM_EMAIL or self.smtp_user
        self.app_name = "DocumenteMe Chatbot"
    
    def send_email(self, to_email: str, subject: str, body_html: str, body_text: Optional[str] = None) -> bool:
        """
        Envía un email usando SMTP.
        
        Args:
            to_email: Email destinatario
            subject: Asunto del email
            body_html: Cuerpo del email en HTML
            body_text: Cuerpo del email en texto plano (opcional)
            
        Returns:
            bool: True si el email fue enviado exitosamente
        """
        try:
            # Si no hay configuración SMTP, solo loguear (modo desarrollo)
            if not self.smtp_user or not self.smtp_password:
                logger.warning(f"SMTP no configurado. Email simulado a {to_email}")
                logger.info(f"Asunto: {subject}")
                logger.info(f"Contenido: {body_text or 'Ver HTML'}")
                return True
            
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.app_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Agregar versión texto
            if body_text:
                part1 = MIMEText(body_text, 'plain')
                msg.attach(part1)
            
            # Agregar versión HTML
            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)
            
            # Conectar y enviar
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email enviado exitosamente a {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar email a {to_email}: {str(e)}")
            return False
    
    def send_password_reset_email(self, to_email: str, username: str, reset_token: str) -> bool:
        """
        Envía email de restablecimiento de contraseña.
        """
        # URL con el token en el parámetro
        reset_url = f"{settings.FRONTEND_URL}/?token={reset_token}"
        
        subject = f"Restablecer contraseña - {self.app_name}"
        
        body_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Hola {username},</h2>
                <p>Recibimos una solicitud para restablecer tu contraseña.</p>
                <p>Haz clic en el siguiente botón para crear una nueva contraseña:</p>
                <p style="margin: 30px 0; text-align: center;">
                    <a href="{reset_url}" 
                       style="background-color: #4CAF50; color: white; padding: 15px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;
                              font-weight: bold; font-size: 16px;">
                        Restablecer Contraseña
                    </a>
                </p>
                <p style="color: #666; font-size: 14px;">
                    Si el botón no funciona, visita tu cuenta y usa la opción de "Olvidé mi contraseña".
                </p>
                <p><strong>Este enlace expirará en 1 hora.</strong></p>
                <p>Si no solicitaste este cambio, puedes ignorar este email con seguridad.</p>
                <hr>
                <p style="color: #999; font-size: 12px;">
                    {self.app_name} - Sistema de Gestión Documental<br>
                    Este es un mensaje automático, por favor no respondas a este email.
                </p>
            </body>
        </html>
        """
        
        body_text = f"""
        Hola {username},
        
        Recibimos una solicitud para restablecer tu contraseña.
        
        Para crear una nueva contraseña, visita tu cuenta en {self.app_name}.
        
        Este enlace expirará en 1 hora.
        
        Si no solicitaste este cambio, puedes ignorar este email.
        
        {self.app_name}
        """
        
        return self.send_email(to_email, subject, body_html, body_text)
    
    def send_email_verification(self, to_email: str, username: str, verification_token: str) -> bool:
        """
        Envía email de verificación de cuenta.
        """
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        subject = f"Verifica tu email - {self.app_name}"
        
        body_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>¡Bienvenido {username}!</h2>
                <p>Gracias por registrarte en {self.app_name}.</p>
                <p>Por favor, verifica tu dirección de email haciendo clic en el siguiente enlace:</p>
                <p style="margin: 20px 0;">
                    <a href="{verify_url}" 
                       style="background-color: #2196F3; color: white; padding: 10px 20px; 
                              text-decoration: none; border-radius: 5px;">
                        Verificar Email
                    </a>
                </p>
                <p>O copia y pega este enlace en tu navegador:</p>
                <p style="background-color: #f5f5f5; padding: 10px; word-break: break-all;">
                    {verify_url}
                </p>
                <hr>
                <p style="color: #666; font-size: 12px;">
                    {self.app_name} - Sistema de Gestión Documental
                </p>
            </body>
        </html>
        """
        
        body_text = f"""
        ¡Bienvenido {username}!
        
        Gracias por registrarte en {self.app_name}.
        
        Por favor, verifica tu email usando este enlace:
        {verify_url}
        
        {self.app_name}
        """
        
        return self.send_email(to_email, subject, body_html, body_text)

# Instancia singleton
email_service = EmailService()
