import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/token_refresh_service.dart';

/// Widget que muestra el estado de la sesión y renovación de tokens
class SessionStatusWidget extends StatefulWidget {
  const SessionStatusWidget({Key? key}) : super(key: key);

  @override
  State<SessionStatusWidget> createState() => _SessionStatusWidgetState();
}

class _SessionStatusWidgetState extends State<SessionStatusWidget> {
  final TokenRefreshService _tokenService = TokenRefreshService();
  bool _isRefreshing = false;

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthService>(
      builder: (context, authService, child) {
        if (!authService.isAuthenticated) {
          return const SizedBox.shrink();
        }

        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: _isRefreshing ? Colors.orange : Colors.green,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                _isRefreshing ? Icons.refresh : Icons.check_circle,
                size: 16,
                color: Colors.white,
              ),
              const SizedBox(width: 4),
              Text(
                _isRefreshing ? 'Renovando sesión...' : 'Sesión activa',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

/// Dialog para mostrar cuando la sesión está por expirar
class SessionExpiringDialog extends StatelessWidget {
  final VoidCallback onRenew;
  final VoidCallback onLogout;

  const SessionExpiringDialog({
    Key? key,
    required this.onRenew,
    required this.onLogout,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.warning_amber_rounded, color: Colors.orange),
          SizedBox(width: 8),
          Text('Sesión por expirar'),
        ],
      ),
      content: const Text(
        'Tu sesión está por expirar. ¿Deseas continuar trabajando?',
      ),
      actions: [
        TextButton(
          onPressed: onLogout,
          child: const Text('Cerrar sesión'),
        ),
        ElevatedButton(
          onPressed: onRenew,
          child: const Text('Continuar'),
        ),
      ],
    );
  }
}

/// Snackbar para mostrar errores de sesión
void showSessionErrorSnackBar(BuildContext context, String message) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Row(
        children: [
          const Icon(Icons.error_outline, color: Colors.white),
          const SizedBox(width: 8),
          Expanded(
            child: Text(message),
          ),
        ],
      ),
      backgroundColor: Colors.red,
      behavior: SnackBarBehavior.floating,
      action: SnackBarAction(
        label: 'Reintentar',
        textColor: Colors.white,
        onPressed: () {
          // Intentar renovar manualmente
          TokenRefreshService().validateAndRefreshIfNeeded();
        },
      ),
    ),
  );
}

/// Widget wrapper que maneja notificaciones de sesión
class SessionAwareScreen extends StatefulWidget {
  final Widget child;
  
  const SessionAwareScreen({
    Key? key,
    required this.child,
  }) : super(key: key);

  @override
  State<SessionAwareScreen> createState() => _SessionAwareScreenState();
}

class _SessionAwareScreenState extends State<SessionAwareScreen> {
  final TokenRefreshService _tokenService = TokenRefreshService();
  final AuthService _authService = AuthService();

  @override
  void initState() {
    super.initState();
    _checkSessionPeriodically();
  }

  void _checkSessionPeriodically() {
    // Verificar cada 5 minutos si el token está por expirar
    Future.delayed(const Duration(minutes: 5), () {
      if (mounted && _authService.isAuthenticated) {
        _checkTokenExpiry();
        _checkSessionPeriodically(); // Continuar verificando
      }
    });
  }

  Future<void> _checkTokenExpiry() async {
    // Aquí podrías verificar si el token expira en menos de 2 minutos
    // y mostrar un diálogo de advertencia
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        widget.child,
        // Indicador de estado en la esquina
        const Positioned(
          top: 40,
          right: 16,
          child: SessionStatusWidget(),
        ),
      ],
    );
  }
}

/// Ejemplo de uso en una pantalla
class ExampleUsageScreen extends StatelessWidget {
  const ExampleUsageScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return SessionAwareScreen(
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Mi App'),
          actions: const [
            // El indicador de sesión se muestra automáticamente
          ],
        ),
        body: const Center(
          child: Text('Contenido de la pantalla'),
        ),
      ),
    );
  }
}
