import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';

class ErrorInterceptor {
  static final ErrorInterceptor _instance = ErrorInterceptor._internal();
  
  factory ErrorInterceptor() => _instance;
  
  ErrorInterceptor._internal();
  
  BuildContext? _context;
  bool _isHandlingError = false;
  
  void setContext(BuildContext context) {
    _context = context;
  }
  
  Future<void> handleError(dynamic error) async {
    if (_isHandlingError || _context == null) return;
    
    _isHandlingError = true;
    
    try {
      final errorStr = error.toString();
      
      // Detectar errores de autenticación
      if (errorStr.contains('401') || 
          errorStr.contains('Unauthorized') ||
          errorStr.contains('Token expired') ||
          errorStr.contains('No hay token de autenticación')) {
        
        // Intentar refresh token
        final authService = _context!.read<AuthService>();
        final newToken = await authService.refreshToken();
        
        if (newToken == null) {
          // No se pudo renovar - forzar re-login
          await authService.clearSession();
          
          // Mostrar mensaje amigable
          if (_context != null && _context!.mounted) {
            ScaffoldMessenger.of(_context!).showSnackBar(
              const SnackBar(
                content: Text('Tu sesión ha expirado. Por favor inicia sesión nuevamente.'),
                backgroundColor: Colors.orange,
                duration: Duration(seconds: 3),
              ),
            );
            
            // Navegar al login
            Navigator.of(_context!).pushNamedAndRemoveUntil('/', (route) => false);
          }
        }
      }
      // Manejar errores de conexión
      else if (errorStr.contains('SocketException') || 
               errorStr.contains('Failed to fetch') ||
               errorStr.contains('Connection refused')) {
        
        if (_context != null && _context!.mounted) {
          ScaffoldMessenger.of(_context!).showSnackBar(
            const SnackBar(
              content: Text('Error de conexión. Verifica tu internet.'),
              backgroundColor: Colors.red,
              duration: Duration(seconds: 2),
            ),
          );
        }
      }
    } finally {
      _isHandlingError = false;
    }
  }
}

// Widget para proveer el contexto al interceptor
class ErrorInterceptorProvider extends StatefulWidget {
  final Widget child;
  
  const ErrorInterceptorProvider({Key? key, required this.child}) : super(key: key);
  
  @override
  State<ErrorInterceptorProvider> createState() => _ErrorInterceptorProviderState();
}

class _ErrorInterceptorProviderState extends State<ErrorInterceptorProvider> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ErrorInterceptor().setContext(context);
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return widget.child;
  }
}
