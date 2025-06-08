import 'package:flutter/material.dart';
import '../services/auth_service.dart';

class AuthProvider extends ChangeNotifier {
  final AuthService _authService = AuthService();
  bool _isAuthenticated = false;
  
  bool get isAuthenticated => _isAuthenticated;
  
  AuthProvider() {
    checkAuthentication();
  }
  
  Future<void> checkAuthentication() async {
    try {
      final token = await _authService.getToken();
      _isAuthenticated = token != null;
      notifyListeners();
    } catch (e) {
      _isAuthenticated = false;
      notifyListeners();
    }
  }
  
  Future<void> logout(BuildContext context) async {
    await _authService.logout();
    _isAuthenticated = false;
    notifyListeners();
    
    if (context.mounted) {
      Navigator.of(context).pushNamedAndRemoveUntil('/login', (route) => false);
    }
  }
  
  void handleAuthError(BuildContext context) {
    logout(context);
  }
}
