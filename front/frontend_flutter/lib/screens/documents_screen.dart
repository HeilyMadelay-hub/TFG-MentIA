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
import '../utils/responsive_utils.dart';

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
      final myDocs = await _documentService.listDocuments();
      allDocuments.addAll(myDocs);

      // Si NO es admin, también cargar documentos compartidos con él
      if (!(_currentUser?.isAdmin ?? false)) {
        try {
          final sharedDocs = await _documentService.getSharedWithMe();
          // Marcar los documentos compartidos
          for (var doc in sharedDocs) {
            doc.isShared = true;
          }
          allDocuments.addAll(sharedDocs);
        } catch (e) {
          // Continuar sin documentos compartidos si hay error
        }
      }

      setState(() {
        _documents = allDocuments;
        _isLoading = false;
      });
    } catch (e) {
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
    return ResponsiveBuilder(
      builder: (context, sizingInfo) {
        return Scaffold(
          backgroundColor: Colors.grey[50],
          body: Padding(
            padding: EdgeInsets.all(sizingInfo.padding),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                _buildHeader(sizingInfo),
                SizedBox(height: sizingInfo.spacing * 2),

                // Barra de búsqueda y filtros
                _buildSearchAndFilters(sizingInfo),
                SizedBox(height: sizingInfo.spacing * 2),

                // Lista de documentos
                Expanded(
                  child: _isLoading
                      ? const Center(
                          child:
                              CircularProgressIndicator(color: Color(0xFF6B4CE6)))
                      : _filteredDocuments.isEmpty
                          ? _buildEmptyState(sizingInfo)
                          : _buildDocumentsList(sizingInfo),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildHeader(ResponsiveInfo sizingInfo) {
    return sizingInfo.isMobile
        ? Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Mis Documentos',
                    style: TextStyle(
                      fontSize: sizingInfo.fontSize.title,
                      fontWeight: FontWeight.bold,
                      color: const Color(0xFF2C3E50),
                    ),
                  ),
                  SizedBox(height: sizingInfo.spacing / 2),
                  Text(
                    '${_documents.length} documento${_documents.length != 1 ? 's' : ''}',
                    style: TextStyle(
                      fontSize: sizingInfo.fontSize.body,
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ),
              SizedBox(height: sizingInfo.spacing),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _uploadDocument,
                  icon: Icon(Icons.add, size: sizingInfo.fontSize.icon),
                  label: Text(
                    'Subir Documento',
                    style: TextStyle(fontSize: sizingInfo.fontSize.button),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF6B4CE6),
                    foregroundColor: Colors.white,
                    padding: EdgeInsets.symmetric(
                      horizontal: sizingInfo.cardPadding,
                      vertical: sizingInfo.spacing,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
                    ),
                  ),
                ),
              ),
            ],
          )
        : Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Mis Documentos',
                    style: TextStyle(
                      fontSize: sizingInfo.fontSize.title,
                      fontWeight: FontWeight.bold,
                      color: const Color(0xFF2C3E50),
                    ),
                  ),
                  Text(
                    '${_documents.length} documento${_documents.length != 1 ? 's' : ''}',
                    style: TextStyle(
                      fontSize: sizingInfo.fontSize.body,
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ),
              ElevatedButton.icon(
                onPressed: _uploadDocument,
                icon: Icon(Icons.add, size: sizingInfo.fontSize.icon),
                label: Text(
                  'Subir Documento',
                  style: TextStyle(fontSize: sizingInfo.fontSize.button),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6B4CE6),
                  foregroundColor: Colors.white,
                  padding: EdgeInsets.symmetric(
                    horizontal: sizingInfo.cardPadding,
                    vertical: sizingInfo.spacing,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
                  ),
                ),
              ),
            ],
          );
  }

  Widget _buildSearchAndFilters(ResponsiveInfo sizingInfo) {
    if (sizingInfo.isMobile) {
      return Column(
        children: [
          // Barra de búsqueda
          TextField(
            controller: _searchController,
            style: TextStyle(fontSize: sizingInfo.fontSize.body),
            decoration: InputDecoration(
              hintText: 'Buscar documentos...',
              hintStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
              prefixIcon: Icon(Icons.search, size: sizingInfo.fontSize.icon),
              suffixIcon: _searchController.text.isNotEmpty
                  ? IconButton(
                      icon: Icon(Icons.clear, size: sizingInfo.fontSize.icon),
                      onPressed: () {
                        _searchController.clear();
                      },
                    )
                  : null,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                borderSide: BorderSide.none,
              ),
              filled: true,
              fillColor: Colors.white,
              contentPadding: EdgeInsets.symmetric(
                horizontal: sizingInfo.cardPadding,
                vertical: sizingInfo.spacing,
              ),
            ),
          ),
          SizedBox(height: sizingInfo.spacing),
          // Filtros en línea horizontal con scroll
          SizedBox(
            height: 40,
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: _buildFilterChips(sizingInfo),
            ),
          ),
        ],
      );
    }

    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: _searchController,
            style: TextStyle(fontSize: sizingInfo.fontSize.body),
            decoration: InputDecoration(
              hintText: 'Buscar documentos...',
              hintStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
              prefixIcon: Icon(Icons.search, size: sizingInfo.fontSize.icon),
              suffixIcon: _searchController.text.isNotEmpty
                  ? IconButton(
                      icon: Icon(Icons.clear, size: sizingInfo.fontSize.icon),
                      onPressed: () {
                        _searchController.clear();
                      },
                    )
                  : null,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                borderSide: BorderSide.none,
              ),
              filled: true,
              fillColor: Colors.white,
              contentPadding: EdgeInsets.symmetric(
                horizontal: sizingInfo.cardPadding,
                vertical: sizingInfo.spacing,
              ),
            ),
          ),
        ),
        SizedBox(width: sizingInfo.spacing),
        // Filtros
        ..._buildFilterChips(sizingInfo),
      ],
    );
  }

  List<Widget> _buildFilterChips(ResponsiveInfo sizingInfo) {
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
        padding: EdgeInsets.only(left: sizingInfo.spacing / 2),
        child: FilterChip(
          label: Text(
            filter,
            style: TextStyle(fontSize: sizingInfo.fontSize.caption),
          ),
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
            fontSize: sizingInfo.fontSize.caption,
          ),
          padding: EdgeInsets.symmetric(
            horizontal: sizingInfo.spacing,
            vertical: sizingInfo.spacing / 2,
          ),
        ),
      );
    }).toList();
  }

  Widget _buildEmptyState(ResponsiveInfo sizingInfo) {
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
      child: Padding(
        padding: EdgeInsets.all(sizingInfo.padding),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.folder_open,
              size: sizingInfo.fontSize.emptyStateIcon,
              color: Colors.grey[400],
            ),
            SizedBox(height: sizingInfo.spacing * 2),
            Text(
              title,
              style: TextStyle(
                fontSize: sizingInfo.fontSize.subtitle,
                fontWeight: FontWeight.w600,
                color: const Color(0xFF2C3E50),
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: sizingInfo.spacing),
            Text(
              subtitle,
              style: TextStyle(
                fontSize: sizingInfo.fontSize.body,
                color: Colors.grey[600],
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDocumentsList(ResponsiveInfo sizingInfo) {
    if (sizingInfo.isMobile || sizingInfo.isTablet) {
      return ListView.builder(
        itemCount: _filteredDocuments.length,
        itemBuilder: (context, index) {
          final doc = _filteredDocuments[index];
          return _buildDocumentCard(doc, sizingInfo);
        },
      );
    }

    // Vista en grid para desktop
    return ResponsiveGrid(
      maxColumns: 3,
      childAspectRatio: 3.5,
      children: _filteredDocuments
          .map((doc) => _buildDocumentCard(doc, sizingInfo))
          .toList(),
    );
  }

  Widget _buildDocumentCard(Document doc, ResponsiveInfo sizingInfo) {
    final isAdmin = _currentUser?.isAdmin ?? false;
    final isOwner = doc.uploadedBy == _currentUser?.id;

    return ResponsiveCard(
      onTap: () => _openDocument(doc),
      child: Row(
        children: [
          // Icono del documento
          Container(
            width: sizingInfo.listTileIconSize,
            height: sizingInfo.listTileIconSize,
            decoration: BoxDecoration(
              color: _getDocumentColor(doc.contentType).withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
            ),
            child: Icon(
              _getDocumentIcon(doc.contentType),
              color: _getDocumentColor(doc.contentType),
              size: sizingInfo.fontSize.icon,
            ),
          ),
          SizedBox(width: sizingInfo.spacing),

          // Información del documento
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  doc.title,
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: sizingInfo.fontSize.body,
                    color: const Color(0xFF2C3E50),
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                SizedBox(height: sizingInfo.spacing / 2),
                Row(
                  children: [
                    Text(
                      _getDocumentType(doc.contentType),
                      style: TextStyle(
                        fontSize: sizingInfo.fontSize.caption,
                        color: Colors.grey[600],
                      ),
                    ),
                    if (!isAdmin && doc.isShared) ...[
                      SizedBox(width: sizingInfo.spacing),
                      Container(
                        padding: EdgeInsets.symmetric(
                          horizontal: sizingInfo.spacing,
                          vertical: sizingInfo.spacing / 4,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.blue.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius / 2),
                        ),
                        child: Text(
                          'Compartido',
                          style: TextStyle(
                            fontSize: sizingInfo.fontSize.caption * 0.9,
                            color: Colors.blue[700],
                            fontWeight: FontWeight.w500,
                          ),
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
            icon: Icon(
              Icons.more_vert, 
              color: Colors.grey[600],
              size: sizingInfo.fontSize.icon,
            ),
            onSelected: (value) => _handleDocumentAction(value, doc),
            itemBuilder: (context) {
              List<PopupMenuItem<String>> items = [];

              // Opción de compartir (solo para administradores y propietarios)
              if (isOwner && isAdmin) {
                items.add(
                  PopupMenuItem(
                    value: 'share',
                    child: Row(
                      children: [
                        Icon(Icons.share, size: sizingInfo.fontSize.icon),
                        SizedBox(width: sizingInfo.spacing),
                        Text('Compartir', style: TextStyle(fontSize: sizingInfo.fontSize.body)),
                      ],
                    ),
                  ),
                );
              }

              // Opción de eliminar (solo para propietarios)
              if (isOwner) {
                items.add(
                  PopupMenuItem(
                    value: 'delete',
                    child: Row(
                      children: [
                        Icon(Icons.delete, size: sizingInfo.fontSize.icon, color: Colors.red),
                        SizedBox(width: sizingInfo.spacing),
                        Text(
                          'Eliminar',
                          style: TextStyle(
                            color: Colors.red,
                            fontSize: sizingInfo.fontSize.body,
                          ),
                        ),
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
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Documento eliminado exitosamente'),
            backgroundColor: Colors.green,
          ),
        );
          _loadDocuments();
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error al eliminar documento: $e'),
            backgroundColor: Colors.red,
          ),
        );
        }
      }
    }
  }

  Future<void> _uploadDocument() async {
    final sizingInfo = context.responsive;
    
    // Mostrar diálogo de selección de tipo con diseño responsive
    final fileType = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          'Seleccionar tipo de archivo',
          style: TextStyle(fontSize: sizingInfo.fontSize.subtitle),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: Icon(Icons.picture_as_pdf, color: Colors.red, size: sizingInfo.fontSize.icon),
              title: Text('PDF', style: TextStyle(fontSize: sizingInfo.fontSize.body)),
              onTap: () => Navigator.pop(context, 'PDF'),
            ),
            ListTile(
              leading: Icon(Icons.text_snippet, color: Colors.blue, size: sizingInfo.fontSize.icon),
              title: Text('Texto (TXT)', style: TextStyle(fontSize: sizingInfo.fontSize.body)),
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
          builder: (context) => AlertDialog(
            content: Row(
              children: [
                const CircularProgressIndicator(color: Color(0xFF6B4CE6)),
                SizedBox(width: sizingInfo.spacing * 2),
                Text(
                  'Subiendo documento...',
                  style: TextStyle(fontSize: sizingInfo.fontSize.body),
                ),
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
    final sizingInfo = context.responsive;
    
    // Mostrar diálogo con opciones
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          'Documento: ${document.title}',
          style: TextStyle(fontSize: sizingInfo.fontSize.subtitle),
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    _getDocumentIcon(document.contentType),
                    color: _getDocumentColor(document.contentType),
                    size: sizingInfo.fontSize.icon,
                  ),
                  SizedBox(width: sizingInfo.spacing),
                  Expanded(
                    child: Text(
                      document.fileName,
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: sizingInfo.fontSize.body,
                      ),
                    ),
                  ),
                ],
              ),
              SizedBox(height: sizingInfo.spacing),
              _buildInfoRow('Tipo:', _getDocumentType(document.contentType), sizingInfo),
              if (document.fileSize != null)
                _buildInfoRow('Tamaño:', _formatFileSize(document.fileSize!), sizingInfo),
              _buildInfoRow('Estado:', _getDocumentStatus(document), sizingInfo),
              if (document.isShared)
                _buildInfoRow('Acceso:', 'Compartido', sizingInfo),
              SizedBox(height: sizingInfo.spacing * 2),
              if (document.fileUrl != null && document.fileUrl!.isNotEmpty) ...[
                const Divider(),
                SizedBox(height: sizingInfo.spacing),
                Text(
                  'Acciones disponibles:',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: sizingInfo.fontSize.body,
                  ),
                ),
                SizedBox(height: sizingInfo.spacing),
                if (sizingInfo.isMobile) ...[
                  // Botones en columna para móvil
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: () {
                        Navigator.pop(context);
                        _viewDocumentInBrowser(document);
                      },
                      icon: Icon(Icons.open_in_new, size: sizingInfo.fontSize.icon),
                      label: Text(
                        'Ver en navegador',
                        style: TextStyle(fontSize: sizingInfo.fontSize.button),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF2196F3),
                        foregroundColor: Colors.white,
                        padding: EdgeInsets.symmetric(vertical: sizingInfo.spacing),
                      ),
                    ),
                  ),
                  if (!kIsWeb) ...[
                    SizedBox(height: sizingInfo.spacing),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: () {
                          Navigator.pop(context);
                          _downloadDocument(document);
                        },
                        icon: Icon(Icons.download, size: sizingInfo.fontSize.icon),
                        label: Text(
                          'Descargar',
                          style: TextStyle(fontSize: sizingInfo.fontSize.button),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF4CAF50),
                          foregroundColor: Colors.white,
                          padding: EdgeInsets.symmetric(vertical: sizingInfo.spacing),
                        ),
                      ),
                    ),
                  ],
                ] else ...[
                  // Botones en fila para tablet/desktop
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      ElevatedButton.icon(
                        onPressed: () {
                          Navigator.pop(context);
                          _viewDocumentInBrowser(document);
                        },
                        icon: Icon(Icons.open_in_new, size: sizingInfo.fontSize.icon),
                        label: Text(
                          'Ver en navegador',
                          style: TextStyle(fontSize: sizingInfo.fontSize.button),
                        ),
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
                          icon: Icon(Icons.download, size: sizingInfo.fontSize.icon),
                          label: Text(
                            'Descargar',
                            style: TextStyle(fontSize: sizingInfo.fontSize.button),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF4CAF50),
                            foregroundColor: Colors.white,
                          ),
                        ),
                    ],
                  ),
                ],
              ] else ...[
                Container(
                  padding: EdgeInsets.all(sizingInfo.spacing),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade50,
                    borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                    border: Border.all(color: Colors.orange.shade200),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.warning, 
                        color: Colors.orange.shade700, 
                        size: sizingInfo.fontSize.icon
                      ),
                      SizedBox(width: sizingInfo.spacing),
                      Expanded(
                        child: Text(
                          _getStatusMessage(document),
                          style: TextStyle(fontSize: sizingInfo.fontSize.caption),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              'Cerrar',
              style: TextStyle(fontSize: sizingInfo.fontSize.button),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, ResponsiveInfo sizingInfo) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: sizingInfo.spacing / 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: sizingInfo.isSmallDevice ? 60 : 80,
            child: Text(
              label,
              style: TextStyle(
                color: Colors.grey[600], 
                fontSize: sizingInfo.fontSize.caption
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(fontSize: sizingInfo.fontSize.body),
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
          content: Text('Este documento no tiene un archivo asociado'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    try {
      // Para archivos PDF, abrir en nueva pestaña con visor nativo del navegador
      if (document.contentType == 'application/pdf') {
        // Asegurarse de que la URL sea absoluta
        String fileUrl = document.fileUrl!;
        if (!fileUrl.startsWith('http')) {
          fileUrl = 'http://localhost:2690$fileUrl';
        }
        
        final Uri url = Uri.parse(fileUrl);
        
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
      } else {
        // Para otros tipos de archivo, descargar
        await _downloadDocument(document);
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
            // Progress: (received / total * 100).toStringAsFixed(0)%
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