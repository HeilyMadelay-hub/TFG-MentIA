import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Clase base para todos los servicios
/// Proporciona funcionalidad común como manejo de tokens y headers
abstract class BaseService {
  static const String _tokenKey = 'auth_token';

  /// Obtener el token de autenticación almacenado
  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  /// Guardar token de autenticación
  Future<void> saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
  }

  /// Limpiar token de autenticación
  Future<void> clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
  }

  /// Obtener headers para peticiones HTTP
  Future<Map<String, String>> getHeaders({
    bool isMultipart = false,
    bool requireAuth = true,
  }) async {
    final headers = <String, String>{};

    // Solo agregar Content-Type si no es multipart
    if (!isMultipart) {
      headers['Content-Type'] = 'application/json';
    }

    headers['Accept'] = 'application/json';

    // Agregar token de autenticación si es requerido
    if (requireAuth) {
      final token = await getToken();
      if (token == null) {
        throw Exception('No authentication token found');
      }
      headers['Authorization'] = 'Bearer $token';
    }

    return headers;
  }

  /// Manejar respuesta HTTP común
  dynamic handleResponse(http.Response response,
      {bool expectNoContent = false}) {
    if (expectNoContent && response.statusCode == 204) {
      return true;
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) {
        return null;
      }
      try {
        return json.decode(response.body);
      } catch (e) {
        // Si no es JSON válido, devolver el body como string
        return response.body;
      }
    } else if (response.statusCode == 401) {
      // Manejar error de autenticación
      debugPrint('❌ Error 401: Token inválido o expirado');
      
      // Limpiar token
      clearToken();
      
      // Lanzar excepción especial para 401
      throw HttpException(
        'Sesión expirada. Por favor, inicia sesión nuevamente.',
        statusCode: 401,
      );
    } else {
      // Intentar obtener el mensaje de error del backend
      String errorMessage =
          'Request failed with status: ${response.statusCode}';
      try {
        final errorData = json.decode(response.body);
        errorMessage =
            errorData['detail'] ?? errorData['message'] ?? errorMessage;
      } catch (_) {
        // Si no se puede parsear el error, usar el mensaje por defecto
      }
      throw HttpException(errorMessage, statusCode: response.statusCode);
    }
  }

  /// Construir query parameters
  String buildQueryString(Map<String, dynamic> params) {
    if (params.isEmpty) return '';

    final queryParams = <String>[];
    params.forEach((key, value) {
      if (value != null) {
        if (value is List) {
          // Para listas, agregar cada elemento
          for (var item in value) {
            queryParams.add('$key=${Uri.encodeComponent(item.toString())}');
          }
        } else {
          queryParams.add('$key=${Uri.encodeComponent(value.toString())}');
        }
      }
    });

    return queryParams.isEmpty ? '' : '?${queryParams.join('&')}';
  }
}

/// Excepción personalizada para errores HTTP
class HttpException implements Exception {
  final String message;
  final int? statusCode;

  HttpException(this.message, {this.statusCode});

  @override
  String toString() => message;

  /// Verifica si es un error de autenticación
  bool get isAuthError => statusCode == 401 || statusCode == 403;

  /// Verifica si es un error de no encontrado
  bool get isNotFound => statusCode == 404;

  /// Verifica si es un error del servidor
  bool get isServerError => statusCode != null && statusCode! >= 500;
}
