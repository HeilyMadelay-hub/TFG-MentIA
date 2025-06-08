import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';

import '../config/api_config.dart';
import '../models/chat.dart';
import '../services/auth_service.dart';

class DashboardData {
  final Map<String, int> statistics;
  final List<dynamic> recentDocuments;
  final List<ChatModel> recentChats;
  final DateTime lastUpdated;

  DashboardData({
    required this.statistics,
    required this.recentDocuments,
    required this.recentChats,
    required this.lastUpdated,
  });

  // Verificar si los datos son obsoletos (más de 5 minutos)
  bool get isStale {
    return DateTime.now().difference(lastUpdated).inMinutes > 5;
  }
}

class DashboardProvider extends ChangeNotifier {
  static final DashboardProvider _instance = DashboardProvider._internal();
  
  factory DashboardProvider() => _instance;
  
  DashboardProvider._internal();

  DashboardData? _dashboardData;
  bool _isLoading = false;
  String? _error;
  Timer? _refreshTimer;

  DashboardData? get dashboardData => _dashboardData;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get hasData => _dashboardData != null;

  // Estadísticas individuales
  Map<String, int> get statistics => _dashboardData?.statistics ?? {
    'total_users': 0,
    'total_documents': 0,
    'active_chats': 0,
  };

  List<dynamic> get recentDocuments => _dashboardData?.recentDocuments ?? [];
  List<ChatModel> get recentChats => _dashboardData?.recentChats ?? [];

  // Inicializar y precargar datos al hacer login
  Future<void> initializeOnLogin() async {
    print('🚀 Inicializando dashboard al hacer login...');
    await loadDashboardData(showLoading: true);
    
    // Configurar actualización automática cada 5 minutos
    _refreshTimer?.cancel();
    _refreshTimer = Timer.periodic(const Duration(minutes: 5), (_) {
      loadDashboardData(showLoading: false);
    });
  }

  // Cargar datos del dashboard
  Future<void> loadDashboardData({bool showLoading = true}) async {
    print('🔄 DashboardProvider: loadDashboardData llamado (showLoading: $showLoading)');
    
    // Si ya estamos cargando, no hacer nada
    if (_isLoading) {
      print('⚠️ Ya estamos cargando, saliendo...');
      return;
    }

    // Si tenemos datos y no son obsoletos, y no queremos mostrar loading, salir
    if (!showLoading && _dashboardData != null && !_dashboardData!.isStale) {
      print('📦 Usando datos en caché');
      return;
    }

    if (showLoading) {
      _isLoading = true;
      notifyListeners();
    }

    try {
      final token = await AuthService().getToken();
      print('🔑 Token obtenido: ${token != null ? "Sí" : "No"}');
      
      if (token == null) {
        throw Exception('No hay token de autenticación');
      }

      print('🌐 Llamando a: ${ApiConfig.dashboard}');
      final response = await http.get(
        Uri.parse(ApiConfig.dashboard),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      ).timeout(const Duration(seconds: 10));

      print('📡 Response status: ${response.statusCode}');
      print('📤 Response body: ${response.body}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        print('📊 Datos decodificados: $data');
        
        // Verificar y parsear estadísticas
        Map<String, int> statistics = {
          'total_users': 0,
          'total_documents': 0,
          'active_chats': 0,
        };
        
        if (data['statistics'] != null && data['statistics'] is Map) {
          print('📦 Parseando estadísticas: ${data['statistics']}');
          statistics['total_users'] = data['statistics']['total_users'] ?? 0;
          statistics['total_documents'] = data['statistics']['total_documents'] ?? 0;
          statistics['active_chats'] = data['statistics']['active_chats'] ?? 0;
        } else {
          print('⚠️ No se encontraron estadísticas en la respuesta');
        }
        
        print('📊 Estadísticas finales: $statistics');
        
        // Parsear documentos recientes
        List<dynamic> recentDocs = [];
        if (data['recent_documents'] != null && data['recent_documents'] is List) {
          recentDocs = data['recent_documents'];
          print('📄 Documentos recientes: ${recentDocs.length}');
        }
        List<ChatModel> parsedChats = [];
        if (data['recent_chats'] != null && data['recent_chats'] is List) {
          for (var chatData in data['recent_chats']) {
            try {
              // Verificar que sea un mapa
              if (chatData is! Map<String, dynamic>) {
                continue;
              }
              
              // Asegurar que los campos necesarios existen
              chatData['name_chat'] = chatData['title'] ?? chatData['name_chat'] ?? 'Chat sin título';
              chatData['id_user'] = chatData['id_user'] ?? AuthService().currentUser?.id;
              
              // Si no tiene updated_at, usar created_at
              if (chatData['updated_at'] == null && chatData['created_at'] != null) {
                chatData['updated_at'] = chatData['created_at'];
              }
              
              parsedChats.add(ChatModel.fromJson(chatData));
            } catch (e) {
              print('Error parseando chat: $e');
            }
          }
        }

        _dashboardData = DashboardData(
          statistics: statistics,  // Usar las estadísticas parseadas
          recentDocuments: recentDocs,
          recentChats: parsedChats,
          lastUpdated: DateTime.now(),
        );

        _error = null;
        print('✅ Dashboard cargado exitosamente:');
        print('   - Usuarios: ${statistics['total_users']}');
        print('   - Documentos: ${statistics['total_documents']}');
        print('   - Chats activos: ${statistics['active_chats']}');
        print('   - Documentos recientes: ${recentDocs.length}');
        print('   - Chats recientes: ${parsedChats.length}');
      } else {
        throw Exception('Error al cargar dashboard: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ Error cargando dashboard: $e');
      _error = e.toString();
      
      // Si no hay datos previos, inicializar con valores vacíos
      if (_dashboardData == null) {
        _dashboardData = DashboardData(
          statistics: {
            'total_users': 0,
            'total_documents': 0,
            'active_chats': 0,
          },
          recentDocuments: [],
          recentChats: [],
          lastUpdated: DateTime.now(),
        );
      }
    } finally {
      if (showLoading) {
        _isLoading = false;
        notifyListeners();
      }
    }
  }

  // Refrescar datos manualmente
  Future<void> refresh() async {
    await loadDashboardData(showLoading: true);
  }

  // Actualizar datos en segundo plano sin mostrar loading
  Future<void> refreshInBackground() async {
    await loadDashboardData(showLoading: false);
  }

  // Limpiar datos al cerrar sesión
  void clear() {
    _dashboardData = null;
    _isLoading = false;
    _error = null;
    _refreshTimer?.cancel();
    _refreshTimer = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }
}
