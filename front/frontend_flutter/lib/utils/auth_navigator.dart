import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';

class AuthNavigator {
  static void navigateToLogin(BuildContext context) {
    if (context.mounted) {
      Navigator.of(context).pushNamedAndRemoveUntil('/login', (route) => false);
    }
  }
  
  static void navigateToHome(BuildContext context) {
    if (context.mounted) {
      Navigator.of(context).pushNamedAndRemoveUntil('/home', (route) => false);
    }
  }
  
  static Future<void> logout(BuildContext context) async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    
    // Primero hacer logout
    await authProvider.logout();
    
    // Luego navegar
    if (context.mounted) {
      navigateToLogin(context);
    }
  }
  
  static void handleSessionExpired(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    
    // Manejar el error de autenticación
    authProvider.handleAuthError();
    
    // Mostrar mensaje al usuario
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Tu sesión ha expirado. Por favor, inicia sesión nuevamente.'),
          backgroundColor: Colors.orange,
          duration: Duration(seconds: 3),
        ),
      );
      
      // Navegar al login
      navigateToLogin(context);
    }
  }
  
  static void handleAuthenticationRequired(BuildContext context, {String? message}) {
    if (context.mounted) {
      if (message != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: Colors.orange,
            duration: const Duration(seconds: 3),
          ),
        );
      }
      
      navigateToLogin(context);
    }
  }
}
