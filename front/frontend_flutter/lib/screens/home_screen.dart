import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:async';
import '../models/user.dart';
import '../models/document.dart';
import '../models/chat.dart';
import '../services/auth_service.dart';
import '../providers/dashboard_provider.dart';
import 'documents_screen.dart';
import 'chat_list_screen.dart';
import 'admin_panel_screen.dart';
import 'profile_screen.dart';
import 'chat.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;
  late List<NavigationItem> _navigationItems;
  final DashboardProvider _dashboardProvider = DashboardProvider();
  
  // Usuario actual
  User? _currentUser;
  
  // Timer para actualización automática
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _currentUser = AuthService().currentUser;
    _initializeNavigation();
    
    // Cargar datos del dashboard inmediatamente
    print('🚀 HomeScreen: Iniciando carga del dashboard...');
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _dashboardProvider.loadDashboardData(showLoading: true);
    });
    
    // Configurar actualización automática cada 2 minutos
    _refreshTimer = Timer.periodic(const Duration(minutes: 2), (timer) {
      if (mounted) {
        _dashboardProvider.refreshInBackground();
      }
    });
  }
  
  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _initializeNavigation() {
    final user = AuthService().currentUser;

    _navigationItems = [
      NavigationItem(
        icon: Icons.home_outlined,
        selectedIcon: Icons.home,
        label: 'Inicio',
        screen: _buildDashboard(),
      ),
      NavigationItem(
        icon: Icons.folder_outlined,
        selectedIcon: Icons.folder,
        label: 'Mis Documentos',
        screen: const DocumentsScreen(),
      ),
      NavigationItem(
        icon: Icons.chat_bubble_outline,
        selectedIcon: Icons.chat_bubble,
        label: 'Chats',
        screen: ChatListScreen(),
      ),
    ];

    // Agregar opciones de administrador si el usuario es admin
    if (user?.isAdmin ?? false) {
      _navigationItems.add(
        NavigationItem(
          icon: Icons.admin_panel_settings_outlined,
          selectedIcon: Icons.admin_panel_settings,
          label: 'Administración',
          screen: const AdminPanelScreen(),
        ),
      );
    }

    _navigationItems.add(
      NavigationItem(
        icon: Icons.person_outline,
        selectedIcon: Icons.person,
        label: 'Perfil',
        screen: const ProfileScreen(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = AuthService().currentUser;
    final isSmallScreen = MediaQuery.of(context).size.width < 600;
    final isMediumScreen = MediaQuery.of(context).size.width >= 600 &&
        MediaQuery.of(context).size.width < 900;

    return ChangeNotifierProvider.value(
      value: _dashboardProvider,
      child: Scaffold(
        bottomNavigationBar: isSmallScreen
            ? BottomNavigationBar(
                currentIndex: _selectedIndex,
                onTap: (index) {
                  setState(() {
                    _selectedIndex = index;
                  });
                },
                selectedItemColor: const Color(0xFF6B4CE6),
                unselectedItemColor: Colors.grey[600],
                type: BottomNavigationBarType.fixed,
                items: _navigationItems
                    .map((item) => BottomNavigationBarItem(
                          icon: Icon(item.icon),
                          activeIcon: Icon(item.selectedIcon),
                          label: item.label,
                        ))
                    .toList(),
              )
            : null,
        body: Row(
          children: [
            if (!isSmallScreen) ...[
              NavigationRail(
                extended: !isMediumScreen,
                selectedIndex: _selectedIndex,
                onDestinationSelected: (index) {
                  setState(() {
                    _selectedIndex = index;
                  });
                },
                labelType: isMediumScreen
                    ? NavigationRailLabelType.selected
                    : NavigationRailLabelType.none,
                backgroundColor: Colors.white,
                selectedIconTheme: const IconThemeData(
                  color: Color(0xFF6B4CE6),
                  size: 28,
                ),
                unselectedIconTheme: IconThemeData(
                  color: Colors.grey[600],
                  size: 24,
                ),
                selectedLabelTextStyle: const TextStyle(
                  color: Color(0xFF6B4CE6),
                  fontWeight: FontWeight.w600,
                  fontSize: 12,
                ),
                unselectedLabelTextStyle: TextStyle(
                  color: Colors.grey[600],
                  fontSize: 12,
                ),
                leading: Container(
                  padding: const EdgeInsets.symmetric(vertical: 20),
                  child: Column(
                    children: [
                      Container(
                        width: 50,
                        height: 50,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [
                              Color(0xFF6B4CE6),
                              Color(0xFFE91E63),
                            ],
                          ),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(
                          Icons.description_outlined,
                          color: Colors.white,
                          size: 24,
                        ),
                      ),
                      if (!isMediumScreen) const SizedBox(height: 8),
                      if (!isMediumScreen)
                        Text(
                          'DocuMente',
                          style: TextStyle(
                            color: Colors.grey[800],
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                    ],
                  ),
                ),
                trailing: Container(
                  padding: const EdgeInsets.symmetric(vertical: 20),
                  child: Column(
                    children: [
                      CircleAvatar(
                        radius: 20,
                        backgroundColor: user?.isAdmin ?? false
                            ? const Color(0xFF6B4CE6).withOpacity(0.1)
                            : Colors.grey[200],
                        child: Text(
                          user?.username.substring(0, 1).toUpperCase() ?? 'U',
                          style: TextStyle(
                            color: user?.isAdmin ?? false
                                ? const Color(0xFF6B4CE6)
                                : Colors.grey[700],
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      if (!isMediumScreen) const SizedBox(height: 4),
                      if ((user?.isAdmin ?? false) && !isMediumScreen)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 4, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFF6B4CE6),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Text(
                            'ADMIN',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 8,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                destinations: _navigationItems
                    .map((item) => NavigationRailDestination(
                          icon: Icon(item.icon),
                          selectedIcon: Icon(item.selectedIcon),
                          label: Text(item.label),
                        ))
                    .toList(),
              ),
              const VerticalDivider(thickness: 1, width: 1),
            ],
            Expanded(
              child: _navigationItems[_selectedIndex].screen,
            ),
          ],
        ),
      ),
    );
  }

  // Método para obtener padding responsivo optimizado
  EdgeInsets _getResponsivePadding(double screenWidth) {
    if (screenWidth < 600) {
      return const EdgeInsets.symmetric(horizontal: 16, vertical: 8);
    } else if (screenWidth < 900) {
      return const EdgeInsets.symmetric(horizontal: 24, vertical: 12);
    } else {
      return const EdgeInsets.symmetric(horizontal: 32, vertical: 16);
    }
  }

  // Método para obtener espaciado responsivo optimizado
  double _getResponsiveSpacing(double screenWidth) {
    if (screenWidth < 600) {
      return 10.0;
    } else if (screenWidth < 900) {
      return 14.0;
    } else {
      return 18.0;
    }
  }

  // Sistema de tipografía responsiva con mejor manejo de tamaños
  TextStyle _getResponsiveTextStyle(double screenWidth, String type) {
    final Map<String, Map<String, double>> fontSizes = {
      'small': {
        'title': 20.0,
        'subtitle': 16.0,
        'body': 14.0,
        'caption': 12.0,
      },
      'medium': {
        'title': 24.0,
        'subtitle': 18.0,
        'body': 16.0,
        'caption': 14.0,
      },
      'large': {
        'title': 28.0,
        'subtitle': 20.0,
        'body': 18.0,
        'caption': 16.0,
      },
    };

    String screenType;
    if (screenWidth >= 900) {
      screenType = 'large';
    } else if (screenWidth >= 600) {
      screenType = 'medium';
    } else {
      screenType = 'small';
    }

    final fontSize = fontSizes[screenType]![type] ?? 16.0;

    switch (type) {
      case 'title':
        return TextStyle(
          fontSize: fontSize,
          fontWeight: FontWeight.bold,
          color: const Color(0xFF2C3E50),
        );
      case 'subtitle':
        return TextStyle(
          fontSize: fontSize,
          fontWeight: FontWeight.w600,
          color: const Color(0xFF2C3E50),
        );
      case 'body':
        return TextStyle(
          fontSize: fontSize,
          fontWeight: FontWeight.normal,
          color: const Color(0xFF2C3E50),
        );
      case 'caption':
        return TextStyle(
          fontSize: fontSize,
          fontWeight: FontWeight.normal,
          color: Colors.grey[600],
        );
      default:
        return TextStyle(fontSize: fontSize);
    }
  }

  Widget _buildDashboard() {
    return Consumer<DashboardProvider>(
      builder: (context, dashboardProvider, child) {
        return LayoutBuilder(builder: (context, constraints) {
          final screenWidth = constraints.maxWidth;
          final isSmallScreen = screenWidth < 600;
          final isMediumScreen = screenWidth >= 600 && screenWidth < 900;
          final isLargeScreen = screenWidth >= 900;

          final user = AuthService().currentUser;
          final EdgeInsets contentPadding = _getResponsivePadding(screenWidth);
          final double sectionSpacing = _getResponsiveSpacing(screenWidth);

          final double headerSpacing = isLargeScreen
              ? 1.0
              : isMediumScreen
                  ? 0.85
                  : 0.7;
          final double contentSpacing = isLargeScreen
              ? 0.3
              : isMediumScreen
                  ? 0.25
                  : 0.15;
          final double footerSpacing = isLargeScreen
              ? 0.1
              : isMediumScreen
                  ? 0.08
                  : 0.05;

          return Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Colors.grey[50]!,
                  const Color(0xFF6B4CE6).withOpacity(
                    isLargeScreen
                        ? 0.02
                        : isMediumScreen
                            ? 0.015
                            : 0.01,
                  ),
                ],
              ),
            ),
            child: RefreshIndicator(
              onRefresh: () async {
                await dashboardProvider.refresh();
              },
              child: SingleChildScrollView(
                padding: contentPadding,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildWelcomeHeader(user, screenWidth),
                    SizedBox(height: sectionSpacing * headerSpacing),
                    Padding(
                      padding:
                          EdgeInsets.symmetric(horizontal: isSmallScreen ? 8.0 : 0),
                      child: _buildQuickAccessCards(user, screenWidth),
                    ),
                    SizedBox(height: sectionSpacing * headerSpacing),
                    // Estadísticas visibles para TODOS los usuarios
                    Padding(
                      padding:
                          EdgeInsets.symmetric(horizontal: isSmallScreen ? 8.0 : 0),
                      child: _buildStatistics(screenWidth, dashboardProvider),
                    ),
                    SizedBox(height: sectionSpacing * headerSpacing),
                    // Documentos recientes
                    Padding(
                      padding: EdgeInsets.symmetric(
                          horizontal: isSmallScreen ? 8.0 : 0),
                      child: _buildRecentDocuments(screenWidth, dashboardProvider),
                    ),
                    SizedBox(height: sectionSpacing * contentSpacing),
                    // Chats recientes
                    Padding(
                      padding: EdgeInsets.symmetric(
                          horizontal: isSmallScreen ? 8.0 : 0),
                      child: _buildRecentChats(screenWidth, dashboardProvider),
                    ),
                    SizedBox(height: sectionSpacing * footerSpacing),
                  ],
                ),
              ),
            ),
          );
        });
      },
    );
  }

  Widget _buildWelcomeHeader(User? user, double screenWidth) {
    String greeting = 'Hola de nuevo';

    final isSmallScreen = screenWidth < 600;
    final isMediumScreen = screenWidth >= 600 && screenWidth < 900;

    final double greetingFontSize =
        isSmallScreen ? 22 : (isMediumScreen ? 26 : 32);
    final double usernameFontSize =
        isSmallScreen ? 26 : (isMediumScreen ? 30 : 36);
    final double subtitleFontSize =
        isSmallScreen ? 15 : (isMediumScreen ? 17 : 19);

    return Container(
      padding: EdgeInsets.all(
          isSmallScreen ? 16 : (isMediumScreen ? 24 : 28)),
      margin: EdgeInsets.symmetric(horizontal: isSmallScreen ? 0 : 2),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [
            Color(0xFF6B4CE6),
            Color(0xFFE91E63),
          ],
        ),
        borderRadius: BorderRadius.circular(
            isSmallScreen ? 16 : (isMediumScreen ? 20 : 22)),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF6B4CE6).withOpacity(0.2),
            blurRadius:
                isSmallScreen ? 15 : (isMediumScreen ? 18 : 22),
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: isSmallScreen
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$greeting,',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: greetingFontSize,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  user?.username ?? 'Usuario',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: usernameFontSize,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  user?.isAdmin ?? false
                      ? 'Panel de administrador de DocuMente'
                      : 'Gestiona tus documentos de forma inteligente',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.95),
                    fontSize: subtitleFontSize,
                    fontWeight: FontWeight.w400,
                  ),
                ),
                const SizedBox(height: 16),
              ],
            )
          : Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '$greeting, ${user?.username ?? 'Usuario'}',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: greetingFontSize,
                          fontWeight: FontWeight.bold,
                          letterSpacing: -0.5,
                        ),
                      ),
                      SizedBox(height: isSmallScreen ? 6 : 10),
                      Text(
                        user?.isAdmin ?? false
                            ? 'Panel de administrador de DocuMente'
                            : 'Gestiona tus documentos de forma inteligente',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.95),
                          fontSize: subtitleFontSize,
                          fontWeight: FontWeight.w400,
                          height: 1.3,
                        ),
                      ),
                      SizedBox(height: isSmallScreen ? 16 : 20),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(40),
                  ),
                  child: const Icon(
                    Icons.description_outlined,
                    size: 40,
                    color: Colors.white,
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildQuickAccessCards(User? user, double screenWidth) {
    final isSmallScreen = screenWidth < 600;
    final isMediumScreen = screenWidth >= 600 && screenWidth < 900;
    final cards = [
      _QuickAccessCard(
        icon: Icons.upload_file,
        title: 'Subir o Buscar Documento',
        subtitle: 'Agregar un nuevo archivo o buscar uno existente',
        color: const Color(0xFF4CAF50),
        onTap: () {
          setState(() {
            _selectedIndex = 1; // Ir a Mis Documentos
          });
        },
      ),
      if (user?.isAdmin ?? false)
        _QuickAccessCard(
          icon: Icons.admin_panel_settings,
          title: 'Administración',
          subtitle: 'Panel de control',
          color: const Color(0xFF9C27B0),
          onTap: () {
            setState(() {
              _selectedIndex = _navigationItems.length - 2; // Admin panel
            });
          },
        ),
    ];

    int crossAxisCount = isSmallScreen ? 1 : (isMediumScreen ? 2 : 3);
    double childAspectRatio = isSmallScreen ? 3.0 : 2.2;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Accesos Rápidos',
          style: _getResponsiveTextStyle(screenWidth, 'title'),
        ),
        SizedBox(height: isSmallScreen ? 12 : 16),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            childAspectRatio: childAspectRatio,
            crossAxisSpacing: 16,
            mainAxisSpacing: 16,
          ),
          itemCount: cards.length,
          itemBuilder: (context, index) => cards[index],
        ),
      ],
    );
  }

  Widget _buildStatistics(double screenWidth, DashboardProvider provider) {
    final isSmallScreen = screenWidth < 600;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Estadísticas del Sistema',
              style: _getResponsiveTextStyle(screenWidth, 'title'),
            ),
            if (provider.isLoading)
              const SizedBox(
                height: 20,
                width: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Color(0xFF6B4CE6),
                ),
              ),
          ],
        ),
        SizedBox(height: isSmallScreen ? 12 : 16),
        _buildStatisticsCards(screenWidth, provider.statistics),
      ],
    );
  }

  Widget _buildStatisticsCards(double screenWidth, Map<String, int> statistics) {
    final isSmallScreen = screenWidth < 600;
    final isMediumScreen = screenWidth >= 600 && screenWidth < 900;

    return isSmallScreen
        ? GridView.count(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisCount: 2,
            childAspectRatio: 1.4,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            children: [
              _buildStatCard(
                  'Total Usuarios',
                  statistics['total_users'].toString(),
                  Icons.people,
                  const Color(0xFF3F51B5),
                  screenWidth),
              _buildStatCard(
                  'Documentos',
                  statistics['total_documents'].toString(),
                  Icons.description,
                  const Color(0xFF009688),
                  screenWidth),
              _buildStatCard(
                  'Chats Activos',
                  statistics['active_chats'].toString(),
                  Icons.chat,
                  const Color(0xFFFF5722),
                  screenWidth),
            ],
          )
        : Row(
            children: [
              Expanded(
                child: _buildStatCard(
                    'Total Usuarios',
                    statistics['total_users'].toString(),
                    Icons.people,
                    const Color(0xFF3F51B5),
                    screenWidth),
              ),
              SizedBox(width: isSmallScreen ? 10 : (isMediumScreen ? 12 : 16)),
              Expanded(
                child: _buildStatCard(
                    'Documentos',
                    statistics['total_documents'].toString(),
                    Icons.description,
                    const Color(0xFF009688),
                    screenWidth),
              ),
              SizedBox(width: isSmallScreen ? 10 : (isMediumScreen ? 12 : 16)),
              Expanded(
                child: _buildStatCard(
                    'Chats Activos',
                    statistics['active_chats'].toString(),
                    Icons.chat,
                    const Color(0xFFFF5722),
                    screenWidth),
              ),
            ],
          );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color,
      double screenWidth) {
    final isSmallScreen = screenWidth < 600;
    final isMediumScreen = screenWidth >= 600 && screenWidth < 900;

    final double cardPadding =
        isSmallScreen ? 14 : (isMediumScreen ? 16 : 18);
    final double iconPadding =
        isSmallScreen ? 8 : (isMediumScreen ? 10 : 12);
    final double iconSize =
        isSmallScreen ? 20 : (isMediumScreen ? 24 : 26);
    final double valueFontSize =
        isSmallScreen ? 22 : (isMediumScreen ? 28 : 32);
    final double titleFontSize =
        isSmallScreen ? 13 : (isMediumScreen ? 14 : 15);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      padding: EdgeInsets.all(cardPadding),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(
            isSmallScreen ? 14 : (isMediumScreen ? 16 : 18)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.06),
            blurRadius:
                isSmallScreen ? 10 : (isMediumScreen ? 12 : 15),
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: EdgeInsets.all(iconPadding),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: color, size: iconSize),
              ),
              Icon(icon,
                  color: color.withOpacity(0.2), size: iconSize * 0.7),
            ],
          ),
          SizedBox(
              height:
                  isSmallScreen ? 12 : (isMediumScreen ? 14 : 16)),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 500),
              child: Text(
                value,
                key: ValueKey(value),
                style: TextStyle(
                  fontSize: valueFontSize,
                  fontWeight: FontWeight.bold,
                  color: const Color(0xFF2C3E50),
                  letterSpacing: -0.5,
                ),
              ),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            title,
            style: TextStyle(
              fontSize: titleFontSize,
              color: Colors.grey[600],
              fontWeight: FontWeight.w500,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildRecentDocuments(double screenWidth, DashboardProvider provider) {
    final isSmallScreen = screenWidth < 600;
    final recentDocuments = provider.recentDocuments;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Documentos Recientes',
              style: _getResponsiveTextStyle(screenWidth, 'title'),
            ),
            TextButton(
              onPressed: () {
                setState(() {
                  _selectedIndex = 1; // Ir a Mis Documentos
                });
              },
              child: const Text('Ver todos'),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: recentDocuments.isEmpty
              ? Container(
                  padding: const EdgeInsets.all(32),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.folder_open,
                          size: 48,
                          color: Colors.grey[400],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'No hay documentos recientes',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: Colors.grey[600],
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Sube tu primer documento desde "Mis Documentos"',
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey[500],
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                )
              : ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: recentDocuments.length > 3
                      ? 3
                      : recentDocuments.length,
                  separatorBuilder: (context, index) =>
                      const Divider(height: 1),
                  itemBuilder: (context, index) {
                    final doc = recentDocuments[index];
                    final icon = _getDocumentIcon(doc['content_type']);

                    return ListTile(
                      leading: Icon(icon, color: const Color(0xFF6B4CE6)),
                      title: Text(
                        doc['title'] ?? 'Sin título',
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Text(_formatDateTime(
                          doc['created_at'] != null
                              ? DateTime.parse(doc['created_at'])
                              : null)),
                      trailing: isSmallScreen
                          ? const Icon(Icons.arrow_forward_ios, size: 16)
                          : TextButton(
                              onPressed: () {
                                setState(() {
                                  _selectedIndex = 1;
                                });
                              },
                              child: const Text('Abrir'),
                            ),
                      onTap: () {
                        setState(() {
                          _selectedIndex = 1;
                        });
                      },
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildRecentChats(double screenWidth, DashboardProvider provider) {
    final isSmallScreen = screenWidth < 600;
    final recentChats = provider.recentChats;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Chats Recientes',
              style: _getResponsiveTextStyle(screenWidth, 'title'),
            ),
            TextButton(
              onPressed: () {
                setState(() {
                  _selectedIndex = 2; // Ir a Chats
                });
              },
              child: const Text('Ver todos'),
            ),
          ],
        ),
        const SizedBox(height: 1),
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: recentChats.isEmpty
              ? Container(
                  padding: const EdgeInsets.all(32),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.chat_bubble_outline,
                          size: 48,
                          color: Colors.grey[400],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'No hay chats recientes',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: Colors.grey[600],
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Inicia una conversación desde la sección "Chats"',
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey[500],
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                )
              : ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: recentChats.length > 3
                      ? 3
                      : recentChats.length,
                  separatorBuilder: (context, index) =>
                      const Divider(height: 0),
                  itemBuilder: (context, index) {
                    final chat = recentChats[index];
                    final lastMessage = chat.messages.isNotEmpty
                        ? chat.messages.last
                        : null;
                    final formattedDate = _formatDateTime(chat.updatedAt ?? chat.createdAt);

                    return ListTile(
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 4),
                      leading: CircleAvatar(
                        backgroundColor: const Color(0xFF6B4CE6),
                        radius: isSmallScreen ? 15 : 20,
                        child: const Icon(Icons.smart_toy,
                            color: Colors.white),
                      ),
                      title: Text(
                        chat.title,
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Text(
                        lastMessage != null
                            ? (lastMessage.question.startsWith('Tú:')
                                ? lastMessage.question
                                : 'Tú: ${lastMessage.question}')
                            : 'Sin mensajes',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      trailing: Text(
                        formattedDate,
                        style: TextStyle(
                          color: Colors.grey[600],
                          fontSize: 12,
                        ),
                      ),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) =>
                                ChatScreen(chatId: chat.id),
                          ),
                        );
                      },
                    );
                  },
                ),
        ),
      ],
    );
  }

  String _formatDateTime(DateTime? dateTime) {
    if (dateTime == null) return 'Fecha desconocida';

    try {
      final now = DateTime.now();
      final difference = now.difference(dateTime);

      if (difference.inDays == 0) {
        if (difference.inHours == 0) {
          if (difference.inMinutes == 0) {
            return 'Hace un momento';
          }
          return 'Hace ${difference.inMinutes} min';
        }
        return 'Hace ${difference.inHours}h';
      } else if (difference.inDays == 1) {
        return 'Ayer';
      } else if (difference.inDays < 7) {
        return 'Hace ${difference.inDays} días';
      } else {
        return '${dateTime.day}/${dateTime.month}/${dateTime.year}';
      }
    } catch (e) {
      return 'Fecha desconocida';
    }
  }

  IconData _getDocumentIcon(String? contentType) {
    switch (contentType) {
      case 'application/pdf':
        return Icons.picture_as_pdf;
      case 'text/plain':
        return Icons.description;
      case 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
      case 'application/msword':
        return Icons.description;
      case 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
      case 'application/vnd.ms-excel':
        return Icons.table_chart;
      case 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
      case 'application/vnd.ms-powerpoint':
        return Icons.slideshow;
      default:
        return Icons.insert_drive_file;
    }
  }
}

