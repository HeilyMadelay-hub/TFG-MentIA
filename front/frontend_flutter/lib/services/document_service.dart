import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart'; // Agregar esta importación
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';
import '../models/document.dart';

class DocumentService {
  static const String _tokenKey = 'auth_token';

  // Obtener el token de autenticación
  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  // Configurar headers con autenticación
  Future<Map<String, String>> _getHeaders({bool isMultipart = false}) async {
    final token = await _getToken();
    if (token == null) {
      throw Exception('No authentication token found');
    }

    if (isMultipart) {
      return {
        'Authorization': 'Bearer $token',
      };
    }

    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };
  }

  // Subir un documento
  Future<Document> uploadDocument({
    required String title,
    required String filePath,
    required String contentType,
  }) async {
    try {
      final headers = await _getHeaders(isMultipart: true);
      final uri = Uri.parse(ApiConfig.uploadDocument);

      var request = http.MultipartRequest('POST', uri);
      request.headers.addAll(headers);

      // Agregar el archivo
      request.files.add(await http.MultipartFile.fromPath(
        'file',
        filePath,
        contentType: MediaType.parse(contentType),
      ));

      // Agregar campos del formulario
      request.fields['title'] = title;

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200 || response.statusCode == 201) {
        final jsonData = json.decode(response.body);
        return Document.fromJson(jsonData);
      } else {
        throw Exception('Failed to upload document: ${response.body}');
      }
    } catch (e) {
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
      final headers = await _getHeaders(isMultipart: true);
      final uri = Uri.parse(ApiConfig.uploadDocument);

      var request = http.MultipartRequest('POST', uri);
      request.headers.addAll(headers);

      // Agregar el archivo desde bytes
      request.files.add(http.MultipartFile.fromBytes(
        'file',
        fileBytes,
        filename: filename,
        contentType: MediaType.parse(contentType),
      ));

      // Agregar campos del formulario
      request.fields['title'] = title;

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200 || response.statusCode == 201) {
        final jsonData = json.decode(response.body);
        return Document.fromJson(jsonData);
      } else {
        throw Exception('Failed to upload document: ${response.body}');
      }
    } catch (e) {
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
      final headers = await _getHeaders();
      debugPrint('📤 Headers obtenidos');
      
      // Construir la URL con parámetros de paginación y ordenamiento
      String url = ApiConfig.listDocuments;
      final params = <String, String>{};
      
      params['skip'] = skip.toString();
      params['limit'] = limit.toString();
      if (sortBy != null) params['sort_by'] = sortBy;
      if (order != null) params['order'] = order;
      
      if (params.isNotEmpty) {
        url = '$url?${params.entries.map((e) => '${e.key}=${e.value}').join('&')}';
      }
      
      debugPrint('🌐 URL: $url');
      final uri = Uri.parse(url);

      final response = await http.get(uri, headers: headers).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          debugPrint('❌ Timeout al cargar documentos');
          throw Exception('Timeout al cargar documentos');
        },
      );

      debugPrint('📥 Response status: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        debugPrint('✅ Documentos cargados: ${jsonList.length}');
        return jsonList.map((json) => Document.fromJson(json)).toList();
      } else if (response.statusCode == 401) {
        debugPrint('❌ Error de autenticación');
        throw Exception('No autenticado o token inválido');
      } else {
        debugPrint('❌ Error del servidor: ${response.statusCode}');
        debugPrint('📥 Response body: ${response.body}');
        throw Exception('Failed to load documents: ${response.body}');
      }
    } catch (e) {
      debugPrint('❌ Error completo: $e');
      // Re-lanzar errores de autenticación para que sean manejados arriba
      if (e.toString().contains('No authentication token') || 
          e.toString().contains('401') ||
          e.toString().contains('No autenticado')) {
        throw Exception('No autenticado o token inválido');
      }
      throw Exception('Error loading documents: $e');
    }
  }

  // Obtener un documento específico
  Future<Document> getDocument(int documentId) async {
    try {
      final headers = await _getHeaders();
      final uri = Uri.parse(ApiConfig.documentById(documentId));

      final response = await http.get(uri, headers: headers);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return Document.fromJson(jsonData);
      } else {
        throw Exception('Failed to get document: ${response.body}');
      }
    } catch (e) {
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
      final headers = await _getHeaders();
      final uri = Uri.parse(ApiConfig.updateDocument(documentId));

      Map<String, dynamic> body = {};
      if (title != null) body['title'] = title;
      if (content != null) body['content'] = content;
      if (contentType != null) body['content_type'] = contentType;
      if (tags != null) body['tags'] = tags;

      final response = await http.put(
        uri,
        headers: headers,
        body: json.encode(body),
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return Document.fromJson(jsonData);
      } else {
        throw Exception('Failed to update document: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error updating document: $e');
    }
  }

  // Eliminar un documento
  Future<bool> deleteDocument(int documentId) async {
    try {
      final headers = await _getHeaders();
      final uri = Uri.parse(ApiConfig.deleteDocument(documentId));

      final response = await http.delete(uri, headers: headers);

      if (response.statusCode == 204) {
        return true;
      } else {
        throw Exception('Failed to delete document: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error deleting document: $e');
    }
  }

  // Compartir documento con usuarios
  Future<void> shareDocument({
    required int documentId,
    required List<int> userIds,
  }) async {
    try {
      final headers = await _getHeaders();
      final uri = Uri.parse(ApiConfig.shareDocument(documentId));

      final response = await http.post(
        uri,
        headers: headers,
        body: json.encode({'user_ids': userIds}),
      );

      if (response.statusCode == 200) {
        return;
      } else {
        // Log de respuesta para debug
        debugPrint('Error response status: ${response.statusCode}');
        debugPrint('Error response body: ${response.body}');
        
        // Intentar decodificar el error del backend
        try {
          final error = json.decode(response.body);
          final detail = error['detail'] ?? 'Error al compartir documento';
          
          // Si el mensaje contiene información sobre IDs inválidos, incluirlo completo
          if (detail.toString().contains('Los siguientes IDs de usuario no existen')) {
            throw Exception('detail: $detail');
          } else {
            throw Exception(detail);
          }
        } catch (e) {
          // Si ya es una Exception, re-lanzarla
          if (e is Exception) {
            rethrow;
          }
          // Si no se puede decodificar, lanzar error genérico
          throw Exception('Error al compartir documento: ${response.statusCode}');
        }
      }
    } catch (e) {
      // Si ya es una Exception, re-lanzarla
      if (e is Exception) {
        rethrow;
      }
      throw Exception('Error al compartir documento: $e');
    }
  }

  // Listar documentos compartidos conmigo
  Future<List<Document>> getSharedDocuments(
      {int skip = 0, int limit = 100}) async {
    try {
      final headers = await _getHeaders();
      final uri = Uri.parse(ApiConfig.getPaginatedEndpoint(
        ApiConfig.sharedDocuments,
        skip: skip,
        limit: limit,
      ));

      final response = await http.get(uri, headers: headers);

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        return jsonList.map((json) => Document.fromJson(json)).toList();
      } else {
        throw Exception('Failed to load shared documents: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error loading shared documents: $e');
    }
  }

  // Obtener documentos compartidos conmigo
  Future<List<Document>> getSharedWithMe({int skip = 0, int limit = 100}) async {
    try {
      final headers = await _getHeaders();
      final uri = Uri.parse(ApiConfig.getPaginatedEndpoint(
        ApiConfig.sharedWithMe,
        skip: skip,
        limit: limit,
      ));

      final response = await http.get(uri, headers: headers);

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        return jsonList.map((doc) {
          var document = Document.fromJson(doc);
          document.isShared = true; // Marcar como compartido
          return document;
        }).toList();
      } else {
        throw Exception('Failed to load shared documents: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error loading shared documents: $e');
    }
  }

  // Obtener el estado de procesamiento de un documento
  Future<Map<String, dynamic>> getDocumentStatus(int documentId) async {
    try {
      final headers = await _getHeaders();
      final uri = Uri.parse(ApiConfig.documentStatus(documentId));

      final response = await http.get(uri, headers: headers);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to get document status: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error getting document status: $e');
    }
  }

  // Listar usuarios con acceso a un documento
  Future<List<Map<String, dynamic>>> getDocumentUsers(int documentId) async {
    try {
      final headers = await _getHeaders();
      final uri = Uri.parse(ApiConfig.documentUsers(documentId));

      final response = await http.get(uri, headers: headers);

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        return jsonList.cast<Map<String, dynamic>>();
      } else {
        throw Exception('Failed to get document users: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error getting document users: $e');
    }
  }

  // Eliminar acceso de un usuario a un documento
  Future<bool> removeUserAccess({
    required int documentId,
    required int userId,
  }) async {
    try {
      final headers = await _getHeaders();
      final uri = Uri.parse(ApiConfig.removeUserAccess(documentId, userId));

      final response = await http.delete(uri, headers: headers);

      if (response.statusCode == 204) {
        return true;
      } else {
        throw Exception('Failed to remove user access: ${response.body}');
      }
    } catch (e) {
      throw Exception('Error removing user access: $e');
    }
  }

  // Verificar acceso a un documento
  Future<bool> hasAccessToDocument(int documentId) async {
    try {
      final headers = await _getHeaders();
      final uri = Uri.parse(ApiConfig.checkDocumentAccess(documentId));

      final response = await http.get(uri, headers: headers);

      return response.statusCode == 200;
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
      final headers = await _getHeaders();
      final uri = Uri.parse(ApiConfig.removeUserAccess(documentId, userId));

      final response = await http.delete(uri, headers: headers);

      if (response.statusCode != 200 && response.statusCode != 204) {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Error al revocar acceso');
      }
    } catch (e) {
      if (e is Exception) {
        rethrow;
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
      final headers = await _getHeaders();
      final uri = Uri.parse(ApiConfig.searchDocumentsUrl(
        query: query,
        nResults: nResults,
      ));

      final response = await http.get(uri, headers: headers);

      if (response.statusCode == 200) {
        final List<dynamic> jsonList = json.decode(response.body);
        return jsonList.cast<Map<String, dynamic>>();
      } else {
        throw Exception('Failed to search documents: ${response.body}');
      }
    } catch (e) {
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
