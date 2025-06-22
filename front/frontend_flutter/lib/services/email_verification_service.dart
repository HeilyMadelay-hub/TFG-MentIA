// email_verification_service.dart

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/material.dart';
import '../config/api_config.dart';

class EmailVerificationService {
  static final String baseUrl = ApiConfig.baseUrl;
  
  /// Maneja el clic en "Sí, fui yo" desde el email o desde el modal
  static Future<bool> verifyEmailChange(BuildContext context, String token) async {
    try {
      print('🔍 Iniciando verificación de email');
      print('📝 Token a verificar: $token');
      
      // Limpiar el token de espacios o caracteres no deseados
      final cleanToken = token.trim();
      
      final response = await http.post(
        Uri.parse('$baseUrl/api/users/verify-email'),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'token': cleanToken,
        }),
      );
      
      print('📡 Respuesta del servidor: ${response.statusCode}');
      print('📤 Body: ${response.body}');
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        // Mostrar mensaje de éxito
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Row(
                children: [
                  Icon(Icons.check_circle, color: Colors.white),
                  SizedBox(width: 8),
                  Text(data['message'] ?? 'Email actualizado correctamente'),
                ],
              ),
              backgroundColor: Colors.green,
              duration: Duration(seconds: 3),
            ),
          );
        }
        
        return true;
      } else {
        final error = jsonDecode(response.body);
        final errorMessage = error['detail'] ?? 'Error al verificar email';
        
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Row(
                children: [
                  Icon(Icons.error, color: Colors.white),
                  SizedBox(width: 8),
                  Expanded(child: Text(errorMessage)),
                ],
              ),
              backgroundColor: Colors.red,
              duration: Duration(seconds: 4),
            ),
          );
        }
        
        return false;
      }
    } catch (e) {
      print('💥 Error en verificación: $e');
      
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                Icon(Icons.error, color: Colors.white),
                SizedBox(width: 8),
                Text('Error de conexión'),
              ],
            ),
            backgroundColor: Colors.red,
          ),
        );
      }
      
      return false;
    }
  }
  
  /// Extrae el token de un deep link
  static String? extractTokenFromUrl(String url) {
    try {
      final uri = Uri.parse(url);
      return uri.queryParameters['token'];
    } catch (e) {
      print('Error extrayendo token de URL: $e');
      return null;
    }
  }
  
  /// Maneja la verificación manual (para testing)
  static Future<bool> verifyManualToken(BuildContext context, String token) async {
    print('🧪 Verificación manual con token: $token');
    
    // Si el token parece ser un UUID (36 caracteres)
    if (token.length == 36 && 
        RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
            .hasMatch(token)) {
      print('📌 Token es un UUID válido');
      return verifyEmailChange(context, token);
    }
    
    // Si el token está codificado, intentar decodificar
    if (token.contains('eyJ') || token.length > 50) {
      try {
        final decoded = utf8.decode(base64.decode(token));
        final tokenData = jsonDecode(decoded);
        final actualToken = tokenData['token'];
        print('✅ Token decodificado: $actualToken');
        return verifyEmailChange(context, actualToken);
      } catch (e) {
        print('⚠️ No se pudo decodificar, usando token original');
      }
    }
    
    return verifyEmailChange(context, token);
  }
}
