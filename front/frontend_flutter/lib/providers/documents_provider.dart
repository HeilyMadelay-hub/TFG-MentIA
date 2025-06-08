import 'package:flutter/material.dart';
import '../models/document.dart';
import 'dart:typed_data'; // Agregar esta importación para Uint8List
import '../services/document_service.dart';
import '../services/auth_service.dart';
import '../services/statistics_service.dart';
import 'package:flutter/foundation.dart'
    show kIsWeb; // Agregar esta importación

class DocumentsProvider extends ChangeNotifier {
  final DocumentService _documentService = DocumentService();
  final StatisticsService _statisticsService = StatisticsService();

  List<Document> _documents = [];
  List<Document> _filteredDocuments = [];
  bool _isLoading = false;
  String _selectedFilter = 'Todos';
  String _searchQuery = '';

  // Getters
  List<Document> get documents => _documents;
  List<Document> get filteredDocuments => _filteredDocuments;
  bool get isLoading => _isLoading;
  String get selectedFilter => _selectedFilter;
  String get searchQuery => _searchQuery;

  // Messenger key para mostrar SnackBars sin BuildContext
  final GlobalKey<ScaffoldMessengerState> messengerKey =
      GlobalKey<ScaffoldMessengerState>();

  // Cargar documentos
  Future<void> loadDocuments() async {
    _isLoading = true;
    notifyListeners();

    try {
      // Cargar documentos propios
      final userDocuments = await _documentService.listDocuments();
      final allDocuments = <Document>[];
      allDocuments.addAll(userDocuments);
      
      // Solo cargar documentos compartidos si NO es admin
      final currentUser = AuthService().currentUser;
      if (!(currentUser?.isAdmin ?? false)) {
        try {
          final sharedDocuments = await _documentService.getSharedDocuments();
          // Agregar documentos compartidos (marcándolos como compartidos)
          for (var doc in sharedDocuments) {
            if (!allDocuments.any((d) => d.id == doc.id)) {
              allDocuments.add(doc.copyWith(isShared: true));
            }
          }
        } catch (e) {
          debugPrint('Error loading shared documents: $e');
          // Continuar sin documentos compartidos si hay error
        }
      }

      _documents = allDocuments;
      _filterDocuments();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();

      showMessage(
        'Error al cargar documentos: ${e.toString()}',
        isError: true,
        action: SnackBarAction(
          label: 'Reintentar',
          onPressed: loadDocuments,
          textColor: Colors.white,
        ),
      );
    }
  }

  // Establecer filtro
  void setFilter(String filter) {
    _selectedFilter = filter;
    _filterDocuments();
    notifyListeners();
  }

  // Establecer búsqueda
  void setSearchQuery(String query) {
    _searchQuery = query;
    _filterDocuments();
    notifyListeners();
  }

  // Filtrar documentos
  void _filterDocuments() {
    final query = _searchQuery.toLowerCase();

    _filteredDocuments = _documents.where((doc) {
      final matchesSearch = doc.title.toLowerCase().contains(query) ||
          doc.fileName.toLowerCase().contains(query);

      final matchesFilter = _selectedFilter == 'Todos' ||
          (_selectedFilter == 'Compartidos' && doc.isShared) ||
          (_selectedFilter == 'PDF' && doc.mimeType.contains('pdf')) ||
          (_selectedFilter == 'TXT' && doc.mimeType.contains('text/plain'));

      return matchesSearch && matchesFilter;
    }).toList();
  }

  Future<void> uploadDocument({
    required String title,
    required String filePath,
    required String contentType,
    Uint8List? fileBytes, // Añadir parámetro para bytes
    String? filename, // Añadir parámetro para nombre
  }) async {
    try {
      showMessage('Subiendo documento...');

      Document newDocument;

      // Si estamos en web, usar bytes
      if (kIsWeb && fileBytes != null && filename != null) {
        newDocument = await _documentService.uploadDocumentFromBytes(
          title: title,
          fileBytes: fileBytes,
          filename: filename,
          contentType: contentType,
        );
      } else {
        // Para móvil/desktop, usar path
        newDocument = await _documentService.uploadDocument(
          title: title,
          filePath: filePath,
          contentType: contentType,
        );
      }

      if (newDocument.isPending || newDocument.isProcessing) {
        // Mostrar diálogo de procesamiento
        showMessage('Procesando documento...');
        await _pollDocumentStatus(newDocument.id);
      }

      // Recargar lista de documentos
      await loadDocuments();
      
      // Invalidar caché de estadísticas para forzar actualización
      await _statisticsService.invalidateCache();
      debugPrint('🔄 Caché de estadísticas invalidado después de subir documento');

      showMessage(
        'Documento subido exitosamente',
        isError: false,
      );
    } catch (e) {
      showMessage(
        'Error al subir documento: ${e.toString()}',
        isError: true,
      );
    }
  }

  // Monitorear estado del documento
  Future<void> _pollDocumentStatus(int documentId) async {
    bool isComplete = false;
    int attempts = 0;
    const maxAttempts = 30; // 1 minuto máximo

    while (!isComplete && attempts < maxAttempts) {
      await Future.delayed(const Duration(seconds: 2));

      try {
        final status = await _documentService.getDocumentStatus(documentId);

        if (status['status'] == 'completed') {
          isComplete = true;
          showMessage('Documento procesado exitosamente');
        } else if (status['status'] == 'error') {
          throw Exception(status['message'] ?? 'Error procesando documento');
        }
      } catch (e) {
        showMessage(
          'Error procesando documento: ${e.toString()}',
          isError: true,
        );
        break;
      }

      attempts++;
    }

    if (!isComplete && attempts >= maxAttempts) {
      showMessage(
        'El procesamiento está tomando más tiempo de lo esperado',
        isError: true,
      );
    }
  }

  // Compartir documento
  Future<void> shareDocument(Document document, List<int> userIds) async {
    try {
      await _documentService.shareDocument(
        documentId: document.id,
        userIds: userIds,
      );

      showMessage('Documento compartido exitosamente');

      // Recargar documentos para actualizar estado
      await loadDocuments();
    } catch (e) {
      showMessage(
        'Error al compartir: ${e.toString()}',
        isError: true,
      );
    }
  }



  // Eliminar documento
  Future<void> deleteDocument(Document document) async {
    try {
      showMessage('Eliminando documento...');

      await _documentService.deleteDocument(document.id);

      showMessage(
        'Documento eliminado exitosamente',
        isError: true, // Rojo para indicar eliminación
      );

      // Recargar lista de documentos
      await loadDocuments();
      
      // Invalidar caché de estadísticas para forzar actualización
      await _statisticsService.invalidateCache();
      debugPrint('🔄 Caché de estadísticas invalidado después de eliminar documento');
    } catch (e) {
      showMessage(
        'Error al eliminar documento: ${e.toString()}',
        isError: true,
      );
    }
  }

  // Mostrar mensaje (SnackBar)
  void showMessage(
    String message, {
    bool isError = false,
    SnackBarAction? action,
  }) {
    messengerKey.currentState?.showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError
            ? Colors.red
            : (message.contains('eliminado')
                ? Colors.red
                : (message.contains('Obteniendo')
                    ? const Color(0xFF2196F3)
                    : const Color(0xFF4CAF50))),
        action: action,
      ),
    );
  }
}
