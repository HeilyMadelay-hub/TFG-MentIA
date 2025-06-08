import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';
import '../models/document.dart';
import '../models/user.dart';
import '../services/document_service.dart';
import '../services/auth_service.dart';
import '../providers/documents_provider.dart';
import '../widgets/share_document_dialog.dart';

class DocumentsScreen extends StatefulWidget {
  const DocumentsScreen({super.key});

  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  final TextEditingController _searchController = TextEditingController();
  final DocumentService _documentService = DocumentService();
  List<Document> _documents = [];
  bool _isLoading = true;
  String _searchQuery = '';
  String _selectedFilter = 'Todos';
  User? _currentUser;

  @override
  void initState() {
    super.initState();
    _currentUser = AuthService().currentUser;
    _loadDocuments();
    _searchController.addListener(_onSearchChanged);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadDocuments() async {
    setState(() => _isLoading = true);

    try {
      List<Document> allDocuments = [];

      // Cargar documentos propios
      debugPrint('🔄 Iniciando carga de documentos...');
      final myDocs = await _documentService.listDocuments();
      debugPrint('📄 Documentos propios cargados: ${myDocs.length}');
      allDocuments.addAll(myDocs);

      // Si NO es admin, también cargar documentos compartidos con él
      if (!(_currentUser?.isAdmin ?? false)) {
        try {
          debugPrint('🔄 Cargando documentos compartidos...');
          final sharedDocs = await _documentService.getSharedWithMe();
          debugPrint(
              '📄 Documentos compartidos cargados: ${sharedDocs.length}');
          // Marcar los documentos compartidos
          for (var doc in sharedDocs) {
            doc.isShared = true;
          }
          allDocuments.addAll(sharedDocs);
        } catch (e) {
          debugPrint('Error loading shared documents: $e');
          // Continuar sin documentos compartidos si hay error
        }
      }

      setState(() {
        _documents = allDocuments;
        _isLoading = false;
      });
      debugPrint('✅ Total documentos cargados: ${_documents.length}');
    } catch (e) {
      debugPrint('❌ Error loading documents: $e');
      setState(() => _isLoading = false);

      if (e.toString().contains('No autenticado') ||
          e.toString().contains('401') ||
          e.toString().contains('token inválido')) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Sesión expirada. Redirigiendo a login...'),
              backgroundColor: Colors.orange,
              duration: Duration(seconds: 2),
            ),
          );

          Future.delayed(const Duration(seconds: 2), () {
            if (mounted) {
              Navigator.of(context)
                  .pushNamedAndRemoveUntil('/login', (route) => false);
            }
          });
        }
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Error al cargar documentos: ${e.toString()}'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    }
  }

  List<Document> get _filteredDocuments {
    var docs = _documents;

    // Filtrar por búsqueda
    if (_searchQuery.isNotEmpty) {
      docs = docs
          .where((doc) =>
              doc.title.toLowerCase().contains(_searchQuery.toLowerCase()))
          .toList();
    }

    // Filtrar por tipo
    switch (_selectedFilter) {
      case 'Compartidos':
        docs = docs.where((doc) => doc.isShared).toList();
        break;
      case 'PDF':
        docs =
            docs.where((doc) => doc.contentType == 'application/pdf').toList();
        break;
      case 'TXT':
        docs = docs.where((doc) => doc.contentType == 'text/plain').toList();
        break;
    }

    return docs;
  }

  void _onSearchChanged() {
    setState(() {
      _searchQuery = _searchController.text;
    });
  }

  @override
  Widget build(BuildContext context) {
    final isAdmin = _currentUser?.isAdmin ?? false;

    return Scaffold(
      backgroundColor: Colors.grey[50],
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Mis Documentos',
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF2C3E50),
                      ),
                    ),
                    Text(
                      '${_documents.length} documento${_documents.length != 1 ? 's' : ''}',
                      style: TextStyle(
                        fontSize: 16,
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                ),
                ElevatedButton.icon(
                  onPressed: _uploadDocument,
                  icon: const Icon(Icons.add),
                  label: const Text('Subir Documento'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF6B4CE6),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 24,
                      vertical: 12,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Barra de búsqueda y filtros
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      hintText: 'Buscar documentos...',
                      prefixIcon: const Icon(Icons.search),
                      suffixIcon: _searchController.text.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear),
                              onPressed: () {
                                _searchController.clear();
                              },
                            )
                          : null,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                      filled: true,
                      fillColor: Colors.white,
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                // Filtros
                ..._buildFilterChips(),
              ],
            ),
            const SizedBox(height: 24),

            // Lista de documentos
            Expanded(
              child: _isLoading
                  ? const Center(
                      child:
                          CircularProgressIndicator(color: Color(0xFF6B4CE6)))
                  : _filteredDocuments.isEmpty
                      ? _buildEmptyState()
                      : _buildDocumentsList(),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildFilterChips() {
    final isAdmin = _currentUser?.isAdmin ?? false;
    final filters = ['Todos'];

    // Solo mostrar filtro "Compartidos" si NO es admin
    if (!isAdmin) {
      filters.add('Compartidos');
    }

    filters.addAll(['PDF', 'TXT']);

    return filters.map((filter) {
      final isSelected = _selectedFilter == filter;
      return Padding(
        padding: const EdgeInsets.only(left: 8),
        child: FilterChip(
          label: Text(filter),
          selected: isSelected,
          onSelected: (selected) {
            setState(() {
              _selectedFilter = selected ? filter : 'Todos';
            });
          },
          selectedColor: const Color(0xFF6B4CE6).withValues(alpha: 0.2),
          checkmarkColor: const Color(0xFF6B4CE6),
          labelStyle: TextStyle(
            color: isSelected ? const Color(0xFF6B4CE6) : Colors.grey[700],
          ),
        ),
      );
    }).toList();
  }

  Widget _buildEmptyState() {
    // Determinar qué mensaje mostrar según el filtro seleccionado
    String title;
    String subtitle;
    
    if (_searchQuery.isNotEmpty) {
      title = 'No se encontraron documentos';
      subtitle = 'Intenta con otros términos de búsqueda';
    } else if (_selectedFilter == 'Compartidos') {
      title = 'No te han dado acceso a ningún documento';
      subtitle = 'Los documentos compartidos contigo aparecerán aquí';
    } else {
      title = 'No tienes documentos aún';
      subtitle = 'Sube tu primer documento para comenzar';
    }
    
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.folder_open,
            size: 80,
            color: Colors.grey[400],
          ),
          const SizedBox(height: 24),
          Text(
            title,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: Color(0xFF2C3E50),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDocumentsList() {
    return ListView.builder(
      itemCount: _filteredDocuments.length,
      itemBuilder: (context, index) {
        final doc = _filteredDocuments[index];
        return _buildDocumentCard(doc);
      },
    );
  }

  Widget _buildDocumentCard(Document doc) {
    final isAdmin = _currentUser?.isAdmin ?? false;
    final isOwner = doc.uploadedBy == _currentUser?.id;

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => _openDocument(doc),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              // Icono del documento
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color:
                      _getDocumentColor(doc.contentType).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  _getDocumentIcon(doc.contentType),
                  color: _getDocumentColor(doc.contentType),
                  size: 28,
                ),
              ),
              const SizedBox(width: 16),

              // Información del documento
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      doc.title,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 16,
                        color: Color(0xFF2C3E50),
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Text(
                          _getDocumentType(doc.contentType),
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey[600],
                          ),
                        ),
                        if (!isAdmin && doc.isShared) ...[
                          const SizedBox(width: 8),
                          Text(
                            '• Compartido',
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.blue[600],
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),

              // Acciones
              PopupMenuButton<String>(
                icon: Icon(Icons.more_vert, color: Colors.grey[600]),
                onSelected: (value) => _handleDocumentAction(value, doc),
                itemBuilder: (context) {
                  List<PopupMenuItem<String>> items = [];

                  // Opción de compartir (solo para administradores y propietarios)
                  if (isOwner && isAdmin) {
                    items.add(
                      const PopupMenuItem(
                        value: 'share',
                        child: Row(
                          children: [
                            Icon(Icons.share, size: 20),
                            SizedBox(width: 8),
                            Text('Compartir'),
                          ],
                        ),
                      ),
                    );
                  }

                  // Opción de eliminar (solo para propietarios)
                  if (isOwner) {
                    items.add(
                      const PopupMenuItem(
                        value: 'delete',
                        child: Row(
                          children: [
                            Icon(Icons.delete, size: 20, color: Colors.red),
                            SizedBox(width: 8),
                            Text('Eliminar',
                                style: TextStyle(color: Colors.red)),
                          ],
                        ),
                      ),
                    );
                  }

                  return items;
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _handleDocumentAction(String action, Document doc) {
    switch (action) {
      case 'share':
        showDialog(
          context: context,
          builder: (context) => ShareDocumentDialog(
            document: doc,
            onShared: _loadDocuments,
          ),
        );
        break;
      case 'delete':
        _deleteDocument(doc);
        break;
    }
  }

  Future<void> _deleteDocument(Document doc) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Eliminar Documento'),
        content: Text('¿Estás seguro de que deseas eliminar "${doc.title}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );

    if (confirm ?? false) {
      try {
        await _documentService.deleteDocument(doc.id);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Documento eliminado exitosamente'),
            backgroundColor: Colors.green,
          ),
        );
        _loadDocuments();
      } catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error al eliminar documento: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _uploadDocument() async {
    // Mostrar diálogo de selección de tipo
    final fileType = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Seleccionar tipo de archivo'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.picture_as_pdf, color: Colors.red),
              title: const Text('PDF'),
              onTap: () => Navigator.pop(context, 'PDF'),
            ),
            ListTile(
              leading: const Icon(Icons.text_snippet, color: Colors.blue),
              title: const Text('Texto (TXT)'),
              onTap: () => Navigator.pop(context, 'TXT'),
            ),
          ],
        ),
      ),
    );

    if (fileType == null) return;

    try {
      List<String> allowedExtensions = fileType == 'PDF' ? ['pdf'] : ['txt'];

      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: allowedExtensions,
        withData: kIsWeb,
      );

      if (result != null) {
        PlatformFile file = result.files.first;

        // Validar tamaño
        if (file.size > 100 * 1024 * 1024) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content:
                  Text('El archivo excede el tamaño máximo permitido de 100MB'),
              backgroundColor: Colors.red,
            ),
          );
          return;
        }

        String contentType =
            file.extension == 'pdf' ? 'application/pdf' : 'text/plain';
        String title = file.name.replaceAll('.${file.extension}', '');

        // Mostrar diálogo de progreso
        if (!mounted) return;
        showDialog(
          context: context,
          barrierDismissible: false,
          builder: (context) => const AlertDialog(
            content: Row(
              children: [
                CircularProgressIndicator(color: Color(0xFF6B4CE6)),
                SizedBox(width: 20),
                Text('Subiendo documento...'),
              ],
            ),
          ),
        );

        // En web, usar bytes; en otras plataformas, usar path
        if (kIsWeb) {
          if (file.bytes != null) {
            if (!mounted) return;
            await context.read<DocumentsProvider>().uploadDocument(
                  title: title,
                  filePath: '',
                  contentType: contentType,
                  fileBytes: file.bytes,
                  filename: file.name,
                );
          }
        } else {
          if (file.path != null) {
            if (!mounted) return;
            await context.read<DocumentsProvider>().uploadDocument(
                  title: title,
                  filePath: file.path!,
                  contentType: contentType,
                );
          }
        }

        if (!mounted) return;
        Navigator.pop(context); // Cerrar diálogo de progreso
        _loadDocuments(); // Recargar documentos
      }
    } catch (e) {
      if (!mounted) return;
      Navigator.pop(context); // Cerrar diálogo si está abierto
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error al subir documento: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  IconData _getDocumentIcon(String? contentType) {
    switch (contentType) {
      case 'application/pdf':
        return Icons.picture_as_pdf;
      case 'text/plain':
        return Icons.description;
      default:
        return Icons.insert_drive_file;
    }
  }

  Color _getDocumentColor(String? contentType) {
    switch (contentType) {
      case 'application/pdf':
        return Colors.red;
      case 'text/plain':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }

  String _getDocumentType(String? contentType) {
    switch (contentType) {
      case 'application/pdf':
        return 'PDF';
      case 'text/plain':
        return 'Documento de texto';
      default:
        return 'Documento';
    }
  }

  void _openDocument(Document document) async {
    // Mostrar diálogo con opciones
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Documento: ${document.title}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  _getDocumentIcon(document.contentType),
                  color: _getDocumentColor(document.contentType),
                  size: 24,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    document.fileName,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _buildInfoRow('Tipo:', _getDocumentType(document.contentType)),
            if (document.fileSize != null)
              _buildInfoRow('Tamaño:', _formatFileSize(document.fileSize!)),
            _buildInfoRow('Estado:', _getDocumentStatus(document)),
            if (document.isShared)
              _buildInfoRow('Acceso:', 'Compartido'),
            const SizedBox(height: 16),
            if (document.fileUrl != null && document.fileUrl!.isNotEmpty) ...
            [
              const Divider(),
              const SizedBox(height: 8),
              const Text(
                'Acciones disponibles:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  ElevatedButton.icon(
                    onPressed: () {
                      Navigator.pop(context);
                      _viewDocumentInBrowser(document);
                    },
                    icon: const Icon(Icons.open_in_new),
                    label: const Text('Ver en navegador'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF2196F3),
                      foregroundColor: Colors.white,
                    ),
                  ),
                  if (!kIsWeb)
                    ElevatedButton.icon(
                      onPressed: () {
                        Navigator.pop(context);
                        _downloadDocument(document);
                      },
                      icon: const Icon(Icons.download),
                      label: const Text('Descargar'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF4CAF50),
                        foregroundColor: Colors.white,
                      ),
                    ),
                ],
              ),
            ] else ...
            [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.orange.shade200),
                ),
                child: Row(
                  children: [
                    Icon(Icons.warning, color: Colors.orange.shade700, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _getStatusMessage(document),
                        style: const TextStyle(fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cerrar'),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(
              label,
              style: TextStyle(color: Colors.grey[600], fontSize: 14),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }

  String _formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }

  Future<void> _viewDocumentInBrowser(Document document) async {
    if (document.fileUrl == null || document.fileUrl!.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('URL del documento no disponible'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    try {
      final Uri url = Uri.parse(document.fileUrl!);
      if (await canLaunchUrl(url)) {
        await launchUrl(url, mode: LaunchMode.externalApplication);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Abriendo ${document.title} en el navegador'),
            backgroundColor: const Color(0xFF2196F3),
          ),
        );
      } else {
        throw 'No se pudo abrir la URL';
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error al abrir el documento: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  String _getDocumentStatus(Document document) {
    switch (document.status) {
      case 'completed':
        return 'Procesado ✅';
      case 'processing':
        return 'Procesando... ⏳';
      case 'error':
        return 'Error ❌';
      case 'pending':
        return 'Pendiente ⏱️';
      default:
        return 'Desconocido';
    }
  }

  String _getStatusMessage(Document document) {
    if (document.status == 'processing') {
      return 'El documento aún se está procesando. Por favor, espera unos momentos...';
    } else if (document.status == 'error') {
      return document.statusMessage ?? 'Ocurrió un error al procesar el documento';
    } else if (document.status == 'pending') {
      return 'El documento está en cola para ser procesado';
    } else if (document.fileUrl == null || document.fileUrl!.isEmpty) {
      return 'Este documento no tiene un archivo asociado (solo contenido de texto)';
    }
    return 'El archivo no está disponible para visualización';
  }

  Future<void> _downloadDocument(Document document) async {
    if (document.fileUrl == null || document.fileUrl!.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('URL del documento no disponible'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    try {
      // Mostrar indicador de descarga
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Row(
            children: [
              SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              ),
              SizedBox(width: 12),
              Text('Descargando documento...'),
            ],
          ),
          duration: Duration(seconds: 30),
        ),
      );

      // Obtener el directorio de descargas
      final Directory? downloadsDir = await getDownloadsDirectory();
      if (downloadsDir == null) {
        throw 'No se pudo acceder al directorio de descargas';
      }

      // Crear nombre de archivo único
      final String fileName = '${document.id}_${document.fileName}';
      final String filePath = '${downloadsDir.path}/$fileName';

      // Descargar el archivo
      final dio = Dio();
      await dio.download(
        document.fileUrl!,
        filePath,
        onReceiveProgress: (received, total) {
          if (total != -1) {
            final progress = (received / total * 100).toStringAsFixed(0);
            debugPrint('Descarga: $progress%');
          }
        },
      );

      // Mostrar mensaje de éxito
      ScaffoldMessenger.of(context).clearSnackBars();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Documento descargado en: $filePath'),
          backgroundColor: const Color(0xFF4CAF50),
          action: SnackBarAction(
            label: 'Abrir',
            textColor: Colors.white,
            onPressed: () async {
              final file = File(filePath);
              if (await file.exists()) {
                final Uri fileUri = Uri.file(filePath);
                if (await canLaunchUrl(fileUri)) {
                  await launchUrl(fileUri);
                }
              }
            },
          ),
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).clearSnackBars();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error al descargar: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
}
