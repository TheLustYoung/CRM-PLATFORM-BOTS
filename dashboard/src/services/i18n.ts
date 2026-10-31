import {createContext, useContext} from 'react';
import {en as baseEn, ar as baseAr, he as baseHe} from './i18n.base';
import zh from './locales/zh';
import hi from './locales/hi';
import es from './locales/es';
import fr from './locales/fr';
import bn from './locales/bn';
import pt from './locales/pt';
import ru from './locales/ru';
import ur from './locales/ur';
import {teamAr, teamBn, teamEn, teamEs, teamFr, teamHe, teamHi, teamPt, teamRu, teamUr, teamZh} from './i18n.team';
import {adminEn, adminTexts} from './i18n.admin';
import {moreTexts} from './i18n.more';

const extraEn = {
  guide_video_title: 'Video bot',
  guide_video_text: 'Videos from Internet Archive and Wikimedia Commons, with the licence of each item.',
  guide_video_1: 'Find a video on archive.org or commons.wikimedia.org',
  guide_video_2: 'Send its link to the bot',
  guide_video_3: 'Pick a quality: video or audio only',
  guide_media_title: 'Media bot',
  guide_media_text: 'Openly licensed photos, audio and video, plus direct links to media files.',
  guide_media_1: 'Send a Wikimedia Commons or Internet Archive link, or a direct file link',
  guide_media_2: 'Check the licence on the card',
  guide_media_3: 'Choose a format; collections arrive as one album',
  uploads:'Completed uploads', new_users_week:'New users · 7 days', activity7:'Activity · last 7 days', perBot:'Jobs by bot',
  botUsers:'Users', jobsToday:'Jobs today', errorsToday:'Errors today', welcomeText:'Custom welcome message (optional)',
  welcomeHint:'Leave empty to use the translated default text.', details:'Details', close:'Close', language:'Language',
  downloadsCount:'Downloads', uploadsCount:'Uploads', failedCount:'Failed', filesActive:'Active files', bots_list:'Bots',
  allStatuses:'All statuses', allBots:'All bots', audit:'Audit log', action:'Action', target:'Target', admin:'Administrator',
  downloadsShort:'Downloads', metadata:'Info', download:'Download', upload:'Upload', telegram:'Telegram', joined:'Joined',
  lastSeen:'Last seen', files_of_user:'Files', jobs_of_user:'History', link:'Link', active:'Active',
  'VERIFIED':'Verified', 'PARTIAL':'Partial', 'TEMPORARILY UNAVAILABLE':'Temporarily unavailable', 'UNSUPPORTED':'Unsupported', 'NOT VERIFIED':'Not verified',
  lastTest:'Last test',
  appearance:'Appearance', appearanceHint:'Changes go to Telegram immediately. The @username can only be changed in @BotFather.',
  allLanguages:'All languages (default)', botName:'Bot name', shortDescription:'Short description (profile and link previews)',
  botDescription:'Description ("What can this bot do?" before /start)', menuCommands:'Menu commands', addCommand:'Add command',
  command:'Command', commandDescription:'Command description', photo:'Profile photo', uploadPhoto:'Upload photo',
  removePhoto:'Remove photo', confirmRemovePhoto:'Remove the bot profile photo?', noPhoto:'No photo', photoHint:'JPEG or PNG, up to 10 MB, square works best.',
  remove:'Remove',
  welcomeBack:'Welcome back, {name}.', welcomeSub:"Here's what's happening with your bots today.", viewDownloads:'View downloads',
  successRate:'Success rate', successful:'Successful', failedShort:'Failed', toggleTheme:'Switch theme', openMenu:'Menu',
  jobsTodayHero:'jobs today', online:'Online', ofTotal:'of {total}',
  guide:'Guide', guideTitle:'How to use the bots', guideSub:'Three bots, one account: send a link or a file and get the result right in the chat.',
  openGuide:'Full guide', openBot:'Open in Telegram', adminGuidePdf:'Admin guide (PDF)',
  
  
  
  
  
  
  
  
  testProxies:'Test',
  
  
  apiKeyActive:'Key saved', apiKeyMissing:'No key', apiKeyInput:'Access key', 
  
  
  
  
  guide_files_title:'File sharing bot', guide_files_text:'Turns any file into a public download link.',
  guide_files_1:'Open the bot and press Start.', guide_files_2:'Send a document, photo, video or audio.', guide_files_3:'Share the link. Revoke or delete it any time in “My files”.',
  guideMenuTitle:'Bot menu buttons', guide_menu_1:'🕘 My downloads / 📁 My files: your history and links.',
  guide_menu_2:'❓ Help: step-by-step instructions inside each bot.', guide_menu_3:'🌐 Language: 11 languages, including English, Chinese, Hindi, Spanish, Arabic and French.',
  guideAdminTitle:'For administrators', guide_admin_1:'Bots: turn a bot on or off, set the daily limit, change its name, descriptions, commands and photo.',
  guide_admin_2:'Downloads and Files: every request, its status and error; download, revoke or delete files.',
  guide_admin_3:'Users: search, see a user’s history, ban abuse.', guide_admin_4:'Settings: enabled platforms, size limits and how long files are kept.',
  guideTipsTitle:'Good to know', guide_tip_1:'Files over 49 MB are sent as a download link instead of a Telegram file.',
  guide_tip_2:'Private, deleted or login-only posts cannot be downloaded.', guide_tip_3:'Download links expire after the retention period set in Settings.',
  monetization:'Monetization', monetizationHint:'Premium, invites, required channel and ads',
  guide_admin_5:'Monetization: Premium plans for Telegram Stars, invite rewards, a required channel and sponsored messages. Each one is switched on separately.',
  starsEarned30:'Stars · 30 days', starsTotal:'Stars · all time', premiumUsers:'Active Premium', invitedUsers:'Invited friends',
  purchases:'{count} purchases', rewardsGiven:'{count} rewards given', on:'On', off:'Off',
  premiumSection:'Premium for Telegram Stars', premiumHint:'Users pay in Stars right in the bot. Premium: unlimited downloads, HD/4K, large files, priority in the queue and no ads. Stars collect on each bot’s balance in @BotFather.',
  plans:'Plans', planDays:'Days', planStars:'Price, Stars', addPlan:'Add plan', payout:'≈ ${usd} payout',
  freeTier:'Free plan limits', freeMaxHeight:'Highest free quality', anyQuality:'Any quality (no limit)',
  freeMaxMb:'Largest free file, MB (0 = no limit)', freeDailyHint:'Free downloads per day are set in Settings → Limits. Premium users have no daily limit.',
  referralsSection:'Invite friends', referralsHint:'Each user gets a personal invite link in ⭐ Premium. A friend counts after their first successful download, so empty sign-ups earn nothing.',
  referralInvites:'Friends needed for a reward', referralDays:'Premium days per reward', referralExample:'Every {invites} invited friends give the user {days} days of Premium.',
  channelSection:'Required channel', channelHint:'Users must join your channel before downloading. Add every bot to the channel as an administrator, otherwise it cannot check subscriptions.',
  channelId:'Channel (@username or -100… id)', channelLink:'Invite link (required for private channels)', channelSkipPremium:'Premium users don’t have to join',
  checkChannel:'Check bots', botIsAdmin:'admin ✓', botNotAdmin:'make it an admin',
  adsSection:'Sponsored messages', adsHint:'A short message under the download status while the file is being prepared. One ad per download; Premium users never see ads.',
  adText:'Ad text', adButton:'Button text', adUrl:'Button link (https://…)', addAd:'Add ad', views:'{count} views', adEnabled:'Show this ad',
  saveChanges:'Save changes', discard:'Discard', unsaved:'Unsaved changes',
  recentPayments:'Premium history', recentPaymentsHint:'Last 20 purchases, invite rewards and gifts', source:'Source', stars:'Stars', days:'Days',
  src_stars:'Purchase', src_referral:'Invite reward', src_admin:'Gift',
  premium:'Premium', free:'Free', premiumUntil:'Until', grantPremium:'Gift Premium', grantDays:'Premium days',
  removePremium:'Remove Premium', confirmRemovePremium:'Remove Premium from this user?',
  ads:'Ads', adsPageHint:'Ad posts in your bots: send to users, delete from their chats',
  composeTitle:'New ad post', composeHint:'Formatted like in Telegram. Each person gets the post once, from the first selected bot they use.',
  fmtBold:'Bold', fmtItalic:'Italic', fmtUnderline:'Underline', fmtStrike:'Strikethrough', fmtSpoiler:'Spoiler', fmtCode:'Monospace',
  fmtPre:'Code block', fmtLink:'Link', fmtQuote:'Quote', fmtClear:'Clear formatting', apply:'Apply', removeLink:'Remove link',
  postPlaceholder:'Write your post…', chars:'{count} / {limit}', addPhoto:'Add photo', removePhotoShort:'Remove photo',
  postButton:'Button under the post (optional)', sendTo:'Send through bots', skipPremiumAds:'Skip Premium users (Premium is ad-free)',
  audienceTotal:'Will reach {count} people', audienceShort:'Audience', testTitle:'Test on yourself: your Telegram ID',
  testHint:'Find it with @userinfobot. Open the bot and press Start first.', sendTest:'Send test', done:'Done.',
  publish:'Publish to {count}', confirmPublish:'Send this post to {count} people now?', preview:'Preview', history:'Sent posts',
  st_sending:'Sending', st_sent:'Sent', st_deleting:'Deleting', st_deleted:'Deleted', delivered:'Delivered', notDelivered:'Not delivered',
  removedCount:'Removed', notRemoved:'not removed', deleteFromChats:'Delete from chats', confirmDeletePost:'Delete this post from every chat it reached?',
  tooOldToDelete:'Telegram lets bots delete their messages only within {hours} hours after sending.', useAgain:'Use again', withPhoto:'with photo',
  payments:'Payments', paymentsHint:'Payment methods, provider keys, transactions and revenue',
  revenue:'Revenue', revenueHint:'Paid orders by method, refunds excluded', today:'Today', d7:'7 days', d30:'30 days', allTime:'All time', ordersCount:'{count} payments',
  method:'Method', m_stars:'Telegram Stars',
  publicDomain:'Domain for links and the payment page', publicDomainHint:'A neutral domain users see in file links and on the payment page instead of the main one. Add it in Plesk first, then enter it here.', currentBase:'Used now: {url}',
  starsHint:'Paid right inside the bot. Withdraw Stars in @BotFather → your bot → Balance.',
  cardPayments:'Bank cards', cardHint:'The «💳 Bank card» button in the bots. It opens the payment page, which sends the user to the provider chosen below.',
  cryptoPayments:'Cryptocurrency', cryptoHint:'The «🪙 Crypto» button in the bots: TON, USDT and other coins through the provider chosen below.',
  provider:'Provider', providerPending:'Integration in the next update', providerPendingShort:'fields only',
  providerPendingHint:'You can already enter and save the keys for this provider. Its connection module comes with the next update; until then the button shows a «coming soon» page.',
  soonInBots:'The button is already shown in the bots. Until the provider is connected, users see a «coming soon» page and can pay with Stars.',
  whereKeys:'Where to get the keys for {name}', removeKeyShort:'Remove', keySaved:'Saved: {hint}. Leave empty to keep it.', willRemove:'Will be removed when you save.',
  webhookUrl:'Webhook URL (paste it in the provider’s dashboard)', webhookEvents:'Events to send: {events}', copy:'Copy', copied:'Copied ✓',
  configured:'Connected', notConfigured:'Keys missing',
  priceUsdHint:'Card and crypto prices are set per plan in Monetization → Plans (the «Price, $» column).',
  transactions:'Transactions', amount:'Amount', refund:'Refund', confirmRefund:'Refund this payment and take back the Premium days?',
  os_pending:'Pending', os_paid:'Paid', os_failed:'Failed', os_expired:'Expired', os_canceled:'Canceled', os_refunded:'Refunded', allMethods:'All methods', planUsd:'Price, $',
  starsRules:'Telegram rules for Stars: a price is a whole number from 1 to 10,000 ⭐. A plan is either a one-time purchase for any number of days or a subscription that Telegram renews every 30 days (users cancel it in Telegram settings). Discounts apply to both ⭐ and $ prices.', planEnabled:'Plan is on sale', planType:'Plan type', planOnce:'One-time', planSubscription:'Subscription · every 30 days', planDiscount:'Discount, %', planTitle:'Name (optional)', planTitlePh:'e.g. Monthly', planBadge:'Badge (optional)', invoicePhoto:'Picture on the Stars invoice (optional)', invoicePhotoHint:'A https:// link to a JPG/PNG shown on the Telegram payment window.', freeDailyJobs:'Free downloads per day',
};
export type Key = keyof typeof baseEn | keyof typeof extraEn;  // Team texts are typed separately (i18n.team.ts: every language has every key)
const extraAr: typeof extraEn = {
  guide_video_title: 'بوت الفيديو',
  guide_video_text: 'مقاطع فيديو من Internet Archive وWikimedia Commons مع ترخيص كل ملف.',
  guide_video_1: 'ابحث عن فيديو في archive.org أو commons.wikimedia.org',
  guide_video_2: 'أرسل رابطه إلى البوت',
  guide_video_3: 'اختر الجودة: فيديو أو صوت فقط',
  guide_media_title: 'بوت الوسائط',
  guide_media_text: 'صور وصوت وفيديو بتراخيص حرة، وروابط مباشرة لملفات الوسائط.',
  guide_media_1: 'أرسل رابطًا من Wikimedia Commons أو Internet Archive أو رابطًا مباشرًا لملف',
  guide_media_2: 'تحقق من الترخيص في البطاقة',
  guide_media_3: 'اختر صيغة؛ تصل المجموعات كألبوم واحد',
  uploads:'الملفات المرفوعة', new_users_week:'مستخدمون جدد · 7 أيام', activity7:'النشاط · آخر 7 أيام', perBot:'المهام حسب البوت',
  botUsers:'المستخدمون', jobsToday:'مهام اليوم', errorsToday:'أخطاء اليوم', welcomeText:'رسالة ترحيب مخصصة (اختياري)',
  welcomeHint:'اتركه فارغاً لاستخدام النص الافتراضي المترجم.', details:'التفاصيل', close:'إغلاق', language:'اللغة',
  downloadsCount:'التنزيلات', uploadsCount:'الرفع', failedCount:'الفاشلة', filesActive:'الملفات النشطة', bots_list:'البوتات',
  allStatuses:'جميع الحالات', allBots:'جميع البوتات', audit:'سجل التدقيق', action:'الإجراء', target:'الهدف', admin:'المسؤول',
  downloadsShort:'التنزيلات', metadata:'معلومات', download:'تنزيل', upload:'رفع', telegram:'تيليجرام', joined:'تاريخ الانضمام',
  lastSeen:'آخر ظهور', files_of_user:'الملفات', jobs_of_user:'السجل', link:'الرابط', active:'نشط',
  'VERIFIED':'تم التحقق', 'PARTIAL':'جزئي', 'TEMPORARILY UNAVAILABLE':'غير متاح مؤقتاً', 'UNSUPPORTED':'غير مدعوم', 'NOT VERIFIED':'لم يتم التحقق',
  lastTest:'آخر اختبار',
  appearance:'المظهر', appearanceHint:'تُطبَّق التغييرات في تيليجرام فوراً. لا يمكن تغيير @username إلا عبر @BotFather.',
  allLanguages:'جميع اللغات (افتراضي)', botName:'اسم البوت', shortDescription:'وصف قصير (الملف الشخصي ومعاينة الرابط)',
  botDescription:'الوصف («ماذا يمكن لهذا البوت أن يفعل؟» قبل /start)', menuCommands:'أوامر القائمة', addCommand:'إضافة أمر',
  command:'الأمر', commandDescription:'وصف الأمر', photo:'صورة الملف الشخصي', uploadPhoto:'رفع صورة',
  removePhoto:'حذف الصورة', confirmRemovePhoto:'حذف صورة الملف الشخصي للبوت؟', noPhoto:'لا توجد صورة', photoHint:'JPEG أو PNG حتى 10 ميغابايت، ويفضل أن تكون مربعة.',
  remove:'حذف',
  welcomeBack:'مرحباً بعودتك، {name}.', welcomeSub:'إليك ما يحدث مع بوتاتك اليوم.', viewDownloads:'عرض التنزيلات',
  successRate:'نسبة النجاح', successful:'ناجحة', failedShort:'فاشلة', toggleTheme:'تبديل المظهر', openMenu:'القائمة',
  jobsTodayHero:'مهام اليوم', online:'متصل', ofTotal:'من {total}',
  guide:'الدليل', guideTitle:'كيفية استخدام البوتات', guideSub:'ثلاثة بوتات وحساب واحد: أرسل رابطاً أو ملفاً واحصل على النتيجة في المحادثة.',
  openGuide:'الدليل الكامل', openBot:'فتح في تيليجرام', adminGuidePdf:'دليل المسؤول (PDF)',
  
  
  
  
  
  
  
  
  testProxies:'اختبار',
  
  
  apiKeyActive:'تم حفظ المفتاح', apiKeyMissing:'لا يوجد مفتاح', apiKeyInput:'مفتاح الوصول', 
  
  
  
  
  guide_files_title:'بوت مشاركة الملفات', guide_files_text:'يحوّل أي ملف إلى رابط تنزيل عام.',
  guide_files_1:'افتح البوت واضغط Start.', guide_files_2:'أرسل مستنداً أو صورة أو فيديو أو صوتاً.', guide_files_3:'شارك الرابط. يمكنك إلغاؤه أو حذفه في أي وقت من «ملفاتي».',
  guideMenuTitle:'أزرار قائمة البوت', guide_menu_1:'🕘 تنزيلاتي / 📁 ملفاتي: السجل والروابط.',
  guide_menu_2:'❓ مساعدة: تعليمات خطوة بخطوة داخل كل بوت.', guide_menu_3:'🌐 اللغة: 11 لغة، منها الإنجليزية والصينية والهندية والإسبانية والعربية والفرنسية.',
  guideAdminTitle:'للمسؤولين', guide_admin_1:'البوتات: تشغيل البوت أو إيقافه، الحد اليومي، تغيير الاسم والأوصاف والأوامر والصورة.',
  guide_admin_2:'التنزيلات والملفات: كل طلب وحالته وخطؤه؛ تنزيل الملفات أو إلغاء روابطها أو حذفها.',
  guide_admin_3:'المستخدمون: البحث، سجل المستخدم، حظر إساءة الاستخدام.', guide_admin_4:'الإعدادات: المنصات المفعّلة، حدود الحجم، ومدة الاحتفاظ بالملفات.',
  guideTipsTitle:'معلومات مفيدة', guide_tip_1:'الملفات الأكبر من 49 ميغابايت تُرسل كرابط تنزيل بدلاً من ملف تيليجرام.',
  guide_tip_2:'لا يمكن تنزيل المنشورات الخاصة أو المحذوفة أو التي تتطلب تسجيل الدخول.', guide_tip_3:'تنتهي صلاحية روابط التنزيل بعد مدة الاحتفاظ المحددة في الإعدادات.',
  monetization:'تحقيق الدخل', monetizationHint:'بريميوم والدعوات والقناة الإلزامية والإعلانات',
  guide_admin_5:'تحقيق الدخل: خطط بريميوم مقابل نجوم تيليجرام ومكافآت الدعوة وقناة إلزامية ورسائل إعلانية. يُفعَّل كل منها على حدة.',
  starsEarned30:'النجوم · 30 يومًا', starsTotal:'النجوم · الإجمالي', premiumUsers:'بريميوم نشط', invitedUsers:'الأصدقاء المدعوون',
  purchases:'{count} عمليات شراء', rewardsGiven:'{count} مكافآت', on:'مفعّل', off:'متوقف',
  premiumSection:'بريميوم مقابل نجوم تيليجرام', premiumHint:'يدفع المستخدمون بالنجوم داخل البوت مباشرة. بريميوم: تنزيلات غير محدودة وHD/4K وملفات كبيرة وأولوية في الانتظار وبدون إعلانات. تتجمع النجوم في رصيد كل بوت في @BotFather.',
  plans:'الخطط', planDays:'الأيام', planStars:'السعر بالنجوم', addPlan:'إضافة خطة', payout:'≈ ${usd} عائد',
  freeTier:'حدود الخطة المجانية', freeMaxHeight:'أعلى جودة مجانية', anyQuality:'أي جودة (بلا حد)',
  freeMaxMb:'أكبر ملف مجاني بالميغابايت (0 = بلا حد)', freeDailyHint:'عدد التنزيلات المجانية اليومية يُضبط في الإعدادات ← الحدود. مستخدمو بريميوم بلا حد يومي.',
  referralsSection:'ادعُ الأصدقاء', referralsHint:'يحصل كل مستخدم على رابط دعوة شخصي في ⭐ بريميوم. يُحتسب الصديق بعد أول تنزيل ناجح له، فلا تُكافأ التسجيلات الفارغة.',
  referralInvites:'عدد الأصدقاء للمكافأة', referralDays:'أيام بريميوم لكل مكافأة', referralExample:'كل {invites} أصدقاء مدعوين يمنحون المستخدم {days} أيام من بريميوم.',
  channelSection:'القناة الإلزامية', channelHint:'يجب على المستخدمين الانضمام إلى قناتك قبل التنزيل. أضف كل بوت إلى القناة كمشرف، وإلا فلن يتمكن من التحقق من الاشتراك.',
  channelId:'القناة (‎@username أو معرّف ‎-100…)', channelLink:'رابط الدعوة (مطلوب للقنوات الخاصة)', channelSkipPremium:'مستخدمو بريميوم لا يحتاجون إلى الانضمام',
  checkChannel:'فحص البوتات', botIsAdmin:'مشرف ✓', botNotAdmin:'اجعله مشرفًا',
  adsSection:'رسائل إعلانية', adsHint:'رسالة قصيرة تحت حالة التنزيل أثناء تجهيز الملف. إعلان واحد لكل تنزيل؛ مستخدمو بريميوم لا يرون إعلانات.',
  adText:'نص الإعلان', adButton:'نص الزر', adUrl:'رابط الزر (https://…)', addAd:'إضافة إعلان', views:'{count} مشاهدة', adEnabled:'عرض هذا الإعلان',
  saveChanges:'حفظ التغييرات', discard:'تجاهل', unsaved:'تغييرات غير محفوظة',
  recentPayments:'سجل بريميوم', recentPaymentsHint:'آخر 20 عملية شراء ومكافأة دعوة وهدية', source:'المصدر', stars:'النجوم', days:'الأيام',
  src_stars:'شراء', src_referral:'مكافأة دعوة', src_admin:'هدية',
  premium:'بريميوم', free:'مجاني', premiumUntil:'حتى', grantPremium:'إهداء بريميوم', grantDays:'أيام بريميوم',
  removePremium:'إزالة بريميوم', confirmRemovePremium:'إزالة بريميوم من هذا المستخدم؟',
  ads:'الإعلانات', adsPageHint:'منشورات إعلانية في بوتاتك: أرسلها إلى المستخدمين واحذفها من محادثاتهم',
  composeTitle:'منشور إعلاني جديد', composeHint:'تنسيق كما في تيليجرام. يتلقى كل شخص المنشور مرة واحدة، من أول بوت مختار يستخدمه.',
  fmtBold:'عريض', fmtItalic:'مائل', fmtUnderline:'تسطير', fmtStrike:'يتوسطه خط', fmtSpoiler:'مخفي', fmtCode:'خط ثابت العرض',
  fmtPre:'كتلة شيفرة', fmtLink:'رابط', fmtQuote:'اقتباس', fmtClear:'مسح التنسيق', apply:'تطبيق', removeLink:'إزالة الرابط',
  postPlaceholder:'اكتب منشورك…', chars:'{count} / {limit}', addPhoto:'إضافة صورة', removePhotoShort:'إزالة الصورة',
  postButton:'زر أسفل المنشور (اختياري)', sendTo:'الإرسال عبر البوتات', skipPremiumAds:'استثناء مستخدمي بريميوم (بريميوم بلا إعلانات)',
  audienceTotal:'سيصل إلى {count} شخص', audienceShort:'الجمهور', testTitle:'جرّب على نفسك: معرّف تيليجرام الخاص بك',
  testHint:'اعرفه عبر ‎@userinfobot. افتح البوت واضغط ابدأ أولًا.', sendTest:'إرسال تجريبي', done:'تم.',
  publish:'نشر إلى {count}', confirmPublish:'إرسال هذا المنشور إلى {count} شخص الآن؟', preview:'معاينة', history:'المنشورات المرسلة',
  st_sending:'جارٍ الإرسال', st_sent:'أُرسل', st_deleting:'جارٍ الحذف', st_deleted:'حُذف', delivered:'تم التسليم', notDelivered:'لم يُسلَّم',
  removedCount:'محذوف', notRemoved:'لم يُحذف', deleteFromChats:'حذف من المحادثات', confirmDeletePost:'حذف هذا المنشور من كل المحادثات التي وصل إليها؟',
  tooOldToDelete:'يسمح تيليجرام للبوتات بحذف رسائلها خلال {hours} ساعة فقط من إرسالها.', useAgain:'استخدام مجددًا', withPhoto:'مع صورة',
  payments:'المدفوعات', paymentsHint:'طرق الدفع ومفاتيح المزوّدين والمعاملات والإيرادات',
  revenue:'الإيرادات', revenueHint:'الطلبات المدفوعة حسب الطريقة، دون المبالغ المستردة', today:'اليوم', d7:'7 أيام', d30:'30 يومًا', allTime:'الإجمالي', ordersCount:'{count} دفعة',
  method:'الطريقة', m_stars:'نجوم تيليجرام',
  publicDomain:'نطاق الروابط وصفحة الدفع', publicDomainHint:'نطاق محايد يراه المستخدمون في روابط الملفات وصفحة الدفع بدل النطاق الرئيسي. أضفه في Plesk أولًا ثم أدخله هنا.', currentBase:'المستخدم الآن: {url}',
  starsHint:'الدفع داخل البوت مباشرة. اسحب النجوم من ‎@BotFather ← بوتك ← Balance.',
  cardPayments:'البطاقات البنكية', cardHint:'زر «💳 بطاقة بنكية» في البوتات. يفتح صفحة الدفع التي تحوّل المستخدم إلى المزوّد المختار أدناه.',
  cryptoPayments:'العملات المشفرة', cryptoHint:'زر «🪙 عملات مشفرة» في البوتات: TON وUSDT وغيرها عبر المزوّد المختار أدناه.',
  provider:'المزوّد', providerPending:'الربط في التحديث القادم', providerPendingShort:'الحقول فقط',
  providerPendingHint:'يمكنك الآن إدخال مفاتيح هذا المزوّد وحفظها. وحدة الربط تأتي مع التحديث القادم؛ وحتى ذلك يعرض الزر صفحة «قريبًا».',
  soonInBots:'الزر ظاهر في البوتات بالفعل. حتى يتم ربط المزوّد، يرى المستخدمون صفحة «قريبًا» ويمكنهم الدفع بالنجوم.',
  whereKeys:'من أين تحصل على مفاتيح {name}', removeKeyShort:'إزالة', keySaved:'محفوظ: {hint}. اتركه فارغًا للإبقاء عليه.', willRemove:'سيُحذف عند الحفظ.',
  webhookUrl:'رابط Webhook (الصقه في لوحة المزوّد)', webhookEvents:'الأحداث المطلوبة: {events}', copy:'نسخ', copied:'تم النسخ ✓',
  configured:'متصل', notConfigured:'المفاتيح ناقصة',
  priceUsdHint:'أسعار البطاقات والعملات المشفرة تُحدد لكل خطة في تحقيق الدخل ← الخطط (عمود «السعر، $»).',
  transactions:'المعاملات', amount:'المبلغ', refund:'استرداد', confirmRefund:'استرداد هذا الدفع واسترجاع أيام بريميوم؟',
  os_pending:'قيد الانتظار', os_paid:'مدفوع', os_failed:'فشل', os_expired:'منتهي', os_canceled:'ملغى', os_refunded:'مسترد', allMethods:'كل الطرق', planUsd:'السعر، $',
  starsRules:'قواعد تيليجرام للنجوم: السعر عدد صحيح من 1 إلى 10,000 ⭐. الخطة إما شراء لمرة واحدة لأي عدد من الأيام أو اشتراك يجدده تيليجرام كل 30 يومًا (يلغيه المستخدم من إعدادات تيليجرام). الخصم يطبق على سعر النجوم والدولار.', planEnabled:'الخطة معروضة للبيع', planType:'نوع الخطة', planOnce:'لمرة واحدة', planSubscription:'اشتراك · كل 30 يومًا', planDiscount:'الخصم، %', planTitle:'الاسم (اختياري)', planTitlePh:'مثلًا: شهري', planBadge:'شارة (اختياري)', invoicePhoto:'صورة على فاتورة النجوم (اختياري)', invoicePhotoHint:'رابط https:// لصورة JPG/PNG تظهر في نافذة الدفع في تيليجرام.', freeDailyJobs:'التنزيلات المجانية يوميًا',
};

