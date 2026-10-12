"""
Script rápido para testar a saúde das vozes do TTS (Microsoft Edge e Google TTS)
Uso:
    py test_voices.py
"""

import sys
import asyncio

# Garante suporte a UTF-8 no terminal Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from utils.edge_tts_compat import test_voices_health

if __name__ == "__main__":
    print("=" * 55)
    print("🔍 Diagnosticando vozes do Furious Multi Chat Pro...")
    print("=" * 55)
    all_ok, results = asyncio.run(test_voices_health())

    for name, info in results.items():
        if info["ok"]:
            print(f" [OK] {name:<12} ({info['voice']}): gerou áudio com {info['size']} bytes")
        else:
            print(f" [ERRO] {name:<10} ({info['voice']}): {info['error']}")

    print("=" * 55)
    if all_ok:
        print("✅ TODAS AS VOZES NEURAIS ESTÃO 100% OPERACIONAIS!")
    else:
        print("⚠️ Atenção: Uma ou mais vozes falharam. Verifique a conexão com a internet.")
    print("=" * 55)
