// models/chat.dart

import 'message.dart';

// Clase para la respuesta de enviar un mensaje
class ChatMessage {
  final String answer;
  final DateTime? createdAt;
  final List<String>? sources;

  ChatMessage({
    required this.answer,
    this.createdAt,
    this.sources,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      answer: json['answer'] ?? '',
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at']) 
          : null,
      sources: json['sources'] != null 
          ? List<String>.from(json['sources']) 
          : null,
    );
  }
}

class Chat {
  final int id;
  final String title;
  final String? description;
  final DateTime createdAt;
  final DateTime lastMessageAt;
  final int messageCount;
  final String userId;
  final bool isActive;
  final List<String>? documentIds;
  final List<Message> messages;

  Chat({
    required this.id,
    required this.title,
    this.description,
    required this.createdAt,
    required this.lastMessageAt,
    this.messageCount = 0,
    required this.userId,
    this.isActive = true,
    this.documentIds,
    this.messages = const [],
  });

  // Constructor desde JSON (útil para las respuestas de la API)
  factory Chat.fromJson(Map<String, dynamic> json) {
    // Mapear diferentes campos de título que puede enviar el backend
    String title = json['title'] ?? json['name_chat'] ?? json['name'] ?? 'Chat sin título';
    
    // Asegurar que el título no esté vacío
    if (title.trim().isEmpty) {
      title = 'Chat sin título';
    }
    
    return Chat(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id'].toString()) ?? 0,
      title: title,
      description: json['description'],
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at']) 
          : DateTime.now(),
      lastMessageAt: json['last_message_at'] != null 
          ? DateTime.parse(json['last_message_at']) 
          : (json['updated_at'] != null
              ? DateTime.parse(json['updated_at'])
              : (json['created_at'] != null 
                  ? DateTime.parse(json['created_at'])
                  : DateTime.now())),
      messageCount: json['message_count'] ?? 0,
      userId: (json['user_id'] ?? json['id_user'] ?? '').toString(),
      isActive: json['is_active'] ?? true,
      documentIds: json['document_ids'] != null 
          ? List<String>.from(json['document_ids']) 
          : null,
      messages: json['messages'] != null 
          ? (json['messages'] as List).map((m) => Message.fromJson(m)).toList()
          : [],
    );
  }

  // Convertir a JSON (útil para enviar a la API)
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'created_at': createdAt.toIso8601String(),
      'last_message_at': lastMessageAt.toIso8601String(),
      'message_count': messageCount,
      'user_id': userId,
      'is_active': isActive,
      'document_ids': documentIds,
    };
  }

  // Método para crear una copia con modificaciones
  Chat copyWith({
    int? id,
    String? title,
    String? description,
    DateTime? createdAt,
    DateTime? lastMessageAt,
    int? messageCount,
    String? userId,
    bool? isActive,
    List<String>? documentIds,
    List<Message>? messages,
  }) {
    return Chat(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      createdAt: createdAt ?? this.createdAt,
      lastMessageAt: lastMessageAt ?? this.lastMessageAt,
      messageCount: messageCount ?? this.messageCount,
      userId: userId ?? this.userId,
      isActive: isActive ?? this.isActive,
      documentIds: documentIds ?? this.documentIds,
      messages: messages ?? this.messages,
    );
  }

  // Método para obtener el tiempo desde el último mensaje
  String getTimeAgo() {
    final now = DateTime.now();
    final difference = now.difference(lastMessageAt);

    if (difference.inDays > 365) {
      return '${(difference.inDays / 365).floor()} año${(difference.inDays / 365).floor() > 1 ? 's' : ''} atrás';
    } else if (difference.inDays > 30) {
      return '${(difference.inDays / 30).floor()} mes${(difference.inDays / 30).floor() > 1 ? 'es' : ''} atrás';
    } else if (difference.inDays > 0) {
      return '${difference.inDays} día${difference.inDays > 1 ? 's' : ''} atrás';
    } else if (difference.inHours > 0) {
      return '${difference.inHours} hora${difference.inHours > 1 ? 's' : ''} atrás';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes} minuto${difference.inMinutes > 1 ? 's' : ''} atrás';
    } else {
      return 'Ahora mismo';
    }
  }

  @override
  String toString() {
    return 'Chat(id: $id, title: $title, messageCount: $messageCount)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is Chat && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;
}