const extraHe: typeof extraEn = {
  guide_video_title: 'בוט וידאו',
  guide_video_text: 'סרטונים מ-Internet Archive ומ-Wikimedia Commons, עם הרישיון של כל קובץ.',
  guide_video_1: 'מצאו סרטון ב-archive.org או ב-commons.wikimedia.org',
  guide_video_2: 'שלחו את הקישור לבוט',
  guide_video_3: 'בחרו איכות: וידאו או שמע בלבד',
  guide_media_title: 'בוט מדיה',
  guide_media_text: 'תמונות, שמע ווידאו ברישיון חופשי, וקישורים ישירים לקובצי מדיה.',
  guide_media_1: 'שלחו קישור ל-Wikimedia Commons, ל-Internet Archive או קישור ישיר לקובץ',
  guide_media_2: 'בדקו את הרישיון בכרטיס',
  guide_media_3: 'בחרו פורמט; אוספים מגיעים כאלבום אחד',
  uploads:'העלאות שהושלמו', new_users_week:'משתמשים חדשים · 7 ימים', activity7:'פעילות · 7 הימים האחרונים', perBot:'משימות לפי בוט',
  botUsers:'משתמשים', jobsToday:'משימות היום', errorsToday:'שגיאות היום', welcomeText:'הודעת פתיחה מותאמת (אופציונלי)',
  welcomeHint:'השאירו ריק כדי להשתמש בטקסט ברירת המחדל המתורגם.', details:'פרטים', close:'סגירה', language:'שפה',
  downloadsCount:'הורדות', uploadsCount:'העלאות', failedCount:'נכשלו', filesActive:'קבצים פעילים', bots_list:'בוטים',
  allStatuses:'כל הסטטוסים', allBots:'כל הבוטים', audit:'יומן פעולות', action:'פעולה', target:'יעד', admin:'מנהל',
  downloadsShort:'הורדות', metadata:'מידע', download:'הורדה', upload:'העלאה', telegram:'טלגרם', joined:'הצטרף',
  lastSeen:'נראה לאחרונה', files_of_user:'קבצים', jobs_of_user:'היסטוריה', link:'קישור', active:'פעיל',
  'VERIFIED':'מאומת', 'PARTIAL':'חלקי', 'TEMPORARILY UNAVAILABLE':'לא זמין זמנית', 'UNSUPPORTED':'לא נתמך', 'NOT VERIFIED':'לא נבדק',
  lastTest:'בדיקה אחרונה',
  appearance:'מראה', appearanceHint:'השינויים נשלחים לטלגרם מיד. את ה-@username אפשר לשנות רק ב-@BotFather.',
  allLanguages:'כל השפות (ברירת מחדל)', botName:'שם הבוט', shortDescription:'תיאור קצר (פרופיל ותצוגה מקדימה של קישור)',
  botDescription:'תיאור ("מה הבוט הזה יודע לעשות?" לפני /start)', menuCommands:'פקודות תפריט', addCommand:'הוספת פקודה',
  command:'פקודה', commandDescription:'תיאור הפקודה', photo:'תמונת פרופיל', uploadPhoto:'העלאת תמונה',
  removePhoto:'הסרת תמונה', confirmRemovePhoto:'להסיר את תמונת הפרופיל של הבוט?', noPhoto:'אין תמונה', photoHint:'JPEG או PNG עד 10 MB, עדיף ריבועית.',
  remove:'הסרה',
  welcomeBack:'ברוכים השבים, {name}.', welcomeSub:'זה מה שקורה היום עם הבוטים שלכם.', viewDownloads:'להורדות',
  successRate:'שיעור הצלחה', successful:'הצליחו', failedShort:'נכשלו', toggleTheme:'החלפת ערכת נושא', openMenu:'תפריט',
  jobsTodayHero:'משימות היום', online:'מחובר', ofTotal:'מתוך {total}',
  guide:'מדריך', guideTitle:'איך משתמשים בבוטים', guideSub:'שלושה בוטים, חשבון אחד: שלחו קישור או קובץ וקבלו את התוצאה ישירות בצ׳אט.',
  openGuide:'מדריך מלא', openBot:'פתיחה בטלגרם', adminGuidePdf:'מדריך למנהל (PDF)',
  
  
  
  
  
  
  
  
  testProxies:'בדיקה',
  
  
  apiKeyActive:'המפתח נשמר', apiKeyMissing:'אין מפתח', apiKeyInput:'מפתח גישה', 
  
  
  
  
  guide_files_title:'בוט שיתוף קבצים', guide_files_text:'הופך כל קובץ לקישור הורדה ציבורי.',
  guide_files_1:'פתחו את הבוט ולחצו Start.', guide_files_2:'שלחו מסמך, תמונה, סרטון או אודיו.', guide_files_3:'שתפו את הקישור. אפשר לבטל או למחוק אותו בכל עת ב"הקבצים שלי".',
  guideMenuTitle:'כפתורי התפריט של הבוט', guide_menu_1:'🕘 ההורדות שלי / 📁 הקבצים שלי: ההיסטוריה והקישורים שלכם.',
  guide_menu_2:'❓ עזרה: הוראות שלב אחר שלב בתוך כל בוט.', guide_menu_3:'🌐 שפה: 11 שפות, ביניהן אנגלית, סינית, הינדי, ספרדית, ערבית ועברית.',
  guideAdminTitle:'למנהלים', guide_admin_1:'בוטים: הפעלה או השבתה של בוט, מגבלה יומית, שינוי שם, תיאורים, פקודות ותמונה.',
  guide_admin_2:'הורדות וקבצים: כל בקשה, הסטטוס והשגיאה שלה; הורדה, ביטול קישור או מחיקה של קבצים.',
  guide_admin_3:'משתמשים: חיפוש, היסטוריית משתמש, חסימת שימוש לרעה.', guide_admin_4:'הגדרות: פלטפורמות פעילות, מגבלות גודל וזמן שמירת הקבצים.',
  guideTipsTitle:'כדאי לדעת', guide_tip_1:'קבצים מעל 49 MB נשלחים כקישור הורדה במקום כקובץ בטלגרם.',
  guide_tip_2:'לא ניתן להוריד פוסטים פרטיים, מחוקים או כאלה שדורשים התחברות.', guide_tip_3:'קישורי ההורדה פגים בתום תקופת השמירה שנקבעה בהגדרות.',
  monetization:'מונטיזציה', monetizationHint:'פרימיום, הזמנות, ערוץ חובה ופרסומות',
  guide_admin_5:'מונטיזציה: מסלולי פרימיום בכוכבי טלגרם, תגמולי הזמנה, ערוץ חובה והודעות ממומנות. כל אחד מופעל בנפרד.',
  starsEarned30:'כוכבים · 30 יום', starsTotal:'כוכבים · סה״כ', premiumUsers:'פרימיום פעיל', invitedUsers:'חברים שהוזמנו',
  purchases:'{count} רכישות', rewardsGiven:'{count} תגמולים', on:'פעיל', off:'כבוי',
  premiumSection:'פרימיום בכוכבי טלגרם', premiumHint:'המשתמשים משלמים בכוכבים ישירות בבוט. פרימיום: הורדות ללא הגבלה, HD/4K, קבצים גדולים, עדיפות בתור ובלי פרסומות. הכוכבים מצטברים ביתרת כל בוט ב-@BotFather.',
  plans:'מסלולים', planDays:'ימים', planStars:'מחיר בכוכבים', addPlan:'הוספת מסלול', payout:'≈ ${usd} תמורה',
  freeTier:'מגבלות המסלול החינמי', freeMaxHeight:'האיכות הגבוהה ביותר בחינם', anyQuality:'כל איכות (ללא מגבלה)',
  freeMaxMb:'הקובץ הגדול ביותר בחינם, MB ‏(0 = ללא מגבלה)', freeDailyHint:'מספר ההורדות החינמיות ביום נקבע בהגדרות ← מגבלות. למשתמשי פרימיום אין מגבלה יומית.',
  referralsSection:'הזמנת חברים', referralsHint:'כל משתמש מקבל קישור הזמנה אישי ב-⭐ פרימיום. חבר נספר אחרי ההורדה המוצלחת הראשונה שלו, כך שהרשמות ריקות לא מתוגמלות.',
  referralInvites:'חברים לתגמול', referralDays:'ימי פרימיום לכל תגמול', referralExample:'כל {invites} חברים שהוזמנו נותנים למשתמש {days} ימי פרימיום.',
  channelSection:'ערוץ חובה', channelHint:'המשתמשים חייבים להצטרף לערוץ שלכם לפני ההורדה. הוסיפו כל בוט לערוץ כמנהל, אחרת הוא לא יוכל לבדוק מנויים.',
  channelId:'ערוץ (‎@username או מזהה ‎-100…)', channelLink:'קישור הזמנה (חובה לערוץ פרטי)', channelSkipPremium:'משתמשי פרימיום לא חייבים להצטרף',
  checkChannel:'בדיקת הבוטים', botIsAdmin:'מנהל ✓', botNotAdmin:'הגדירו כמנהל',
  adsSection:'הודעות ממומנות', adsHint:'הודעה קצרה מתחת לסטטוס ההורדה בזמן הכנת הקובץ. פרסומת אחת לכל הורדה; משתמשי פרימיום לא רואים פרסומות.',
  adText:'טקסט הפרסומת', adButton:'טקסט הכפתור', adUrl:'קישור הכפתור (https://…)', addAd:'הוספת פרסומת', views:'{count} צפיות', adEnabled:'להציג את הפרסומת',
  saveChanges:'שמירת שינויים', discard:'ביטול', unsaved:'יש שינויים שלא נשמרו',
  recentPayments:'היסטוריית פרימיום', recentPaymentsHint:'20 הרכישות, תגמולי ההזמנה והמתנות האחרונים', source:'מקור', stars:'כוכבים', days:'ימים',
  src_stars:'רכישה', src_referral:'תגמול הזמנה', src_admin:'מתנה',
  premium:'פרימיום', free:'חינמי', premiumUntil:'עד', grantPremium:'פרימיום במתנה', grantDays:'ימי פרימיום',
  removePremium:'הסרת פרימיום', confirmRemovePremium:'להסיר את הפרימיום מהמשתמש?',
  ads:'פרסומות', adsPageHint:'פוסטים פרסומיים בבוטים: שליחה למשתמשים ומחיקה מהצ׳אטים שלהם',
  composeTitle:'פוסט פרסומי חדש', composeHint:'עיצוב כמו בטלגרם. כל אדם מקבל את הפוסט פעם אחת, מהבוט הנבחר הראשון שבו הוא משתמש.',
  fmtBold:'מודגש', fmtItalic:'נטוי', fmtUnderline:'קו תחתון', fmtStrike:'קו חוצה', fmtSpoiler:'ספוילר', fmtCode:'רוחב קבוע',
  fmtPre:'בלוק קוד', fmtLink:'קישור', fmtQuote:'ציטוט', fmtClear:'ניקוי עיצוב', apply:'החלה', removeLink:'הסרת קישור',
  postPlaceholder:'כתבו את הפוסט…', chars:'{count} / {limit}', addPhoto:'הוספת תמונה', removePhotoShort:'הסרת תמונה',
  postButton:'כפתור מתחת לפוסט (לא חובה)', sendTo:'שליחה דרך הבוטים', skipPremiumAds:'לדלג על משתמשי פרימיום (פרימיום בלי פרסומות)',
  audienceTotal:'יגיע ל-{count} אנשים', audienceShort:'קהל', testTitle:'בדיקה על עצמכם: מזהה הטלגרם שלכם',
  testHint:'אפשר לברר דרך ‎@userinfobot. פתחו את הבוט ולחצו התחל קודם.', sendTest:'שליחת בדיקה', done:'בוצע.',
  publish:'פרסום ל-{count}', confirmPublish:'לשלוח את הפוסט ל-{count} אנשים עכשיו?', preview:'תצוגה מקדימה', history:'פוסטים שנשלחו',
  st_sending:'בשליחה', st_sent:'נשלח', st_deleting:'במחיקה', st_deleted:'נמחק', delivered:'נמסרו', notDelivered:'לא נמסרו',
  removedCount:'נמחקו', notRemoved:'לא נמחקו', deleteFromChats:'מחיקה מהצ׳אטים', confirmDeletePost:'למחוק את הפוסט מכל הצ׳אטים שאליהם הגיע?',
  tooOldToDelete:'טלגרם מאפשר לבוטים למחוק הודעות רק בתוך {hours} שעות מהשליחה.', useAgain:'שימוש חוזר', withPhoto:'עם תמונה',
  payments:'תשלומים', paymentsHint:'אמצעי תשלום, מפתחות ספקים, עסקאות והכנסות',
  revenue:'הכנסות', revenueHint:'הזמנות ששולמו לפי אמצעי, ללא החזרים', today:'היום', d7:'7 ימים', d30:'30 יום', allTime:'סה״כ', ordersCount:'{count} תשלומים',
  method:'אמצעי', m_stars:'כוכבי טלגרם',
  publicDomain:'דומיין לקישורים ולדף התשלום', publicDomainHint:'דומיין ניטרלי שהמשתמשים רואים בקישורי הקבצים ובדף התשלום במקום הדומיין הראשי. הוסיפו אותו קודם ב-Plesk ואז הזינו כאן.', currentBase:'בשימוש כעת: {url}',
  starsHint:'תשלום ישירות בתוך הבוט. משיכת הכוכבים ב-‎@BotFather ← הבוט ← Balance.',
  cardPayments:'כרטיסי אשראי', cardHint:'הכפתור «💳 כרטיס אשראי» בבוטים. הוא פותח את דף התשלום, שמעביר את המשתמש לספק שנבחר למטה.',
  cryptoPayments:'מטבעות קריפטו', cryptoHint:'הכפתור «🪙 קריפטו» בבוטים: TON‏, USDT ומטבעות נוספים דרך הספק שנבחר למטה.',
  provider:'ספק', providerPending:'החיבור בעדכון הבא', providerPendingShort:'שדות בלבד',
  providerPendingHint:'כבר אפשר להזין ולשמור את המפתחות של הספק הזה. מודול החיבור מגיע בעדכון הבא; עד אז הכפתור מציג דף «בקרוב».',
  soonInBots:'הכפתור כבר מוצג בבוטים. עד שהספק יחובר, המשתמשים רואים דף «בקרוב» ויכולים לשלם בכוכבים.',
  whereKeys:'איפה משיגים את המפתחות של {name}', removeKeyShort:'הסרה', keySaved:'נשמר: {hint}. השאירו ריק כדי לשמור.', willRemove:'יוסר בשמירה.',
  webhookUrl:'כתובת Webhook (הדביקו אותה בלוח של הספק)', webhookEvents:'אירועים לשליחה: {events}', copy:'העתקה', copied:'הועתק ✓',
  configured:'מחובר', notConfigured:'חסרים מפתחות',
  priceUsdHint:'מחירי כרטיס וקריפטו נקבעים לכל מסלול במונטיזציה ← מסלולים (עמודת «מחיר, $»).',
  transactions:'עסקאות', amount:'סכום', refund:'החזר', confirmRefund:'להחזיר את התשלום ולבטל את ימי הפרימיום?',
  os_pending:'ממתין', os_paid:'שולם', os_failed:'נכשל', os_expired:'פג תוקף', os_canceled:'בוטל', os_refunded:'הוחזר', allMethods:'כל האמצעים', planUsd:'מחיר, $',
  starsRules:'כללי טלגרם לכוכבים: המחיר הוא מספר שלם מ-1 עד 10,000 ⭐. מסלול הוא רכישה חד-פעמית לכל מספר ימים או מנוי שטלגרם מחדש כל 30 יום (המשתמש מבטל בהגדרות טלגרם). ההנחה חלה על מחיר הכוכבים ועל מחיר ה-$.', planEnabled:'המסלול במכירה', planType:'סוג מסלול', planOnce:'חד-פעמי', planSubscription:'מנוי · כל 30 יום', planDiscount:'הנחה, %', planTitle:'שם (לא חובה)', planTitlePh:'למשל: חודשי', planBadge:'תגית (לא חובה)', invoicePhoto:'תמונה בחשבונית הכוכבים (לא חובה)', invoicePhotoHint:'קישור https:// לתמונת JPG/PNG שמוצגת בחלון התשלום של טלגרם.', freeDailyJobs:'הורדות חינם ביום',
};

