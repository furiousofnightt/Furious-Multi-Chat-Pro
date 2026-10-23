"""
Neural TTS Comprehensive Benchmark Suite (Microsoft Edge)
----------------------------------------------------------
Features two dedicated test modes:
  1. Sequential Mode (--sequential):
     Simulates realistic livestream chat pace (20 messages per voice at 2.0s intervals).
  2. Concurrent Burst Mode (--concurrent):
     Simulates extreme raid/hype peaks (20 parallel requests fired simultaneously per voice).

Usage:
    py test_voices.py --sequential   # Real-world chat simulation (2s delay)
    py test_voices.py --concurrent   # Extreme burst concurrency (20 in parallel)
    py test_voices.py --all          # Runs both benchmarks consecutively
    py test_voices.py                # Interactive selection menu
"""

import os
import sys
import time
import asyncio
import argparse
from datetime import datetime

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import edge_tts
from utils.edge_tts_compat import apply_edge_tts_compat

# Apply Edge TTS protocol compatibility patch
apply_edge_tts_compat()

# Output folder for generated test audio files
BASE_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audios_test_output")

# Target neural voices to test
VOICES_TO_TEST = [
    {
        "name": "Antonio",
        "voice_id": "pt-BR-AntonioNeural",
        "platform": "Twitch / YouTube",
        "folder": "01_Antonio"
    },
    {
        "name": "Francisca",
        "voice_id": "pt-BR-FranciscaNeural",
        "platform": "TikTok",
        "folder": "02_Francisca"
    },
    {
        "name": "Thalita",
        "voice_id": "pt-BR-ThalitaMultilingualNeural",
        "platform": "Kick",
        "folder": "03_Thalita"
    }
]

# 20 realistic livestream chat messages
MESSAGES_POOL = [
    "Boa noite streamer! Como foi seu dia hoje?",
    "Salve salve galera do chat, cheguei agora!",
    "Caramba, que jogada incrível que você acabou de fazer!",
    "Qual é o seu setup atual? O jogo está rodando muito liso.",
    "kkk essa foi muito engraçada, não esperava por essa reação.",
    "O áudio e o microfone estão com uma qualidade excelente hoje.",
    "Você vai jogar até que horas essa noite?",
    "GG demais essa partida, jogou com muita calma!",
    "Manda um abraço para a galera de São Paulo que está assistindo!",
    "Essa fase do jogo é bem difícil, cuidado com os inimigos na direita.",
    "Estou adorando a transmissão, você faz lives todos os dias?",
    "Parabéns pelo conteúdo, acompanho o canal sempre que posso.",
    "Alguém no chat sabe qual é a próxima meta do canal?",
    "O bot de voz está lendo as mensagens perfeitamente e sem atraso.",
    "Testando o tempo de resposta do servidor de síntese neural.",
    "Olha a jogada sensacional, mereceu muito essa vitória!",
    "Opa, mais um sub no canal, sejam todos muito bem-vindos!",
    "Muito boa a escolha dessa música de fundo para a gameplay.",
    "A qualidade dessa voz neural é impressionante e super natural.",
    "Vigésima mensagem concluída com sucesso no teste de estabilidade!"
]


async def synthesize_message(text: str, voice_id: str, output_path: str, timeout: float = 15.0):
    """Synthesizes a single message, saves to disk, and measures elapsed time and size."""
    t0 = time.time()
    try:
        comm = edge_tts.Communicate(text, voice_id)
        await asyncio.wait_for(comm.save(output_path), timeout=timeout)
        elapsed = time.time() - t0
        size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        if size == 0:
            return False, elapsed, 0, "Generated file is empty (0 bytes)"
        return True, elapsed, size, None
    except asyncio.TimeoutError:
        return False, time.time() - t0, 0, "Connection timeout (15s exceeded)"
    except Exception as e:
        return False, time.time() - t0, 0, str(e)


# ============================================================================
# BLOCK 1: SEQUENTIAL TEST (Realistic Livestream Chat Pace - 2.0s Intervals)
# ============================================================================

