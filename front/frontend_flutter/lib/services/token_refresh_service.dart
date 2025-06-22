import 'dart:async';
import 'package:flutter/material.dart';
import 'auth_service.dart';
import '../utils/logger.dart';

class TokenRefreshService {
  static final TokenRefreshService _instance = TokenRefreshService._internal();
  factory TokenRefreshService() => _instance;
  TokenRefreshService._internal();

  final AuthService _authService = AuthService();
  final Logger _logger = Logger('TokenRefreshService');
  Timer? _refreshTimer;
  bool _isInitialized = false;

  // Inicializar el servicio
  Future<void> initialize() async {
    if (_isInitialized) return;
    _isInitialized = true;

    // Cargar token existente
    await _authService.loadCurrentUser();

    // Si hay usuario autenticado, programar renovación
    if (_authService.isAuthenticated) {
      _scheduleTokenRefresh();
    }

    // Escuchar cambios en la autenticación
    _authService.addListener(_onAuthStateChanged);
  }

  // Manejar cambios en el estado de autenticación
  void _onAuthStateChanged() {
    if (_authService.isAuthenticated && _refreshTimer == null) {
      _scheduleTokenRefresh();
    } else if (!_authService.isAuthenticated && _refreshTimer != null) {
      _cancelTokenRefresh();
    }
  }

  // Programar renovación automática
  void _scheduleTokenRefresh() {
    _cancelTokenRefresh(); // Cancelar timer anterior si existe

    // Renovar token 2 minutos antes de expirar
    // Por defecto los tokens duran 15 minutos
    const refreshInterval = Duration(minutes: 13);

    _refreshTimer = Timer.periodic(refreshInterval, (timer) async {
      _logger.info('⏰ Intentando renovar token automáticamente...');
      
      try {
        final newToken = await _authService.refreshToken();
        if (newToken != null) {
          _logger.info('✅ Token renovado automáticamente');
        } else {
          _logger.error('❌ No se pudo renovar el token');
          _cancelTokenRefresh();
          
          // Si no se puede renovar, limpiar sesión
          await _authService.clearSession();
        }
      } catch (e) {
        _logger.error('❌ Error renovando token: $e');
        _cancelTokenRefresh();
        
        // Si hay error grave, limpiar sesión
        if (e.toString().contains('401') || 
            e.toString().contains('Invalid refresh token')) {
          await _authService.clearSession();
        }
      }
    });

    _logger.info('⏰ Renovación automática programada cada 13 minutos');
  }

  // Cancelar renovación automática
  void _cancelTokenRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = null;
    _logger.info('⏰ Renovación automática cancelada');
  }

  // Limpiar recursos
  void dispose() {
    _cancelTokenRefresh();
    _authService.removeListener(_onAuthStateChanged);
    _isInitialized = false;
  }

  // Validar token manualmente
  Future<bool> validateAndRefreshIfNeeded() async {
    // Primero validar si el token es válido
    final isValid = await _authService.validateToken();
    
    if (!isValid && _authService.isAuthenticated) {
      // Intentar renovar
      _logger.info('🔄 Token inválido, intentando renovar...');
      final newToken = await _authService.refreshToken();
      return newToken != null;
    }
    
    return isValid;
  }
}

// Widget wrapper para inicializar el servicio
class TokenRefreshWrapper extends StatefulWidget {
  final Widget child;
  
  const TokenRefreshWrapper({
    super.key,
    required this.child,
  });

  @override
  State<TokenRefreshWrapper> createState() => _TokenRefreshWrapperState();
}

class _TokenRefreshWrapperState extends State<TokenRefreshWrapper> {
  final TokenRefreshService _tokenService = TokenRefreshService();

  @override
  void initState() {
    super.initState();
    _tokenService.initialize();
  }

  @override
  void dispose() {
    _tokenService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return widget.child;
  }
}