class _QuickAccessCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  const _QuickAccessCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isSmallScreen = screenWidth < 600;
    final isMediumScreen = screenWidth >= 600 && screenWidth < 900;

    final double cardPadding =
        isSmallScreen ? 12 : (isMediumScreen ? 16 : 20);
    final double iconPadding =
        isSmallScreen ? 8 : (isMediumScreen ? 10 : 12);
    final double iconSize =
        isSmallScreen ? 20 : (isMediumScreen ? 24 : 26);
    final double titleFontSize =
        isSmallScreen ? 14 : (isMediumScreen ? 15 : 17);
    final double subtitleFontSize =
        isSmallScreen ? 12 : (isMediumScreen ? 13 : 14);
    final double arrowSize =
        isSmallScreen ? 14 : (isMediumScreen ? 16 : 18);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.all(cardPadding),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(
              isSmallScreen ? 12 : (isMediumScreen ? 14 : 16)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.06),
              blurRadius:
                  isSmallScreen ? 8 : (isMediumScreen ? 10 : 12),
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              padding: EdgeInsets.all(iconPadding),
              decoration: BoxDecoration(
                color: color.withOpacity(0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: color, size: iconSize),
            ),
            SizedBox(
                width: isSmallScreen
                    ? 12
                    : (isMediumScreen ? 14 : 16)),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: titleFontSize,
                      color: const Color(0xFF2C3E50),
                      letterSpacing: -0.2,
                    ),
                  ),
                  const SizedBox(height: 1),
                  Text(
                    subtitle,
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: subtitleFontSize,
                      fontWeight: FontWeight.w400,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.arrow_forward_ios,
              size: arrowSize,
              color: Colors.grey[400],
            ),
          ],
        ),
      ),
    );
  }
}

class NavigationItem {
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final Widget screen;

  NavigationItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.screen,
  });
}
