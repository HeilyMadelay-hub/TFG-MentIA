import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';

class AuthGuard extends StatefulWidget {
  final Widget child;
  
  const AuthGuard({Key? key, required this.child}) : super(key: key);
  
  @override
  State<AuthGuard> createState() => _AuthGuardState();
}

class _AuthGuardState extends State<AuthGuard> {
  @override
  void initState() {
    super.initState();
    _checkAuthStatus();
  }
  
  Future<void> _checkAuthStatus() async {
    final authService = context.read<AuthService>();
    
    // Verificar si el token es válido
    final isValid = await authService.validateToken();
    
    if (!isValid && mounted) {
      // Token inválido o expirado - forzar logout
      await authService.clearSession();
      
      // Navegar al login
      if (mounted) {
        Navigator.of(context).pushNamedAndRemoveUntil('/', (route) => false);
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return widget.child;
  }
}
