import 'package:http/http.dart' as http;
import 'dart:convert';
import '../services/auth_service.dart';
import '../config/api_config.dart';

class AdminPanelService {

  /// Obtiene todos los datos del dashboard administrativo
  static Future<Map<String, dynamic>> getDashboard() async {
    try {
      final authService = AuthService();
      final token = await authService.getToken();
      if (token == null) {
        throw Exception('No hay token de autenticación');
      }
      
      const url = ApiConfig.adminPanelDashboard;
      
      final response = await http.get(
        Uri.parse(url),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );
      


      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        

        
        return data;
      } else if (response.statusCode == 403) {
        throw Exception('Acceso denegado: Solo administradores');
      } else {
        throw Exception('Error al cargar dashboard: ${response.statusCode}');
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Formatea números grandes de forma legible
  static String formatNumber(int number) {
    if (number >= 1000000) {
      return '${(number / 1000000).toStringAsFixed(1)}M';
    } else if (number >= 1000) {
      return '${(number / 1000).toStringAsFixed(1)}K';
    }
    return number.toString();
  }

  /// Convierte timestamp a DateTime
  static DateTime? parseTimestamp(String? timestamp) {
    if (timestamp == null || timestamp.isEmpty) return null;
    
    try {
      // Remover microsegundos si están presentes (después del punto)
      String cleanTimestamp = timestamp;
      if (timestamp.contains('.') && timestamp.contains('Z')) {
        // Formato: 2025-06-18T00:44:53.299291Z -> 2025-06-18T00:44:53Z
        cleanTimestamp = timestamp.substring(0, timestamp.indexOf('.')) + 'Z';
      } else if (timestamp.contains('.') && !timestamp.endsWith('Z')) {
        // Formato: 2025-06-18T00:44:53.299291 -> 2025-06-18T00:44:53
        cleanTimestamp = timestamp.substring(0, timestamp.indexOf('.'));
      }
      
      // Si termina con 'Z', es UTC
      if (cleanTimestamp.endsWith('Z')) {
        return DateTime.parse(cleanTimestamp);
      }
      
      // Si no tiene información de zona horaria, asumimos UTC
      if (!cleanTimestamp.contains('+') && !cleanTimestamp.contains('-')) {
        return DateTime.parse(cleanTimestamp + 'Z');
      }
      
      return DateTime.parse(cleanTimestamp);
    } catch (e) {

      // Intento alternativo: parsear directamente
      try {
        return DateTime.parse(timestamp);
      } catch (_) {
        return null;
      }
    }
  }

  /// Formatea tiempo relativo (hace X minutos/horas/días)
  static String formatRelativeTime(String? timestamp) {
    if (timestamp == null || timestamp.isEmpty) {
      return 'Fecha desconocida';
    }

    try {
      DateTime dateTime;
      
      // Si el timestamp ya incluye 'Z' o zona horaria, lo parseamos directamente
      if (timestamp.endsWith('Z') || timestamp.contains('+') || timestamp.contains('-')) {
        dateTime = DateTime.parse(timestamp);
      } else {
        // Si no tiene zona horaria, asumimos que es UTC
        dateTime = DateTime.parse(timestamp + 'Z');
      }
      
      // IMPORTANTE: Trabajar siempre en UTC para evitar problemas de zona horaria
      final now = DateTime.now().toUtc();
      final utcDateTime = dateTime.toUtc();
      final difference = now.difference(utcDateTime);



      // Si la diferencia es negativa (fecha futura), mostrar "Ahora"
      if (difference.isNegative) {
        return 'Ahora';
      }
      
      if (difference.inSeconds < 60) {
        return 'Hace un momento';
      } else if (difference.inMinutes < 60) {
        final mins = difference.inMinutes;
        return mins == 1 ? 'Hace 1 min' : 'Hace $mins min';
      } else if (difference.inHours < 24) {
        final hours = difference.inHours;
        return hours == 1 ? 'Hace 1h' : 'Hace ${hours}h';
      } else {
        // Para días, calculamos basado en fechas calendario, no en horas exactas
        final nowLocal = now.toLocal();
        final dateTimeLocal = utcDateTime.toLocal();
        
        // Calcular la diferencia en días calendario
        final nowDate = DateTime(nowLocal.year, nowLocal.month, nowLocal.day);
        final targetDate = DateTime(dateTimeLocal.year, dateTimeLocal.month, dateTimeLocal.day);
        final daysDifference = nowDate.difference(targetDate).inDays;
        
        if (daysDifference == 0) {
          // Es hoy
          return 'Hoy';
        } else if (daysDifference == 1) {
          // Es ayer
          return 'Ayer';
        } else if (daysDifference < 7) {
          return daysDifference == 1 ? 'Hace 1 día' : 'Hace $daysDifference días';
        } else if (daysDifference < 30) {
          final weeks = (daysDifference / 7).floor();
          return weeks == 1 ? 'Hace 1 semana' : 'Hace $weeks semanas';
        } else {
          // Para fechas muy antiguas, mostrar formato corto
          final localDate = dateTime.toLocal();
          final day = localDate.day.toString().padLeft(2, '0');
          final month = localDate.month.toString().padLeft(2, '0');
          final year = localDate.year;
          return '$day/$month/$year';
        }
      }
    } catch (e) {

      // Intentar mostrar al menos algo útil
      try {
        final date = DateTime.parse(timestamp);
        return '${date.day}/${date.month}/${date.year}';
      } catch (_) {
        return 'Fecha inválida';
      }
    }
  }

  /// Obtiene el icono según el tipo de actividad
  static String getActivityIcon(String type) {
    switch (type) {
      case 'document':
        return '📄';
      case 'chat':
        return '💬';
      case 'user':
        return '👤';
      default:
        return '📌';
    }
  }

  /// Obtiene el color según el estado
  static String getStatusColor(String? status) {
    switch (status?.toLowerCase()) {
      case 'procesando':
      case 'processing':
        return 'orange';
      case 'completado':
      case 'completed':
      case 'success':
        return 'green';
      case 'error':
      case 'failed':
        return 'red';
      default:
        return 'grey';
    }
  }
}
