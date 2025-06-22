import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'api_client.dart';
import '../config/api_config.dart';

class StatisticsService {
  final ApiClient _apiClient = apiClient;
  
  static const String _cacheKey = 'cached_statistics';
  static const String _cacheTimeKey = 'cached_statistics_time';
  static const String _dashboardCacheKey = 'cached_dashboard';
  static const String _dashboardCacheTimeKey = 'cached_dashboard_time';
  static const Duration _cacheValidDuration = Duration(minutes: 5);
  
  /// Guarda las estadísticas en caché
  Future<void> _saveStatisticsToCache(Map<String, int> stats) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_cacheKey, json.encode(stats));
      await prefs.setInt(_cacheTimeKey, DateTime.now().millisecondsSinceEpoch);
      debugPrint('💾 Estadísticas guardadas en caché');
    } catch (e) {
      debugPrint('❌ Error al guardar caché: $e');
    }
  }
  
  /// Obtiene las estadísticas desde el caché
  Future<Map<String, int>?> _getStatisticsFromCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final cachedData = prefs.getString(_cacheKey);
      final cacheTime = prefs.getInt(_cacheTimeKey);
      
      if (cachedData != null && cacheTime != null) {
        final age = DateTime.now().millisecondsSinceEpoch - cacheTime;
        if (age < _cacheValidDuration.inMilliseconds) {
          debugPrint('📦 Usando estadísticas del caché');
          final decoded = json.decode(cachedData) as Map<String, dynamic>;
          return {
            'total_users': decoded['total_users'] as int,
            'total_documents': decoded['total_documents'] as int,
            'active_chats': decoded['active_chats'] as int,
          };
        }
      }
    } catch (e) {
      debugPrint('❌ Error al leer caché: $e');
    }
    return null;
  }
  
  /// Obtiene las estadísticas globales del sistema
  Future<Map<String, int>> getGlobalStatistics() async {
    try {
      debugPrint('🔄 Solicitando estadísticas a: ${ApiConfig.globalStatistics}');
      
      // Usar endpoint público sin autenticación (no requiere ApiClient)
      // Este endpoint es público y no requiere token
      final response = await http.get(
        Uri.parse(ApiConfig.globalStatistics),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ).timeout(
        const Duration(seconds: 3),
        onTimeout: () {
          debugPrint('❌ Timeout al obtener estadísticas');
          throw Exception('Timeout al obtener estadísticas');
        },
      );
      
      debugPrint('📥 Respuesta recibida - Status: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        debugPrint('📊 Datos procesados: $data');
        
        // El backend devuelve directamente el objeto con las estadísticas
        if (data != null && data is Map<String, dynamic>) {
          final stats = {
            'total_users': (data['total_users'] ?? 0) as int,
            'total_documents': (data['total_documents'] ?? 0) as int,
            'active_chats': (data['active_chats'] ?? 0) as int,
          };
          
          debugPrint('✅ Estadísticas procesadas correctamente: $stats');
          
          // Guardar en caché para uso futuro
          await _saveStatisticsToCache(stats);
          
          return stats;
        }
      }
      
      throw Exception('Invalid response format');
      
    } catch (e) {
      debugPrint('❌ Error completo al obtener estadísticas: $e');
      
      // Intentar obtener datos del caché
      final cachedStats = await _getStatisticsFromCache();
      if (cachedStats != null) {
        debugPrint('📦 Usando estadísticas del caché debido al error');
        return cachedStats;
      }
      
      // Si no hay caché, retornar valores por defecto
      final fallbackStats = {
        'total_users': 0,
        'total_documents': 0,
        'active_chats': 0,
      };
      
      debugPrint('🔄 Usando estadísticas por defecto: $fallbackStats');
      return fallbackStats;
    }
  }
  
  /// Obtiene todos los datos del dashboard en una sola llamada
  Future<Map<String, dynamic>> getDashboardData() async {
    try {
      debugPrint('🔄 Solicitando datos del dashboard...');
      
      // Verificar caché primero
      final cachedData = await _getDashboardFromCache();
      if (cachedData != null) {
        return cachedData;
      }
      
      final response = await _apiClient.get(ApiConfig.dashboard);
      
      debugPrint('📥 Dashboard response: ${response.statusCode}');
      
      final data = json.decode(response.body);
      
      // Guardar en caché
      await _saveDashboardToCache(data);
      
      return data;
    } catch (e) {
      debugPrint('❌ Error obteniendo dashboard: $e');
      
      // Si es error de autenticación, propagar
      if (e is ApiException && (e.statusCode == 401 || e.errorCode == 'SESSION_EXPIRED')) {
        rethrow;
      }
      
      // Intentar cargar por separado como fallback
      return await _loadDashboardDataSeparately();
    }
  }
  
  /// Carga los datos del dashboard por separado (fallback)
  Future<Map<String, dynamic>> _loadDashboardDataSeparately() async {
    // Usar el método existente para estadísticas
    final stats = await getGlobalStatistics();
    
    return {
      'statistics': stats,
      'recent_documents': [], // Se cargarán por separado en el frontend
      'recent_chats': [], // Se cargarán por separado en el frontend
    };
  }
  
  /// Guarda los datos del dashboard en caché
  Future<void> _saveDashboardToCache(Map<String, dynamic> data) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_dashboardCacheKey, json.encode(data));
      await prefs.setInt(_dashboardCacheTimeKey, DateTime.now().millisecondsSinceEpoch);
      debugPrint('💾 Dashboard guardado en caché');
    } catch (e) {
      debugPrint('❌ Error al guardar dashboard en caché: $e');
    }
  }
  
  /// Obtiene los datos del dashboard desde el caché
  Future<Map<String, dynamic>?> _getDashboardFromCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final cachedData = prefs.getString(_dashboardCacheKey);
      final cacheTime = prefs.getInt(_dashboardCacheTimeKey);
      
      if (cachedData != null && cacheTime != null) {
        final age = DateTime.now().millisecondsSinceEpoch - cacheTime;
        if (age < _cacheValidDuration.inMilliseconds) {
          debugPrint('📦 Usando dashboard del caché');
          return json.decode(cachedData) as Map<String, dynamic>;
        }
      }
    } catch (e) {
      debugPrint('❌ Error al leer caché del dashboard: $e');
    }
    return null;
  }
  
  /// Invalida todo el caché de estadísticas para forzar una recarga
  Future<void> invalidateCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_cacheKey);
      await prefs.remove(_cacheTimeKey);
      await prefs.remove(_dashboardCacheKey);
      await prefs.remove(_dashboardCacheTimeKey);
      debugPrint('🗑️ Caché de estadísticas invalidado');
    } catch (e) {
      debugPrint('❌ Error al invalidar caché: $e');
    }
  }
  
  /// Refresca las estadísticas globales forzando una nueva carga
  Future<Map<String, int>> refreshGlobalStatistics() async {
    await invalidateCache();
    return getGlobalStatistics();
  }
  
  /// Refresca el dashboard completo forzando una nueva carga
  Future<Map<String, dynamic>> refreshDashboard() async {
    await invalidateCache();
    return getDashboardData();
  }
}
