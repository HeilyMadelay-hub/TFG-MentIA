import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;
import 'auth_service.dart';
import '../config/api_config.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final String? errorCode;

  ApiException({required this.message, this.statusCode, this.errorCode});

  @override
  String toString() => message;
}

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal();

  final AuthService _authService = AuthService();
  
  // Mutex para evitar múltiples renovaciones simultáneas
  bool _isRefreshing = false;
  final List<Completer<String?>> _refreshCompleterQueue = [];

  Future<Map<String, String>> _getHeaders() async {
    final token = await _authService.getToken();
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<http.Response> _handleResponse(
    Future<http.Response> Function() request, {
    bool retry = true,
  }) async {
    try {
      final response = await request();
      
      // Si la respuesta es exitosa, devolverla
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return response;
      }
      
      // Si es 401 y tenemos código TOKEN_EXPIRED
      if (response.statusCode == 401 && retry) {
        final body = jsonDecode(response.body);
        final errorCode = body['error_code'];
        
        if (errorCode == 'TOKEN_EXPIRED') {
          print('🔄 Token expirado, intentando renovar...');
          
          // Renovar token
          final newToken = await _refreshTokenWithQueue();
          
          if (newToken != null) {
            // Reintentar la petición con el nuevo token
            return _handleResponse(request, retry: false);
          } else {
            // No se pudo renovar, forzar logout
            await _authService.logout();
            throw ApiException(
              message: 'Sesión expirada. Por favor, inicia sesión nuevamente.',
              statusCode: 401,
              errorCode: 'SESSION_EXPIRED',
            );
          }
        }
      }
      
      // Para otros errores, lanzar excepción
      final errorBody = _parseErrorResponse(response);
      throw ApiException(
        message: errorBody['detail'] ?? 'Error en la petición',
        statusCode: response.statusCode,
      );
      
    } catch (e) {
      if (e is ApiException) {
        rethrow;
      }
      throw ApiException(message: 'Error de conexión: $e');
    }
  }

  Future<String?> _refreshTokenWithQueue() async {
    // Si ya estamos renovando, agregar a la cola
    if (_isRefreshing) {
      final completer = Completer<String?>();
      _refreshCompleterQueue.add(completer);
      return completer.future;
    }
    
    _isRefreshing = true;
    
    try {
      final newToken = await _authService.refreshToken();
      
      // Resolver todos los completers en la cola
      for (final completer in _refreshCompleterQueue) {
        completer.complete(newToken);
      }
      _refreshCompleterQueue.clear();
      
      return newToken;
    } catch (e) {
      // Rechazar todos los completers en la cola
      for (final completer in _refreshCompleterQueue) {
        completer.completeError(e);
      }
      _refreshCompleterQueue.clear();
      
      rethrow;
    } finally {
      _isRefreshing = false;
    }
  }

  Map<String, dynamic> _parseErrorResponse(http.Response response) {
    try {
      return jsonDecode(response.body);
    } catch (e) {
      return {'detail': 'Error desconocido'};
    }
  }

  // GET Request
  Future<http.Response> get(String url, {Map<String, String>? queryParams}) async {
    final uri = Uri.parse(url);
    final uriWithParams = queryParams != null 
        ? uri.replace(queryParameters: queryParams) 
        : uri;
    
    return _handleResponse(() async {
      final headers = await _getHeaders();
      return http.get(uriWithParams, headers: headers);
    });
  }

  // POST Request
  Future<http.Response> post(String url, {dynamic body}) async {
    return _handleResponse(() async {
      final headers = await _getHeaders();
      return http.post(
        Uri.parse(url),
        headers: headers,
        body: body != null ? jsonEncode(body) : null,
      );
    });
  }

  // POST Form Data
  Future<http.Response> postForm(String url, Map<String, String> body) async {
    return _handleResponse(() async {
      final token = await _authService.getToken();
      final headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };
      
      return http.post(
        Uri.parse(url),
        headers: headers,
        body: body,
      );
    });
  }

  // PUT Request
  Future<http.Response> put(String url, {dynamic body}) async {
    return _handleResponse(() async {
      final headers = await _getHeaders();
      return http.put(
        Uri.parse(url),
        headers: headers,
        body: body != null ? jsonEncode(body) : null,
      );
    });
  }

  // DELETE Request
  Future<http.Response> delete(String url) async {
    return _handleResponse(() async {
      final headers = await _getHeaders();
      return http.delete(Uri.parse(url), headers: headers);
    });
  }

  // Multipart Request (para subir archivos)
  Future<http.Response> multipart(
    String url,
    String method, {
    Map<String, String>? fields,
    List<http.MultipartFile>? files,
  }) async {
    final token = await _authService.getToken();
    
    final request = http.MultipartRequest(method, Uri.parse(url));
    
    // Headers
    request.headers['Accept'] = 'application/json';
    if (token != null) {
      request.headers['Authorization'] = 'Bearer $token';
    }
    
    // Fields
    if (fields != null) {
      request.fields.addAll(fields);
    }
    
    // Files
    if (files != null) {
      request.files.addAll(files);
    }
    
    try {
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      
      // Manejar la respuesta con el mismo sistema
      if (response.statusCode == 401) {
        final body = jsonDecode(response.body);
        if (body['error_code'] == 'TOKEN_EXPIRED') {
          final newToken = await _refreshTokenWithQueue();
          
          if (newToken != null) {
            // Recrear la petición con el nuevo token
            return multipart(url, method, fields: fields, files: files);
          }
        }
      }
      
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return response;
      }
      
      throw ApiException(
        message: _parseErrorResponse(response)['detail'] ?? 'Error en la petición',
        statusCode: response.statusCode,
      );
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(message: 'Error de conexión: $e');
    }
  }
}

// Instancia global para facilitar el uso
final apiClient = ApiClient();
