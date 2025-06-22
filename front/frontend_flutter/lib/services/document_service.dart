import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'api_client.dart';
import '../config/api_config.dart';
import '../models/document.dart';

class DocumentService {
  final ApiClient _apiClient = apiClient;

  // Subir un documento
  Future<Document> uploadDocument({
    required String title,
    required String filePath,
    required String contentType,
  }) async {
    try {
      final file = await http.MultipartFile.fromPath(
        'file',
        filePath,
        contentType: MediaType.parse(contentType),
      );

      final response = await _apiClient.multipart(
        ApiConfig.uploadDocument,
        'POST',
        fields: {'title': title},
        files: [file],
      );

      final jsonData = json.decode(response.body);
      return Document.fromJson(jsonData);
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al subir documento: ${e.message}');
      }
      throw Exception('Error uploading document: $e');
    }
  }

  // Subir un documento desde bytes (para web)
  Future<Document> uploadDocumentFromBytes({
    required String title,
    required Uint8List fileBytes,
    required String filename,
    required String contentType,
  }) async {
    try {
      final file = http.MultipartFile.fromBytes(
        'file',
        fileBytes,
        filename: filename,
        contentType: MediaType.parse(contentType),
      );

      final response = await _apiClient.multipart(
        ApiConfig.uploadDocument,
        'POST',
        fields: {'title': title},
        files: [file],
      );

      final jsonData = json.decode(response.body);
      return Document.fromJson(jsonData);
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al subir documento: ${e.message}');
      }
      throw Exception('Error uploading document: $e');
    }
  }

  // Alias para compatibilidad - llama a listDocuments
  Future<List<Document>> getDocuments({
    int skip = 0,
    int limit = 100,
    String? sortBy,
    String? order,
  }) {
    return listDocuments(
      skip: skip,
      limit: limit,
      sortBy: sortBy,
      order: order,
    );
  }

  // Listar documentos del usuario
  Future<List<Document>> listDocuments({
    int skip = 0,
    int limit = 100,
    String? sortBy,
    String? order,
  }) async {
    try {
      debugPrint('🔄 Cargando documentos...');
      
      // Construir parámetros de paginación
      final params = <String, String>{};
      params['skip'] = skip.toString();
      params['limit'] = limit.toString();
      if (sortBy != null) params['sort_by'] = sortBy;
      if (order != null) params['order'] = order;
      
      final response = await _apiClient.get(
        ApiConfig.listDocuments,
        queryParams: params,
      );

      debugPrint('📥 Response status: ${response.statusCode}');
      
      final List<dynamic> jsonList = json.decode(response.body);
      debugPrint('✅ Documentos cargados: ${jsonList.length}');
      return jsonList.map((json) => Document.fromJson(json)).toList();
    } catch (e) {
      debugPrint('❌ Error completo: $e');
      if (e is ApiException) {
        if (e.statusCode == 401 || e.errorCode == 'SESSION_EXPIRED') {
          throw Exception('No autenticado o token inválido');
        }
        throw Exception('Error al cargar documentos: ${e.message}');
      }
      throw Exception('Error loading documents: $e');
    }
  }

  // Obtener un documento específico
  Future<Document> getDocument(int documentId) async {
    try {
      final response = await _apiClient.get(ApiConfig.documentById(documentId));
      final jsonData = json.decode(response.body);
      return Document.fromJson(jsonData);
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al obtener documento: ${e.message}');
      }
      throw Exception('Error getting document: $e');
    }
  }

  // Actualizar metadata del documento
  Future<Document> updateDocument({
    required int documentId,
    String? title,
    String? content,
    String? contentType,
    List<String>? tags,
  }) async {
    try {
      Map<String, dynamic> body = {};
      if (title != null) body['title'] = title;
      if (content != null) body['content'] = content;
      if (contentType != null) body['content_type'] = contentType;
      if (tags != null) body['tags'] = tags;

      final response = await _apiClient.put(
        ApiConfig.updateDocument(documentId),
        body: body,
      );

      final jsonData = json.decode(response.body);
      return Document.fromJson(jsonData);
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al actualizar documento: ${e.message}');
      }
      throw Exception('Error updating document: $e');
    }
  }

  // Eliminar un documento
  Future<bool> deleteDocument(int documentId) async {
    try {
      await _apiClient.delete(ApiConfig.deleteDocument(documentId));
      return true;
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al eliminar documento: ${e.message}');
      }
      throw Exception('Error deleting document: $e');
    }
  }

  // Compartir documento con usuarios
  Future<Map<String, dynamic>> shareDocument({
    required int documentId,
    required List<int> userIds,
  }) async {
    try {
      final response = await _apiClient.post(
        ApiConfig.shareDocument(documentId),
        body: {'user_ids': userIds},
      );
      
      // Devolver la respuesta completa del backend
      return json.decode(response.body);
    } catch (e) {
      if (e is ApiException) {
        debugPrint('Error response: ${e.message}');
        
        // Si el mensaje contiene información sobre IDs inválidos, incluirlo completo
        if (e.message.contains('Los siguientes IDs de usuario no existen')) {
          throw Exception('detail: ${e.message}');
        } else {
          throw Exception(e.message);
        }
      }
      throw Exception('Error al compartir documento: $e');
    }
  }

  // Listar documentos compartidos conmigo
  Future<List<Document>> getSharedDocuments(
      {int skip = 0, int limit = 100}) async {
    try {
      final response = await _apiClient.get(
        ApiConfig.sharedDocuments,
        queryParams: {
          'skip': skip.toString(),
          'limit': limit.toString(),
        },
      );

      final List<dynamic> jsonList = json.decode(response.body);
      return jsonList.map((json) => Document.fromJson(json)).toList();
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al cargar documentos compartidos: ${e.message}');
      }
      throw Exception('Error loading shared documents: $e');
    }
  }

  // Obtener documentos compartidos conmigo
  Future<List<Document>> getSharedWithMe({int skip = 0, int limit = 100}) async {
    try {
      final response = await _apiClient.get(
        ApiConfig.sharedWithMe,
        queryParams: {
          'skip': skip.toString(),
          'limit': limit.toString(),
        },
      );

      final List<dynamic> jsonList = json.decode(response.body);
      return jsonList.map((doc) {
        var document = Document.fromJson(doc);
        document.isShared = true; // Marcar como compartido
        return document;
      }).toList();
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al cargar documentos compartidos: ${e.message}');
      }
      throw Exception('Error loading shared documents: $e');
    }
  }

  // Obtener el estado de procesamiento de un documento
  Future<Map<String, dynamic>> getDocumentStatus(int documentId) async {
    try {
      final response = await _apiClient.get(ApiConfig.documentStatus(documentId));
      return json.decode(response.body);
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al obtener estado del documento: ${e.message}');
      }
      throw Exception('Error getting document status: $e');
    }
  }

  // Listar usuarios con acceso a un documento
  Future<List<Map<String, dynamic>>> getDocumentUsers(int documentId) async {
    try {
      final response = await _apiClient.get(ApiConfig.documentUsers(documentId));
      final List<dynamic> jsonList = json.decode(response.body);
      return jsonList.cast<Map<String, dynamic>>();
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al obtener usuarios del documento: ${e.message}');
      }
      throw Exception('Error getting document users: $e');
    }
  }

  // Eliminar acceso de un usuario a un documento
  Future<bool> removeUserAccess({
    required int documentId,
    required int userId,
  }) async {
    try {
      await _apiClient.delete(ApiConfig.removeUserAccess(documentId, userId));
      return true;
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al eliminar acceso: ${e.message}');
      }
      throw Exception('Error removing user access: $e');
    }
  }

  // Verificar acceso a un documento
  Future<bool> hasAccessToDocument(int documentId) async {
    try {
      await _apiClient.get(ApiConfig.checkDocumentAccess(documentId));
      return true;
    } catch (e) {
      debugPrint('Error verificando acceso: $e');
      return false;
    }
  }

  // Revocar acceso a un documento
  Future<void> revokeAccess({
    required int documentId,
    required int userId,
  }) async {
    try {
      await _apiClient.delete(ApiConfig.removeUserAccess(documentId, userId));
    } catch (e) {
      if (e is ApiException) {
        throw Exception(e.message);
      }
      throw Exception('Error al revocar acceso: $e');
    }
  }

  // Buscar documentos
  Future<List<Map<String, dynamic>>> searchDocuments({
    required String query,
    int nResults = 5,
  }) async {
    try {
      final response = await _apiClient.get(
        ApiConfig.searchDocumentsUrl(query: query, nResults: nResults),
      );

      final List<dynamic> jsonList = json.decode(response.body);
      return jsonList.cast<Map<String, dynamic>>();
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al buscar documentos: ${e.message}');
      }
      throw Exception('Error searching documents: $e');
    }
  }



  // Método helper para esperar a que un documento esté completamente procesado
  Future<Document> waitForDocumentProcessing(
    int documentId, {
    Duration checkInterval = const Duration(seconds: 2),
    Duration timeout = const Duration(minutes: 5),
  }) async {
    final startTime = DateTime.now();

    while (DateTime.now().difference(startTime) < timeout) {
      final status = await getDocumentStatus(documentId);

      if (status['status'] == 'completed') {
        return await getDocument(documentId);
      } else if (status['status'] == 'error') {
        throw Exception('Document processing failed: ${status['message']}');
      }

      await Future.delayed(checkInterval);
    }

    throw Exception('Document processing timeout');
  }
}
