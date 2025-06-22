import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:async';
import '../services/auth_service.dart';
import '../services/api_service.dart';

class ChangeEmailValidationScreen extends StatefulWidget {
  final String newEmail;
  
  const ChangeEmailValidationScreen({
    Key? key,
    required this.newEmail,
  }) : super(key: key);

  @override
  State<ChangeEmailValidationScreen> createState() => _ChangeEmailValidationScreenState();
}

enum EmailValidationStatus {
  idle,
  validating,
  invalid,
  valid,
  verifyingCode,
  success,
  error
}

class _ChangeEmailValidationScreenState extends State<ChangeEmailValidationScreen> {
  EmailValidationStatus _status = EmailValidationStatus.validating;
  Timer? _validationTimer;
  int _secondsElapsed = 0;
  String? _errorMessage;
  String? _errorDetails;
  String? _technicalReason;
  String? _token;
  final _codeController = TextEditingController();
  bool _isVerifyingCode = false;
  
  @override
  void initState() {
    super.initState();
    _validateEmail();
  }
  
  @override
  void dispose() {
    _validationTimer?.cancel();
    _codeController.dispose();
    super.dispose();
  }
  
  Future<void> _validateEmail() async {
    setState(() {
      _status = EmailValidationStatus.validating;
      _secondsElapsed = 0;
      _errorMessage = null;
    });
    
    // Mostrar contador de 5 segundos
    _validationTimer = Timer.periodic(Duration(seconds: 1), (timer) {
      setState(() {
        _secondsElapsed++;
        if (_secondsElapsed >= 5) {
          timer.cancel();
        }
      });
    });
    
    try {
      final response = await ApiService().changeEmailWithValidation(widget.newEmail);
      
      _validationTimer?.cancel();
      
      if (response['status'] == 'verification_sent') {
        // Email válido - mostrar campo para código
        setState(() {
          _status = EmailValidationStatus.valid;
          _token = response['token'];
        });
      }
      
    } catch (e) {
      _validationTimer?.cancel();
      
      final error = e.toString();
      
      if (error.contains('email_not_valid')) {
        setState(() {
          _status = EmailValidationStatus.invalid;
          
          // Extraer información del error
          if (error.contains('message":')) {
            final startMsg = error.indexOf('message":"') + 10;
            final endMsg = error.indexOf('"', startMsg);
            if (endMsg > startMsg) {
              _errorMessage = error.substring(startMsg, endMsg);
            }
          }
          
          if (error.contains('details":"')) {
            final startDetails = error.indexOf('details":"') + 10;
            final endDetails = error.indexOf('"', startDetails);
            if (endDetails > startDetails) {
              _errorDetails = error.substring(startDetails, endDetails);
            }
          }
          
          if (error.contains('technical_reason":"')) {
            final startReason = error.indexOf('technical_reason":"') + 19;
            final endReason = error.indexOf('"', startReason);
            if (endReason > startReason) {
              _technicalReason = error.substring(startReason, endReason);
            }
          }
          
          _errorMessage = _errorMessage ?? 'El email ingresado no existe o no puede recibir correos';
          _errorDetails = _errorDetails ?? 'No se pudo verificar que el email pueda recibir correos';
        });
      } else if (error.contains('disposable_email')) {
        setState(() {
          _status = EmailValidationStatus.invalid;
          _errorMessage = 'No se permiten emails temporales o desechables';
          _errorDetails = 'El dominio de este email es conocido como temporal';
        });
      } else if (error.contains('email_already_exists')) {
        setState(() {
          _status = EmailValidationStatus.invalid;
          _errorMessage = 'Este email ya está registrado';
          _errorDetails = 'El email pertenece a otra cuenta';
        });
      } else {
        setState(() {
          _status = EmailValidationStatus.error;
          _errorMessage = 'Error al validar el email';
          _errorDetails = error;
        });
      }
    }
  }
  