async def run_sequential_test():
    """Simulates active livestream chat pace (20 messages per voice at 2.0s intervals)."""
    output_dir = os.path.join(BASE_OUTPUT_DIR, "sequential")
    os.makedirs(output_dir, exist_ok=True)
    interval_seconds = 2.0

    print("=" * 80)
    print("🎙️ MODE 1: SEQUENTIAL STREAMING BENCHMARK (REALISTIC CHAT PACE)")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Voices: {len(VOICES_TO_TEST)} (Antonio, Francisca, Thalita)")
    print(f"Cadence: {len(MESSAGES_POOL)} messages per voice at {interval_seconds:.1f}s intervals")
    print(f"Total Requests: {len(VOICES_TO_TEST) * len(MESSAGES_POOL)}")
    print(f"Target Output Folder: {output_dir}")
    print("=" * 80)
    print()

    global_stats = {
        "total_requests": 0,
        "success_requests": 0,
        "failed_requests": 0,
        "total_bytes": 0,
        "voice_stats": {}
    }

    start_all = time.time()

    for v_idx, voice_cfg in enumerate(VOICES_TO_TEST, 1):
        v_name = voice_cfg["name"]
        v_id = voice_cfg["voice_id"]
        v_plat = voice_cfg["platform"]
        v_folder = os.path.join(output_dir, voice_cfg["folder"])
        os.makedirs(v_folder, exist_ok=True)

        print("-" * 80)
        print(f"🎙️  STARTING SEQUENTIAL BATCH [{v_idx}/{len(VOICES_TO_TEST)}]: Voice '{v_name}'")
        print(f"    Identifier: {v_id} | Default Platform: {v_plat}")
        print(f"    Target Folder: {v_folder}")
        print("-" * 80)

        voice_success = 0
        voice_fail = 0
        voice_times = []

        for m_idx, message in enumerate(MESSAGES_POOL, 1):
            filename = f"seq_{m_idx:02d}_{v_name.lower()}.mp3"
            filepath = os.path.join(v_folder, filename)

            ok, elapsed, size, error = await synthesize_message(message, v_id, filepath)
            global_stats["total_requests"] += 1

            now_str = datetime.now().strftime("%H:%M:%S")
            if ok:
                voice_success += 1
                global_stats["success_requests"] += 1
                global_stats["total_bytes"] += size
                voice_times.append(elapsed)
                kb_size = size / 1024
                print(f"[{now_str}] [OK] #{m_idx:02d}/20 | Voice: {v_name:<9} | {elapsed:.2f}s | {kb_size:5.1f} KB -> {filename}")
            else:
                voice_fail += 1
                global_stats["failed_requests"] += 1
                print(f"[{now_str}] [FAILED] #{m_idx:02d}/20 | Voice: {v_name:<9} | Error: {error}")

            is_last = (v_idx == len(VOICES_TO_TEST)) and (m_idx == len(MESSAGES_POOL))
            if not is_last:
                await asyncio.sleep(interval_seconds)

        avg_voice_time = (sum(voice_times) / len(voice_times)) if voice_times else 0.0
        global_stats["voice_stats"][v_name] = {
            "success": voice_success,
            "fail": voice_fail,
            "avg_time": avg_voice_time
        }

        print()
        print(f"✔️ Finished voice '{v_name}': {voice_success}/{len(MESSAGES_POOL)} OK (Avg Latency: {avg_voice_time:.2f}s/audio)")
        print()

    total_elapsed = time.time() - start_all
    total_mb = global_stats["total_bytes"] / (1024 * 1024)

    print("=" * 80)
    print("📊 SEQUENTIAL BENCHMARK REPORT")
    print("=" * 80)
    print(f"Total Time           : {total_elapsed:.1f}s (~{total_elapsed/60:.1f} min)")
    print(f"Total Requests       : {global_stats['total_requests']}")
    print(f"Success Rate         : {global_stats['success_requests']}/{global_stats['total_requests']} ({global_stats['success_requests']/global_stats['total_requests']*100:.1f}%)")
    print(f"Failures             : {global_stats['failed_requests']}")
    print(f"Audio Volume         : {total_mb:.2f} MB")
    print("Voice Breakdown:")
    for v_name, stats in global_stats["voice_stats"].items():
        rate = (stats["success"] / len(MESSAGES_POOL)) * 100
        print(f" - {v_name:<10}: {stats['success']:02d}/20 OK ({rate:5.1f}%) | Avg Latency: {stats['avg_time']:.2f}s")
    print(f"\n📁 Files saved in: {output_dir}")
    print("=" * 80)
    print()


