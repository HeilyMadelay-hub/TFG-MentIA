import 'package:flutter/material.dart';
import '../models/chat.dart';
import '../models/document.dart';
import '../models/user.dart';
import '../services/chat_service.dart';
import '../services/document_service.dart';
import '../services/auth_service.dart';

class ChatScreen extends StatefulWidget {
  final Chat? existingChat;
  final List<Document>? selectedDocuments;
  final int? chatId;
  final String? chatName;
  final bool isAdminView;

  const ChatScreen({
    super.key,
    this.existingChat,
    this.selectedDocuments,
    this.chatId,
    this.chatName,
    this.isAdminView = false, // Por defecto false
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final ChatService _chatService = ChatService();
  final DocumentService _documentService = DocumentService();
  final AuthService _authService = AuthService();

  List<Map<String, dynamic>> _messages = [];
  Chat? _currentChat;
  bool _isLoading = false;
  bool _isSending = false;
  List<Document> _availableDocuments = [];
  List<Document> _ownDocuments = [];
  List<Document> _sharedDocuments = [];
  int? _selectedDocumentId; // Solo un documento a la vez
  bool _showDocumentSelector = false;
  User? _currentUser;
  bool _isLoadingDocuments = true; // Nuevo: estado de carga de documentos

  @override
  void initState() {
    super.initState();
    _currentUser = _authService.currentUser;
    _initializeChat();
    _loadDocuments();
  }

  Future<void> _initializeChat() async {
    if (widget.existingChat != null) {
      setState(() {
        _currentChat = widget.existingChat;
      });
      await _loadMessages();
    } else if (widget.chatId != null) {
      // Si viene con un chatId específico, cargar ese chat
      try {
        final chat = await _chatService.getChat(widget.chatId!);
        setState(() {
          _currentChat = chat;
        });
        await _loadMessages();
      } catch (e) {
        _showError('Error al cargar chat: ${e.toString()}');
      }
    } else {
      await _createNewChat();
    }
  }

  Future<void> _createNewChat() async {
    try {
      final chatName = widget.chatName ??
          'Nueva conversación - ${DateTime.now().toString().substring(0, 16)}';

      final chat = await _chatService.createChat(name: chatName);
      setState(() {
        _currentChat = chat;
      });
    } catch (e) {
      _showError('Error al crear chat: ${e.toString()}');
    }
  }

  Future<void> _loadDocuments() async {
    setState(() {
      _isLoadingDocuments = true;
    });

    try {
      debugPrint('🔄 Cargando documentos en chat...');
      debugPrint(
          '📝 Usuario actual: ${_currentUser?.username} (ID: ${_currentUser?.id})');
      debugPrint('👤 Es admin: ${_currentUser?.isAdmin}');

      // Cargar documentos propios
      final myDocs = await _documentService.listDocuments();
      debugPrint('📁 Documentos propios cargados: ${myDocs.length}');
      for (var doc in myDocs) {
        debugPrint(
            '  - ${doc.title} (ID: ${doc.id}, Owner: ${doc.uploadedBy})');
      }

      List<Document> sharedDocs = [];
      // Solo cargar documentos compartidos si NO es admin
      if (!(_currentUser?.isAdmin ?? false)) {
        sharedDocs = await _documentService.getSharedWithMe();
        debugPrint('📁 Documentos compartidos cargados: ${sharedDocs.length}');
      }

      setState(() {
        _ownDocuments = myDocs;
        _sharedDocuments = sharedDocs;
        _availableDocuments = [...myDocs, ...sharedDocs];
        _isLoadingDocuments = false;

        // Si había documentos seleccionados inicialmente, tomar solo el primero
        if (widget.selectedDocuments != null &&
            widget.selectedDocuments!.isNotEmpty) {
          _selectedDocumentId = widget.selectedDocuments!.first.id;
        }
      });

      debugPrint(
          '✅ Total documentos disponibles: ${_availableDocuments.length}');
      debugPrint('🔍 ¿Debe mostrar mensaje?: ${_shouldShowNoDocumentsMessage}');
    } catch (e) {
      debugPrint('❌ Error cargando documentos: $e');
      setState(() {
        _ownDocuments = [];
        _sharedDocuments = [];
        _availableDocuments = [];
        _isLoadingDocuments = false;
      });
    }
  }

  // Determinar si debe mostrar el mensaje de "no tienes documentos"
  bool get _shouldShowNoDocumentsMessage {
    // No mostrar el mensaje si aún se están cargando los documentos
    if (_isLoadingDocuments) return false;

    if (_currentUser == null) return false;

    if (_currentUser!.isAdmin) {
      // Para admin: mostrar mensaje si NO tiene documentos propios
      debugPrint(
          '📊 Admin check: documentos propios = ${_ownDocuments.length}');
      return _ownDocuments.isEmpty;
    } else {
      // Para usuarios: mostrar mensaje si NO tiene documentos propios NI compartidos
      debugPrint(
          '📊 Usuario check: propios = ${_ownDocuments.length}, compartidos = ${_sharedDocuments.length}');
      return _ownDocuments.isEmpty && _sharedDocuments.isEmpty;
    }
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadMessages() async {
    if (_currentChat == null) return;

    setState(() {
      _isLoading = true;
    });

    try {
      final messages =
          await _chatService.listMessages(chatId: _currentChat!.id);
      setState(() {
        _messages = [];
        // Convertir cada mensaje en dos entradas: pregunta y respuesta
        for (var msg in messages) {
          final question = msg['question'];
          final answer = msg['answer'];
          final timestamp = msg['created_at'];

          // Agregar la pregunta del usuario si existe
          if (question != null && question.toString().trim().isNotEmpty) {
            _messages.add({
              'type': 'user',
              'question': question,
              'timestamp': timestamp,
            });
          }

          // Agregar la respuesta del bot si existe
          if (answer != null && answer.toString().trim().isNotEmpty) {
            _messages.add({
              'type': 'bot',
              'answer': answer,
              'timestamp': timestamp,
            });
          }
        }
        _isLoading = false;
      });
      _scrollToBottom();
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
      _showError('Error al cargar mensajes: ${e.toString()}');
    }
  }

  Future<void> _sendMessage() async {
    if (_messageController.text.trim().isEmpty ||
        _isSending ||
        _currentChat == null) {
      return;
    }

    final message = _messageController.text.trim();
    _messageController.clear();

    // Agregar mensaje del usuario a la lista
    setState(() {
      _isSending = true;
      _messages.add({
        'type': 'user',
        'question': message,
        'timestamp': DateTime.now().toIso8601String(),
      });
    });
    _scrollToBottom();

    try {
      // Enviar mensaje usando el endpoint unificado
      final response = await _chatService.sendMessage(
        chatId: _currentChat!.id,
        message: message,
        documentIds:
            _selectedDocumentId != null ? [_selectedDocumentId!] : null,
        nResults: 5,
      );

      // Agregar respuesta del bot
      setState(() {
        final answer = response.answer;
        // Solo agregar la respuesta si existe y no está vacía
        if (answer.trim().isNotEmpty) {
          _messages.add({
            'type': 'bot',
            'answer': answer.trim(),
            'timestamp': response.createdAt?.toIso8601String() ??
                DateTime.now().toIso8601String(),
          });
        }
        _isSending = false;
      });
      _scrollToBottom();
    } catch (e) {
      setState(() {
        _isSending = false;
        _messages.add({
          'type': 'bot',
          'answer': 'Error: ${e.toString()}',
          'timestamp': DateTime.now().toIso8601String(),
          'isError': true,
        });
      });
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  void _toggleDocumentSelector() {
    setState(() {
      _showDocumentSelector = !_showDocumentSelector;
    });
  }

  Widget _buildMessageBubble(Map<String, dynamic> message) {
    final isUser = message['type'] == 'user';

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isUser
              ? const Color(0xFFE91E63)
              : message['isError'] == true
                  ? Colors.red.withValues(alpha: 0.1)
                  : Colors.white,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.1),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              isUser ? (message['question'] ?? '') : (message['answer'] ?? ''),
              style: TextStyle(
                color: isUser
                    ? Colors.white
                    : message['isError'] == true
                        ? Colors.red
                        : const Color(0xFF2C3E50),
              ),
            ),
            if (message['context'] != null && message['context'].isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Basado en: ${message['context'].length} fragmento(s)',
                  style: TextStyle(
                    fontSize: 11,
                    color: Colors.grey[600],
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.isAdminView 
            ? 'Vista Admin: ${_currentChat?.title ?? "Chat"}'
            : (_currentChat?.title ?? 'Chat con Documentos')
        ),
        backgroundColor: const Color(0xFFE91E63),
        actions: [
          // Botón para ver información del documento en modo admin
          if (widget.isAdminView)
            IconButton(
              icon: const Icon(Icons.info_outline),
              onPressed: () => _showChatInfo(),
              tooltip: 'Información del chat',
            ),
          // Botón para seleccionar documentos
          IconButton(
            icon: Badge(
              label: Text(_selectedDocumentId != null ? '1' : '0'),
              isLabelVisible: _selectedDocumentId != null,
              child: _isLoadingDocuments
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Icon(Icons.folder),
            ),
            onPressed: _availableDocuments.isNotEmpty && !_isLoadingDocuments && !widget.isAdminView
                ? _toggleDocumentSelector
                : null,
          ),
          // Indicador de documentos accesibles
          Container(
            margin: const EdgeInsets.only(right: 16),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              children: [
                if (_isLoadingDocuments)
                  const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                else
                  const Icon(Icons.folder, size: 16),
                const SizedBox(width: 4),
                Text(
                  _isLoadingDocuments
                      ? 'Cargando...'
                      : '${_availableDocuments.length} docs',
                  style: const TextStyle(fontSize: 14),
                ),
              ],
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // Banner informativo si no hay documentos (según lógica de usuario)
          // NO mostrar si es vista de administrador
          if (!widget.isAdminView && _shouldShowNoDocumentsMessage)
            Container(
              padding: const EdgeInsets.all(16),
              color: Colors.orange.shade100,
              child: Row(
                children: [
                  Icon(Icons.warning, color: Colors.orange.shade700),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'No tienes documentos disponibles. Sube o solicita acceso a documentos para hacer preguntas.',
                      style: TextStyle(color: Colors.orange.shade700),
                    ),
                  ),
                ],
              ),
            ),

          // Selector de documentos (no mostrar en vista admin)
          if (_showDocumentSelector && !widget.isAdminView)
            Container(
              constraints: const BoxConstraints(
                  maxHeight: 150), // Limitar altura para evitar overflow
              decoration: BoxDecoration(
                color: Colors.grey[100],
                border: Border(
                  bottom: BorderSide(color: Colors.grey[300]!),
                ),
              ),
              child: _availableDocuments.isEmpty
                  ? const Center(
                      child: Padding(
                        padding: EdgeInsets.all(16),
                        child: Text('No hay documentos disponibles'),
                      ),
                    )
                  : SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: _availableDocuments.map((doc) {
                          final isSelected = _selectedDocumentId == doc.id;

                          return GestureDetector(
                            onTap: () {
                              setState(() {
                                // Toggle: si está seleccionado, deseleccionar; si no, seleccionar
                                _selectedDocumentId =
                                    isSelected ? null : doc.id;
                              });
                            },
                            child: Container(
                              width: 150,
                              margin: const EdgeInsets.only(right: 12),
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: isSelected
                                    ? const Color(0xFFE91E63)
                                        .withValues(alpha: 0.1)
                                    : Colors.white,
                                border: Border.all(
                                  color: isSelected
                                      ? const Color(0xFFE91E63)
                                      : Colors.grey[300]!,
                                  width: isSelected ? 2 : 1,
                                ),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    _getDocumentIcon(doc.contentType),
                                    color: isSelected
                                        ? const Color(0xFFE91E63)
                                        : Colors.grey[600],
                                    size: 22, // Reducido de 24
                                  ),
                                  const SizedBox(height: 6), // Reducido de 8
                                  Flexible(
                                    child: Text(
                                      doc.title,
                                      style: TextStyle(
                                        fontSize: 11, // Reducido de 12
                                        fontWeight: isSelected
                                            ? FontWeight.bold
                                            : FontWeight.normal,
                                        color: isSelected
                                            ? const Color(0xFFE91E63)
                                            : Colors.grey[800],
                                      ),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  if (doc.isShared &&
                                      !(_currentUser?.isAdmin ?? false)) ...[
                                    const SizedBox(height: 2), // Reducido de 4
                                    Text(
                                      'Compartido',
                                      style: TextStyle(
                                        fontSize: 9, // Reducido de 10
                                        color: Colors.blue[600],
                                        fontStyle: FontStyle.italic,
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                    ),
            ),

          // Lista de mensajes
          Expanded(
            child: _messages.isEmpty && !_isLoading
                ? _buildEmptyState()
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      return _buildMessageBubble(_messages[index]);
                    },
                  ),
          ),

          // Input de mensaje
          _buildMessageInput(),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFFE91E63), Color(0xFFFF69B4)],
                ),
                borderRadius: BorderRadius.circular(50),
              ),
              child: const Icon(
                Icons.chat_bubble_outline,
                color: Colors.white,
                size: 50,
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              '¡Hola! Soy MentIA, tu asistente inteligente',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Color(0xFF2C3E50),
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              _selectedDocumentId == null
                  ? 'Puedo ayudarte con cualquier pregunta o buscar información en tus documentos'
                  : 'Responderé basándome en el documento seleccionado',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[600],
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            Wrap(
              alignment: WrapAlignment.center,
              spacing: 8,
              runSpacing: 8,
              children: [
                _buildSuggestionChip('Dime qué documentos tengo'),
                _buildSuggestionChip('Resume mi documento'),
                _buildSuggestionChip('Busca información sobre...'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSuggestionChip(String text) {
    return ActionChip(
      label: Text(text),
      onPressed: () {
        _messageController.text = text;
      },
      backgroundColor: Colors.white,
      side: BorderSide(
        color: const Color(0xFFE91E63).withValues(alpha: 0.3),
      ),
    );
  }

  Widget _buildMessageInput() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.1),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _messageController,
              enabled: !_isSending && !widget.isAdminView,
              decoration: InputDecoration(
                hintText: widget.isAdminView
                    ? 'Vista de solo lectura (Administrador)'
                    : _selectedDocumentId != null
                        ? 'Pregunta sobre el documento seleccionado...'
                        : 'Escribe un mensaje...',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                filled: true,
                fillColor: const Color(0xFFFFC0CB).withValues(alpha: 0.2),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 12,
                ),
              ),
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
          const SizedBox(width: 12),
          CircleAvatar(
            backgroundColor: const Color(0xFFE91E63),
            child: IconButton(
              icon: _isSending
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Icon(Icons.send, color: Colors.white),
              onPressed: (_isSending || widget.isAdminView) ? null : _sendMessage,
            ),
          ),
        ],
      ),
    );
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

  void _showChatInfo() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Información del Chat'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Chat: ${_currentChat?.title ?? "Sin título"}',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text('ID del Chat: ${_currentChat?.id ?? "N/A"}'),
              const SizedBox(height: 8),
              Text('Usuario ID: ${_currentChat?.userId ?? "N/A"}'),
              const SizedBox(height: 8),
              Text(
                'Creado: ${_currentChat?.createdAt != null ? _formatDateTime(_currentChat!.createdAt) : "N/A"}',
              ),
              const SizedBox(height: 8),
              Text(
                'Última actualización: ${_currentChat?.lastMessageAt != null ? _formatDateTime(_currentChat!.lastMessageAt) : "N/A"}',
              ),
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 8),
              const Text(
                'Documentos en este chat:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              if (_isLoadingDocuments)
                const Center(
                  child: CircularProgressIndicator(),
                )
              else if (_availableDocuments.isEmpty)
                const Text(
                  'No hay documentos asociados',
                  style: TextStyle(fontStyle: FontStyle.italic),
                )
              else
                ..._availableDocuments.map((doc) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Icon(
                            _getDocumentIcon(doc.contentType),
                            size: 20,
                            color: Colors.grey[600],
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  doc.title,
                                  style: const TextStyle(fontSize: 14),
                                ),
                                Text(
                                  'Archivo: ${doc.fileName}',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: Colors.grey[600],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    )).toList(),
              const SizedBox(height: 16),
              const Text(
                'Nota: Esta es una vista de solo lectura para administradores.',
                style: TextStyle(
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                  color: Colors.grey,
                ),
              ),
            ],
          ),
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

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}
