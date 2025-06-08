import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io';
import 'package:url_launcher/url_launcher.dart';
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:flutter/foundation.dart' show kIsWeb;

import '../models/user.dart';
import '../models/document.dart';
import '../models/chat.dart';
import '../services/auth_service.dart';
import '../services/statistics_service.dart';
import '../services/document_service.dart';
import '../services/chat_service.dart';
import '../services/user_service.dart';
import '../services/admin_service.dart';
import '../config/api_config.dart';
import 'chat.dart'; // Importar la pantalla de chat

class AdminPanelScreen extends StatefulWidget {
  const AdminPanelScreen({super.key});

  @override
  State<AdminPanelScreen> createState() => _AdminPanelScreenState();
}

class _AdminPanelScreenState extends State<AdminPanelScreen>
    with TickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = false;
  bool _isLoadingStats = true;
  bool _isLoadingUsers = true;
  bool _isLoadingDocs = true;
  bool _isLoadingChats = true;

  // Servicios
  final StatisticsService _statisticsService = StatisticsService();
  final DocumentService _documentService = DocumentService();
  final ChatService _chatService = ChatService();
  final UserService _userService = UserService();
  final AdminService _adminService = AdminService();

  // Datos reales
  Map<String, int> _statistics = {
    'total_users': 0,
    'total_documents': 0,
    'active_chats': 0,
  };
  List<User> _users = [];
  List<Document> _allDocuments = [];
  List<ChatModel> _allChats = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadAdminData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _loadAdminData() async {
    // Cargar estadísticas
    _loadStatistics();
    // Cargar usuarios primero si es admin (necesario para el filtrado)
    if (AuthService().currentUser?.isAdmin == true) {
      await _loadUsers();
    }
    // Cargar documentos después de usuarios
    _loadDocuments();
    // Cargar chats después de usuarios
    _loadChats();
  }

  Future<void> _loadStatistics() async {
    try {
      setState(() {
        _isLoadingStats = true;
      });

      // Intentar obtener todos los datos del dashboard de una sola vez
      final dashboardData = await _statisticsService.getDashboardData();

      if (dashboardData['statistics'] != null) {
        if (mounted) {
          setState(() {
            _statistics = Map<String, int>.from(dashboardData['statistics']);
            _isLoadingStats = false;
          });
        }

        // Si el dashboard incluye documentos y chats recientes, actualizar también
        if (dashboardData['recent_documents'] != null &&
            dashboardData['recent_documents'].isNotEmpty) {
          // Los datos del dashboard son limitados, pero podemos usarlos para la actividad reciente
          debugPrint(
              'Dashboard incluye ${dashboardData['recent_documents'].length} documentos recientes');
        }

        if (dashboardData['recent_chats'] != null &&
            dashboardData['recent_chats'].isNotEmpty) {
          debugPrint(
              'Dashboard incluye ${dashboardData['recent_chats'].length} chats recientes');
        }
      }
    } catch (e) {
      debugPrint('Error loading dashboard data: $e');
      // Si falla el dashboard, intentar cargar solo las estadísticas
      try {
        final stats = await _statisticsService.getGlobalStatistics();
        if (mounted) {
          setState(() {
            _statistics = stats;
            _isLoadingStats = false;
          });
        }
      } catch (e2) {
        debugPrint('Error loading statistics: $e2');
        if (mounted) {
          setState(() {
            _isLoadingStats = false;
          });
        }
      }
    }
  }

  Future<void> _loadUsers() async {
    try {
      setState(() {
        _isLoadingUsers = true;
      });

      final users = await _userService.getUsers();

      if (mounted) {
        setState(() {
          _users = users;
          _isLoadingUsers = false;
        });
      }
    } catch (e) {
      debugPrint('Error loading users: $e');
      if (mounted) {
        setState(() {
          _isLoadingUsers = false;
        });
      }
    }
  }

  Future<void> _loadDocuments() async {
    try {
      setState(() {
        _isLoadingDocs = true;
      });

      debugPrint('🔄 [ADMIN PANEL] Cargando documentos...');
      
      // Para administradores, usar el servicio admin para obtener TODOS los documentos
      final documents = await _adminService.getAllDocuments();
      
      debugPrint('✅ [ADMIN PANEL] Total de documentos recibidos: ${documents.length}');
      
      // Mostrar algunos detalles de los documentos recibidos
      for (var i = 0; i < documents.length && i < 5; i++) {
        final doc = documents[i];
        debugPrint('  Doc ${i + 1}: ID=${doc.id}, UploadedBy=${doc.uploadedBy}, Title="${doc.title}"');
      }

      if (mounted) {
        setState(() {
          _allDocuments = documents;
          _isLoadingDocs = false;
        });
      }

      debugPrint('✅ Total de documentos en el sistema: ${documents.length}');
    } catch (e) {
      debugPrint('Error loading documents: $e');
      // Si falla el servicio admin, intentar con el servicio normal
      try {
        final documents = await _documentService.getDocuments();
        if (mounted) {
          setState(() {
            _allDocuments = documents;
            _isLoadingDocs = false;
          });
        }
      } catch (e2) {
        debugPrint('Error loading documents (fallback): $e2');
        if (mounted) {
          setState(() {
            _isLoadingDocs = false;
          });
        }
      }
    }
  }

  Future<void> _loadChats() async {
    try {
      setState(() {
        _isLoadingChats = true;
      });

      debugPrint('🔄 [ADMIN PANEL] Cargando chats...');
      debugPrint('👤 [ADMIN PANEL] Usuario actual: ${AuthService().currentUser?.username} (ID: ${AuthService().currentUser?.id})');
      
      // Para administradores, usar el servicio admin para obtener TODOS los chats
      final chats = await _adminService.getAllChats();
      
      debugPrint('✅ [ADMIN PANEL] Total de chats recibidos: ${chats.length}');
      
      // Mostrar algunos detalles de los chats recibidos
      for (var i = 0; i < chats.length && i < 10; i++) {
        final chat = chats[i];
        debugPrint('  Chat ${i + 1}: ID=${chat.id}, UserID=${chat.userId}, Title="${chat.title}"');
      }

      if (mounted) {
        setState(() {
          _allChats = chats;
          _isLoadingChats = false;
        });
      }

      debugPrint('✅ Total de chats en el sistema: ${chats.length}');
    } catch (e) {
      debugPrint('❌ Error loading chats: $e');
      if (mounted) {
        setState(() {
          _isLoadingChats = false;
          _allChats = [];
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isTablet = screenWidth >= 600;
    final isDesktop = screenWidth >= 1200;

    return SafeArea(
      child: Scaffold(
        backgroundColor: Colors.grey[50],
        body: Column(
          children: [
            // Header del panel de administración
            _buildAdminHeader(),

            // Tabs adaptables
            Container(
              color: Colors.white,
              child: TabBar(
                controller: _tabController,
                labelColor: const Color(0xFF6B4CE6),
                unselectedLabelColor: Colors.grey[600],
                indicatorColor: const Color(0xFF6B4CE6),
                isScrollable: !isDesktop, // Scrollable en móviles y tablets
                labelStyle: TextStyle(
                  fontSize: isDesktop ? 14 : (isTablet ? 12 : 10),
                  fontWeight: FontWeight.w500,
                ),
                tabs: [
                  Tab(
                    icon: Icon(Icons.dashboard,
                        size: isDesktop ? 24 : (isTablet ? 20 : 18)),
                    text: isDesktop
                        ? 'Dashboard'
                        : (screenWidth > 360 ? 'Dashboard' : 'Inicio'),
                  ),
                  Tab(
                    icon: Icon(Icons.people,
                        size: isDesktop ? 24 : (isTablet ? 20 : 18)),
                    text: 'Usuarios',
                  ),
                  Tab(
                    icon: Icon(Icons.folder,
                        size: isDesktop ? 24 : (isTablet ? 20 : 18)),
                    text: isDesktop
                        ? 'Documentos'
                        : (screenWidth > 360 ? 'Documentos' : 'Docs'),
                  ),
                  Tab(
                    icon: Icon(Icons.chat,
                        size: isDesktop ? 24 : (isTablet ? 20 : 18)),
                    text: 'Chats',
                  ),
                ],
              ),
            ),

            // Contenido de las tabs
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  _buildDashboardTab(),
                  _buildUsersTab(),
                  _buildDocumentsTab(),
                  _buildChatsTab(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAdminHeader() {
    final screenWidth = MediaQuery.of(context).size.width;
    final isTablet = screenWidth >= 600;

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isTablet ? 16 : 12,
        vertical: isTablet ? 12 : 10,
      ),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFF6B4CE6), Color(0xFF9C27B0)],
        ),
        boxShadow: [
          BoxShadow(color: Colors.black12, blurRadius: 8, offset: Offset(0, 4)),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  screenWidth > 360 ? 'Panel de Administración' : 'Admin Panel',
                  style: TextStyle(
                    fontSize: isTablet ? 22 : 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                if (screenWidth > 360) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Gestión completa del sistema DocuMente',
                    style: TextStyle(
                      fontSize: isTablet ? 14 : 12,
                      color: Colors.white.withAlpha(230),
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
          Container(
            padding: EdgeInsets.all(isTablet ? 12 : 8),
            decoration: BoxDecoration(
              color: Colors.white.withAlpha(51),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              Icons.admin_panel_settings,
              color: Colors.white,
              size: isTablet ? 24 : 20,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDashboardTab() {
    final screenWidth = MediaQuery.of(context).size.width;
    final isTablet = screenWidth >= 600;
    final padding = isTablet ? 24.0 : 16.0;

    return SingleChildScrollView(
      padding: EdgeInsets.all(padding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Estadísticas principales
          _buildStatsGrid(),

          SizedBox(height: isTablet ? 32 : 24),

          // Actividad reciente
          _buildRecentActivity(),
        ],
      ),
    );
  }

  Widget _buildStatsGrid() {
    final screenWidth = MediaQuery.of(context).size.width;
    final isTablet = screenWidth >= 600;
    final isDesktop = screenWidth >= 1200;
    final padding = isTablet ? 24.0 : 16.0;

    final stats = [
      {
        'title': 'Total Usuarios',
        'value': _isLoadingStats ? '...' : '${_statistics['total_users'] ?? 0}',
        'icon': Icons.people,
        'color': const Color(0xFF4CAF50),
      },
      {
        'title': 'Documentos',
        'value':
            _isLoadingStats ? '...' : '${_statistics['total_documents'] ?? 0}',
        'icon': Icons.folder,
        'color': const Color(0xFF2196F3),
      },
      {
        'title': 'Chats Activos',
        'value':
            _isLoadingStats ? '...' : '${_statistics['active_chats'] ?? 0}',
        'icon': Icons.chat,
        'color': const Color(0xFFFF9800),
      },
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Estadísticas del Sistema',
          style: TextStyle(
            fontSize: isTablet ? 20 : 18,
            fontWeight: FontWeight.bold,
            color: const Color(0xFF2C3E50),
          ),
        ),
        const SizedBox(height: 16),
        // Using a Wrap widget instead of GridView to avoid overflow issues
        Wrap(
          spacing: 16, // horizontal spacing
          runSpacing: 16, // vertical spacing
          children: stats.map((stat) {
            // Calculate number of columns based on screen size
            final crossAxisCount =
                isDesktop ? 3 : (isTablet ? 2 : (screenWidth > 360 ? 2 : 1));
            final itemWidth =
                (screenWidth - (padding * 2) - (16 * (crossAxisCount - 1))) /
                    crossAxisCount;

            return SizedBox(
              width: itemWidth,
              child: Container(
                padding: EdgeInsets.all(isTablet ? 16 : 12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withAlpha(13),
                      blurRadius: 10,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min, // Use minimal space needed
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: (stat['color'] as Color).withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        stat['icon'] as IconData,
                        color: stat['color'] as Color,
                        size: isTablet ? 24 : 20,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      stat['value'] as String,
                      style: TextStyle(
                        fontSize: isTablet ? 22 : 18,
                        fontWeight: FontWeight.bold,
                        color: const Color(0xFF2C3E50),
                      ),
                    ),
                    Text(
                      stat['title'] as String,
                      style: TextStyle(
                        fontSize: isTablet ? 12 : 11,
                        color: Colors.grey[600],
                      ),
                      textAlign: TextAlign.center,
                      overflow: TextOverflow.ellipsis,
                      maxLines: 2,
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildRecentActivity() {
    final screenWidth = MediaQuery.of(context).size.width;
    final isTablet = screenWidth >= 600;

    // Generar actividades dinámicamente basadas en los datos reales
    final activities = <Map<String, dynamic>>[];

    // Filtrar documentos excluyendo los de Ivan
    final userDocuments = _allDocuments.where((doc) {
      try {
        final owner = _users.firstWhere((u) => u.id == doc.uploadedBy);
        return owner.username.toLowerCase() != 'ivan';
      } catch (e) {
        return true;
      }
    }).toList();

    for (int i = 0; i < userDocuments.length && i < 2; i++) {
      final doc = userDocuments[i];
      activities.add({
        'action': 'Documento subido',
        'user': doc.title,
        'time': _formatDateTime(doc.createdAt),
        'icon': Icons.upload_file,
      });
    }

    // Filtrar chats excluyendo los de Ivan
    final userChats = _allChats.where((chat) {
      try {
        final user = _users.firstWhere((u) => u.id == chat.userId);
        return user.username.toLowerCase() != 'ivan';
      } catch (e) {
        return true;
      }
    }).toList();

    for (int i = 0; i < userChats.length && i < 2; i++) {
      final chat = userChats[i];
      activities.add({
        'action': 'Chat actualizado',
        'user': chat.title,
        'time': _formatDateTime(chat.updatedAt),
        'icon': Icons.chat,
      });
    }

    // Si no hay actividades, mostrar mensaje por defecto
    if (activities.isEmpty) {
      activities.add({
        'action': 'Sin actividad reciente',
        'user': 'El sistema está esperando nueva actividad',
        'time': 'Ahora',
        'icon': Icons.hourglass_empty,
      });
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Flexible(
              child: Text(
                'Actividad Reciente',
                style: TextStyle(
                  fontSize: isTablet ? 20 : 18,
                  fontWeight: FontWeight.bold,
                  color: const Color(0xFF2C3E50),
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            TextButton(onPressed: () {}, child: const Text('Ver todo')),
          ],
        ),
        const SizedBox(height: 16),
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withAlpha(13),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: activities.length,
            itemBuilder: (context, index) {
              final activity = activities[index];
              return Column(
                children: [
                  ListTile(
                    dense: true, // Makes the ListTile more compact
                    leading: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: const Color(0xFF6B4CE6).withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(
                        activity['icon'] as IconData,
                        color: const Color(0xFF6B4CE6),
                        size: 18,
                      ),
                    ),
                    title: Text(
                      activity['action'] as String,
                      style: TextStyle(fontSize: isTablet ? 14 : 13),
                    ),
                    subtitle: Text(
                      activity['user'] as String,
                      style: TextStyle(fontSize: isTablet ? 12 : 11),
                    ),
                    trailing: Text(
                      activity['time'] as String,
                      style: TextStyle(color: Colors.grey[600], fontSize: 11),
                    ),
                  ),
                  if (index < activities.length - 1)
                    const Divider(height: 1, indent: 16, endIndent: 16),
                ],
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildUsersTab() {
    final screenWidth = MediaQuery.of(context).size.width;
    final isTablet = screenWidth >= 600;
    final padding = isTablet ? 24.0 : 16.0;

    // Filtrar usuarios para excluir a Ivan
    final filteredUsers = _users.where((user) {
      // No mostrar a Ivan
      if (user.username.toLowerCase() == 'ivan') {
        return false;
      }
      return true;
    }).toList();

    return SingleChildScrollView(
      padding: EdgeInsets.all(padding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Gestión de Usuarios',
            style: TextStyle(
              fontSize: isTablet ? 20 : 18,
              fontWeight: FontWeight.bold,
              color: const Color(0xFF2C3E50),
            ),
          ),
          const SizedBox(height: 16),
          if (_isLoadingUsers)
            Container(
              height: 200,
              alignment: Alignment.center,
              child: const CircularProgressIndicator(
                color: Color(0xFF6B4CE6),
              ),
            )
          else if (filteredUsers.isEmpty)
            Container(
              padding: EdgeInsets.all(32),
              alignment: Alignment.center,
              child: Text(
                'No hay usuarios registrados',
                style: TextStyle(
                  color: Colors.grey[600],
                  fontSize: 16,
                ),
              ),
            )
          else
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withAlpha(13),
                    blurRadius: 10,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: filteredUsers.length,
                separatorBuilder: (context, index) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final user = filteredUsers[index];
                  return ListTile(
                    leading: CircleAvatar(
                      backgroundColor: user.isAdmin
                          ? const Color(0xFF6B4CE6).withValues(alpha: 0.1)
                          : Colors.grey[200],
                      child: Text(
                        user.username.substring(0, 1).toUpperCase(),
                        style: TextStyle(
                          color: user.isAdmin
                              ? const Color(0xFF6B4CE6)
                              : Colors.grey[700],
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    title: Text(user.username),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user.email,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Wrap(
                          spacing: 8,
                          runSpacing: 4,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: user.isAdmin
                                    ? const Color(0xFF6B4CE6)
                                        .withValues(alpha: 0.1)
                                    : Colors.grey[200],
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Text(
                                user.isAdmin ? 'Administrador' : 'Usuario',
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w500,
                                  color: user.isAdmin
                                      ? const Color(0xFF6B4CE6)
                                      : Colors.grey[700],
                                ),
                              ),
                            ),
                            if (screenWidth > 360)
                              Text(
                                'Registro: ${_formatDate(user.createdAt)}',
                                style: TextStyle(
                                  fontSize: 10,
                                  color: Colors.grey[600],
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
                    trailing: PopupMenuButton<String>(
                      onSelected: (action) => _handleUserAction(action, user),
                      itemBuilder: (context) => [
                        const PopupMenuItem(
                          value: 'edit',
                          child: Row(
                            children: [
                              Icon(Icons.edit, size: 18),
                              SizedBox(width: 12),
                              Text('Editar'),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'delete',
                          child: Row(
                            children: [
                              Icon(
                                Icons.delete,
                                size: 18,
                                color: Colors.red,
                              ),
                              SizedBox(width: 12),
                              Text(
                                'Eliminar',
                                style: TextStyle(color: Colors.red),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildDocumentsTab() {
    final screenWidth = MediaQuery.of(context).size.width;
    final isTablet = screenWidth >= 600;
    final padding = isTablet ? 24.0 : 16.0;

    // Filtrar documentos para excluir los de Ivan
    final filteredDocuments = _allDocuments.where((document) {
      // Obtener el propietario del documento
      final ownerId = document.uploadedBy;
      
      // Buscar si el propietario es Ivan
      try {
        final owner = _users.firstWhere((u) => u.id == ownerId);
        if (owner.username.toLowerCase() == 'ivan') {
          debugPrint('  ❌ Excluyendo doc ID=${document.id} (pertenece a Ivan)');
          return false;
        }
      } catch (e) {
        // Si no se encuentra el usuario, incluir el documento
      }
      
      return true;
    }).toList();
    
    debugPrint('👤 [ADMIN PANEL - DOCS] Excluyendo documentos de Ivan');
    debugPrint('📁 [ADMIN PANEL - DOCS] Total documentos después de filtrar: ${filteredDocuments.length}');

    return SingleChildScrollView(
      padding: EdgeInsets.all(padding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Documentos de Usuarios',
            style: TextStyle(
              fontSize: isTablet ? 20 : 18,
              fontWeight: FontWeight.bold,
              color: const Color(0xFF2C3E50),
            ),
          ),
          const SizedBox(height: 16),
          if (_isLoadingDocs)
            Container(
              height: 200,
              alignment: Alignment.center,
              child: const CircularProgressIndicator(
                color: Color(0xFF6B4CE6),
              ),
            )
          else if (filteredDocuments.isEmpty)
            Container(
              padding: EdgeInsets.all(32),
              alignment: Alignment.center,
              child: Text(
                'No hay documentos de otros usuarios (excluyendo Ivan)',
                style: TextStyle(
                  color: Colors.grey[600],
                  fontSize: 16,
                ),
              ),
            )
          else
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withAlpha(13),
                    blurRadius: 10,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: filteredDocuments.length,
                separatorBuilder: (context, index) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final document = filteredDocuments[index];
                  return ListTile(
                    leading: Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: _getFileTypeColor(document.mimeType)
                            .withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(
                        _getFileTypeIcon(document.mimeType),
                        color: _getFileTypeColor(document.mimeType),
                        size: 20,
                      ),
                    ),
                    title: Text(document.title),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          document.fileName,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Wrap(
                          spacing: 8,
                          runSpacing: 4,
                          children: [
                            Text(
                              'Propietario: ${_getUsernameById(document.uploadedBy)}',
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.grey[600],
                              ),
                            ),
                            if (document.isShared)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 6,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: const Color(0xFF4CAF50)
                                      .withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: const Text(
                                  'Compartido',
                                  style: TextStyle(
                                    fontSize: 10,
                                    color: Color(0xFF4CAF50),
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
                    trailing: PopupMenuButton<String>(
                      onSelected: (action) =>
                          _handleDocumentAction(action, document),
                      itemBuilder: (context) => [
                        const PopupMenuItem(
                          value: 'view',
                          child: Row(
                            children: [
                              Icon(Icons.visibility, size: 18),
                              SizedBox(width: 12),
                              Text('Ver'),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'delete',
                          child: Row(
                            children: [
                              Icon(Icons.delete, size: 18, color: Colors.red),
                              SizedBox(width: 12),
                              Text(
                                'Eliminar',
                                style: TextStyle(color: Colors.red),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildChatsTab() {
    final screenWidth = MediaQuery.of(context).size.width;
    final isTablet = screenWidth >= 600;
    final padding = isTablet ? 24.0 : 16.0;

    // Filtrar chats para excluir los de Ivan
    final filteredChats = _allChats.where((chat) {
      // Obtener el ID del usuario del chat
      final userId = chat.userId;
      
      // Buscar si el usuario es Ivan
      try {
        final user = _users.firstWhere((u) => u.id == userId);
        if (user.username.toLowerCase() == 'ivan') {
          debugPrint('  ❌ Excluyendo chat ID=${chat.id} (pertenece a Ivan)');
          return false;
        }
      } catch (e) {
        // Si no se encuentra el usuario, incluir el chat
      }
      
      return true;
    }).toList();
    
    debugPrint('👤 [ADMIN PANEL - CHATS] Excluyendo chats de Ivan');
    debugPrint('📁 [ADMIN PANEL - CHATS] Total chats después de filtrar: ${filteredChats.length}');

    return SingleChildScrollView(
      padding: EdgeInsets.all(padding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Chats de Usuarios',
            style: TextStyle(
              fontSize: isTablet ? 20 : 18,
              fontWeight: FontWeight.bold,
              color: const Color(0xFF2C3E50),
            ),
          ),
          const SizedBox(height: 16),
          if (_isLoadingChats)
            Container(
              height: 200,
              alignment: Alignment.center,
              child: const CircularProgressIndicator(
                color: Color(0xFF6B4CE6),
              ),
            )
          else if (filteredChats.isEmpty)
            Container(
              padding: EdgeInsets.all(32),
              alignment: Alignment.center,
              child: Text(
                'No hay chats de otros usuarios (excluyendo Ivan)',
                style: TextStyle(
                  color: Colors.grey[600],
                  fontSize: 16,
                ),
              ),
            )
          else
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withAlpha(13),
                    blurRadius: 10,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: filteredChats.length,
                separatorBuilder: (context, index) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final chat = filteredChats[index];
                  // Obtener usuario de forma segura
                  User? user;
                  try {
                    if (_users.isNotEmpty) {
                      user = _users.firstWhere((u) => u.id == chat.userId);
                    }
                  } catch (e) {
                    user = null;
                  }

                  // Si no se encuentra el usuario, usar valores por defecto
                  final displayUser = user ??
                      User(
                          id: 0,
                          username: 'Usuario desconocido',
                          email: '',
                          role: UserRole.user,
                          createdAt: DateTime.now());

                  return ListTile(
                    leading: const CircleAvatar(
                      backgroundColor: Color(0xFF6B4CE6),
                      child: Icon(Icons.chat, color: Colors.white),
                    ),
                    title: Text(chat.title),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Usuario: ${displayUser.username}'),
                        const SizedBox(height: 4),
                        Text(
                          'Última actividad: ${_formatDateTime(chat.updatedAt)}',
                          style:
                              TextStyle(fontSize: 12, color: Colors.grey[600]),
                        ),
                      ],
                    ),
                    trailing: PopupMenuButton<String>(
                      onSelected: (action) => _handleChatAction(action, chat),
                      itemBuilder: (context) => [
                        const PopupMenuItem(
                          value: 'view',
                          child: Row(
                            children: [
                              Icon(Icons.visibility, size: 18),
                              SizedBox(width: 12),
                              Text('Ver chat'),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }

  IconData _getFileTypeIcon(String mimeType) {
    if (mimeType.contains('pdf')) return Icons.picture_as_pdf;
    if (mimeType.contains('word') || mimeType.contains('document')) {
      return Icons.description;
    }
    if (mimeType.contains('spreadsheet') || mimeType.contains('excel')) {
      return Icons.table_chart;
    }
    if (mimeType.contains('presentation') || mimeType.contains('powerpoint')) {
      return Icons.slideshow;
    }
    return Icons.insert_drive_file;
  }

  Color _getFileTypeColor(String mimeType) {
    if (mimeType.contains('pdf')) {
      return const Color(0xFFD32F2F);
    }
    if (mimeType.contains('word') || mimeType.contains('document')) {
      return const Color(0xFF1976D2);
    }
    if (mimeType.contains('spreadsheet') || mimeType.contains('excel')) {
      return const Color(0xFF388E3C);
    }
    if (mimeType.contains('presentation') || mimeType.contains('powerpoint')) {
      return const Color(0xFFF57C00);
    }
    return const Color(0xFF6B4CE6);
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }

  String _formatDateTime(DateTime? date) {
    if (date == null) {
      return 'Sin fecha';
    }

    final now = DateTime.now();
    final difference = now.difference(date);

    if (difference.inDays == 0) {
      if (difference.inHours == 0) {
        return 'Hace ${difference.inMinutes} minutos';
      }
      return 'Hace ${difference.inHours} horas';
    } else if (difference.inDays == 1) {
      return 'Ayer';
    } else {
      return '${date.day}/${date.month}/${date.year}';
    }
  }

  // Método helper para obtener el nombre de usuario de forma segura
  String _getUsernameById(int userId) {
    if (_users.isEmpty) return 'Desconocido';

    try {
      final user = _users.firstWhere((u) => u.id == userId);
      return user.username;
    } catch (e) {
      return 'Desconocido';
    }
  }

  // Método auxiliar para verificar si un usuario es admin
  bool _isUserAdmin(User user) {
    return user.username.toLowerCase() == 'ivan' || user.role == UserRole.admin;
  }

  // Método auxiliar para verificar si el usuario current es Ivan
  bool _isCurrentUserIvan() {
    final currentUser = AuthService().currentUser;
    return currentUser?.username.toLowerCase() == 'ivan';
  }

  void _handleUserAction(String action, User user) {
    // Verificación adicional: no permitir acciones sobre Ivan
    if (user.username.toLowerCase() == 'ivan') {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'No se pueden realizar acciones sobre el usuario Ivan',
          ),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    switch (action) {
      case 'edit':
        _showEditUserDialog(user);
        break;
      case 'delete':
        // Solo admins pueden eliminar usuarios
        final currentUser = AuthService().currentUser;
        if (currentUser?.isAdmin == true) {
          _showDeleteUserDialog(user);
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content:
                  Text('Solo los administradores pueden eliminar usuarios'),
              backgroundColor: Colors.red,
            ),
          );
        }
        break;
    }
  }

  void _showEditUserDialog(User user) {
    final usernameController = TextEditingController(text: user.username);
    final emailController = TextEditingController(text: user.email);
    final screenWidth = MediaQuery.of(context).size.width;

    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          constraints: BoxConstraints(
            maxWidth: screenWidth > 600 ? 500 : double.infinity,
          ),
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Editar Usuario: ${user.username}',
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: usernameController,
                decoration: const InputDecoration(
                  labelText: 'Nombre de usuario',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: emailController,
                decoration: const InputDecoration(
                  labelText: 'Correo electrónico',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.emailAddress,
              ),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Cancelar'),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () async {
                      await _updateUser(
                        user,
                        usernameController.text,
                        emailController.text,
                      );
                      if (mounted) {
                        Navigator.pop(context);
                      }
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF6B4CE6),
                      foregroundColor: Colors.white,
                    ),
                    child: const Text('Guardar'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _updateUser(
      User user, String newUsername, String newEmail) async {
    try {
      await _userService.updateUser(
        userId: user.id,
        username: newUsername,
        email: newEmail,
      );

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Usuario actualizado exitosamente'),
          backgroundColor: Color(0xFF4CAF50),
        ),
      );

      // Recargar la lista de usuarios
      _loadUsers();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error al actualizar: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _showDeleteUserDialog(User user) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        title: const Text('Eliminar Usuario'),
        content: Text(
          '¿Estás seguro de que quieres eliminar al usuario "${user.username}"? Esta acción no se puede deshacer.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(context);
              await _deleteUser(user);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteUser(User user) async {
    try {
      await _userService.deleteUser(user.id);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Usuario ${user.username} eliminado'),
          backgroundColor: Colors.red,
        ),
      );

      // Recargar la lista de usuarios
      _loadUsers();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error al eliminar: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _handleDocumentAction(String action, Document document) {
    switch (action) {
      case 'view':
        _openDocument(document);
        break;
      case 'delete':
        _showDeleteDocumentDialog(document);
        break;
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
                  _getFileTypeIcon(document.mimeType),
                  color: _getFileTypeColor(document.mimeType),
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
            _buildInfoRow('Tipo:', document.mimeType),
            _buildInfoRow('Subido por:', _getUsernameById(document.uploadedBy)),
            _buildInfoRow('Fecha:', _formatDateTime(document.createdAt)),
            if (document.fileSize != null)
              _buildInfoRow('Tamaño:', _formatFileSize(document.fileSize!)),
            _buildInfoRow('Estado:', _getDocumentStatus(document)),
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
            width: 100,
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

  void _showDeleteDocumentDialog(Document document) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        title: const Text('Eliminar Documento'),
        content: Text(
          '¿Estás seguro de que quieres eliminar "${document.title}"? Esta acción no se puede deshacer.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            onPressed: () {
              _deleteDocument(document);
              Navigator.pop(context);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
  }

  void _deleteDocument(Document document) {
    setState(() {
      _allDocuments.removeWhere((d) => d.id == document.id);
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Documento ${document.title} eliminado'),
        backgroundColor: Colors.red,
      ),
    );
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

  void _handleChatAction(String action, ChatModel chat) {
    switch (action) {
      case 'view':
        // Navegar a la pantalla de chat en modo lectura para administradores
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => ChatScreen(
              existingChat: chat,
              chatId: chat.id,
              chatName: chat.title,
              isAdminView: true, // Añadir este parámetro
            ),
          ),
        );
        break;
    }
  }
}