  Future<void> _verifyCode() async {
    if (_codeController.text.length != 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('El código debe tener 6 dígitos'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }
    
    setState(() {
      _isVerifyingCode = true;
    });
    
    try {
      final response = await ApiService().verifyEmailChangeCode(
        token: _token!,
        code: _codeController.text,
      );
      
      if (response['status'] == 'success') {
        setState(() {
          _status = EmailValidationStatus.success;
        });
        
        // Recargar datos del usuario
        await AuthService().refreshUserData();
        
        // Esperar un momento y cerrar
        Future.delayed(Duration(seconds: 2), () {
          Navigator.of(context).pop(true);
        });
      }
    } catch (e) {
      setState(() {
        _isVerifyingCode = false;
      });
      
      String errorMsg = 'Error al verificar el código';
      if (e.toString().contains('incorrecto')) {
        errorMsg = 'Código incorrecto';
      } else if (e.toString().contains('expirado')) {
        errorMsg = 'El código ha expirado';
      }
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(errorMsg),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF6B4CE6),
              Color(0xFF8B5CF6),
              Color(0xFF7C3AED),
            ],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Header
              Padding(
                padding: EdgeInsets.all(16),
                child: Row(
                  children: [
                    IconButton(
                      icon: Icon(Icons.close, color: Colors.white),
                      onPressed: () => Navigator.pop(context),
                    ),
                    Expanded(
                      child: Text(
                        'Cambio de Email',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                    SizedBox(width: 48), // Balance para el botón de cerrar
                  ],
                ),
              ),
              
              // Contenido
              Expanded(
                child: Center(
                  child: SingleChildScrollView(
                    padding: EdgeInsets.all(24),
                    child: _buildContent(),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildContent() {
    switch (_status) {
      case EmailValidationStatus.validating:
        return _buildValidatingStatus();
      case EmailValidationStatus.invalid:
        return _buildInvalidStatus();
      case EmailValidationStatus.valid:
        return _buildCodeEntryStatus();
      case EmailValidationStatus.success:
        return _buildSuccessStatus();
      default:
        return _buildErrorStatus();
    }
  }
  
  Widget _buildValidatingStatus() {
    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(
              valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF6B4CE6)),
              strokeWidth: 3,
            ),
            SizedBox(height: 24),
            Text(
              'Validando email...',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Color(0xFF2C3E50),
              ),
            ),
            SizedBox(height: 12),
            Text(
              'Verificando que el email pueda recibir correos',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[600],
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 24),
            Container(
              width: 200,
              child: LinearProgressIndicator(
                value: _secondsElapsed / 5,
                backgroundColor: Colors.grey[300],
                valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF6B4CE6)),
              ),
            ),
            SizedBox(height: 8),
            Text(
              '${5 - _secondsElapsed} segundos restantes',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildInvalidStatus() {
    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.error_outline,
                color: Colors.red,
                size: 48,
              ),
            ),
            SizedBox(height: 24),
            Text(
              'Email No Válido',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.red.shade700,
              ),
            ),
            SizedBox(height: 16),
            Container(
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.red.shade200),
              ),
              child: Column(
                children: [
                  Text(
                    widget.newEmail,
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 16,
                      color: Colors.red.shade700,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
            if (_errorMessage != null) ...[
              SizedBox(height: 20),
              Text(
                _errorMessage!,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                  color: Color(0xFF2C3E50),
                ),
                textAlign: TextAlign.center,
              ),
            ],
            if (_errorDetails != null) ...[
              SizedBox(height: 12),
              Text(
                _errorDetails!,
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.grey[600],
                ),
                textAlign: TextAlign.center,
              ),
            ],
            SizedBox(height: 24),
            _buildPossibleReasons(),
            SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Color(0xFF6B4CE6),
                  padding: EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: Text(
                  'Entendido',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildPossibleReasons() {
    Map<String, List<String>> reasonsByType = {
      'no_mx_records': [
        'El dominio no tiene servidores de correo',
        'El dominio no existe',
        'Error de escritura en el dominio',
      ],
      'recipient_not_found': [
        'La dirección de email no existe',
        'Error de escritura en el usuario',
        'La cuenta fue eliminada',
      ],
      'recipient_refused': [
        'El servidor rechazó el email',
        'La bandeja está llena',
        'El email está bloqueado',
      ],
      'delivery_timeout': [
        'El servidor no respondió a tiempo',
        'Problemas de conexión',
        'Servidor sobrecargado',
      ],
      'domain_not_found': [
        'El dominio no existe',
        'Error de escritura en el dominio',
        'Dominio no registrado',
      ],
    };
    
    List<String> reasons = reasonsByType[_technicalReason] ?? [
      'El email no existe',
      'Error de escritura en el email',
      'El dominio no recibe correos',
      'Es un email temporal o desechable',
    ];
    
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Posibles razones:',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: Color(0xFF2C3E50),
            ),
          ),
          SizedBox(height: 12),
          ...reasons.map((reason) => Padding(
            padding: EdgeInsets.only(bottom: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.circle, size: 6, color: Colors.grey),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    reason,
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey[700],
                    ),
                  ),
                ),
              ],
            ),
          )).toList(),
        ],
      ),
    );
  }
  
  Widget _buildCodeEntryStatus() {
    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: Colors.green.shade50,
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.email_outlined,
                color: Colors.green,
                size: 48,
              ),
            ),
            SizedBox(height: 24),
            Text(
              'Email Válido ✓',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.green.shade700,
              ),
            ),
            SizedBox(height: 16),
            Text(
              'Hemos enviado un código de verificación a:',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[600],
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 8),
            Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Color(0xFF6B4CE6).withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                widget.newEmail,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF6B4CE6),
                  fontSize: 16,
                ),
              ),
            ),
            SizedBox(height: 32),
            Text(
              'Ingresa el código de 6 dígitos:',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w500,
                color: Color(0xFF2C3E50),
              ),
            ),
            SizedBox(height: 16),
            TextField(
              controller: _codeController,
              textAlign: TextAlign.center,
              keyboardType: TextInputType.number,
              maxLength: 6,
              style: TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.bold,
                letterSpacing: 8,
                color: Color(0xFF6B4CE6),
              ),
              decoration: InputDecoration(
                counterText: '',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: Color(0xFF6B4CE6), width: 2),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: Color(0xFF6B4CE6), width: 2),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: Colors.grey.shade300, width: 2),
                ),
                filled: true,
                fillColor: Colors.grey.shade50,
              ),
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(6),
              ],
            ),
            SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isVerifyingCode ? null : _verifyCode,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Color(0xFF6B4CE6),
                  padding: EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: _isVerifyingCode
                    ? SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2,
                        ),
                      )
                    : Text(
                        'Verificar Código',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
              ),
            ),
            SizedBox(height: 16),
            Text(
              'El código expira en 5 minutos',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildSuccessStatus() {
    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                color: Colors.green.shade50,
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.check_circle,
                color: Colors.green,
                size: 64,
              ),
            ),
            SizedBox(height: 24),
            Text(
              '¡Email Actualizado!',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.green.shade700,
              ),
            ),
            SizedBox(height: 16),
            Text(
              'Tu email ha sido actualizado exitosamente',
              style: TextStyle(
                fontSize: 16,
                color: Colors.grey[600],
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 12),
            Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.green.shade50,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                widget.newEmail,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.green.shade700,
                  fontSize: 16,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildErrorStatus() {
    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline,
              color: Colors.orange,
              size: 64,
            ),
            SizedBox(height: 24),
            Text(
              'Error',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.orange.shade700,
              ),
            ),
            SizedBox(height: 16),
            Text(
              _errorMessage ?? 'Ocurrió un error inesperado',
              style: TextStyle(
                fontSize: 16,
                color: Colors.grey[600],
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              style: ElevatedButton.styleFrom(
                backgroundColor: Color(0xFF6B4CE6),
              ),
              child: Text('Cerrar'),
            ),
          ],
        ),
      ),
    );
  }
}
