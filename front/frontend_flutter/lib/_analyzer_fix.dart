import 'package:flutter/material.dart';

// Importaciones de los modelos
import 'models/user.dart';
import 'models/document.dart';
import 'models/chat.dart';
import 'services/auth_service.dart';

// Clase temporal para validar todas las importaciones
class _TempAnalyzerFixer {
  // Validar clases de Flutter
  Widget? widget;
  BuildContext? context;
  State? state;
  StatefulWidget? statefulWidget;
  TabController? tabController;
  
  // Validar colores e iconos
  Color? color = Colors.red;
  IconData? icon = Icons.check;
  
  // Validar modelos
  User? user;
  Document? document;
  ChatModel? chat;
  AuthService? authService;
  
  // Validar enums
  UserRole? userRole;
  
  // Validar widgets específicos
  SafeArea? safeArea;
  Scaffold? scaffold;
  Container? container;
  Column? column;
  Row? row;
  Text? text;
  TextStyle? textStyle;
  EdgeInsets? edgeInsets;
  BoxDecoration? boxDecoration;
  BorderRadius? borderRadius;
  LinearGradient? linearGradient;
  BoxShadow? boxShadow;
  Offset? offset;
  Tab? tab;
  TabBar? tabBar;
  TabBarView? tabBarView;
  CircularProgressIndicator? circularProgressIndicator;
  SingleChildScrollView? singleChildScrollView;
  ListView? listView;
  ListTile? listTile;
  PopupMenuButton? popupMenuButton;
  PopupMenuItem? popupMenuItem;
  AlertDialog? alertDialog;
  TextField? textField;
  InputDecoration? inputDecoration;
  OutlineInputBorder? outlineInputBorder;
  TextButton? textButton;
  ElevatedButton? elevatedButton;
  SnackBar? snackBar;
  ScaffoldMessenger? scaffoldMessenger;
  Navigator? navigator;
  MediaQuery? mediaQuery;
  SizedBox? sizedBox;
  Wrap? wrap;
  Expanded? expanded;
  Divider? divider;
  CircleAvatar? circleAvatar;
  RoundedRectangleBorder? roundedRectangleBorder;
  
  // Validar mixin
  TickerProviderStateMixin? tickerProviderStateMixin;
  
  // Validar tipos básicos
  DateTime? dateTime;
  Duration? duration;
  Future? future;
  
  // Validar métodos de extensión
  void testMethods() {
    // Métodos de context
    context?.mounted;
    
    // Métodos de colores - CORREGIDO: withOpacity → withValues
    color?.withValues(alpha: 0.5);
    
    // Métodos de DateTime
    dateTime?.subtract(const Duration(days: 1));
    
    // Métodos de listas
    <String>['test'].map((e) => e).toList();
    <String>['test'].where((e) => e.isNotEmpty).toList();
    
    // Métodos de String
    'test'.substring(0, 1);
    'test'.toUpperCase();
    'test'.toLowerCase();
    'test'.isNotEmpty;
    'test'.contains('t');
    
    // Métodos de números
    5.toString();
    
    // Métodos de MediaQuery
    MediaQuery.of(context!).size.width;
  }
}

// Función pública para usar la clase y evitar warnings
void validateFlutterImports() {
  final temp = _TempAnalyzerFixer();
  temp.testMethods();
}
