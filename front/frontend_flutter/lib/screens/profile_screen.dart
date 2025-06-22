import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import '../models/user.dart';
import '../services/auth_service.dart';
import '../widgets/email_change_dialog.dart';
import 'change_email_validation_screen.dart';
import '../utils/responsive_utils.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _usernameController;
  late TextEditingController _emailController;
  late TextEditingController _currentPasswordController;
  late TextEditingController _newPasswordController;
  late TextEditingController _confirmPasswordController;

  bool _isEditing = false;
  bool _isLoading = false;
  bool _showPasswordFields = false;
  bool _showCurrentPassword = false;
  bool _showNewPassword = false;
  bool _showConfirmPassword = false;

  // Método para verificar si el usuario es Ivan
  bool _isUserIvan() {
    final user = AuthService().currentUser;
    return user?.username.toLowerCase() == 'ivan';
  }

  @override
  void initState() {
    super.initState();
    final user = AuthService().currentUser;
    _usernameController = TextEditingController(text: user?.username ?? '');
    _emailController = TextEditingController(text: user?.email ?? '');
    _currentPasswordController = TextEditingController();
    _newPasswordController = TextEditingController();
    _confirmPasswordController = TextEditingController();
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _emailController.dispose();
    _currentPasswordController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final user = AuthService().currentUser;

    return ResponsiveBuilder(
      builder: (context, sizingInfo) {
        return Scaffold(
          backgroundColor: Colors.grey[50],
          body: SingleChildScrollView(
            child: Column(
              children: [
                // Header con información del usuario
                _buildProfileHeader(user, sizingInfo),

                SizedBox(height: sizingInfo.spacing * 2),

                // Contenedor con ancho máximo para desktop
                ConstrainedBox(
                  constraints: BoxConstraints(
                    maxWidth: sizingInfo.isDesktop ? 800 : double.infinity,
                  ),
                  child: Column(
                    children: [
                      // Información personal
                      _buildPersonalInfoSection(user, sizingInfo),

                      SizedBox(height: sizingInfo.spacing * 2),

                      // Opciones adicionales
                      _buildAdditionalOptionsSection(sizingInfo),

                      SizedBox(height: sizingInfo.spacing * 2),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildProfileHeader(User? user, ResponsiveInfo sizingInfo) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF6B4CE6),
            Color(0xFFE91E63),
            Color(0xFF2196F3),
          ],
        ),
        borderRadius: BorderRadius.only(
          bottomLeft: Radius.circular(sizingInfo.borderRadius),
          bottomRight: Radius.circular(sizingInfo.borderRadius),
        ),
      ),
      child: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(sizingInfo.padding),
          child: Column(
            children: [
              // Avatar y badge de admin
              Stack(
                children: [
                  Container(
                    width: sizingInfo.isSmallDevice ? 80 : 100,
                    height: sizingInfo.isSmallDevice ? 80 : 100,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(50),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.1),
                          blurRadius: 20,
                          offset: const Offset(0, 10),
                        ),
                      ],
                    ),
                    child: Center(
                      child: Text(
                        user?.username.substring(0, 1).toUpperCase() ?? 'U',
                        style: TextStyle(
                          fontSize: sizingInfo.fontSize.header,
                          fontWeight: FontWeight.bold,
                          color: user?.isAdmin == true
                              ? const Color(0xFF6B4CE6)
                              : Colors.grey[700],
                        ),
                      ),
                    ),
                  ),
                  if (user?.isAdmin == true)
                    Positioned(
                      bottom: 5,
                      right: 5,
                      child: Container(
                        padding: EdgeInsets.all(sizingInfo.iconPadding / 2),
                        decoration: const BoxDecoration(
                          color: Color(0xFFFFD700),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          Icons.admin_panel_settings,
                          color: Colors.white,
                          size: sizingInfo.fontSize.smallIcon,
                        ),
                      ),
                    ),
                ],
              ),

              SizedBox(height: sizingInfo.spacing),

              // Nombre y email
              Text(
                user?.username ?? 'Usuario',
                style: TextStyle(
                  fontSize: sizingInfo.fontSize.title,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              SizedBox(height: sizingInfo.spacing / 2),
              Text(
                user?.email ?? '',
                style: TextStyle(
                  fontSize: sizingInfo.fontSize.body,
                  color: Colors.white.withValues(alpha: 0.9),
                ),
              ),
              SizedBox(height: sizingInfo.spacing),

              // Role badge
              Container(
                padding: EdgeInsets.symmetric(
                  horizontal: sizingInfo.cardPadding,
                  vertical: sizingInfo.spacing / 2,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      user?.isAdmin == true
                          ? Icons.admin_panel_settings
                          : Icons.person,
                      color: Colors.white,
                      size: sizingInfo.fontSize.smallIcon,
                    ),
                    SizedBox(width: sizingInfo.spacing / 2),
                    Text(
                      user?.isAdmin == true ? 'Administrador' : 'Usuario',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w500,
                        fontSize: sizingInfo.fontSize.caption,
                      ),
                    ),
                  ],
                ),
              ),

              SizedBox(height: sizingInfo.spacing),

              // Fecha de registro
              Text(
                'Miembro desde ${_formatDate(user?.createdAt ?? DateTime.now())}',
                style: TextStyle(
                  fontSize: sizingInfo.fontSize.caption,
                  color: Colors.white.withValues(alpha: 0.8),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPersonalInfoSection(User? user, ResponsiveInfo sizingInfo) {
    return Container(
      margin: EdgeInsets.symmetric(horizontal: sizingInfo.padding),
      padding: EdgeInsets.all(sizingInfo.cardPadding),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Información Personal',
                style: TextStyle(
                  fontSize: sizingInfo.fontSize.sectionTitle,
                  fontWeight: FontWeight.bold,
                  color: const Color(0xFF2C3E50),
                ),
              ),
              _isEditing
                  ? IconButton(
                      icon: Icon(Icons.close, 
                        color: Colors.purple,
                        size: sizingInfo.fontSize.icon,
                      ),
                      onPressed: _isLoading ||
                              !_formKey.currentState!.validate()
                          ? null
                          : () {
                              setState(() {
                                _isEditing = false;
                                // Resetear campos si se cancela la edición
                                _usernameController.text = user?.username ?? '';
                                _emailController.text = user?.email ?? '';
                                _showPasswordFields = false;
                                _formKey.currentState?.reset();
                              });
                            },
                    )
                  : TextButton.icon(
                      onPressed: _isLoading
                          ? null
                          : () {
                              setState(() {
                                _isEditing = true;
                              });
                            },
                      icon: Icon(Icons.edit, size: sizingInfo.fontSize.smallIcon),
                      label: Text('Editar', 
                        style: TextStyle(fontSize: sizingInfo.fontSize.button),
                      ),
                      style: TextButton.styleFrom(
                        foregroundColor: const Color(0xFF6B4CE6),
                      ),
                    ),
            ],
          ),
          SizedBox(height: sizingInfo.spacing * 2),
          Form(
            key: _formKey,
            child: Column(
              children: [
                // Campo de nombre de usuario
                TextFormField(
                  controller: _usernameController,
                  enabled: _isEditing,
                  style: TextStyle(fontSize: sizingInfo.fontSize.body),
                  decoration: InputDecoration(
                    labelText: 'Nombre de usuario',
                    labelStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                    prefixIcon: Icon(Icons.person_outline, size: sizingInfo.fontSize.icon),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                    ),
                    filled: true,
                    fillColor: _isEditing ? null : Colors.grey[100],
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: sizingInfo.cardPadding,
                      vertical: sizingInfo.spacing,
                    ),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'El nombre de usuario es requerido';
                    }
                    if (value.length < 3) {
                      return 'Debe tener al menos 3 caracteres';
                    }
                    return null;
                  },
                ),

                SizedBox(height: sizingInfo.spacing),

                // Campo de email
                TextFormField(
                  controller: _emailController,
                  enabled: _isEditing,
                  keyboardType: TextInputType.emailAddress,
                  style: TextStyle(fontSize: sizingInfo.fontSize.body),
                  decoration: InputDecoration(
                    labelText: 'Correo electrónico',
                    labelStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                    prefixIcon: Icon(Icons.email_outlined, size: sizingInfo.fontSize.icon),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                    ),
                    filled: true,
                    fillColor: _isEditing ? null : Colors.grey[100],
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: sizingInfo.cardPadding,
                      vertical: sizingInfo.spacing,
                    ),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'El correo electrónico es requerido';
                    }
                    if (!value.contains('@')) {
                      return 'El correo debe contener el símbolo @';
                    }
                    // Solo validar que sea @gmail.com si NO es Ivan
                    if (!_isUserIvan() && !value.endsWith('@gmail.com')) {
                      return 'Solo se permiten correos @gmail.com';
                    }
                    if (!RegExp(r'^[\w\-\.]+@([\w\-]+\.)+[\w\-]{2,4}$')
                        .hasMatch(value)) {
                      return 'Ingresa un correo válido';
                    }
                    return null;
                  },
                ),

                if (_isEditing) ...[
                  SizedBox(height: sizingInfo.spacing),

                  // Botón para cambiar contraseña
                  OutlinedButton.icon(
                    onPressed: () {
                      setState(() {
                        _showPasswordFields = !_showPasswordFields;
                        if (!_showPasswordFields) {
                          _currentPasswordController.clear();
                          _newPasswordController.clear();
                          _confirmPasswordController.clear();
                        }
                      });
                    },
                    icon: Icon(Icons.lock_outline, size: sizingInfo.fontSize.icon),
                    label: Text('Cambiar contraseña',
                      style: TextStyle(fontSize: sizingInfo.fontSize.button),
                    ),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF6B4CE6),
                      side: const BorderSide(color: Color(0xFF6B4CE6)),
                      padding: EdgeInsets.symmetric(
                          horizontal: sizingInfo.cardPadding, 
                          vertical: sizingInfo.spacing,
                      ),
                      minimumSize: Size(double.infinity, 48),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                      ),
                    ),
                  ),

                  // Campos de contraseña
                  if (_showPasswordFields) ...[
                    SizedBox(height: sizingInfo.spacing),
                    TextFormField(
                      controller: _currentPasswordController,
                      obscureText: !_showCurrentPassword,
                      style: TextStyle(fontSize: sizingInfo.fontSize.body),
                      decoration: InputDecoration(
                        labelText: 'Contraseña actual',
                        labelStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                        prefixIcon: Icon(Icons.lock_outline, size: sizingInfo.fontSize.icon),
                        suffixIcon: IconButton(
                          icon: Icon(_showCurrentPassword
                              ? Icons.visibility
                              : Icons.visibility_off,
                            size: sizingInfo.fontSize.icon,
                          ),
                          onPressed: () {
                            setState(() {
                              _showCurrentPassword = !_showCurrentPassword;
                            });
                          },
                        ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                        ),
                        contentPadding: EdgeInsets.symmetric(
                          horizontal: sizingInfo.cardPadding,
                          vertical: sizingInfo.spacing,
                        ),
                      ),
                      validator: (value) {
                        if (_showPasswordFields &&
                            (value == null || value.isEmpty)) {
                          return 'Ingresa tu contraseña actual';
                        }
                        return null;
                      },
                    ),
                    SizedBox(height: sizingInfo.spacing),
                    TextFormField(
                      controller: _newPasswordController,
                      obscureText: !_showNewPassword,
                      style: TextStyle(fontSize: sizingInfo.fontSize.body),
                      decoration: InputDecoration(
                        labelText: 'Nueva contraseña',
                        labelStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                        prefixIcon: Icon(Icons.lock_outline, size: sizingInfo.fontSize.icon),
                        suffixIcon: IconButton(
                          icon: Icon(_showNewPassword
                              ? Icons.visibility
                              : Icons.visibility_off,
                            size: sizingInfo.fontSize.icon,
                          ),
                          onPressed: () {
                            setState(() {
                              _showNewPassword = !_showNewPassword;
                            });
                          },
                        ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                        ),
                        contentPadding: EdgeInsets.symmetric(
                          horizontal: sizingInfo.cardPadding,
                          vertical: sizingInfo.spacing,
                        ),
                      ),
                      validator: (value) {
                        if (_showPasswordFields &&
                            (value == null || value.isEmpty)) {
                          return 'Ingresa la nueva contraseña';
                        }
                        if (_showPasswordFields && value!.length < 6) {
                          return 'Debe tener al menos 6 caracteres';
                        }
                        return null;
                      },
                    ),
                    SizedBox(height: sizingInfo.spacing),
                    TextFormField(
                      controller: _confirmPasswordController,
                      obscureText: !_showConfirmPassword,
                      style: TextStyle(fontSize: sizingInfo.fontSize.body),
                      decoration: InputDecoration(
                        labelText: 'Confirmar nueva contraseña',
                        labelStyle: TextStyle(fontSize: sizingInfo.fontSize.body),
                        prefixIcon: Icon(Icons.lock_outline, size: sizingInfo.fontSize.icon),
                        suffixIcon: IconButton(
                          icon: Icon(_showConfirmPassword
                              ? Icons.visibility
                              : Icons.visibility_off,
                            size: sizingInfo.fontSize.icon,
                          ),
                          onPressed: () {
                            setState(() {
                              _showConfirmPassword = !_showConfirmPassword;
                            });
                          },
                        ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                        ),
                        contentPadding: EdgeInsets.symmetric(
                          horizontal: sizingInfo.cardPadding,
                          vertical: sizingInfo.spacing,
                        ),
                      ),
                      validator: (value) {
                        if (_showPasswordFields &&
                            value != _newPasswordController.text) {
                          return 'Las contraseñas no coinciden';
                        }
                        return null;
                      },
                    ),
                  ],

                  SizedBox(height: sizingInfo.spacing * 2),

                  // Botón de guardar
                  SizedBox(
                    width: double.infinity,
                    height: sizingInfo.isSmallDevice ? 44 : 48,
                    child: ElevatedButton(
                      onPressed: _isLoading ? null : _saveProfile,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF6B4CE6),
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                        ),
                      ),
                      child: _isLoading
                          ? SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(
                                color: Colors.white,
                                strokeWidth: 2,
                              ),
                            )
                          : Text(
                              'Guardar Cambios',
                              style: TextStyle(
                                fontSize: sizingInfo.fontSize.button,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAdditionalOptionsSection(ResponsiveInfo sizingInfo) {
    return Container(
      margin: EdgeInsets.symmetric(horizontal: sizingInfo.padding),
      padding: EdgeInsets.all(sizingInfo.cardPadding),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Más Opciones',
            style: TextStyle(
              fontSize: sizingInfo.fontSize.sectionTitle,
              fontWeight: FontWeight.bold,
              color: const Color(0xFF2C3E50),
            ),
          ),
          SizedBox(height: sizingInfo.spacing),
          _buildSettingsItem(
            icon: Icons.help_outline,
            title: 'Ayuda y Soporte',
            subtitle: 'Centro de ayuda y contacto',
            onTap: () {
              _showHelpDialog();
            },
            sizingInfo: sizingInfo,
          ),
          _buildSettingsItem(
            icon: Icons.info_outline,
            title: 'Acerca de DocuMente',
            subtitle: 'Versión 1.0.0',
            onTap: () {
              _showAboutDialog();
            },
            sizingInfo: sizingInfo,
          ),
          _buildSettingsItem(
            icon: Icons.logout,
            title: 'Cerrar Sesión',
            subtitle: 'Salir de tu cuenta',
            onTap: () {
              _showLogoutDialog();
            },
            textColor: Colors.red,
            iconColor: Colors.red,
            sizingInfo: sizingInfo,
          ),
        ],
      ),
    );
  }

  Widget _buildSettingsItem({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    Color? textColor,
    Color? iconColor,
    required ResponsiveInfo sizingInfo,
  }) {
    return ListTile(
      contentPadding: EdgeInsets.symmetric(
        horizontal: 0,
        vertical: sizingInfo.listTilePadding,
      ),
      leading: Container(
        padding: EdgeInsets.all(sizingInfo.iconPadding),
        decoration: BoxDecoration(
          color: (iconColor ?? const Color(0xFF6B4CE6)).withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius / 2),
        ),
        child: Icon(
          icon,
          color: iconColor ?? const Color(0xFF6B4CE6),
          size: sizingInfo.fontSize.icon,
        ),
      ),
      title: Text(
        title,
        style: TextStyle(
          fontWeight: FontWeight.w500,
          color: textColor ?? const Color(0xFF2C3E50),
          fontSize: sizingInfo.fontSize.body,
        ),
      ),
      subtitle: sizingInfo.showDescriptions ? Text(
        subtitle,
        style: TextStyle(
          color: Colors.grey[600],
          fontSize: sizingInfo.fontSize.caption,
        ),
      ) : null,
      trailing: Icon(Icons.arrow_forward_ios, 
        size: sizingInfo.fontSize.smallIcon,
      ),
      onTap: onTap,
    );
  }

  String _formatDate(DateTime date) {
    const months = [
      'enero',
      'febrero',
      'marzo',
      'abril',
      'mayo',
      'junio',
      'julio',
      'agosto',
      'septiembre',
      'octubre',
      'noviembre',
      'diciembre'
    ];

    return '${date.day} de ${months[date.month - 1]} de ${date.year}';
  }

  void _saveProfile() async {
    if (_formKey.currentState!.validate()) {
      setState(() {
        _isLoading = true;
      });

      try {
        final user = AuthService().currentUser;
        
        // Verificar si el email ha cambiado
        final emailChanged = _emailController.text != user?.email;
        
        if (emailChanged && !_isUserIvan()) {
          // Si el email ha cambiado y NO es Ivan, usar el nuevo flujo de validación
          setState(() {
            _isLoading = false;
          });
          
          // Navegar a la pantalla de validación de email
          final result = await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => ChangeEmailValidationScreen(
                newEmail: _emailController.text,
              ),
            ),
          );
          
          if (result == true) {
            // Email actualizado exitosamente
            setState(() {
              _isEditing = false;
              _showPasswordFields = false;
              _currentPasswordController.clear();
              _newPasswordController.clear();
              _confirmPasswordController.clear();
            });
            
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Email actualizado exitosamente'),
                  backgroundColor: Color(0xFF4CAF50),
                ),
              );
            }
          }
          
          return; // Salir del método
        }
        
        // Para otros cambios (username, password) o si es Ivan
        // Preparar datos para actualizar
        final updateData = <String, dynamic>{
          'username': _usernameController.text,
          'email': _emailController.text,
        };

        // Si se está cambiando la contraseña
        if (_showPasswordFields && _newPasswordController.text.isNotEmpty) {
          updateData['current_password'] = _currentPasswordController.text;
          updateData['new_password'] = _newPasswordController.text;
        }

        // Llamar al servicio de autenticación
        final result = await AuthService().updateProfile(updateData);

        setState(() {
          _isLoading = false;
        });

        if (result) {
          // Verificar si hay confirmación pendiente
          final prefs = await SharedPreferences.getInstance();
          final pendingEmailChange = prefs.getString('pending_email_change');
          
          if (pendingEmailChange != null) {
            // Mostrar diálogo de confirmación pendiente
            final pendingData = json.decode(pendingEmailChange);
            
            if (mounted) {
              // Extraer el token de verificación si está disponible
              String? verificationToken;
              
              // Si hay información de verificación almacenada, intentar extraer el token
              if (pendingData['token'] != null) {
                verificationToken = pendingData['token'];
              } else if (pendingData['verification_token'] != null) {
                verificationToken = pendingData['verification_token'];
              }
              
              showEmailChangeConfirmationDialog(
                context,
                oldEmail: pendingData['old_email'],
                newEmail: pendingData['new_email'],
                verificationToken: verificationToken,
                onVerified: () {
                  // Recargar datos del usuario
                  setState(() {});
                },
              );
            }
            
            // Limpiar el estado de cambio pendiente
            await prefs.remove('pending_email_change');
          } else {
            // Actualización exitosa sin confirmación pendiente
            setState(() {
              _isEditing = false;
              _showPasswordFields = false;
              _currentPasswordController.clear();
              _newPasswordController.clear();
              _confirmPasswordController.clear();
            });

            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Perfil actualizado exitosamente'),
                  backgroundColor: Color(0xFF4CAF50),
                ),
              );
            }
          }
        } else {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Error al actualizar el perfil'),
                backgroundColor: Colors.red,
              ),
            );
          }
        }
      } catch (e) {
        setState(() {
          _isLoading = false;
        });

        String errorMessage = 'Error al actualizar el perfil';
        
        // Extraer mensaje de error específico
        if (e.toString().contains('email_already_exists') || 
            e.toString().contains('ya está registrado')) {
          errorMessage = 'Este email ya está registrado';
        } else if (e.toString().contains('username') && 
                   e.toString().contains('ya está en uso')) {
          errorMessage = 'Este nombre de usuario ya está en uso';
        }

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(errorMessage),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    }
  }

  void _showHelpDialog() {
    final sizingInfo = context.responsive;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
        ),
        title: Text('Ayuda y Soporte',
          style: TextStyle(fontSize: sizingInfo.fontSize.subtitle),
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '¿Necesitas ayuda con DocuMente?',
                style: TextStyle(
                  fontWeight: FontWeight.bold, 
                  fontSize: sizingInfo.fontSize.body,
                ),
              ),
              SizedBox(height: sizingInfo.spacing),
              _buildHelpItem(
                title: 'Información de contacto',
                items: [
                  'Centro de ayuda: help.documente.com',
                  'Email: soporte@documente.com',
                  'Teléfono: +1 (555) 123-4567',
                ],
                sizingInfo: sizingInfo,
              ),
              SizedBox(height: sizingInfo.spacing),
              _buildHelpItem(
                title: 'Horario de atención',
                items: [
                  'Lunes a Viernes, 9:00 - 18:00 (UTC-5)',
                  'Sábados: 10:00 - 14:00 (Emergencias)',
                ],
                sizingInfo: sizingInfo,
              ),
              SizedBox(height: sizingInfo.spacing),
              _buildHelpItem(
                title: 'Preguntas frecuentes',
                items: [
                  '¿Cómo subir documentos grandes?',
                  '¿Cómo compartir documentos con usuarios externos?',
                  '¿Cómo recuperar versiones anteriores de documentos?',
                  '¿Cómo usar el chat asistido por IA?',
                ],
                sizingInfo: sizingInfo,
              ),
              SizedBox(height: sizingInfo.spacing),
              _buildHelpItem(
                title: 'Soluciones rápidas',
                items: [
                  'Problema de sincronización: Cierre sesión y vuelva a iniciar',
                  'Documentos no visibles: Verifique permisos',
                  'Búsqueda semántica no funciona: Verifique la conexión',
                ],
                sizingInfo: sizingInfo,
              ),
              SizedBox(height: sizingInfo.spacing),
              Text(
                'Para asistencia inmediata con cuentas corporativas, contacte a su administrador de TI interno.',
                style: TextStyle(
                  fontStyle: FontStyle.italic, 
                  fontSize: sizingInfo.fontSize.caption,
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            style: TextButton.styleFrom(
              foregroundColor: const Color(0xFF6B4CE6),
            ),
            child: Text('Cerrar',
              style: TextStyle(fontSize: sizingInfo.fontSize.button),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHelpItem({
    required String title, 
    required List<String> items,
    required ResponsiveInfo sizingInfo,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: sizingInfo.fontSize.body,
          ),
        ),
        SizedBox(height: sizingInfo.spacing / 2),
        ...items.map((item) => Padding(
              padding: EdgeInsets.only(
                left: sizingInfo.spacing, 
                bottom: sizingInfo.spacing / 2,
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('• ', 
                    style: TextStyle(
                      color: Color(0xFF6B4CE6),
                      fontSize: sizingInfo.fontSize.body,
                    ),
                  ),
                  Expanded(
                    child: Text(item, 
                      style: TextStyle(fontSize: sizingInfo.fontSize.caption),
                    ),
                  ),
                ],
              ),
            )),
      ],
    );
  }

  void _showAboutDialog() {
    final sizingInfo = context.responsive;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
        ),
        title: Text('Acerca de DocuMente',
          style: TextStyle(fontSize: sizingInfo.fontSize.subtitle),
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.description_outlined,
                size: sizingInfo.fontSize.emptyStateIcon,
                color: const Color(0xFF6B4CE6),
              ),
              SizedBox(height: sizingInfo.spacing),
              Text(
                'DocuMente',
                style: TextStyle(
                  fontSize: sizingInfo.fontSize.title,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: sizingInfo.spacing / 2),
              Text('Versión 1.0.0',
                style: TextStyle(fontSize: sizingInfo.fontSize.body),
              ),
              SizedBox(height: sizingInfo.spacing * 2),
              Text(
                'Tu asistente inteligente para la gestión de documentos potenciado por IA',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: sizingInfo.fontSize.body,
                ),
              ),
              SizedBox(height: sizingInfo.spacing * 2),
              _buildFeatureItem(
                icon: Icons.upload_file,
                title: 'Gestión de Documentos',
                description:
                    'Sube, organiza y accede a tus documentos desde cualquier dispositivo con seguridad y eficiencia.',
                sizingInfo: sizingInfo,
              ),
              SizedBox(height: sizingInfo.spacing),
              _buildFeatureItem(
                icon: Icons.search,
                title: 'Búsqueda Semántica',
                description:
                    'Encuentra documentos por su contenido, no solo por el título, gracias a nuestro motor de búsqueda semántica avanzado.',
                sizingInfo: sizingInfo,
              ),
              SizedBox(height: sizingInfo.spacing),
              _buildFeatureItem(
                icon: Icons.share,
                title: 'Compartición Inteligente',
                description:
                    'Comparte documentos con otros usuarios y establece permisos personalizados de forma sencilla.',
                sizingInfo: sizingInfo,
              ),
              SizedBox(height: sizingInfo.spacing),
              _buildFeatureItem(
                icon: Icons.chat,
                title: 'Chat Asistido por IA',
                description:
                    'Pregunta a tu asistente virtual sobre el contenido de tus documentos y obtén respuestas precisas.',
                sizingInfo: sizingInfo,
              ),
              SizedBox(height: sizingInfo.spacing),
              _buildFeatureItem(
                icon: Icons.security,
                title: 'Seguridad Avanzada',
                description:
                    'Tus documentos están protegidos con cifrado de extremo a extremo y autenticación segura.',
                sizingInfo: sizingInfo,
              ),
              SizedBox(height: sizingInfo.spacing),
              Text(
                '© 2024 DocuMente Inc. Todos los derechos reservados.',
                style: TextStyle(
                  color: Colors.grey,
                  fontSize: sizingInfo.fontSize.caption,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cerrar',
              style: TextStyle(fontSize: sizingInfo.fontSize.button),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFeatureItem({
    required IconData icon,
    required String title,
    required String description,
    required ResponsiveInfo sizingInfo,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: EdgeInsets.all(sizingInfo.iconPadding),
          decoration: BoxDecoration(
            color: const Color(0xFF6B4CE6).withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius / 2),
          ),
          child: Icon(
            icon,
            color: const Color(0xFF6B4CE6),
            size: sizingInfo.fontSize.icon,
          ),
        ),
        SizedBox(width: sizingInfo.spacing),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: sizingInfo.fontSize.body,
                ),
              ),
              SizedBox(height: sizingInfo.spacing / 4),
              Text(
                description,
                style: TextStyle(
                  fontSize: sizingInfo.fontSize.caption,
                  color: Colors.grey,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  void _showLogoutDialog() {
    final sizingInfo = context.responsive;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
        ),
        title: Text('Cerrar Sesión',
          style: TextStyle(fontSize: sizingInfo.fontSize.subtitle),
        ),
        content: Text('¿Estás seguro de que quieres cerrar sesión?',
          style: TextStyle(fontSize: sizingInfo.fontSize.body),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancelar',
              style: TextStyle(fontSize: sizingInfo.fontSize.button),
            ),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              AuthService().logout();
              Navigator.of(context).pushNamedAndRemoveUntil(
                '/',
                (route) => false,
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
              padding: EdgeInsets.symmetric(
                horizontal: sizingInfo.cardPadding,
                vertical: sizingInfo.spacing,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
              ),
            ),
            child: Text('Cerrar Sesión',
              style: TextStyle(fontSize: sizingInfo.fontSize.button),
            ),
          ),
        ],
      ),
    );
  }
}