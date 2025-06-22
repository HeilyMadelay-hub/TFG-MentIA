import 'package:flutter/material.dart';
import '../models/chat.dart';
import '../services/chat_service.dart';
import 'chat_with_websocket.dart';
import '../utils/responsive_utils.dart';

class ChatListScreen extends StatefulWidget {
  const ChatListScreen({super.key});
  @override
  State<ChatListScreen> createState() => _ChatListScreenState();
}

class _ChatListScreenState extends State<ChatListScreen> {
  final ChatService _chatService = ChatService();
  final TextEditingController _searchController = TextEditingController();
  List<Chat> _chats = [];
  List<Chat> _filteredChats = [];
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadChats();
    _searchController.addListener(_filterChats);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadChats() async {
    // Evitar usar BuildContext después de await sin verificar mounted
    if (!mounted) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      // Cargar chats del usuario actual desde el backend
      debugPrint('🔄 Iniciando carga de chats...');
      final chats = await _chatService.listChats();

      if (!mounted) return;

      setState(() {
        _chats = chats;
        _filteredChats = List.from(_chats);
        _isLoading = false;
      });
      debugPrint('✅ Chats cargados exitosamente: ${_chats.length}');
    } catch (e) {
      if (!mounted) return;

      debugPrint('❌ Error al cargar chats: $e');

      // Manejar error de autenticación de forma específica
      if (e.toString().contains('No autenticado') ||
          e.toString().contains('401') ||
          e.toString().contains('token inválido')) {
        setState(() {
          _errorMessage = 'Sesión expirada. Redirigiendo a login...';
          _isLoading = false;
        });

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Sesión expirada. Redirigiendo a login...'),
              backgroundColor: Colors.orange,
              duration: Duration(seconds: 2),
            ),
          );

