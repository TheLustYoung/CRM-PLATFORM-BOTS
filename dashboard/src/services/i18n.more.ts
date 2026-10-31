/** The screens added after the MVP (Reports, Translations, Monitoring, Tiers, Instagram accounts, ads, proxies, bot
 * tokens) in the other dashboard languages. English and Russian live in i18n.instagram.ts. */
export const moreTexts: Record<string, Record<string, string>> = {
  es: {
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    reports: 'Informes', reportsHint: 'Cifras diarias, semanales y mensuales por bot, servicio y plataforma',
    period_day: 'Días', period_week: 'Semanas', period_month: 'Meses', allBots: 'Todos los bots', period: 'Periodo',
    rDownloads: 'Descargas', rUploads: 'Subidas', permanent: 'permanente', makePermanent: 'Hacer permanente',
    paymentSource: 'Origen', referralCredits: 'Más créditos (descargas extra) por recompensa', bot: 'Bot',
    newUsersPeriod: 'Usuarios nuevos', activeUsersPeriod: 'Usuarios activos', errorRate: 'Tasa de errores', storageUsed: 'Almacenamiento usado',
    completedFailed: 'Completadas y fallidas', byPlatform: 'Por plataforma', byBot: 'Por bot', byService: 'Por servicio',
    failedByPlatform: 'Fallos por plataforma', topErrors: 'Errores más frecuentes', revenueByMethod: 'Ingresos por método de pago',
    reportRules: 'Reglas de cálculo: los periodos son días, semanas ISO y meses en UTC; tasa de errores = fallidas / (completadas + fallidas); usuarios activos = quienes iniciaron una tarea en el periodo; ingresos = pedidos pagados por fecha de pago, sin reembolsos (Stars en Stars, tarjetas y cripto en USD). El CSV usa las mismas cifras.',
    translations: 'Traducciones', translationsHint: 'Cambia cualquier texto de los bots en cualquier idioma y activa o desactiva idiomas sin tocar el código. Un campo vacío devuelve el texto original. Los marcadores como {count} deben mantenerse.',
    editedTexts: '{count} editados', narrowSearch: 'Coinciden {count} textos: afina la búsqueda para ver el resto.',
    monitoring: 'Monitorización y alertas', monitoringHint: 'Cada 5 minutos la plataforma revisa el disco, las descargas fallidas, los bots inactivos y la cola, y envía alertas (como máximo una por hora por problema).',
    problemsFound: '{count} problema(s)', allGood: 'Todo bien', diskFree: 'Disco: {free} GB libres de {total} GB', lastCheck: 'revisado {date}',
    alertChat: 'Chat de Telegram para alertas', alertChatHint: 'Tu ID de Telegram o el ID de un grupo (-100…). Inicia allí uno de los bots primero.',
    diskMinGb: 'Alertar con menos disco libre (GB)', errorRateAlert: 'Alertar con más descargas fallidas (%)', queueMinutes: 'Alertar si una tarea espera más de (min)',
    botSilentMinutes: 'Alertar si un bot no responde durante (min)', checkNow: 'Revisar ahora y enviar una alerta de prueba',
    tier: 'Nivel', credits: 'Créditos', creditsHint: '(descargas extra por encima del límite diario)',
    botToken: 'Token del bot', botTokenHint: 'Pega un token de @BotFather para conectar o sustituir este bot sin editar archivos en el servidor. Se comprueba con Telegram, se guarda cifrado y no vuelve a mostrarse; el bot se reinicia con él en un minuto.',
    saveToken: 'Guardar token', tiers: 'Niveles', tiersHint: 'Cada nivel de pago tiene sus límites (0 = sin límite extra). Los planes de abajo venden un nivel por días.',
    tierName: 'Nombre', tierDaily: 'Descargas al día (0 = sin límite)', tierMaxMb: 'Archivo máximo, MB (0 = límite del servidor)', tierStorageMb: 'Almacenamiento de archivos, MB (0 = sin cuota)',
    tierPriority: 'Cola prioritaria', tierNoAds: 'Sin anuncios', tierKeyPrompt: 'ID corto del nuevo nivel (letras latinas, p. ej. gold):', addTier: 'Añadir nivel',
    tierPlatforms: 'Plataformas incluidas (todas marcadas = todas)',
    botPlatforms: 'Plataformas de este bot', alertEmails: 'Correos para alertas', alertEmailFrom: 'Dirección del remitente',
    alertEmailProvider: 'Servicio de correo', alertEmailKey: 'Clave API del servicio de correo',
    alertEmailHint: 'El servidor envía correo mediante una API HTTPS (SendGrid o Resend; basta el plan gratuito). El remitente debe estar verificado en ese servicio. La clave se guarda cifrada.',
    adClicks: '{count} clics', adWeight: 'Peso (frecuencia frente a otros anuncios)', adMaxViews: 'Parar tras visualizaciones (0 = sin límite)',
    adBots: 'Mostrar en bots', adLanguages: 'Solo para idiomas (vacío = todos)', adsEvery: 'Mostrar un anuncio cada N descargas de un usuario',
    
    
    
    fileView: 'Ver', fileDownload: 'Descargar', fileClose: 'Cerrar', noPreview: 'Este tipo de archivo no se puede mostrar aquí. Usa Descargar para abrirlo.', userData: 'Datos del usuario', jobChannel: 'Autor', jobDuration: 'Duración', jobViews: 'Vistas', jobLikes: 'Me gusta', jobItems: 'Elementos', jobFormat: 'Formato', jobCompleted: 'Terminado', jobLink: 'Enlace', fileLabel: 'Archivo', jobDescription: 'Descripción', jobNoFiles: 'No hay archivos guardados para esta tarea (consulta de información, fallo o archivos ya eliminados).', userName: 'Nombre', addChannel: 'Añadir otro canal', channelsHint: 'Los usuarios deben unirse a todos los canales de la lista (hasta 10). El bot debe ser administrador en cada uno; Comprobar muestra el resultado de cada canal y bot.', media_retention_days: 'Conservar medios descargados · días', retention_days: 'Conservar archivos subidos · días', channel: 'Canal', channelPageHint: 'Canal público de los bots: publicar, programar, editar, fijar y borrar publicaciones', channelConnect: 'Conectar el canal', channelConnectHint: 'Añade el bot al canal como administrador con permiso para publicar (y editar, borrar y fijar) y escribe aquí el canal.', channelPostingBot: 'Bot que publica', saveAndCheck: 'Guardar y comprobar', channelPrivate: 'canal privado', channelSubscribers: 'suscriptores', rightPost: 'publicar', rightEdit: 'editar', rightDelete: 'borrar', rightPin: 'fijar', channelNotAdmin: 'El bot no es administrador de este canal: añádelo en Ajustes del canal → Administradores.', channelEditPost: 'Editar publicación', channelNewPost: 'Nueva publicación', channelComposeHint: 'Texto con formato, foto o vídeo, botones con enlace; publicar ahora o a una hora.', addPhotoOrVideo: 'Añadir foto o vídeo', channelButtons: 'Botones bajo la publicación', addButton: 'Añadir botón', channelWhen: 'Cuándo', channelNow: 'Ahora', channelLater: 'A una hora fija', channelConnectFirst: 'Conecta primero el canal', channelSchedule: 'Programar', channelPublishNow: 'Publicar ahora', channelPosts: 'Publicaciones del canal', channelViewsNote: 'La Bot API de Telegram no da las visualizaciones; ábrelas en Telegram.', cp_scheduled: 'Programada', cp_sending: 'Enviando', cp_published: 'Publicada', cp_failed: 'Error', pinned: 'fijada', pin: 'Fijar', unpin: 'Desfijar', edit: 'Editar', channelConfirmDelete: '¿Borrar esta publicación del canal?', channelConfirmCancel: '¿Cancelar esta publicación programada?', channelDelete: 'Borrar del canal', cancel: 'Cancelar', openInTelegram: 'Abrir en Telegram', channelAllBots: 'Todos los bots', channelPostsFrom: 'publica', channelBots: 'Bots de este canal', channelBotAdmin: 'Administrador del canal', channelNoBots: 'Aún no hay bots conectados: añádelos en la página Bots.', channelPostingAs: 'Publica {bot}.', channelNoPoster: 'Ningún bot elegido puede publicar aquí: haz a uno administrador con permiso para publicar.',
  },
  fr: {
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    reports: 'Rapports', reportsHint: 'Chiffres quotidiens, hebdomadaires et mensuels par bot, service et plateforme',
    period_day: 'Jours', period_week: 'Semaines', period_month: 'Mois', allBots: 'Tous les bots', period: 'Période',
    rDownloads: 'Téléchargements', rUploads: 'Envois', permanent: 'permanent', makePermanent: 'Rendre permanent',
    paymentSource: 'Source', referralCredits: 'Plus des crédits (téléchargements en plus) par récompense', bot: 'Bot',
    newUsersPeriod: 'Nouveaux utilisateurs', activeUsersPeriod: 'Utilisateurs actifs', errorRate: 'Taux d’erreurs', storageUsed: 'Stockage utilisé',
    completedFailed: 'Réussis et échoués', byPlatform: 'Par plateforme', byBot: 'Par bot', byService: 'Par service',
    failedByPlatform: 'Échecs par plateforme', topErrors: 'Erreurs les plus fréquentes', revenueByMethod: 'Revenus par moyen de paiement',
    reportRules: 'Règles de calcul : périodes en jours, semaines ISO et mois (UTC) ; taux d’erreurs = échoués / (réussis + échoués) ; utilisateurs actifs = ceux qui ont lancé une tâche sur la période ; revenus = commandes payées à la date de paiement, remboursements exclus (Stars en Stars, cartes et crypto en USD). L’export CSV reprend les mêmes chiffres.',
    translations: 'Traductions', translationsHint: 'Modifiez n’importe quel texte des bots dans n’importe quelle langue et activez ou désactivez des langues, sans toucher au code. Un champ vide rétablit le texte d’origine. Les variables comme {count} doivent rester.',
    editedTexts: '{count} modifiés', narrowSearch: '{count} textes correspondent : affinez la recherche pour voir le reste.',
    monitoring: 'Surveillance et alertes', monitoringHint: 'Toutes les 5 minutes, la plateforme vérifie le disque, les téléchargements échoués, les bots silencieux et la file d’attente, et envoie des alertes (au plus une par heure et par problème).',
    problemsFound: '{count} problème(s)', allGood: 'Tout va bien', diskFree: 'Disque : {free} Go libres sur {total} Go', lastCheck: 'vérifié {date}',
    alertChat: 'Chat Telegram pour les alertes', alertChatHint: 'Votre ID Telegram ou l’ID d’un groupe (-100…). Lancez-y d’abord l’un des bots.',
    diskMinGb: 'Alerter sous cet espace libre (Go)', errorRateAlert: 'Alerter au-delà de ce taux d’échecs (%)', queueMinutes: 'Alerter si une tâche attend plus de (min)',
    botSilentMinutes: 'Alerter si un bot est muet depuis (min)', checkNow: 'Vérifier maintenant et envoyer une alerte de test',
    tier: 'Formule', credits: 'Crédits', creditsHint: '(téléchargements en plus de la limite quotidienne)',
    botToken: 'Jeton du bot', botTokenHint: 'Collez un jeton de @BotFather pour connecter ou remplacer ce bot sans modifier de fichiers sur le serveur. Il est vérifié auprès de Telegram, stocké chiffré et jamais réaffiché ; le bot redémarre avec lui en une minute.',
    saveToken: 'Enregistrer le jeton', tiers: 'Formules', tiersHint: 'Chaque formule payante a ses limites (0 = pas de limite en plus). Les offres ci-dessous vendent une formule pour un nombre de jours.',
    tierName: 'Nom', tierDaily: 'Téléchargements par jour (0 = illimité)', tierMaxMb: 'Fichier max, Mo (0 = limite du serveur)', tierStorageMb: 'Stockage de fichiers, Mo (0 = sans quota)',
    tierPriority: 'File prioritaire', tierNoAds: 'Sans publicité', tierKeyPrompt: 'ID court de la nouvelle formule (lettres latines, ex. gold) :', addTier: 'Ajouter une formule',
    tierPlatforms: 'Plateformes incluses (toutes cochées = toutes)',
    botPlatforms: 'Plateformes de ce bot', alertEmails: 'Adresses e-mail des alertes', alertEmailFrom: 'Adresse d’expéditeur',
    alertEmailProvider: 'Service d’e-mail', alertEmailKey: 'Clé API du service d’e-mail',
    alertEmailHint: 'Le serveur envoie les e-mails via une API HTTPS (SendGrid ou Resend ; l’offre gratuite suffit). L’expéditeur doit être vérifié dans ce service. La clé est stockée chiffrée.',
    adClicks: '{count} clics', adWeight: 'Poids (fréquence par rapport aux autres)', adMaxViews: 'Arrêter après vues (0 = sans limite)',
    adBots: 'Afficher dans les bots', adLanguages: 'Seulement pour les langues (vide = toutes)', adsEvery: 'Afficher une pub tous les N téléchargements d’un utilisateur',
    
    
    
    fileView: 'Voir', fileDownload: 'Télécharger', fileClose: 'Fermer', noPreview: 'Ce type de fichier ne peut pas être affiché ici. Utilisez Télécharger pour l’ouvrir.', userData: 'Données de l’utilisateur', jobChannel: 'Auteur', jobDuration: 'Durée', jobViews: 'Vues', jobLikes: 'J’aime', jobItems: 'Éléments', jobFormat: 'Format', jobCompleted: 'Terminé', jobLink: 'Lien', fileLabel: 'Fichier', jobDescription: 'Description', jobNoFiles: 'Aucun fichier enregistré pour cette tâche (demande d’infos, échec ou fichiers déjà supprimés).', userName: 'Nom', addChannel: 'Ajouter un autre canal', channelsHint: 'Les utilisateurs doivent rejoindre tous les canaux de la liste (jusqu’à 10). Le bot doit être administrateur de chacun ; Vérifier affiche le résultat pour chaque canal et bot.', media_retention_days: 'Conservation des médias téléchargés · jours', retention_days: 'Conservation des fichiers envoyés · jours', channel: 'Canal', channelPageHint: 'Canal public des bots : publier, programmer, modifier, épingler et supprimer', channelConnect: 'Connecter le canal', channelConnectHint: 'Ajoutez le bot au canal comme administrateur pouvant publier (et modifier, supprimer, épingler), puis indiquez le canal ici.', channelPostingBot: 'Bot qui publie', saveAndCheck: 'Enregistrer et vérifier', channelPrivate: 'canal privé', channelSubscribers: 'abonnés', rightPost: 'publier', rightEdit: 'modifier', rightDelete: 'supprimer', rightPin: 'épingler', channelNotAdmin: 'Le bot n’est pas administrateur de ce canal : ajoutez-le dans Paramètres du canal → Administrateurs.', channelEditPost: 'Modifier la publication', channelNewPost: 'Nouvelle publication', channelComposeHint: 'Texte mis en forme, photo ou vidéo, boutons-liens ; maintenant ou à une heure fixée.', addPhotoOrVideo: 'Ajouter photo ou vidéo', channelButtons: 'Boutons sous la publication', addButton: 'Ajouter un bouton', channelWhen: 'Quand', channelNow: 'Maintenant', channelLater: 'À une heure fixée', channelConnectFirst: 'Connectez d’abord le canal', channelSchedule: 'Programmer', channelPublishNow: 'Publier maintenant', channelPosts: 'Publications du canal', channelViewsNote: 'La Bot API de Telegram ne donne pas les vues ; ouvrez la publication dans Telegram.', cp_scheduled: 'Programmée', cp_sending: 'Envoi', cp_published: 'Publiée', cp_failed: 'Échec', pinned: 'épinglée', pin: 'Épingler', unpin: 'Désépingler', edit: 'Modifier', channelConfirmDelete: 'Supprimer cette publication du canal ?', channelConfirmCancel: 'Annuler cette publication programmée ?', channelDelete: 'Supprimer du canal', cancel: 'Annuler', openInTelegram: 'Ouvrir dans Telegram', channelAllBots: 'Tous les bots', channelPostsFrom: 'publie', channelBots: 'Bots de ce canal', channelBotAdmin: 'Administrateur du canal', channelNoBots: 'Aucun bot connecté : ajoutez-les sur la page Bots.', channelPostingAs: 'Les publications sont faites par {bot}.', channelNoPoster: 'Aucun bot choisi ne peut publier ici : nommez-en un administrateur avec le droit de publier.',
  },
  pt: {
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    reports: 'Relatórios', reportsHint: 'Números diários, semanais e mensais por bot, serviço e plataforma',
    period_day: 'Dias', period_week: 'Semanas', period_month: 'Meses', allBots: 'Todos os bots', period: 'Período',
    rDownloads: 'Downloads', rUploads: 'Envios', permanent: 'permanente', makePermanent: 'Tornar permanente',
    paymentSource: 'Origem', referralCredits: 'Mais créditos (downloads extras) por recompensa', bot: 'Bot',
    newUsersPeriod: 'Novos usuários', activeUsersPeriod: 'Usuários ativos', errorRate: 'Taxa de erros', storageUsed: 'Armazenamento usado',
    completedFailed: 'Concluídos e com falha', byPlatform: 'Por plataforma', byBot: 'Por bot', byService: 'Por serviço',
    failedByPlatform: 'Falhas por plataforma', topErrors: 'Erros mais frequentes', revenueByMethod: 'Receita por forma de pagamento',
    reportRules: 'Regras de cálculo: períodos são dias, semanas ISO e meses em UTC; taxa de erros = com falha / (concluídos + com falha); usuários ativos = quem iniciou uma tarefa no período; receita = pedidos pagos pela data do pagamento, sem reembolsos (Stars em Stars, cartões e cripto em USD). O CSV usa os mesmos números.',
    translations: 'Traduções', translationsHint: 'Altere qualquer texto dos bots em qualquer idioma e ative ou desative idiomas, sem mexer no código. Um campo vazio volta ao texto original. Marcadores como {count} devem permanecer.',
    editedTexts: '{count} editados', narrowSearch: '{count} textos correspondem: refine a busca para ver o resto.',
    monitoring: 'Monitoramento e alertas', monitoringHint: 'A cada 5 minutos a plataforma verifica o disco, os downloads com falha, os bots silenciosos e a fila, e envia alertas (no máximo um por hora por problema).',
    problemsFound: '{count} problema(s)', allGood: 'Tudo certo', diskFree: 'Disco: {free} GB livres de {total} GB', lastCheck: 'verificado {date}',
    alertChat: 'Chat do Telegram para alertas', alertChatHint: 'Seu ID do Telegram ou o ID de um grupo (-100…). Inicie um dos bots lá primeiro.',
    diskMinGb: 'Alertar abaixo deste espaço livre (GB)', errorRateAlert: 'Alertar acima desta taxa de falhas (%)', queueMinutes: 'Alertar se uma tarefa espera mais de (min)',
    botSilentMinutes: 'Alertar se um bot fica em silêncio por (min)', checkNow: 'Verificar agora e enviar um alerta de teste',
    tier: 'Plano', credits: 'Créditos', creditsHint: '(downloads extras além do limite diário)',
    botToken: 'Token do bot', botTokenHint: 'Cole um token do @BotFather para conectar ou trocar este bot sem editar arquivos no servidor. Ele é verificado no Telegram, guardado criptografado e não é mostrado de novo; o bot reinicia com ele em até um minuto.',
    saveToken: 'Salvar token', tiers: 'Planos', tiersHint: 'Cada plano pago tem os seus limites (0 = sem limite extra). As ofertas abaixo vendem um plano por um número de dias.',
    tierName: 'Nome', tierDaily: 'Downloads por dia (0 = ilimitado)', tierMaxMb: 'Arquivo máximo, MB (0 = limite do servidor)', tierStorageMb: 'Armazenamento de arquivos, MB (0 = sem cota)',
    tierPriority: 'Fila prioritária', tierNoAds: 'Sem anúncios', tierKeyPrompt: 'ID curto do novo plano (letras latinas, ex.: gold):', addTier: 'Adicionar plano',
    tierPlatforms: 'Plataformas incluídas (todas marcadas = todas)',
    botPlatforms: 'Plataformas deste bot', alertEmails: 'E-mails para alertas', alertEmailFrom: 'Endereço do remetente',
    alertEmailProvider: 'Serviço de e-mail', alertEmailKey: 'Chave de API do serviço de e-mail',
    alertEmailHint: 'O servidor envia e-mails por uma API HTTPS (SendGrid ou Resend; o plano gratuito basta). O remetente precisa estar verificado nesse serviço. A chave é guardada criptografada.',
    adClicks: '{count} cliques', adWeight: 'Peso (frequência em relação aos outros)', adMaxViews: 'Parar após exibições (0 = sem limite)',
    adBots: 'Mostrar nos bots', adLanguages: 'Só para idiomas (vazio = todos)', adsEvery: 'Mostrar um anúncio a cada N downloads de um usuário',
    
    
    
    fileView: 'Ver', fileDownload: 'Baixar', fileClose: 'Fechar', noPreview: 'Este tipo de arquivo não pode ser mostrado aqui. Use Baixar para abri-lo.', userData: 'Dados do usuário', jobChannel: 'Autor', jobDuration: 'Duração', jobViews: 'Visualizações', jobLikes: 'Curtidas', jobItems: 'Itens', jobFormat: 'Formato', jobCompleted: 'Concluído', jobLink: 'Link', fileLabel: 'Arquivo', jobDescription: 'Descrição', jobNoFiles: 'Nenhum arquivo salvo para esta tarefa (pedido de informações, falha ou arquivos já removidos).', userName: 'Nome', addChannel: 'Adicionar outro canal', channelsHint: 'Os usuários precisam entrar em todos os canais da lista (até 10). O bot deve ser administrador em cada um; Verificar mostra o resultado de cada canal e bot.', media_retention_days: 'Guardar mídias baixadas · dias', retention_days: 'Guardar arquivos enviados · dias', channel: 'Canal', channelPageHint: 'Canal público dos bots: publicar, agendar, editar, fixar e apagar posts', channelConnect: 'Conectar o canal', channelConnectHint: 'Adicione o bot ao canal como administrador com permissão para publicar (e editar, apagar, fixar) e informe o canal aqui.', channelPostingBot: 'Bot que publica', saveAndCheck: 'Salvar e verificar', channelPrivate: 'canal privado', channelSubscribers: 'inscritos', rightPost: 'publicar', rightEdit: 'editar', rightDelete: 'apagar', rightPin: 'fixar', channelNotAdmin: 'O bot não é administrador deste canal: adicione-o em Configurações do canal → Administradores.', channelEditPost: 'Editar post', channelNewPost: 'Novo post', channelComposeHint: 'Texto formatado, foto ou vídeo, botões com link; publicar agora ou num horário.', addPhotoOrVideo: 'Adicionar foto ou vídeo', channelButtons: 'Botões sob o post', addButton: 'Adicionar botão', channelWhen: 'Quando', channelNow: 'Agora', channelLater: 'Num horário definido', channelConnectFirst: 'Conecte o canal primeiro', channelSchedule: 'Agendar', channelPublishNow: 'Publicar agora', channelPosts: 'Posts do canal', channelViewsNote: 'A Bot API do Telegram não fornece visualizações; abra o post no Telegram.', cp_scheduled: 'Agendado', cp_sending: 'Enviando', cp_published: 'Publicado', cp_failed: 'Falha', pinned: 'fixado', pin: 'Fixar', unpin: 'Desafixar', edit: 'Editar', channelConfirmDelete: 'Apagar este post do canal?', channelConfirmCancel: 'Cancelar este post agendado?', channelDelete: 'Apagar do canal', cancel: 'Cancelar', openInTelegram: 'Abrir no Telegram', channelAllBots: 'Todos os bots', channelPostsFrom: 'publica', channelBots: 'Bots deste canal', channelBotAdmin: 'Administrador do canal', channelNoBots: 'Ainda não há bots conectados: adicione-os na página Bots.', channelPostingAs: 'Quem publica é {bot}.', channelNoPoster: 'Nenhum bot escolhido pode publicar aqui: torne um deles administrador com permissão para publicar.',
  },
  ar: {
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    reports: 'التقارير', reportsHint: 'أرقام يومية وأسبوعية وشهرية حسب البوت والخدمة والمنصة',
    period_day: 'أيام', period_week: 'أسابيع', period_month: 'أشهر', allBots: 'كل البوتات', period: 'الفترة',
    rDownloads: 'التنزيلات', rUploads: 'الرفع', permanent: 'دائم', makePermanent: 'اجعله دائمًا',
    paymentSource: 'المصدر', referralCredits: 'إضافة أرصدة (تنزيلات إضافية) لكل مكافأة', bot: 'البوت',
    newUsersPeriod: 'مستخدمون جدد', activeUsersPeriod: 'مستخدمون نشطون', errorRate: 'نسبة الأخطاء', storageUsed: 'التخزين المستخدم',
    completedFailed: 'ناجحة وفاشلة', byPlatform: 'حسب المنصة', byBot: 'حسب البوت', byService: 'حسب الخدمة',
    failedByPlatform: 'الإخفاقات حسب المنصة', topErrors: 'الأخطاء الأكثر تكرارًا', revenueByMethod: 'الإيرادات حسب طريقة الدفع',
    reportRules: 'قواعد الحساب: الفترات أيام وأسابيع ISO وأشهر بتوقيت UTC؛ نسبة الأخطاء = الفاشلة / (الناجحة + الفاشلة)؛ المستخدمون النشطون = من بدأ مهمة في الفترة؛ الإيرادات = الطلبات المدفوعة حسب وقت الدفع دون المستردة (Stars بالنجوم، والبطاقات والعملات الرقمية بالدولار). يستخدم ملف CSV الأرقام نفسها.',
    translations: 'الترجمات', translationsHint: 'غيّر أي نص للبوتات بأي لغة وفعّل اللغات أو أوقفها دون تعديل الكود. الحقل الفارغ يعيد النص الأصلي. يجب إبقاء العناصر مثل {count}.',
    editedTexts: 'تم تعديل {count}', narrowSearch: 'تطابق {count} نصًا: ضيّق البحث لرؤية البقية.',
    monitoring: 'المراقبة والتنبيهات', monitoringHint: 'كل 5 دقائق تفحص المنصة مساحة القرص والتنزيلات الفاشلة والبوتات الصامتة وقائمة الانتظار، وترسل تنبيهات (مرة في الساعة كحد أقصى لكل مشكلة).',
    problemsFound: '{count} مشكلة', allGood: 'كل شيء جيد', diskFree: 'القرص: {free} غيغابايت متاحة من {total}', lastCheck: 'آخر فحص {date}',
    alertChat: 'محادثة تيليغرام للتنبيهات', alertChatHint: 'معرّفك في تيليغرام أو معرّف مجموعة (-100…). شغّل أحد البوتات هناك أولًا.',
    diskMinGb: 'تنبيه عند مساحة حرة أقل من (غيغابايت)', errorRateAlert: 'تنبيه عند تنزيلات فاشلة أكثر من (%)', queueMinutes: 'تنبيه إذا انتظرت مهمة أكثر من (دقيقة)',
    botSilentMinutes: 'تنبيه إذا صمت بوت لمدة (دقيقة)', checkNow: 'افحص الآن وأرسل تنبيهًا تجريبيًا',
    tier: 'الباقة', credits: 'الأرصدة', creditsHint: '(تنزيلات إضافية فوق الحد اليومي)',
    botToken: 'رمز البوت', botTokenHint: 'الصق رمزًا من @BotFather لربط هذا البوت أو استبداله دون تعديل ملفات على الخادم. يُتحقق منه لدى تيليغرام ويُخزّن مشفرًا ولا يُعرض مجددًا؛ يعيد البوت التشغيل به خلال دقيقة.',
    saveToken: 'حفظ الرمز', tiers: 'الباقات', tiersHint: 'لكل باقة مدفوعة حدودها (0 = بلا حد إضافي). العروض أدناه تبيع باقة لعدد من الأيام.',
    tierName: 'الاسم', tierDaily: 'تنزيلات يوميًا (0 = بلا حد)', tierMaxMb: 'أكبر ملف، ميغابايت (0 = حد الخادم)', tierStorageMb: 'تخزين الملفات، ميغابايت (0 = بلا حصة)',
    tierPriority: 'قائمة أولوية', tierNoAds: 'بدون إعلانات', tierKeyPrompt: 'معرّف قصير للباقة الجديدة (أحرف لاتينية مثل gold):', addTier: 'إضافة باقة',
    tierPlatforms: 'المنصات المشمولة (تحديد الكل = الكل)',
    botPlatforms: 'منصات هذا البوت', alertEmails: 'عناوين البريد للتنبيهات', alertEmailFrom: 'عنوان المرسل',
    alertEmailProvider: 'خدمة البريد', alertEmailKey: 'مفتاح API لخدمة البريد',
    alertEmailHint: 'يرسل الخادم البريد عبر واجهة HTTPS (SendGrid أو Resend؛ تكفي الخطة المجانية). يجب توثيق عنوان المرسل في تلك الخدمة. يُخزّن المفتاح مشفرًا.',
    adClicks: '{count} نقرة', adWeight: 'الوزن (التكرار مقارنة بالإعلانات الأخرى)', adMaxViews: 'إيقاف بعد عدد مشاهدات (0 = بلا حد)',
    adBots: 'العرض في البوتات', adLanguages: 'للغات فقط (فارغ = الكل)', adsEvery: 'عرض إعلان مع كل N تنزيلات للمستخدم',
    
    
    
    fileView: 'عرض', fileDownload: 'تنزيل', fileClose: 'إغلاق', noPreview: 'لا يمكن عرض هذا النوع من الملفات هنا. استخدم «تنزيل» لفتحه.', userData: 'بيانات المستخدم', jobChannel: 'الناشر', jobDuration: 'المدة', jobViews: 'المشاهدات', jobLikes: 'الإعجابات', jobItems: 'العناصر', jobFormat: 'الصيغة', jobCompleted: 'انتهت', jobLink: 'الرابط', fileLabel: 'الملف', jobDescription: 'الوصف', jobNoFiles: 'لا توجد ملفات محفوظة لهذه المهمة (طلب معلومات أو فشل أو حُذفت الملفات).', userName: 'الاسم', addChannel: 'إضافة قناة أخرى', channelsHint: 'يجب على المستخدمين الانضمام إلى كل القنوات في القائمة (حتى 10). يجب أن يكون البوت مشرفًا في كل قناة؛ يعرض «تحقق» النتيجة لكل قناة وبوت.', media_retention_days: 'مدة حفظ الوسائط المنزّلة · أيام', retention_days: 'مدة حفظ الملفات المرفوعة · أيام', channel: 'القناة', channelPageHint: 'القناة العامة للبوتات: النشر والجدولة والتعديل والتثبيت والحذف', channelConnect: 'ربط القناة', channelConnectHint: 'أضف البوت إلى القناة كمشرف يملك صلاحية النشر (والتعديل والحذف والتثبيت)، ثم أدخل القناة هنا.', channelPostingBot: 'البوت الناشر', saveAndCheck: 'حفظ وتحقق', channelPrivate: 'قناة خاصة', channelSubscribers: 'مشترك', rightPost: 'النشر', rightEdit: 'التعديل', rightDelete: 'الحذف', rightPin: 'التثبيت', channelNotAdmin: 'البوت ليس مشرفًا في هذه القناة: أضفه من إعدادات القناة ← المشرفون.', channelEditPost: 'تعديل المنشور', channelNewPost: 'منشور جديد', channelComposeHint: 'نص منسّق، صورة أو فيديو، أزرار روابط؛ النشر الآن أو في وقت محدد.', addPhotoOrVideo: 'إضافة صورة أو فيديو', channelButtons: 'أزرار تحت المنشور', addButton: 'إضافة زر', channelWhen: 'متى', channelNow: 'الآن', channelLater: 'في وقت محدد', channelConnectFirst: 'اربط القناة أولًا', channelSchedule: 'جدولة', channelPublishNow: 'انشر الآن', channelPosts: 'منشورات القناة', channelViewsNote: 'لا توفر Bot API في تيليغرام عدد المشاهدات؛ افتح المنشور في تيليغرام لرؤيتها.', cp_scheduled: 'مجدول', cp_sending: 'قيد الإرسال', cp_published: 'منشور', cp_failed: 'فشل', pinned: 'مثبّت', pin: 'تثبيت', unpin: 'إلغاء التثبيت', edit: 'تعديل', channelConfirmDelete: 'حذف هذا المنشور من القناة؟', channelConfirmCancel: 'إلغاء هذا المنشور المجدول؟', channelDelete: 'حذف من القناة', cancel: 'إلغاء', openInTelegram: 'فتح في تيليغرام', channelAllBots: 'كل البوتات', channelPostsFrom: 'ينشر', channelBots: 'بوتات هذه القناة', channelBotAdmin: 'مشرف في القناة', channelNoBots: 'لا توجد بوتات متصلة بعد: أضفها من صفحة البوتات.', channelPostingAs: 'ينشر المنشورات {bot}.', channelNoPoster: 'لا يستطيع أي بوت مختار النشر هنا: اجعل أحدها مشرفًا بصلاحية النشر.',
  },
  he: {
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    reports: 'דוחות', reportsHint: 'נתונים יומיים, שבועיים וחודשיים לפי בוט, שירות ופלטפורמה',
    period_day: 'ימים', period_week: 'שבועות', period_month: 'חודשים', allBots: 'כל הבוטים', period: 'תקופה',
    rDownloads: 'הורדות', rUploads: 'העלאות', permanent: 'קבוע', makePermanent: 'להפוך לקבוע',
    paymentSource: 'מקור', referralCredits: 'בנוסף קרדיטים (הורדות נוספות) לכל פרס', bot: 'בוט',
    newUsersPeriod: 'משתמשים חדשים', activeUsersPeriod: 'משתמשים פעילים', errorRate: 'שיעור שגיאות', storageUsed: 'אחסון בשימוש',
    completedFailed: 'הצליחו ונכשלו', byPlatform: 'לפי פלטפורמה', byBot: 'לפי בוט', byService: 'לפי שירות',
    failedByPlatform: 'כישלונות לפי פלטפורמה', topErrors: 'השגיאות הנפוצות', revenueByMethod: 'הכנסות לפי אמצעי תשלום',
    reportRules: 'כללי חישוב: תקופות הן ימים, שבועות ISO וחודשים לפי UTC; שיעור שגיאות = נכשלו / (הצליחו + נכשלו); משתמשים פעילים = מי שהתחיל משימה בתקופה; הכנסות = הזמנות ששולמו לפי זמן התשלום, בלי החזרים (Stars בכוכבים, כרטיסים וקריפטו בדולרים). קובץ ה־CSV משתמש באותם נתונים.',
    translations: 'תרגומים', translationsHint: 'שנו כל טקסט של הבוטים בכל שפה והפעילו או כבו שפות, בלי לגעת בקוד. שדה ריק מחזיר את הטקסט המקורי. יש להשאיר משתנים כמו {count}.',
    editedTexts: '{count} נערכו', narrowSearch: '{count} טקסטים מתאימים: צמצמו את החיפוש כדי לראות את השאר.',
    monitoring: 'ניטור והתראות', monitoringHint: 'כל 5 דקות הפלטפורמה בודקת את הדיסק, הורדות שנכשלו, בוטים שקטים ואת התור, ושולחת התראות (לכל היותר פעם בשעה לכל בעיה).',
    problemsFound: '{count} בעיות', allGood: 'הכול תקין', diskFree: 'דיסק: {free} GB פנויים מתוך {total} GB', lastCheck: 'נבדק {date}',
    alertChat: 'צ׳אט טלגרם להתראות', alertChatHint: 'מזהה הטלגרם שלכם או מזהה קבוצה (-100…). הפעילו שם קודם את אחד הבוטים.',
    diskMinGb: 'התראה מתחת לנפח פנוי (GB)', errorRateAlert: 'התראה מעל שיעור הורדות שנכשלו (%)', queueMinutes: 'התראה כשמשימה ממתינה יותר מ־(דקות)',
    botSilentMinutes: 'התראה כשבוט שקט במשך (דקות)', checkNow: 'בדיקה עכשיו ושליחת התראת ניסיון',
    tier: 'מסלול', credits: 'קרדיטים', creditsHint: '(הורדות נוספות מעבר למגבלה היומית)',
    botToken: 'טוקן הבוט', botTokenHint: 'הדביקו טוקן מ־@BotFather כדי לחבר או להחליף את הבוט בלי לערוך קבצים בשרת. הוא נבדק מול טלגרם, נשמר מוצפן ולא מוצג שוב; הבוט מופעל מחדש איתו תוך דקה.',
    saveToken: 'שמירת טוקן', tiers: 'מסלולים', tiersHint: 'לכל מסלול בתשלום מגבלות משלו (0 = בלי מגבלה נוספת). ההצעות למטה מוכרות מסלול למספר ימים.',
    tierName: 'שם', tierDaily: 'הורדות ביום (0 = ללא הגבלה)', tierMaxMb: 'קובץ מרבי, MB (0 = מגבלת השרת)', tierStorageMb: 'אחסון קבצים, MB (0 = בלי מכסה)',
    tierPriority: 'תור עדיפות', tierNoAds: 'בלי פרסומות', tierKeyPrompt: 'מזהה קצר למסלול החדש (אותיות לטיניות, למשל gold):', addTier: 'הוספת מסלול',
    tierPlatforms: 'פלטפורמות כלולות (כולן מסומנות = הכול)',
    botPlatforms: 'הפלטפורמות של הבוט הזה', alertEmails: 'כתובות דוא״ל להתראות', alertEmailFrom: 'כתובת השולח',
    alertEmailProvider: 'שירות דוא״ל', alertEmailKey: 'מפתח API של שירות הדוא״ל',
    alertEmailHint: 'השרת שולח דוא״ל דרך API ב־HTTPS (SendGrid או Resend; מספיק המסלול החינמי). יש לאמת את כתובת השולח בשירות. המפתח נשמר מוצפן.',
    adClicks: '{count} קליקים', adWeight: 'משקל (תדירות ביחס לאחרות)', adMaxViews: 'עצירה אחרי צפיות (0 = בלי הגבלה)',
    adBots: 'הצגה בבוטים', adLanguages: 'רק לשפות (ריק = כולן)', adsEvery: 'להציג פרסומת כל N הורדות של משתמש',
    
    
    
    fileView: 'צפייה', fileDownload: 'הורדה', fileClose: 'סגירה', noPreview: 'אי אפשר להציג כאן סוג קובץ זה. השתמשו ב«הורדה» כדי לפתוח אותו.', userData: 'נתוני המשתמש', jobChannel: 'יוצר', jobDuration: 'משך', jobViews: 'צפיות', jobLikes: 'לייקים', jobItems: 'פריטים', jobFormat: 'פורמט', jobCompleted: 'הסתיים', jobLink: 'קישור', fileLabel: 'קובץ', jobDescription: 'תיאור', jobNoFiles: 'אין קבצים שמורים למשימה זו (בקשת מידע, כישלון או שהקבצים כבר נמחקו).', userName: 'שם', addChannel: 'הוספת ערוץ נוסף', channelsHint: 'המשתמשים חייבים להצטרף לכל הערוצים ברשימה (עד 10). הבוט חייב להיות מנהל בכל אחד מהם; «בדיקה» מציגה תוצאה לכל ערוץ ובוט.', media_retention_days: 'שמירת מדיה שהורדה · ימים', retention_days: 'שמירת קבצים שהועלו · ימים', channel: 'ערוץ', channelPageHint: 'הערוץ הציבורי של הבוטים: פרסום, תזמון, עריכה, הצמדה ומחיקה', channelConnect: 'חיבור הערוץ', channelConnectHint: 'הוסיפו את הבוט לערוץ כמנהל עם הרשאת פרסום (ועריכה, מחיקה, הצמדה), ואז הזינו את הערוץ כאן.', channelPostingBot: 'הבוט שמפרסם', saveAndCheck: 'שמירה ובדיקה', channelPrivate: 'ערוץ פרטי', channelSubscribers: 'מנויים', rightPost: 'פרסום', rightEdit: 'עריכה', rightDelete: 'מחיקה', rightPin: 'הצמדה', channelNotAdmin: 'הבוט אינו מנהל בערוץ: הוסיפו אותו בהגדרות הערוץ ← מנהלים.', channelEditPost: 'עריכת פוסט', channelNewPost: 'פוסט חדש', channelComposeHint: 'טקסט מעוצב, תמונה או וידאו, כפתורי קישור; פרסום עכשיו או בזמן קבוע.', addPhotoOrVideo: 'הוספת תמונה או וידאו', channelButtons: 'כפתורים מתחת לפוסט', addButton: 'הוספת כפתור', channelWhen: 'מתי', channelNow: 'עכשיו', channelLater: 'בזמן קבוע', channelConnectFirst: 'חברו קודם את הערוץ', channelSchedule: 'תזמון', channelPublishNow: 'פרסום עכשיו', channelPosts: 'פוסטים בערוץ', channelViewsNote: 'ה־Bot API של טלגרם לא מספק צפיות; פתחו את הפוסט בטלגרם.', cp_scheduled: 'מתוזמן', cp_sending: 'נשלח', cp_published: 'פורסם', cp_failed: 'נכשל', pinned: 'מוצמד', pin: 'הצמדה', unpin: 'ביטול הצמדה', edit: 'עריכה', channelConfirmDelete: 'למחוק את הפוסט מהערוץ?', channelConfirmCancel: 'לבטל את הפוסט המתוזמן?', channelDelete: 'מחיקה מהערוץ', cancel: 'ביטול', openInTelegram: 'פתיחה בטלגרם', channelAllBots: 'כל הבוטים', channelPostsFrom: 'מפרסם', channelBots: 'הבוטים של הערוץ', channelBotAdmin: 'מנהל בערוץ', channelNoBots: 'עדיין אין בוטים מחוברים: הוסיפו אותם בעמוד הבוטים.', channelPostingAs: 'הפוסטים מתפרסמים על ידי {bot}.', channelNoPoster: 'אף בוט שנבחר לא יכול לפרסם כאן: הפכו אחד מהם למנהל עם הרשאת פרסום.',
  },
  zh: {
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    reports: '报表', reportsHint: '按机器人、服务和平台统计的每日、每周和每月数据',
    period_day: '按天', period_week: '按周', period_month: '按月', allBots: '所有机器人', period: '周期',
    rDownloads: '下载', rUploads: '上传', permanent: '永久', makePermanent: '设为永久',
    paymentSource: '来源', referralCredits: '每次奖励额外赠送次数（额外下载）', bot: '机器人',
    newUsersPeriod: '新用户', activeUsersPeriod: '活跃用户', errorRate: '错误率', storageUsed: '已用存储',
    completedFailed: '成功与失败', byPlatform: '按平台', byBot: '按机器人', byService: '按服务',
    failedByPlatform: '各平台失败', topErrors: '最常见错误', revenueByMethod: '按支付方式的收入',
    reportRules: '计算规则：周期为 UTC 的自然日、ISO 周和自然月；错误率 = 失败 / (成功 + 失败)；活跃用户 = 在该周期内发起过任务的用户；收入 = 按支付时间统计的已付订单，不含退款（Stars 以 Stars 计，银行卡和加密货币以美元计）。CSV 导出使用相同数据。',
    translations: '翻译', translationsHint: '无需改代码即可修改机器人在任何语言下的任何文字，并开关语言。留空则恢复原文。必须保留 {count} 等占位符。',
    editedTexts: '已修改 {count} 条', narrowSearch: '匹配 {count} 条：请缩小搜索范围查看其余内容。',
    monitoring: '监控与告警', monitoringHint: '平台每 5 分钟检查磁盘、失败的下载、无响应的机器人和队列，并发送告警（同一问题每小时最多一次）。',
    problemsFound: '{count} 个问题', allGood: '一切正常', diskFree: '磁盘：{total} GB 中空闲 {free} GB', lastCheck: '检查于 {date}',
    alertChat: '接收告警的 Telegram 聊天', alertChatHint: '您的 Telegram ID 或群组 ID（-100…）。请先在那里启动一个机器人。',
    diskMinGb: '空闲磁盘低于（GB）时告警', errorRateAlert: '失败下载高于（%）时告警', queueMinutes: '任务等待超过（分钟）时告警',
    botSilentMinutes: '机器人无响应超过（分钟）时告警', checkNow: '立即检查并发送测试告警',
    tier: '套餐等级', credits: '额外次数', creditsHint: '（超出每日限额的额外下载）',
    botToken: '机器人令牌', botTokenHint: '粘贴来自 @BotFather 的令牌，无需修改服务器文件即可接入或更换此机器人。令牌会经 Telegram 校验、加密保存且不再显示；机器人会在一分钟内用它重启。',
    saveToken: '保存令牌', tiers: '套餐等级', tiersHint: '每个付费等级都有自己的限制（0 = 不额外限制）。下方的方案按天数出售某个等级。',
    tierName: '名称', tierDaily: '每日下载数（0 = 不限）', tierMaxMb: '最大文件 MB（0 = 服务器限制）', tierStorageMb: '文件存储 MB（0 = 无配额）',
    tierPriority: '优先队列', tierNoAds: '无广告', tierKeyPrompt: '新等级的短 ID（拉丁字母，例如 gold）：', addTier: '添加等级',
    tierPlatforms: '包含的平台（全选 = 全部）',
    botPlatforms: '此机器人支持的平台', alertEmails: '告警邮箱', alertEmailFrom: '发件人地址',
    alertEmailProvider: '邮件服务', alertEmailKey: '邮件服务 API 密钥',
    alertEmailHint: '服务器通过 HTTPS 邮件 API 发信（SendGrid 或 Resend，免费套餐即可）。发件人地址需在该服务中验证。密钥加密保存。',
    adClicks: '{count} 次点击', adWeight: '权重（相对其他广告的出现频率）', adMaxViews: '展示达到该数后停止（0 = 不限）',
    adBots: '在哪些机器人中显示', adLanguages: '仅限语言（留空 = 全部）', adsEvery: '用户每下载 N 次显示一次广告',
    
    
    
    fileView: '查看', fileDownload: '下载', fileClose: '关闭', noPreview: '此类文件无法在此预览，请点击「下载」打开。', userData: '用户资料', jobChannel: '作者', jobDuration: '时长', jobViews: '播放量', jobLikes: '点赞', jobItems: '条目', jobFormat: '格式', jobCompleted: '完成时间', jobLink: '链接', fileLabel: '文件', jobDescription: '描述', jobNoFiles: '此任务没有保存的文件（信息查询、失败或文件已删除）。', userName: '名称', addChannel: '再添加一个频道', channelsHint: '用户必须加入列表中的所有频道（最多 10 个）。机器人必须是每个频道的管理员；「检查」会显示每个频道和机器人的结果。', media_retention_days: '下载的媒体保存天数', retention_days: '上传的文件保存天数', channel: '频道', channelPageHint: '机器人的公开频道：发布、定时、编辑、置顶和删除帖子', channelConnect: '连接频道', channelConnectHint: '将机器人添加为频道管理员并授予发布（以及编辑、删除、置顶）权限，然后在此输入频道。', channelPostingBot: '发布用的机器人', saveAndCheck: '保存并检查', channelPrivate: '私有频道', channelSubscribers: '订阅者', rightPost: '发布', rightEdit: '编辑', rightDelete: '删除', rightPin: '置顶', channelNotAdmin: '机器人不是该频道的管理员：请在频道设置 → 管理员中添加。', channelEditPost: '编辑帖子', channelNewPost: '新帖子', channelComposeHint: '带格式的文字、图片或视频、链接按钮；立即发布或定时发布。', addPhotoOrVideo: '添加图片或视频', channelButtons: '帖子下方的按钮', addButton: '添加按钮', channelWhen: '时间', channelNow: '立即', channelLater: '定时', channelConnectFirst: '请先连接频道', channelSchedule: '定时发布', channelPublishNow: '立即发布', channelPosts: '频道帖子', channelViewsNote: 'Telegram Bot API 不提供帖子浏览量，请在 Telegram 中打开帖子查看。', cp_scheduled: '已定时', cp_sending: '发送中', cp_published: '已发布', cp_failed: '失败', pinned: '已置顶', pin: '置顶', unpin: '取消置顶', edit: '编辑', channelConfirmDelete: '从频道删除此帖子？', channelConfirmCancel: '取消此定时帖子？', channelDelete: '从频道删除', cancel: '取消', openInTelegram: '在 Telegram 中打开', channelAllBots: '所有机器人', channelPostsFrom: '负责发布', channelBots: '此频道的机器人', channelBotAdmin: '频道管理员', channelNoBots: '还没有连接机器人：请在「机器人」页面添加。', channelPostingAs: '由 {bot} 发布帖子。', channelNoPoster: '所选机器人都无法在此发布：请将其中一个设为有发布权限的管理员。',
  },
  hi: {
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    reports: 'रिपोर्ट', reportsHint: 'बॉट, सेवा और प्लेटफ़ॉर्म के हिसाब से दैनिक, साप्ताहिक और मासिक आँकड़े',
    period_day: 'दिन', period_week: 'सप्ताह', period_month: 'महीने', allBots: 'सभी बॉट', period: 'अवधि',
    rDownloads: 'डाउनलोड', rUploads: 'अपलोड', permanent: 'स्थायी', makePermanent: 'स्थायी बनाएँ',
    paymentSource: 'स्रोत', referralCredits: 'हर इनाम पर अतिरिक्त क्रेडिट (अतिरिक्त डाउनलोड)', bot: 'बॉट',
    newUsersPeriod: 'नए उपयोगकर्ता', activeUsersPeriod: 'सक्रिय उपयोगकर्ता', errorRate: 'त्रुटि दर', storageUsed: 'इस्तेमाल हुआ स्टोरेज',
    completedFailed: 'सफल और असफल', byPlatform: 'प्लेटफ़ॉर्म के अनुसार', byBot: 'बॉट के अनुसार', byService: 'सेवा के अनुसार',
    failedByPlatform: 'प्लेटफ़ॉर्म के अनुसार विफलताएँ', topErrors: 'सबसे आम त्रुटियाँ', revenueByMethod: 'भुगतान तरीक़े के अनुसार आय',
    reportRules: 'गणना के नियम: अवधि UTC में दिन, ISO सप्ताह और महीने हैं; त्रुटि दर = असफल / (सफल + असफल); सक्रिय उपयोगकर्ता = जिन्होंने अवधि में कोई काम शुरू किया; आय = भुगतान के समय के अनुसार भुगतान हुए ऑर्डर, रिफ़ंड को छोड़कर (Stars में Stars, कार्ड और क्रिप्टो USD में)। CSV में यही आँकड़े होते हैं।',
    translations: 'अनुवाद', translationsHint: 'बिना कोड बदले किसी भी भाषा में बॉट का कोई भी टेक्स्ट बदलें और भाषाएँ चालू या बंद करें। खाली फ़ील्ड मूल टेक्स्ट वापस लाता है। {count} जैसे प्लेसहोल्डर बने रहने चाहिए।',
    editedTexts: '{count} बदले गए', narrowSearch: '{count} टेक्स्ट मिले: बाक़ी देखने के लिए खोज सीमित करें।',
    monitoring: 'निगरानी और अलर्ट', monitoringHint: 'हर 5 मिनट में प्लेटफ़ॉर्म डिस्क, असफल डाउनलोड, चुप बॉट और कतार जाँचता है और अलर्ट भेजता है (हर समस्या पर घंटे में अधिकतम एक बार)।',
    problemsFound: '{count} समस्या', allGood: 'सब ठीक है', diskFree: 'डिस्क: {total} GB में से {free} GB ख़ाली', lastCheck: 'जाँचा गया {date}',
    alertChat: 'अलर्ट के लिए Telegram चैट', alertChatHint: 'आपकी Telegram ID या किसी समूह की ID (-100…)। पहले वहाँ कोई बॉट शुरू करें।',
    diskMinGb: 'ख़ाली डिस्क इससे कम होने पर अलर्ट (GB)', errorRateAlert: 'असफल डाउनलोड इससे ज़्यादा होने पर अलर्ट (%)', queueMinutes: 'काम इससे ज़्यादा इंतज़ार करे तो अलर्ट (मिनट)',
    botSilentMinutes: 'बॉट इतनी देर चुप रहे तो अलर्ट (मिनट)', checkNow: 'अभी जाँचें और टेस्ट अलर्ट भेजें',
    tier: 'स्तर', credits: 'क्रेडिट', creditsHint: '(दैनिक सीमा से ऊपर अतिरिक्त डाउनलोड)',
    botToken: 'बॉट टोकन', botTokenHint: 'सर्वर पर फ़ाइलें बदले बिना इस बॉट को जोड़ने या बदलने के लिए @BotFather का टोकन चिपकाएँ। इसे Telegram से जाँचा जाता है, एन्क्रिप्ट करके रखा जाता है और फिर कभी नहीं दिखाया जाता; बॉट एक मिनट में इसके साथ फिर शुरू होता है।',
    saveToken: 'टोकन सहेजें', tiers: 'स्तर', tiersHint: 'हर भुगतान वाले स्तर की अपनी सीमाएँ हैं (0 = कोई अतिरिक्त सीमा नहीं)। नीचे के प्लान किसी स्तर को कुछ दिनों के लिए बेचते हैं।',
    tierName: 'नाम', tierDaily: 'रोज़ डाउनलोड (0 = असीमित)', tierMaxMb: 'सबसे बड़ी फ़ाइल, MB (0 = सर्वर सीमा)', tierStorageMb: 'फ़ाइल स्टोरेज, MB (0 = कोई कोटा नहीं)',
    tierPriority: 'प्राथमिकता कतार', tierNoAds: 'बिना विज्ञापन', tierKeyPrompt: 'नए स्तर की छोटी ID (लैटिन अक्षर, जैसे gold):', addTier: 'स्तर जोड़ें',
    tierPlatforms: 'शामिल प्लेटफ़ॉर्म (सब चुने = सभी)',
    botPlatforms: 'इस बॉट के प्लेटफ़ॉर्म', alertEmails: 'अलर्ट के लिए ई-मेल', alertEmailFrom: 'भेजने वाले का पता',
    alertEmailProvider: 'ई-मेल सेवा', alertEmailKey: 'ई-मेल सेवा की API कुंजी',
    alertEmailHint: 'सर्वर HTTPS ई-मेल API से मेल भेजता है (SendGrid या Resend; मुफ़्त प्लान काफ़ी है)। भेजने वाले का पता उस सेवा में सत्यापित होना चाहिए। कुंजी एन्क्रिप्ट करके रखी जाती है।',
    adClicks: '{count} क्लिक', adWeight: 'वज़न (दूसरे विज्ञापनों की तुलना में कितनी बार)', adMaxViews: 'इतने व्यू के बाद रोकें (0 = असीमित)',
    adBots: 'किन बॉट में दिखाएँ', adLanguages: 'सिर्फ़ इन भाषाओं के लिए (खाली = सभी)', adsEvery: 'उपयोगकर्ता के हर N-वें डाउनलोड पर विज्ञापन दिखाएँ',
    
    
    
    fileView: 'देखें', fileDownload: 'डाउनलोड', fileClose: 'बंद करें', noPreview: 'इस प्रकार की फ़ाइल यहाँ नहीं दिखाई जा सकती। खोलने के लिए डाउनलोड करें।', userData: 'उपयोगकर्ता का डेटा', jobChannel: 'लेखक', jobDuration: 'अवधि', jobViews: 'व्यू', jobLikes: 'लाइक', jobItems: 'आइटम', jobFormat: 'फ़ॉर्मैट', jobCompleted: 'पूरा हुआ', jobLink: 'लिंक', fileLabel: 'फ़ाइल', jobDescription: 'विवरण', jobNoFiles: 'इस काम की कोई फ़ाइल सहेजी नहीं गई (जानकारी का अनुरोध, विफलता या फ़ाइलें हटाई जा चुकी हैं)।', userName: 'नाम', addChannel: 'एक और चैनल जोड़ें', channelsHint: 'उपयोगकर्ताओं को सूची के सभी चैनल जॉइन करने होंगे (अधिकतम 10)। बॉट हर चैनल में एडमिन होना चाहिए; «जाँचें» हर चैनल और बॉट का नतीजा दिखाता है।', media_retention_days: 'डाउनलोड मीडिया रखें · दिन', retention_days: 'अपलोड फ़ाइलें रखें · दिन', channel: 'चैनल', channelPageHint: 'बॉट का सार्वजनिक चैनल: पोस्ट करें, शेड्यूल करें, संपादित करें, पिन करें और हटाएँ', channelConnect: 'चैनल जोड़ें', channelConnectHint: 'बॉट को चैनल में पोस्ट (और संपादन, हटाने, पिन) की अनुमति वाला एडमिन बनाएँ, फिर यहाँ चैनल लिखें।', channelPostingBot: 'पोस्ट करने वाला बॉट', saveAndCheck: 'सहेजें और जाँचें', channelPrivate: 'निजी चैनल', channelSubscribers: 'सब्सक्राइबर', rightPost: 'पोस्ट', rightEdit: 'संपादन', rightDelete: 'हटाना', rightPin: 'पिन', channelNotAdmin: 'बॉट इस चैनल का एडमिन नहीं है: चैनल सेटिंग → एडमिन में जोड़ें।', channelEditPost: 'पोस्ट संपादित करें', channelNewPost: 'नई पोस्ट', channelComposeHint: 'फ़ॉर्मैट वाला टेक्स्ट, फ़ोटो या वीडियो, लिंक बटन; अभी या तय समय पर।', addPhotoOrVideo: 'फ़ोटो या वीडियो जोड़ें', channelButtons: 'पोस्ट के नीचे बटन', addButton: 'बटन जोड़ें', channelWhen: 'कब', channelNow: 'अभी', channelLater: 'तय समय पर', channelConnectFirst: 'पहले चैनल जोड़ें', channelSchedule: 'शेड्यूल करें', channelPublishNow: 'अभी पोस्ट करें', channelPosts: 'चैनल की पोस्ट', channelViewsNote: 'Telegram Bot API पोस्ट के व्यू नहीं देता; देखने के लिए पोस्ट Telegram में खोलें।', cp_scheduled: 'शेड्यूल', cp_sending: 'भेजा जा रहा', cp_published: 'पोस्ट हुआ', cp_failed: 'विफल', pinned: 'पिन', pin: 'पिन करें', unpin: 'पिन हटाएँ', edit: 'संपादित करें', channelConfirmDelete: 'यह पोस्ट चैनल से हटाएँ?', channelConfirmCancel: 'यह शेड्यूल पोस्ट रद्द करें?', channelDelete: 'चैनल से हटाएँ', cancel: 'रद्द करें', openInTelegram: 'Telegram में खोलें', channelAllBots: 'सभी बॉट', channelPostsFrom: 'पोस्ट करता है', channelBots: 'इस चैनल के बॉट', channelBotAdmin: 'चैनल का एडमिन', channelNoBots: 'अभी कोई बॉट जुड़ा नहीं है: बॉट पेज पर जोड़ें।', channelPostingAs: 'पोस्ट {bot} करता है।', channelNoPoster: 'चुना गया कोई बॉट यहाँ पोस्ट नहीं कर सकता: किसी एक को पोस्ट की अनुमति वाला एडमिन बनाएँ।',
  },
  bn: {
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    reports: 'রিপোর্ট', reportsHint: 'বট, সেবা ও প্ল্যাটফর্ম অনুযায়ী দৈনিক, সাপ্তাহিক ও মাসিক হিসাব',
    period_day: 'দিন', period_week: 'সপ্তাহ', period_month: 'মাস', allBots: 'সব বট', period: 'সময়কাল',
    rDownloads: 'ডাউনলোড', rUploads: 'আপলোড', permanent: 'স্থায়ী', makePermanent: 'স্থায়ী করুন',
    paymentSource: 'উৎস', referralCredits: 'প্রতি পুরস্কারে অতিরিক্ত ক্রেডিট (বাড়তি ডাউনলোড)', bot: 'বট',
    newUsersPeriod: 'নতুন ব্যবহারকারী', activeUsersPeriod: 'সক্রিয় ব্যবহারকারী', errorRate: 'ত্রুটির হার', storageUsed: 'ব্যবহৃত স্টোরেজ',
    completedFailed: 'সফল ও ব্যর্থ', byPlatform: 'প্ল্যাটফর্ম অনুযায়ী', byBot: 'বট অনুযায়ী', byService: 'সেবা অনুযায়ী',
    failedByPlatform: 'প্ল্যাটফর্ম অনুযায়ী ব্যর্থতা', topErrors: 'সবচেয়ে বেশি ত্রুটি', revenueByMethod: 'পেমেন্ট পদ্ধতি অনুযায়ী আয়',
    reportRules: 'হিসাবের নিয়ম: সময়কাল UTC-তে দিন, ISO সপ্তাহ ও মাস; ত্রুটির হার = ব্যর্থ / (সফল + ব্যর্থ); সক্রিয় ব্যবহারকারী = যারা সময়কালে কোনো কাজ শুরু করেছে; আয় = পেমেন্টের সময় অনুযায়ী পরিশোধিত অর্ডার, রিফান্ড বাদে (Stars-এ Stars, কার্ড ও ক্রিপ্টো USD-তে)। CSV-তে একই হিসাব থাকে।',
    translations: 'অনুবাদ', translationsHint: 'কোড না বদলে যেকোনো ভাষায় বটের যেকোনো লেখা বদলান এবং ভাষা চালু বা বন্ধ করুন। খালি ঘর মূল লেখা ফিরিয়ে আনে। {count}-এর মতো প্লেসহোল্ডার রাখতে হবে।',
    editedTexts: '{count}টি বদলানো', narrowSearch: '{count}টি লেখা মিলেছে: বাকিগুলো দেখতে খোঁজ সংকুচিত করুন।',
    monitoring: 'নজরদারি ও সতর্কতা', monitoringHint: 'প্রতি 5 মিনিটে প্ল্যাটফর্ম ডিস্ক, ব্যর্থ ডাউনলোড, নীরব বট ও সারি পরীক্ষা করে এবং সতর্কতা পাঠায় (প্রতি সমস্যায় ঘণ্টায় সর্বোচ্চ একবার)।',
    problemsFound: '{count}টি সমস্যা', allGood: 'সব ঠিক আছে', diskFree: 'ডিস্ক: {total} GB-এর মধ্যে {free} GB খালি', lastCheck: 'পরীক্ষা {date}',
    alertChat: 'সতর্কতার জন্য Telegram চ্যাট', alertChatHint: 'আপনার Telegram ID বা কোনো গ্রুপের ID (-100…)। আগে সেখানে একটি বট চালু করুন।',
    diskMinGb: 'খালি ডিস্ক এর কম হলে সতর্কতা (GB)', errorRateAlert: 'ব্যর্থ ডাউনলোড এর বেশি হলে সতর্কতা (%)', queueMinutes: 'কাজ এর বেশি অপেক্ষা করলে সতর্কতা (মিনিট)',
    botSilentMinutes: 'বট এতক্ষণ নীরব থাকলে সতর্কতা (মিনিট)', checkNow: 'এখনই পরীক্ষা করে টেস্ট সতর্কতা পাঠান',
    tier: 'স্তর', credits: 'ক্রেডিট', creditsHint: '(দৈনিক সীমার বাইরে বাড়তি ডাউনলোড)',
    botToken: 'বট টোকেন', botTokenHint: 'সার্ভারে ফাইল না বদলে এই বট যুক্ত বা বদলাতে @BotFather-এর টোকেন পেস্ট করুন। এটি Telegram-এ যাচাই হয়, এনক্রিপ্ট করে রাখা হয় এবং আর দেখানো হয় না; বট এক মিনিটের মধ্যে এটি দিয়ে আবার চালু হয়।',
    saveToken: 'টোকেন সংরক্ষণ', tiers: 'স্তর', tiersHint: 'প্রতিটি পেইড স্তরের নিজস্ব সীমা আছে (0 = বাড়তি সীমা নেই)। নিচের প্ল্যানগুলো কিছু দিনের জন্য একটি স্তর বিক্রি করে।',
    tierName: 'নাম', tierDaily: 'দিনে ডাউনলোড (0 = সীমাহীন)', tierMaxMb: 'সবচেয়ে বড় ফাইল, MB (0 = সার্ভারের সীমা)', tierStorageMb: 'ফাইল স্টোরেজ, MB (0 = কোটা নেই)',
    tierPriority: 'অগ্রাধিকার সারি', tierNoAds: 'বিজ্ঞাপন ছাড়া', tierKeyPrompt: 'নতুন স্তরের ছোট ID (ল্যাটিন অক্ষর, যেমন gold):', addTier: 'স্তর যোগ করুন',
    tierPlatforms: 'অন্তর্ভুক্ত প্ল্যাটফর্ম (সব টিক = সব)',
    botPlatforms: 'এই বটের প্ল্যাটফর্ম', alertEmails: 'সতর্কতার ই-মেইল', alertEmailFrom: 'প্রেরকের ঠিকানা',
    alertEmailProvider: 'ই-মেইল সেবা', alertEmailKey: 'ই-মেইল সেবার API কী',
    alertEmailHint: 'সার্ভার HTTPS ই-মেইল API দিয়ে মেইল পাঠায় (SendGrid বা Resend; ফ্রি প্ল্যানই যথেষ্ট)। প্রেরকের ঠিকানা সেই সেবায় যাচাই করা থাকতে হবে। কী এনক্রিপ্ট করে রাখা হয়।',
    adClicks: '{count} ক্লিক', adWeight: 'ওজন (অন্য বিজ্ঞাপনের তুলনায় কতবার)', adMaxViews: 'এত ভিউয়ের পর থামুন (0 = সীমাহীন)',
    adBots: 'যে বটে দেখাবে', adLanguages: 'শুধু এই ভাষাগুলোর জন্য (খালি = সব)', adsEvery: 'ব্যবহারকারীর প্রতি N-তম ডাউনলোডে বিজ্ঞাপন দেখান',
    
    
    
    fileView: 'দেখুন', fileDownload: 'ডাউনলোড', fileClose: 'বন্ধ', noPreview: 'এই ধরনের ফাইল এখানে দেখানো যায় না। খুলতে ডাউনলোড করুন।', userData: 'ব্যবহারকারীর তথ্য', jobChannel: 'লেখক', jobDuration: 'সময়কাল', jobViews: 'ভিউ', jobLikes: 'লাইক', jobItems: 'আইটেম', jobFormat: 'ফরম্যাট', jobCompleted: 'শেষ হয়েছে', jobLink: 'লিংক', fileLabel: 'ফাইল', jobDescription: 'বিবরণ', jobNoFiles: 'এই কাজের কোনো ফাইল সংরক্ষিত নেই (তথ্যের অনুরোধ, ব্যর্থতা বা ফাইল মুছে ফেলা হয়েছে)।', userName: 'নাম', addChannel: 'আরেকটি চ্যানেল যোগ করুন', channelsHint: 'ব্যবহারকারীদের তালিকার সব চ্যানেলে যোগ দিতে হবে (সর্বোচ্চ 10)। প্রতিটি চ্যানেলে বটকে অ্যাডমিন হতে হবে; «যাচাই» প্রতিটি চ্যানেল ও বটের ফল দেখায়।', media_retention_days: 'ডাউনলোড করা মিডিয়া রাখা · দিন', retention_days: 'আপলোড করা ফাইল রাখা · দিন', channel: 'চ্যানেল', channelPageHint: 'বটের পাবলিক চ্যানেল: পোস্ট, সময় নির্ধারণ, সম্পাদনা, পিন ও মুছে ফেলা', channelConnect: 'চ্যানেল যুক্ত করুন', channelConnectHint: 'বটকে চ্যানেলে পোস্ট (এবং সম্পাদনা, মোছা, পিন) করার অনুমতিসহ অ্যাডমিন করুন, তারপর এখানে চ্যানেল লিখুন।', channelPostingBot: 'যে বট পোস্ট করে', saveAndCheck: 'সংরক্ষণ ও যাচাই', channelPrivate: 'প্রাইভেট চ্যানেল', channelSubscribers: 'সাবস্ক্রাইবার', rightPost: 'পোস্ট', rightEdit: 'সম্পাদনা', rightDelete: 'মোছা', rightPin: 'পিন', channelNotAdmin: 'বটটি এই চ্যানেলের অ্যাডমিন নয়: চ্যানেল সেটিংস → অ্যাডমিনে যোগ করুন।', channelEditPost: 'পোস্ট সম্পাদনা', channelNewPost: 'নতুন পোস্ট', channelComposeHint: 'ফরম্যাট করা লেখা, ছবি বা ভিডিও, লিংক বোতাম; এখনই বা নির্দিষ্ট সময়ে।', addPhotoOrVideo: 'ছবি বা ভিডিও যোগ করুন', channelButtons: 'পোস্টের নিচে বোতাম', addButton: 'বোতাম যোগ করুন', channelWhen: 'কখন', channelNow: 'এখনই', channelLater: 'নির্দিষ্ট সময়ে', channelConnectFirst: 'আগে চ্যানেল যুক্ত করুন', channelSchedule: 'সময় নির্ধারণ', channelPublishNow: 'এখনই পোস্ট করুন', channelPosts: 'চ্যানেলের পোস্ট', channelViewsNote: 'Telegram Bot API পোস্টের ভিউ দেয় না; দেখতে Telegram-এ পোস্টটি খুলুন।', cp_scheduled: 'নির্ধারিত', cp_sending: 'পাঠানো হচ্ছে', cp_published: 'প্রকাশিত', cp_failed: 'ব্যর্থ', pinned: 'পিন করা', pin: 'পিন', unpin: 'আনপিন', edit: 'সম্পাদনা', channelConfirmDelete: 'চ্যানেল থেকে এই পোস্ট মুছবেন?', channelConfirmCancel: 'এই নির্ধারিত পোস্ট বাতিল করবেন?', channelDelete: 'চ্যানেল থেকে মুছুন', cancel: 'বাতিল', openInTelegram: 'Telegram-এ খুলুন', channelAllBots: 'সব বট', channelPostsFrom: 'পোস্ট করে', channelBots: 'এই চ্যানেলের বট', channelBotAdmin: 'চ্যানেলের অ্যাডমিন', channelNoBots: 'এখনো কোনো বট যুক্ত নেই: বট পেজে যোগ করুন।', channelPostingAs: 'পোস্ট করে {bot}।', channelNoPoster: 'বাছাই করা কোনো বট এখানে পোস্ট করতে পারে না: একটিকে পোস্টের অনুমতিসহ অ্যাডমিন করুন।',
  },
  ur: {
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    reports: 'رپورٹس', reportsHint: 'بوٹ، سروس اور پلیٹ فارم کے لحاظ سے روزانہ، ہفتہ وار اور ماہانہ اعداد',
    period_day: 'دن', period_week: 'ہفتے', period_month: 'مہینے', allBots: 'تمام بوٹس', period: 'مدت',
    rDownloads: 'ڈاؤن لوڈز', rUploads: 'اپ لوڈز', permanent: 'مستقل', makePermanent: 'مستقل بنائیں',
    paymentSource: 'ذریعہ', referralCredits: 'ہر انعام پر اضافی کریڈٹ (اضافی ڈاؤن لوڈز)', bot: 'بوٹ',
    newUsersPeriod: 'نئے صارفین', activeUsersPeriod: 'فعال صارفین', errorRate: 'خرابی کی شرح', storageUsed: 'استعمال شدہ اسٹوریج',
    completedFailed: 'کامیاب اور ناکام', byPlatform: 'پلیٹ فارم کے لحاظ سے', byBot: 'بوٹ کے لحاظ سے', byService: 'سروس کے لحاظ سے',
    failedByPlatform: 'پلیٹ فارم کے لحاظ سے ناکامیاں', topErrors: 'سب سے عام خرابیاں', revenueByMethod: 'ادائیگی کے طریقے کے لحاظ سے آمدنی',
    reportRules: 'حساب کے اصول: مدت UTC میں دن، ISO ہفتے اور مہینے ہیں؛ خرابی کی شرح = ناکام / (کامیاب + ناکام)؛ فعال صارفین = جنہوں نے مدت میں کوئی کام شروع کیا؛ آمدنی = ادائیگی کے وقت کے مطابق ادا شدہ آرڈرز، ریفنڈ کے بغیر (Stars میں Stars، کارڈ اور کرپٹو USD میں)۔ CSV میں یہی اعداد ہوتے ہیں۔',
    translations: 'ترجمے', translationsHint: 'کوڈ بدلے بغیر کسی بھی زبان میں بوٹس کا کوئی بھی متن بدلیں اور زبانیں آن یا بند کریں۔ خالی خانہ اصل متن واپس لاتا ہے۔ {count} جیسے پلیس ہولڈر باقی رہنے چاہئیں۔',
    editedTexts: '{count} تبدیل شدہ', narrowSearch: '{count} متن ملے: باقی دیکھنے کے لیے تلاش محدود کریں۔',
    monitoring: 'نگرانی اور الرٹس', monitoringHint: 'ہر 5 منٹ میں پلیٹ فارم ڈسک، ناکام ڈاؤن لوڈز، خاموش بوٹس اور قطار چیک کرتا ہے اور الرٹ بھیجتا ہے (ہر مسئلے پر گھنٹے میں زیادہ سے زیادہ ایک بار)۔',
    problemsFound: '{count} مسائل', allGood: 'سب ٹھیک ہے', diskFree: 'ڈسک: {total} GB میں سے {free} GB خالی', lastCheck: 'چیک کیا گیا {date}',
    alertChat: 'الرٹس کے لیے Telegram چیٹ', alertChatHint: 'آپ کی Telegram ID یا کسی گروپ کی ID (-100…)۔ پہلے وہاں کوئی بوٹ شروع کریں۔',
    diskMinGb: 'خالی ڈسک اس سے کم ہو تو الرٹ (GB)', errorRateAlert: 'ناکام ڈاؤن لوڈز اس سے زیادہ ہوں تو الرٹ (%)', queueMinutes: 'کام اس سے زیادہ انتظار کرے تو الرٹ (منٹ)',
    botSilentMinutes: 'بوٹ اتنی دیر خاموش رہے تو الرٹ (منٹ)', checkNow: 'ابھی چیک کریں اور ٹیسٹ الرٹ بھیجیں',
    tier: 'درجہ', credits: 'کریڈٹ', creditsHint: '(روزانہ حد سے زیادہ اضافی ڈاؤن لوڈز)',
    botToken: 'بوٹ ٹوکن', botTokenHint: 'سرور پر فائلیں بدلے بغیر اس بوٹ کو جوڑنے یا بدلنے کے لیے @BotFather کا ٹوکن چسپاں کریں۔ یہ Telegram سے جانچا جاتا ہے، خفیہ کر کے محفوظ ہوتا ہے اور دوبارہ نہیں دکھایا جاتا؛ بوٹ ایک منٹ میں اس کے ساتھ دوبارہ شروع ہوتا ہے۔',
    saveToken: 'ٹوکن محفوظ کریں', tiers: 'درجے', tiersHint: 'ہر ادا شدہ درجے کی اپنی حدیں ہیں (0 = کوئی اضافی حد نہیں)۔ نیچے کے پلان کسی درجے کو کچھ دنوں کے لیے بیچتے ہیں۔',
    tierName: 'نام', tierDaily: 'روزانہ ڈاؤن لوڈز (0 = لامحدود)', tierMaxMb: 'سب سے بڑی فائل، MB (0 = سرور کی حد)', tierStorageMb: 'فائل اسٹوریج، MB (0 = کوئی کوٹا نہیں)',
    tierPriority: 'ترجیحی قطار', tierNoAds: 'بغیر اشتہار', tierKeyPrompt: 'نئے درجے کی مختصر ID (لاطینی حروف، جیسے gold):', addTier: 'درجہ شامل کریں',
    tierPlatforms: 'شامل پلیٹ فارمز (سب منتخب = سب)',
    botPlatforms: 'اس بوٹ کے پلیٹ فارمز', alertEmails: 'الرٹس کے لیے ای میل', alertEmailFrom: 'بھیجنے والے کا پتہ',
    alertEmailProvider: 'ای میل سروس', alertEmailKey: 'ای میل سروس کی API کلید',
    alertEmailHint: 'سرور HTTPS ای میل API سے میل بھیجتا ہے (SendGrid یا Resend؛ مفت پلان کافی ہے)۔ بھیجنے والے کا پتہ اس سروس میں تصدیق شدہ ہونا چاہیے۔ کلید خفیہ کر کے محفوظ ہوتی ہے۔',
    adClicks: '{count} کلکس', adWeight: 'وزن (دوسرے اشتہارات کے مقابلے میں کتنی بار)', adMaxViews: 'اتنے ویوز کے بعد روکیں (0 = لامحدود)',
    adBots: 'کن بوٹس میں دکھائیں', adLanguages: 'صرف ان زبانوں کے لیے (خالی = سب)', adsEvery: 'صارف کے ہر N ویں ڈاؤن لوڈ پر اشتہار دکھائیں',
    
    
    
    fileView: 'دیکھیں', fileDownload: 'ڈاؤن لوڈ', fileClose: 'بند کریں', noPreview: 'اس قسم کی فائل یہاں نہیں دکھائی جا سکتی۔ کھولنے کے لیے ڈاؤن لوڈ کریں۔', userData: 'صارف کا ڈیٹا', jobChannel: 'مصنف', jobDuration: 'دورانیہ', jobViews: 'ویوز', jobLikes: 'لائکس', jobItems: 'آئٹمز', jobFormat: 'فارمیٹ', jobCompleted: 'مکمل', jobLink: 'لنک', fileLabel: 'فائل', jobDescription: 'تفصیل', jobNoFiles: 'اس کام کی کوئی فائل محفوظ نہیں (معلومات کی درخواست، ناکامی یا فائلیں حذف ہو چکیں)۔', userName: 'نام', addChannel: 'ایک اور چینل شامل کریں', channelsHint: 'صارفین کو فہرست کے تمام چینلز جوائن کرنا ہوں گے (زیادہ سے زیادہ 10)۔ بوٹ کو ہر چینل میں ایڈمن ہونا چاہیے؛ «چیک» ہر چینل اور بوٹ کا نتیجہ دکھاتا ہے۔', media_retention_days: 'ڈاؤن لوڈ میڈیا محفوظ · دن', retention_days: 'اپ لوڈ فائلیں محفوظ · دن', channel: 'چینل', channelPageHint: 'بوٹس کا عوامی چینل: پوسٹ، شیڈول، ترمیم، پن اور حذف', channelConnect: 'چینل جوڑیں', channelConnectHint: 'بوٹ کو چینل میں پوسٹ (اور ترمیم، حذف، پن) کی اجازت کے ساتھ ایڈمن بنائیں، پھر یہاں چینل لکھیں۔', channelPostingBot: 'پوسٹ کرنے والا بوٹ', saveAndCheck: 'محفوظ کریں اور جانچیں', channelPrivate: 'نجی چینل', channelSubscribers: 'سبسکرائبرز', rightPost: 'پوسٹ', rightEdit: 'ترمیم', rightDelete: 'حذف', rightPin: 'پن', channelNotAdmin: 'بوٹ اس چینل کا ایڈمن نہیں: چینل کی ترتیبات ← ایڈمنز میں شامل کریں۔', channelEditPost: 'پوسٹ میں ترمیم', channelNewPost: 'نئی پوسٹ', channelComposeHint: 'فارمیٹ شدہ متن، تصویر یا ویڈیو، لنک بٹن؛ ابھی یا مقررہ وقت پر۔', addPhotoOrVideo: 'تصویر یا ویڈیو شامل کریں', channelButtons: 'پوسٹ کے نیچے بٹن', addButton: 'بٹن شامل کریں', channelWhen: 'کب', channelNow: 'ابھی', channelLater: 'مقررہ وقت پر', channelConnectFirst: 'پہلے چینل جوڑیں', channelSchedule: 'شیڈول کریں', channelPublishNow: 'ابھی پوسٹ کریں', channelPosts: 'چینل کی پوسٹس', channelViewsNote: 'Telegram Bot API پوسٹ کے ویوز نہیں دیتا؛ دیکھنے کے لیے پوسٹ Telegram میں کھولیں۔', cp_scheduled: 'شیڈول شدہ', cp_sending: 'بھیجی جا رہی', cp_published: 'شائع شدہ', cp_failed: 'ناکام', pinned: 'پن شدہ', pin: 'پن کریں', unpin: 'پن ہٹائیں', edit: 'ترمیم', channelConfirmDelete: 'یہ پوسٹ چینل سے حذف کریں؟', channelConfirmCancel: 'یہ شیڈول پوسٹ منسوخ کریں؟', channelDelete: 'چینل سے حذف کریں', cancel: 'منسوخ', openInTelegram: 'Telegram میں کھولیں', channelAllBots: 'تمام بوٹس', channelPostsFrom: 'پوسٹ کرتا ہے', channelBots: 'اس چینل کے بوٹس', channelBotAdmin: 'چینل کا ایڈمن', channelNoBots: 'ابھی کوئی بوٹ جڑا نہیں: بوٹس کے صفحے پر شامل کریں۔', channelPostingAs: 'پوسٹ {bot} کرتا ہے۔', channelNoPoster: 'منتخب کوئی بوٹ یہاں پوسٹ نہیں کر سکتا: کسی ایک کو پوسٹ کی اجازت کے ساتھ ایڈمن بنائیں۔',
  },
};