# ============================================================================
# BLOCK 2: CONCURRENT BURST TEST (Extreme Raid/Hype Peak - 20 In Parallel)
# ============================================================================

async def _run_single_concurrent_task(m_idx: int, message: str, voice_name: str, voice_id: str, filepath: str):
    """Executes single task within concurrent batch and logs immediately upon completion."""
    ok, elapsed, size, error = await synthesize_message(message, voice_id, filepath)
    filename = os.path.basename(filepath)
    now_str = datetime.now().strftime("%H:%M:%S")

    if ok:
        kb_size = size / 1024
        print(f"[{now_str}] [OK] #{m_idx:02d}/20 CONCURRENT | Voice: {voice_name:<9} | {elapsed:.2f}s | {kb_size:5.1f} KB -> {filename}")
    else:
        print(f"[{now_str}] [FAILED] #{m_idx:02d}/20 CONCURRENT | Voice: {voice_name:<9} | {elapsed:.2f}s | ERROR: {error}")

    return {
        "m_idx": m_idx,
        "ok": ok,
        "elapsed": elapsed,
        "size": size,
        "error": error
    }


async def run_concurrent_test():
    """Simulates extreme burst traffic: fires 20 simultaneous WebSocket requests per voice."""
    output_dir = os.path.join(BASE_OUTPUT_DIR, "concurrent")
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 80)
    print("🔥 MODE 2: EXTREME BURST CONCURRENCY BENCHMARK (20 IN PARALLEL)")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Goal: Tests server resilience under immediate 20-connection bursts (zero delay)")
    print(f"Voices: {len(VOICES_TO_TEST)} (Antonio, Francisca, Thalita)")
    print(f"Requests per Batch: 20 simultaneous WebSocket connections")
    print(f"Target Output Folder: {output_dir}")
    print("=" * 80)
    print()

    global_stats = {
        "total_requests": 0,
        "success_requests": 0,
        "failed_requests": 0,
        "total_bytes": 0,
        "voice_stats": {}
    }

    start_all = time.time()

    for v_idx, voice_cfg in enumerate(VOICES_TO_TEST, 1):
        v_name = voice_cfg["name"]
        v_id = voice_cfg["voice_id"]
        v_plat = voice_cfg["platform"]
        v_folder = os.path.join(output_dir, voice_cfg["folder"])
        os.makedirs(v_folder, exist_ok=True)

        print("-" * 80)
        print(f"⚡ BATCH [{v_idx}/{len(VOICES_TO_TEST)}]: Voice '{v_name}' ({v_id})")
        print(f"   DISPATCHING ALL 20 REQUESTS SIMULTANEOUSLY RIGHT NOW...")
        print("-" * 80)

        tasks = []
        for m_idx, message in enumerate(MESSAGES_POOL, 1):
            filename = f"burst_{m_idx:02d}_{v_name.lower()}.mp3"
            filepath = os.path.join(v_folder, filename)
            tasks.append(_run_single_concurrent_task(m_idx, message, v_name, v_id, filepath))

        batch_t0 = time.time()
        results = await asyncio.gather(*tasks)
        batch_elapsed = time.time() - batch_t0

        voice_success = sum(1 for r in results if r["ok"])
        voice_fail = sum(1 for r in results if not r["ok"])
        voice_bytes = sum(r["size"] for r in results if r["ok"])
        voice_times = [r["elapsed"] for r in results if r["ok"]]
        avg_time = (sum(voice_times) / len(voice_times)) if voice_times else 0.0

        global_stats["total_requests"] += len(results)
        global_stats["success_requests"] += voice_success
        global_stats["failed_requests"] += voice_fail
        global_stats["total_bytes"] += voice_bytes
        global_stats["voice_stats"][v_name] = {
            "success": voice_success,
            "fail": voice_fail,
            "batch_time": batch_elapsed,
            "avg_time": avg_time,
            "errors": [r["error"] for r in results if not r["ok"]]
        }

        print()
        print(f"⏱️  Batch '{v_name}' finished in {batch_elapsed:.2f}s total!")
        print(f"    Result: {voice_success}/20 OK ({voice_success/20*100:.1f}%) | Failures: {voice_fail}")
        print()

        if v_idx < len(VOICES_TO_TEST):
            print("⏳ Pausing 3s before next voice batch...\n")
            await asyncio.sleep(3.0)

    total_elapsed = time.time() - start_all
    total_mb = global_stats["total_bytes"] / (1024 * 1024)

    print("=" * 80)
    print("📊 CONCURRENT BURST BENCHMARK REPORT")
    print("=" * 80)
    print(f"Total Execution Time : {total_elapsed:.2f}s")
    print(f"Total Requests       : {global_stats['total_requests']}")
    print(f"Success Rate         : {global_stats['success_requests']}/{global_stats['total_requests']} ({global_stats['success_requests']/global_stats['total_requests']*100:.1f}%)")
    print(f"Failures             : {global_stats['failed_requests']}")
    print(f"Audio Volume         : {total_mb:.2f} MB")
    print("Performance Breakdown by Voice:")
    for v_name, stats in global_stats["voice_stats"].items():
        rate = (stats["success"] / 20) * 100
        print(f" - {v_name:<10}: {stats['success']:02d}/20 OK ({rate:5.1f}%) | Batch Time: {stats['batch_time']:.2f}s | Avg Latency: {stats['avg_time']:.2f}s")
        if stats["errors"]:
            print(f"   ⚠️ Errors: {set(stats['errors'])}")
    print(f"\n📁 Files saved in: {output_dir}")
    print("=" * 80)


