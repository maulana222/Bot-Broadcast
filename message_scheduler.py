from telethon import TelegramClient, events
import asyncio
import logging
import json
import time
import os
import random
from datetime import datetime

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('telegram_scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Konfigurasi API
API_ID = '28785825'
API_HASH = 'e5026ae707857c60dc16b5856a5a69d1'
SESSION_NAME = 'message_scheduler'

# Konfigurasi pengguna dan grup
ALLOWED_USER_ID = 7339106883
ALLOWED_USERNAME = "digiprosb_cs"  
TARGET_GROUPS = [
    -1001074420898,
    -1001092684469,
    -1001103018847,
    -1001165415900,
    -1001169191009,
    -1001171926447,
    -1001173604751,
    -1001345824902,
    -1001350748176,
    -1001370164075,
    -1001435629989,
    -1001619295591,
    -1001823750940,
    -1001826408075,
    -1001879229631,
    -1002008055762,
    -1002024956205,
    -1002037581701,
    -1002040195353,
    -1002044976617,
    -1002061755851,
    -1002079698240,
    -1002143458709,
    -1002145643932,
    -1002177242649,
    -1002219838044,
    -1002312783580,
    -1002384073971,
    -1001185847591,
    -1001180605382,
]

# File untuk menyimpan pesan
MESSAGES_FILE = 'scheduled_messages.json'
# File untuk menyimpan cooldown grup
GROUP_COOLDOWNS_FILE = 'group_cooldowns.json'

class MessageScheduler:
    def __init__(self):
        self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        self.messages = []
        self.is_active = False
        self.is_forwarding = False
        self.allowed_user = None
        self.handlers_setup = False
        self.group_cooldowns = {}  # Dictionary untuk melacak cooldown setiap grup
        self.load_messages()
        self.load_cooldowns()

    def load_messages(self):
        if os.path.exists(MESSAGES_FILE):
            try:
                with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                    self.messages = json.load(f)
                    logger.info(f"Loaded {len(self.messages)} messages from storage")
            except Exception as e:
                logger.error(f"Error loading messages: {e}")
                self.messages = []
        else:
            self.messages = []

    def load_cooldowns(self):
        if os.path.exists(GROUP_COOLDOWNS_FILE):
            try:
                with open(GROUP_COOLDOWNS_FILE, 'r', encoding='utf-8') as f:
                    self.group_cooldowns = json.load(f)
                    logger.info(f"Loaded cooldowns for {len(self.group_cooldowns)} groups")
                    
                    # Hapus cooldown yang sudah berakhir
                    current_time = time.time()
                    expired_cooldowns = []
                    for group_id, cooldown_time in self.group_cooldowns.items():
                        if current_time > cooldown_time:
                            expired_cooldowns.append(group_id)
                    
                    for group_id in expired_cooldowns:
                        del self.group_cooldowns[group_id]
                    
                    if expired_cooldowns:
                        self.save_cooldowns()
                        logger.info(f"Removed {len(expired_cooldowns)} expired cooldowns")
            except Exception as e:
                logger.error(f"Error loading cooldowns: {e}")
                self.group_cooldowns = {}
        else:
            self.group_cooldowns = {}

    def save_messages(self):
        try:
            with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f)
            logger.info(f"Saved {len(self.messages)} messages to storage")
        except Exception as e:
            logger.error(f"Error saving messages: {e}")

    def save_cooldowns(self):
        try:
            with open(GROUP_COOLDOWNS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.group_cooldowns, f)
            logger.info(f"Saved cooldowns for {len(self.group_cooldowns)} groups")
        except Exception as e:
            logger.error(f"Error saving cooldowns: {e}")

    def add_message(self, message_data):
        self.messages.append(message_data)
        self.save_messages()

    def remove_message(self, message_id):
        self.messages = [msg for msg in self.messages if msg['id'] != message_id]
        self.save_messages()

    def set_group_cooldown(self, group_id, seconds):
        # Menyimpan waktu berakhirnya cooldown
        cooldown_end_time = time.time() + seconds
        # Tambahkan jitter acak antara 10-60 detik untuk mencegah cooldown berakhir bersamaan
        cooldown_end_time += random.randint(10, 60)
        
        self.group_cooldowns[str(group_id)] = cooldown_end_time
        self.save_cooldowns()
        logger.info(f"Set cooldown for group {group_id} for {seconds} seconds (until {datetime.fromtimestamp(cooldown_end_time)})")

    def is_group_in_cooldown(self, group_id):
        group_id_str = str(group_id)
        if group_id_str in self.group_cooldowns:
            cooldown_end_time = self.group_cooldowns[group_id_str]
            current_time = time.time()
            
            if current_time < cooldown_end_time:
                remaining = int(cooldown_end_time - current_time)
                logger.info(f"Group {group_id} is in cooldown for {remaining} more seconds")
                return True, remaining
            else:
                # Cooldown sudah berakhir, hapus dari dictionary
                del self.group_cooldowns[group_id_str]
                self.save_cooldowns()
        
        return False, 0

    async def setup_handlers(self):
        """Setup event handlers only once"""
        if self.handlers_setup:
            logger.info("Handlers already set up, skipping...")
            return
        
        @self.client.on(events.NewMessage(pattern='/start_schedule', from_users=ALLOWED_USER_ID))
        async def start_schedule(event):
            if not self.is_active:
                self.is_active = True
                logger.info("✅ Penjadwalan diaktifkan")
                await event.respond("✅ Penjadwalan pesan aktif! Pesan akan diforward setiap 5 detik (mode testing).")
            else:
                await event.respond("ℹ️ Penjadwalan sudah aktif.")

        @self.client.on(events.NewMessage(pattern='/stop_schedule', from_users=ALLOWED_USER_ID))
        async def stop_schedule(event):
            if self.is_active:
                self.is_active = False
                logger.info("❌ Penjadwalan dinonaktifkan")
                await event.respond("❌ Penjadwalan pesan dinonaktifkan.")
            else:
                await event.respond("ℹ️ Penjadwalan sudah nonaktif.")

        @self.client.on(events.NewMessage(pattern='/status', from_users=ALLOWED_USER_ID))
        async def check_status(event):
            message_count = len(self.messages)
            status_text = f"📊 Status Penjadwalan:\n\n" \
                        f"- Penjadwalan: {'✅ Aktif' if self.is_active else '❌ Nonaktif'}\n" \
                        f"- Jumlah pesan dalam antrian: {message_count}\n\n" \
                        f"📛 Cooldown Grup:"
            
            current_time = time.time()
            cooldown_info = []
            
            for group_id, end_time in self.group_cooldowns.items():
                if current_time < end_time:
                    remaining = int(end_time - current_time)
                    cooldown_info.append(f"- Grup {group_id}: {remaining} detik")
            
            if cooldown_info:
                status_text += "\n" + "\n".join(cooldown_info)
            else:
                status_text += "\n- Tidak ada grup dalam cooldown"
            
            if message_count > 0:
                status_text += "\n\n📋 5 Pesan teratas dalam antrian:"
                for i, msg in enumerate(self.messages[:5], 1):
                    preview = msg['text'][:50] + '...' if len(msg['text']) > 50 else msg['text']
                    status_text += f"\n{i}. {preview}"
            
            await event.respond(status_text)

        @self.client.on(events.NewMessage(pattern='/clear', from_users=ALLOWED_USER_ID))
        async def clear_queue(event):
            self.messages = []
            self.save_messages()
            logger.info("🗑️ Antrian pesan dibersihkan")
            await event.respond("🗑️ Semua pesan dalam antrian telah dihapus.")

        @self.client.on(events.NewMessage(pattern='/reset_cooldowns', from_users=ALLOWED_USER_ID))
        async def reset_cooldowns(event):
            self.group_cooldowns = {}
            self.save_cooldowns()
            logger.info("🔄 Semua cooldown grup direset")
            await event.respond("🔄 Semua cooldown grup telah direset.")

        @self.client.on(events.NewMessage(pattern='/help', from_users=ALLOWED_USER_ID))
        async def show_help(event):
            help_text = "📚 **Panduan Penggunaan Bot**\n\n" \
                        "Perintah yang tersedia:\n" \
                        "• /start_schedule - Mengaktifkan penjadwalan\n" \
                        "• /stop_schedule - Menonaktifkan penjadwalan\n" \
                        "• /status - Melihat status dan antrian pesan\n" \
                        "• /clear - Membersihkan antrian pesan\n" \
                        "• /reset_cooldowns - Reset semua cooldown grup\n" \
                        "• /help - Menampilkan panduan ini\n\n" \
                        "INTERVAL PESAN DALAM HELP:\n" \
                        "Untuk menambahkan pesan ke antrian, cukup kirim pesan apapun (teks/media) di chat ini.\n" \
                        "Pesan akan diforward ke grup - grup secara otomatis dengan memperhatikan batas waktu cooldown Telegram."
            await event.respond(help_text)

        @self.client.on(events.NewMessage(from_users=ALLOWED_USER_ID))
        async def handle_new_message(event):
            # Ignore commands
            if event.raw_text and event.raw_text.startswith('/'):
                return

            try:
                message_data = {
                    'id': event.message.id,
                    'text': event.raw_text if event.raw_text else "(Media)",
                    'has_media': event.message.media is not None,
                    'timestamp': int(time.time())
                }
                
                self.add_message(message_data)
                logger.info(f"Pesan baru ditambahkan ke antrian. Jumlah pesan: {len(self.messages)}")
                await event.respond("✅ Pesan ditambahkan ke antrian penjadwalan.")
                
            except Exception as e:
                logger.error(f"Error menambahkan pesan: {str(e)}")
                await event.respond("❌ Error menambahkan pesan ke antrian.")

        self.handlers_setup = True
        logger.info("Event handlers have been set up successfully")

    async def connect_to_user(self):
        """Menghubungkan ke user yang diizinkan"""
        try:
            # Try multiple methods to connect to the user
            methods = [
                # Method 1: Try with username
                lambda: self.client.get_entity(f"@{ALLOWED_USERNAME}"),
                # Method 2: Try with user ID
                lambda: self.client.get_entity(ALLOWED_USER_ID),
                # Method 3: Try getting input entity from username
                lambda: self.client.get_input_entity(f"@{ALLOWED_USERNAME}"),
                # Method 4: Try getting input entity from ID
                lambda: self.client.get_input_entity(ALLOWED_USER_ID)
            ]

            for method in methods:
                try:
                    self.allowed_user = await method()
                    if self.allowed_user:
                        logger.info(f"Successfully connected to user: {getattr(self.allowed_user, 'username', ALLOWED_USER_ID)}")
                        return True
                except Exception as e:
                    logger.debug(f"Connection attempt failed: {str(e)}")
                    continue

            logger.error("All connection methods failed")
            return False

        except Exception as e:
            logger.error(f"Error connecting to user: {str(e)}")
            return False

    async def extract_cooldown_time(self, error_message):
        """Ekstrak waktu cooldown dari pesan error Telegram"""
        try:
            # Coba ekstrak waktu dari error "A wait of X seconds is required..."
            import re
            match = re.search(r'A wait of (\d+) seconds is required', error_message)
            if match:
                return int(match.group(1))
            return 3600  # Default 1 jam jika tidak bisa mengekstrak
        except:
            return 3600  # Default 1 jam jika terjadi error

    async def forward_messages(self):
        """Forward messages to target groups with proper error handling and cooldown management"""
        while True:
            try:
                if self.is_active and not self.is_forwarding and self.messages:
                    self.is_forwarding = True
                    logger.info("Starting scheduled message forwarding process...")
                    
                    message = self.messages[0]
                    message_id = message['id']
                    
                    # Ensure we're still connected to the user
                    if not self.allowed_user or not await self.connect_to_user():
                        logger.error("Cannot process forward: User connection unavailable")
                        self.is_forwarding = False
                        # INTERVAL RETRY - Ubah ke 60 untuk produksi
                        await asyncio.sleep(3600)  # Wait before retrying
                        continue
                    
                    try:
                        # Get original message
                        original_message = await self.client.get_messages(self.allowed_user, ids=message_id)
                        
                        if not original_message:
                            logger.warning(f"Message with ID {message_id} not found, removing from queue")
                            self.remove_message(message_id)
                            self.is_forwarding = False
                            continue
                        
                        # Track successful forwards
                        forward_success = []
                        
                        # Find groups that are not in cooldown
                        available_groups = []
                        for group_id in TARGET_GROUPS:
                            in_cooldown, remaining = self.is_group_in_cooldown(group_id)
                            if not in_cooldown:
                                available_groups.append(group_id)
                            else:
                                logger.info(f"Skipping group {group_id}, in cooldown for {remaining} seconds")
                        
                        if not available_groups:
                            logger.info("All groups are in cooldown, will try again later")
                            self.is_forwarding = False
                            # UBAH BARIS INI UNTUK INTERVAL:
                            # Untuk testing: 30 detik
                            # Untuk produksi: lebih lama (600+ detik)
                            await asyncio.sleep(30)  # <- Ubah angka disini untuk mengganti interval jika semua grup dalam cooldown
                            continue
                        
                        # Forward to available groups
                        for group_id in available_groups:
                            try:
                                # Forward to group
                                result = await self.client.forward_messages(
                                    group_id,
                                    original_message
                                )
                                
                                if result:
                                    logger.info(f"Message successfully forwarded to group {group_id}")
                                    forward_success.append(group_id)
                                    # Set cooldown untuk grup besar (60 detik untuk testing)
                                    # Di produksi, ini bisa ditingkatkan jika perlu
                                    self.set_group_cooldown(group_id, 60)  
                                    await asyncio.sleep(1)  # Delay between forwards
                                else:
                                    logger.warning(f"Failed to forward message to group {group_id}")
                                
                            except Exception as e:
                                error_str = str(e)
                                logger.error(f"Error forwarding to group {group_id}: {error_str}")
                                
                                # Jika error karena flood/wait, ekstrak waktu cooldown dan set
                                if "wait" in error_str.lower() and "seconds" in error_str.lower():
                                    cooldown = await self.extract_cooldown_time(error_str)
                                    # Tambahkan sedikit margin untuk keamanan
                                    cooldown = cooldown + 60
                                    self.set_group_cooldown(group_id, cooldown)
                                else:
                                    # Set cooldown default 1 jam untuk error lainnya
                                    self.set_group_cooldown(group_id, 3600)
                        
                        # Remove message if forwarded to at least one group
                        if forward_success:
                            self.remove_message(message_id)
                            logger.info(f"Message {message_id} removed from queue after successful forwards")
                        
                    except Exception as e:
                        logger.error(f"Error processing message {message_id}: {str(e)}")
                    
                    self.is_forwarding = False
                
                # UBAH BARIS INI UNTUK INTERVAL:
                # Untuk testing: 5 detik
                # Untuk produksi: 3600 detik (1 jam)
                await asyncio.sleep(5)  # <- Ubah angka 5 disini untuk mengganti interval
                
            except Exception as e:
                logger.error(f"Error in scheduling process: {str(e)}")
                self.is_forwarding = False
                # INTERVAL RETRY ERROR - Ubah ke 60 untuk produksi
                await asyncio.sleep(5)  # Wait before retrying

    async def start(self):
        try:
            # Mulai client
            await self.client.start()
            logger.info("Client telah terhubung")
            
            # Coba terhubung dengan user yang diizinkan
            if await self.connect_to_user():
                # Setup event handlers sekali saja
                await self.setup_handlers()
                
                # Kirim pesan startup
                try:
                    startup_message = "🚀 Bot penjadwal pesan telah aktif! (Mode cooldown aware)\n\nKetik /help untuk melihat panduan penggunaan."
                    await self.client.send_message(self.allowed_user, startup_message)
                    logger.info("Pesan startup berhasil dikirim")
                except Exception as e:
                    logger.error(f"Gagal mengirim pesan startup: {str(e)}")
                
                # Jalankan task penjadwalan
                asyncio.create_task(self.forward_messages())
                
                # Jalankan client
                await self.client.run_until_disconnected()
            else:
                logger.error("Tidak dapat terhubung dengan user yang diizinkan")
                
        except Exception as e:
            logger.error(f"Error saat menjalankan client: {str(e)}")

if __name__ == '__main__':
    scheduler = MessageScheduler()
    scheduler.client.loop.run_until_complete(scheduler.start())