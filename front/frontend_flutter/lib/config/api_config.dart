class ApiConfig {
  static const String baseUrl = 'http://localhost:2690/api';
  
  // WebSocket configuration
  static const String wsBase = 'ws://localhost:2690/api';  // Añadido para compatibilidad
  static const String wsBaseUrl = 'ws://localhost:2690/api';
  static const String wsBaseUrlSecure = 'wss://localhost:2690/api';

  // ------------------------------
  // STATISTICS ENDPOINTS
  // ------------------------------
  static const String globalStatistics = '$baseUrl/statistics/public'; // GET - Público, no requiere auth
  static const String globalStatisticsAuth = '$baseUrl/statistics/global'; // GET - Requiere auth
  static const String dashboard = '$baseUrl/statistics/dashboard'; // GET - Dashboard completo

  // ------------------------------
  // AUTH & USER ENDPOINTS
  // ------------------------------

  // User endpoints base
  static const String userBase = '$baseUrl/users';

  // Auth endpoints
  static const String login = '$userBase/login';
  static const String register = '$userBase/register';
  static const String forgotPassword = '$userBase/forgot-password';
  static const String resetPassword = '$userBase/reset-password';

  // Endpoints faltantes de auth (TO-DO en backend)
  static const String logout = '$userBase/logout'; // No implementado aún
  static const String refreshToken =
      '$userBase/refresh-token'; // No implementado aún
  static const String verifyEmail =
      '$userBase/verify-email'; // No implementado aún
  static const String resendVerification =
      '$userBase/resend-verification'; // No implementado aún

  // Current user endpoints
  static const String me = '$userBase/me';
  static const String updateMe = '$userBase/me'; // PUT
  static const String changePassword = '$userBase/me/change-password';

  // User management endpoints
  static const String listUsers = userBase; // GET con paginación
  static String userById(int userId) => '$userBase/$userId';
  static String updateUser(int userId) => '$userBase/$userId'; // PUT
  static String changeUserPassword(int userId) =>
      '$userBase/$userId/change-password';
  static String deleteUser(int userId) => '$userBase/$userId';

  // User search (TO-DO en backend)
  static const String searchUsers = '$userBase/search'; // No implementado aún

  // User avatar endpoints (TO-DO en backend)
  static String uploadAvatar(int userId) =>
      '$userBase/$userId/avatar'; // POST - No implementado
  static String deleteAvatar(int userId) =>
      '$userBase/$userId/avatar'; // DELETE - No implementado

  // ------------------------------
  // CHAT ENDPOINTS
  // ------------------------------
  static const String chatBase = '$baseUrl/chats';

  // Chat management endpoints
  static const String createChat = chatBase; // POST
  static const String listChats = chatBase; // GET con paginación
  static String chatById(int chatId) => '$chatBase/$chatId'; // GET
  static String updateChat(int chatId) => '$chatBase/$chatId'; // PUT
  static String renameChat(int chatId) => '$chatBase/$chatId/rename'; // PUT
  static String deleteChat(int chatId) => '$chatBase/$chatId'; // DELETE

  // Message endpoints
  static String sendMessage(int chatId) =>
      '$chatBase/$chatId/messages'; // POST - con RAG integrado
  static String listMessages(int chatId) =>
      '$chatBase/$chatId/messages'; // GET con paginación
  static String deleteMessage(int chatId, int messageId) =>
      '$chatBase/$chatId/messages/$messageId'; // DELETE

  // ------------------------------
  // DOCUMENT ENDPOINTS
  // ------------------------------
  static const String documentsBase = '$baseUrl/documents';

  // Document management endpoints
  static const String uploadDocument =
      '$documentsBase/upload'; // POST - nuevo endpoint híbrido
  static const String createDocument =
      documentsBase; // POST - crear documento con contenido
  static const String listDocuments = documentsBase; // GET con paginación
  static const String sharedDocuments = '$documentsBase/shared'; // GET
  static String searchDocumentsUrl({required String query, int? nResults}) {
    final uri = Uri.parse('$baseUrl/documents/search');
    final queryParams = {
      'query': query,
      if (nResults != null) 'n_results': nResults.toString(),
    };
    return uri.replace(queryParameters: queryParams).toString();
  }

  // Document specific endpoints
  static String documentById(int docId) => '$documentsBase/$docId'; // GET
  static String updateDocument(int docId) => '$documentsBase/$docId'; // PUT
  static String deleteDocument(int docId) => '$documentsBase/$docId'; // DELETE

  static String documentStatus(int docId) =>
      '$documentsBase/$docId/status'; // GET
  static String reindexDocument(int docId) =>
      '$documentsBase/$docId/reindex'; // POST

  // Document sharing endpoints
  static String shareDocument(int docId) =>
      '$documentsBase/$docId/share'; // POST
  static const String shareDocumentLegacy =
      '$documentsBase/share'; // POST - DEPRECADO
  static String checkDocumentAccess(int docId) =>
      '$documentsBase/$docId/access'; // GET - Verificar acceso
  static const String sharedWithMe = 
      '$documentsBase/shared-with-me'; // GET - Documentos compartidos conmigo

  // Document users endpoints
  static String linkUsersToDocument(int docId) =>
      '$documentsBase/$docId/users'; // POST
  static String documentUsers(int docId) =>
      '$documentsBase/$docId/users'; // GET
  static String removeUserAccess(int docId, int userId) =>
      '$documentsBase/$docId/users/$userId'; // DELETE

  // Endpoint faltante que agregaste
  static String verifyDocumentIndex(int docId) =>
      '$documentsBase/$docId/verify-index'; // GET - si lo agregaste

  // ------------------------------
  // ADMIN ENDPOINTS
  // ------------------------------
  static const String adminBase = '$baseUrl/admin';
  
  // Admin - Documents endpoints
  static const String adminDocuments = '$adminBase/documents'; // GET - Todos los documentos del sistema
  static const String adminDocumentsStats = '$adminBase/documents/stats'; // GET - Estadísticas de documentos
  
  // Métodos helper para admin documents
  static String adminDocumentsWithFilters({
    int skip = 0,
    int limit = 100,
    String sortBy = 'created_at',
    String order = 'desc',
    int? userFilter,
    String? contentTypeFilter,
  }) {
    var url = '$adminDocuments?skip=$skip&limit=$limit&sort_by=$sortBy&order=$order';
    
    if (userFilter != null) {
      url += '&user_filter=$userFilter';
    }
    
    if (contentTypeFilter != null) {
      url += '&content_type_filter=$contentTypeFilter';
    }
    
    return url;
  }
  
  static String adminDocumentsStatsWithPeriod({
    String timePeriod = 'all',
    String groupBy = 'user',
  }) {
    return '$adminDocumentsStats?time_period=$timePeriod&group_by=$groupBy';
  }
  
  static String deleteDocumentAdmin(int documentId, {bool force = false}) {
    return '$adminBase/documents/$documentId?force=$force';
  }
  
  // Admin - Other endpoints
  static const String adminUsers = '$adminBase/users'; // GET - Todos los usuarios
  static const String adminChats = '$adminBase/chats'; // GET - Todos los chats
  static const String adminStats = '$adminBase/stats'; // GET - Estadísticas generales
  
  // Admin Panel - New dashboard endpoint
  static const String adminPanelDashboard = '$baseUrl/admin-panel/dashboard'; // GET - Dashboard completo del panel
  
  // ------------------------------
  // HELPER METHODS
  // ------------------------------

  // Helper para endpoints con paginación
  static String getPaginatedEndpoint(String baseEndpoint,
      {int skip = 0, int limit = 100}) {
    return '$baseEndpoint?skip=$skip&limit=$limit';
  }

  // Helper para búsqueda de documentos con parámetros
  static String searchDocumentsWithParams({
    required String query,
    int nResults = 5,
    List<String>? tags,
  }) {
    String url = '$documentsBase/search?query=$query&n_results=$nResults';
    if (tags != null && tags.isNotEmpty) {
      url += '&tags=${tags.join(',')}';
    }
    return url;
  }

  // Helper para mensajes con documentos
  static Map<String, dynamic> createMessageBody({
    required String question,
    List<int>? documentIds,
    int nResults = 5,
  }) {
    return {
      'question': question,
      if (documentIds != null) 'document_ids': documentIds,
      'n_results': nResults,
    };
  }
}
