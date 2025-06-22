// ARCHIVO DE CORRECCIÓN ESPECÍFICA
// Reemplazar el método _buildUsersTab() en admin_panel_screen.dart

Widget _buildUsersTab() {
  final screenWidth = MediaQuery.of(context).size.width;
  final isTablet = screenWidth >= 600;
  final padding = isTablet ? 24.0 : 16.0;

  return SingleChildScrollView(
    padding: EdgeInsets.all(padding),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Gestión de Usuarios',
          style: TextStyle(
            fontSize: isTablet ? 20 : 18,
            fontWeight: FontWeight.bold,
            color: const Color(0xFF2C3E50),
          ),
        ),
        const SizedBox(height: 16),
        if (_isLoadingUsers)
          Container(
            height: 200,
            alignment: Alignment.center,
            child: const CircularProgressIndicator(
              color: Color(0xFF6B4CE6),
            ),
          )
        else if (_users.isEmpty)
          Container(
            padding: EdgeInsets.all(32),
            alignment: Alignment.center,
            child: Text(
              'No hay usuarios registrados',
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 16,
              ),
            ),
          )
        else
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withAlpha(13),
                  blurRadius: 10,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _users.length,
              separatorBuilder: (context, index) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final user = _users[index];
                
                // 🔧 CORRECCIÓN: Usar el tiempo formateado del backend
                String formattedTime = 'Fecha desconocida';
                
                // Buscar los datos del usuario en el dashboard data del backend
                if (_dashboardData != null && 
                    _dashboardData!['users'] != null && 
                    index < _dashboardData!['users'].length) {
                  final userData = _dashboardData!['users'][index];
                  
                  // ✅ USAR EL TIEMPO YA FORMATEADO DEL BACKEND
                  if (userData['formatted_created'] != null && userData['formatted_created'].toString().isNotEmpty) {
                    formattedTime = userData['formatted_created'];
                    print('✅ Usando tiempo del backend para ${user.username}: $formattedTime');
                  } else {
                    // Fallback: calcular en el frontend solo si no viene del backend
                    formattedTime = _formatDateTime(user.createdAt);
                    print('⚠️ Calculando tiempo en frontend para ${user.username}: $formattedTime');
                  }
                } else {
                  // Fallback: calcular en el frontend
                  formattedTime = _formatDateTime(user.createdAt);
                  print('❌ Sin datos del backend, calculando en frontend para ${user.username}: $formattedTime');
                }
                
                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: const Color(0xFF6B4CE6).withOpacity(0.2),
                    child: Icon(
                      Icons.person,
                      color: const Color(0xFF6B4CE6),
                    ),
                  ),
                  title: Text(
                    user.username,
                    style: const TextStyle(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(user.email),
                      Text(
                        // 🎯 AQUÍ ESTÁ EL CAMBIO PRINCIPAL: usar formattedTime del backend
                        'Cuenta creada: $formattedTime',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                  trailing: PopupMenuButton<String>(
                    icon: const Icon(Icons.more_vert),
                    itemBuilder: (context) => [
                      const PopupMenuItem(
                        value: 'edit',
                        child: Row(
                          children: [
                            Icon(Icons.edit),
                            SizedBox(width: 8),
                            Text('Editar'),
                          ],
                        ),
                      ),
                      const PopupMenuItem(
                        value: 'delete',
                        child: Row(
                          children: [
                            Icon(Icons.delete, color: Colors.red),
                            SizedBox(width: 8),
                            Text('Eliminar'),
                          ],
                        ),
                      ),
                    ],
                    onSelected: (action) => _handleUserAction(action, user),
                  ),
                );
              },
            ),
          ),
      ],
    ),
  );
}
