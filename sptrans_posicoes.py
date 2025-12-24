import requests
import json
import datetime
import os

# --- CONFIGURAÇÃO ---
# Token de Acesso (vem do GitHub Secrets)
TOKEN = os.getenv("SPTRANS_TOKEN")

# URL Base (Utilizando HTTPS)
BASE_URL = "https://api.olhovivo.sptrans.com.br/v2.1"

# Objeto de sessão para manter o cookie de autenticação
session = requests.Session()

# Garante que as pastas existam
os.makedirs("dados/posicoes", exist_ok=True)

# ----------------------------------------------------------------------
# FUNÇÃO 1: AUTENTICAÇÃO
# ----------------------------------------------------------------------
def autenticar_api():
    if not TOKEN:
        print("❌ SPTRANS_TOKEN não encontrado no ambiente.")
        return False

    AUTH_URL = f"{BASE_URL}/Login/Autenticar?token={TOKEN}"
    try:
        response = session.post(AUTH_URL)
        if response.status_code == 200 and response.text.strip().lower() == 'true':
            print("✅ Autenticação realizada com sucesso!")
            return True
        else:
            print("❌ Falha na autenticação. Resposta:", response.text)
            return False
    except requests.exceptions.RequestException as e:
        print("❌ Erro na autenticação:", e)
        return False


# ----------------------------------------------------------------------
# FUNÇÃO 2: SOLICITAR LOCALIZAÇÕES E SALVAR JSON
# ----------------------------------------------------------------------
def solicitar_e_salvar_posicoes():
    POSICAO_URL = f"{BASE_URL}/Posicao"
    try:
        response = session.get(POSICAO_URL)
        if response.status_code == 200:
            dados_posicao = response.json()

            timestamp_ta = None
            linhas_localizadas = dados_posicao.get('l', [])

            if linhas_localizadas:
                primeira_linha = linhas_localizadas[0]
                veiculos = primeira_linha.get('vs', [])
                if veiculos:
                    primeiro_veiculo = veiculos[0]
                    timestamp_ta = primeiro_veiculo.get('ta')

            if timestamp_ta:
                nome_base = timestamp_ta.replace('T', '_').replace(':', '-').replace('Z', '')
                nome_arquivo = f"dados/posicoes/posicao_veiculos_{nome_base}.json"
            elif dados_posicao.get('hr'):
                nome_base = dados_posicao['hr'].replace(':', '-')
                nome_arquivo = f"dados/posicoes/posicao_veiculos_hr_{nome_base}.json"
            else:
                nome_arquivo = f"dados/posicoes/posicao_veiculos_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(nome_arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados_posicao, f, ensure_ascii=False, indent=4)

            print(f"✅ Arquivo salvo com sucesso: {nome_arquivo}")
            return True

        else:
            print(f"❌ Falha ao obter dados. Código HTTP: {response.status_code}")
            return False

    except Exception as e:
        print("❌ Erro ao salvar posição:", e)
        return False



# ----------------------------------------------------------------------
# BAIXAR KMZ
# ----------------------------------------------------------------------
def baixar_kmz(endpoint):
    url = f"{BASE_URL}{endpoint}"

    print(f"\n📡 Consultando: {url}")

    try:
        response = session.get(url, timeout=30)

        if response.status_code == 200:
            agora = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_endpoint = endpoint.replace("/", "_").strip("_")
            nome_arquivo = f"{caminho}{safe_endpoint}_{agora}.kmz"

            with open(nome_arquivo, "wb") as f:
                f.write(response.content)

            print(f"📁 KMZ salvo: {nome_arquivo}")

        else:
            print(f"⚠ Erro {response.status_code}: {response.text[:200]}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição KMZ: {e}")


# ----------------------------------------------------------------------
# LOOP COMPLETO EM TODOS OS ENDPOINTS
# ----------------------------------------------------------------------
def iniciar_loop_kmz(intervalo=10):

    # Lista de endpoints a serem consultados
    endpoints = [
        "/KMZ",
        "/KMZ/BC",
        "/KMZ/CB",
        "/KMZ/Corredor",
        "/KMZ/Corredor/BC",
        "/KMZ/OutrasVias"
    ]

    print("\n🔄 Iniciando ciclo contínuo de KMZ...\n")

    # Autentica uma vez no início
    if not autenticar_api():
        print("❌ Não foi possível autenticar. Abortando.")
        return

    # Loop infinito
    while True:
        for endpoint in endpoints:
            baixar_kmz(endpoint)

            print(f"⏳ Aguardando {intervalo} segundos até a próxima consulta...\n")
            time.sleep(intervalo)

        print("🔁 Reiniciando o ciclo completo de consultas...\n")


# ----------------------------------------------------------------------
# EXECUÇÃO PRINCIPAL
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("SPTRANS_TOKEN presente?", bool(TOKEN))
    if autenticar_api():
        solicitar_e_salvar_posicoes()
         iniciar_loop_kmz(intervalo=10)
    else:
        print("❌ Autenticação falhou. Abortando.")
