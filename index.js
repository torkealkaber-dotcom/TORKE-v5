const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

// إعدادات البوت والمتصفح
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
        ]
    }
});

// عرض كود QR كصورة عشان تمسحه بسهولة من الموبايل
client.on('qr', (qr) => {
    qrcode.generate(qr, { small: true });
    
    const qrImageUrl = `https://api.qrserver.com/v1/create-qr-code/?size=500x500&data=${encodeURIComponent(qr)}`;
    
    console.log('\n==================================================');
    console.log('🔗 اضغط على الرابط ده عشان تفتح صورة كود QR وتعمل مسح:');
    console.log(qrImageUrl);
    console.log('==================================================\n');
});

client.on('ready', () => {
    console.log('✅ البوت شغال وجاهز!');
});

// استخدام message_create عشان يمسك الرسايل اللي إنت بتبعتاها من نفسك كمان
client.on('message_create', async (msg) => {
    const body = msg.body.trim();

    // التأكد إن فيه نص، وإنه مش ستوري
    if (!body || msg.from === 'status@broadcast') return;

    // تجاهل ردود البوت نفسه عشان ميعملش لوب (البوت مش بيبعت رسايل بتبدأ بنقطة)
    if (body.startsWith('.')) {
        
        // 1. أمر عرض قائمة الأوامر
        if (body === '.الاوامر') {
            const commandsList = `📋 *قائمة الأوامر:*\n\n.الاوامر - عرض القائمة\n.السلام عليكم - رد التحية\n.عرض - رد على صورة واكتبها لعرضها`;
            msg.reply(commandsList);
        }

        // 2. ردود على كلمات معينة
        else if (body === '.السلام عليكم') {
            msg.reply('وعليكم السلام ورحمة الله وبركاته 🌹');
        }

        // 3. ميزة عرض الصورة
        else if (body === '.عرض') {
            if (msg.hasQuotedMsg) {
                const quotedMsg = await msg.getQuotedMessage();
                
                if (quotedMsg.hasMedia) {
                    try {
                        const media = await quotedMsg.downloadMedia();
                        
                        if (media) {
                            await msg.reply('شوف شوف يعم ادي صورتك 👇');
                            await client.sendMessage(msg.from, media);
                        } else {
                            msg.reply('❌ معلش، مش قادر أحمّل الصورة دي. (لو دي صورة مؤقتة، واتساب بيمنع أي بوت من تحميلها).');
                        }
                    } catch (error) {
                        console.log('خطأ في تحميل الصورة:', error);
                        msg.reply('❌ حصل خطأ وأنا بحاول أجيب الصورة.');
                    }
                } else {
                    msg.reply('⚠️ الرسالة اللي عملتلها رد مش فيها صورة. جرب ترد على صورة عادية.');
                }
            } else {
                msg.reply('⚠️ لازم تعمل رد (Quote) على الصورة اللي عايزها وتكتب .عرض');
            }
        }
    }
});

// تشغيل البوت
client.initialize();
