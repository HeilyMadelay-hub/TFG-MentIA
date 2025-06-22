import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import '../models/user.dart';

class AuthProvider extends ChangeNotifier {
  final AuthService _authService = AuthService();
  bool _isAuthenticated = false;
  bool _isLoading = false;
  User? _currentUser;
  String? _authError;
  
  // Getters
  bool get isAuthenticated => _isAuthenticated;
  bool get isLoading => _isLoading;
  User? get currentUser => _currentUser;
  String? get authError => _authError;
  bool get isAdmin => _currentUser?.isAdmin ?? false;
  
  AuthProvider() {
    _initializeAuth();
  }
  
  // Inicialización privada para evitar llamadas async en constructor
  void _initializeAuth() {
    checkAuthentication();
  }
  
  Future<void> checkAuthentication() async {
    _setLoading(true);
    _clearError();
    
    try {
      final token = await _authService.getToken();
      if (token != null) {
        // Verificar que el token sea válido
        final user = await _authService.getCurrentUser();
        if (user != null) {
        _currentUser = user;
        _isAuthenticated = true;
        } else {
        // Token existe pero no es válido
        await _authService.clearSession();
        _isAuthenticated = false;
        _currentUser = null;
        }
      } else {
        _isAuthenticated = false;
        _currentUser = null;
      }
    } catch (e) {
      debugPrint('Error checking authentication: $e');
      _isAuthenticated = false;
      _currentUser = null;
      _setError('Error al verificar la autenticación');
    } finally {
      _setLoading(false);
    }
  }
  
  Future<bool> login(String username, String password) async {
    _setLoading(true);
    _clearError();
    
    try {
      final success = await _authService.login(username, password);
      if (success) {
        _currentUser = _authService.currentUser;
        _isAuthenticated = true;
        notifyListeners();
        return true;
      } else {
        _setError('Credenciales inválidas');
        return false;
      }
    } catch (e) {
      debugPrint('Error during login: $e');
      _setError('Error al iniciar sesión: ${e.toString()}');
      return false;
    } finally {
      _setLoading(false);
    }
  }
  
  Future<void> logout() async {
    _setLoading(true);
    
    try {
      await _authService.logout();
      _isAuthenticated = false;
      _currentUser = null;
      _clearError();
    } catch (e) {
      debugPrint('Error during logout: $e');
      // Aún así limpiamos el estado local
      _isAuthenticated = false;
      _currentUser = null;
    } finally {
      _setLoading(false);
    }
  }
  
  // Método mejorado que no depende del contexto
  void handleAuthError() {
    _isAuthenticated = false;
    _currentUser = null;
    _setError('Sesión expirada. Por favor, inicia sesión nuevamente.');
    notifyListeners();
  }
  
  // Método para refrescar el token
  Future<bool> refreshToken() async {
    try {
      final newToken = await _authService.refreshToken();
      if (newToken != null) {
        // Token refrescado exitosamente
        await checkAuthentication();
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('Error refreshing token: $e');
      handleAuthError();
      return false;
    }
  }
  
  // Método para actualizar el usuario actual
  Future<void> updateCurrentUser() async {
    try {
      final user = await _authService.getCurrentUser();
      if (user != null) {
        _currentUser = user;
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Error updating current user: $e');
    }
  }
  
  // Métodos auxiliares privados
  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }
  
  void _setError(String? error) {
    _authError = error;
    notifyListeners();
  }
  
  void _clearError() {
    _authError = null;
  }
  
  @override
  void dispose() {
    // Limpiar recursos si es necesario
    super.dispose();
  }
}
