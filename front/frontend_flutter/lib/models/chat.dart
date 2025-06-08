class ChatModel {
  final int id;
  final String title;
  final int userId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<ChatMessage> messages;

  const ChatModel({
    required this.id,
    required this.title,
    required this.userId,
    required this.createdAt,
    required this.updatedAt,
    this.messages = const [],
  });

  factory ChatModel.fromJson(Map<String, dynamic> json) {
    return ChatModel(
      id: json['id'],
      title: json['name_chat'] ?? json['title'] ?? 'Chat sin título',
      userId: json['id_user'] ?? json['user_id'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at'] ?? json['created_at']),
      messages: (json['messages'] as List<dynamic>?)
          ?.map((msg) => ChatMessage.fromJson(msg))
          .toList() ?? [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name_chat': title,
      'id_user': userId,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'messages': messages.map((msg) => msg.toJson()).toList(),
    };
  }
}

class ChatMessage {
  final int id;
  final int chatId;
  final String question;
  final String answer;
  final DateTime? createdAt;  // CORREGIDO: Ahora es opcional

  const ChatMessage({
    required this.id,
    required this.chatId,
    required this.question,
    required this.answer,
    this.createdAt,  // CORREGIDO: Ya no es required
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] ?? 0,  // CORREGIDO: valor por defecto
      chatId: json['id_chat'] ?? json['chat_id'] ?? 0,
      question: json['question'] ?? '',
      answer: json['answer'] ?? '',
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at']) 
          : null,  // CORREGIDO: manejo de null
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'id_chat': chatId,
      'question': question,
      'answer': answer,
      'created_at': createdAt?.toIso8601String(),  // CORREGIDO: manejo de null
    };
  }
}
