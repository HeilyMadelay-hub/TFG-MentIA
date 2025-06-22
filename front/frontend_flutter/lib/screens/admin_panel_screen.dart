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
import '../services/document_service.dart';
import '../services/user_service.dart';
import '../services/admin_panel_service.dart';
import '../config/api_config.dart';
import 'chat.dart'; // Importar la pantalla de chat
import '../utils/email_validator.dart';
import '../utils/responsive_utils.dart';

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
  final UserService _userService = UserService();
  final DocumentService _documentService = DocumentService();
  
  // Datos reales
  Map<String, int> _statistics = {
    'total_users': 0,
    'total_documents': 0,
    'active_chats': 0,
  };
  List<User> _users = [];
  List<Document> _allDocuments = [];
  List<Chat> _allChats = [];
  
  // Datos del dashboard
  Map<String, dynamic>? _dashboardData;
  List<dynamic> _recentActivities = [];

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

  void _loadAdminData() {
    // Cargar todo desde el nuevo endpoint unificado
    _loadDashboard();
  }
  
  Future<void> _loadDashboard() async {
    if (!mounted) return;
    
    try {
      setState(() {
        _isLoadingStats = true;
        _isLoadingUsers = true;
        _isLoadingDocs = true;
        _isLoadingChats = true;
      });
      
      // Cargar todos los datos del dashboard de una sola vez
      final dashboard = await AdminPanelService.getDashboard();
      
      if (!mounted) return;
      
      setState(() {
        _dashboardData = dashboard;
        
        // Actualizar estadísticas
        if (dashboard['statistics'] != null) {
          _statistics = Map<String, int>.from(dashboard['statistics']);
        }
        
        // Actualizar usuarios
        if (dashboard['users'] != null) {
          _users = (dashboard['users'] as List).map<User>((userData) {
            print('👤 USUARIO DATA: ${json.encode(userData)}');
            return User(
              id: userData['id'],
              username: userData['username'] ?? 'Unknown',
              email: userData['email'] ?? '',
              role: userData['is_admin'] == true ? UserRole.admin : UserRole.user,
              createdAt: AdminPanelService.parseTimestamp(userData['created_at']) ?? DateTime.now(),
            );
          }).toList();
        }
        
        // Actualizar documentos
        if (dashboard['documents'] != null) {
          _allDocuments = (dashboard['documents'] as List).map<Document>((docData) {
            print('📄 DOCUMENTO DATA: ${json.encode(docData)}');
            return Document(
              id: docData['id'],
              title: docData['title'] ?? 'Sin título',
              content: '',
              originalFilename: docData['title'] ?? 'documento',
              fileUrl: docData['file_url'],
              contentType: docData['content_type'] ?? 'application/octet-stream',
              uploadedBy: docData['owner']?['id'] ?? 0,
              createdAt: AdminPanelService.parseTimestamp(docData['created_at']) ?? DateTime.now(),
              status: docData['status'] ?? 'unknown',
              fileSize: docData['file_size'],
              isShared: docData['is_shared'] ?? false,
            );
          }).toList();
        }
        
        // Actualizar chats
        if (dashboard['chats'] != null) {
          _allChats = (dashboard['chats'] as List).map<Chat>((chatData) {
            // DEBUGGING: Ver TODOS los campos que vienen del backend
            print('🔍 CHAT DATA COMPLETO: ${json.encode(chatData)}');
            
            final createdAt = AdminPanelService.parseTimestamp(chatData['created_at']) ?? DateTime.now();
            // Buscar el campo correcto: puede ser updated_at, last_message_at, last_activity, etc.
            final updatedAt = AdminPanelService.parseTimestamp(
              chatData['updated_at'] ?? 
              chatData['last_message_at'] ?? 
              chatData['last_activity'] ?? 
              chatData['created_at']
            ) ?? createdAt;
            
            print('💙 Chat ${chatData['id']}: created_at=${chatData['created_at']}, updated_at=${chatData['updated_at']}, last_message_at=${chatData['last_message_at']}');
            
            return Chat(
              id: chatData['id'],
              title: chatData['title'] ?? 'Chat sin título',
              userId: chatData['owner']?['id']?.toString() ?? '0',
              createdAt: createdAt,
              lastMessageAt: updatedAt,
              messageCount: chatData['message_count'] ?? 0,
            );
          }).toList();
        }
        
        // Actualizar actividades recientes
        if (dashboard['recent_activities'] != null) {
          _recentActivities = dashboard['recent_activities'];
          print('📅 ACTIVIDADES RECIENTES:');
          for (var activity in _recentActivities) {
            if (activity['type'] == 'chat') {
              print('  - Chat: "${activity['title']}" | Tiempo: ${activity['formatted_time']} | ID: ${activity['id']} | chat_id: ${activity['chat_id']}');
            } else if (activity['type'] == 'document') {
              print('  - Documento: "${activity['title']}" | Tiempo: ${activity['formatted_time']} | ID: ${activity['id']} | document_id: ${activity['document_id']}');
            }
          }
        }
        
        _isLoadingStats = false;
        _isLoadingUsers = false;
        _isLoadingDocs = false;
        _isLoadingChats = false;
      });
      
      debugPrint('✅ Dashboard cargado exitosamente');
      debugPrint('📊 Estadísticas: $_statistics');
      debugPrint('👥 Usuarios: ${_users.length}');
      debugPrint('📄 Documentos: ${_allDocuments.length}');
      debugPrint('💬 Chats: ${_allChats.length}');
      
    } catch (e) {
      debugPrint('❌ Error cargando dashboard: $e');
      
      if (!mounted) return;
      
      setState(() {
        _isLoadingStats = false;
        _isLoadingUsers = false;
        _isLoadingDocs = false;
        _isLoadingChats = false;
      });
      
      // Mostrar error al usuario
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error al cargar el panel: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _refreshDashboard() async {
    await _loadDashboard();
  }

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      builder: (context, sizingInfo) {
        return SafeArea(
          child: Scaffold(
            backgroundColor: Colors.grey[50],
            body: Column(
              children: [
                // Header del panel de administración
                _buildAdminHeader(sizingInfo),

                // Tabs adaptables
                Container(
                  color: Colors.white,
                  child: TabBar(
                    controller: _tabController,
                    labelColor: const Color(0xFF6B4CE6),
                    unselectedLabelColor: Colors.grey[600],
                    indicatorColor: const Color(0xFF6B4CE6),
                    isScrollable: !sizingInfo.isDesktop, // Scrollable en móviles y tablets
                    labelStyle: TextStyle(
                      fontSize: sizingInfo.fontSize.body,
                      fontWeight: FontWeight.w500,
                    ),
                    tabs: [
                      Tab(
                        icon: Icon(Icons.dashboard,
                            size: sizingInfo.fontSize.icon),
                        text: sizingInfo.isDesktop
                            ? 'Dashboard'
                            : (sizingInfo.screenSize.width > 360 ? 'Dashboard' : 'Inicio'),
                      ),
                      Tab(
                        icon: Icon(Icons.people,
                            size: sizingInfo.fontSize.icon),
                        text: 'Usuarios',
                      ),
                      Tab(
                        icon: Icon(Icons.folder,
                            size: sizingInfo.fontSize.icon),
                        text: sizingInfo.isDesktop
                            ? 'Documentos'
                            : (sizingInfo.screenSize.width > 360 ? 'Documentos' : 'Docs'),
                      ),
                      Tab(
                        icon: Icon(Icons.chat,
                            size: sizingInfo.fontSize.icon),
                        text: 'Chats',
                      ),
                    ],
                  ),
                ),

                // Contenido de las tabs con contenedor flexible
                Flexible(
                  fit: FlexFit.tight,
                  child: TabBarView(
                    controller: _tabController,
                    physics: const NeverScrollableScrollPhysics(), // Prevenir scroll del TabBarView
                    children: [
                      _buildDashboardTab(sizingInfo),
                      _buildUsersTab(sizingInfo),
                      _buildDocumentsTab(sizingInfo),
                      _buildChatsTab(sizingInfo),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildAdminHeader(ResponsiveInfo sizingInfo) {
    return Container(
      padding: EdgeInsets.all(sizingInfo.padding),
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
                  'Panel de Administración',
                  style: TextStyle(
                    fontSize: sizingInfo.fontSize.title,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                if (sizingInfo.screenSize.width > 360)
                  Text(
                    'Gestiona usuarios, documentos y chats',
                    style: TextStyle(
                      fontSize: sizingInfo.fontSize.body,
                      color: Colors.white.withOpacity(0.8),
                    ),
                  ),
              ],
            ),
          ),
          Container(
            padding: EdgeInsets.all(sizingInfo.spacing),
            decoration: BoxDecoration(
              color: Colors.white.withAlpha(51),
              borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
            ),
            child: Icon(
              Icons.admin_panel_settings,
              color: Colors.white,
              size: sizingInfo.fontSize.icon,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDashboardTab(ResponsiveInfo sizingInfo) {
    return SingleChildScrollView(
      padding: EdgeInsets.only(
        left: sizingInfo.padding,
        right: sizingInfo.padding,
        top: sizingInfo.padding,
        bottom: sizingInfo.padding + 26, // Agregar padding extra para evitar overflow
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Estadísticas principales
          _buildStatsGrid(sizingInfo),

          SizedBox(height: sizingInfo.spacing * 2),

          // Actividad reciente
          _buildRecentActivity(sizingInfo),
          
          // Espacio adicional al final para evitar overflow
          const SizedBox(height: 30),
        ],
      ),
    );
  }

  Widget _buildStatsGrid(ResponsiveInfo sizingInfo) {

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
            fontSize: sizingInfo.fontSize.title,
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
                sizingInfo.isDesktop ? 3 : (sizingInfo.isTablet ? 2 : (sizingInfo.screenSize.width > 360 ? 2 : 1));
            final itemWidth =
                (sizingInfo.screenSize.width - (sizingInfo.padding * 2) - (16 * (crossAxisCount - 1))) /
                    crossAxisCount;

            return SizedBox(
              width: itemWidth,
              child: Container(
                padding: EdgeInsets.all(sizingInfo.cardPadding),
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
                        size: sizingInfo.fontSize.icon,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      stat['value'] as String,
                      style: TextStyle(
                        fontSize: sizingInfo.fontSize.subtitle,
                        fontWeight: FontWeight.bold,
                        color: const Color(0xFF2C3E50),
                      ),
                    ),
                    Text(
                      stat['title'] as String,
                      style: TextStyle(
                        fontSize: sizingInfo.fontSize.caption,
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

  Widget _buildRecentActivity(ResponsiveInfo sizingInfo) {

    // Usar las actividades recientes del dashboard
    final activities = _recentActivities.isEmpty ? 
      [{
        'action': 'Sin actividad reciente',
        'user': 'El sistema está esperando nueva actividad',
        'formatted_time': 'Ahora',
        'type': 'empty',
      }] : 
      _recentActivities;

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
                  fontSize: sizingInfo.fontSize.title,
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
          // Limitar la altura máxima del contenedor para evitar overflow
          constraints: BoxConstraints(
            maxHeight: MediaQuery.of(context).size.height * 0.4, // 40% de la altura de pantalla
          ),
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
            physics: activities.length > 5 ? const AlwaysScrollableScrollPhysics() : const NeverScrollableScrollPhysics(),
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
                        _getActivityIcon(activity['type'] ?? 'unknown'),
                        color: const Color(0xFF6B4CE6),
                        size: 18,
                      ),
                    ),
                    title: Text(
                      activity['action'] ?? 'Actividad',
                      style: TextStyle(fontSize: sizingInfo.fontSize.body),
                    ),
                    subtitle: Text(
                      activity['user'] ?? activity['title'] ?? 'Usuario',
                      style: TextStyle(fontSize: sizingInfo.fontSize.caption),
                    ),
                    trailing: Text(
                      activity['formatted_time'] ?? 'Desconocido',
                      style: TextStyle(color: Colors.grey[600], fontSize: 11),
                    ),
                    onTap: () {
                      // DEBUG: Ver qué contiene cada actividad
                      print('🎯 ACTIVIDAD COMPLETA: ${json.encode(activity)}');
                    },
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

  Widget _buildUsersTab(ResponsiveInfo sizingInfo) {

    // Los usuarios ya vienen filtrados desde el backend (sin el admin actual)

    return SingleChildScrollView(
      padding: EdgeInsets.all(sizingInfo.padding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Gestión de Usuarios',
            style: TextStyle(
              fontSize: sizingInfo.fontSize.title,
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
          else if (_users.isEmpty)
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
                itemCount: _users.length,
                separatorBuilder: (context, index) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final user = _users[index];
                // 🔧 CORRECCIÓN: Buscar por ID en lugar de por índice
                String formattedTime = 'Fecha desconocida';
                
                // Buscar los datos del usuario por ID en el dashboard data del backend
                if (_dashboardData != null && _dashboardData!['users'] != null) {
                  // 🎯 BUSCAR POR ID EN LUGAR DE ÍNDICE
                  final userData = (_dashboardData!['users'] as List).firstWhere(
                    (userData) => userData['id'] == user.id,
                    orElse: () => null,
                  );
                  
                  if (userData != null) {
                    // ✅ USAR EL TIEMPO YA FORMATEADO DEL BACKEND
                    if (userData['formatted_created'] != null && userData['formatted_created'].toString().isNotEmpty) {
                      formattedTime = userData['formatted_created'];
                      print('✅ Usando tiempo del backend para ${user.username} (ID: ${user.id}): $formattedTime');
                    } else {
                      // Fallback: calcular en el frontend solo si no viene del backend
                      formattedTime = _formatDateTime(user.createdAt);
                      print('⚠️ Sin formatted_created del backend para ${user.username}, calculando en frontend: $formattedTime');
                    }
                  } else {
                    // Usuario no encontrado en los datos del backend
                    formattedTime = _formatDateTime(user.createdAt);
                    print('❌ Usuario ${user.username} (ID: ${user.id}) no encontrado en datos del backend');
                  }
                } else {
                  // Fallback: calcular en el frontend
                  formattedTime = _formatDateTime(user.createdAt);
                  print('❌ Sin datos del backend, calculando en frontend para ${user.username}: $formattedTime');
                }
                
                  return ListTile(
                    leading: CircleAvatar(
                      backgroundColor: const Color(0xFF6B4CE6).withOpacity(0.2),
                      child: Icon(
                        Icons.person,
                        color: const Color(0xFF6B4CE6),
                      ),
                    ),
                    title: Text(
                      user.username,
                      style: const TextStyle(
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(user.email),
                        Text(
                          'Cuenta creada: $formattedTime',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ),
                    trailing: PopupMenuButton<String>(
                      icon: const Icon(Icons.more_vert),
                      itemBuilder: (context) => [
                        const PopupMenuItem(
                          value: 'edit',
                          child: Row(
                            children: [
                              Icon(Icons.edit),
                              SizedBox(width: 8),
                              Text('Editar'),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'delete',
                          child: Row(
                            children: [
                              Icon(Icons.delete, color: Colors.red),
                              SizedBox(width: 8),
                              Text('Eliminar'),
                            ],
                          ),
                        ),
                      ],
                      onSelected: (action) => _handleUserAction(action, user),
                    ),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildDocumentsTab(ResponsiveInfo sizingInfo) {

    // Los documentos ya vienen filtrados desde el backend (sin los del admin actual)

    return SingleChildScrollView(
      padding: EdgeInsets.all(sizingInfo.padding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Documentos de Usuarios',
            style: TextStyle(
              fontSize: sizingInfo.fontSize.title,
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
          else if (_allDocuments.isEmpty)
            Container(
              padding: EdgeInsets.all(32),
              alignment: Alignment.center,
              child: Text(
                'No hay documentos de otros usuarios',
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
                itemCount: _allDocuments.length,
                separatorBuilder: (context, index) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final document = _allDocuments[index];
                  String uploadTime = 'Sin fecha';
                  String username = 'Usuario desconocido';
                  
                  print('\n🔍 === PROCESANDO DOCUMENTO $index: "${document.title}" ===');
                  
                  // Obtener información del documento del dashboard
                  if (_dashboardData != null && _dashboardData!['documents'] != null && 
                      index < _dashboardData!['documents'].length) {
                    final docData = _dashboardData!['documents'][index];
                    username = docData['owner']?['username'] ?? 'Usuario desconocido';
                    
                    // Usar el tiempo formateado del backend si está disponible
                    if (docData['formatted_created'] != null) {
                      uploadTime = docData['formatted_created'];
                      print('✅ Usando formatted_created del backend: $uploadTime');
                    } else {
                      // Buscar en actividades recientes
                      final matchingActivity = _recentActivities.firstWhere(
                        (act) => act['type'] == 'document' && 
                                (act['title'] == document.title || 
                                 (act['document_id'] != null && act['document_id'] == document.id)),
                        orElse: () => {},
                      );
                      
                      if (matchingActivity.isNotEmpty && matchingActivity['formatted_time'] != null) {
                        uploadTime = matchingActivity['formatted_time'];
                        print('🎯 Encontrada actividad reciente para "${document.title}": $uploadTime');
                      } else if (matchingActivity.isNotEmpty && matchingActivity['timestamp'] != null) {
                        uploadTime = AdminPanelService.formatRelativeTime(matchingActivity['timestamp']);
                        print('🕒 Formateando timestamp de actividad: $uploadTime');
                      } else {
                        // Fallback: usar created_at del documento
                        uploadTime = _formatDateTime(document.createdAt);
                        print('⚠️ Sin actividad reciente, usando created_at: ${document.createdAt} -> $uploadTime');
                      }
                    }
                  } else {
                    uploadTime = _formatDateTime(document.createdAt);
                    print('❌ No hay datos del dashboard para este documento');
                  }
                  
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
                        Text(username, style: TextStyle(fontSize: 12)),
                        Text(
                          uploadTime,
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ),
                    trailing: PopupMenuButton<String>(
                      onSelected: (action) => _handleDocumentAction(action, document),
                      itemBuilder: (context) => [
                        const PopupMenuItem(
                          value: 'view',
                          child: Row(
                            children: [
                              Icon(Icons.visibility, size: 18),
                              SizedBox(width: 12),
                              Text('Ver documento'),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'delete',
                          child: Row(
                            children: [
                              Icon(Icons.delete, color: Colors.red, size: 18),
                              SizedBox(width: 12),
                              Text('Eliminar'),
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

  Widget _buildChatsTab(ResponsiveInfo sizingInfo) {

    // Los chats ya vienen filtrados desde el backend (sin los del admin actual)

    return SingleChildScrollView(
      padding: EdgeInsets.all(sizingInfo.padding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Chats de Usuarios',
            style: TextStyle(
              fontSize: sizingInfo.fontSize.title,
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
          else if (_allChats.isEmpty)
            Container(
              padding: EdgeInsets.all(32),
              alignment: Alignment.center,
              child: Text(
                'No hay chats de otros usuarios',
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
                itemCount: _allChats.length,
                separatorBuilder: (context, index) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  print('\n🔍 === PROCESANDO CHAT $index ===');
                  final chat = _allChats[index];
                  
                  // Obtener el nombre del usuario desde el dashboard data
                  String username = 'Usuario desconocido';
                  String lastActivity = 'Sin actividad reciente';
                  
                  if (_dashboardData != null && _dashboardData!['chats'] != null && 
                      index < _dashboardData!['chats'].length) {
                    username = _dashboardData!['chats'][index]['owner']?['username'] ?? 'Usuario desconocido';
                  }
                  
                  // SOLUCIÓN TEMPORAL: El backend no envía updated_at correctamente
                  // Buscar información adicional del chat en el dashboard
                  if (_dashboardData != null && _dashboardData!['chats'] != null && 
                      index < _dashboardData!['chats'].length) {
                    final chatData = _dashboardData!['chats'][index];
                    
                    // Intentar obtener el timestamp de la última actividad
                    final lastMessageTime = chatData['last_message_at'] ?? 
                                          chatData['last_activity'] ?? 
                                          chatData['updated_at'];
                    
                    if (lastMessageTime != null) {
                      // Si tenemos un timestamp de última actividad, usarlo
                      lastActivity = AdminPanelService.formatRelativeTime(lastMessageTime);
                      print('✅ Chat "${chat.title}" usando last_message_at: $lastMessageTime -> $lastActivity');
                    } else {
                      // Si no, buscar en actividades recientes
                      // Primero intentar por ID (más confiable)
                      var matchingActivity = _recentActivities.firstWhere(
                        (act) => act['type'] == 'chat' && 
                                (act['chat_id'] == chat.id || act['id'] == chat.id),
                        orElse: () => {},
                      );
                      
                      // Si no encontramos por ID, buscar por título exacto
                      if (matchingActivity.isEmpty) {
                        matchingActivity = _recentActivities.firstWhere(
                          (act) => act['type'] == 'chat' && act['title'] == chat.title,
                          orElse: () => {},
                        );
                      }
                      
                      // Último intento: buscar por coincidencia parcial de título
                      if (matchingActivity.isEmpty) {
                        matchingActivity = _recentActivities.firstWhere(
                          (act) => act['type'] == 'chat' && 
                                  act['title'] != null &&
                                  (act['title'].contains(chat.title) || chat.title.contains(act['title'])),
                          orElse: () => {},
                        );
                      }
                      
                      if (matchingActivity.isNotEmpty) {
                        // Preferir formatted_time del backend, sino formatear el timestamp
                        if (matchingActivity['formatted_time'] != null) {
                          lastActivity = matchingActivity['formatted_time'];
                          print('🎯 Encontrada actividad con tiempo formateado para "${chat.title}": $lastActivity');
                        } else if (matchingActivity['timestamp'] != null) {
                          // Si hay timestamp pero no formatted_time, formatearlo nosotros
                          lastActivity = AdminPanelService.formatRelativeTime(matchingActivity['timestamp']);
                          print('🕒 Formateando timestamp de actividad para "${chat.title}": ${matchingActivity['timestamp']} -> $lastActivity');
                        } else {
                          // Sin datos de tiempo en la actividad
                          lastActivity = _formatDateTime(chat.createdAt);
                          print('⚠️ Actividad sin timestamp para "${chat.title}"');
                        }
                      } else {
                        // Fallback: usar created_at
                        lastActivity = _formatDateTime(chat.createdAt);
                        print('⚠️ Sin actividad reciente para "${chat.title}", usando created_at');
                      }
                    }
                  } else {
                    lastActivity = _formatDateTime(chat.createdAt);
                  }
                  
                  return ListTile(
                    leading: const CircleAvatar(
                      backgroundColor: Color(0xFF6B4CE6),
                      child: Icon(Icons.chat, color: Colors.white),
                    ),
                    title: Text(chat.title),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Usuario: $username'),
                        const SizedBox(height: 4),
                        Text(
                          'Última actividad: $lastActivity',
                          style: TextStyle(
                            fontSize: 12, 
                            color: Colors.grey[600]
                          ),
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
    
    try {
      // NO convertir a UTC aquí, dejar que formatRelativeTime maneje la conversión
      return AdminPanelService.formatRelativeTime(date.toIso8601String());
    } catch (e) {
      print('❌ Error formateando fecha: $e');
      // Fallback: mostrar fecha simple
      return '${date.day}/${date.month}/${date.year}';
    }
  }
  
  IconData _getActivityIcon(String type) {
    switch (type) {
      case 'document':
        return Icons.upload_file;
      case 'chat':
        return Icons.chat;
      case 'user':
        return Icons.person_add;
      case 'empty':
        return Icons.hourglass_empty;
      default:
        return Icons.notifications;
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

    showDialog(
      context: context,
      builder: (context) => ResponsiveBuilder(
        builder: (context, sizingInfo) => Dialog(
          child: Container(
            constraints: BoxConstraints(
              maxWidth: sizingInfo.isTablet ? 500 : double.infinity,
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
                      // Validar formato de email
                      if (!EmailValidator.isValidFormat(emailController.text)) {
                        showDialog(
                          context: context,
                          builder: (BuildContext context) {
                            return AlertDialog(
                              title: Text('Error de Validación'),
                              content: Text(
                                  'El email ingresado no tiene un formato válido. Por favor, verifique e intente nuevamente.'),
                              actions: [
                                TextButton(
                                  onPressed: () {
                                    Navigator.of(context).pop();
                                  },
                                  child: Text('Aceptar'),
                                ),
                              ],
                            );
                          },
                        );
                        return;
                      }

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

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Usuario actualizado exitosamente'),
          backgroundColor: Color(0xFF4CAF50),
        ),
      );

      // Recargar el dashboard completo
      _refreshDashboard();
    } catch (e) {
      if (!mounted) return;

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

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Usuario ${user.username} eliminado'),
          backgroundColor: Colors.red,
        ),
      );

      // Recargar el dashboard completo
      _refreshDashboard();
    } catch (e) {
      if (!mounted) return;

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
            if (document.fileUrl != null && document.fileUrl!.isNotEmpty) ...[
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
            ] else ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.orange.shade200),
                ),
                child: Row(
                  children: [
                    Icon(Icons.warning,
                        color: Colors.orange.shade700, size: 20),
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
    if (bytes < 1024 * 1024 * 1024)
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
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

  void _deleteDocument(Document document) async {
    try {
      // Llamar al servicio para eliminar el documento del backend
      await _documentService.deleteDocument(document.id);

      if (!mounted) return;

      setState(() {
        _allDocuments.removeWhere((d) => d.id == document.id);
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Documento ${document.title} eliminado'),
          backgroundColor: Colors.red,
        ),
      );

      // Recargar el dashboard completo
      _refreshDashboard();
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error al eliminar documento: ${e.toString()}'),
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
      return document.statusMessage ??
          'Ocurrió un error al procesar el documento';
    } else if (document.status == 'pending') {
      return 'El documento está en cola para ser procesado';
    } else if (document.fileUrl == null || document.fileUrl!.isEmpty) {
      return 'Este documento no tiene un archivo asociado (solo contenido de texto)';
    }
    return 'El archivo no está disponible para visualización';
  }

  void _handleChatAction(String action, Chat chat) {
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
