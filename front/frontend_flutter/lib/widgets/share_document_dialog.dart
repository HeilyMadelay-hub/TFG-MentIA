import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/document_service.dart';
import '../services/auth_service.dart';
import '../models/document.dart';

class ShareDocumentDialog extends StatefulWidget {
  final Document document;
  final VoidCallback? onShared;

  const ShareDocumentDialog({
    super.key,
    required this.document,
    this.onShared,
  });

  @override
  State<ShareDocumentDialog> createState() => _ShareDocumentDialogState();
}

class _ShareDocumentDialogState extends State<ShareDocumentDialog> {
  final TextEditingController _idsController = TextEditingController();
  final DocumentService _documentService = DocumentService();
  final AuthService _authService = AuthService();
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void dispose() {
    _idsController.dispose();
    super.dispose();
  }

  List<int> _parseUserIds(String input) {
    if (input.trim().isEmpty) return [];
    
    try {
      return input
          .split(',')
          .map((id) => id.trim())
          .where((id) => id.isNotEmpty)
          .map((id) => int.parse(id))
          .toSet() // Eliminar duplicados
          .toList();
    } catch (e) {
      throw FormatException('IDs inválidos. Use números separados por comas');
    }
  }

  Future<void> _shareDocument() async {
    setState(() {
      _errorMessage = null;
    });

    // Validar entrada
    List<int> userIds;
    try {
      userIds = _parseUserIds(_idsController.text);
      
      if (userIds.isEmpty) {
        setState(() {
          _errorMessage = 'Debe especificar al menos un ID de usuario';
        });
        return;
      }
      
      // Validar que no intente compartir consigo mismo
      final currentUserId = _authService.currentUser?.id;
      if (currentUserId != null && userIds.contains(currentUserId)) {
        setState(() {
          _errorMessage = '¿Para qué quieres compartir el documento contigo mismo?';
        });
        return;
      }
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
      });
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      final response = await _documentService.shareDocument(
        documentId: widget.document.id,
        userIds: userIds,
      );

      if (mounted) {
        // Interpretar la respuesta del backend
        final bool success = response['success'] ?? false;
        final String message = response['message'] ?? '';
        final List alreadyShared = response['already_shared'] ?? [];
        final Map<String, dynamic> summary = response['share_summary'] ?? {};
        
        // Determinar el color y el ícono según el resultado
        Color snackBarColor;
        String displayMessage;
        
        if (summary['new_shares'] > 0) {
          // Se compartieron nuevos documentos
          snackBarColor = Colors.green;
          displayMessage = message;
        } else if (summary['already_shared'] > 0 && summary['new_shares'] == 0) {
          // Todos ya tenían acceso
          snackBarColor = Colors.orange;
          displayMessage = message;
        } else {
          // Error o ningún cambio
          snackBarColor = Colors.red;
          displayMessage = 'No se pudo compartir el documento';
        }
        
        // Mostrar mensaje apropiado
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(displayMessage),
            backgroundColor: snackBarColor,
            duration: const Duration(seconds: 4),
          ),
        );
        
        // Si hay usuarios que ya tenían acceso, mostrar detalles
        if (alreadyShared.isNotEmpty && summary['new_shares'] == 0) {
          // Mostrar diálogo informativo
          Navigator.of(context).pop(); // Cerrar diálogo de compartir
          
          showDialog(
            context: context,
            builder: (BuildContext context) {
              return AlertDialog(
                title: Row(
                  children: [
                    Icon(Icons.info_outline, color: Colors.orange),
                    const SizedBox(width: 8),
                    const Text('Información'),
                  ],
                ),
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Los siguientes usuarios ya tenían acceso:'),
                    const SizedBox(height: 12),
                    ...alreadyShared.map((user) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Icon(Icons.person, size: 20, color: Colors.grey),
                          const SizedBox(width: 8),
                          Text('${user['username']} (ID: ${user['id']})',
                            style: const TextStyle(fontWeight: FontWeight.w500),
                          ),
                        ],
                      ),
                    )).toList(),
                  ],
                ),
                actions: [
                  TextButton(
                    child: const Text('Entendido'),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              );
            },
          );
        } else {
          Navigator.of(context).pop();
        }
        
        widget.onShared?.call();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          // Extraer mensaje de error más específico
          String errorMsg = e.toString();
          
          // Log para debug
          debugPrint('Error al compartir: $errorMsg');
          
          // Buscar el mensaje de error en diferentes formatos
          if (errorMsg.contains('¿Para qué quieres compartir el documento contigo mismo?')) {
            _errorMessage = '¿Para qué quieres compartir el documento contigo mismo?';
          } else if (errorMsg.contains('detail:')) {
            // Extraer el mensaje después de 'detail:'
            _errorMessage = errorMsg.split('detail:').last.trim();
          } else if (errorMsg.contains('Los siguientes IDs de usuario no existen')) {
            // Extraer el mensaje completo si está presente
            final match = RegExp(r'Los siguientes IDs de usuario no existen[^}]+').firstMatch(errorMsg);
            _errorMessage = match?.group(0) ?? 'Error: IDs de usuario no válidos';
          } else if (errorMsg.contains('403')) {
            _errorMessage = 'No tienes permisos para compartir este documento';
          } else if (errorMsg.contains('404')) {
            _errorMessage = 'Documento no encontrado';
          } else {
            _errorMessage = 'Error al compartir documento. Verifique los IDs ingresados.';
          }
          
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Container(
        padding: const EdgeInsets.all(24),
        constraints: const BoxConstraints(maxWidth: 400),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Compartir: ${widget.document.title}',
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Compartir con usuarios:',
              style: TextStyle(fontSize: 16),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _idsController,
              decoration: InputDecoration(
                hintText: 'Ejemplo: 2, 3, 4',
                helperText: 'IDs de usuarios (separados por comas)',
                prefixIcon: const Icon(Icons.people),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                errorText: _errorMessage,
                enabled: !_isLoading,
              ),
              keyboardType: TextInputType.number,
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[0-9,\s]')),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.blue.shade200),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.info_outline, color: Colors.blue.shade700),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Los usuarios compartidos podrán ver este documento',
                          style: TextStyle(
                            color: Colors.blue.shade700,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ],
                  ),
                  if (_authService.currentUser != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      'Tu ID de usuario: ${_authService.currentUser!.id}',
                      style: TextStyle(
                        color: Colors.blue.shade700,
                        fontSize: 12,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: _isLoading ? null : () => Navigator.of(context).pop(),
                  child: const Text('Cancelar'),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: _isLoading ? null : _shareDocument,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF6B4CE6),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 24,
                      vertical: 12,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  child: _isLoading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        )
                      : const Text('Compartir'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
