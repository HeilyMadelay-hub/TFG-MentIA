import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:async';
import '../models/user.dart';
import '../models/document.dart';
import '../models/chat.dart';
import '../services/auth_service.dart';
import '../providers/dashboard_provider.dart';
import '../utils/responsive_utils.dart';
import 'documents_screen.dart';
import 'chat_list_screen.dart';
import 'admin_panel_screen.dart';
import 'profile_screen.dart';
import 'chat_with_websocket.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;
  late List<NavigationItem> _navigationItems;
  final DashboardProvider _dashboardProvider = DashboardProvider();
  User? _currentUser;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _currentUser = AuthService().currentUser;
    _initializeNavigation();

    print('🚀 HomeScreen: Iniciando carga del dashboard...');
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _dashboardProvider.loadDashboardData(showLoading: true);
    });

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
    return ChangeNotifierProvider.value(
      value: _dashboardProvider,
      child: ResponsiveBuilder(
        builder: (context, sizingInfo) {
          return Scaffold(
            bottomNavigationBar: sizingInfo.isMobile
                ? _buildBottomNavigationBar(sizingInfo)
                : null,
            body: Row(
              children: [
                if (!sizingInfo.isMobile)
                  _buildNavigationRail(sizingInfo),
                Expanded(
                  child: _navigationItems[_selectedIndex].screen,
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildBottomNavigationBar(ResponsiveInfo sizingInfo) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: OverflowBox(
          minHeight: 0,
          maxHeight: sizingInfo.isSmallDevice ? 56 : 72,
          child: SizedBox(
            height: sizingInfo.isSmallDevice ? 56 : 72,
            child: BottomNavigationBar(
            currentIndex: _selectedIndex,
            onTap: (index) => setState(() => _selectedIndex = index),
            selectedItemColor: const Color(0xFF6B4CE6),
            unselectedItemColor: Colors.grey[600],
            type: BottomNavigationBarType.fixed,
            selectedFontSize: 0,
            unselectedFontSize: 0,
            iconSize: sizingInfo.isSmallDevice ? 20 : 24,
            elevation: 0,
            backgroundColor: Colors.transparent,
            showSelectedLabels: false,
            showUnselectedLabels: false,
            items: _navigationItems
                .map((item) => BottomNavigationBarItem(
                      icon: Tooltip(
                        message: item.label,
                        child: Icon(item.icon),
                      ),
                      activeIcon: Tooltip(
                        message: item.label,
                        child: Icon(item.selectedIcon),
                      ),
                      label: item.label,
                    ))
              .toList(),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildNavigationRail(ResponsiveInfo sizingInfo) {
    final isExtended = sizingInfo.isDesktop;
    final user = AuthService().currentUser;
    
    return Container(
      width: isExtended ? 256 : 80,
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(2, 0),
          ),
        ],
      ),
      child: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  minHeight: constraints.maxHeight,
                ),
                child: IntrinsicHeight(
                  child: NavigationRail(
                    extended: isExtended,
                    selectedIndex: _selectedIndex,
                    onDestinationSelected: (index) => setState(() => _selectedIndex = index),
                    labelType: isExtended 
                        ? NavigationRailLabelType.none 
                        : NavigationRailLabelType.selected,
                    backgroundColor: Colors.transparent,
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
                      fontSize: 13,
                    ),
                    unselectedLabelTextStyle: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 12,
                    ),
                    leading: _buildNavigationRailHeader(isExtended, sizingInfo),
                    trailing: _buildNavigationRailFooter(user, isExtended),
                    destinations: _navigationItems
                        .map((item) => NavigationRailDestination(
                              icon: Icon(item.icon),
                              selectedIcon: Icon(item.selectedIcon),
                              label: Text(item.label),
                            ))
                        .toList(),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildNavigationRailHeader(bool isExtended, ResponsiveInfo sizingInfo) {
    return Container(
      padding: EdgeInsets.symmetric(
        vertical: isExtended ? 16 : 12,
        horizontal: 8,
      ),
      child: Column(
        children: [
          Container(
            width: isExtended ? 56 : 48,
            height: isExtended ? 56 : 48,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF6B4CE6), Color(0xFFE91E63)],
              ),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              Icons.description_outlined,
              color: Colors.white,
              size: isExtended ? 28 : 24,
            ),
          ),
          if (isExtended) ...[
            const SizedBox(height: 12),
            const Text(
              'MentIA',
              style: TextStyle(
                color: Color(0xFF2C3E50),
                fontSize: 16,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.2,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildNavigationRailFooter(User? user, bool isExtended) {
    return Container(
      padding: EdgeInsets.symmetric(
        vertical: isExtended ? 16 : 12,
        horizontal: 8,
      ),
      child: Column(
        children: [
          CircleAvatar(
            radius: isExtended ? 24 : 20,
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
                fontSize: isExtended ? 18 : 16,
              ),
            ),
          ),
          if ((user?.isAdmin ?? false) && isExtended) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFF6B4CE6),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Text(
                'ADMIN',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 0.5,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDashboard() {
    return Consumer<DashboardProvider>(
      builder: (context, dashboardProvider, child) {
        return ResponsiveBuilder(
          builder: (context, sizingInfo) {
            return Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Colors.grey[50]!,
                    const Color(0xFF6B4CE6).withOpacity(0.02),
                  ],
                ),
              ),
              child: RefreshIndicator(
                onRefresh: () async => await dashboardProvider.refresh(),
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: EdgeInsets.all(sizingInfo.padding),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildWelcomeHeader(sizingInfo),
                      SizedBox(height: sizingInfo.spacing * 2),
                      _buildQuickAccessCards(sizingInfo),
                      SizedBox(height: sizingInfo.spacing * 2),
                      _buildStatistics(sizingInfo, dashboardProvider),
                      SizedBox(height: sizingInfo.spacing * 2),
                      _buildRecentDocuments(sizingInfo, dashboardProvider),
                      SizedBox(height: sizingInfo.spacing * 2),
                      _buildRecentChats(sizingInfo, dashboardProvider),
                      SizedBox(height: sizingInfo.spacing * 2),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildWelcomeHeader(ResponsiveInfo sizingInfo) {
    final user = AuthService().currentUser;
    final screenWidth = MediaQuery.of(context).size.width;
    final isVerySmallScreen = screenWidth < 360;
    
    // Ajustes adaptativos para pantallas muy pequeñas
    final headerPadding = isVerySmallScreen 
        ? sizingInfo.cardPadding * 0.8 
        : sizingInfo.cardPadding;
    final greetingSize = isVerySmallScreen 
        ? sizingInfo.fontSize.caption 
        : sizingInfo.fontSize.subtitle;
    final nameSize = isVerySmallScreen 
        ? sizingInfo.fontSize.subtitle 
        : sizingInfo.fontSize.title;
    final descriptionSize = isVerySmallScreen 
        ? sizingInfo.fontSize.caption 
        : sizingInfo.fontSize.body;
    
    return Container(
      padding: EdgeInsets.all(headerPadding),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF6B4CE6), Color(0xFFE91E63)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF6B4CE6).withOpacity(0.3),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Hola de nuevo,',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.9),
                    fontSize: greetingSize,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                SizedBox(height: sizingInfo.spacing / 2),
                Flexible(
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerLeft,
                    child: Text(
                      user?.username ?? 'Usuario',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: nameSize,
                        fontWeight: FontWeight.bold,
                        letterSpacing: -0.5,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
                SizedBox(height: sizingInfo.spacing * (isVerySmallScreen ? 0.5 : 1)),
                Text(
                  user?.isAdmin ?? false
                      ? 'Panel de administrador de MentIA'
                      : 'Gestiona tus documentos de forma inteligente',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.9),
                    fontSize: descriptionSize,
                    fontWeight: FontWeight.w400,
                    height: 1.4,
                  ),
                  maxLines: isVerySmallScreen ? 1 : 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          // Mostrar icono solo si hay suficiente espacio
          if (!sizingInfo.isMobile || screenWidth > 400) ...[
            SizedBox(width: isVerySmallScreen ? 12 : 24),
            Container(
              padding: EdgeInsets.all(sizingInfo.iconPadding * (isVerySmallScreen ? 0.7 : 1)),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.description_outlined,
                size: isVerySmallScreen 
                    ? sizingInfo.fontSize.icon 
                    : sizingInfo.fontSize.largeIcon,
                color: Colors.white,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildQuickAccessCards(ResponsiveInfo sizingInfo) {
    final user = AuthService().currentUser;
    final cards = [
      _QuickAccessData(
        icon: Icons.upload_file,
        title: 'Subir o Buscar',
        subtitle: 'Documento',
        description: 'Agregar un nuevo archivo o buscar uno existente',
        color: const Color(0xFF4CAF50),
        onTap: () => setState(() => _selectedIndex = 1),
      ),
      if (user?.isAdmin ?? false)
        _QuickAccessData(
          icon: Icons.admin_panel_settings,
          title: 'Administración',
          subtitle: '',
          description: 'Panel de control',
          color: const Color(0xFF9C27B0),
          onTap: () => setState(() => _selectedIndex = _navigationItems.length - 2),
        ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Accesos Rápidos',
          style: TextStyle(
            fontSize: sizingInfo.fontSize.sectionTitle,
            fontWeight: FontWeight.bold,
            color: const Color(0xFF2C3E50),
          ),
        ),
        SizedBox(height: sizingInfo.spacing * 1.5),
        LayoutBuilder(
          builder: (context, constraints) {
            // Determinar el diseño basado en el tamaño disponible
            final screenWidth = MediaQuery.of(context).size.width;
            final isVerySmallScreen = screenWidth < 360;
            final availableWidth = constraints.maxWidth;
            
            // Calcular el número de columnas de manera más inteligente
            int crossAxisCount;
            if (isVerySmallScreen || sizingInfo.isSmallDevice) {
              crossAxisCount = 1; // Una columna para pantallas muy pequeñas
            } else if (sizingInfo.isMobile) {
              // Para móviles, verificar si hay espacio para 2 columnas
              crossAxisCount = availableWidth > 500 ? 2 : 1;
            } else {
              crossAxisCount = cards.length; // Mostrar todas las cards en línea en tablets/desktop
            }
            
            // Calcular dimensiones adaptativas
            final spacing = sizingInfo.spacing * (isVerySmallScreen ? 0.5 : 1);
            final itemWidth = crossAxisCount == 1 
                ? availableWidth 
                : (availableWidth - (crossAxisCount - 1) * spacing) / crossAxisCount;
            
            // Altura adaptativa basada en el contenido y el espacio disponible
            double itemHeight;
            if (isVerySmallScreen) {
              itemHeight = 65.0;
            } else if (sizingInfo.isSmallDevice) {
              itemHeight = 75.0;
            } else if (sizingInfo.isMobile) {
              itemHeight = 85.0;
            } else if (sizingInfo.isTablet) {
              itemHeight = 95.0;
            } else {
              itemHeight = 100.0;
            }
            
            // Si es una sola columna y hay múltiples cards, reducir la altura
            if (crossAxisCount == 1 && cards.length > 1) {
              itemHeight *= 0.9;
            }
            
            return Wrap(
              spacing: spacing,
              runSpacing: spacing,
              children: cards.map((data) => SizedBox(
                width: itemWidth,
                height: itemHeight,
                child: _QuickAccessCard(
                  data: data, 
                  sizingInfo: sizingInfo,
                  isCompactMode: isVerySmallScreen || (crossAxisCount == 1 && cards.length > 1),
                ),
              )).toList(),
            );
          },
        ),
      ],
    );
  }

  Widget _buildStatistics(ResponsiveInfo sizingInfo, DashboardProvider provider) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                'Mi Actividad',
                style: TextStyle(
                  fontSize: sizingInfo.fontSize.sectionTitle,
                  fontWeight: FontWeight.bold,
                  color: const Color(0xFF2C3E50),
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (provider.isLoading)
              SizedBox(
                height: sizingInfo.fontSize.icon,
                width: sizingInfo.fontSize.icon,
                child: const CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Color(0xFF6B4CE6),
                ),
              ),
          ],
        ),
        SizedBox(height: sizingInfo.spacing * 1.5),
        _buildStatisticsCards(sizingInfo, provider.statistics),
      ],
    );
  }

  Widget _buildStatisticsCards(ResponsiveInfo sizingInfo, Map<String, int> statistics) {
    final user = AuthService().currentUser;
    final sharedDocsTitle = user?.isAdmin == true ? 'Compartidos' : 'Compartidos';
    
    final cards = [
      _StatCardData(
        title: 'Mis Documentos',
        value: statistics['total_documents'].toString(),
        icon: Icons.description,
        color: const Color(0xFF009688),
      ),
      _StatCardData(
        title: 'Mis Chats',
        value: statistics['active_chats'].toString(),
        icon: Icons.chat,
        color: const Color(0xFFFF5722),
      ),
      _StatCardData(
        title: sharedDocsTitle,
        value: statistics['shared_documents']?.toString() ?? '0',
        icon: Icons.share,
        color: const Color(0xFF6B4CE6),
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = sizingInfo.isMobile ? 2 : 3;
        final itemWidth = (constraints.maxWidth - (crossAxisCount - 1) * sizingInfo.spacing) / crossAxisCount;
        final itemHeight = sizingInfo.isSmallDevice ? 100.0 : 120.0;
        
        return Wrap(
          spacing: sizingInfo.spacing,
          runSpacing: sizingInfo.spacing,
          children: cards.map((data) => SizedBox(
            width: itemWidth,
            height: itemHeight,
            child: _StatCard(data: data, sizingInfo: sizingInfo),
          )).toList(),
        );
      },
    );
  }

  Widget _buildRecentDocuments(ResponsiveInfo sizingInfo, DashboardProvider provider) {
    final recentDocuments = provider.recentDocuments;
    
    return _buildSection(
      title: 'Documentos Recientes',
      onViewAll: () => setState(() => _selectedIndex = 1),
      sizingInfo: sizingInfo,
      emptyWidget: _buildEmptyState(
        icon: Icons.folder_open,
        title: 'No hay documentos recientes',
        subtitle: 'Sube tu primer documento desde "Mis Documentos"',
        sizingInfo: sizingInfo,
      ),
      content: recentDocuments.isEmpty
          ? null
          : ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: recentDocuments.length > 3 ? 3 : recentDocuments.length,
              separatorBuilder: (context, index) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final doc = recentDocuments[index];
                return _buildDocumentTile(doc, sizingInfo);
              },
            ),
    );
  }

  Widget _buildRecentChats(ResponsiveInfo sizingInfo, DashboardProvider provider) {
    final recentChats = provider.recentChats;
    
    return _buildSection(
      title: 'Chats Recientes',
      onViewAll: () => setState(() => _selectedIndex = 2),
      sizingInfo: sizingInfo,
      emptyWidget: _buildEmptyState(
        icon: Icons.chat_bubble_outline,
        title: 'No hay chats recientes',
        subtitle: 'Inicia una conversación desde la sección "Chats"',
        sizingInfo: sizingInfo,
      ),
      content: recentChats.isEmpty
          ? null
          : ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: recentChats.length > 3 ? 3 : recentChats.length,
              separatorBuilder: (context, index) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final chat = recentChats[index];
                return _buildChatTile(chat, sizingInfo);
              },
            ),
    );
  }

  Widget _buildSection({
    required String title,
    required VoidCallback onViewAll,
    required ResponsiveInfo sizingInfo,
    required Widget emptyWidget,
    Widget? content,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                title,
                style: TextStyle(
                  fontSize: sizingInfo.fontSize.sectionTitle,
                  fontWeight: FontWeight.bold,
                  color: const Color(0xFF2C3E50),
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            TextButton(
              onPressed: onViewAll,
              child: Text(
                'Ver todos',
                style: TextStyle(
                  fontSize: sizingInfo.fontSize.button,
                  color: const Color(0xFF6B4CE6),
                ),
              ),
            ),
          ],
        ),
        SizedBox(height: sizingInfo.spacing),
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
            child: content ?? emptyWidget,
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState({
    required IconData icon,
    required String title,
    required String subtitle,
    required ResponsiveInfo sizingInfo,
  }) {
    return Container(
      padding: EdgeInsets.all(sizingInfo.cardPadding * 2),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon, 
              size: sizingInfo.fontSize.emptyStateIcon, 
              color: Colors.grey[400]
            ),
            SizedBox(height: sizingInfo.spacing * 2),
            Text(
              title,
              style: TextStyle(
                fontSize: sizingInfo.fontSize.subtitle,
                fontWeight: FontWeight.w600,
                color: Colors.grey[700],
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: sizingInfo.spacing),
            Text(
              subtitle,
              style: TextStyle(
                fontSize: sizingInfo.fontSize.body,
                color: Colors.grey[500],
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDocumentTile(Map<String, dynamic> doc, ResponsiveInfo sizingInfo) {
    final icon = _getDocumentIcon(doc['content_type']);
    
    return ListTile(
      contentPadding: EdgeInsets.symmetric(
        horizontal: sizingInfo.cardPadding,
        vertical: sizingInfo.listTilePadding,
      ),
      leading: Container(
        width: sizingInfo.listTileIconSize,
        height: sizingInfo.listTileIconSize,
        decoration: BoxDecoration(
          color: const Color(0xFF6B4CE6).withOpacity(0.1),
          borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
        ),
        child: Icon(
          icon, 
          color: const Color(0xFF6B4CE6), 
          size: sizingInfo.fontSize.icon
        ),
      ),
      title: Text(
        doc['title'] ?? 'Sin título',
        style: TextStyle(
          fontSize: sizingInfo.fontSize.body,
          fontWeight: FontWeight.w600,
        ),
        overflow: TextOverflow.ellipsis,
        maxLines: 1,
      ),
      trailing: TextButton(
        onPressed: () => setState(() => _selectedIndex = 1),
        style: TextButton.styleFrom(
          padding: EdgeInsets.symmetric(
            horizontal: sizingInfo.spacing,
            vertical: sizingInfo.spacing / 2,
          ),
        ),
        child: Text(
          'Abrir',
          style: TextStyle(fontSize: sizingInfo.fontSize.button),
        ),
      ),
      onTap: () => setState(() => _selectedIndex = 1),
    );
  }

  Widget _buildChatTile(Chat chat, ResponsiveInfo sizingInfo) {
    return ListTile(
      contentPadding: EdgeInsets.symmetric(
        horizontal: sizingInfo.cardPadding,
        vertical: sizingInfo.listTilePadding,
      ),
      leading: CircleAvatar(
        backgroundColor: const Color(0xFF6B4CE6),
        radius: sizingInfo.listTileIconSize / 2,
        child: Icon(
          Icons.smart_toy, 
          color: Colors.white, 
          size: sizingInfo.fontSize.icon
        ),
      ),
      title: Text(
        chat.title,
        style: TextStyle(
          fontSize: sizingInfo.fontSize.body,
          fontWeight: FontWeight.w600,
        ),
        overflow: TextOverflow.ellipsis,
        maxLines: 1,
      ),
      trailing: TextButton(
        onPressed: () => _navigateToChat(chat),
        style: TextButton.styleFrom(
          padding: EdgeInsets.symmetric(
            horizontal: sizingInfo.spacing,
            vertical: sizingInfo.spacing / 2,
          ),
        ),
        child: Text(
          'Abrir',
          style: TextStyle(fontSize: sizingInfo.fontSize.button),
        ),
      ),
      onTap: () => _navigateToChat(chat),
    );
  }

  void _navigateToChat(Chat chat) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ChatWithWebSocketScreen(existingChat: chat),
      ),
    );
  }

  IconData _getDocumentIcon(String? contentType) {
    final iconMap = {
      'application/pdf': Icons.picture_as_pdf,
      'text/plain': Icons.description,
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': Icons.description,
      'application/msword': Icons.description,
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': Icons.table_chart,
      'application/vnd.ms-excel': Icons.table_chart,
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': Icons.slideshow,
      'application/vnd.ms-powerpoint': Icons.slideshow,
    };
    
    return iconMap[contentType] ?? Icons.insert_drive_file;
  }
}

// Clases auxiliares
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

class _QuickAccessData {
  final IconData icon;
  final String title;
  final String subtitle;
  final String description;
  final Color color;
  final VoidCallback onTap;

  _QuickAccessData({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.description,
    required this.color,
    required this.onTap,
  });
}

class _QuickAccessCard extends StatelessWidget {
  final _QuickAccessData data;
  final ResponsiveInfo sizingInfo;
  final bool isCompactMode;

  const _QuickAccessCard({
    required this.data,
    required this.sizingInfo,
    this.isCompactMode = false,
  });

  @override
  Widget build(BuildContext context) {
    // Ajustes adaptativos para modo compacto
    final cardPadding = isCompactMode 
        ? sizingInfo.cardPadding * 0.7 
        : sizingInfo.cardPadding;
    final iconSize = isCompactMode 
        ? sizingInfo.fontSize.icon * 0.85 
        : sizingInfo.fontSize.icon;
    final titleSize = isCompactMode 
        ? sizingInfo.fontSize.subtitle * 0.9 
        : sizingInfo.fontSize.subtitle;
    final spacing = isCompactMode 
        ? sizingInfo.spacing * 0.7 
        : sizingInfo.spacing;
    
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: data.onTap,
        borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
        child: Container(
          padding: EdgeInsets.all(cardPadding),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                padding: EdgeInsets.all(sizingInfo.iconPadding * (isCompactMode ? 0.8 : 1)),
                decoration: BoxDecoration(
                  color: data.color.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                ),
                child: Icon(
                  data.icon,
                  color: data.color,
                  size: iconSize,
                ),
              ),
              SizedBox(width: spacing),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Flexible(
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        alignment: Alignment.centerLeft,
                        child: Text(
                          '${data.title} ${data.subtitle}'.trim(),
                          style: TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: titleSize,
                            color: const Color(0xFF2C3E50),
                          ),
                          overflow: TextOverflow.ellipsis,
                          maxLines: 1,
                        ),
                      ),
                    ),
                    // Mostrar descripción solo si hay suficiente espacio
                    if (!isCompactMode && sizingInfo.showDescriptions && !sizingInfo.isSmallDevice) ...[
                      SizedBox(height: spacing / 2),
                      Text(
                        data.description,
                        style: TextStyle(
                          color: Colors.grey[600],
                          fontSize: sizingInfo.fontSize.caption,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ],
                ),
              ),
              // Mostrar flecha solo si hay espacio suficiente
              if (!isCompactMode && !sizingInfo.isSmallDevice)
                Padding(
                  padding: EdgeInsets.only(left: spacing / 2),
                  child: Icon(
                    Icons.arrow_forward_ios,
                    size: sizingInfo.fontSize.smallIcon,
                    color: Colors.grey[400],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatCardData {
  final String title;
  final String value;
  final IconData icon;
  final Color color;

  _StatCardData({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
  });
}

class _StatCard extends StatelessWidget {
  final _StatCardData data;
  final ResponsiveInfo sizingInfo;

  const _StatCard({
    required this.data,
    required this.sizingInfo,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(sizingInfo.cardPadding),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(sizingInfo.borderRadius),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: EdgeInsets.all(sizingInfo.iconPadding),
                decoration: BoxDecoration(
                  color: data.color.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(sizingInfo.smallBorderRadius),
                ),
                child: Icon(
                  data.icon,
                  color: data.color,
                  size: sizingInfo.fontSize.icon,
                ),
              ),
              Flexible(
                child: Text(
                  data.value,
                  style: TextStyle(
                    fontSize: sizingInfo.fontSize.statValue,
                    fontWeight: FontWeight.bold,
                    color: const Color(0xFF2C3E50),
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          Text(
            data.title,
            style: TextStyle(
              fontSize: sizingInfo.fontSize.caption,
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
}