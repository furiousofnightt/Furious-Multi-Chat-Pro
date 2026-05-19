import sys
import os

# Adiciona o diretório atual ao sys.path para garantir que os módulos locais sejam encontrados
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from main import main
    print("🚀 Iniciando Furious Multi Chat Pro...")
    main()
except ImportError as e:
    print(f"❌ Erro de Importação: {e}")
    print("Certifique-se de que instalou as dependências: pip install -r requirements.txt")
except Exception as e:
    print(f"💥 Ocorreu um erro inesperado: {e}")
