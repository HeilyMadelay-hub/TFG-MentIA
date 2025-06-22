class WebSocketMessage {
  final String type;
  final Map<String, dynamic> data;
  final DateTime? timestamp;

  WebSocketMessage({
    required this.type,
    required this.data,
    this.timestamp,
  });

  factory WebSocketMessage.fromJson(Map<String, dynamic> json) {
    return WebSocketMessage(
      type: json['type'] ?? '',
      data: json['data'] ?? {},
      timestamp: json['timestamp'] != null 
          ? DateTime.parse(json['timestamp']) 
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'type': type,
      'data': data,
      if (timestamp != null) 'timestamp': timestamp!.toIso8601String(),
    };
  }
  
  // Helper methods para tipos comunes
  bool get isConnectionSuccess => type == 'connection_success';
  bool get isError => type == 'error';
  bool get isStreamStart => type == 'stream_start';
  bool get isStreamChunk => type == 'stream_chunk';
  bool get isStreamEnd => type == 'stream_end';
  bool get isStreamUpdate => type == 'stream_update';
  bool get isMessageComplete => type == 'message_complete';
  bool get isTypingIndicator => type == 'typing_indicator';
  bool get isHeartbeat => type == 'heartbeat';
  
  // Getters para datos comunes
  String? get errorMessage => isError ? data['error'] : null;
  String? get streamId => data['stream_id'];
  String? get content => data['content'];
  String? get fullContent => data['full_content'];
  int? get chunkIndex => data['chunk_index'];
  int? get totalChunks => data['total_chunks'];
  
  @override
  String toString() {
    return 'WebSocketMessage(type: $type, data: $data, timestamp: $timestamp)';
  }
}

// Tipos de mensajes WebSocket
class WebSocketMessageType {
  static const String connectionSuccess = 'connection_success';
  static const String connectionError = 'connection_error';
  static const String disconnect = 'disconnect';
  
  static const String message = 'message';
  static const String messageSaved = 'message_saved';
  
  static const String streamStart = 'stream_start';
  static const String streamChunk = 'stream_chunk';
  static const String streamEnd = 'stream_end';
  static const String streamUpdate = 'stream_update';
  
  static const String statusUpdate = 'status_update';
  static const String typingIndicator = 'typing_indicator';
  
  static const String error = 'error';
  
  static const String heartbeat = 'heartbeat';
  static const String ping = 'ping';
  static const String pong = 'pong';
  
  static const String userJoined = 'user_joined';
  static const String userLeft = 'user_left';
  static const String rateLimitWarning = 'rate_limit_warning';
  
  static const String messageComplete = 'message_complete';
}

// Estados del streaming
class StreamStatus {
  static const String starting = 'starting';
  static const String inProgress = 'in_progress';
  static const String completed = 'completed';
  static const String failed = 'failed';
  static const String cancelled = 'cancelled';
}
