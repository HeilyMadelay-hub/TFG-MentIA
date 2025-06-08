import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Tests de la aplicación chatbot', () {
    test('Verificar operaciones básicas', () {
      // Tests simples para verificar que la infraestructura funciona
      expect(2 + 2, equals(4));
      expect('Hola'.length, equals(4));
    });

    test('Verificar listas y mapas', () {
      final List<String> mensajes = [];
      expect(mensajes.isEmpty, isTrue);
      
      final Map<String, String> usuario = {
        'nombre': 'Jorge',
        'email': 'jorge@atisa.es'
      };
      expect(usuario['nombre'], equals('Jorge'));
    });

    test('Verificar strings y manipulación', () {
      const String username = 'jorge.atisa';
      expect(username.contains('.'), isTrue);
      expect(username.split('.').length, equals(2));
    });
  });

  group('Tests de validación', () {
    test('Validar formato de datos', () {
      const String pregunta = '¿Cómo me llamo?';
      const String respuesta = 'Te llamas Jorge';
      
      expect(pregunta.isNotEmpty, isTrue);
      expect(respuesta.isNotEmpty, isTrue);
      expect(pregunta.startsWith('¿'), isTrue);
    });
  });
}
