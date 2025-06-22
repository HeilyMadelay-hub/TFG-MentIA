import 'package:flutter/foundation.dart';

/// Simple logger utility for debugging
class Logger {
  final String name;
  static bool enableLogging = kDebugMode;
  
  Logger(this.name);
  
  void _log(String level, String message, [Object? error, StackTrace? stackTrace]) {
    if (!enableLogging) return;
    
    final timestamp = DateTime.now().toIso8601String();
    final logMessage = '[$timestamp] [$name] $level: $message';
    
    // En debug mode, usar debugPrint
    if (kDebugMode) {
      debugPrint(logMessage);
      if (error != null) {
        debugPrint('Error: $error');
      }
      if (stackTrace != null) {
        debugPrint('StackTrace: $stackTrace');
      }
    }
  }
  
  void debug(String message) {
    _log('DEBUG', message);
  }
  
  void info(String message) {
    _log('INFO', message);
  }
  
  void warning(String message) {
    _log('WARN', message);
  }
  
  void error(String message, [Object? error, StackTrace? stackTrace]) {
    _log('ERROR', message, error, stackTrace);
  }
}
