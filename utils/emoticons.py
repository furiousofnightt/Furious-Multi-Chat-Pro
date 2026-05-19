import base64
import urllib.request
import os
import gzip
import tempfile
import shutil
import atexit
from PyQt6.QtGui import QImage
from PyQt6.QtCore import QUrl

# Criar pasta temporária única para esta sessão de chat
# Ela será apagada 100% ao fechar o programa
SESSION_TEMP_DIR = tempfile.mkdtemp(prefix="furious_chat_emotes_")

def cleanup_emotes():
    """Remove a pasta temporária de emotes ao encerrar."""
    if os.path.exists(SESSION_TEMP_DIR):
        try:
            shutil.rmtree(SESSION_TEMP_DIR, ignore_errors=True)
            # print(f"♻️ Pasta temporária de emotes removida: {SESSION_TEMP_DIR}")
        except: pass

# Registrar para apagar ao sair do Python
atexit.register(cleanup_emotes)

# Cache de URLs (Desta vez apontando para arquivos locais)
EMOTE_CACHE = {}

def get_emote_url(url, emote_id):
    """
    Baixa o emote para um arquivo temporário e retorna o caminho file:///
    Isso é 100% mais estável que Base64 no QLabel do Windows.
    """
    if emote_id in EMOTE_CACHE:
        return EMOTE_CACHE[emote_id]
        
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = response.read()
            
            # Descompressão GZIP se necessário
            if response.info().get('Content-Encoding') == 'gzip' or raw_data.startswith(b'\x1f\x8b\x08'):
                try: data = gzip.decompress(raw_data)
                except: data = raw_data
            else:
                data = raw_data
                
            if len(data) < 50: return None
                
            # Salvar como arquivo real
            # Usamos o ID do emote como nome de arquivo para evitar duplicatas
            ext = ".png"
            if data.startswith(b'GIF'): ext = ".gif"
            elif b'WEBP' in data[:16]: ext = ".webp"
            
            file_path = os.path.join(SESSION_TEMP_DIR, f"{emote_id}{ext}")
            
            with open(file_path, "wb") as f:
                f.write(data)
            
            # Gerar URL file:/// compatível com HTML do QLabel
            local_url = QUrl.fromLocalFile(file_path).toString()
            
            EMOTE_CACHE[emote_id] = local_url
            return local_url
            
    except Exception as e:
        return None

# Buffer para mapeamento de emotes de terceiros (7TV/BTTV)
THIRD_PARTY_CACHE = {
    "thimag1Risada": "651f893e3752e5576d1e4335",
    "KEKW": "60ae5267e0358896085e3966",
    "LULW": "60ae5244e0358896085e3962",
    "POGGERS": "60ae529ee0358896085e3972",
    "CatJAM": "60af456be0358896085e3a5a",
}

def resolve_7tv_emote(emote_name):
    """Tenta encontrar um emote da 7TV pelo nome."""
    if emote_name in THIRD_PARTY_CACHE:
        emote_id = THIRD_PARTY_CACHE[emote_name]
        return f"https://cdn.7tv.app/emote/{emote_id}/1x.webp", f"7tv_{emote_name}"
    return None, None

# Mapeamento expandido de emoticons nativos das plataformas
# Usado para converter emoticons de código para emojis

