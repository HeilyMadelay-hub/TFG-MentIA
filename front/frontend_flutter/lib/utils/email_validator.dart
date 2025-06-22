/// Validador de emails para prevenir duplicados y aplicar reglas específicas
class EmailValidator {
  // Dominios válidos de Gmail
  static const List<String> gmailDomains = ['gmail.com', 'googlemail.com'];
  
  // Proveedores que solo usan .com
  static const List<String> comOnlyProviders = [
    'gmail', 'hotmail', 'outlook', 'yahoo', 
    'aol', 'icloud', 'protonmail', 'zoho'
  ];
  
  /// Valida el formato básico de un email
  static bool isValidFormat(String email) {
    final RegExp emailRegex = RegExp(
      r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    );
    return emailRegex.hasMatch(email);
  }
  
  /// Extrae las partes del email (username y dominio)
  static Map<String, String> extractParts(String email) {
    if (email.isEmpty || !email.contains('@')) {
      return {'username': email, 'domain': ''};
    }
    
    final List<String> parts = email.split('@');
    return {
      'username': parts[0],
      'domain': parts.length > 1 ? parts[1] : ''
    };
  }
  
  /// Valida el dominio de Gmail
  static Map<String, dynamic> validateGmailDomain(String email) {
    final Map<String, String> emailParts = extractParts(email);
    final String username = emailParts['username'] ?? '';
    final String domain = emailParts['domain'] ?? '';
    
    // Solo validar si es un dominio de Gmail
    if (domain.toLowerCase() == 'gmail.com' || domain.toLowerCase() == 'googlemail.com') {
      // Verificar si tiene mayúsculas
      if (domain != domain.toLowerCase()) {
        return {
          'isValid': false,
          'error': 'El dominio de Gmail debe estar en minúsculas',
          'suggestion': '$username@${domain.toLowerCase()}'
        };
      }
    }
    
    // Detectar intentos de Gmail con dominio incorrecto
    if (domain.toLowerCase().contains('gmail') && !gmailDomains.contains(domain.toLowerCase())) {
      final Map<String, String> corrections = {
        'gmail.es': 'gmail.com',
        'gmail.com.es': 'gmail.com',
        'gmail.co': 'gmail.com',
        'gmail.cm': 'gmail.com',
        'gmai.com': 'gmail.com',
        'gmial.com': 'gmail.com',
        'gmal.com': 'gmail.com',
        'gmil.com': 'gmail.com'
      };
      
      if (corrections.containsKey(domain.toLowerCase())) {
        return {
          'isValid': false,
          'error': 'Gmail siempre usa .com',
          'suggestion': '$username@${corrections[domain.toLowerCase()]}'
        };
      }
      
      return {
        'isValid': false,
        'error': 'Dominio de Gmail inválido. Use @gmail.com'
      };
    }
    
    return {'isValid': true};
  }
  
  /// Valida dominios de otros proveedores
  static Map<String, dynamic> validateProviderDomain(String email) {
    final Map<String, String> emailParts = extractParts(email);
    final String username = emailParts['username'] ?? '';
    final String domain = emailParts['domain'] ?? '';
    
    // Verificar proveedores que solo usan .com
    for (final String provider in comOnlyProviders) {
      if (domain.toLowerCase().startsWith('$provider.') && !domain.toLowerCase().endsWith('.com')) {
        return {
          'isValid': false,
          'error': '${provider[0].toUpperCase()}${provider.substring(1)} usa dominio .com',
          'suggestion': '$username@$provider.com'
        };
      }
    }
    
    return {'isValid': true};
  }
  
  /// Validación completa del email
  static Map<String, dynamic> validate(String email) {
    // 1. Validar formato básico
    if (!isValidFormat(email)) {
      return {
        'isValid': false,
        'error': 'Formato de email inválido'
      };
    }
    
    // 2. Verificar específicamente si es un email de Gmail con mayúsculas
    final emailParts = extractParts(email);
    final domain = emailParts['domain'] ?? '';
    
    // Solo validar mayúsculas si es un dominio de Gmail
    if ((domain.toLowerCase() == 'gmail.com' || domain.toLowerCase() == 'googlemail.com') && 
        domain != domain.toLowerCase()) {
      return {
        'isValid': false,
        'error': 'El dominio de Gmail debe ser @gmail.com (en minúsculas)',
        'suggestion': '${emailParts['username'] ?? ''}@${domain.toLowerCase()}'
      };
    }
    
    // 3. Validar Gmail
    final Map<String, dynamic> gmailValidation = validateGmailDomain(email);
    if (!(gmailValidation['isValid'] ?? true)) {
      return gmailValidation;
    }
    
    // 4. Validar otros proveedores
    final Map<String, dynamic> providerValidation = validateProviderDomain(email);
    if (!(providerValidation['isValid'] ?? true)) {
      return providerValidation;
    }
    
    return {'isValid': true};
  }
  
  /// Sugiere correcciones para emails mal escritos
  static List<String> getSuggestions(String email) {
    final List<String> suggestions = [];
    
    // Si falta el @
    if (!email.contains('@') && email.contains('.')) {
      final List<String> providers = ['gmail', 'hotmail', 'yahoo', 'outlook'];
      for (final String provider in providers) {
        if (email.toLowerCase().contains(provider)) {
          final int idx = email.toLowerCase().indexOf(provider);
          if (idx > 0) {
            suggestions.add(
              '${email.substring(0, idx)}@${email.substring(idx)}'
            );
          }
        }
      }
    }
    
    return suggestions;
  }
  
  /// Verifica si dos emails son similares (mismo usuario, diferente dominio)
  static bool areSimilarEmails(String email1, String email2) {
    final Map<String, String> parts1 = extractParts(email1);
    final Map<String, String> parts2 = extractParts(email2);
    
    final String username1 = (parts1['username'] ?? '').toLowerCase();
    final String username2 = (parts2['username'] ?? '').toLowerCase();
    final String domain1 = (parts1['domain'] ?? '').toLowerCase();
    final String domain2 = (parts2['domain'] ?? '').toLowerCase();
    
    // Mismo username, diferente dominio
    return username1.isNotEmpty && 
           username1 == username2 && 
           domain1 != domain2;
  }
  
  /// Valida un email para registro (con lista de emails existentes)
  static Map<String, dynamic> validateForRegistration(
    String email, 
    List<String> existingEmails
  ) {
    // Primero validar formato y reglas
    final Map<String, dynamic> validation = validate(email);
    if (!(validation['isValid'] ?? true)) {
      return validation;
    }
    
    // Buscar emails similares
    for (final String existingEmail in existingEmails) {
      if (areSimilarEmails(email, existingEmail)) {
        return {
          'isValid': false,
          'error': 'Ya existe una cuenta con el email $existingEmail. '
                   'No se permite crear múltiples cuentas con el mismo nombre de email.',
          'similarEmail': existingEmail
        };
      }
    }
    
    return {'isValid': true};
  }
}
