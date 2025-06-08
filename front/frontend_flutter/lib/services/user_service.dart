import 'package:http/http.dart' as http;
import 'dart:convert';
import '../models/user.dart';
import '../config/api_config.dart';
import '../services/auth_service.dart';

class UserService {
  static final UserService _instance = UserService._internal();
  factory UserService() => _instance;
  UserService._internal();

  // Obtener todos los usuarios (solo admins)
  Future<List<User>> getUsers() async {
    final token = await AuthService().getToken();
    if (token == null) {
      throw Exception('No authentication token');
    }

    final response = await http.get(
      Uri.parse(ApiConfig.listUsers),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body) as List;
      return data.map((userJson) => User.fromJson(userJson)).toList();
    } else {
      throw Exception('Failed to load users: ${response.statusCode}');
    }
  }

  // Crear un nuevo usuario
  Future<User> createUser({
    required String username,
    required String email,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse(ApiConfig.register),
      headers: {
        'Content-Type': 'application/json',
      },
      body: json.encode({
        'username': username,
        'email': email,
        'password': password,
      }),
    );

    if (response.statusCode == 201 || response.statusCode == 200) {
      final data = json.decode(response.body);
      // El registro devuelve el usuario creado
      return User(
        id: data['user_id'],
        username: username,
        email: email,
        role: UserRole.user, // Los nuevos usuarios siempre son normales
        createdAt: DateTime.now(),
      );
    } else {
      final error = json.decode(response.body);
      throw Exception(error['detail'] ?? 'Error creating user');
    }
  }

  // Actualizar un usuario
  Future<User> updateUser({
    required int userId,
    required String username,
    required String email,
  }) async {
    final token = await AuthService().getToken();
    if (token == null) {
      throw Exception('No authentication token');
    }

    final response = await http.put(
      Uri.parse('${ApiConfig.baseUrl}/users/$userId'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: json.encode({
        'username': username,
        'email': email,
      }),
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return User.fromJson(data);
    } else {
      final error = json.decode(response.body);
      throw Exception(error['detail'] ?? 'Error updating user');
    }
  }

  // Eliminar un usuario
  Future<void> deleteUser(int userId) async {
    final token = await AuthService().getToken();
    if (token == null) {
      throw Exception('No authentication token');
    }

    final response = await http.delete(
      Uri.parse('${ApiConfig.baseUrl}/users/$userId'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode != 204 && response.statusCode != 200) {
      final error = json.decode(response.body);
      throw Exception(error['detail'] ?? 'Error deleting user');
    }
  }

  // Buscar usuarios
  Future<List<User>> searchUsers(String query) async {
    final token = await AuthService().getToken();
    if (token == null) {
      throw Exception('No authentication token');
    }

    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/users/search?q=$query'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body) as List;
      return data.map((userJson) => User.fromJson(userJson)).toList();
    } else {
      throw Exception('Failed to search users: ${response.statusCode}');
    }
  }
}