EMOTICONS_MAP = {
    # ===== EMOÇÕES BÁSICAS =====
    "[laugh]": "🤣", "[cry]": "😢", "[shock]": "😱", "[smile]": "😊",
    "[laughcry]": "😂", "[rockyproud]": "🤘",
    "[complacent]": "😎", "[envy]": "😒", "[happy]": "😊", "[slap]": "😞",
    "[tears]": "😭", "[stunned]": "😲", "[cute]": "😊", "[blink]": "😉",
    "[look]": "🙄", "[cool]": "😎", "[wow]": "😮", "[wicked]": "😈",
    "[huffy]": "😤", "[scream]": "😱", "[rage]": "😡", "[thinking]": "🤔",
    "[shame]": "😳", "[disdain]": "😒", "[funnyface]": "😜",
    "[tongue]": "😛", "[drool]": "🤤", "[yell]": "😫", "[surprised]": "😲",
    "[cool]": "😎", "[love]": "😍", "[angry]": "😠", "[sad]": "😞",
    "[wink]": "😉", "[tongue]": "😛", "[nerd]": "🤓", "[confused]": "😕",
    "[sleepy]": "😴", "[sick]": "🤒", "[dizzy]": "😵", "[star_eyes]": "🤩",
    "[thinking]": "🤔", "[laughing]": "😆", "[innocent]": "😇", "[unamused]": "😒",
    "[neutral]": "😐", "[expressionless]": "😑", "[no_mouth]": "😶", "[anguished]": "😧",
    "[open_mouth]": "😮", "[weary]": "😩", "[tired]": "😫", "[relieved]": "😌",
    
    # ===== EMOTES POPULARES DA TWITCH =====
    # KEKW e variações
    "KEKW": "😆", "KEK": "😂", "LULW": "🤣", "LUL": "😂", "OMEGALUL": "🤣",
    
    # Emotes de reação
    "MonkaS": "😰", "Monkas": "😰", "POGGERS": "😲", "POG": "😊", "Pog": "😊",
    "HOLY": "😲", "CLAP": "👏", "clap": "👏",
    "GG": "🎮", "gg": "🎮", "AYAYA": "👧", "WAYTOODANK": "🔥",
    
    # Emotes de personalidade
    "CatJAM": "🎧", "Sadge": "😔", "COPIUM": "😤", "HOPIUM": "🤞",
    "PepeLaugh": "😂", "PepeHands": "😢", "Peepo": "👀", "Pepega": "🤪",
    "5Head": "🍷", "big5Head": "🍷", "BRAIN": "🧠", "coomer": "🤤",
    
    # Emotes gestuais e corporais
    "HandsUp": "🙌", "Hands": "👐", "WidePeepoHappy": "😊", "Widepeeposad": "😢",
    "DansGame": "🤢", "NotLikeThis": "😩", "PJSalt": "😤",
    
    # Emotes customizadas populares Twitch
    "WutFace": "😮", "BibleThump": "😭",
    "Jebaited": "😏", "twitchRPG": "🎮", "TriHard": "💪", "ResidentSleeper": "😴",
    
    # ===== EMOTES DO KICK =====
    "KICKPOG": "😊", "KICKFIRE": "🔥", "KICKLET": "⬅️", 
    "KICKRIGHT": "➡️", "KICKUP": "⬆️", "KICKDOWN": "⬇️",
    
    # ===== OBJETOS E SÍMBOLOS =====
    "[heart]": "❤️", "[rose]": "🌹", "[fire]": "🔥", "[sparkle]": "✨",
    "[star]": "⭐", "[crown]": "👑", "[100]": "💯", "[clap]": "👏",
    "[pray]": "🙏", "[eyes]": "👀", "[muscle]": "💪", "[rocket]": "🚀",
    "[money]": "💰", "[gift]": "🎁", "[party]": "🎉", "[balloon]": "🎈",
    "[cake]": "🎂", "[pizza]": "🍕", "[beer]": "🍺", "[wine]": "🍷",
    "[cocktail]": "🍹", "[coffee]": "☕", "[skull]": "💀", "[bomb]": "💣",
    "[thunder]": "⚡", "[lightning]": "⚡", "[sun]": "☀️", "[moon]": "🌙",
    "[diamond]": "💎", "[gem]": "💎", "[key]": "🔑", "[lock]": "🔒",
    "[sword]": "⚔️", "[shield]": "🛡️", "[target]": "🎯", "[medal]": "🏅",
    "[trophy]": "🏆", "[ring]": "💍", "[hourglass]": "⏳",
    
    # ===== GESTOS E AÇÕES =====
    "[dance]": "💃", "[wave]": "👋", "[thumbs_up]": "👍", "[thumbs_down]": "👎",
    "[ok]": "👌", "[point_right]": "👉", "[point_left]": "👈", "[raised_hand]": "✋",
    "[punch]": "👊", "[fist]": "✊", "[handshake]": "🤝",
    "[raising_hand]": "🙋", "[woman_dancing]": "💃", "[man_dancing]": "🕺",
    "[running]": "🏃", "[walking]": "🚶", "[standing]": "🧍",
    
    # ===== VALIDAÇÃO E NEGAÇÃO =====
    "[yep]": "✅", "[nop]": "❌", "[check]": "✔️", "[cross]": "❌",
    "[no_entry]": "🚫", "[warning]": "⚠️", "[prohibited]": "🚯", "[ok_button]": "🆗",
    "[negative]": "🆖", "[no]": "⛔", "[yes]": "✅", "[true]": "✅", "[false]": "❌",
    
    # ===== JOGOS E ENTRETENIMENTO =====
    "[gg]": "🎮", "[game]": "🎮", "[video_game]": "🕹️", "[sports]": "⚽",
    "[football]": "🏈", "[basketball]": "🏀", "[baseball]": "⚾",
    "[darts]": "🎯", "[bowling]": "🎳", "[billiards]": "🎱", "[tennis]": "🎾",
    "[ping_pong]": "🏓", "[hockey]": "🎾", "[dice]": "🎲", "[cards]": "🃏",
    "[circus_tent]": "🎪", "[roller_coaster]": "🎢", "[carousel]": "🎠",
    
    # ===== ANIMAIS =====
    "[cat]": "🐱", "[dog]": "🐶", "[monkey]": "🐵", "[pig]": "🐷",
    "[rabbit]": "🐰", "[bird]": "🦅", "[fish]": "🐠", "[snake]": "🐍",
    "[panda]": "🐼", "[koala]": "🐨", "[bear]": "🐻", "[lion]": "🦁",
    "[tiger]": "🐯", "[elephant]": "🐘", "[horse]": "🐴", "[cow]": "🐄",
    "[penguin]": "🐧", "[owl]": "🦉", "[duck]": "🦆", "[swan]": "🦢",
    "[butterfly]": "🦋", "[bee]": "🐝", "[spider]": "🕷️", "[scorpion]": "🦂",
    "[shark]": "🦈", "[dolphin]": "🐬", "[whale]": "🐳", "[dinosaur]": "🦕",
    
    # ===== NATUREZA =====
    "[tree]": "🌳", "[flower]": "🌸", "[grass]": "🌱", "[cactus]": "🌵",
    "[watermelon]": "🍉", "[strawberry]": "🍓", "[apple]": "🍎", "[banana]": "🍌",
    "[lemon]": "🍋", "[orange]": "🍊", "[grapes]": "🍇", "[cherry]": "🍒",
    "[pineapple]": "🍍", "[kiwi]": "🥝", "[avocado]": "🥑", "[coconut]": "🥥",
    "[corn]": "🌽", "[broccoli]": "🥦", "[carrot]": "🥕", "[tomato]": "🍅",
    "[cucumber]": "🥒", "[mushroom]": "🍄", "[peanuts]": "🥜",
    
    # ===== VIAGENS E LUGARES =====
    "[car]": "🚗", "[bus]": "🚌", "[train]": "🚆", "[airplane]": "✈️",
    "[rocket_ship]": "🚀", "[boat]": "⛵", "[ship]": "🚢", "[house]": "🏠",
    "[castle]": "🏰", "[mountain]": "⛰️", "[beach]": "🏖️", "[forest]": "🌲",
    "[desert]": "🏜️", "[volcano]": "🌋", "[bridge]": "🌉", "[city]": "🌃",
    "[temple]": "🏯", "[church]": "⛪", "[hospital]": "🏥", "[school]": "🏫",
    
    # ===== DIVERSOS =====
    "[clock]": "⏰", "[watch]": "⌚", "[alarm]": "🔔",
    "[camera]": "📷", "[telescope]": "🔭", "[microscope]": "🔬",
    "[book]": "📖", "[pencil]": "✏️", "[paintbrush]": "🎨", "[music]": "🎵",
    "[notes]": "🎶", "[microphone]": "🎤", "[headphones]": "🎧", "[radio]": "📻",
    "[phone]": "☎️", "[computer]": "💻", "[keyboard]": "⌨️", "[mouse]": "🖱️",
    "[lightbulb]": "💡", "[candle]": "🕯️", "[flashlight]": "🔦", "[lantern]": "🏮",
    "[lamp]": "🪔", "[fireplace]": "🔥",
    
    # ===== NÚMEROS E SÍMBOLOS ADICIONAIS =====
    "[1]": "1️⃣", "[2]": "2️⃣", "[3]": "3️⃣", "[4]": "4️⃣", "[5]": "5️⃣",
    "[6]": "6️⃣", "[7]": "7️⃣", "[8]": "8️⃣", "[9]": "9️⃣", "[0]": "0️⃣",
    "[plus]": "➕", "[minus]": "➖", "[divide]": "➗", "[multiply]": "✖️",
    "[arrow_up]": "⬆️", "[arrow_down]": "⬇️",
    "[arrow_left]": "⬅️", "[arrow_right]": "➡️",

    # ===== EMOTICONS NATIVOS DO TIKTOK LIVE =====
    # Personagens / Mascotes TikTok
    "[rosiecute]": "🌹😊", "[loverose]": "🌹❤️", "[rose]": "🌹",
    "[tiktokrose]": "🌹", "[prettyrose]": "🌹✨",

    # Emoções TikTok (nomes específicos do app)
    "[facewithtearsofhappy]": "😂", "[facewithtears]": "😂",
    "[happyface]": "😊", "[sadface]": "😢", "[cryingface]": "😭",
    "[angryface]": "😠", "[lovingface]": "🥰", "[kissingface]": "😘",
    "[winkingface]": "😉", "[thinkingface]": "🤔", "[shockedface]": "😱",
    "[scaredface]": "😨", "[disgustedface]": "🤮", "[sleepyface]": "😴",
    "[sickface]": "🤒", "[hotface]": "🥵", "[coldface]": "🥶",
    "[explodinghead]": "🤯", "[partying]": "🥳", "[cowboy]": "🤠",
    "[nerd]": "🤓", "[sunglasses]": "😎", "[monocle]": "🧐",
    "[hushed]": "😯", "[flushed]": "😳", "[zipper]": "🤐",
    "[saluting]": "🫡", "[melting]": "🫠", "[shaking]": "🫨",
    "[dotted]": "😶‍🌫️", "[cloudface]": "😶‍🌫️",

    # Gestos TikTok
    "[heart_hands]": "🫶", "[shake_hands]": "🤝", "[hand_ok]": "👌",
    "[thumbup]": "👍", "[thumbdown]": "👎", "[clapping]": "👏",
    "[raising_hands]": "🙌", "[folded_hands]": "🙏", "[waving]": "👋",
    "[crossed_fingers]": "🤞", "[pinching]": "🤌", "[love_you]": "🤟",
    "[rock_on]": "🤘", "[point_up]": "☝️", "[fist_bump]": "🤜",
    "[writing]": "✍️", "[nail_polish]": "💅", "[selfie]": "🤳",
    "[call_me]": "🤙", "[backhand_index]": "👆",

    # Corações e amor TikTok
    "[redhart]": "❤️", "[orangeheart]": "🧡", "[yellowheart]": "💛",
    "[greenheart]": "💚", "[blueheart]": "💙", "[purpleheart]": "💜",
    "[blackheart]": "🖤", "[whiteheart]": "🤍", "[brownheart]": "🤎",
    "[pinkheart]": "🩷", "[lightblueheart]": "🩵", "[greyheart]": "🩶",
    "[heartexclamation]": "❣️", "[twohearts]": "💕", "[heartarrow]": "💘",
    "[heartribbon]": "💝", "[sparkleheart]": "💖", "[hearthands]": "🫶",
    "[revolving_hearts]": "💞", "[heartpulse]": "💗", "[beating_heart]": "💓",
    "[broken_heart]": "💔", "[heartfire]": "❤️‍🔥", "[heartmend]": "❤️‍🩹",
    "[lovit]": "💕", "[lovelyface]": "😍",

    # Símbolos e itens TikTok específicos
    "[streamer]": "🎙️", "[live]": "🔴", "[camera_flash]": "📸",
    "[like]": "👍", "[follow]": "➕", "[share]": "🔗",
    "[coins]": "🪙", "[diamond_gift]": "💎", "[universe]": "🌌",
    "[galaxy]": "🌌", "[comet]": "☄️", "[meteor]": "🌠",
    "[firework]": "🎆", "[sparkles]": "✨", "[glowing_star]": "🌟",
    "[dizzy_symbol]": "💫",

    # Emojis de celebração TikTok
    "[birthday]": "🎂", "[confetti]": "🎊", "[tada]": "🎉",
    "[wrapped_gift]": "🎁", "[champagne]": "🍾", "[trophy_cup]": "🏆",
    "[1st_place]": "🥇", "[2nd_place]": "🥈", "[3rd_place]": "🥉",

    # Clima e natureza TikTok
    "[rainbow]": "🌈", "[sunny]": "☀️", "[cloudy]": "☁️",
    "[stormy]": "⛈️", "[snowy]": "❄️", "[windy]": "🌬️",
    "[foggy]": "🌫️", "[wave_water]": "🌊", "[splash]": "💦",
    "[droplet]": "💧", "[hot_spring]": "♨️", "[snowflake]": "❄️",

    # Comida TikTok
    "[boba]": "🧋", "[popcorn]": "🍿", "[icecream]": "🍦",
    "[donut]": "🍩", "[cookie]": "🍪", "[candy]": "🍬",
    "[chocolate]": "🍫", "[cupcake]": "🧁", "[pie]": "🥧",
    "[burger]": "🍔", "[fries]": "🍟", "[hotdog]": "🌭",
    "[taco]": "🌮", "[sushi]": "🍣", "[ramen]": "🍜",
    "[dumplings]": "🥟", "[rice_ball]": "🍙",

    # Gaming TikTok  
    "[joystick]": "🕹️", "[gaming]": "🎮", "[controller]": "🎮",
    "[pac_man]": "👾", "[space_invader]": "👾", "[chess]": "♟️",
    "[puzzle]": "🧩", "[slot_machine]": "🎰", "[dart]": "🎯",
}

def convert_emoticons(text):
    """
    Converte emoticons de código para emojis.
    
    Args:
        text (str): Texto contendo emoticons no formato [codigo]
        
    Returns:
        str: Texto com emoticons convertidos para emojis
    """
    result = text
    for code, emoji in EMOTICONS_MAP.items():
        result = result.replace(code, emoji)
    return result

def get_emoticons():
    """Retorna o dicionário completo de emoticons"""
    return EMOTICONS_MAP.copy()

def add_emoticon(code, emoji):
    """
    Adiciona um novo emoticon ao mapa.
    
    Args:
        code (str): Código do emoticon (ex: "[novo]")
        emoji (str): Emoji correspondente
    """
    EMOTICONS_MAP[code] = emoji

def remove_emoticon(code):
    """Remove um emoticon do mapa"""
    if code in EMOTICONS_MAP:
        del EMOTICONS_MAP[code]
