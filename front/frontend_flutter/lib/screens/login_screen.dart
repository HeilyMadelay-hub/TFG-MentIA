import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../main.dart';
import '../utils/email_validator.dart';
import '../utils/responsive_utils.dart';
import 'register_screen.dart';
import 'forgot_password_screen.dart';

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

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameOrEmailController = TextEditingController();
  final _passwordController = TextEditingController();
  
  bool _isLoading = false;
  bool _obscurePassword = true;
  String? _errorMessage;

  @override
  void dispose() {
    _usernameOrEmailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  // Validación de username o email
  String? _validateUsernameOrEmail(String? value) {
    if (value == null || value.isEmpty) {
      return 'Ingresa tu usuario o email';
    }
    
    // Si contiene @, validar como email
    if (value.contains('@')) {
      final validation = EmailValidator.validate(value.trim());
      if (!(validation['isValid'] ?? false)) {
        final error = validation['error'] ?? 'Email inválido';
        final suggestion = validation['suggestion'];
        
        if (suggestion != null) {
          return '$error\n¿Quisiste decir: $suggestion?';
        }
        return error;
      }
    } else {
      // Validar como username
      if (value.length < 3) {
        return 'El nombre de usuario debe tener al menos 3 caracteres';
      }
    }
    
    return null;
  }

  // Validación de contraseña
  String? _validatePassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'La contraseña es requerida';
    }
    return null;
  }

  // Método para iniciar sesión
  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final authService = Provider.of<AuthService>(context, listen: false);
      
      // Llamar al servicio de login
      final success = await authService.login(
        _usernameOrEmailController.text.trim(),
        _passwordController.text,
      );

      if (success && mounted) {
        // Mostrar mensaje de éxito
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('¡Bienvenido de nuevo!'),
            backgroundColor: Colors.green,
          ),
        );

        // La navegación se maneja automáticamente por el AuthWrapper
      }
    } catch (e) {
      String errorMessage = e.toString().replaceAll('Exception: ', '');
      
      // Detectar y mejorar mensajes de error
      if (errorMessage.contains('Failed to fetch') || 
          errorMessage.contains('Client failed to fetch') ||
          errorMessage.contains('SocketException') ||
          errorMessage.contains('Connection refused')) {
        errorMessage = 'No se pudo conectar al servidor. Por favor verifica tu conexión a internet.';
      } else if (errorMessage.contains('TimeoutException')) {
        errorMessage = 'La conexión tardó demasiado. Intenta nuevamente.';
      } else if (errorMessage.contains('Credenciales inválidas') || 
                 errorMessage.contains('Invalid credentials')) {
        errorMessage = 'Usuario/email o contraseña incorrectos';
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
                                    Icons.login_rounded,
                                    size: sizingInfo.fontSize.largeIcon,
                                    color: const Color(0xFFE91E63),
                                  ),
                                ),
                              ),
                              SizedBox(height: sizingInfo.spacing * 2),
                              
                              // Title
                              Text(
                                'Bienvenido',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: sizingInfo.fontSize.header,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                              SizedBox(height: sizingInfo.spacing / 2),
                              Text(
                                'Inicia sesión en MentIA',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: sizingInfo.fontSize.body,
                                  color: Colors.white70,
                                ),
                              ),
                              SizedBox(height: sizingInfo.spacing * 3),
                              
                              // Formulario de login
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
                                    
                                    // Campo Username o Email
                                    TextFormField(
                                      controller: _usernameOrEmailController,
                                      keyboardType: TextInputType.emailAddress,
                                      textInputAction: TextInputAction.next,
                                      autocorrect: false,
                                      enableSuggestions: false,
                                      style: TextStyle(fontSize: sizingInfo.fontSize.body),
                                      decoration: InputDecoration(
                                        labelText: 'Usuario o Email',
                                        labelStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                                        hintText: 'usuario123 o tu@email.com',
                                        hintStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                                        prefixIcon: Icon(Icons.account_circle_outlined, size: sizingInfo.fontSize.icon),
                                        border: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                                        ),
                                        helperText: 'Puedes usar tu nombre de usuario o email',
                                        helperStyle: TextStyle(fontSize: sizingInfo.fontSize.caption),
                                        contentPadding: EdgeInsets.symmetric(
                                          horizontal: sizingInfo.cardPadding,
                                          vertical: sizingInfo.spacing,
                                        ),
                                      ),
                                      validator: _validateUsernameOrEmail,
                                      onChanged: (value) {
                                        // Validar en tiempo real para dar feedback inmediato si es email
                                        if (value.contains('@')) {
                                          final validation = EmailValidator.validate(value);
                                          if (!(validation['isValid'] ?? true)) {
                                            final suggestion = validation['suggestion'];
                                            if (suggestion != null && mounted) {
                                              // Opcionalmente mostrar sugerencia
                                            }
                                          }
                                        }
                                      },
                                    ),
                                    SizedBox(height: sizingInfo.spacing),
                                    
                                    // Campo Contraseña
                                    TextFormField(
                                      controller: _passwordController,
                                      obscureText: _obscurePassword,
                                      textInputAction: TextInputAction.done,
                                      onFieldSubmitted: (_) => _login(),
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
                                    
                                    // Link Olvidé contraseña
                                    Align(
                                      alignment: Alignment.centerRight,
                                      child: TextButton(
                                        onPressed: () {
                                          Navigator.push(
                                            context,
                                            MaterialPageRoute(
                                              builder: (context) => const ForgotPasswordScreen(),
                                            ),
                                          );
                                        },
                                        child: Text(
                                          '¿Olvidaste tu contraseña?',
                                          style: TextStyle(
                                            color: const Color(0xFFE91E63),
                                            fontSize: sizingInfo.fontSize.body,
                                          ),
                                        ),
                                      ),
                                    ),
                                    SizedBox(height: sizingInfo.spacing * 2),
                                    
                                    // Botón de login
                                    ElevatedButton(
                                      onPressed: _isLoading ? null : _login,
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
                                              'Iniciar Sesión',
                                              style: TextStyle(
                                                fontSize: sizingInfo.fontSize.button,
                                                fontWeight: FontWeight.bold,
                                                color: Colors.white,
                                              ),
                                            ),
                                    ),
                                    SizedBox(height: sizingInfo.spacing),
                                    
                                    // Divider
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Divider(
                                            color: Colors.grey[300],
                                            thickness: 1,
                                          ),
                                        ),
                                        Padding(
                                          padding: EdgeInsets.symmetric(horizontal: sizingInfo.spacing),
                                          child: Text(
                                            'o',
                                            style: TextStyle(
                                              color: Colors.grey[600],
                                              fontSize: sizingInfo.fontSize.body,
                                            ),
                                          ),
                                        ),
                                        Expanded(
                                          child: Divider(
                                            color: Colors.grey[300],
                                            thickness: 1,
                                          ),
                                        ),
                                      ],
                                    ),
                                    SizedBox(height: sizingInfo.spacing),
                                    
                                    // Link para ir a registro
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        Text(
                                          '¿No tienes cuenta? ',
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
                                                builder: (context) => const RegisterScreen(),
                                              ),
                                            );
                                          },
                                          child: Text(
                                            'Regístrate',
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
                              
                              // Información adicional
                              if (sizingInfo.isDesktop) ...[
                                SizedBox(height: sizingInfo.spacing * 2),
                                Text(
                                  'MentIA - Tu asistente inteligente',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    fontSize: sizingInfo.fontSize.caption,
                                    color: Colors.white70,
                                  ),
                                ),
                              ],
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