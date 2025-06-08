import 'package:flutter/material.dart';

class ChatInputBox extends StatefulWidget {
  const ChatInputBox({super.key});

  @override
  State<ChatInputBox> createState() => _ChatInputBoxState();
}

class _ChatInputBoxState extends State<ChatInputBox> {
  final TextEditingController _controller = TextEditingController();
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() {
      setState(() {
        _hasText = _controller.text.trim().isNotEmpty;
      });
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        child: Row(
          children: [
            // Campo de texto expandido
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  color: const Color(0xFFFFC0CB).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(25),
                  border: Border.all(
                    color: Colors.grey[300]!,
                    width: 1,
                  ),
                ),
                child: Row(
                  children: [
                    // Botón de adjuntar
                    IconButton(
                      icon: Icon(
                        Icons.attach_file_rounded,
                        color: Colors.grey[600],
                        size: 20,
                      ),
                      onPressed: () {
                        // Función para adjuntar archivos
                      },
                    ),

                    // Campo de texto
                    Expanded(
                      child: TextField(
                        controller: _controller,
                        maxLines: null,
                        textCapitalization: TextCapitalization.sentences,
                        decoration: const InputDecoration(
                          hintText: 'Escribe tu pregunta...',
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.symmetric(
                            horizontal: 0,
                            vertical: 12,
                          ),
                          hintStyle: TextStyle(
                            color: Colors.grey,
                            fontSize: 14,
                          ),
                        ),
                        style: const TextStyle(
                          fontSize: 14,
                          color: Color(0xFF2C3E50),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(width: 12),

            // Botón de enviar
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              child: Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  gradient: _hasText
                      ? const LinearGradient(
                          colors: [
                            Color(0xFFE91E63), // Rosa
                            Color(0xFFFF69B4), // Rosa más claro
                          ],
                        )
                      : null,
                  color: _hasText ? null : Colors.grey[400],
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: _hasText
                      ? [
                          BoxShadow(
                            color:
                                const Color(0xFFE91E63).withValues(alpha: 0.3),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ]
                      : null,
                ),
                child: IconButton(
                  icon: const Icon(
                    Icons.send_rounded,
                    color: Colors.white,
                    size: 20,
                  ),
                  onPressed: _hasText
                      ? () {
                          // Función para enviar mensaje
                          final text = _controller.text.trim();
                          if (text.isNotEmpty) {
                            // Aquí iría la lógica para enviar el mensaje
                            //print('Enviando: $text');
                            _controller.clear();
                          }
                        }
                      : null,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
