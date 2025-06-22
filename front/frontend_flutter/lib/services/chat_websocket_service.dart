// ignore_for_file: avoid_print

import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;
import '../models/message.dart';
import '../config/api_config.dart';
import 'auth_service.dart';
import '../utils/logger.dart';

class ChatWebSocketService extends ChangeNotifier {
  static final ChatWebSocketService _instance = ChatWebSocketService._internal();
  
  factory ChatWebSocketService() => _instance;
  
  ChatWebSocketService._internal();

  final Logger _logger = Logger('ChatWebSocketService');
  WebSocketChannel? _channel;
  int? _currentChatId;
  StreamSubscription? _subscription;
  Timer? _pingTimer;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  static const int _maxReconnectAttempts = 5;
  bool _isConnecting = false;
  bool _disposed = false;
  bool _manuallyDisconnected = false;
  String? _lastError;
  
  // Stream para mensajes recibidos
  final _messagesController = StreamController<Message>.broadcast();
  Stream<Message> get messages => _messagesController.stream;
  
  // Stream para estado de conexión
  final _connectionStateController = StreamController<bool>.broadcast();
  Stream<bool> get connectionState => _connectionStateController.stream;
  
  bool get isConnected => _channel?.closeCode == null;
  String? get lastError => _lastError;

  Future<bool> connect(int chatId) async {
    if (_isConnecting) {
      _logger.info('⏳ Ya hay una conexión en progreso');
      return false;
    }
    
    _isConnecting = true;
    _currentChatId = chatId;
    _manuallyDisconnected = false;
    _lastError = null;
    
    try {
      await disconnect();
      
      final token = await AuthService().getToken();
      if (token == null) {
        _lastError = 'No hay token de autenticación';
        _logger.error('❌ No hay token de autenticación');
        _isConnecting = false;
        return false;
      }
      
      // Validar token antes de conectar
      final isValid = await AuthService().validateToken();
      if (!isValid) {
        _lastError = 'Token inválido o expirado';
        _logger.error('❌ Token inválido o expirado');
        _isConnecting = false;
        return false;
      }
      
      final wsUrl = Uri.parse('${ApiConfig.wsBase}/chat/$chatId?token=$token');
      _logger.info('Conectando a WebSocket: $wsUrl');
      
      _channel = WebSocketChannel.connect(wsUrl);
      
      _subscription = _channel!.stream.listen(
        _handleMessage,
        onError: (error) {
          _lastError = 'Error de conexión';
          _logger.error('Error en WebSocket: $error');
          if (!_manuallyDisconnected) {
            _scheduleReconnect();
          }
        },
        onDone: () {
          _logger.warning('WebSocket desconectado');
          _connectionStateController.add(false);
          if (!_manuallyDisconnected && !_disposed) {
            _scheduleReconnect();
          }
        },
        cancelOnError: false,
      );
      
      // Esperar confirmación de conexión
      await Future.delayed(const Duration(milliseconds: 500));
      
      if (isConnected) {
        _reconnectAttempts = 0;
        _startPingTimer();
        _connectionStateController.add(true);
        _logger.info('✅ WebSocket conectado exitosamente');
        _isConnecting = false;
        return true;
      } else {
        _logger.error('❌ No se pudo establecer la conexión');
        _isConnecting = false;
        return false;
      }
    } catch (e) {
      _lastError = 'Error al conectar';
      _logger.error('Error conectando WebSocket: $e');
      _isConnecting = false;
      if (!_manuallyDisconnected) {
        _scheduleReconnect();
      }
      return false;
    }
  }

  void _handleMessage(dynamic message) {
    try {
      _logger.debug('Mensaje recibido: $message');
      
      if (message == 'pong') {
        _logger.debug('Pong recibido');
        return;
      }
      
      final data = jsonDecode(message);
      
      switch (data['type']) {
        case 'connection_success':
          _logger.info('Conexión WebSocket establecida');
          break;
          
        case 'message':
          final msg = Message.fromJson(data['data']);
          _messagesController.add(msg);
          break;
          
        case 'error':
          _handleError(data);
          break;
          
        case 'stream_start':
          _logger.info('Stream iniciado: ${data['stream_id']}');
          notifyListeners();
          break;
          
        case 'stream_chunk':
          notifyListeners();
          break;
          
        case 'stream_end':
          _logger.info('Stream finalizado: ${data['stream_id']}');
          notifyListeners();
          break;
          
        case 'message_saved':
          // Mensaje guardado exitosamente
          break;
          
        default:
          _logger.debug('Mensaje WebSocket no manejado: ${data['type']}');
      }
    } catch (e) {
      _logger.error('Error procesando mensaje: $e');
    }
  }
  
  void _handleError(Map<String, dynamic> errorData) {
    final error = errorData['error'] ?? 'Error desconocido';
    _lastError = error;
    
    // Si es error de autenticación, no reintentar
    if (error.toString().contains('401') || 
        error.toString().contains('Unauthorized') ||
        error.toString().contains('Token expired')) {
      _logger.error('❌ Error de autenticación: $error');
      _manuallyDisconnected = true;
      disconnect();
      
      // Limpiar sesión
      AuthService().clearSession();
    } else {
      _logger.error('Error del servidor: $error');
    }
  }

  void _scheduleReconnect() {
    if (_disposed || _manuallyDisconnected) return;
    
    _reconnectTimer?.cancel();
    
    if (_reconnectAttempts >= _maxReconnectAttempts) {
      _logger.error('❌ Máximo número de intentos de reconexión alcanzado');
      _lastError = 'No se pudo reconectar al servidor';
      return;
    }
    
    _reconnectAttempts++;
    final delay = Duration(seconds: _reconnectAttempts * 2);
    
    _logger.info('Intento de reconexión $_reconnectAttempts de $_maxReconnectAttempts');
    
    _reconnectTimer = Timer(delay, () async {
      if (!_disposed && !_manuallyDisconnected && _currentChatId != null) {
        await connect(_currentChatId!);
      }
    });
  }

  void _startPingTimer() {
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(const Duration(seconds: 30), (timer) {
      if (isConnected) {
        try {
          sendMessage({'type': 'ping'});
          _logger.debug('Ping enviado');
        } catch (e) {
          _logger.error('Error enviando ping: $e');
        }
      }
    });
  }

  Future<void> disconnect() async {
    _manuallyDisconnected = true;
    _pingTimer?.cancel();
    _reconnectTimer?.cancel();
    await _subscription?.cancel();
    _channel?.sink.close(status.normalClosure);
    _channel = null;
    _connectionStateController.add(false);
    _logger.info('🔌 WebSocket desconectado');
  }

  void sendMessage(dynamic message) {
    if (!isConnected) {
      _logger.warning('⚠️ No hay conexión WebSocket activa');
      return;
    }
    
    try {
      final jsonMessage = message is String ? message : jsonEncode(message);
      _channel!.sink.add(jsonMessage);
      
      if (message is Map && message['type'] != 'ping') {
        _logger.info('Enviando mensaje: $jsonMessage');
      }
    } catch (e) {
      _logger.error('Error enviando mensaje: $e');
    }
  }

  void sendChatMessage({
    required String content,
    List<int>? documentIds,
    bool stream = true,
  }) {
    sendMessage({
      'content': content,
      'document_ids': documentIds,
      'stream': stream,
    });
  }

  void resetReconnectAttempts() {
    _reconnectAttempts = 0;
  }

  @override
  void dispose() {
    _disposed = true;
    _manuallyDisconnected = true;
    disconnect();
    _messagesController.close();
    _connectionStateController.close();
    super.dispose();
  }
}
