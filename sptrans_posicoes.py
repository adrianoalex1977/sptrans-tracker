import os
import requests
import json
import datetime
import sys
import traceback

# Garante que as pastas existam
OUT_DIR = os.path.join("dados", "posicoes")
os.makedirs(OUT_DIR, exist_ok=True)

# Lê token do ambiente
API_KEY = os.getenv("SPTRANS_TOKEN")

BASE_URL = "https://api.olhovivo.sptrans.com.br/v2.1"
session = requests.Session()

def autenticar_api():
    if not API_KEY:
        print("❌ SPTRANS_API_KEY não encontrado no ambiente.")
        return False
    AUTH_URL = f"{BASE_URL}/Login/Autenticar?token={API_KEY}"
    try:
        r = session.post(AUTH_URL, timeout=15)
        print(f"Autenticação: status {r.status_code}")
        print("Resposta (curta):", (r.text or "")[:200])
        return r.status_code == 200 and r.text.strip().lower() == 'true'
    except Exception as e:
        print("Erro na autenticação:", e)
        return False

def solicitar_posicoes():
    try:
        POS_URL = f"{BASE_URL}/Posicao"
        r = session.get(POS_URL, timeout=20)
        print(f"GET {POS_URL} -> {r.status_code}")
        if r.status_code != 200:
            print("Resposta da API:", r.text[:500])
            return None
        return r.json()
    except Exception as e:
        print("Erro ao solicitar posicoes:", e)
        return None

def salvar_json(dados):
    try:
        # nome baseado em ta/hr quando possível
        nome_arquivo = None
        if isinstance(dados, dict):
            linhas = dados.get('l', [])
            if linhas and isinstance(linhas, list) and len(linhas) > 0:
                primeira = linhas[0]
                if isinstance(primeira, dict):
                    vs = primeira.get('vs', [])
                    if vs and isinstance(vs, list) and len(vs) > 0:
                        ta = vs[0].get('ta')
                        if ta:
                            nome_base = ta.replace('T', '_').replace(':', '-').replace('Z', '')
                            nome_arquivo = f"posicao_veiculos_{nome_base}.json"
            if not nome_arquivo and dados.get('hr'):
                nome_base = dados['hr'].replace(':', '-')
                nome_arquivo = f"posicao_veiculos_hr_{nome_base}.json"

        if not nome_arquivo:
            nome_base = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"posicao_veiculos_sem_ts_{nome_base}.json"

        caminho = os.path.join(OUT_DIR, nome_arquivo)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(f"💾 Arquivo salvo: {os.path.abspath(caminho)}")
        return caminho
    except Exception:
        print("Erro ao salvar JSON:")
        traceback.print_exc()
        return None

def listar_arquivos():
    print("=== CWD ===")
    print(os.path.abspath(os.getcwd()))
    print("=== Conteúdo raiz ===")
    for root, dirs, files in os.walk(".", topdown=True):
        # limita profundidade para não poluir muito
        depth = root.count(os.sep)
        prefix = "  " * depth
        print(f"{prefix}{os.path.basename(root)}/ (files: {len(files)})")
        if depth >= 3:
            continue

if __name__ == "__main__":
    print("Iniciando script de coleta SPTrans (debug).")
    listar_arquivos()
    print(f"Verificando OUT_DIR: {OUT_DIR} (existe? {os.path.exists(OUT_DIR)})")
    print("SPTRANS_API_KEY presente?", bool(API_KEY))
    if not autenticar_api():
        print("❌ Autenticação falhou. Abortando.")
        sys.exit(1)

    dados = solicitar_posicoes()
    if not dados:
        print("❌ Não obteve dados de posição. Abortando.")
        sys.exit(2)

    caminho = salvar_json(dados)
    if not caminho:
        print("❌ Falha ao salvar JSON.")
        sys.exit(3)

    print("=== Após salvar, listando dados/posicoes ===")
    try:
        for fn in sorted(os.listdir(OUT_DIR)):
            print(" -", fn)
    except Exception as e:
        print("Erro listando OUT_DIR:", e)

    print("Script finalizado com sucesso.")

