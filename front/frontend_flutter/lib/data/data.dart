const List<Map<String, String>> chatMessage = [  // Datos que creo que recibiré de la api.

  /*{                         //Datos usuario
    'id': '4444',
    'username': 'carlos.luna',
    'email': 'usuario@documente.com',
    'password_hash': 'jhae626VVJ_.', // Regular cuándo se tienen los datosm y a cuáles accede el Chatbot.
    'created_at': '2025-01-04 09:53:45',
    'updated_at': 'null',
    'is_admin': 'false',
  },*/


  {               // El primer mensaje no se genera por el Chatbot para no gastar tokens, pero sí se registra en BBDD para saber quiénes acceden.
    'id': '0',
    'id_user': '0',
    'username': '',
    'id_chat': '1',
    'question': '',
    'answer': 'Hola! Soy MentIA, tu asistente personal de DocuMente. Puedo ayudarte a gestionar y buscar en tus documentos. ¿Qué necesitas?',
    'name_chat': 'Nuevo chat',
    'documents_referenced': '',
    'tokens_used': '0',
    //sentiment VARCHAR(50), -- Nuevo: análisis de sentimiento de la pregunta
    'created_at': '2025-24-04 09:53:45',
  },


  {
    'id': '1',
    'id_user': '4444',
    'username': 'carlos.luna',
    'id_chat': '1',
    'question': '¿Puedes ayudarme a encontrar un documento?',
    'answer': 'Por supuesto! Puedo buscar en todos tus documentos subidos. ¿Cómo se llama o qué contiene el documento que buscas?',
    'name_chat': 'Consulta de nombre',
    'documents_referenced': 'documents/dniCarlos.png',
    'tokens_used': '4',
    //sentiment VARCHAR(50), -- Nuevo: análisis de sentimiento de la pregunta
    'created_at': '2025-24-04 09:54:21',
  },


  {
    'id': '2',
    'id_user': '4444',
    'username': 'carlos.luna',
    'id_chat': '1',
    'question': '¿Qué tipos de archivos puedo subir?',
    'answer': 'Puedes subir PDFs, imágenes (JPG, PNG), documentos de Word y texto plano. El límite es de aproximadamente 100 páginas por documento. ¿Te gustaría subir algo ahora?',
    'name_chat': 'Consulta sobre archivos',
    'documents_referenced': 'documents/dniCarlos.png',
    'tokens_used': '5',
    //sentiment VARCHAR(50), -- Nuevo: análisis de sentimiento de la pregunta
    'created_at': '2025-24-04 09:54:47',
  },

];
