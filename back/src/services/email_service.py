"""
Servicio para envío de emails
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import Optional
from datetime import datetime
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

class EmailService:
    """
    Servicio para enviar emails usando SMTP
    """
    
    def __init__(self):
        self.settings = get_settings()
        # Configurar estos valores en tu .env
        import os
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@chatbot.com")
        self.app_name = "DocuMente"
        self.app_url = os.getenv("FRONTEND_URL", "http://localhost:53793")
        
        # Log de configuración para debug
        logger.info(f"📧 Email Service configurado:")
        logger.info(f"  - SMTP Host: {self.smtp_host}")
        logger.info(f"  - SMTP Port: {self.smtp_port}")
        logger.info(f"  - SMTP User: {self.smtp_user[:5]}..." if self.smtp_user else "  - SMTP User: No configurado")
        logger.info(f"  - From Email: {self.from_email}")
        logger.info(f"  - App URL: {self.app_url}")
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """
        Envía un email
        """
        try:
            # Si no hay configuración SMTP, solo loguear
            if not self.smtp_user or not self.smtp_password:
                logger.warning(f"SMTP no configurado. Email simulado a {to_email}")
                logger.info(f"Asunto: {subject}")
                logger.info(f"Contenido: {text_content or html_content}")
                return True
            
            # Crear mensaje
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.app_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Agregar partes del mensaje
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)
            
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Enviar email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"Email enviado exitosamente a {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email a {to_email}: {str(e)}")
            return False
    
    def send_password_reset_email(self, to_email: str, username: str, reset_token: str) -> bool:
        """
        Envía email de recuperación de contraseña
        """
        reset_url = f"{self.app_url}/reset_password_screen?token={reset_token}"
        
        subject = f"{self.app_name} - Recuperación de Contraseña"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4A90E2; color: white; padding: 30px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 30px; margin-top: 0; }}
                .button {{ display: inline-block; padding: 15px 40px; background-color: #4A90E2 !important; 
                          color: white !important; text-decoration: none !important; border-radius: 5px; margin: 20px 0; 
                          font-weight: bold !important; font-size: 16px !important; text-transform: uppercase !important; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
                a.button:hover {{ background-color: #357ABD !important; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{self.app_name}</h1>
                </div>
                <div class="content">
                    <h2>Hola {username},</h2>
                    <p>Hemos recibido una solicitud para restablecer tu contraseña.</p>
                    <p>Si no solicitaste este cambio, puedes ignorar este correo.</p>
                    <p>Para restablecer tu contraseña, haz clic en el siguiente botón:</p>
                    <center>
                        <a href="{reset_url}" class="button" style="color: white !important; text-decoration: none !important;">RESTABLECER CONTRASEÑA</a>
                    </center>
                    <p><strong>Este enlace expirará en 1 hora.</strong></p>
                </div>
                <div class="footer">
                    <p>© 2024 {self.app_name}. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hola {username},
        
        Hemos recibido una solicitud para restablecer tu contraseña.
        
        Si no solicitaste este cambio, puedes ignorar este correo.
        
        Para restablecer tu contraseña, haz clic en el botón del email HTML o visita la aplicación.
        
        Este enlace expirará en 1 hora.
        
        Saludos,
        El equipo de {self.app_name}
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_verification_email(self, to_email: str, username: str, verification_token: str) -> bool:
        """
        Envía email de verificación
        """
        verify_url = f"{self.app_url}/verify-email?token={verification_token}"
        
        subject = f"{self.app_name} - Verifica tu Email"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4A90E2; color: white; padding: 30px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 30px; margin-top: 0; }}
                .button {{ display: inline-block; padding: 15px 40px; background-color: #4A90E2 !important; 
                          color: white !important; text-decoration: none !important; border-radius: 5px; margin: 20px 0; 
                          font-weight: bold !important; font-size: 16px !important; text-transform: uppercase !important; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
                a.button:hover {{ background-color: #357ABD !important; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>¡Bienvenido a {self.app_name}!</h1>
                </div>
                <div class="content">
                    <h2>Hola {username},</h2>
                    <p>Gracias por registrarte en {self.app_name}.</p>
                    <p>Para completar tu registro, por favor verifica tu dirección de email:</p>
                    <center>
                        <a href="{verify_url}" class="button" style="color: white !important; text-decoration: none !important;">VERIFICAR EMAIL</a>
                    </center>
                    <p><strong>Este enlace expirará en 24 horas.</strong></p>
                </div>
                <div class="footer">
                    <p>© 2024 {self.app_name}. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        ¡Bienvenido a {self.app_name}!
        
        Hola {username},
        
        Gracias por registrarte en {self.app_name}.
        
        Para completar tu registro, por favor verifica tu dirección de email haciendo clic en el botón del email.
        
        Este enlace expirará en 24 horas.
        
        Saludos,
        El equipo de {self.app_name}
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_welcome_email(self, to_email: str, username: str) -> bool:
        """
        Envía email de bienvenida después de verificar
        """
        subject = f"¡Bienvenido a {self.app_name}!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 20px; margin-top: 20px; }}
                .feature {{ margin: 15px 0; padding: 10px; background: white; border-radius: 5px; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #4CAF50; 
                          color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>¡Tu cuenta está verificada!</h1>
                </div>
                <div class="content">
                    <h2>Hola {username},</h2>
                    <p>¡Tu cuenta ha sido verificada exitosamente!</p>
                    <p>Ahora puedes disfrutar de todas las funcionalidades de {self.app_name}:</p>
                    
                    <div class="feature">
                        📄 <strong>Gestión de Documentos:</strong> Sube y organiza tus documentos
                    </div>
                    <div class="feature">
                        💬 <strong>Chat Inteligente:</strong> Haz preguntas sobre tus documentos
                    </div>
                    <div class="feature">
                        🔍 <strong>Búsqueda Avanzada:</strong> Encuentra información rápidamente
                    </div>
                    
                    <center>
                        <a href="{self.app_url}" class="button">Ir a la Aplicación</a>
                    </center>
                </div>
                <div class="footer">
                    <p>© 2024 {self.app_name}. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        ¡Tu cuenta está verificada!
        
        Hola {username},
        
        ¡Tu cuenta ha sido verificada exitosamente!
        
        Ahora puedes disfrutar de todas las funcionalidades de {self.app_name}:
        - Gestión de Documentos
        - Chat Inteligente
        - Búsqueda Avanzada
        
        Visita {self.app_url} para comenzar.
        
        Saludos,
        El equipo de {self.app_name}
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_password_changed_email(self, to_email: str, username: str) -> bool:
        """
        Envía email de confirmación de cambio de contraseña
        """
        subject = f"{self.app_name} - Contraseña Actualizada"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #FF6B6B; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 20px; margin-top: 20px; }}
                .alert {{ background-color: #FFE0E0; padding: 15px; border-radius: 5px; margin: 20px 0;
                         border-left: 4px solid #FF6B6B; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #4CAF50; 
                          color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Contraseña Actualizada</h1>
                </div>
                <div class="content">
                    <h2>Hola {username},</h2>
                    <p>Tu contraseña ha sido actualizada exitosamente.</p>
                    
                    <div class="alert">
                        <strong>⚠️ Si no realizaste este cambio:</strong>
                        <p>Por favor, contacta inmediatamente con soporte o intenta recuperar tu cuenta.</p>
                    </div>
                    
                    <p><strong>Detalles del cambio:</strong></p>
                    <ul>
                        <li>Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}</li>
                        <li>Acción: Contraseña restablecida mediante token de recuperación</li>
                    </ul>
                    
                    <center>
                        <a href="{self.app_url}" class="button">Ir a la Aplicación</a>
                    </center>
                </div>
                <div class="footer">
                    <p>© 2024 {self.app_name}. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Contraseña Actualizada
        
        Hola {username},
        
        Tu contraseña ha sido actualizada exitosamente.
        
        Si no realizaste este cambio, por favor contacta inmediatamente con soporte.
        
        Detalles del cambio:
        - Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        - Acción: Contraseña restablecida mediante token de recuperación
        
        Saludos,
        El equipo de {self.app_name}
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_email_change_notification(self, old_email: str, new_email: str, username: str, confirmation_token: str) -> bool:
        """
        Envía email de notificación de cambio de email al correo ANTERIOR
        """
        confirmation_url = f"{self.app_url}/api/users/verify-email-change?token={confirmation_token}"
        
        subject = f"{self.app_name} - Solicitud de Cambio de Email"
        
        # Leer el template HTML
        import os
        from pathlib import Path
        
        template_path = Path(__file__).parent.parent / "templates" / "emails" / "email_change_notification.html"
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                html_template = f.read()
            
            # Reemplazar las variables en el template
            html_content = html_template.replace('{{username}}', username)
            html_content = html_content.replace('{{old_email}}', old_email)
            html_content = html_content.replace('{{new_email}}', new_email)
            html_content = html_content.replace('{{confirmation_link}}', confirmation_url)
            
        except FileNotFoundError:
            # Fallback a un template simple si no se encuentra el archivo
            logger.warning(f"Template HTML no encontrado en {template_path}, usando fallback")
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #6B4CE6; color: white; padding: 30px; text-align: center; }}
                    .content {{ background-color: #f9f9f9; padding: 30px; margin-top: 0; }}
                    .button {{ display: inline-block; padding: 15px 40px; background-color: #6B4CE6 !important; 
                              color: white !important; text-decoration: none !important; border-radius: 5px; margin: 20px 0; 
                              font-weight: bold !important; font-size: 16px !important; text-transform: uppercase !important; }}
                    .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
                    .alert {{ background-color: #FFF3CD; padding: 15px; border-left: 4px solid #FFC107; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔄 Cambio de Email Detectado</h1>
                    </div>
                    <div class="content">
                        <h2>Hola {username},</h2>
                        <div class="alert">
                            <p><strong>⚠️ Se ha solicitado cambiar tu email de:</strong></p>
                            <p>{old_email} → {new_email}</p>
                        </div>
                        <p>Si realizaste esta solicitud, confirma el cambio haciendo clic en el siguiente botón:</p>
                        <center>
                            <a href="{confirmation_url}" class="button" style="color: white !important; text-decoration: none !important;">✅ SÍ, FUI YO - CONFIRMAR CAMBIO</a>
                        </center>
                        <p><strong>Este enlace expirará en 24 horas.</strong></p>
                        <p><small>Si no fuiste tú, ignora este email y tu cuenta permanecerá sin cambios.</small></p>
                    </div>
                    <div class="footer">
                        <p>© 2024 {self.app_name}. Todos los derechos reservados.</p>
                    </div>
                </div>
            </body>
            </html>
            """
        
        text_content = f"""
        Cambio de Email Detectado
        
        Hola {username},
        
        Se ha solicitado cambiar tu email de:
        {old_email} → {new_email}
        
        Si realizaste esta solicitud, confirma el cambio visitando:
        {confirmation_url}
        
        Este enlace expirará en 24 horas.
        
        Si no fuiste tú, ignora este email y tu cuenta permanecerá sin cambios.
        
        Saludos,
        El equipo de {self.app_name}
        """
        
        # IMPORTANTE: Enviar al email ANTERIOR
        return self.send_email(old_email, subject, html_content, text_content)

# Instancia global del servicio
email_service = EmailService()
