class Document {
  final int id;
  final String title;
  final String? content;
  final String contentType;
  final String? chromadbId;
  final int uploadedBy;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final String? fileUrl;
  final String status;
  final String? statusMessage;
  final int? fileSize;
  final String? originalFilename;

  // Campos adicionales para compatibilidad con el frontend
  bool isShared;
  final List<int> sharedWithUsers;

  Document({
    required this.id,
    required this.title,
    this.content,
    required this.contentType,
    this.chromadbId,
    required this.uploadedBy,
    this.createdAt,
    this.updatedAt,
    this.fileUrl,
    this.status = 'pending',
    this.statusMessage,
    this.fileSize,
    this.originalFilename,
    this.isShared = false,
    this.sharedWithUsers = const [],
  });

  // Getters para compatibilidad con código existente
  String get fileName => originalFilename ?? title;
  String get mimeType => contentType;
  int get ownerId => uploadedBy;
  String get ownerName => 'Usuario';

  factory Document.fromJson(Map<String, dynamic> json) {
    return Document(
      id: json['id'],
      title: json['title'],
      content: json['content'],
      contentType: json['content_type'] ?? 'text/plain',
      chromadbId: json['chromadb_id'],
      uploadedBy: json['uploaded_by'],
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : null,
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
      fileUrl: json['file_url'],
      status: json['status'] ?? 'pending',
      statusMessage: json['status_message'],
      fileSize: json['file_size'],
      originalFilename: json['original_filename'],
      isShared: json['is_shared'] ?? false,
      sharedWithUsers: List<int>.from(json['shared_with_users'] ?? []),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'content': content,
      'content_type': contentType,
      'chromadb_id': chromadbId,
      'uploaded_by': uploadedBy,
      'created_at': createdAt?.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'file_url': fileUrl,
      'status': status,
      'status_message': statusMessage,
      'file_size': fileSize,
      'original_filename': originalFilename,
      'is_shared': isShared,
      'shared_with_users': sharedWithUsers,
    };
  }

  // Método helper para verificar si el documento está procesado
  bool get isProcessed => status == 'completed';
  bool get isProcessing => status == 'processing';
  bool get hasError => status == 'error';
  bool get isPending => status == 'pending';

  // Método para crear una copia con valores actualizados
  Document copyWith({
    int? id,
    String? title,
    String? content,
    String? contentType,
    String? chromadbId,
    int? uploadedBy,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? fileUrl,
    String? status,
    String? statusMessage,
    int? fileSize,
    String? originalFilename,
    bool? isShared,
    List<int>? sharedWithUsers,
  }) {
    return Document(
      id: id ?? this.id,
      title: title ?? this.title,
      content: content ?? this.content,
      contentType: contentType ?? this.contentType,
      chromadbId: chromadbId ?? this.chromadbId,
      uploadedBy: uploadedBy ?? this.uploadedBy,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      fileUrl: fileUrl ?? this.fileUrl,
      status: status ?? this.status,
      statusMessage: statusMessage ?? this.statusMessage,
      fileSize: fileSize ?? this.fileSize,
      originalFilename: originalFilename ?? this.originalFilename,
      isShared: isShared ?? this.isShared,
      sharedWithUsers: sharedWithUsers ?? this.sharedWithUsers,
    );
  }
}
