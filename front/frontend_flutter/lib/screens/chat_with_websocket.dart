import 'package:flutter/material.dart';
import 'dart:async';
import '../models/chat.dart';
import '../models/document.dart';
import '../models/user.dart';
import '../models/message.dart';
import '../models/websocket_state.dart';
import '../services/chat_service.dart';
import '../services/document_service.dart';
import '../services/auth_service.dart';
import '../services/chat_websocket_service.dart';
import '../models/chat_websocket_message.dart';
import '../utils/responsive_utils.dart';

class ChatWithWebSocketScreen extends StatefulWidget {
  final Chat? existingChat;
  final List<Document>? selectedDocuments;
  final int? chatId;
  final String? chatName;
  final bool isAdminView;

  const ChatWithWebSocketScreen({
    super.key,
    this.existingChat,
    this.selectedDocuments,
    this.chatId,
    this.chatName,
    this.isAdminView = false,
  });

  @override
  State<ChatWithWebSocketScreen> createState() => _ChatWithWebSocketScreenState();
}

class _ChatWithWebSocketScreenState extends State<ChatWithWebSocketScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final ChatService _chatService = ChatService();
  final DocumentService _documentService = DocumentService();
  final AuthService _authService = AuthService();
  
  // WebSocket
  late ChatWebSocketService _wsService;
  StreamSubscription<Message>? _messageSubscription;
  StreamSubscription<bool>? _connectionSubscription;
  
  List<Map<String, dynamic>> _messages = [];
  Chat? _currentChat;
  bool _isLoading = false;
  bool _isSending = false;
  List<Document> _availableDocuments = [];
  List<Document> _ownDocuments = [];
  List<Document> _sharedDocuments = [];
  int? _selectedDocumentId;
  bool _showDocumentSelector = false;
  User? _currentUser;
  bool _isLoadingDocuments = true;
  bool _shouldHighlightDocumentButton = false;
  
  // Estados WebSocket
  bool _isStreaming = false;
  String _streamingContent = '';
  WebSocketConnectionState _connectionState = WebSocketConnectionState.disconnected;

  @override
  void initState() {
    super.initState();
    _currentUser = _authService.currentUser;
    _wsService = ChatWebSocketService();
    _initializeChat();
    _loadDocuments();
  }

  Future<void> _initializeChat() async {
    if (widget.existingChat != null) {
      setState(() {
        _currentChat = widget.existingChat;
      });
      await _loadMessages();
      await _initializeWebSocket();
    } else if (widget.chatId != null) {
      try {
        final chat = await _chatService.getChat(widget.chatId!);
        setState(() {
          _currentChat = chat;
        });
        await _loadMessages();
        await _initializeWebSocket();
      } catch (e) {
        _showError('Error al cargar chat: ${e.toString()}');
      }
    } else {
      await _createNewChat();
    }
  }

  Future<void> _initializeWebSocket() async {
    if (_currentChat != null && _authService.currentUser != null) {
      try {
        // Conectar WebSocket
        await _wsService.connect(_currentChat!.id);
        
        // Escuchar mensajes
        _messageSubscription = _wsService.messages.listen(_handleWebSocketMessage);
        
        // Escuchar estado de conexión
        _connectionSubscription = _wsService.connectionState.listen((connected) {
          setState(() {
            _connectionState = connected 
                ? WebSocketConnectionState.connected 
                : WebSocketConnectionState.disconnected;
          });
        });
      } catch (e) {
        debugPrint('Error inicializando WebSocket: $e');
      }
    }
  }

  void _handleWebSocketMessage(Message message) {
    setState(() {
      // Agregar el mensaje a la lista
      _messages.add({
        'type': 'bot',
        'answer': message.content ?? '',
        'timestamp': message.timestamp?.toIso8601String() ?? DateTime.now().toIso8601String(),
      });
    });
    _scrollToBottom();
  }

  Future<void> _createNewChat() async {
    try {
      final chatName = widget.chatName ??
          'Nueva conversación - ${DateTime.now().toString().substring(0, 16)}';

      final chat = await _chatService.createChat(name: chatName);
      setState(() {
        _currentChat = chat;
      });
      await _initializeWebSocket();
    } catch (e) {
      _showError('Error al crear chat: ${e.toString()}');
    }
  }

  Future<void> _loadDocuments() async {
    setState(() {
      _isLoadingDocuments = true;
    });

    try {
      final myDocs = await _documentService.listDocuments();
      
      List<Document> sharedDocs = [];
      if (!(_currentUser?.isAdmin ?? false)) {
        sharedDocs = await _documentService.getSharedWithMe();
      }

      setState(() {
        _ownDocuments = myDocs;
        _sharedDocuments = sharedDocs;
        _availableDocuments = [...myDocs, ...sharedDocs];
        _isLoadingDocuments = false;

        if (widget.selectedDocuments != null &&
            widget.selectedDocuments!.isNotEmpty) {
          _selectedDocumentId = widget.selectedDocuments!.first.id;
        }
      });
    } catch (e) {
      debugPrint('Error cargando documentos: $e');
      setState(() {
        _ownDocuments = [];
        _sharedDocuments = [];
        _availableDocuments = [];
        _isLoadingDocuments = false;
      });
    }
  }

  bool get _shouldShowNoDocumentsMessage {
    if (_isLoadingDocuments) return false;
    if (_currentUser == null) return false;

    if (_currentUser!.isAdmin) {
      return _ownDocuments.isEmpty;
    } else {
      return _ownDocuments.isEmpty && _sharedDocuments.isEmpty;
    }
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    _messageSubscription?.cancel();
    _connectionSubscription?.cancel();
    _wsService.dispose();
    super.dispose();
  }

  Future<void> _loadMessages() async {
    if (_currentChat == null) return;

    setState(() {
      _isLoading = true;
    });

    try {
      final messages = await _chatService.listMessages(chatId: _currentChat!.id);
      setState(() {
        _messages = [];
        for (var msg in messages) {
          final question = msg['question'];
          final answer = msg['answer'];
          final timestamp = msg['created_at'];

          if (question != null && question.toString().trim().isNotEmpty) {
            _messages.add({
              'type': 'user',
              'question': question,
              'timestamp': timestamp,
            });
          }

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

  // Detectar si la pregunta es sobre documentos
  bool _isDocumentRelatedQuestion(String message) {
    final lowerMessage = message.toLowerCase();
    final documentKeywords = [
      'documento', 'doc', 'archivo', 'pdf', 'texto', 'paper',
      'que va', 'de que trata', 'de qué trata', 'que trata', 'sobre qué',
      'resumen', 'resume', 'contenido', 'habla', 'menciona',
      'dice', 'explica', 'analiza', 'información', 'describe',
      'cuál es', 'qué es', 'de qué habla', 'qué dice',
      'tema principal', 'idea principal', 'puntos clave',
      'busca en', 'encuentra en', 'según el', 'en el texto'
    ];
    
    return documentKeywords.any((keyword) => lowerMessage.contains(keyword));
  }

  // Generar mensaje de ayuda para documentos
  String _getDocumentHelpMessage() {
    if (_availableDocuments.isEmpty) {
      return 'No tienes documentos en tu biblioteca. Primero debes subir documentos para poder hacer preguntas sobre ellos.';
    }
    
    String message = '📄 Tienes ${_availableDocuments.length} documento(s) en tu biblioteca:\n\n';
    
    // Listar documentos
    for (int i = 0; i < _availableDocuments.length && i < 5; i++) {
      final doc = _availableDocuments[i];
      final icon = doc.contentType == 'application/pdf' ? '📄' : '📝';
      message += '$icon ${doc.title}';
      if (doc.isShared && !(_currentUser?.isAdmin ?? false)) {
        message += ' (compartido)';
      }
      message += '\n';
    }
    
    if (_availableDocuments.length > 5) {
      message += '... y ${_availableDocuments.length - 5} más\n';
    }
    
    message += '\n👉 Para hacer preguntas sobre un documento específico, selecciónalo con el botón de carpeta en la parte superior.';
    
    return message;
  }

  Future<void> _sendMessage() async {
    if (_messageController.text.trim().isEmpty || _isSending || _currentChat == null) {
      return;
    }

    final message = _messageController.text.trim();
    _messageController.clear();

    // Verificar si es una pregunta sobre documentos sin documento seleccionado
    if (_selectedDocumentId == null && _isDocumentRelatedQuestion(message)) {
      setState(() {
        _messages.add({
          'type': 'user',
          'question': message,
          'timestamp': DateTime.now().toIso8601String(),
        });
        _messages.add({
          'type': 'bot',
          'answer': _getDocumentHelpMessage(),
          'timestamp': DateTime.now().toIso8601String(),
          'isHelpMessage': true,
        });
        _shouldHighlightDocumentButton = true;
      });
      _scrollToBottom();
      
      // Quitar el resaltado después de 3 segundos
      Future.delayed(const Duration(seconds: 3), () {
        if (mounted) {
          setState(() {
            _shouldHighlightDocumentButton = false;
          });
        }
      });
      
      return;
    }

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
      // Usar WebSocket si está conectado
      if (_wsService.isConnected) {
        _wsService.sendChatMessage(
          content: message,
          documentIds: _selectedDocumentId != null ? [_selectedDocumentId!] : null,
          stream: true,
        );
        
        setState(() {
          _isSending = false;
        });
      } else {
        // Fallback a HTTP si WebSocket no está disponible
        final response = await _chatService.sendMessage(
          chatId: _currentChat!.id,
          message: message,
          documentIds: _selectedDocumentId != null ? [_selectedDocumentId!] : null,
          nResults: 5,
        );

        setState(() {
          final answer = response.answer;
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
      }
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

  Widget _buildMessageBubble(Map<String, dynamic> message, ResponsiveInfo sizingInfo) {
    final isUser = message['type'] == 'user';
    final isStreaming = message['isStreaming'] == true;
    final isHelpMessage = message['isHelpMessage'] == true;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * (sizingInfo.isMobile ? 0.85 : 0.75),
        ),
        margin: EdgeInsets.only(bottom: sizingInfo.spacing),
        padding: EdgeInsets.all(sizingInfo.cardPadding),
        decoration: BoxDecoration(
          color: isUser
              ? const Color(0xFFE91E63)
              : message['isError'] == true
                  ? Colors.red.withValues(alpha: 0.1)
                  : isHelpMessage
                      ? Colors.amber.withValues(alpha: 0.1)
                      : Colors.white,
          borderRadius: BorderRadius.only(
            topLeft: Radius.circular(sizingInfo.borderRadius),
            topRight: Radius.circular(sizingInfo.borderRadius),
            bottomLeft: Radius.circular(isUser ? sizingInfo.borderRadius : sizingInfo.smallBorderRadius),
            bottomRight: Radius.circular(isUser ? sizingInfo.smallBorderRadius : sizingInfo.borderRadius),
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
            if (isHelpMessage && !isUser)
              Row(
                children: [
                  Icon(
                    Icons.lightbulb_outline,
                    size: sizingInfo.fontSize.icon,
                    color: Colors.amber[700],
                  ),
                  SizedBox(width: sizingInfo.spacing),
                  Text(
                    'Sugerencia',
                    style: TextStyle(
                      fontSize: sizingInfo.fontSize.caption,
                      color: Colors.amber[700],
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            if (isStreaming && !isUser)
              Row(
                children: [
                  SizedBox(
                    width: sizingInfo.fontSize.caption,
                    height: sizingInfo.fontSize.caption,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        Colors.grey[600]!,
                      ),
                    ),
                  ),
                  SizedBox(width: sizingInfo.spacing),
                  Text(
                    'Escribiendo...',
                    style: TextStyle(
                      fontSize: sizingInfo.fontSize.caption,
                      color: Colors.grey[600],
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ),
            if ((isStreaming || isHelpMessage) && !isUser) SizedBox(height: sizingInfo.spacing),
            Text(
              isUser ? (message['question'] ?? '') : (message['answer'] ?? ''),
              style: TextStyle(
                fontSize: sizingInfo.fontSize.body,
                color: isUser
                    ? Colors.white
                    : message['isError'] == true
                        ? Colors.red
                        : isHelpMessage
                            ? Colors.amber[900]
                            : const Color(0xFF2C3E50),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      builder: (context, sizingInfo) {
        return Scaffold(
          appBar: AppBar(
            title: Row(
              children: [
                // Indicador de conexión WebSocket
                Container(
                  width: sizingInfo.spacing,
                  height: sizingInfo.spacing,
                  margin: EdgeInsets.only(right: sizingInfo.spacing),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _connectionState == WebSocketConnectionState.connected
                        ? Colors.green
                        : _connectionState == WebSocketConnectionState.connecting
                            ? Colors.orange
                            : Colors.red,
                  ),
                ),
                Expanded(
                  child: Text(
                    widget.isAdminView 
                      ? 'Vista Admin: ${_currentChat?.title ?? "Chat"}'
                      : (_currentChat?.title ?? 'Chat con Documentos'),
                    style: TextStyle(fontSize: sizingInfo.fontSize.subtitle),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            backgroundColor: const Color(0xFFE91E63),
            actions: [
              if (widget.isAdminView)
                IconButton(
                  icon: Icon(Icons.info_outline, size: sizingInfo.fontSize.icon),
                  onPressed: () => _showChatInfo(sizingInfo),
                  tooltip: 'Información del chat',
                ),
              AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
                  color: _shouldHighlightDocumentButton 
                      ? Colors.amber.withValues(alpha: 0.3)
                      : Colors.transparent,
                  boxShadow: _shouldHighlightDocumentButton
                      ? [
                          BoxShadow(
                            color: Colors.amber.withValues(alpha: 0.5),
                            blurRadius: 12,
                            spreadRadius: 1,
                          ),
                        ]
                      : [],
                ),
                child: IconButton(
                  icon: Badge(
                    label: Text(
                      _selectedDocumentId != null ? '1' : '0',
                      style: TextStyle(fontSize: sizingInfo.fontSize.caption * 0.8),
                    ),
                    isLabelVisible: _selectedDocumentId != null,
                    child: AnimatedScale(
                      scale: _shouldHighlightDocumentButton ? 1.2 : 1.0,
                      duration: const Duration(milliseconds: 300),
                      child: _isLoadingDocuments
                          ? SizedBox(
                              width: sizingInfo.fontSize.icon,
                              height: sizingInfo.fontSize.icon,
                              child: const CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                              ),
                            )
                          : Icon(Icons.folder, size: sizingInfo.fontSize.icon),
                    ),
                  ),
                  onPressed: _availableDocuments.isNotEmpty && !_isLoadingDocuments && !widget.isAdminView
                      ? _toggleDocumentSelector
                      : null,
                ),
              ),
              Container(
                margin: EdgeInsets.only(right: sizingInfo.cardPadding),
                padding: EdgeInsets.symmetric(
                  horizontal: sizingInfo.spacing, 
                  vertical: sizingInfo.spacing / 2
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
                ),
                child: Row(
                  children: [
                    if (_isLoadingDocuments)
                      SizedBox(
                        width: sizingInfo.fontSize.smallIcon,
                        height: sizingInfo.fontSize.smallIcon,
                        child: const CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      )
                    else
                      Icon(Icons.folder, size: sizingInfo.fontSize.smallIcon),
                    SizedBox(width: sizingInfo.spacing / 2),
                    Text(
                      _isLoadingDocuments
                          ? 'Cargando...'
                          : '${_availableDocuments.length} docs',
                      style: TextStyle(fontSize: sizingInfo.fontSize.caption),
                    ),
                  ],
                ),
              ),
            ],
          ),
          body: Column(
            children: [
              if (!widget.isAdminView && _shouldShowNoDocumentsMessage)
                Container(
                  padding: EdgeInsets.all(sizingInfo.cardPadding),
                  color: Colors.orange.shade100,
                  child: Row(
                    children: [
                      Icon(
                        Icons.warning, 
                        color: Colors.orange.shade700,
                        size: sizingInfo.fontSize.icon,
                      ),
                      SizedBox(width: sizingInfo.spacing),
                      Expanded(
                        child: Text(
                          'No tienes documentos disponibles. Sube o solicita acceso a documentos para hacer preguntas.',
                          style: TextStyle(
                            color: Colors.orange.shade700,
                            fontSize: sizingInfo.fontSize.body,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

              if (_showDocumentSelector && !widget.isAdminView)
                Container(
                  constraints: BoxConstraints(
                    maxHeight: sizingInfo.isMobile ? 120 : 150,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.grey[100],
                    border: Border(
                      bottom: BorderSide(color: Colors.grey[300]!),
                    ),
                  ),
                  child: _buildDocumentSelector(sizingInfo),
                ),

              Expanded(
                child: _messages.isEmpty && !_isLoading
                    ? _buildEmptyState(sizingInfo)
                    : ListView.builder(
                        controller: _scrollController,
                        padding: EdgeInsets.all(sizingInfo.cardPadding),
                        itemCount: _messages.length,
                        itemBuilder: (context, index) {
                          return _buildMessageBubble(_messages[index], sizingInfo);
                        },
                      ),
              ),

              _buildMessageInput(sizingInfo),
            ],
          ),
        );
      },
    );
  }

  Widget _buildDocumentSelector(ResponsiveInfo sizingInfo) {
    if (_availableDocuments.isEmpty) {
      return Center(
        child: Padding(
          padding: EdgeInsets.all(sizingInfo.cardPadding),
          child: Text(
            'No hay documentos disponibles',
            style: TextStyle(fontSize: sizingInfo.fontSize.body),
          ),
        ),
      );
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: EdgeInsets.all(sizingInfo.cardPadding),
      child: Row(
        children: _availableDocuments.map((doc) {
          final isSelected = _selectedDocumentId == doc.id;

          return GestureDetector(
            onTap: () {
              setState(() {
                _selectedDocumentId = isSelected ? null : doc.id;
              });
            },
            child: Container(
              width: sizingInfo.isMobile ? 120 : 150,
              margin: EdgeInsets.only(right: sizingInfo.spacing),
              padding: EdgeInsets.all(sizingInfo.spacing),
              decoration: BoxDecoration(
                color: isSelected
                    ? const Color(0xFFE91E63).withValues(alpha: 0.1)
                    : Colors.white,
                border: Border.all(
                  color: isSelected
                      ? const Color(0xFFE91E63)
                      : Colors.grey[300]!,
                  width: isSelected ? 2 : 1,
                ),
                borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
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
                    size: sizingInfo.fontSize.icon,
                  ),
                  SizedBox(height: sizingInfo.spacing / 2),
                  Flexible(
                    child: Text(
                      doc.title,
                      style: TextStyle(
                        fontSize: sizingInfo.fontSize.caption,
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
                  if (doc.isShared && !(_currentUser?.isAdmin ?? false)) ...[
                    SizedBox(height: sizingInfo.spacing / 4),
                    Text(
                      'Compartido',
                      style: TextStyle(
                        fontSize: sizingInfo.fontSize.caption * 0.8,
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
                gradient: const LinearGradient(
                  colors: [Color(0xFFE91E63), Color(0xFFFF69B4)],
                ),
                borderRadius: BorderRadius.circular(sizingInfo.fontSize.emptyStateIcon),
              ),
              child: Icon(
                Icons.chat_bubble_outline,
                color: Colors.white,
                size: sizingInfo.fontSize.emptyStateIcon,
              ),
            ),
            SizedBox(height: sizingInfo.spacing * 3),
            Text(
              '¡Hola! Soy MentIA, tu asistente inteligente',
              style: TextStyle(
                fontSize: sizingInfo.fontSize.subtitle,
                fontWeight: FontWeight.bold,
                color: const Color(0xFF2C3E50),
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: sizingInfo.spacing),
            Text(
              _selectedDocumentId == null
                  ? 'Puedo ayudarte con cualquier pregunta o buscar información en tus documentos'
                  : 'Responderé basándome en el documento seleccionado',
              style: TextStyle(
                fontSize: sizingInfo.fontSize.body,
                color: Colors.grey[600],
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: sizingInfo.spacing * 4),
            Wrap(
              alignment: WrapAlignment.center,
              spacing: sizingInfo.spacing,
              runSpacing: sizingInfo.spacing,
              children: [
                _buildSuggestionChip('Dime qué documentos tengo', sizingInfo),
                _buildSuggestionChip('Resume mi documento', sizingInfo),
                _buildSuggestionChip('Busca información sobre...', sizingInfo),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSuggestionChip(String text, ResponsiveInfo sizingInfo) {
    return ActionChip(
      label: Text(
        text,
        style: TextStyle(fontSize: sizingInfo.fontSize.caption),
      ),
      onPressed: () {
        _messageController.text = text;
      },
      backgroundColor: Colors.white,
      side: BorderSide(
        color: const Color(0xFFE91E63).withValues(alpha: 0.3),
      ),
      padding: EdgeInsets.symmetric(
        horizontal: sizingInfo.spacing,
        vertical: sizingInfo.spacing / 2,
      ),
    );
  }

  Widget _buildMessageInput(ResponsiveInfo sizingInfo) {
    return Container(
      padding: EdgeInsets.all(sizingInfo.cardPadding),
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
              enabled: !_isSending && !widget.isAdminView && !_isStreaming,
              style: TextStyle(fontSize: sizingInfo.fontSize.body),
              decoration: InputDecoration(
                hintText: widget.isAdminView
                    ? 'Vista de solo lectura (Administrador)'
                    : _isStreaming
                        ? 'Esperando respuesta...'
                        : _selectedDocumentId != null
                            ? 'Pregunta sobre el documento seleccionado...'
                            : 'Escribe un mensaje...',
                hintStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
                  borderSide: BorderSide.none,
                ),
                filled: true,
                fillColor: const Color(0xFFFFC0CB).withValues(alpha: 0.2),
                contentPadding: EdgeInsets.symmetric(
                  horizontal: sizingInfo.cardPadding,
                  vertical: sizingInfo.spacing,
                ),
              ),
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
          SizedBox(width: sizingInfo.spacing),
          CircleAvatar(
            radius: sizingInfo.isMobile ? 20 : 24,
            backgroundColor: const Color(0xFFE91E63),
            child: IconButton(
              icon: _isSending || _isStreaming
                  ? SizedBox(
                      width: sizingInfo.fontSize.icon,
                      height: sizingInfo.fontSize.icon,
                      child: const CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : Icon(Icons.send, color: Colors.white, size: sizingInfo.fontSize.icon),
              onPressed: (_isSending || widget.isAdminView || _isStreaming) ? null : _sendMessage,
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

  void _showChatInfo(ResponsiveInfo sizingInfo) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          'Información del Chat',
          style: TextStyle(fontSize: sizingInfo.fontSize.subtitle),
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Chat: ${_currentChat?.title ?? "Sin título"}',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: sizingInfo.fontSize.body,
                ),
              ),
              SizedBox(height: sizingInfo.spacing),
              Text(
                'ID del Chat: ${_currentChat?.id ?? "N/A"}',
                style: TextStyle(fontSize: sizingInfo.fontSize.body),
              ),
              SizedBox(height: sizingInfo.spacing),
              Text(
                'Usuario ID: ${_currentChat?.userId ?? "N/A"}',
                style: TextStyle(fontSize: sizingInfo.fontSize.body),
              ),
              SizedBox(height: sizingInfo.spacing),
              Text(
                'Estado WebSocket: ${_connectionState.name}',
                style: TextStyle(
                  fontSize: sizingInfo.fontSize.body,
                  color: _connectionState == WebSocketConnectionState.connected
                      ? Colors.green
                      : Colors.red,
                ),
              ),
              SizedBox(height: sizingInfo.spacing * 2),
              const Divider(),
              SizedBox(height: sizingInfo.spacing),
              Text(
                'Documentos en este chat:',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: sizingInfo.fontSize.body,
                ),
              ),
              SizedBox(height: sizingInfo.spacing),
              if (_isLoadingDocuments)
                const Center(
                  child: CircularProgressIndicator(),
                )
              else if (_availableDocuments.isEmpty)
                Text(
                  'No hay documentos asociados',
                  style: TextStyle(
                    fontStyle: FontStyle.italic,
                    fontSize: sizingInfo.fontSize.body,
                  ),
                )
              else
                ..._availableDocuments.map((doc) => Padding(
                      padding: EdgeInsets.symmetric(vertical: sizingInfo.spacing / 2),
                      child: Row(
                        children: [
                          Icon(
                            _getDocumentIcon(doc.contentType),
                            size: sizingInfo.fontSize.icon,
                            color: Colors.grey[600],
                          ),
                          SizedBox(width: sizingInfo.spacing),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  doc.title,
                                  style: TextStyle(fontSize: sizingInfo.fontSize.body),
                                ),
                                Text(
                                  'Archivo: ${doc.fileName}',
                                  style: TextStyle(
                                    fontSize: sizingInfo.fontSize.caption,
                                    color: Colors.grey[600],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    )).toList(),
              SizedBox(height: sizingInfo.spacing * 2),
              Text(
                'Nota: Esta es una vista de solo lectura para administradores.',
                style: TextStyle(
                  fontSize: sizingInfo.fontSize.caption,
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
            child: Text(
              'Cerrar',
              style: TextStyle(fontSize: sizingInfo.fontSize.button),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
  }
}
