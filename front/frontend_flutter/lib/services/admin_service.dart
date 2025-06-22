import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'api_client.dart';
import '../config/api_config.dart';
import '../models/document.dart';
import '../models/chat.dart';
import '../models/user.dart';

class AdminService {
  final ApiClient _apiClient = apiClient;

  // Obtener TODOS los documentos del sistema (para administradores)
  Future<List<Document>> getAllDocuments({
    int skip = 0,
    int limit = 100,
    String sortBy = 'created_at',
    String order = 'desc',
    int? userFilter,
    String? contentTypeFilter,
  }) async {
    try {
      debugPrint('🔄 [ADMIN] Cargando TODOS los documentos del sistema...');
      
      // ✅ NUEVA URL CORRECTA: /admin/documents
      final url = ApiConfig.adminDocumentsWithFilters(
        skip: skip,
        limit: limit,
        sortBy: sortBy,
        order: order,
        userFilter: userFilter,
        contentTypeFilter: contentTypeFilter,
      );
      
      debugPrint('📡 [ADMIN SERVICE] Calling: $url');
      
      final response = await _apiClient.get(url);

      final List<dynamic> jsonList = json.decode(response.body);
      debugPrint('✅ [ADMIN] Documentos totales cargados: ${jsonList.length}');
      return jsonList.map((json) => Document.fromJson(json)).toList();
    } catch (e) {
      debugPrint('❌ [ADMIN] Error al cargar documentos: $e');
      if (e is ApiException && e.statusCode == 403) {
        throw Exception('No tienes permisos de administrador');
      }
      throw Exception('Error loading all documents: $e');
    }
  }

  // Obtener TODOS los chats del sistema (para administradores)
  Future<List<Chat>> getAllChats({
    int skip = 0,
    int limit = 500, // Límite máximo permitido por el backend
  }) async {
    try {
      debugPrint('🔄 [ADMIN] Cargando TODOS los chats del sistema...');
      
      // Usar el endpoint admin correcto que sí existe en el backend
      final response = await _apiClient.get(
        '${ApiConfig.baseUrl}/chats/admin/all',
        queryParams: {
          'skip': skip.toString(),
          'limit': limit.toString(),
        },
      );

      debugPrint('📦 [ADMIN] Response status: ${response.statusCode}');

      final List<dynamic> jsonList = json.decode(response.body);
      debugPrint('✅ [ADMIN] Chats totales cargados: ${jsonList.length}');
      return jsonList.map((json) => Chat.fromJson(json)).toList();
    } catch (e) {
      debugPrint('❌ [ADMIN] Error al cargar chats: $e');
      if (e is ApiException && e.statusCode == 403) {
        throw Exception('No tienes permisos de administrador');
      }
      throw Exception('Error loading all chats: $e');
    }
  }

  // 🆕 NUEVO MÉTODO: Obtener estadísticas avanzadas de documentos
  Future<Map<String, dynamic>> getDocumentsStatistics({
    String timePeriod = 'all',
    String groupBy = 'user',
  }) async {
    try {
      debugPrint('📈 [ADMIN] Obteniendo estadísticas de documentos...');
      
      // ✅ NUEVA URL CORRECTA: /admin/documents/stats
      final url = ApiConfig.adminDocumentsStatsWithPeriod(
        timePeriod: timePeriod,
        groupBy: groupBy,
      );
      
      debugPrint('📈 [ADMIN SERVICE] Getting documents stats: $url');
      
      final response = await _apiClient.get(url);

      final data = json.decode(response.body);
      debugPrint('✅ [ADMIN] Estadísticas de documentos recibidas');
      return data;
    } catch (e) {
      debugPrint('❌ [ADMIN] Error al obtener estadísticas de documentos: $e');
      throw Exception('Error al obtener estadísticas de documentos: $e');
    }
  }
  
  // 🆕 NUEVO MÉTODO: Eliminar documento como administrador
  Future<bool> deleteDocumentAsAdmin(int documentId, {bool force = false}) async {
    try {
      debugPrint('🗑️ [ADMIN] Eliminando documento como admin: ID=$documentId');
      
      final url = ApiConfig.deleteDocumentAdmin(documentId, force: force);
      
      debugPrint('🗑️ [ADMIN SERVICE] Deleting document: $url');
      
      final response = await _apiClient.delete(url);

      if (response.statusCode == 200) {
        debugPrint('✅ [ADMIN] Documento eliminado exitosamente');
        return true;
      } else {
        debugPrint('❌ [ADMIN] Error al eliminar: ${response.statusCode}');
        return false;
      }
    } catch (e) {
      debugPrint('❌ [ADMIN] Error eliminando documento: $e');
      throw Exception('Error al eliminar documento: $e');
    }
  }
  
  // Obtener estadísticas generales del sistema
  Future<Map<String, dynamic>> getAdminStatistics() async {
    try {
      debugPrint('🔄 [ADMIN] Cargando estadísticas del sistema...');
      
      // Usar el endpoint correcto para estadísticas generales
      final response = await _apiClient.get(ApiConfig.adminStats);

      final data = json.decode(response.body);
      debugPrint('✅ [ADMIN] Estadísticas generales cargadas');
      return data;
    } catch (e) {
      debugPrint('❌ [ADMIN] Error al cargar estadísticas: $e');
      throw Exception('Error loading statistics: $e');
    }
  }
}
