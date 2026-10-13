import pytchat
from .base_handler import BaseChatHandler
import threading
import time
import re
import httpx
import collections
import urllib.request
from utils.emoticons import get_emote_url


class YoutubeHandler(BaseChatHandler):
    def __init__(self, username):
        super().__init__(username)
        self.platform = "youtube"
        self.chat = None
        # Camada 2: LRU Set para dedup de mensagens (máximo 500 IDs)
        self.seen_message_ids = collections.deque(maxlen=500)

    def start(self):
        if not self.username:
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._run_listener, daemon=True)
        self.thread.start()

    def _resolve_video_id(self, input_value):
        """
        Tenta extrair o video_id de uma live ativa do YouTube a partir de:
        - URL direta      → extrai o v=... ou youtu.be/...
        - @username       → busca /@username/live
        - username        → busca /@username/live
        Retorna o video_id se encontrado, ou None se não encontrar live ativa.

        NOTA: Strings de 11 chars NÃO são tratadas diretamente como video_id,
        pois nomes de canal também podem ter 11 chars (ex: PUBGEsports).
        O fallback para video_id direto só ocorre se a busca de canal falhar.
        """
        raw = input_value.strip()

        # Caso 1: URL direta com v= ou youtu.be → extrai video_id sem busca
        if "youtube.com/watch?v=" in raw:
            return raw.split("v=")[1].split("&")[0]
        if "youtu.be/" in raw:
            return raw.split("youtu.be/")[1].split("?")[0]

        # Caso 2: username ou @username → busca a live ativa no canal
        if raw.startswith('@'):
            url = f"https://www.youtube.com/{raw}/live"
        else:
            url = f"https://www.youtube.com/@{raw}/live"

        try:
            print(f"[YouTube] Buscando live em: {url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            }
            with httpx.Client(follow_redirects=True, timeout=15, headers=headers) as client:
                r = client.get(url)
                # O YouTube entrega o videoId no JSON embutido da página
                # Usamos o padrão mais confiável: "videoId":"XXXXXXXXXXX"
                matches = re.findall(r'"videoId"\s*:\s*"([A-Za-z0-9_\-]{11})"', r.text)
                if matches:
                    video_id = matches[0]
                    print(f"[YouTube] Live encontrada: video_id={video_id}")
                    return video_id
                else:
                    print(f"[YouTube] Nenhuma live ativa encontrada para '{raw}'")
        except Exception as e:
            print(f"[YouTube] Erro ao buscar live: {e}")

        # Caso 3 (fallback): se o valor tem exatamente 11 chars alfanuméricos,
        # pode ser um video_id direto (ex: link copiado sem o domínio)
        if re.fullmatch(r'[A-Za-z0-9_\-]{11}', raw):
            print(f"[YouTube] Tentando usar '{raw}' diretamente como video_id (fallback)")
            return raw

        return None

    def _run_listener(self):
        retry_count = 0

        while self.is_running:
            try:
                # Notifica o usuário que está tentando conectar
                self.message_received.emit(
                    "Sistema (YouTube)",
                    f"🔴 Tentando conectar ao YouTube: {self.username}...",
                    "system"
                )

                video_id = self._resolve_video_id(self.username)

                if not video_id:
                    self.status_changed.emit(False)
                    self.message_received.emit(
                        "Sistema (YouTube)",
                        f"⚠️ YouTube: Canal '{self.username}' não encontrado ou sem live ativa.",
                        "system"
                    )
                    # Espera antes de tentar de novo
                    for _ in range(30):
                        if not self.is_running:
                            break
                        time.sleep(1)
                    continue

                print(f"[YouTube] Conectando ao video_id: {video_id}")

                self.chat = pytchat.create(
                    video_id=video_id,
                    interruptable=False
                )

                if not self.chat.is_alive():
                    self.status_changed.emit(False)
                    self.message_received.emit(
                        "Sistema (YouTube)",
                        f"⚠️ YouTube: Live do canal '{self.username}' não está mais ativa.",
                        "system"
                    )
                    for _ in range(30):
                        if not self.is_running:
                            break
                        time.sleep(1)
                    continue

                # 🔥 FASE 1 — SYNC (Camada 1: Seed e descarte do backlog)
                # Marcamos o timestamp do momento de conexão
                sync_start_ms = int(time.time() * 1000)

                # Descartamos silenciosamente o primeiro batch (histórico/backlog)
                try:
                    initial_data = self.chat.get()
                    for c in initial_data.items:
                        self.seen_message_ids.append(c.id)
                    print(f"[YouTube] Backlog descartado: {len(initial_data.items)} msgs")
                except Exception:
                    pass

                # Conectado! Atualiza status
                retry_count = 0
                self.status_changed.emit(True)
                self.message_received.emit(
                    "Sistema (YouTube)",
                    f"✅ Conectado ao chat do YouTube: {self.username}",
                    "system"
                )
                
                last_viewers_update = 0

                # 🔥 FASE 2 — TEMPO REAL (Camadas 2 e 3)
                while self.chat.is_alive() and self.is_running:
                    data = self.chat.get()

                    for c in data.items:
                        # Camada 2: Dedup por ID
                        if c.id in self.seen_message_ids:
                            continue

                        # Camada 3: Filtro de timestamp — só passa o que chegou após a conexão
                        if c.timestamp < sync_start_ms:
                            self.seen_message_ids.append(c.id)
                            continue

                        self.seen_message_ids.append(c.id)

                        # Constrói a mensagem com suporte total a emojis do YouTube
                        # messageEx é uma lista de segmentos: str (texto) ou dict (emoji)
                        try:
                            msg_parts = []
                            for seg in c.messageEx:
                                if isinstance(seg, str):
                                    msg_parts.append(seg)
                                elif isinstance(seg, dict):
                                    url = seg.get('url', '')
                                    if url:
                                        # Emojis com URL relativa (começa com //)
                                        if url.startswith('//'):
                                            url = 'https:' + url
                                        
                                        # Baixa o emote para o disco temporário e pega o caminho file:///
                                        # Usamos um ID gerado a partir do nome do emoji ou um hash da URL
                                        emote_id = seg.get('id', url.split('/')[-1].split('.')[0][:10])
                                        local_url = get_emote_url(url, f"yt_{emote_id}")
                                        
                                        if local_url:
                                            msg_parts.append(
                                                f"<img src='{local_url}' width='22' height='22' "
                                                f"style='vertical-align: middle; margin: 0 1px;'>"
                                            )
                                        else:
                                            msg_parts.append(seg.get('txt', ''))
                                    else:
                                        # Fallback: usa o texto curto do emoji (:shortcut:)
                                        msg_parts.append(seg.get('txt', ''))
                            msg = ''.join(msg_parts) if msg_parts else c.message
                        except Exception:
                            msg = c.message

                        # Remove o @ do handle do YouTube (ex: @Farax2 → Farax2)
                        author_name = c.author.name
                        if author_name and author_name[0] == '@':
                            author_name = author_name[1:]

                        # Processar badges do YouTube (Membro do Canal, Moderador, Dono)
                        badge_str = ''
                        try:
                            from utils.badge_manager import badge_manager
                            badge_str = badge_manager.get_youtube_badges_html(c.author)
                        except Exception:
                            pass

                        author_display = f"{badge_str} {author_name}".strip() if badge_str else author_name
                        self.message_received.emit(author_display, msg, "youtube")

                    # Atualiza os viewers a cada 15 segundos
                    current_time = time.time()
                    if current_time - last_viewers_update > 15:
                        last_viewers_update = current_time
                        try:
                            # Fazemos o scraping leve e rápido da própria página do vídeo
                            req = urllib.request.Request(
                                f"https://www.youtube.com/watch?v={video_id}", 
                                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                            )
                            with urllib.request.urlopen(req, timeout=5) as response:
                                html = response.read().decode('utf-8', errors='ignore')
                                
                                vc_str = None
                                # Formato 1: runs text
                                m1 = re.search(r'"viewCount":\{"runs":\[\{"text":"([\d,]+)', html)
                                if m1:
                                    vc_str = m1.group(1)
                                else:
                                    # Formato 2: videoViewCountRenderer simpleText
                                    m2 = re.search(r'"videoViewCountRenderer":\{"viewCount":\{"simpleText":"([\d,]+)', html)
                                    if m2:
                                        vc_str = m2.group(1)
                                    else:
                                        # Formato 3: concurrentViewers (raro mas possivel)
                                        m3 = re.search(r'"concurrentViewers":\{"simpleText":"([\d,]+)', html)
                                        if m3:
                                            vc_str = m3.group(1)
                                
                                if vc_str:
                                    vc = vc_str.replace(',', '').replace('.', '')
                                    if vc.isdigit():
                                        # Emite (viewers, uptime_seconds, likes, total_views)
                                        self.stats_updated.emit(int(vc), 0, 0, 0)
                        except Exception as e:
                            print(f"[YouTube] Erro ao buscar viewers: {e}")
                            pass

                    time.sleep(0.5)

            except Exception as e:
                if self.is_running:
                    self.status_changed.emit(False)
                    self.message_received.emit(
                        "Sistema (YouTube)",
                        f"❌ YouTube desconectado: {str(e)}. Reconectando em 15s...",
                        "system"
                    )
                    print(f"[YouTube] Exceção: {e}")

            finally:
                if self.chat:
                    try:
                        self.chat.terminate()
                    except Exception:
                        pass
                self.chat = None
                if self.is_running:
                    self.status_changed.emit(False)

            # 🔥 RECONEXÃO CONTROLADA com backoff leve
            if self.is_running:
                retry_count += 1
                delay = min(15 * retry_count, 60)  # máximo 60s entre tentativas
                print(f"[YouTube] Aguardando {delay}s antes de reconectar (tentativa {retry_count})")
                for _ in range(delay):
                    if not self.is_running:
                        break
                    time.sleep(1)

    def stop(self):
        super().stop()
        if self.chat:
            try:
                self.chat.terminate()
            except Exception:
                pass