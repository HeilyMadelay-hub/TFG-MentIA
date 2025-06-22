import '../services/auth_service.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  
  factory ApiService() => _instance;
  
  ApiService._internal();
  
  final AuthService _authService = AuthService();
  
  Future<Map<String, dynamic>> changeEmailWithValidation(String newEmail) async {
    return await _authService.changeEmailWithValidation(newEmail);
  }
  
  Future<Map<String, dynamic>> verifyEmailChangeCode({
    required String token,
    required String code,
  }) async {
    return await _authService.verifyEmailChangeCode(
      token: token,
      code: code,
    );
  }
}
