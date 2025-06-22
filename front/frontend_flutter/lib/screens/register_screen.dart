import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/gestures.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../utils/email_validator.dart';
import '../utils/responsive_utils.dart';
import 'login_screen.dart';

// ScrollBehavior personalizado para ocultar scrollbars pero permitir scroll táctil
class NoScrollbarBehavior extends MaterialScrollBehavior {
  @override
  Widget buildScrollbar(BuildContext context, Widget child, ScrollableDetails details) {
    // No construir scrollbar
    return child;
  }
  
  @override
  Set<PointerDeviceKind> get dragDevices => {
    PointerDeviceKind.touch,
    PointerDeviceKind.mouse,
    PointerDeviceKind.trackpad,
  };
}

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  
  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;
  String? _errorMessage;

  @override
  void dispose() {
    _emailController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  // Validación de email con el nuevo validador
  String? _validateEmail(String? value) {
    if (value == null || value.isEmpty) {
      return 'El email es requerido';
    }
    
    // Usar el validador personalizado
    final validation = EmailValidator.validate(value.trim());
    if (!(validation['isValid'] ?? false)) {
      final error = validation['error'] ?? 'Email inválido';
      final suggestion = validation['suggestion'];
      
      if (suggestion != null) {
        return '$error\n¿Quisiste decir: $suggestion?';
      }
      return error;
    }
    
    return null;
  }

  // Validación de username
  String? _validateUsername(String? value) {
    if (value == null || value.isEmpty) {
      return 'El nombre de usuario es requerido';
    }
    if (value.length < 3) {
      return 'El nombre de usuario debe tener al menos 3 caracteres';
    }
    if (value.length > 20) {
      return 'El nombre de usuario no puede tener más de 20 caracteres';
    }
    // Solo permitir letras, números, guiones y guiones bajos
    final usernameRegex = RegExp(r'^[a-zA-Z0-9_-]+$');
    if (!usernameRegex.hasMatch(value)) {
      return 'Solo se permiten letras, números, guiones y guiones bajos';
    }
    // Verificar que no empiece con número o caracteres especiales
    if (RegExp(r'^[0-9_-]').hasMatch(value)) {
      return 'El nombre de usuario debe empezar con una letra';
    }
    return null;
  }

  // Validación de contraseña
  String? _validatePassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'La contraseña es requerida';
    }
    if (value.length < 8) {
      return 'La contraseña debe tener al menos 8 caracteres';
    }
    return null;
  }

  // Validación de confirmación de contraseña
  String? _validateConfirmPassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'Confirme su contraseña';
    }
    if (value != _passwordController.text) {
      return 'Las contraseñas no coinciden';
    }
    return null;
  }

  // Método para registrar usuario
  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final authService = Provider.of<AuthService>(context, listen: false);
      
      // Llamar al servicio de registro
      final success = await authService.register(
        _usernameController.text.trim(),
        _emailController.text.trim(),
        _passwordController.text,
      );

      if (success && mounted) {
        // Mostrar mensaje de éxito con información útil
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('¡Registro exitoso! Bienvenido a MentIA'),
                const SizedBox(height: 4),
                Text(
                  'Puedes iniciar sesión con:\n'
                  'Username: ${_usernameController.text.trim()}\n'
                  'Email: ${_emailController.text.trim()}',
                  style: const TextStyle(fontSize: 12),
                ),
              ],
            ),
            backgroundColor: Colors.green,
            duration: const Duration(seconds: 5),
          ),
        );

        // La navegación se maneja automáticamente por el AuthWrapper
        // ya que el AuthService notifica a los listeners
      }
    } catch (e) {
      String errorMessage = e.toString().replaceAll('Exception: ', '');
      
      // Detectar y mejorar mensajes de error de conexión
      if (errorMessage.contains('Failed to fetch') || 
          errorMessage.contains('Client failed to fetch') ||
          errorMessage.contains('SocketException') ||
          errorMessage.contains('Connection refused')) {
        errorMessage = 'No se pudo conectar al servidor. Por favor verifica tu conexión a internet.';
      } else if (errorMessage.contains('TimeoutException')) {
        errorMessage = 'La conexión tardó demasiado. Intenta nuevamente.';
      } else if (errorMessage.contains('http://') || 
                 errorMessage.contains('https://') || 
                 errorMessage.contains('localhost') ||
                 errorMessage.contains('uri=')) {
        errorMessage = 'Error de conexión. Por favor intenta más tarde.';
      }
      
      setState(() {
        _errorMessage = errorMessage;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      builder: (context, sizingInfo) {
        return Scaffold(
          body: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: const [Color(0xFFE91E63), Color(0xFFFF69B4)],
              ),
            ),
            child: SafeArea(
              child: Center(
                child: ScrollConfiguration(
                  behavior: NoScrollbarBehavior(),
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    padding: EdgeInsets.symmetric(
                      horizontal: sizingInfo.padding,
                      vertical: sizingInfo.padding / 2,
                    ),
                    child: ConstrainedBox(
                      constraints: BoxConstraints(
                        maxWidth: sizingInfo.isDesktop ? 500 : double.infinity,
                      ),
                      child: IntrinsicHeight(
                        child: Form(
                          key: _formKey,
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              // Logo
                              Center(
                                child: Container(
                                  width: sizingInfo.isSmallDevice ? 60 : 80,
                                  height: sizingInfo.isSmallDevice ? 60 : 80,
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
                                    boxShadow: [
                                      BoxShadow(
                                        color: Colors.black.withValues(alpha: 0.1),
                                        blurRadius: 20,
                                        offset: const Offset(0, 10),
                                      ),
                                    ],
                                  ),
                                  child: Icon(
                                    Icons.person_add_outlined,
                                    size: sizingInfo.fontSize.largeIcon,
                                    color: const Color(0xFFE91E63),
                                  ),
                                ),
                              ),
                              SizedBox(height: sizingInfo.spacing * 2),
                              
                              // Title
                              Text(
                                'Crear Cuenta',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: sizingInfo.fontSize.header,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                              SizedBox(height: sizingInfo.spacing / 2),
                              Text(
                                'Únete a MentIA',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: sizingInfo.fontSize.body,
                                  color: Colors.white70,
                                ),
                              ),
                              SizedBox(height: sizingInfo.spacing * 3),
                              
                              // Formulario de registro
                              Container(
                                padding: EdgeInsets.all(sizingInfo.cardPadding),
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
                                  boxShadow: [
                                    BoxShadow(
                                      color: Colors.black.withValues(alpha: 0.1),
                                      blurRadius: 20,
                                      offset: const Offset(0, 10),
                                    ),
                                  ],
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.stretch,
                                  children: [
                                    // Mensaje de error
                                    if (_errorMessage != null)
                                      Container(
                                        padding: EdgeInsets.all(sizingInfo.spacing),
                                        margin: EdgeInsets.only(bottom: sizingInfo.spacing),
                                        decoration: BoxDecoration(
                                          color: Colors.red.shade50,
                                          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                                          border: Border.all(color: Colors.red.shade200),
                                        ),
                                        child: Row(
                                          children: [
                                            Icon(Icons.error_outline, 
                                              color: Colors.red.shade700, 
                                              size: sizingInfo.fontSize.icon,
                                            ),
                                            SizedBox(width: sizingInfo.spacing / 2),
                                            Expanded(
                                              child: Text(
                                                _errorMessage!,
                                                style: TextStyle(
                                                  color: Colors.red.shade700,
                                                  fontSize: sizingInfo.fontSize.caption,
                                                ),
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    
                                    // Campo Email
                                    TextFormField(
                                      controller: _emailController,
                                      keyboardType: TextInputType.emailAddress,
                                      textInputAction: TextInputAction.next,
                                      autocorrect: false,
                                      enableSuggestions: false,
                                      style: TextStyle(fontSize: sizingInfo.fontSize.body),
                                      decoration: InputDecoration(
                                        labelText: 'Email',
                                        labelStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                                        hintText: 'tu@email.com',
                                        hintStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                                        prefixIcon: Icon(Icons.email_outlined, size: sizingInfo.fontSize.icon),
                                        border: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                                        ),
                                        helperText: 'Usa tu email real para recuperar tu cuenta',
                                        helperMaxLines: 2,
                                        helperStyle: TextStyle(fontSize: sizingInfo.fontSize.caption),
                                        contentPadding: EdgeInsets.symmetric(
                                          horizontal: sizingInfo.cardPadding,
                                          vertical: sizingInfo.spacing,
                                        ),
                                      ),
                                      validator: _validateEmail,
                                      onChanged: (value) {
                                        // Validar en tiempo real para dar feedback inmediato
                                        if (value.contains('@')) {
                                          final validation = EmailValidator.validate(value);
                                          if (!(validation['isValid'] ?? true)) {
                                            final suggestion = validation['suggestion'];
                                            if (suggestion != null && mounted) {
                                              // Actualizar el campo con la sugerencia si el usuario lo desea
                                              // Esto es opcional, podemos solo mostrar el error
                                            }
                                          }
                                        }
                                      },
                                    ),
                                    SizedBox(height: sizingInfo.spacing),
                                    
                                    // Campo Username
                                    TextFormField(
                                      controller: _usernameController,
                                      textInputAction: TextInputAction.next,
                                      autocorrect: false,
                                      enableSuggestions: false,
                                      style: TextStyle(fontSize: sizingInfo.fontSize.body),
                                      inputFormatters: [
                                        FilteringTextInputFormatter.allow(RegExp(r'[a-zA-Z0-9_-]')),
                                      ],
                                      decoration: InputDecoration(
                                        labelText: 'Nombre de usuario',
                                        labelStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                                        hintText: 'usuario123',
                                        hintStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                                        prefixIcon: Icon(Icons.person_outline, size: sizingInfo.fontSize.icon),
                                        border: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                                        ),
                                        contentPadding: EdgeInsets.symmetric(
                                          horizontal: sizingInfo.cardPadding,
                                          vertical: sizingInfo.spacing,
                                        ),
                                      ),
                                      validator: _validateUsername,
                                    ),
                                    SizedBox(height: sizingInfo.spacing),
                                    
                                    // Campo Contraseña
                                    TextFormField(
                                      controller: _passwordController,
                                      obscureText: _obscurePassword,
                                      textInputAction: TextInputAction.next,
                                      style: TextStyle(fontSize: sizingInfo.fontSize.body),
                                      decoration: InputDecoration(
                                        labelText: 'Contraseña',
                                        labelStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                                        hintText: '••••••••',
                                        hintStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                                        prefixIcon: Icon(Icons.lock_outline, size: sizingInfo.fontSize.icon),
                                        suffixIcon: IconButton(
                                          icon: Icon(
                                            _obscurePassword 
                                              ? Icons.visibility_off_outlined 
                                              : Icons.visibility_outlined,
                                            size: sizingInfo.fontSize.icon,
                                          ),
                                          onPressed: () {
                                            setState(() {
                                              _obscurePassword = !_obscurePassword;
                                            });
                                          },
                                        ),
                                        border: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                                        ),
                                        contentPadding: EdgeInsets.symmetric(
                                          horizontal: sizingInfo.cardPadding,
                                          vertical: sizingInfo.spacing,
                                        ),
                                      ),
                                      validator: _validatePassword,
                                    ),
                                    SizedBox(height: sizingInfo.spacing),
                                    
                                    // Campo Confirmar Contraseña
                                    TextFormField(
                                      controller: _confirmPasswordController,
                                      obscureText: _obscureConfirmPassword,
                                      textInputAction: TextInputAction.done,
                                      onFieldSubmitted: (_) => _register(),
                                      style: TextStyle(fontSize: sizingInfo.fontSize.body),
                                      decoration: InputDecoration(
                                        labelText: 'Confirmar contraseña',
                                        labelStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                                        hintText: '••••••••',
                                        hintStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                                        prefixIcon: Icon(Icons.lock_outline, size: sizingInfo.fontSize.icon),
                                        suffixIcon: IconButton(
                                          icon: Icon(
                                            _obscureConfirmPassword 
                                              ? Icons.visibility_off_outlined 
                                              : Icons.visibility_outlined,
                                            size: sizingInfo.fontSize.icon,
                                          ),
                                          onPressed: () {
                                            setState(() {
                                              _obscureConfirmPassword = !_obscureConfirmPassword;
                                            });
                                          },
                                        ),
                                        border: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                                        ),
                                        contentPadding: EdgeInsets.symmetric(
                                          horizontal: sizingInfo.cardPadding,
                                          vertical: sizingInfo.spacing,
                                        ),
                                      ),
                                      validator: _validateConfirmPassword,
                                    ),
                                    SizedBox(height: sizingInfo.spacing * 2),
                                    
                                    // Botón de registro
                                    ElevatedButton(
                                      onPressed: _isLoading ? null : _register,
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: const Color(0xFFE91E63),
                                        padding: EdgeInsets.symmetric(
                                          vertical: sizingInfo.spacing * 1.5,
                                        ),
                                        shape: RoundedRectangleBorder(
                                          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                                        ),
                                      ),
                                      child: _isLoading
                                          ? SizedBox(
                                              height: 20,
                                              width: 20,
                                              child: CircularProgressIndicator(
                                                color: Colors.white,
                                                strokeWidth: 2,
                                              ),
                                            )
                                          : Text(
                                              'Crear Cuenta',
                                              style: TextStyle(
                                                fontSize: sizingInfo.fontSize.button,
                                                fontWeight: FontWeight.bold,
                                                color: Colors.white,
                                              ),
                                            ),
                                    ),
                                    SizedBox(height: sizingInfo.spacing),
                                    
                                    // Link para ir a login
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        Text(
                                          '¿Ya tienes cuenta? ',
                                          style: TextStyle(
                                            color: Colors.grey,
                                            fontSize: sizingInfo.fontSize.body,
                                          ),
                                        ),
                                        TextButton(
                                          onPressed: () {
                                            Navigator.pushReplacement(
                                              context,
                                              MaterialPageRoute(
                                                builder: (context) => const LoginScreen(),
                                              ),
                                            );
                                          },
                                          child: Text(
                                            'Inicia sesión',
                                            style: TextStyle(
                                              color: const Color(0xFFE91E63),
                                              fontWeight: FontWeight.bold,
                                              fontSize: sizingInfo.fontSize.body,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}