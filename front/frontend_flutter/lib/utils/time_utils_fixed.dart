/// Utilidades para el manejo de fechas y tiempos en la aplicación
class TimeUtils {
  /// Formatea una fecha en tiempo relativo (ej: "Hace 2 min", "Ayer", etc)
  static String formatRelativeTime(DateTime? date, {bool showDebugLogs = false}) {
    if (date == null) {
      return 'Sin fecha';
    }

    try {
      // Si la fecha viene con 'Z' al final, es UTC y necesitamos convertirla a local
      final localDateTime = date.isUtc ? date.toLocal() : date;
      final now = DateTime.now();
      final difference = now.difference(localDateTime);

      // Logs para debugging (solo si está habilitado)
      if (showDebugLogs) {
        print('🕐 TimeUtils: Fecha original: $date (UTC: ${date.isUtc})');
        print('🕐 TimeUtils: Fecha local: $localDateTime');
        print('🕐 TimeUtils: Ahora: $now');
        print('🕐 TimeUtils: Diferencia en minutos: ${difference.inMinutes}');
      }

      // Si es futuro (error de sincronización)
      if (difference.isNegative) {
        return 'Justo ahora';
      }

      // Menos de 1 minuto
      if (difference.inSeconds < 60) {
        return 'Hace un momento';
      }
      
      // Menos de 1 hora
      if (difference.inMinutes < 60) {
        final mins = difference.inMinutes;
        return 'Hace $mins ${mins == 1 ? 'min' : 'min'}';
      }
      
      // Menos de 1 día
      if (difference.inHours < 24) {
        final hours = difference.inHours;
        return 'Hace ${hours}h';
      }
      
      // Ayer
      if (difference.inDays == 1) {
        return 'Ayer';
      }
      
      // Menos de una semana
      if (difference.inDays < 7) {
        final days = difference.inDays;
        return 'Hace $days ${days == 1 ? 'día' : 'días'}';
      }
      
      // Menos de un mes
      if (difference.inDays < 30) {
        final weeks = (difference.inDays / 7).floor();
        return 'Hace $weeks ${weeks == 1 ? 'semana' : 'semanas'}';
      }
      
      // Menos de un año
      if (difference.inDays < 365) {
        final months = (difference.inDays / 30).floor();
        return 'Hace $months ${months == 1 ? 'mes' : 'meses'}';
      }
      
      // Más de un año - mostrar fecha completa
      return formatShortDate(localDateTime);
      
    } catch (e) {
      print('❌ ERROR en TimeUtils.formatRelativeTime: $e');
      return 'Fecha desconocida';
    }
  }

  /// Formatea una fecha en formato corto (DD/MM/YYYY)
  static String formatShortDate(DateTime? date) {
    if (date == null) return 'Sin fecha';
    
    final localDate = date.isUtc ? date.toLocal() : date;
    return '${localDate.day.toString().padLeft(2, '0')}/${localDate.month.toString().padLeft(2, '0')}/${localDate.year}';
  }

  /// Formatea una fecha con hora (DD/MM/YYYY HH:MM)
  static String formatDateTime(DateTime? date) {
    if (date == null) return 'Sin fecha';
    
    final localDate = date.isUtc ? date.toLocal() : date;
    return '${localDate.day.toString().padLeft(2, '0')}/${localDate.month.toString().padLeft(2, '0')}/${localDate.year} '
           '${localDate.hour.toString().padLeft(2, '0')}:${localDate.minute.toString().padLeft(2, '0')}';
  }

  /// Verifica si una fecha es hoy
  static bool isToday(DateTime date) {
    final now = DateTime.now();
    final localDate = date.isUtc ? date.toLocal() : date;
    return localDate.year == now.year && 
           localDate.month == now.month && 
           localDate.day == now.day;
  }

  /// Verifica si una fecha fue ayer
  static bool isYesterday(DateTime date) {
    final yesterday = DateTime.now().subtract(const Duration(days: 1));
    final localDate = date.isUtc ? date.toLocal() : date;
    return localDate.year == yesterday.year && 
           localDate.month == yesterday.month && 
           localDate.day == yesterday.day;
  }
}
