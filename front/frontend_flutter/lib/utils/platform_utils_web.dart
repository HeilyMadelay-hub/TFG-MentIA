// platform_utils_web.dart
import 'package:web/web.dart' as web;
import 'dart:developer' as developer;

Map<String, dynamic>? getUrlInfo() {
  try {
    final uri = Uri.parse(web.window.location.href);
    
    // Buscar token en query parameters
    final token = uri.queryParameters['token'];
    
    // También verificar si la ruta contiene reset-password
    final isResetPassword = uri.path.contains('reset-password') || 
                           uri.toString().contains('reset-password');
    
    if (token != null && token.isNotEmpty) {
      return {
        'path': uri.path,
        'token': token,
        'query': uri.queryParameters,
        'isResetPassword': isResetPassword,
      };
    }
    
    // Si no hay token pero es una ruta de reset-password, 
    // devolver información de todos modos
    if (isResetPassword) {
      return {
        'path': uri.path,
        'query': uri.queryParameters,
        'isResetPassword': true,
      };
    }
    
    return null;
  } catch (e) {
    developer.log('Error parsing URL: $e', name: 'platform_utils_web');
    return null;
  }
}
