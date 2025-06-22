import 'package:flutter/material.dart';
import '../services/email_verification_service.dart';

class EmailChangeConfirmationDialog extends StatefulWidget {
  final String oldEmail;
  final String? newEmail;
  final String? verificationToken;
  final VoidCallback? onVerified;

  const EmailChangeConfirmationDialog({
    Key? key,
    required this.oldEmail,
    this.newEmail,
    this.verificationToken,
    this.onVerified,
  }) : super(key: key);

  @override
  State<EmailChangeConfirmationDialog> createState() => _EmailChangeConfirmationDialogState();
}

class _EmailChangeConfirmationDialogState extends State<EmailChangeConfirmationDialog> {
  bool _isVerifying = false;
  
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      title: Row(
        children: [
          Icon(
            Icons.email_outlined,
            color: Theme.of(context).primaryColor,
            size: 28,
          ),
          const SizedBox(width: 12),
          const Text(
            'Confirmación Pendiente',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.amber.shade50,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: Colors.amber.shade200,
                width: 1,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.info_outline,
                  color: Colors.amber.shade700,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Se ha enviado un email de confirmación',
                    style: TextStyle(
                      color: Colors.amber.shade800,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Email enviado a:',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey,
            ),
          ),
          const SizedBox(height: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.mail,
                  size: 18,
                  color: Colors.grey,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    widget.oldEmail,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (widget.newEmail != null) ...[
            const SizedBox(height: 12),
            const Text(
              'Nuevo email:',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Theme.of(context).primaryColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.arrow_forward,
                    size: 18,
                    color: Theme.of(context).primaryColor,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      widget.newEmail!,
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                        color: Theme.of(context).primaryColor,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.blue.shade50,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.security,
                      color: Colors.blue.shade700,
                      size: 18,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Por tu seguridad',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Colors.blue.shade700,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  '• Revisa tu bandeja de entrada\n'
                  '• Haz clic en el enlace "Sí, fui yo"\n'
                  '• El enlace expira en 24 horas',
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.blue.shade700,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: _isVerifying ? null : () => Navigator.of(context).pop(),
          child: const Text('Entendido'),
        ),
        // Botón de verificación manual (para testing)
        if (widget.verificationToken != null)
          ElevatedButton(
            onPressed: _isVerifying ? null : _verifyNow,
            child: _isVerifying
                ? SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                : Text('Verificar ahora'),
          ),
      ],
    );
  }
  
  Future<void> _verifyNow() async {
    if (widget.verificationToken == null) return;
    
    setState(() {
      _isVerifying = true;
    });
    
    // Extraer solo el UUID del token si es necesario
    String tokenToSend = widget.verificationToken!;
    
    // Si el token parece ser un UUID (36 caracteres)
    final uuidRegex = RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');
    if (tokenToSend.length == 36 && uuidRegex.hasMatch(tokenToSend)) {
      // Es un UUID, enviarlo directamente
      print('📌 Enviando UUID directo: $tokenToSend');
    }
    
    final success = await EmailVerificationService.verifyManualToken(
      context,
      tokenToSend,
    );
    
    setState(() {
      _isVerifying = false;
    });
    
    if (success) {
      Navigator.of(context).pop();
      widget.onVerified?.call();
    }
  }
}

// Función helper para mostrar el diálogo
void showEmailChangeConfirmationDialog(
  BuildContext context, {
  required String oldEmail,
  String? newEmail,
  String? verificationToken,
  VoidCallback? onVerified,
}) {
  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (context) => EmailChangeConfirmationDialog(
      oldEmail: oldEmail,
      newEmail: newEmail,
      verificationToken: verificationToken,
      onVerified: onVerified,
    ),
  );
}
