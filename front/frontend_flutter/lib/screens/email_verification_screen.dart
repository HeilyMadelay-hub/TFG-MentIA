import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../config/api_config.dart';

class EmailVerificationScreen extends StatefulWidget {
  final String? token;
  
  const EmailVerificationScreen({super.key, this.token});
  
  @override
  State<EmailVerificationScreen> createState() => _EmailVerificationScreenState();
}

class _EmailVerificationScreenState extends State<EmailVerificationScreen> 
    with SingleTickerProviderStateMixin {
  bool _isVerifying = true;
  bool _isSuccess = false;
  String _message = 'Verificando tu email...';
  
  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _fadeAnimation;
  
  @override
  void initState() {
    super.initState();
    
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    
    _scaleAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.elasticOut,
    ));
    
    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeIn,
    ));
    
    // Verificar el token
    _verifyEmail();
  }
  
  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }
  
  Future<void> _verifyEmail() async {
    if (widget.token == null) {
      setState(() {
        _isVerifying = false;
        _isSuccess = false;
        _message = 'Token de verificación no válido';
      });
      // No redirigir automáticamente
      return;
    }
    
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.baseUrl}/users/verify-email'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'token': widget.token}),
      );
      
      if (response.statusCode == 200) {
        setState(() {
          _isVerifying = false;
          _isSuccess = true;
          _message = '¡Bienvenido a DocuMente!';
        });
        _animationController.forward();
        
        // No redirigir automáticamente - mostrar mensaje de bienvenida
      } else {
        final error = jsonDecode(response.body);
        setState(() {
          _isVerifying = false;
          _isSuccess = false;
          _message = error['detail'] ?? 'Error al verificar el email';
        });
        // No redirigir automáticamente en caso de error
      }
    } catch (e) {
      setState(() {
        _isVerifying = false;
        _isSuccess = false;
        _message = 'Error de conexión. Por favor, intenta de nuevo.';
      });
      // No redirigir automáticamente
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: const [
              Color(0xFF4CAF50),
              Color(0xFF2E7D32),
            ],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  // Icono animado
                  if (_isVerifying)
                    const CircularProgressIndicator(
                      color: Colors.white,
                      strokeWidth: 3,
                    )
                  else if (_isSuccess)
                    ScaleTransition(
                      scale: _scaleAnimation,
                      child: Container(
                        width: 120,
                        height: 120,
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.2),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.check_circle,
                          color: Colors.white,
                          size: 80,
                        ),
                      ),
                    )
                  else
                    Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.2),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.error_outline,
                        color: Colors.white,
                        size: 80,
                      ),
                    ),
                  
                  const SizedBox(height: 32),
                  
                  // Título animado
                  FadeTransition(
                    opacity: _fadeAnimation,
                    child: Text(
                      _isSuccess 
                        ? '¡Tu cuenta está verificada!' 
                        : _isVerifying 
                          ? 'Verificando...' 
                          : 'Error',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                  
                  const SizedBox(height: 16),
                  
                  // Mensaje
                  FadeTransition(
                    opacity: _fadeAnimation,
                    child: Text(
                      _message,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.w500,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                  
                  if (_isSuccess) ...[
                    const SizedBox(height: 24),
                    Text(
                      '¡Ahora puedes cerrar esta pestaña y usar la aplicación!',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.8),
                        fontSize: 14,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