/** Same order as the bots: English, then the most spoken languages (top 10 + every UN language), then Hebrew. */
export const LANGS = ['en', 'zh', 'hi', 'es', 'ar', 'fr', 'bn', 'pt', 'ru', 'ur', 'he'] as const;
export type Lang = typeof LANGS[number];
export const dictionaries: Record<Lang, Record<string,string>> = {
  en: {...baseEn, ...extraEn, ...teamEn, ...adminEn}, ar: {...baseAr, ...extraAr, ...teamAr, ...moreTexts.ar},
  he: {...baseHe, ...extraHe, ...teamHe, ...moreTexts.he},
  zh: {...zh, ...teamZh, ...moreTexts.zh}, hi: {...hi, ...teamHi, ...moreTexts.hi}, es: {...es, ...teamEs, ...moreTexts.es},
  fr: {...fr, ...teamFr, ...moreTexts.fr}, bn: {...bn, ...teamBn, ...moreTexts.bn},
  pt: {...pt, ...teamPt, ...moreTexts.pt}, ru: {...ru, ...teamRu, ...adminTexts.ru} as Record<string, string>, ur: {...ur, ...teamUr, ...moreTexts.ur},
};
export const languageNames: Record<Lang,string> = {
  en:'English', zh:'中文', hi:'हिन्दी', es:'Español', ar:'العربية', fr:'Français', bn:'বাংলা', pt:'Português', ru:'Русский', ur:'اردو', he:'עברית',
};
const RTL: Lang[] = ['ar', 'ur', 'he'];
export const rtl = (lang: Lang) => RTL.includes(lang);
export const isLang = (value: string): value is Lang => (LANGS as readonly string[]).includes(value);
/** Native name of a language code; labels from the server carry emoji flags, which are dropped (the dashboard draws its own). */
export const languageName = (code: string, serverLabel = '') =>
  isLang(code) ? languageNames[code] : serverLabel.replace(/[\u{1F1E6}-\u{1F1FF}]/gu, '').trim() || code;

export type T = (key: Key|string) => string;
export const makeT = (lang: Lang): T => key => dictionaries[lang][key] ?? dictionaries.en[key] ?? key;

export const I18n = createContext<{lang: Lang; t: T}>({lang:'en', t: makeT('en')});
export const useI18n = () => useContext(I18n);