# ============================================================================
# CLI DISPATCHER
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Neural TTS Benchmark Suite (Microsoft Edge)")
    parser.add_argument("--sequential", "-s", action="store_true", help="Run sequential test (20 msgs @ 2s interval per voice)")
    parser.add_argument("--concurrent", "-c", action="store_true", help="Run concurrent burst test (20 simultaneous requests per voice)")
    parser.add_argument("--all", "-a", action="store_true", help="Run both sequential and concurrent benchmarks")

    args = parser.parse_args()

    mode = None
    if args.all:
        mode = "all"
    elif args.sequential:
        mode = "sequential"
    elif args.concurrent:
        mode = "concurrent"
    else:
        print("=" * 60)
        print("🚀 Neural TTS Benchmark Suite")
        print("=" * 60)
        print("Select benchmark mode:")
        print(" [1] Sequential Mode (Real-world Chat: 20 msgs @ 2s delay)")
        print(" [2] Concurrent Burst Mode (Extreme: 20 simultaneous msgs)")
        print(" [3] Run Both Benchmarks")
        print("=" * 60)
        try:
            choice = input("Enter option [1/2/3] (default: 2): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return

        if choice == "1":
            mode = "sequential"
        elif choice == "3":
            mode = "all"
        else:
            mode = "concurrent"

    if mode == "sequential":
        asyncio.run(run_sequential_test())
    elif mode == "concurrent":
        asyncio.run(run_concurrent_test())
    elif mode == "all":
        asyncio.run(run_sequential_test())
        print("\nPausing 5 seconds before launching Concurrent Burst test...\n")
        time.sleep(5)
        asyncio.run(run_concurrent_test())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Benchmark halted by user.")