          // Redirigir a login después de mostrar el mensaje
          Future.delayed(const Duration(seconds: 2), () {
            if (mounted) {
              Navigator.of(context)
                  .pushNamedAndRemoveUntil('/login', (route) => false);
            }
          });
        }
      } else {
        setState(() {
          _errorMessage = 'Error al cargar conversaciones: ${e.toString()}';
          _isLoading = false;
        });

        // Mostrar snackbar para otros errores
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Error: ${e.toString()}'),
              backgroundColor: Colors.red,
              action: SnackBarAction(
                label: 'Reintentar',
                onPressed: _loadChats,
                textColor: Colors.white,
              ),
            ),
          );
        }
      }
    }
  }

  void _filterChats() {
    final query = _searchController.text.toLowerCase();

    setState(() {
      _filteredChats = _chats.where((chat) {
        final matchesTitle = chat.title.toLowerCase().contains(query);
        final matchesContent = chat.messages.any((message) =>
            message.content.toLowerCase().contains(query));

        return matchesTitle || matchesContent;
      }).toList();
    });
  }

  // SOLUCIÓN 1: Método para navegar a nuevo chat
  Future<void> _navigateToNewChat() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
          builder: (context) => const ChatWithWebSocketScreen())
    );

    // Cuando vuelves de ChatScreen, recarga los chats
    _loadChats();
  }

  // SOLUCIÓN 1: Método para navegar a chat existente
  Future<void> _navigateToExistingChat(Chat chat) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ChatWithWebSocketScreen(existingChat: chat),
      ),
    );

    // Recargar por si hubo cambios en el chat
    _loadChats();
  }

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      builder: (context, sizingInfo) {
        return Scaffold(
          backgroundColor: Colors.grey[50],
          body: Column(
            children: [
              // Header
              _buildHeader(sizingInfo),

              // Barra de búsqueda
              _buildSearchBar(sizingInfo),

              // Lista de chats
              Expanded(
                child: _isLoading
                    ? _buildLoadingState()
                    : _errorMessage != null
                        ? _buildErrorState(sizingInfo)
                        : _filteredChats.isEmpty
                            ? _buildEmptyState(sizingInfo)
                            : _buildChatsList(sizingInfo),
              ),
            ],
          ),
          floatingActionButton: sizingInfo.isMobile
              ? FloatingActionButton(
                  onPressed: _navigateToNewChat,
                  backgroundColor: const Color(0xFF6B4CE6),
                  foregroundColor: Colors.white,
                  child: Icon(Icons.add, size: sizingInfo.fontSize.icon),
                )
              : FloatingActionButton.extended(
                  onPressed: _navigateToNewChat,
                  backgroundColor: const Color(0xFF6B4CE6),
                  foregroundColor: Colors.white,
                  icon: Icon(Icons.add, size: sizingInfo.fontSize.icon),
                  label: Text(
                    'Nuevo Chat',
                    style: TextStyle(fontSize: sizingInfo.fontSize.button),
                  ),
                ),
        );
      },
    );
  }

  Widget _buildHeader(ResponsiveInfo sizingInfo) {
    return Container(
      padding: EdgeInsets.all(sizingInfo.padding),
      decoration: const BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black12,
            blurRadius: 4,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: sizingInfo.isMobile
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Mis Conversaciones',
                            style: TextStyle(
                              fontSize: sizingInfo.fontSize.title,
                              fontWeight: FontWeight.bold,
                              color: const Color(0xFF2C3E50),
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          SizedBox(height: sizingInfo.spacing / 2),
                          Text(
                            '${_filteredChats.length} conversación${_filteredChats.length != 1 ? 'es' : ''}',
                            style: TextStyle(
                              fontSize: sizingInfo.fontSize.caption,
                              color: Colors.grey[600],
                            ),
                          ),
                        ],
                      ),
                    ),
                    Container(
                      padding: EdgeInsets.all(sizingInfo.iconPadding),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF6B4CE6), Color(0xFFE91E63)],
                        ),
                        borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                      ),
                      child: Icon(
                        Icons.chat_bubble,
                        color: Colors.white,
                        size: sizingInfo.fontSize.largeIcon,
                      ),
                    ),
                  ],
                ),
              ],
            )
          : Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Mis Conversaciones',
                        style: TextStyle(
                          fontSize: sizingInfo.fontSize.title,
                          fontWeight: FontWeight.bold,
                          color: const Color(0xFF2C3E50),
                        ),
                      ),
                      SizedBox(height: sizingInfo.spacing / 2),
                      Text(
                        '${_filteredChats.length} conversación${_filteredChats.length != 1 ? 'es' : ''} con MentIA',
                        style: TextStyle(
                          fontSize: sizingInfo.fontSize.body,
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: EdgeInsets.all(sizingInfo.spacing),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF6B4CE6), Color(0xFFE91E63)],
                    ),
                    borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
                  ),
                  child: Icon(
                    Icons.chat_bubble,
                    color: Colors.white,
                    size: sizingInfo.fontSize.largeIcon,
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildSearchBar(ResponsiveInfo sizingInfo) {
    return Container(
      padding: EdgeInsets.all(sizingInfo.cardPadding),
      color: Colors.white,
      child: TextField(
        controller: _searchController,
        style: TextStyle(fontSize: sizingInfo.fontSize.body),
        decoration: InputDecoration(
          hintText: 'Buscar en conversaciones...',
          hintStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
          prefixIcon: Icon(Icons.search, size: sizingInfo.fontSize.icon),
          suffixIcon: _searchController.text.isNotEmpty
              ? IconButton(
                  icon: Icon(Icons.clear, size: sizingInfo.fontSize.icon),
                  onPressed: () {
                    _searchController.clear();
                    _filterChats();
                  },
                )
              : null,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
            borderSide: BorderSide(color: Colors.grey[300]!),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
            borderSide: BorderSide(color: Colors.grey[300]!),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
            borderSide: const BorderSide(color: Color(0xFF6B4CE6), width: 2),
          ),
          filled: true,
          fillColor: Colors.grey[50],
          contentPadding: EdgeInsets.symmetric(
            horizontal: sizingInfo.cardPadding,
            vertical: sizingInfo.spacing,
          ),
        ),
      ),
    );
  }

  Widget _buildLoadingState() {
    return const Center(
      child: CircularProgressIndicator(
        color: Color(0xFF6B4CE6),
      ),
    );
  }

  Widget _buildErrorState(ResponsiveInfo sizingInfo) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(sizingInfo.padding),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: sizingInfo.fontSize.emptyStateIcon,
              color: Colors.red[300],
            ),
            SizedBox(height: sizingInfo.spacing * 2),
            Text(
              'Error al cargar conversaciones',
              style: TextStyle(
                fontSize: sizingInfo.fontSize.subtitle,
                fontWeight: FontWeight.w500,
                color: Colors.red[700],
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: sizingInfo.spacing),
            Text(
              _errorMessage ?? 'Error desconocido',
              style: TextStyle(
                fontSize: sizingInfo.fontSize.body,
                color: Colors.grey[600],
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: sizingInfo.spacing * 3),
            ElevatedButton.icon(
              onPressed: _loadChats,
              icon: Icon(Icons.refresh, size: sizingInfo.fontSize.icon),
              label: Text(
                'Reintentar',
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
                  borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(ResponsiveInfo sizingInfo) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(sizingInfo.padding),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: sizingInfo.fontSize.emptyStateIcon * 2,
              height: sizingInfo.fontSize.emptyStateIcon * 2,
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(sizingInfo.fontSize.emptyStateIcon),
              ),
              child: Icon(
                Icons.chat_bubble_outline,
                size: sizingInfo.fontSize.emptyStateIcon,
                color: Colors.grey[400],
              ),
            ),
            SizedBox(height: sizingInfo.spacing * 3),
            Text(
              _searchController.text.isNotEmpty
                  ? 'No se encontraron conversaciones'
                  : 'No tienes conversaciones aún',
              style: TextStyle(
                fontSize: sizingInfo.fontSize.subtitle,
                fontWeight: FontWeight.w500,
                color: const Color(0xFF2C3E50),
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: sizingInfo.spacing),
            Text(
              _searchController.text.isNotEmpty
                  ? 'Intenta con otros términos de búsqueda'
                  : 'Inicia tu primera conversación con MentIA',
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

  Widget _buildChatsList(ResponsiveInfo sizingInfo) {
    return RefreshIndicator(
      onRefresh: _loadChats,
      color: const Color(0xFF6B4CE6),
      child: ListView.builder(
        padding: EdgeInsets.all(sizingInfo.cardPadding),
        itemCount: _filteredChats.length,
        itemBuilder: (context, index) {
          final chat = _filteredChats[index];
          return _buildChatCard(chat, sizingInfo);
        },
      ),
    );
  }

  Widget _buildChatCard(Chat chat, ResponsiveInfo sizingInfo) {
    final lastMessage = chat.messages.isNotEmpty ? chat.messages.last : null;

    return Card(
      margin: EdgeInsets.only(bottom: sizingInfo.spacing),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
      ),
      child: InkWell(
        onTap: () => _navigateToExistingChat(chat),
        borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
        child: Padding(
          padding: EdgeInsets.all(sizingInfo.cardPadding),
          child: Row(
            children: [
              // Avatar de MentIA responsive
              Container(
                width: sizingInfo.listTileIconSize,
                height: sizingInfo.listTileIconSize,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF6B4CE6), Color(0xFFE91E63)],
                  ),
                  borderRadius: BorderRadius.circular(sizingInfo.listTileIconSize / 2),
                ),
                child: Icon(
                  Icons.smart_toy,
                  color: Colors.white,
                  size: sizingInfo.fontSize.icon,
                ),
              ),

              SizedBox(width: sizingInfo.spacing),

              // Información del chat
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      chat.title,
                      style: TextStyle(
                        fontSize: sizingInfo.fontSize.body,
                        fontWeight: FontWeight.w600,
                        color: const Color(0xFF2C3E50),
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (lastMessage != null && sizingInfo.showDescriptions) ...[
                      SizedBox(height: sizingInfo.spacing / 2),
                      Text(
                        lastMessage.isUser 
                            ? 'Tú: ${lastMessage.content}'
                            : 'MentIA: ${lastMessage.content}',
                        style: TextStyle(
                          fontSize: sizingInfo.fontSize.caption,
                          color: Colors.grey[600],
                          fontWeight: FontWeight.normal,
                        ),
                        maxLines: sizingInfo.isSmallDevice ? 1 : 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ],
                ),
              ),

              // Menú de acciones
              PopupMenuButton<String>(
                onSelected: (action) => _handleChatAction(action, chat),
                itemBuilder: (context) => [
                  PopupMenuItem(
                    value: 'open',
                    child: Row(
                      children: [
                        Icon(Icons.open_in_new, size: sizingInfo.fontSize.icon),
                        SizedBox(width: sizingInfo.spacing),
                        Text('Abrir chat', style: TextStyle(fontSize: sizingInfo.fontSize.body)),
                      ],
                    ),
                  ),
                  PopupMenuItem(
                    value: 'rename',
                    child: Row(
                      children: [
                        Icon(Icons.edit, size: sizingInfo.fontSize.icon),
                        SizedBox(width: sizingInfo.spacing),
                        Text('Renombrar', style: TextStyle(fontSize: sizingInfo.fontSize.body)),
                      ],
                    ),
                  ),
                  PopupMenuItem(
                    value: 'delete',
                    child: Row(
                      children: [
                        Icon(Icons.delete, size: sizingInfo.fontSize.icon, color: Colors.red),
                        SizedBox(width: sizingInfo.spacing),
                        Text('Eliminar', style: TextStyle(color: Colors.red, fontSize: sizingInfo.fontSize.body)),
                      ],
                    ),
                  ),
                ],
                icon: Icon(
                  Icons.more_vert,
                  size: sizingInfo.fontSize.icon,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _handleChatAction(String action, Chat chat) {
    switch (action) {
      case 'open':
        _navigateToExistingChat(chat);
        break;
      case 'rename':
        _showRenameDialog(chat);
        break;
      case 'delete':
        _showDeleteDialog(chat);
        break;
    }
  }

  void _showRenameDialog(Chat chat) {
    final controller = TextEditingController(text: chat.title);
    final sizingInfo = context.responsive;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
        ),
        title: Text(
          'Renombrar Conversación',
          style: TextStyle(fontSize: sizingInfo.fontSize.subtitle),
        ),
        content: TextField(
          controller: controller,
          style: TextStyle(fontSize: sizingInfo.fontSize.body),
          decoration: InputDecoration(
            labelText: 'Nuevo nombre',
            labelStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
            ),
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              'Cancelar',
              style: TextStyle(fontSize: sizingInfo.fontSize.button),
            ),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(context);

              // Verificar mounted antes de usar context
              if (mounted) {
                await _renameChat(chat, controller.text);
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF6B4CE6),
              foregroundColor: Colors.white,
              padding: EdgeInsets.symmetric(
                horizontal: sizingInfo.cardPadding,
                vertical: sizingInfo.spacing,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
              ),
            ),
            child: Text(
              'Guardar',
              style: TextStyle(fontSize: sizingInfo.fontSize.button),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _renameChat(Chat chat, String newTitle) async {
    if (newTitle.isNotEmpty && newTitle != chat.title) {
      try {
        // Llamar al servicio para renombrar en el backend
        await _chatService.renameChat(chat.id, newTitle);

        // Verificar mounted antes de usar context
        if (!mounted) return;

        // Recargar la lista
        await _loadChats();

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Conversación renombrada'),
              backgroundColor: Color(0xFF4CAF50),
            ),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Error al renombrar: ${e.toString()}'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    }
  }

  void _showDeleteDialog(Chat chat) {
    final sizingInfo = context.responsive;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
        ),
        title: Text(
          'Eliminar Conversación',
          style: TextStyle(fontSize: sizingInfo.fontSize.subtitle),
        ),
        content: Text(
          '¿Estás seguro de que quieres eliminar la conversación "${chat.title}"? Esta acción no se puede deshacer.',
          style: TextStyle(fontSize: sizingInfo.fontSize.body),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              'Cancelar',
              style: TextStyle(fontSize: sizingInfo.fontSize.button),
            ),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(context);

              // Verificar mounted antes de usar context
              if (mounted) {
                await _deleteChat(chat);
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
              padding: EdgeInsets.symmetric(
                horizontal: sizingInfo.cardPadding,
                vertical: sizingInfo.spacing,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
              ),
            ),
            child: Text(
              'Eliminar',
              style: TextStyle(fontSize: sizingInfo.fontSize.button),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteChat(Chat chat) async {
    try {
      // Llamar al servicio para eliminar en el backend
      await _chatService.deleteChat(chat.id);

      // Verificar mounted antes de usar context
      if (!mounted) return;

      // Recargar la lista
      await _loadChats();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Conversación "${chat.title}" eliminada'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error al eliminar: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}
