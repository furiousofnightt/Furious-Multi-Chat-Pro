"""
Módulo de Compatibilidade do Edge TTS (Furious Multi Chat Pro)
--------------------------------------------------------------
Objetivo:
    Garante a resiliência e compatibilidade das conexões do Microsoft Edge TTS
    mesmo diante de atualizações de endpoints ou protocolos da Microsoft.

Histórico:
    - Outubro/2026: A Microsoft depreciou o host legado 'speech.platform.bing.com'
      rejeitando o WebSocket com HTTP 403 (WSServerHandshakeError).
    - O Microsoft Edge 155+ migrou o Read Aloud para 'api.msedgeservices.com'.
    - Este módulo aplica a correção de forma graciosa e reversível.
"""

import sys
import logging

logger = logging.getLogger("EdgeTTSCompat")


def apply_edge_tts_compat():
    """
    Aplica patch seguro e idempotente nas constantes do edge_tts.
    Se versões futuras do edge-tts já apontarem para o endpoint novo,
    o patch não sobrescreve desnecessariamente.
    """
    try:
        import edge_tts
        import edge_tts.constants
        import edge_tts.communicate

        current_url = getattr(edge_tts.constants, "WSS_URL", "")
        trusted_token = getattr(edge_tts.constants, "TRUSTED_CLIENT_TOKEN", "6A5AA1D4EAFF4E9FB37E23D68491D6F4")

        # Se o endpoint ainda estiver apontando para o servidor legado com 403:
        if "speech.platform.bing.com" in current_url or "api.msedgeservices.com" not in current_url:
            new_url = (
                "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
                f"?Ocp-Apim-Subscription-Key={trusted_token}"
            )
            edge_tts.constants.WSS_URL = new_url
            edge_tts.communicate.WSS_URL = new_url

        return True
    except ImportError:
        return False
    except Exception as e:
        logger.warning(f"Não foi possível aplicar patch de compatibilidade do edge-tts: {e}")
        return False


async def test_voices_health(voices=None):
    """
    Testa a síntese das vozes do Edge TTS para diagnóstico de conectividade.
    Retorna uma tupla (sucesso: bool, resultados: dict).
    """
    import os
    import tempfile
    import edge_tts

    apply_edge_tts_compat()

    if voices is None:
        voices = [
            ("Antônio", "pt-BR-AntonioNeural"),
            ("Francisca", "pt-BR-FranciscaNeural"),
            ("Thalita", "pt-BR-ThalitaMultilingualNeural")
        ]

    results = {}
    all_ok = True

    for name, voice_id in voices:
        temp_file = None
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_path = temp_file.name
            temp_file.close()

            comm = edge_tts.Communicate("Teste de diagnóstico.", voice_id)
            await comm.save(temp_path)

            size = os.path.getsize(temp_path)
            if size > 0:
                results[name] = {"ok": True, "size": size, "voice": voice_id}
            else:
                results[name] = {"ok": False, "error": "Arquivo vazio", "voice": voice_id}
                all_ok = False

            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            results[name] = {"ok": False, "error": str(e), "voice": voice_id}
            all_ok = False
            if temp_file and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    return all_ok, results


if __name__ == "__main__":
    import asyncio
    print("Iniciando teste de conectividade das vozes neurais...")
    success, res = asyncio.run(test_voices_health())
    for name, data in res.items():
        status = "[OK]" if data["ok"] else "[FALHA]"
        print(f" {status} {name} ({data['voice']}): {data.get('size', data.get('error'))}")
    print("\nResultado geral:", "Todas as vozes 100% operacionais!" if success else "Houve falha em alguma voz.")
