import 'dart:convert';
import 'api_client.dart';
import '../config/api_config.dart';
import '../models/chat.dart';
import '../utils/logger.dart';

class ChatService {
  final ApiClient _apiClient = apiClient;
  final Logger _logger = Logger('ChatService');

  // Alias para compatibilidad - llama a listChats
  Future<List<Chat>> getChats({
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
  Future<Chat> createChat({String? name}) async {
    try {
      final response = await _apiClient.post(
        ApiConfig.createChat,
        body: {
          'name_chat': name ?? 'Nueva conversación',
        },
      );

      final jsonData = json.decode(response.body);
      return Chat.fromJson(jsonData);
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al crear chat: ${e.message}');
      }
      throw Exception('Error creating chat: $e');
    }
  }

  // Listar todos los chats del usuario
  Future<List<Chat>> listChats({
    int skip = 0,
    int limit = 100,
    String? sortBy,
    String? order,
  }) async {
    try {
      _logger.info('🔄 Cargando chats...');
      
      // Construir parámetros de consulta
      final params = <String, String>{};
      params['skip'] = skip.toString();
      params['limit'] = limit.toString();
      if (sortBy != null) params['sort_by'] = sortBy;
      if (order != null) params['order'] = order;
      
      final response = await _apiClient.get(
        ApiConfig.listChats,
        queryParams: params,
      );

      _logger.info('📥 Response status chats: ${response.statusCode}');

      final List<dynamic> jsonList = json.decode(response.body);
      _logger.info('✅ Chats cargados: ${jsonList.length}');
      return jsonList.map((json) => Chat.fromJson(json)).toList();
    } catch (e) {
      _logger.error('❌ Error completo al cargar chats: $e');
      if (e is ApiException) {
        if (e.statusCode == 401 || e.errorCode == 'SESSION_EXPIRED') {
          throw Exception('No autenticado o token inválido');
        }
        throw Exception('Error al cargar chats: ${e.message}');
      }
      throw Exception('Error loading chats: $e');
    }
  }

  // Obtener un chat específico
  Future<Chat> getChat(int chatId) async {
    try {
      final response = await _apiClient.get(ApiConfig.chatById(chatId));
      final jsonData = json.decode(response.body);
      return Chat.fromJson(jsonData);
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al obtener chat: ${e.message}');
      }
      throw Exception('Error getting chat: $e');
    }
  }

  // Renombrar un chat
  Future<Chat> renameChat(int chatId, String newName) async {
    try {
      final response = await _apiClient.put(
        ApiConfig.renameChat(chatId),
        body: {'name': newName},
      );
      final jsonData = json.decode(response.body);
      return Chat.fromJson(jsonData);
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al renombrar chat: ${e.message}');
      }
      throw Exception('Error renaming chat: $e');
    }
  }

  // Eliminar un chat
  Future<bool> deleteChat(int chatId) async {
    try {
      await _apiClient.delete(ApiConfig.deleteChat(chatId));
      return true;
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al eliminar chat: ${e.message}');
      }
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
      final body = <String, dynamic>{
        'question': message,
        'n_results': nResults,
      };
      
      if (documentIds != null && documentIds.isNotEmpty) {
        body['document_ids'] = documentIds;
      }

      final response = await _apiClient.post(
        ApiConfig.sendMessage(chatId),
        body: body,
      );

      final jsonData = json.decode(response.body);
      return ChatMessage.fromJson(jsonData);
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al enviar mensaje: ${e.message}');
      }
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
      final response = await _apiClient.get(
        ApiConfig.listMessages(chatId),
        queryParams: {
          'skip': skip.toString(),
          'limit': limit.toString(),
        },
      );

      final List<dynamic> jsonList = json.decode(response.body);
      return jsonList.cast<Map<String, dynamic>>();
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al cargar mensajes: ${e.message}');
      }
      throw Exception('Error loading messages: $e');
    }
  }

  // Eliminar un mensaje
  Future<bool> deleteMessage(int chatId, int messageId) async {
    try {
      await _apiClient.delete(ApiConfig.deleteMessage(chatId, messageId));
      return true;
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al eliminar mensaje: ${e.message}');
      }
      throw Exception('Error deleting message: $e');
    }
  }
}