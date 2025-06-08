class Message {
  final int id;
  final String content;
  final bool isUser;
  final DateTime timestamp;
  final List<String>? sources; // Para referencias RAG

  Message({
    required this.id,
    required this.content,
    required this.isUser,
    required this.timestamp,
    this.sources,
  });

  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      id: json['id'],
      content: json['content'] ?? json['question'] ?? json['answer'] ?? '',
      isUser: json['is_user'] ?? false,
      timestamp: DateTime.parse(
          json['created_at'] ?? DateTime.now().toIso8601String()),
      sources:
          json['sources'] != null ? List<String>.from(json['sources']) : null,
    );
  }
}
