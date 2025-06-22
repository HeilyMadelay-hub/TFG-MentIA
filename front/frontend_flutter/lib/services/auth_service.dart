import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import '../models/user.dart';
import '../config/api_config.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../providers/dashboard_provider.dart';
import 'api_client.dart';
import '../utils/logger.dart';

class AuthService extends ChangeNotifier {
  static final AuthService _instance = AuthService._internal();
  
  factory AuthService() => _instance;
  
  AuthService._internal();

  final Logger _logger = Logger('AuthService');
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
    await prefs.remove('refresh_token');
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
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          throw Exception('La conexión tardó demasiado. Intenta nuevamente.');
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        // Guardar token
        await _saveToken(data['access_token']);
        
        // Guardar refresh token si existe
        if (data['refresh_token'] != null) {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('refresh_token', data['refresh_token']);
        }
        
        // Crear usuario desde la respuesta real del backend
        _currentUser = User(
          id: data['user_id'] ?? data['id'],
          username: data['username'],
          email: data['email'],
          role: data['is_admin'] == true ? UserRole.admin : UserRole.user,
          token: data['access_token'],
          createdAt: DateTime.parse(data['created_at'] ?? DateTime.now().toIso8601String()),
        );
        
        // Precargar datos del dashboard después del login exitoso
        _logger.info('🔄 Precargando dashboard después del login...');
        try {
          // Forzar recarga completa del dashboard
          DashboardProvider().clear();  // Limpiar datos antiguos
          await DashboardProvider().loadDashboardData(showLoading: false);
          _logger.info('✅ Dashboard precargado exitosamente');
        } catch (e) {
          _logger.warning('⚠️ Error precargando dashboard: $e');
          // No fallar el login si el dashboard no carga
        }
        
