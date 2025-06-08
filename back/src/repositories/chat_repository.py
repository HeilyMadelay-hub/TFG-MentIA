"""
Repositorio para operaciones CRUD de chats en Supabase.
Maneja el acceso a datos para la entidad Chat usando el cliente de Supabase.
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from src.models.domain import Chat
from src.config.database import get_supabase_client

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatRepository:
    """
    Repositorio para gestionar chats en Supabase.
    Implementa operaciones CRUD básicas y consultas específicas.
    """
    
    def __init__(self):
        """Inicializa el repositorio con el cliente de Supabase."""
        self.table_name = "chats"
    
    def create_chat(self, name_chat: str, user_id: int) -> Chat:
        """
        Crea un nuevo chat para el usuario.
        
        Args:
            name_chat: Nombre del chat
            user_id: ID del usuario propietario
            
        Returns:
            Chat: El objeto chat creado
        """
        try:
            # Obtener cliente de Supabase con permisos de servicio
            supabase = get_supabase_client(use_service_role=True)
            
            # Preparar datos para inserción
            chat_data = {
                "name_chat": name_chat,
                "id_user": user_id
                # No incluir created_at, dejar que Supabase use su valor por defecto
            }
            
            # Insertar en Supabase
            response = supabase.table(self.table_name).insert(chat_data).execute()
            
            if response.data and len(response.data) > 0:
                chat_data = response.data[0]
                
                # Convertir a objeto Chat
                chat = Chat(
                    id=chat_data['id'],
                    id_user=chat_data['id_user'],
                    name_chat=chat_data['name_chat'],
                    created_at=chat_data.get('created_at')
                )
                
                logger.info(f"Chat '{name_chat}' creado para usuario {user_id}")
                return chat
            else:
                raise ValueError("No se pudo crear el chat")
                
        except Exception as e:
            logger.error(f"Error al crear chat: {str(e)}")
            raise
    
    def get_chats_by_user(self, user_id: int, limit: int = 100, skip: int = 0, sort_by: str = 'updated_at', order: str = 'desc') -> List[Chat]:
        """
        Obtiene todos los chats de un usuario.
        
        Args:
            user_id: ID del usuario
            limit: Número máximo de chats a retornar
            skip: Número de chats a saltar (paginación)
            sort_by: Campo por el cual ordenar (created_at, updated_at)
            order: Orden (asc o desc)
            
        Returns:
            List[Chat]: Lista de chats del usuario
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Validar parámetros de ordenamiento
            valid_sort_fields = ['created_at']  # Solo created_at existe en la tabla chats
            if sort_by not in valid_sort_fields:
                sort_by = 'created_at'
            
            # Determinar dirección del orden
            desc_order = order.lower() == 'desc' if order else True
            
            # Consultar en Supabase
            response = supabase.table(self.table_name)\
                .select('*')\
                .eq('id_user', user_id)\
                .order(sort_by, desc=desc_order)\
                .range(skip, skip + limit - 1)\
                .execute()
            
            chats = []
            if response.data:
                for chat_data in response.data:
                    chat = Chat(
                        id=chat_data['id'],
                        id_user=chat_data['id_user'],
                        name_chat=chat_data['name_chat'],
                        created_at=chat_data.get('created_at')
                    )
                    chats.append(chat)
            
            return chats
            
        except Exception as e:
            logger.error(f"Error al obtener chats del usuario {user_id}: {str(e)}")
            raise
    
    def get_chat_by_id(self, chat_id: int, user_id: Optional[int] = None) -> Optional[Chat]:
        """
        Obtiene un chat específico por su ID.
        Opcionalmente puede verificar que pertenezca a un usuario específico.
        
        Args:
            chat_id: ID del chat
            user_id: ID del usuario (opcional, para verificación)
            
        Returns:
            Optional[Chat]: El chat encontrado o None
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Construir query base
            query = supabase.table(self.table_name).select('*').eq('id', chat_id)
            
            # Si se especificó user_id, agregar filtro
            if user_id is not None:
                query = query.eq('id_user', user_id)
            
            # Ejecutar consulta
            response = query.execute()
            
            if response.data and len(response.data) > 0:
                chat_data = response.data[0]
                
                chat = Chat(
                    id=chat_data['id'],
                    id_user=chat_data['id_user'],
                    name_chat=chat_data['name_chat'],
                    created_at=chat_data.get('created_at')
                )
                
                return chat
            
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener chat {chat_id}: {str(e)}")
            raise
    
    def update_chat(self, chat_id: int, user_id: int, data: Dict[str, Any]) -> Optional[Chat]:
        """
        Actualiza un chat existente.
        
        Args:
            chat_id: ID del chat a actualizar
            user_id: ID del usuario propietario
            data: Diccionario con los campos a actualizar
            
        Returns:
            Optional[Chat]: El chat actualizado o None si no existe
        """
        try:
            # Verificar que el chat existe y pertenece al usuario
            chat = self.get_chat_by_id(chat_id, user_id)
            if not chat:
                logger.warning(f"Chat {chat_id} no encontrado para actualización")
                return None
            
            supabase = get_supabase_client(use_service_role=True)
            
            # Actualizar en Supabase
            response = supabase.table(self.table_name)\
                .update(data)\
                .eq('id', chat_id)\
                .eq('id_user', user_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                chat_data = response.data[0]
                
                # Convertir a objeto Chat
                chat = Chat(
                    id=chat_data['id'],
                    id_user=chat_data['id_user'],
                    name_chat=chat_data['name_chat'],
                    created_at=chat_data.get('created_at')
                )
                
                logger.info(f"Chat {chat_id} actualizado")
                return chat
            
            return None
            
        except Exception as e:
            logger.error(f"Error al actualizar chat {chat_id}: {str(e)}")
            raise
    
    def delete_chat(self, chat_id: int, user_id: int) -> bool:
        """
        Elimina un chat específico.
        
        Args:
            chat_id: ID del chat a eliminar
            user_id: ID del usuario propietario
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            # Verificar que el chat existe y pertenece al usuario
            chat = self.get_chat_by_id(chat_id, user_id)
            if not chat:
                logger.warning(f"Chat {chat_id} no encontrado para eliminación")
                return False
            
            supabase = get_supabase_client(use_service_role=True)
            
            # Eliminar chat
            response = supabase.table(self.table_name)\
                .delete()\
                .eq('id', chat_id)\
                .eq('id_user', user_id)\
                .execute()
            
            # Verificar si se eliminó
            success = response.data is not None
            
            if success:
                logger.info(f"Chat {chat_id} eliminado")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al eliminar chat {chat_id}: {str(e)}")
            raise
    
    # ==================== MÉTODOS ADMINISTRATIVOS ====================
    
    def get_all_chats(self, limit: int = 100, skip: int = 0, sort_by: str = 'created_at', order: str = 'desc') -> List[Chat]:
        """
        Obtiene TODOS los chats del sistema (para administradores).
        
        Args:
            limit: Número máximo de chats a retornar
            skip: Número de chats a saltar (paginación)
            sort_by: Campo por el cual ordenar
            order: Orden (asc o desc)
            
        Returns:
            List[Chat]: Lista de todos los chats del sistema
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Validar parámetros de ordenamiento
            valid_sort_fields = ['created_at', 'id']
            if sort_by not in valid_sort_fields:
                sort_by = 'created_at'
            
            # Determinar dirección del orden
            desc_order = order.lower() == 'desc' if order else True
            
            # Consultar TODOS los chats
            response = supabase.table(self.table_name)\
                .select('*')\
                .order(sort_by, desc=desc_order)\
                .range(skip, skip + limit - 1)\
                .execute()
            
            chats = []
            if response.data:
                for chat_data in response.data:
                    chat = Chat(
                        id=chat_data['id'],
                        id_user=chat_data['id_user'],
                        name_chat=chat_data['name_chat'],
                        created_at=chat_data.get('created_at')
                    )
                    chats.append(chat)
            
            logger.info(f"Obtenidos {len(chats)} chats del sistema")
            return chats
            
        except Exception as e:
            logger.error(f"Error al obtener todos los chats: {str(e)}")
            raise
    
    def count_all_chats(self) -> int:
        """
        Cuenta el total de chats en el sistema.
        
        Returns:
            int: Número total de chats
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Usar count() para obtener el total
            response = supabase.table(self.table_name)\
                .select('*', count='exact')\
                .execute()
            
            return response.count or 0
            
        except Exception as e:
            logger.error(f"Error al contar chats: {str(e)}")
            return 0
    
    def count_chats_by_user(self) -> Dict[str, int]:
        """
        Obtiene el conteo de chats por usuario.
        
        Returns:
            Dict[str, int]: Diccionario con username como clave y conteo como valor
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Obtener todos los chats con información del usuario
            response = supabase.table(self.table_name)\
                .select('id_user, users!inner(username)')\
                .execute()
            
            # Contar chats por usuario
            user_counts = {}
            if response.data:
                for chat in response.data:
                    username = chat['users']['username']
                    if username not in user_counts:
                        user_counts[username] = 0
                    user_counts[username] += 1
            
            return user_counts
            
        except Exception as e:
            logger.error(f"Error al contar chats por usuario: {str(e)}")
            return {}
    
    def count_active_chats(self, hours: int = 24) -> int:
        """
        Cuenta los chats activos en las últimas N horas.
        Un chat se considera activo si tiene mensajes recientes.
        
        Args:
            hours: Número de horas hacia atrás para considerar
            
        Returns:
            int: Número de chats activos
        """
        try:
            supabase = get_supabase_client(use_service_role=True)
            
            # Calcular fecha límite
            from datetime import datetime, timedelta
            time_limit = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            # Contar chats con mensajes recientes
            # Usar join con messages para encontrar chats con actividad reciente
            response = supabase.table(self.table_name)\
                .select('id, messages!inner(created_at)', count='exact')\
                .gte('messages.created_at', time_limit)\
                .execute()
            
            # Obtener IDs únicos de chats activos
            active_chat_ids = set()
            if response.data:
                for chat in response.data:
                    active_chat_ids.add(chat['id'])
            
            return len(active_chat_ids)
            
        except Exception as e:
            logger.error(f"Error al contar chats activos: {str(e)}")
            return 0
