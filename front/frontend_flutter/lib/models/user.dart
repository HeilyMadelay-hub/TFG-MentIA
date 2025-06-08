enum UserRole { 
  user, 
  admin 
}

class User {
  final int id;
  final String username;
  final String email;
  final UserRole role;
  final String? avatar;
  final DateTime createdAt;

  const User({
    required this.id,
    required this.username,
    required this.email,
    required this.role,
    this.avatar,
    required this.createdAt,
  });

  bool get isAdmin => role == UserRole.admin;

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      username: json['username'],
      email: json['email'],
      role: json['is_admin'] == true ? UserRole.admin : UserRole.user,
      avatar: json['avatar_url'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'email': email,
      'role': role.name,
      'avatar': avatar,
      'created_at': createdAt.toIso8601String(),
    };
  }
}
