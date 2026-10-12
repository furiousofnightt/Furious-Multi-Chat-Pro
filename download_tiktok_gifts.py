import os
import re
import json
import asyncio
import sys
import httpx

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from PyQt6.QtGui import QImage
from TikTokLive import TikTokLiveClient

def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos para nomes de arquivos no Windows."""
    clean = re.sub(r'[\\/*?:"<>|]', '', name).strip()
    return clean if clean else "unnamed_gift"

async def download_single_gift(client_http: httpx.AsyncClient, semaphore: asyncio.Semaphore, gift: dict, output_dirs: dict, stats: dict):
    gid = gift.get("id")
    raw_name = gift.get("name") or f"gift_{gid}"
    safe_name = sanitize_filename(raw_name)
    diamonds = gift.get("diamond_count", 0)

    # Obter melhor URL de imagem disponível
    img_obj = gift.get("image") or {}
    icon_obj = gift.get("icon") or {}
    
    img_urls = img_obj.get("url_list") or img_obj.get("urls_list") or img_obj.get("m_urls") or []
    icon_urls = icon_obj.get("url_list") or icon_obj.get("urls_list") or icon_obj.get("m_urls") or []
    
    url = None
    if img_urls:
        url = img_urls[0]
    elif icon_urls:
        url = icon_urls[0]
    elif gift.get("icon_url"):
        url = gift.get("icon_url")
    elif gift.get("cover_url"):
        url = gift.get("cover_url")

    if not url:
        stats["skipped"] += 1
        return None

    filename_base = f"{gid}_{safe_name}"
    webp_path = os.path.join(output_dirs["webp"], f"{filename_base}.webp")
    png_path = os.path.join(output_dirs["png"], f"{filename_base}.png")
    name_png_path = os.path.join(output_dirs["by_name"], f"{safe_name}.png")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/"
    }

    async with semaphore:
        for attempt in range(3):
            try:
                resp = await client_http.get(url, headers=headers, timeout=10.0)
                if resp.status_code == 200 and resp.content:
                    # 1. Salvar WebP original
                    with open(webp_path, "wb") as f:
                        f.write(resp.content)

                    # 2. Converter e salvar em PNG (alta compatibilidade com transparência)
                    qimg = QImage.fromData(resp.content)
                    if not qimg.isNull():
                        qimg.save(png_path, "PNG")
                        # Salvar cópia em by_name se ainda não existir para esse nome
                        if not os.path.exists(name_png_path):
                            qimg.save(name_png_path, "PNG")
                    else:
                        with open(png_path, "wb") as f:
                            f.write(resp.content)

                    stats["downloaded"] += 1
                    return {
                        "id": gid,
                        "name": raw_name,
                        "safe_name": safe_name,
                        "diamond_count": diamonds,
                        "url": url,
                        "png_file": f"png/{filename_base}.png",
                        "webp_file": f"webp/{filename_base}.webp",
                        "by_name_file": f"by_name/{safe_name}.png" if os.path.exists(name_png_path) else None
                    }
            except Exception as e:
                if attempt == 2:
                    print(f"❌ Falha ao baixar presente [{gid}] {raw_name}: {e}")
                    stats["failed"] += 1
                await asyncio.sleep(1)

    return None

async def main():
    print("==================================================")
    print("🎁 DOWNLOADER DE TODOS OS PRESENTES DO TIKTOK 🎁")
    print("==================================================")

    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tiktok_gifts")
    output_dirs = {
        "base": base_dir,
        "png": os.path.join(base_dir, "png"),
        "webp": os.path.join(base_dir, "webp"),
        "by_name": os.path.join(base_dir, "by_name"),
    }

    for p in output_dirs.values():
        os.makedirs(p, exist_ok=True)

    print("📡 Conectando à API do TikTok para obter lista completa de presentes...")
    client = TikTokLiveClient(unique_id="tiktok")
    data = await client.web.fetch_gift_list()
    gifts = data.get("gifts", data) if isinstance(data, dict) else (data or [])

    if not gifts:
        print("❌ Nenhum presente retornado pela API do TikTok.")
        return

    total = len(gifts)
    print(f"📦 Total de presentes encontrados: {total}")
    print(f"📂 Diretório de saída: {base_dir}")
    print("⏳ Iniciando download concorrente...")

    stats = {"downloaded": 0, "failed": 0, "skipped": 0}
    semaphore = asyncio.Semaphore(15)  # 15 downloads simultâneos

    async with httpx.AsyncClient(timeout=15.0) as client_http:
        tasks = [
            download_single_gift(client_http, semaphore, gift, output_dirs, stats)
            for gift in gifts
        ]
        results = await asyncio.gather(*tasks)

    valid_results = [r for r in results if r is not None]

    # Ordenar por ID ou quantidade de diamantes
    valid_results.sort(key=lambda x: (x["diamond_count"], x["id"]))

    # Salvar índice JSON
    json_path = os.path.join(base_dir, "gifts_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(valid_results, f, ensure_ascii=False, indent=2)

    # Criar um README explicativo na pasta
    readme_path = os.path.join(base_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"""# Ícones de Presentes do TikTok (TikTok Gifts Icons)

Esta pasta contém o catálogo completo dos presentes oficiais do TikTok baixados diretamente do CDN do TikTok.

- **Total de presentes baixados:** {len(valid_results)}
- **Atualizado em:** Lista oficial obtida via TikTokLive Webcast API

## Estrutura de Pastas

- `png/`: Ícones em formato **PNG** transparente de alta qualidade (ex: `5655_Rosa.png`), nomeados no padrão `{{ID}}_{{NOME}}.png`.
- `webp/`: Ícones no formato original **WebP** do TikTok (ex: `5655_Rosa.webp`).
- `by_name/`: Ícones em PNG nomeados diretamente pelo nome do presente (ex: `Rosa.png`), ideal para lookup direto por nome de evento.
- `gifts_data.json`: Arquivo JSON contendo todos os dados detalhados de cada presente (ID, nome, quantidade de diamantes, URLs de imagem e caminhos de arquivo locais).

## Exemplo de uso em outro projeto (Python)

```python
import json

with open("tiktok_gifts/gifts_data.json", "r", encoding="utf-8") as f:
    gifts = json.load(f)

# Buscar por nome
def get_gift_icon_by_name(name):
    for g in gifts:
        if g["name"].lower() == name.lower():
            return g["png_file"]
    return None
```
""")

    print("==================================================")
    print(f"✅ Concluído com sucesso!")
    print(f"🎉 Baixados: {stats['downloaded']}/{total}")
    print(f"⚠️ Falhas: {stats['failed']}")
    print(f"📁 Pasta dos ícones: {base_dir}")
    print(f"📄 Metadados salvos em: {json_path}")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
