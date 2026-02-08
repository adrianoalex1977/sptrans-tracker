import os
import sys
import json
import time
import random
import logging
import requests
from datetime import datetime
from pathlib import Path

# ================== CONFIG ==================

TOKEN = os.getenv("SPTRANS_TOKEN")

BASE_URL = "https://api.olhovivo.sptrans.com.br/v2.1"

ROOT = Path(__file__).parent.resolve()
DADOS_DIR = ROOT / "Dados"

TIMEOUT = 30
SLEEP_CALLS = 0.3
INTERVALO_MIN = 40
INTERVALO_MAX = 70

# ============================================

session = requests.Session()

# ---------------- LOGGING -------------------

LOG_DIR = DADOS_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "coletor.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

def log(msg):
    print(msg)
    logging.info(msg)

# -------------- ESTRUTURA -------------------

PASTAS = [
    "raw/linhas",
    "raw/paradas",
    "raw/corredores",
    "raw/empresas",
    "raw/posicao_global",
    "raw/posicao_linha",
    "raw/posicao_garagem",
    "raw/previsao",
    "raw/kmz",
    "curated"
]

def criar_pastas():
    for p in PASTAS:
        (DADOS_DIR / p).mkdir(parents=True, exist_ok=True)

# -------------- UTIL ------------------------

def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def salvar_json(diretorio, nome, dados):
    arquivo = diretorio / f"{nome}_{timestamp()}.json"
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False)
    return arquivo

# -------------- API -------------------------

def autenticar():
    url = f"{BASE_URL}/Login/Autenticar"
    r = session.post(url, params={"token": TOKEN}, timeout=TIMEOUT)
    return r.status_code == 200 and r.text.strip().lower() == "true"

def get(endpoint, params=None):
    url = f"{BASE_URL}{endpoint}"
    r = session.get(url, params=params, timeout=TIMEOUT)
    if r.status_code != 200:
        raise Exception(f"{r.status_code} - {r.text[:200]}")
    return r.json()

# ------------- COLETORES --------------------

def coletar_linhas():
    log("📥 Coletando linhas")
    return get("/Linha/Buscar", {"termosBusca": ""})

def coletar_corredores():
    log("📥 Coletando corredores")
    return get("/Corredor")

def coletar_empresas():
    log("📥 Coletando empresas")
    return get("/Empresa")

def coletar_paradas(linhas, corredores):
    log("📥 Coletando paradas")
    todas = []

    for l in linhas:
        try:
            todas.extend(get("/Parada/BuscarParadasPorLinha", {"codigoLinha": l["cl"]}))
            time.sleep(SLEEP_CALLS)
        except Exception as e:
            log(f"⚠ Linha {l['cl']} → {e}")

    for c in corredores:
        try:
            todas.extend(get("/Parada/BuscarParadasPorCorredor", {"codigoCorredor": c["cc"]}))
            time.sleep(SLEEP_CALLS)
        except Exception as e:
            log(f"⚠ Corredor {c['cc']} → {e}")

    salvar_json(DADOS_DIR / "raw/paradas", "paradas", todas)

def posicao_global():
    log("📡 Tentando posição global")
    try:
        salvar_json(DADOS_DIR / "raw/posicao_global", "posicao", get("/Posicao"))
        return True
    except:
        return False

def posicao_fallback(linhas, empresas):
    log("🔁 Fallback de posição")

    for l in linhas:
        try:
            salvar_json(
                DADOS_DIR / "raw/posicao_linha",
                f"linha_{l['cl']}",
                get("/Posicao/Linha", {"codigoLinha": l["cl"]})
            )
            time.sleep(SLEEP_CALLS)
        except:
            pass

    for e in empresas:
        try:
            salvar_json(
                DADOS_DIR / "raw/posicao_garagem",
                f"empresa_{e['c']}",
                get("/Posicao/Garagem", {"codigoEmpresa": e["c"]})
            )
            time.sleep(SLEEP_CALLS)
        except:
            pass

def coletar_kmz():
    endpoints = [
        "/KMZ", "/KMZ/BC", "/KMZ/CB",
        "/KMZ/Corredor", "/KMZ/Corredor/BC", "/KMZ/Corredor/CB",
        "/KMZ/OutrasVias", "/KMZ/OutrasVias/BC", "/KMZ/OutrasVias/CB"
    ]

    for ep in endpoints:
        try:
            r = session.get(f"{BASE_URL}{ep}", timeout=TIMEOUT)
            arq = DADOS_DIR / "raw/kmz" / f"{ep.replace('/', '_')}_{timestamp()}.kmz"
            with open(arq, "wb") as f:
                f.write(r.content)
        except Exception as e:
            log(f"⚠ KMZ {ep} → {e}")

# ================= LOOP =====================

def loop():
    criar_pastas()

    ciclo = 1
    while True:
        log(f"\n=== CICLO {ciclo} ===")

        try:
            if not autenticar():
                log("❌ Falha na autenticação — aguardando 60s")
                time.sleep(60)
                continue

            linhas = coletar_linhas()
            corredores = coletar_corredores()
            empresas = coletar_empresas()

            coletar_paradas(linhas, corredores)

            if not posicao_global():
                posicao_fallback(linhas, empresas)

            coletar_kmz()

            espera = random.randint(INTERVALO_MIN, INTERVALO_MAX)
            log(f"⏳ Aguardando {espera}s")

            time.sleep(espera)
            ciclo += 1

        except Exception as e:
            log(f"🔥 ERRO CRÍTICO: {e}")
            time.sleep(60)

# ============================================

if __name__ == "__main__":

    modo = os.getenv("EXEC_MODE", "local")

    print(f"🚀 Modo de execução: {modo.upper()}")

    def executar_ciclo():
        if autenticar():
            coletar_tudo()
        else:
            print("❌ Falha na autenticação")

    if modo == "github":
        executar_ciclo()
        print("✅ Execução finalizada (modo github)")
    else:
        while True:
            executar_ciclo()
            intervalo = random.randint(40, 70)
            print(f"⏳ Aguardando {intervalo}s para novo ciclo")
            time.sleep(intervalo)


