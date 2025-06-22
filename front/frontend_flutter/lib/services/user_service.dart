import 'dart:convert';
import 'api_client.dart';
import '../models/user.dart';
import '../config/api_config.dart';

class UserService {
  static final UserService _instance = UserService._internal();
  factory UserService() => _instance;
  UserService._internal();
  
  final ApiClient _apiClient = apiClient;

  // Obtener todos los usuarios (solo admins)
  Future<List<User>> getUsers() async {
    try {
      final response = await _apiClient.get(ApiConfig.listUsers);
      final data = json.decode(response.body) as List;
      return data.map((userJson) => User.fromJson(userJson)).toList();
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al cargar usuarios: ${e.message}');
      }
      throw Exception('Failed to load users: $e');
    }
  }

  // Crear un nuevo usuario
  Future<User> createUser({
    required String username,
    required String email,
    required String password,
  }) async {
    try {
      final response = await _apiClient.post(
        ApiConfig.register,
        body: {
          'username': username,
          'email': email,
          'password': password,
        },
      );

      final data = json.decode(response.body);
      // El registro devuelve el usuario creado
      return User(
        id: data['user_id'],
        username: username,
        email: email,
        role: UserRole.user, // Los nuevos usuarios siempre son normales
        createdAt: DateTime.now(),
      );
    } catch (e) {
      if (e is ApiException) {
        throw Exception(e.message);
      }
      throw Exception('Error creating user: $e');
    }
  }

  // Actualizar un usuario
  Future<User> updateUser({
    required int userId,
    required String username,
    required String email,
  }) async {
    try {
      final response = await _apiClient.put(
        ApiConfig.updateUser(userId),
        body: {
          'username': username,
          'email': email,
        },
      );

      final data = json.decode(response.body);
      return User.fromJson(data);
    } catch (e) {
      if (e is ApiException) {
        throw Exception(e.message);
      }
      throw Exception('Error updating user: $e');
    }
  }

  // Eliminar un usuario
  Future<void> deleteUser(int userId) async {
    try {
      await _apiClient.delete(ApiConfig.deleteUser(userId));
    } catch (e) {
      if (e is ApiException) {
        throw Exception(e.message);
      }
      throw Exception('Error deleting user: $e');
    }
  }

  // Buscar usuarios
  Future<List<User>> searchUsers(String query) async {
    try {
      final response = await _apiClient.get(
        ApiConfig.searchUsers,
        queryParams: {'q': query},
      );

      final data = json.decode(response.body) as List;
      return data.map((userJson) => User.fromJson(userJson)).toList();
    } catch (e) {
      if (e is ApiException) {
        throw Exception('Error al buscar usuarios: ${e.message}');
      }
      throw Exception('Failed to search users: $e');
    }
  }
}
