const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

// تشغيل البوت
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { args: ['--no-sandbox'] }
});

// إظهار كود QR عشان تمسحه بواتساب
client.on('qr', (qr) => {
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('✅ البوت شغال وجاهز!');
});

// الاستماع للرسائل
client.on('message', async (msg) => {
    // التأكد إن الرسالة بتبدأ بنقطة
    if (msg.body.startsWith('.')) {
        const command = msg.body.slice(1).trim();
        
        // لو الأمر هو "عرض"
        if (command === 'عرض') {
            // التأكد إن الرسالة دي رد (Quote) على رسالة تانية
            if (msg.hasQuotedMsg) {
                const quotedMsg = await msg.getQuotedMessage();
                
                // التأكد إن الرسالة اللي اتعملها رد فيها صورة أو فيديو
                if (quotedMsg.hasMedia) {
                    // تحميل الصورة وإعادة إرسالها
                    const media = await quotedMsg.downloadMedia();
                    client.sendMessage(msg.from, media);
                } else {
                    msg.reply('❌ الرسالة اللي عملتلها رد مش فيها صورة.');
                }
            } else {
                msg.reply('⚠️ لازم تعمل رد (Quote) على الصورة اللي عايز تعرضها وتكتب .عرض');
            }
        }
    }
});

// تشغيل البوت
client.initialize();
