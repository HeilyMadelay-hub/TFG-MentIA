import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/auth_service.dart';
import 'services/token_refresh_service.dart';
import 'providers/documents_provider.dart';
import 'providers/dashboard_provider.dart';
import 'screens/home_screen.dart';
import 'screens/register_screen.dart';
import 'screens/login_screen.dart';
import 'screens/reset_password_screen.dart';
import 'screens/forgot_password_screen.dart';
import 'screens/email_verification_screen.dart';
import 'utils/email_validator.dart';
import 'utils/error_interceptor.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthService()),
        ChangeNotifierProvider(create: (_) => DocumentsProvider()),
        ChangeNotifierProvider(create: (_) => DashboardProvider()),
      ],
      child: const TokenRefreshWrapper(
        child: MyApp(),
      ),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ErrorInterceptorProvider(
      child: MaterialApp(
      title: 'MentIA',
      debugShowCheckedModeBanner: false,
      scaffoldMessengerKey: context.read<DocumentsProvider>().messengerKey,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFE91E63)),
        useMaterial3: true,
        fontFamily: 'Roboto',
      ),
      onGenerateRoute: (settings) {
        // Manejar rutas con parámetros
        final uri = Uri.parse(settings.name ?? '/');

        if (uri.path == '/' || settings.name == '/') {
          // Verificar si la URL actual tiene rutas específicas
          final currentPath = Uri.base.path;
          final currentToken = Uri.base.queryParameters['token'];

          // Si estamos en la ruta de verificación de email
          if (currentPath.contains('verify-email') && currentToken != null) {
            return MaterialPageRoute(
              builder: (context) =>
                  EmailVerificationScreen(token: currentToken),
            );
          }
          // Si estamos en la ruta de reset password
          else if (currentPath.contains('reset_password_screen') &&
              currentToken != null) {
            return MaterialPageRoute(
              builder: (context) => ResetPasswordScreen(token: currentToken),
            );
          }

          return MaterialPageRoute(
            builder: (context) => const AuthWrapper(),
          );
        } else if (uri.path == '/register') {
          return MaterialPageRoute(
            builder: (context) => const RegisterScreen(),
          );
        } else if (uri.path == '/forgot-password') {
          return MaterialPageRoute(
            builder: (context) => const ForgotPasswordScreen(),
          );
        } else if (uri.path == '/reset_password_screen') {
          final token = uri.queryParameters['token'];
          return MaterialPageRoute(
            builder: (context) => ResetPasswordScreen(token: token),
          );
        } else if (uri.path == '/verify-email') {
          final token = uri.queryParameters['token'];
          return MaterialPageRoute(
            builder: (context) => EmailVerificationScreen(token: token),
          );
        } else if (uri.path == '/home') {
          return MaterialPageRoute(
            builder: (context) => const HomeScreen(),
          );
        }

        // Default route
        return MaterialPageRoute(
          builder: (context) => const AuthWrapper(),
        );
      },
      initialRoute: '/',
      ),
    );
  }
}

class AuthWrapper extends StatefulWidget {
  const AuthWrapper({super.key});

  @override
  State<AuthWrapper> createState() => _AuthWrapperState();
}

class _AuthWrapperState extends State<AuthWrapper> {
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadCurrentUser();
  }

  Future<void> _loadCurrentUser() async {
    try {
      await AuthService().loadCurrentUser();
    } catch (e) {
      // Ignorar errores, el usuario simplemente no está autenticado
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    return Consumer<AuthService>(
      builder: (context, authService, _) {
        if (authService.isAuthenticated) {
          return const HomeScreen();
        } else {
          return const LoginScreen();
        }
      },
    );
  }
}

// LoginScreen ya está en screens/login_screen.dart
