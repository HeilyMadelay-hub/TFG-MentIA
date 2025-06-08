import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../models/user.dart';
import '../config/api_config.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../providers/dashboard_provider.dart';

class AuthService extends ChangeNotifier {
  static final AuthService _instance = AuthService._internal();
  
  factory AuthService() => _instance;
  
  AuthService._internal();

  User? _currentUser;
  bool _isLoading = false;
  String? _token;

  User? get currentUser => _currentUser;
  bool get isLoading => _isLoading;
  bool get isAuthenticated => _currentUser != null;
  bool get isAdmin => _currentUser?.isAdmin ?? false;
  String? get token => _token;

  // Método público para obtener el token
  Future<String?> getToken() async {
    if (_token == null) {
      await _loadToken();
    }
    return _token;
  }

  void setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }

  Future<void> _saveToken(String token) async {
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('auth_token', token);
  }

  Future<void> _loadToken() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('auth_token');
  }

  Future<void> _clearToken() async {
    _token = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
  }

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };

  Future<bool> login(String username, String password) async {
    setLoading(true);
    
    try {
      // OAuth2PasswordRequestForm espera form-data, no JSON
      final response = await http.post(
        Uri.parse(ApiConfig.login),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: {
          'username': username,
          'password': password,
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        // Guardar token
        await _saveToken(data['access_token']);
        
        // Crear usuario desde la respuesta real del backend
        _currentUser = User(
          id: data['user_id'] ?? data['id'],
          username: data['username'],
          email: data['email'],
          role: data['is_admin'] == true ? UserRole.admin : UserRole.user,
          createdAt: DateTime.parse(data['created_at'] ?? DateTime.now().toIso8601String()),
        );
        
        // Precargar datos del dashboard después del login exitoso
        print('🔄 Precargando dashboard después del login...');
        try {
          // Forzar recarga completa del dashboard
          DashboardProvider().clear();  // Limpiar datos antiguos
          await DashboardProvider().loadDashboardData(showLoading: false);
          print('✅ Dashboard precargado exitosamente');
        } catch (e) {
          print('⚠️ Error precargando dashboard: $e');
          // No fallar el login si el dashboard no carga
        }
        
        setLoading(false);
        notifyListeners();
        return true;
      } else {
        setLoading(false);
        throw Exception(jsonDecode(response.body)['detail'] ?? 'Error al iniciar sesión');
      }
    } catch (e) {
      setLoading(false);
      rethrow;
    }
  }

  Future<bool> register(String username, String email, String password) async {
    setLoading(true);
    
    try {
      final response = await http.post(
        Uri.parse(ApiConfig.register),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username,
          'email': email,
          'password': password,
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        // Después del registro exitoso, hacer login automático
        await login(username, password);
        
        setLoading(false);
        return true;
      } else {
        setLoading(false);
        final error = jsonDecode(response.body);
        throw Exception(error['detail'] ?? 'Error al registrar usuario');
      }
    } catch (e) {
      setLoading(false);
      rethrow;
    }
  }

  Future<void> loadCurrentUser() async {
    await _loadToken();
    if (_token == null) return;

    try {
      final response = await http.get(
        Uri.parse(ApiConfig.me),
        headers: _headers,
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        _currentUser = User(
          id: data['id'],
          username: data['username'],
          email: data['email'],
          role: data['is_admin'] == true ? UserRole.admin : UserRole.user,
          createdAt: DateTime.parse(data['created_at'] ?? DateTime.now().toIso8601String()),
        );
        
        notifyListeners();
      } else {
        // Token inválido, limpiar
        await _clearToken();
        _currentUser = null;
        notifyListeners();
      }
    } catch (e) {
      // Error de conexión o token inválido
      await _clearToken();
      _currentUser = null;
      notifyListeners();
    }
  }

  void logout() {
    _currentUser = null;
    _clearToken();
    // Limpiar datos del dashboard
    DashboardProvider().clear();
    notifyListeners();
  }

  Future<bool> updateProfile(Map<String, dynamic> data) async {
    if (_currentUser == null || _token == null) return false;
    
    setLoading(true);
    
    try {
      // Preparar datos para el backend
      final updateData = <String, dynamic>{};
      
      if (data['username'] != null && data['username'] != _currentUser!.username) {
        updateData['username'] = data['username'];
      }
      
      if (data['email'] != null && data['email'] != _currentUser!.email) {
        updateData['email'] = data['email'];
      }
      
      // Si hay cambio de contraseña
      if (data['current_password'] != null && data['new_password'] != null) {
        // Endpoint separado para cambio de contraseña
        final passwordResponse = await http.post(
          Uri.parse('${ApiConfig.baseUrl}/users/me/change-password'),
          headers: _headers,
          body: jsonEncode({
            'current_password': data['current_password'],
            'new_password': data['new_password'],
          }),
        );
        
        if (passwordResponse.statusCode != 200) {
          throw Exception('Error al cambiar la contraseña');
        }
      }
      
      // Actualizar perfil si hay cambios
      if (updateData.isNotEmpty) {
        final response = await http.put(
          Uri.parse('${ApiConfig.baseUrl}/users/me'),
          headers: _headers,
          body: jsonEncode(updateData),
        );
        
        if (response.statusCode == 200) {
          final userData = jsonDecode(response.body);
          
          _currentUser = User(
            id: userData['id'],
            username: userData['username'],
            email: userData['email'],
            role: userData['is_admin'] == true ? UserRole.admin : UserRole.user,
            createdAt: DateTime.parse(userData['created_at'] ?? _currentUser!.createdAt.toIso8601String()),
          );
        } else {
          throw Exception('Error al actualizar el perfil');
        }
      }
      
      setLoading(false);
      notifyListeners();
      return true;
    } catch (e) {
      setLoading(false);
      rethrow;
    }
  }
}
