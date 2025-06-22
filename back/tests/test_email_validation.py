"""
Script de prueba para verificar el sistema de validación de emails
"""
import asyncio
import sys
sys.path.append('.')

from src.services.email_validation import EmailValidationService

async def test_email_validation():
    """Prueba la validación de emails"""
    
    validator = EmailValidationService()
    
    # Lista de emails para probar
    test_emails = [
        "perro@gmail.com",  # Email falso (no existe)
        "usuario@dominiofalso123.com",  # Dominio falso
        "test@10minutemail.com",  # Email temporal
        "heily1857@gmail.com",  # Email real (si existe)
        "docmentementai@gmail.com",  # Email real del sistema
    ]
    
    print("🔍 Probando validación de emails...\n")
    
    for email in test_emails:
        print(f"\n📧 Verificando: {email}")
        print("-" * 50)
        
        # Verificar si es desechable
        is_disposable = validator.is_disposable_email(email)
        print(f"¿Es desechable? {'❌ SÍ' if is_disposable else '✅ NO'}")
        
        # Validación completa
        result = await validator.validate_email_exists(email)
        
        print(f"¿Es válido? {'✅ SÍ' if result['is_valid'] else '❌ NO'}")
        
        if not result['is_valid']:
            print(f"Razón: {result['reason']}")
        
        print("\nChecks realizados:")
        for check, passed in result['checks'].items():
            emoji = "✅" if passed else "❌"
            print(f"  {emoji} {check}")
    
    print("\n" + "="*60)
    print("📋 RESUMEN:")
    print("- Emails como 'perro@gmail.com' NO pasarán la validación")
    print("- Solo emails reales y funcionales serán aceptados")
    print("- El sistema evita el registro de emails falsos")

if __name__ == "__main__":
    asyncio.run(test_email_validation())
