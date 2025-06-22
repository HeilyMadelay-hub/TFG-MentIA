# Scripts y Utilidades

Este directorio contiene scripts auxiliares y herramientas de diagnóstico para el proyecto MentIA.

## Estructura

### 📁 `/windows`
Scripts batch (.bat) para automatización en Windows:
- `INICIAR_CHATBOT.bat` - Inicia todos los servicios del chatbot
- `APAGAR_CHATBOT.bat` - Detiene todos los servicios
- `start_docker.bat` - Inicia los contenedores Docker
- `reparar_todo.bat` - Script de reparación general
- `solucionar_puerto.bat` - Soluciona conflictos de puertos

### 📁 `/diagnostico`
Scripts Python para debugging y diagnóstico:
- Scripts de verificación y testing
- Herramientas de debug temporales
- **Nota**: Estos archivos están excluidos del control de versiones

### 📁 `/sql`
Scripts SQL para mantenimiento de base de datos:
- `correccion_urgente_conteo.sql` - Correcciones de conteo en BD
- `verificar_funciones_simples.sql` - Verificación de funciones SQL

## Uso

Para ejecutar los scripts de Windows:
```bash
cd scripts/windows
./INICIAR_CHATBOT.bat
```

Para scripts de diagnóstico:
```bash
cd scripts/diagnostico
python nombre_del_script.py
```

## Importante

Los scripts en `/diagnostico` son temporales y no deben incluirse en producción.
