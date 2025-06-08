import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';
import '../models/chat.dart';

class ChatService {
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

  // Alias para compatibilidad - llama a listChats
  Future<List<ChatModel>> getChats({
    int skip = 0,
    int limit = 100,
    String? sortBy,
    String? order,
  }) {
    return listChats(
      skip: skip,
      limit: limit,
      sortBy: sortBy,
      order: order,
    );
  }

  // Crear un nuevo chat
  Future<ChatModel> createChat({String? name}) async {
    try {
      final headers = await _getHeaders();
      final response = await http.post(
        Uri.parse(ApiConfig.createChat),
        headers: headers,
        body: json.encode({
          'name_chat': name ?? 'Nueva conversación',
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final jsonData = json.decode(response.body);
        return ChatModel.fromJson(jsonData);
      } else {
        throw Exception('Failed to create chat: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error creating chat: $e');
    }
  }

  // Listar todos los chats del usuario
  Future<List<ChatModel>> listChats({
    int skip = 0,
    int limit = 100,
    String? sortBy,
    String? order,
  }) async {
    try {
      print('🔄 Cargando chats...');
      final headers = await _getHeaders();
      print('📤 Headers obtenidos para chats');
      
      // Construir la URL con parámetros de paginación y ordenamiento
      String url = ApiConfig.listChats;
      final params = <String, String>{};
      
      params['skip'] = skip.toString();
      params['limit'] = limit.toString();
      if (sortBy != null) params['sort_by'] = sortBy;
      if (order != null) params['order'] = order;
      
      if (params.isNotEmpty) {
        url = '$url?${params.entries.map((e) => '${e.key}=${e.value}').join('&')}';
      }
      
      print('🌐 URL chats: $url');
      
      final response = await http.get(
        Uri.parse(url),
        headers: headers,
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          print('❌ Timeout al cargar chats');
          throw Exception('Timeout al cargar chats');
        },
      );

      print('📥 Response status chats: ${response.statusCode}');

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        print('✅ Chats cargados: ${jsonList.length}');
        return jsonList.map((json) => ChatModel.fromJson(json)).toList();
      } else if (response.statusCode == 401) {
        print('❌ Error de autenticación en chats');
        throw Exception('No autenticado o token inválido');
      } else {
        print('❌ Error del servidor para chats: ${response.statusCode}');
        print('📥 Response body chats: ${response.body}');
        throw Exception('Failed to load chats: ${response.body}');
      }
    } catch (e) {
      print('❌ Error completo al cargar chats: $e');
      // Re-lanzar errores de autenticación para que sean manejados arriba
      if (e.toString().contains('No authentication token') || 
          e.toString().contains('401') ||
          e.toString().contains('No autenticado')) {
        throw Exception('No autenticado o token inválido');
      }
      throw Exception('Error loading chats: $e');
    }
  }

  // Obtener un chat específico
  Future<ChatModel> getChat(int chatId) async {
    try {
      final headers = await _getHeaders();
      final response = await http.get(
        Uri.parse(ApiConfig.chatById(chatId)),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return ChatModel.fromJson(jsonData);
      } else {
        throw Exception('Failed to get chat: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error getting chat: $e');
    }
  }

  // Renombrar un chat
  Future<ChatModel> renameChat(int chatId, String newName) async {
    try {
      final headers = await _getHeaders();
      final response = await http.put(
        Uri.parse(ApiConfig.renameChat(chatId)),
        headers: headers,
        body: json.encode({'name': newName}),
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return ChatModel.fromJson(jsonData);
      } else {
        throw Exception('Failed to rename chat: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error renaming chat: $e');
    }
  }

  // Eliminar un chat
  Future<bool> deleteChat(int chatId) async {
    try {
      final headers = await _getHeaders();
      final response = await http.delete(
        Uri.parse(ApiConfig.deleteChat(chatId)),
        headers: headers,
      );

      if (response.statusCode == 204 || response.statusCode == 200) {
        return true;
      } else {
        throw Exception('Failed to delete chat: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error deleting chat: $e');
    }
  }

  // Enviar un mensaje en un chat (con documentos opcionales)
  Future<ChatMessage> sendMessage({
    required int chatId,
    required String message,
    List<int>? documentIds,
    int nResults = 5,
  }) async {
    try {
      final headers = await _getHeaders();
      final body = <String, dynamic>{
        'question': message,
        'n_results': nResults,
      };
      
      if (documentIds != null && documentIds.isNotEmpty) {
        body['document_ids'] = documentIds;
      }

      final response = await http.post(
        Uri.parse(ApiConfig.sendMessage(chatId)),
        headers: headers,
        body: json.encode(body),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final jsonData = json.decode(response.body);
        return ChatMessage.fromJson(jsonData);
      } else {
        throw Exception('Failed to send message: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error sending message: $e');
    }
  }

  // DEPRECATED: Usar sendMessage en su lugar
  // Este método se mantiene temporalmente por compatibilidad
  // pero será eliminado en futuras versiones
  @Deprecated('Use sendMessage instead')
  Future<Map<String, dynamic>> sendRAGMessage({
    required String question,
    List<int>? documentIds,
    int nResults = 5,
  }) async {
    throw Exception('sendRAGMessage is deprecated. Use sendMessage instead.');
  }

  // Listar mensajes de un chat
  Future<List<Map<String, dynamic>>> listMessages({
    required int chatId,
    int skip = 0,
    int limit = 100,
  }) async {
    try {
      final headers = await _getHeaders();
      final response = await http.get(
        Uri.parse(ApiConfig.getPaginatedEndpoint(
          ApiConfig.listMessages(chatId),
          skip: skip,
          limit: limit,
        )),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        return jsonList.cast<Map<String, dynamic>>();
      } else {
        throw Exception('Failed to load messages: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error loading messages: $e');
    }
  }

  // Eliminar un mensaje
  Future<bool> deleteMessage(int chatId, int messageId) async {
    try {
      final headers = await _getHeaders();
      final response = await http.delete(
        Uri.parse(ApiConfig.deleteMessage(chatId, messageId)),
        headers: headers,
      );

      if (response.statusCode == 204 || response.statusCode == 200) {
        return true;
      } else {
        throw Exception('Failed to delete message: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error deleting message: $e');
    }
  }
}