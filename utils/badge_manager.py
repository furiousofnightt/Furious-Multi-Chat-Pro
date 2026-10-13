"""
Gerenciador Central de Badges Originais para Twitch, TikTok, Kick e YouTube.

Permite que o chat exiba as insígnias e selos de assinante oficiais
direto das CDNs de cada plataforma, com cache local e fallback para SVGs.
"""

import os
import re
import threading
import httpx
from utils.emoticons import get_emote_url, SESSION_TEMP_DIR
from utils.resource_path import resource_path
from PyQt6.QtGui import QImage, QPainter, QColor, QFont, QFontMetrics, QPainterPath, QIcon
from PyQt6.QtCore import Qt, QRectF, QUrl, QSize

class BadgeManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BadgeManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Cache em memória: chave -> url_local_file_or_html
        self._badge_cache = {}
        
        # Catálogo da Twitch: 'setID/version' -> remote_image_url
        self._twitch_catalog = {}
        self._twitch_channel_loaded = None
        self._twitch_lock = threading.Lock()
        
        # Catálogo do Kick: username -> {months: remote_image_url}
        self._kick_sub_badges = {}
        self._kick_channel_loaded = None
        self._kick_lock = threading.Lock()
        
        # Inicializa catálogo global da Twitch em background
        threading.Thread(target=self._load_twitch_global_catalog, daemon=True).start()

    # =========================================================================
    # 1. TWITCH BADGES
    # =========================================================================

    def _load_twitch_global_catalog(self):
        """Carrega badges globais da Twitch (Mod, VIP, Broadcaster, Staff, etc.) via GQL."""
        url = "https://gql.twitch.tv/gql"
        headers = {
            "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
            "Content-Type": "application/json"
        }
        query = "query { badges { setID version imageURL(size: DOUBLE) title } }"
        try:
            with httpx.Client(timeout=8.0) as client:
                r = client.post(url, json={"query": query}, headers=headers)
                if r.status_code == 200:
                    data = r.json()
                    badges = data.get("data", {}).get("badges", [])
                    with self._twitch_lock:
                        for b in badges:
                            key = f"{b.get('setID')}/{b.get('version')}"
                            self._twitch_catalog[key] = b.get("imageURL")
                    print(f"[Badges Twitch] {len(badges)} badges globais carregadas com sucesso.")
        except Exception as e:
            print(f"[Badges Twitch] Falha ao carregar catalogo global: {e}")

    def load_twitch_channel_badges(self, channel_login: str):
        """Carrega badges de assinante/bits específicas do canal da Twitch."""
        if not channel_login:
            return
        clean_channel = channel_login.lower().replace('#', '').strip()
        if self._twitch_channel_loaded == clean_channel:
            return
        
        def _fetch():
            url = "https://gql.twitch.tv/gql"
            headers = {
                "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
                "Content-Type": "application/json"
            }
            query = """
            query GetChannelBadges($login: String!) {
              user(login: $login) {
                broadcastBadges {
                  setID
                  version
                  imageURL(size: DOUBLE)
                  title
                }
              }
            }
            """
            try:
                with httpx.Client(timeout=8.0) as client:
                    r = client.post(url, json={"query": query, "variables": {"login": clean_channel}}, headers=headers)
                    if r.status_code == 200:
                        data = r.json()
                        badges = data.get("data", {}).get("user", {}).get("broadcastBadges", []) or []
                        with self._twitch_lock:
                            for b in badges:
                                key = f"{b.get('setID')}/{b.get('version')}"
                                self._twitch_catalog[key] = b.get("imageURL")
                            self._twitch_channel_loaded = clean_channel
                        print(f"[Badges Twitch] {len(badges)} badges de canal carregadas para #{clean_channel}.")
            except Exception as e:
                print(f"[Badges Twitch] Erro ao carregar badges de canal: {e}")

        threading.Thread(target=_fetch, daemon=True).start()

    def get_twitch_badges_html(self, badges_tag: str) -> str:
        """
        Converte a tag de badges do IRC da Twitch (ex: 'moderator/1,subscriber/12')
        em tags <img> com as imagens originais da Twitch.
        """
        if not badges_tag:
            return ""

        html_parts = []
        # badges_tag vem como 'broadcaster/1,subscriber/12,partner/1'
        entries = badges_tag.split(',')
        for entry in entries:
            entry = entry.strip()
            if not entry or '/' not in entry:
                continue

            cache_key = f"tw_{entry}"
            if cache_key in self._badge_cache:
                html_parts.append(self._badge_cache[cache_key])
                continue

            # 1. Procura no catálogo oficial da Twitch (GQL)
            remote_url = None
            with self._twitch_lock:
                remote_url = self._twitch_catalog.get(entry)

            local_url = None
            if remote_url:
                local_url = get_emote_url(remote_url, f"tw_badge_{entry.replace('/', '_')}")

            # 2. Se obteve imagem original, usa
            if local_url:
                img_tag = f"<img src='{local_url}' width='18' height='18' style='vertical-align:middle;margin-left:3px;margin-right:1px;'>"
                self._badge_cache[cache_key] = img_tag
                html_parts.append(img_tag)
                continue

            # 3. Fallback: SVGs locais clássicos se a rede ainda não carregou
            set_id = entry.split('/')[0].lower()
            fallback_svg = None
            if set_id in ('broadcaster', 'owner'):
                fallback_svg = 'streamer.svg'
            elif set_id in ('moderator', 'mod'):
                fallback_svg = 'mod.svg'
            elif set_id == 'vip':
                fallback_svg = 'vip.svg'
            elif set_id == 'subscriber':
                fallback_svg = 'subscriber.svg'

            if fallback_svg:
                svg_path = resource_path(f"assets/{fallback_svg}").replace('\\', '/')
                img_tag = f"<img src='file:///{svg_path}' width='18' height='18' style='vertical-align:middle;margin-left:3px;margin-right:1px;'>"
                html_parts.append(img_tag)

        return " ".join(html_parts)

    # =========================================================================
    # 2. TIKTOK BADGES
    # =========================================================================

    def _render_pill_badge(self, icon_local_url: str, text: str, bg_color: str = "#2b498f", text_color: str = "#ffffff", border_color: str = None) -> str:
        """
        Gera uma insígnia estilo pílula arredondada com ícone e texto de nível
        (ex: diamante + 22, coração + Brev, medalha + Nº 1).
        Retorna URL file:/// para a imagem PNG gerada e cacheada.
        """
        cache_key = f"pill_{icon_local_url}_{text}_{bg_color}_{text_color}_{border_color}"
        if cache_key in self._badge_cache:
            return self._badge_cache[cache_key]

        try:
            height = 18
            font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            metrics = QFontMetrics(font)
            text_str = str(text).strip()
            text_width = metrics.horizontalAdvance(text_str) if text_str else 0

            icon_file_path = ""
            if icon_local_url:
                if icon_local_url.startswith("file:///"):
                    icon_file_path = icon_local_url[8:]
                else:
                    icon_file_path = icon_local_url

            has_icon = bool(icon_file_path and os.path.exists(icon_file_path))
            icon_size = 12
            padding_x = 4
            spacing = 3 if (has_icon and text_str) else 0

            total_width = padding_x * 2 + text_width
            if has_icon:
                total_width += icon_size + spacing
            total_width = max(total_width, 18)

            img = QImage(int(total_width), height, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)

            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            path = QPainterPath()
            rect = QRectF(0.5, 0.5, total_width - 1.0, height - 1.0)
            path.addRoundedRect(rect, 4.0, 4.0)

            bg_col = QColor(bg_color) if (bg_color and QColor.isValidColorName(bg_color)) else QColor("#2b498f")
            painter.fillPath(path, bg_col)

            if border_color and QColor.isValidColorName(border_color):
                painter.setPen(QColor(border_color))
                painter.drawPath(path)

            curr_x = padding_x
            if has_icon:
                icon_obj = QIcon(icon_file_path)
                if not icon_obj.isNull():
                    pix = icon_obj.pixmap(QSize(icon_size, icon_size))
                    if not pix.isNull():
                        icon_y = (height - icon_size) / 2.0
                        painter.drawPixmap(int(curr_x), int(icon_y), pix)
                        curr_x += icon_size + spacing

            if text_str:
                painter.setFont(font)
                tx_col = QColor(text_color) if (text_color and QColor.isValidColorName(text_color)) else QColor("#ffffff")
                painter.setPen(tx_col)
                text_y = (height - metrics.height()) / 2.0 + metrics.ascent()
                painter.drawText(int(curr_x), int(text_y), text_str)

            painter.end()

            safe_text = re.sub(r'[^a-zA-Z0-9]', '', text_str)[:12]
            file_name = f"ttk_pill_{safe_text}_{abs(hash(cache_key)) % 1000000}.png"
            out_file = os.path.join(SESSION_TEMP_DIR, file_name)
            img.save(out_file, "PNG")

            local_url = QUrl.fromLocalFile(out_file).toString()
            self._badge_cache[cache_key] = local_url
            return local_url
        except Exception:
            return ""

    def get_tiktok_badges_tuple(self, user_obj) -> tuple[str, str]:
        """
        Extrai as badges oficiais do usuário TikTok completas com seus níveis e nomes
        (ex: Doador Nível 22, Fã-Clube "Brev", Top Gifter "Nº 1") divididas em:
        - Prefix: insígnias à esquerda do nome (Nível Doador, Fã-Clube, Sub, Mod, Streamer)
        - Suffix: insígnias à direita do nome (Top Gifter Rank 1, 2, 3)
        Retorna (prefix_html, suffix_html).
        """
        if not user_obj:
            return ("", "")

        prefix_parts = []
        suffix_parts = []

        added_pay_grade = False
        added_fan = False
        added_rank = False
        added_mod = False
        added_new_gifter = False
        seen_texts = set()

        is_mod = False
        is_host = False
        is_sub = False
        is_pro = False
        is_friend = False
        is_top_gifter = False

        def _extract_cdn_url(obj):
            if not obj:
                return None
            urls = getattr(obj, 'url_list', None) or getattr(obj, 'urls_list', None)
            if urls and isinstance(urls, (list, tuple)) and len(urls) > 0 and str(urls[0]).startswith('http'):
                return str(urls[0])
            inner_img = getattr(obj, 'image', None)
            if inner_img:
                u = _extract_cdn_url(inner_img)
                if u:
                    return u
            if isinstance(obj, dict):
                urls = obj.get('url_list') or obj.get('urls_list')
                if urls and isinstance(urls, (list, tuple)) and len(urls) > 0 and str(urls[0]).startswith('http'):
                    return str(urls[0])
                for v in obj.values():
                    u = _extract_cdn_url(v)
                    if u:
                        return u
            return None

        # -------------------------------------------------------------
        # 1. Nível de Doador / Gifter Level (via user.pay_grade)
        # -------------------------------------------------------------
        pay_grade = getattr(user_obj, 'pay_grade', None)
        if pay_grade:
            try:
                lvl = int(getattr(pay_grade, 'level', 0) or 0)
                if lvl > 0:
                    remote_icon = (
                        _extract_cdn_url(getattr(pay_grade, 'new_im_icon_with_level', None)) or
                        _extract_cdn_url(getattr(pay_grade, 'im_icon_with_level', None)) or
                        _extract_cdn_url(getattr(pay_grade, 'diamond_icon', None)) or
                        _extract_cdn_url(getattr(pay_grade, 'icon', None))
                    )
                    local_icon = None
                    if remote_icon:
                        local_icon = get_emote_url(remote_icon, f"ttk_pg_{lvl}")
                    if not local_icon:
                        local_icon = resource_path('assets/diamond.svg')

                    if lvl < 10:
                        bg_col = "#26497f"
                    elif lvl < 20:
                        bg_col = "#2f449e"
                    elif lvl < 30:
                        bg_col = "#463ba3"
                    elif lvl < 40:
                        bg_col = "#79268c"
                    else:
                        bg_col = "#b35c0d"

                    pill_url = self._render_pill_badge(local_icon, str(lvl), bg_color=bg_col, text_color="#ffffff")
                    if pill_url:
                        prefix_parts.append(f"<img src='{pill_url}' height='18' style='vertical-align:middle;margin-left:3px;margin-right:2px;'>")
                        added_pay_grade = True
            except Exception:
                pass

        # -------------------------------------------------------------
        # 2. Fã-Clube / Fans Club (via user.fans_club)
        # -------------------------------------------------------------
        fans_club = getattr(user_obj, 'fans_club', None)
        fc_data = getattr(fans_club, 'data', None) if fans_club else None
        club_name = (getattr(fc_data, 'club_name', '') or '').strip() if fc_data else ''
        club_lvl = int(getattr(fc_data, 'level', 0) or 0) if fc_data else 0

        if not club_name and not club_lvl:
            mlvl = getattr(user_obj, 'member_level', None)
            if mlvl and str(mlvl).isdigit() and int(mlvl) > 0:
                club_lvl = int(mlvl)

        if club_name or club_lvl > 0:
            try:
                fan_text = club_name if club_name else f"Lv.{club_lvl}"
                fc_badge = getattr(fc_data, 'badge', None) if fc_data else None
                remote_icon = _extract_cdn_url(fc_badge) if fc_badge else None
                local_icon = None
                if remote_icon:
                    local_icon = get_emote_url(remote_icon, f"ttk_fc_{abs(hash(fan_text)) % 100000}")
                if not local_icon:
                    local_icon = resource_path('assets/heart.svg')

                pill_url = self._render_pill_badge(local_icon, fan_text, bg_color="#a04516", text_color="#ffffff")
                if pill_url:
                    prefix_parts.append(f"<img src='{pill_url}' height='18' style='vertical-align:middle;margin-left:3px;margin-right:2px;'>")
                    added_fan = True
            except Exception:
                pass

        # -------------------------------------------------------------
        # 3. Lista de Badges Gerais (user.badge_list)
        # -------------------------------------------------------------
        badge_list = getattr(user_obj, 'badge_list', []) or getattr(user_obj, 'badges', []) or []
        for b in badge_list:
            try:
                scene_name = str(getattr(getattr(b, 'scene_type', None), 'name', '') or '').upper()
                scene_val = getattr(getattr(b, 'scene_type', None), 'value', -1)

                if scene_name == 'ADMIN' or scene_val == 1:
                    is_mod = True
                elif scene_name == 'ANCHOR' or scene_val == 12:
                    is_host = True
                elif scene_name in ('SUBSCRIBER', 'NEW_SUBSCRIBER') or scene_val in (4, 7):
                    is_sub = True
                elif scene_name == 'FRIENDS' or scene_val == 3:
                    is_friend = True
                elif scene_name == 'LIVE_PRO' or scene_val == 11:
                    is_pro = True

                combine = getattr(b, 'combine', None)
                remote_icon = (
                    _extract_cdn_url(getattr(b, 'image', None)) or
                    _extract_cdn_url(getattr(combine, 'icon', None) if combine else None) or
                    _extract_cdn_url(getattr(b, 'origin_img', None))
                )

                level_text = ""
                bg_color = None
                font_color = "#ffffff"
                border_color = None

                if combine:
                    c_text = getattr(combine, 'text', None)
                    if c_text:
                        pieces = getattr(c_text, 'pieces', []) or []
                        pattern = getattr(c_text, 'default_pattern', '') or ''
                        if pieces:
                            if '{0}' in pattern:
                                try: level_text = pattern.format(*pieces).strip()
                                except: level_text = str(pieces[0]).strip()
                            else:
                                level_text = str(pieces[0]).strip()
                        elif pattern and '{' not in pattern:
                            level_text = pattern.strip()

                    if not level_text:
                        c_str = getattr(combine, 'str', '') or ''
                        if c_str and str(c_str).strip():
                            level_text = str(c_str).strip()

                    bg_obj = getattr(combine, 'background', None) or getattr(combine, 'background_dark_mode', None)
                    if bg_obj:
                        bg_color = getattr(bg_obj, 'background_color_code', '') or None
                        border_color = getattr(bg_obj, 'border_color_code', '') or None

                    f_style = getattr(combine, 'font_style', None)
                    if f_style:
                        font_color = getattr(f_style, 'font_color', '#ffffff') or '#ffffff'

                if not level_text:
                    t_obj = getattr(b, 'text', None)
                    if t_obj:
                        pieces = getattr(t_obj, 'pieces', []) or []
                        pattern = getattr(t_obj, 'default_pattern', '') or ''
                        if pieces:
                            if '{0}' in pattern:
                                try: level_text = pattern.format(*pieces).strip()
                                except: level_text = str(pieces[0]).strip()
                            else:
                                level_text = str(pieces[0]).strip()
                        elif pattern and '{' not in pattern:
                            level_text = pattern.strip()

                if not level_text:
                    s_obj = getattr(b, 'str', None)
                    if s_obj:
                        s_val = getattr(s_obj, 'str', '') or getattr(s_obj, 'value', '') or ''
                        if s_val and str(s_val).strip():
                            level_text = str(s_val).strip()

                local_icon = None
                if remote_icon:
                    bid = re.sub(r'[^a-zA-Z0-9]', '', remote_icon.split('/')[-1])[:24]
                    local_icon = get_emote_url(remote_icon, f"ttk_badge_{bid}")

                # TRATAMENTO ESPECIAL PARA MODERADOR:
                # No TikTok, moderador é APENAS o ícone oficial, sem texto "Moderator" e sem formato de pill!
                if scene_name in ('ADMIN', 'MODERATOR') or scene_val == 1 or (level_text and level_text.strip().lower() in ('moderator', 'moderador', 'admin')):
                    is_mod = True
                    if added_mod:
                        continue # Evita duplicatas
                    if local_icon:
                        prefix_parts.append(f"<img src='{local_icon}' width='18' height='18' style='vertical-align:middle;margin-left:3px;margin-right:2px;' title='Moderador'>")
                        added_mod = True
                    continue

                # TRATAMENTO ESPECIAL PARA NOVO DOADOR / NEW GIFTER (FIRST_RECHARGE):
                # O TikTok envia versões duplicadas (legada sem ícone e estilizada com caixinha/fundo cinza).
                # Padroniza na pílula azul com Diamante [💎 New gifter] e elimina a duplicata cinza.
                is_first_recharge = (
                    scene_name == 'FIRST_RECHARGE' or
                    scene_val == 2 or
                    (level_text and 'NEW GIFTER' in level_text.upper()) or
                    (level_text and 'NOVO DOADOR' in level_text.upper())
                )
                if is_first_recharge:
                    if added_new_gifter:
                        continue # Evita qualquer versão duplicada
                    dia_icon = resource_path('assets/diamond.svg')
                    pill_text = level_text if level_text else "New gifter"
                    pill_url = self._render_pill_badge(
                        dia_icon, pill_text,
                        bg_color="#2b498f",
                        text_color="#ffffff"
                    )
                    if pill_url:
                        prefix_parts.append(f"<img src='{pill_url}' height='18' style='vertical-align:middle;margin-left:3px;margin-right:2px;' title='{pill_text}'>")
                        added_new_gifter = True
                    continue

                # Evita qualquer texto de badge duplicado entre diferentes objetos do TikTok
                if level_text:
                    clean_text_key = level_text.strip().lower()
                    if clean_text_key in seen_texts:
                        continue
                    seen_texts.add(clean_text_key)

                # A: TOP GIFTER / RANK BADGE (ex: Nº 1, Nº 2) -> Suffix
                if scene_val == 6 or 'RANK' in scene_name or (level_text and any(rk in level_text.upper() for rk in ('Nº', 'NO.', 'TOP', 'RANK'))):
                    if added_rank:
                        continue
                    rank_text = level_text if level_text else "Nº 1"
                    if not local_icon:
                        local_icon = resource_path('assets/rank_1.svg')
                    pill_url = self._render_pill_badge(
                        local_icon, rank_text,
                        bg_color=bg_color or "#9b1e45",
                        text_color=font_color or "#ffffff",
                        border_color=border_color
                    )
                    if pill_url:
                        suffix_parts.append(f"<img src='{pill_url}' height='18' style='vertical-align:middle;margin-left:3px;margin-right:1px;'>")
                        added_rank = True
                    continue

                # B: FÃ-CLUBE
                if scene_val == 10 or 'FAN' in scene_name:
                    if added_fan:
                        continue
                    fan_text = level_text if level_text else "Fã"
                    if not local_icon:
                        local_icon = resource_path('assets/heart.svg')
                    pill_url = self._render_pill_badge(
                        local_icon, fan_text,
                        bg_color=bg_color or "#a04516",
                        text_color=font_color or "#ffffff",
                        border_color=border_color
                    )
                    if pill_url:
                        prefix_parts.append(f"<img src='{pill_url}' height='18' style='vertical-align:middle;margin-left:3px;margin-right:2px;'>")
                        added_fan = True
                    continue

                # C: NÍVEL DE DOADOR / GIFTER
                if 'GRADE' in scene_name or 'LEVEL' in scene_name or (level_text and level_text.isdigit()):
                    if added_pay_grade:
                        continue
                    if not local_icon:
                        local_icon = resource_path('assets/diamond.svg')
                    pill_url = self._render_pill_badge(
                        local_icon, level_text,
                        bg_color=bg_color or "#463ba3",
                        text_color=font_color or "#ffffff",
                        border_color=border_color
                    )
                    if pill_url:
                        prefix_parts.append(f"<img src='{pill_url}' height='18' style='vertical-align:middle;margin-left:3px;margin-right:2px;'>")
                        added_pay_grade = True
                    continue

                # D: OUTRA BADGE COM TEXTO
                if level_text:
                    pill_url = self._render_pill_badge(
                        local_icon, level_text,
                        bg_color=bg_color or "#2b498f",
                        text_color=font_color or "#ffffff",
                        border_color=border_color
                    )
                    if pill_url:
                        prefix_parts.append(f"<img src='{pill_url}' height='18' style='vertical-align:middle;margin-left:3px;margin-right:2px;'>")
                        continue

                # E: ÍCONE PURO (sem texto)
                if local_icon:
                    prefix_parts.append(f"<img src='{local_icon}' width='18' height='18' style='vertical-align:middle;margin-left:3px;margin-right:2px;'>")

            except Exception:
                pass

        # -------------------------------------------------------------
        # 4. Fallbacks adicionais de status
        # -------------------------------------------------------------
        def badge_img(svg_name):
            path = resource_path(f'assets/{svg_name}').replace('\\', '/')
            return (f"<img src='file:///{path}' width='18' height='18' "
                    f"style='vertical-align:middle;margin-left:3px;margin-right:2px;'>")

        if getattr(user_obj, 'verified', False):
            prefix_parts.insert(0, badge_img('tiktok_verified.svg'))
        if is_host:
            prefix_parts.insert(0, badge_img('tiktok_host.svg'))
        if (is_mod or getattr(user_obj, 'is_moderator', False)) and not added_mod:
            prefix_parts.append(badge_img('tiktok_mod.svg'))
            added_mod = True
        if is_pro:
            prefix_parts.append(badge_img('tiktok_live_pro.svg'))
        if is_sub:
            prefix_parts.append(badge_img('tiktok_sub.svg'))
        if is_friend:
            prefix_parts.append(badge_img('tiktok_friend.svg'))
        if (getattr(user_obj, 'is_top_gifter', False) or is_top_gifter) and not added_rank:
            suffix_parts.append(badge_img('tiktok_top_gifter.svg'))

        prefix_html = (" " + " ".join(prefix_parts) + " ") if prefix_parts else ""
        suffix_html = (" " + " ".join(suffix_parts)) if suffix_parts else ""

        return (prefix_html, suffix_html)

    def get_tiktok_badges_html(self, user_obj) -> str:
        """Retorna todas as badges do TikTok em uma única string HTML."""
        prefix, suffix = self.get_tiktok_badges_tuple(user_obj)
        return f"{prefix}{suffix}".strip()

    # =========================================================================
    # 3. KICK BADGES
    # =========================================================================

    def load_kick_channel_badges(self, channel_slug: str):
        """Carrega badges de assinante personalizadas do canal da Kick."""
        if not channel_slug:
            return
        slug = channel_slug.lower().strip()
        if self._kick_channel_loaded == slug:
            return

        def _fetch():
            import sqlite3
            token = None
            if os.path.exists("kick_tokens.db"):
                try:
                    conn = sqlite3.connect("kick_tokens.db")
                    row = conn.execute("SELECT access_token FROM tokens LIMIT 1").fetchone()
                    if row: token = row[0]
                    conn.close()
                except Exception:
                    pass

            headers = {"Accept": "application/json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            try:
                # Tenta primeiro com curl_cffi para evitar Cloudflare, se disponível
                try:
                    from curl_cffi import requests
                    resp = requests.get(f"https://kick.com/api/v2/channels/{slug}", headers=headers, timeout=10)
                except Exception:
                    resp = httpx.get(f"https://kick.com/api/v2/channels/{slug}", headers=headers, timeout=10)

                if resp.status_code == 200:
                    data = resp.json()
                    sub_badges = data.get("subscriber_badges", []) or []
                    with self._kick_lock:
                        channel_map = {}
                        for b in sub_badges:
                            months = b.get("months", 1)
                            img_obj = b.get("badge_image", {})
                            src = img_obj.get("src", "")
                            if src:
                                channel_map[months] = src
                        self._kick_sub_badges[slug] = channel_map
                        self._kick_channel_loaded = slug
                    print(f"[Badges Kick] {len(sub_badges)} badges de assinante carregadas para {slug}.")
            except Exception as e:
                print(f"[Badges Kick] Erro ao carregar badges do canal {slug}: {e}")

        threading.Thread(target=_fetch, daemon=True).start()

    def get_kick_badges_html(self, badges_data, channel_slug: str = "", badges_v2: list = None) -> str:
        """
        Converte as badges da Kick em tags <img> oficiais.
        Suporta badges do canal (subscriber por mês, moderador, vip, etc.) e badges_v2 (níveis, badges globais).
        """
        if not badges_data and not badges_v2:
            return ""

        html_parts = []
        slug = channel_slug.lower().strip() if channel_slug else ""

        svg_map = {
            'MODERATOR': 'kick_moderator.svg',
            'MOD': 'kick_moderator.svg',
            'VIP': 'kick_vip.svg',
            'VERIFIED': 'kick_verified.svg',
            'VERIFIED_CHANNEL': 'kick_verified.svg',
            'VERIFIED CHANNEL': 'kick_verified.svg',
            'BROADCASTER': 'kick_broadcaster.svg',
            'HOST': 'kick_broadcaster.svg',
            'STREAMER': 'kick_broadcaster.svg',
            'FOUNDER': 'kick_founder.svg',
            'FUNDADOR': 'kick_founder.svg',
            'OG': 'kick_og.svg',
            'BOT': 'kick_bot.svg',
            'STAFF': 'kick_staff.svg',
            'SIDEKICK': 'kick_sidekick.svg',
            'SUBSCRIBER': 'kick_subscriber.svg',
            'SUB': 'kick_subscriber.svg',
            'ASSINANTE': 'kick_subscriber.svg',
            'SUB_GIFTER': 'kick_sub_gifter.svg',
            'SUB GIFTER': 'kick_sub_gifter.svg'
        }

        # 1. Processa badges tradicionais (moderador, vip, verificado, sub, etc.)
        if badges_data:
            for b in badges_data:
                b_type = ""
                count = 1
                if isinstance(b, str):
                    b_type = b.upper()
                elif isinstance(b, dict):
                    b_type = str(b.get("type", "")).upper()
                    count = b.get("count", b.get("months", 1))

                cache_key = f"kick_{slug}_{b_type}_{count}"
                if cache_key in self._badge_cache:
                    html_parts.append(self._badge_cache[cache_key])
                    continue

                local_url = None

                # Se for subscriber, verifica se temos badge personalizada do canal para os meses
                if b_type in ("SUBSCRIBER", "SUB", "ASSINANTE"):
                    with self._kick_lock:
                        channel_badges = self._kick_sub_badges.get(slug, {})
                        available_months = sorted(channel_badges.keys())
                        selected_url = None
                        for m in available_months:
                            if count >= m:
                                selected_url = channel_badges[m]
                        if not selected_url and available_months:
                            selected_url = channel_badges[available_months[0]]

                        if selected_url:
                            local_url = get_emote_url(selected_url, f"kick_sub_{slug}_{count}")

                if local_url:
                    img_tag = f"<img src='{local_url}' width='18' height='18' style='vertical-align:middle;margin-left:3px;margin-right:1px;' title='Inscrito ({count} meses)'>"
                    self._badge_cache[cache_key] = img_tag
                    html_parts.append(img_tag)
                    continue

                # SVGs oficiais extraídos diretamente da Kick
                svg_file = svg_map.get(b_type)
                if svg_file:
                    svg_path = resource_path(f"assets/{svg_file}").replace('\\', '/')
                    img_tag = f"<img src='file:///{svg_path}' width='18' height='18' style='vertical-align:middle;margin-left:3px;margin-right:1px;' title='{b_type.title()}'>"
                    self._badge_cache[cache_key] = img_tag
                    html_parts.append(img_tag)

        # 2. Processa badges_v2 (níveis, kick_founder22, etc.)
        if badges_v2:
            for bv in badges_v2:
                img_url = bv.get("image_url")
                bname = bv.get("name", "badge")
                if img_url:
                    local_url = get_emote_url(img_url, f"kick_v2_{bname}_{abs(hash(img_url)) % 100000}")
                    if local_url:
                        html_parts.append(f"<img src='{local_url}' height='18' style='vertical-align:middle;margin-left:3px;margin-right:1px;'>")

        return " ".join(html_parts)

    # =========================================================================
    # 4. YOUTUBE BADGES
    # =========================================================================

    def get_youtube_badges_html(self, author_obj) -> str:
        """
        Retorna as badges do YouTube Live (Membro/Patrocinador com ícone original,
        Moderador com chave inglesa e Dono/Owner com coroa).
        """
        if not author_obj:
            return ""

        html_parts = []

        # 1. Selo de Membro do Canal (Custom Sponsor Badge)
        badge_url = getattr(author_obj, 'badgeUrl', '') or ''
        if badge_url and badge_url.startswith('http'):
            badge_id = re.sub(r'[^a-zA-Z0-9]', '', badge_url.split('/')[-1])[:24]
            local_url = get_emote_url(badge_url, f"yt_badge_{badge_id}")
            if local_url:
                img_tag = f"<img src='{local_url}' width='18' height='18' style='vertical-align:middle;margin-left:3px;margin-right:1px;' title='Membro do Canal'>"
                html_parts.append(img_tag)

        # 2. Moderador do YouTube (Chave inglesa)
        if getattr(author_obj, 'isChatModerator', False):
            svg_path = resource_path('assets/mod.svg').replace('\\', '/')
            img_tag = f"<img src='file:///{svg_path}' width='18' height='18' style='vertical-align:middle;margin-left:3px;margin-right:1px;' title='Moderador'>"
            html_parts.append(img_tag)

        # 3. Dono do Canal (Broadcaster/Owner)
        if getattr(author_obj, 'isChatOwner', False):
            svg_path = resource_path('assets/streamer.svg').replace('\\', '/')
            img_tag = f"<img src='file:///{svg_path}' width='18' height='18' style='vertical-align:middle;margin-left:3px;margin-right:1px;' title='Streamer'>"
            html_parts.append(img_tag)

        # 4. Verificado
        if getattr(author_obj, 'isVerified', False):
            svg_path = resource_path('assets/kick_verified.svg').replace('\\', '/')
            img_tag = f"<img src='file:///{svg_path}' width='18' height='18' style='vertical-align:middle;margin-left:3px;margin-right:1px;' title='Verificado'>"
            html_parts.append(img_tag)

        return " ".join(html_parts)


# Instância global reutilizável
badge_manager = BadgeManager()