        setLoading(false);
        notifyListeners();
        return true;
      } else {
        setLoading(false);
        
        // Intentar obtener el mensaje de error del servidor
        String errorMessage = 'Error al iniciar sesión';
        try {
          final errorData = jsonDecode(response.body);
          if (errorData['detail'] != null) {
            errorMessage = errorData['detail'];
          }
        } catch (_) {
          // Si no se puede decodificar, usar mensaje genérico basado en código de estado
          switch (response.statusCode) {
            case 401:
              errorMessage = 'Usuario o contraseña incorrectos';
              break;
            case 404:
              errorMessage = 'Usuario no encontrado';
              break;
            case 500:
              errorMessage = 'Error en el servidor. Por favor intenta más tarde';
              break;
            default:
              errorMessage = 'Error al iniciar sesión. Código: ${response.statusCode}';
          }
        }
        
        throw Exception(errorMessage);
      }
    } catch (e) {
      setLoading(false);
      
      // Mejorar mensajes de error antes de relanzar
      if (e.toString().contains('SocketException') || 
          e.toString().contains('Failed host lookup')) {
        throw Exception('No se pudo conectar al servidor. Verifica tu conexión a internet.');
      } else if (e.toString().contains('HandshakeException')) {
        throw Exception('Error de seguridad. No se pudo establecer conexión segura.');
      } else if (e.toString().contains('FormatException')) {
        throw Exception('Respuesta inválida del servidor.');
      }
      
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
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          throw Exception('La conexión tardó demasiado. Intenta nuevamente.');
        },
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        // Después del registro exitoso, hacer login automático
        await login(username, password);
        
        setLoading(false);
        return true;
      } else {
        setLoading(false);
        final responseBody = jsonDecode(response.body);
        
        // Procesar el mensaje de error para hacerlo más amigable
        String errorMessage = 'Error al registrar usuario';
        
        if (responseBody is Map) {
          // Si el error viene en 'detail'
          if (responseBody.containsKey('detail')) {
            final detail = responseBody['detail'];
            
            // Si detail es un string, usarlo directamente
            if (detail is String) {
              errorMessage = detail;
            } 
            // Si detail es un array (error de validación de Pydantic)
            else if (detail is List && detail.isNotEmpty) {
              final firstError = detail.first;
              if (firstError is Map && firstError.containsKey('msg')) {
                // Extraer solo el mensaje de error
                errorMessage = firstError['msg'] ?? errorMessage;
              }
            }
          }
        }
        
        // Limpiar el prefijo "Value error, " si existe
        if (errorMessage.startsWith('Value error, ')) {
          errorMessage = errorMessage.substring(13); // Quitar "Value error, "
        }
        
        // Mejorar mensajes específicos de error
        if (errorMessage.contains('value_error') || errorMessage.contains('Value error')) {
          if (errorMessage.contains('alfanuméricos') || errorMessage.contains('alphanumeric')) {
            errorMessage = 'El nombre de usuario solo puede contener letras, números y guiones bajos';
          } else if (errorMessage.contains('3 caracteres')) {
            errorMessage = 'El nombre de usuario debe tener al menos 3 caracteres';
          }
        }
        
        throw Exception(errorMessage);
      }
    } catch (e) {
      setLoading(false);
      
      // Mejorar mensajes de error antes de relanzar
      if (e.toString().contains('SocketException') || 
          e.toString().contains('Failed host lookup')) {
        throw Exception('No se pudo conectar al servidor. Verifica tu conexión a internet.');
      } else if (e.toString().contains('HandshakeException')) {
        throw Exception('Error de seguridad. No se pudo establecer conexión segura.');
      } else if (e.toString().contains('FormatException')) {
        throw Exception('Respuesta inválida del servidor.');
      }
      
      rethrow;
    }
  }

  Future<void> loadCurrentUser() async {
    await _loadToken();
    if (_token == null) return;

    try {
      final response = await apiClient.get(ApiConfig.me);
      final data = jsonDecode(response.body);
      
      _currentUser = User(
        id: data['id'],
        username: data['username'],
        email: data['email'],
        role: data['is_admin'] == true ? UserRole.admin : UserRole.user,
        token: _token,
        createdAt: DateTime.parse(data['created_at'] ?? DateTime.now().toIso8601String()),
      );
      
      notifyListeners();
    } catch (e) {
      if (e is ApiException && e.statusCode == 401) {
        // Token inválido, limpiar
        await _clearToken();
        _currentUser = null;
        notifyListeners();
      } else {
        // Otro error
        _logger.error('Error loading user: $e');
      }
    }
  }

  Future<void> logout() async {
    try {
      // Intentar hacer logout en el servidor
      if (_token != null) {
        await apiClient.post(ApiConfig.logout);
      }
    } catch (e) {
      _logger.error('Error en logout remoto: $e');
      // Continuar con logout local aunque falle el remoto
    }
    
    _currentUser = null;
    await _clearToken();
    // Limpiar datos del dashboard
    DashboardProvider().clear();
    notifyListeners();
  }
  
  // Método para obtener el usuario actual
  Future<User?> getCurrentUser() async {
    if (_currentUser != null) {
      return _currentUser;
    }
    
    // Si no hay usuario en memoria pero hay token, intentar cargarlo
    await loadCurrentUser();
    return _currentUser;
  }
  
  // Método para limpiar la sesión
  Future<void> clearSession() async {
    _currentUser = null;
    await _clearToken();
    notifyListeners();
  }
  
  // Método para refrescar el token
  Future<String?> refreshToken() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final refreshTokenValue = prefs.getString('refresh_token');
      
      if (refreshTokenValue == null) {
        _logger.warning('⚠️ No hay refresh token disponible');
        return null;
      }
      
      _logger.info('🔄 Intentando renovar token...');
      final response = await http.post(
        Uri.parse(ApiConfig.refreshToken),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode({
          'refresh_token': refreshTokenValue,
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final newToken = data['access_token'];
        
        _logger.info('✅ Token renovado exitosamente');
        
        // Guardar nuevo token
        await _saveToken(newToken);
        
        // Si hay refresh token nuevo (rotación habilitada), guardarlo
        if (data['refresh_token'] != null) {
          await prefs.setString('refresh_token', data['refresh_token']);
          _logger.info('🔄 Refresh token rotado');
        }
        
        return newToken;
      } else if (response.statusCode == 401) {
        _logger.error('❌ Refresh token inválido o expirado');
        // Limpiar tokens y forzar nuevo login
        await _clearToken();
        _currentUser = null;
        notifyListeners();
      }
      
      return null;
    } catch (e) {
      _logger.error('❌ Error refreshing token: $e');
      return null;
    }
  }
  
  // Método para validar token
  Future<bool> validateToken() async {
    if (_token == null) {
      await _loadToken();
      if (_token == null) return false;
    }
    
    try {
      // Intentar hacer una llamada simple para verificar el token
      final response = await http.get(
        Uri.parse(ApiConfig.me),
        headers: _headers,
      ).timeout(
        const Duration(seconds: 5),
        onTimeout: () {
          throw TimeoutException('Timeout validando token');
        },
      );
      
      if (response.statusCode == 200) {
        return true;
      } else if (response.statusCode == 401) {
        // Token inválido - intentar refresh
        final newToken = await refreshToken();
        return newToken != null;
      }
      
      return false;
    } catch (e) {
      _logger.error('Error validating token: $e');
      // En caso de error de red, asumir que el token es válido
      // para no desloguear al usuario innecesariamente
      if (e.toString().contains('SocketException') || 
          e.toString().contains('TimeoutException')) {
        return true; // Mantener al usuario logueado si es error de red
      }
      return false;
    }
  }

  // Método para cambiar email con validación estricta
  Future<Map<String, dynamic>> changeEmailWithValidation(String newEmail) async {
    if (_currentUser == null || _token == null) throw Exception('No autenticado');
    
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.baseUrl}/users/change-email-validated'),
        headers: _headers,
        body: jsonEncode({
          'new_email': newEmail,
        }),
      );
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else if (response.statusCode == 400) {
        final errorData = jsonDecode(response.body);
        throw Exception(jsonEncode(errorData['detail']));
      } else {
        throw Exception('Error al validar email: ${response.statusCode}');
      }
    } catch (e) {
      _logger.error('Error en changeEmailWithValidation: $e');
      rethrow;
    }
  }
  
  // Método para verificar código de cambio de email
  Future<Map<String, dynamic>> verifyEmailChangeCode({
    required String token,
    required String code,
  }) async {
    if (_currentUser == null || _token == null) throw Exception('No autenticado');
    
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.baseUrl}/users/verify-email-change-code'),
        headers: _headers,
        body: jsonEncode({
          'token': token,
          'code': code,
        }),
      );
      
      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        
        // Actualizar usuario local si el cambio fue exitoso
        if (responseData['status'] == 'success' && responseData['user'] != null) {
          final userData = responseData['user'];
          _currentUser = User(
            id: userData['id'],
            username: userData['username'],
            email: userData['email'],
            role: userData['is_admin'] == true ? UserRole.admin : UserRole.user,
            token: _token,
            createdAt: DateTime.parse(userData['created_at'] ?? _currentUser!.createdAt.toIso8601String()),
          );
          notifyListeners();
        }
        
        return responseData;
      } else {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['detail'] ?? 'Error al verificar código');
      }
    } catch (e) {
      _logger.error('Error en verifyEmailChangeCode: $e');
      rethrow;
    }
  }
  
  // Método para refrescar datos del usuario
  Future<void> refreshUserData() async {
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
          token: _token,
          createdAt: DateTime.parse(data['created_at'] ?? DateTime.now().toIso8601String()),
        );
        
        notifyListeners();
      }
    } catch (e) {
      _logger.error('Error refreshing user data: $e');
    }
  }

  // Método para almacenar información sobre cambio de email pendiente
  Future<void> _storePendingEmailChange(Map<String, dynamic> data) async {
    final prefs = await SharedPreferences.getInstance();
    
    // Extraer el token si viene en la respuesta
    if (data['verification_token'] != null) {
      // Si el token viene codificado en base64, intentar decodificarlo
      try {
        final decoded = json.decode(utf8.decode(base64.decode(data['verification_token'])));
        if (decoded['token'] != null) {
          data['token'] = decoded['token'];
        }
      } catch (e) {
        // Si no se puede decodificar, asumir que es el token directo
        data['token'] = data['verification_token'];
      }
    }
    
    await prefs.setString('pending_email_change', jsonEncode(data));
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
          final errorData = jsonDecode(passwordResponse.body);
          String errorMessage = 'Error al cambiar la contraseña';
          
          if (errorData['detail'] != null) {
            errorMessage = errorData['detail'];
            if (errorMessage.contains('incorrect')) {
              errorMessage = 'Contraseña actual incorrecta';
            }
          }
          
          throw Exception(errorMessage);
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
          final responseData = jsonDecode(response.body);
          
          // Verificar si hay confirmación pendiente
          if (responseData['status'] == 'pending_confirmation') {
            // Almacenar información sobre la confirmación pendiente
            await _storePendingEmailChange({
              'old_email': responseData['old_email'],
              'new_email': responseData['new_email'],
              'message': responseData['message'],
            });
            
            // El username puede haber cambiado aunque el email esté pendiente
            if (updateData['username'] != null) {
              _currentUser = User(
                id: _currentUser!.id,
                username: updateData['username'],
                email: _currentUser!.email, // Mantener email anterior
                role: _currentUser!.role,
                token: _token,
                createdAt: _currentUser!.createdAt,
              );
              notifyListeners();
            }
            
            setLoading(false);
            return true;
          } else {
            // Actualización completa (admin o sin cambio de email)
            final userData = responseData is Map && responseData.containsKey('user') 
                ? responseData['user'] 
                : responseData;
            
            _currentUser = User(
              id: userData['id'],
              username: userData['username'],
              email: userData['email'],
              role: userData['is_admin'] == true ? UserRole.admin : UserRole.user,
              token: _token,
              createdAt: DateTime.parse(userData['created_at'] ?? _currentUser!.createdAt.toIso8601String()),
            );
            notifyListeners();
          }
        } else {
          // Manejar errores específicos
          final errorData = jsonDecode(response.body);
          String errorMessage = 'Error al actualizar el perfil';
          
          if (errorData['detail'] != null) {
            errorMessage = errorData['detail'];
          }
          
          throw Exception(errorMessage);
        }
      }
      
      setLoading(false);
      return true;
    } catch (e) {
      setLoading(false);
      _logger.error('Error updating profile: $e');
      rethrow;
    }
  }
}
