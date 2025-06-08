import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';
import '../models/document.dart';
import '../models/chat.dart';
import '../models/user.dart';

class AdminService {
  static const String _tokenKey = 'auth_token';

  // Obtener el token de autenticación
  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  // Configurar headers con autenticación
  Future<Map<String, String>> _getHeaders() async {
    final token = await _getToken();
    if (token == null) {
      throw Exception('No authentication token found');
    }

    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };
  }

  // Obtener TODOS los documentos del sistema (para administradores)
  Future<List<Document>> getAllDocuments({
    int skip = 0,
    int limit = 500, // Límite máximo permitido por el backend
  }) async {
    try {
      debugPrint('🔄 [ADMIN] Cargando TODOS los documentos del sistema...');
      final headers = await _getHeaders();
      
      // Usar el endpoint admin correcto que sí existe en el backend
      String url = '${ApiConfig.baseUrl}/documents/admin/all?skip=$skip&limit=$limit';
      
      final response = await http.get(
        Uri.parse(url),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        debugPrint('✅ [ADMIN] Documentos totales cargados: ${jsonList.length}');
        return jsonList.map((json) => Document.fromJson(json)).toList();
      } else if (response.statusCode == 403) {
        throw Exception('No tienes permisos de administrador');
      } else {
        throw Exception('Failed to load all documents: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('❌ [ADMIN] Error al cargar documentos: $e');
      throw Exception('Error loading all documents: $e');
    }
  }

  // Obtener TODOS los chats del sistema (para administradores)
  Future<List<ChatModel>> getAllChats({
    int skip = 0,
    int limit = 500, // Límite máximo permitido por el backend
  }) async {
    try {
      debugPrint('🔄 [ADMIN] Cargando TODOS los chats del sistema...');
      final headers = await _getHeaders();
      
      // Usar el endpoint admin correcto que sí existe en el backend
      String url = '${ApiConfig.baseUrl}/chats/admin/all?skip=$skip&limit=$limit';
      
      debugPrint('🌐 [ADMIN] URL: $url');
      debugPrint('🔑 [ADMIN] Headers: $headers');
      
      final response = await http.get(
        Uri.parse(url),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      debugPrint('📦 [ADMIN] Response status: ${response.statusCode}');
      debugPrint('📦 [ADMIN] Response body: ${response.body.substring(0, response.body.length > 200 ? 200 : response.body.length)}...');

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        debugPrint('✅ [ADMIN] Chats totales cargados: ${jsonList.length}');
        return jsonList.map((json) => ChatModel.fromJson(json)).toList();
      } else if (response.statusCode == 403) {
        throw Exception('No tienes permisos de administrador');
      } else {
        throw Exception('Failed to load all chats: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      debugPrint('❌ [ADMIN] Error al cargar chats: $e');
      throw Exception('Error loading all chats: $e');
    }
  }

  // Obtener estadísticas reales del sistema
  Future<Map<String, dynamic>> getAdminStatistics() async {
    try {
      debugPrint('🔄 [ADMIN] Cargando estadísticas del sistema...');
      final headers = await _getHeaders();
      
      // Intentar endpoint admin primero
      String url = '${ApiConfig.baseUrl}/admin/statistics';
      
      try {
        final response = await http.get(
          Uri.parse(url),
          headers: headers,
        ).timeout(const Duration(seconds: 10));

        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          debugPrint('✅ [ADMIN] Estadísticas cargadas');
          return data;
        }
      } catch (e) {
        debugPrint('⚠️ Endpoint admin no disponible, usando estadísticas normales...');
      }
      
      // Fallback al endpoint normal
      return {};
    } catch (e) {
      debugPrint('❌ [ADMIN] Error al cargar estadísticas: $e');
      throw Exception('Error loading statistics: $e');
    }
  }
}
