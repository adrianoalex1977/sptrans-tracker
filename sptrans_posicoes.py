import requests
import json
import datetime
import os

# === CONFIGURAÇÕES ===
TOKEN = os.getenv("TOKEN")
BASE_URL = "https://api.olhovivo.sptrans.com.br/v2.1"


# Garante que as pastas existam, mesmo se o repositório estiver vazio
os.makedirs("dados/posicoes", exist_ok=True)


# Sessão persistente
session = requests.Session()

# === FUNÇÃO 1: AUTENTICAÇÃO ===
def autenticar_api():
    """
    Autentica o token na API SPTrans.
    Retorna True se sucesso.
    """
    AUTH_URL = f"{BASE_URL}/Login/Autenticar?token={TOKEN}"
    try:
        response = session.post(AUTH_URL)
        print(f"🔐 Autenticando... (status {response.status_code})")

        if response.status_code == 200 and response.text.strip().lower() == 'true':
            print("✅ Autenticação bem-sucedida!")
            return True
        else:
            print(f"❌ Falha na autenticação: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"🚨 Erro de rede na autenticação: {e}")
        return False

# === FUNÇÃO 2: SOLICITAR E SALVAR POSIÇÕES ===
def solicitar_e_salvar_posicoes():
    """
    Solicita a posição dos veículos e salva em JSON na pasta ./dados/posicoes/
    """
    POSICAO_URL = f"{BASE_URL}/Posicao"
    pasta_saida = os.path.join("dados", "posicoes")
    os.makedirs(pasta_saida, exist_ok=True)

    try:
        response = session.get(POSICAO_URL)
        print(f"📡 Requisição GET {POSICAO_URL} → Status {response.status_code}")

        if response.status_code != 200:
            print(f"❌ Erro ao obter dados: {response.text}")
            return False, None

        dados_posicao = response.json()
        print("📦 Dados recebidos da API.")
        print("🔑 Chaves principais:", list(dados_posicao.keys()))

        timestamp_ta = None
        linhas_localizadas = dados_posicao.get('l', [])

        if not linhas_localizadas:
            print("⚠️ Nenhuma linha encontrada no campo 'l'.")
        else:
            print(f"🚌 Total de linhas: {len(linhas_localizadas)}")

            # pega a primeira linha e o primeiro veículo
            primeira_linha = linhas_localizadas[0]
            veiculos = primeira_linha.get('vs', [])

            if veiculos:
                primeiro_veiculo = veiculos[0]
                timestamp_ta = primeiro_veiculo.get('ta')
                print(f"⏱️ Timestamp encontrado: {timestamp_ta}")
            else:
                print("⚠️ Nenhum veículo encontrado na primeira linha.")

        # === NOME DO ARQUIVO ===
        if timestamp_ta:
            nome_base = timestamp_ta.replace('T', '_').replace(':', '-').replace('Z', '')
            nome_arquivo = f"posicao_veiculos_{nome_base}.json"
        elif dados_posicao.get('hr'):
            nome_base = dados_posicao['hr'].replace(':', '-')
            nome_arquivo = f"posicao_veiculos_hr_{nome_base}.json"
        else:
            nome_base = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"posicao_veiculos_sem_timestamp_{nome_base}.json"

        caminho_completo = os.path.join(pasta_saida, nome_arquivo)

        # === SALVAR JSON ===
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            json.dump(dados_posicao, f, ensure_ascii=False, indent=4)

        print(f"💾 Arquivo salvo com sucesso em: {os.path.abspath(caminho_completo)}")
        return True, caminho_completo

    except json.JSONDecodeError:
        print("🚨 Erro: resposta não é JSON válido.")
        return False, None
    except requests.exceptions.RequestException as e:
        print(f"🚨 Erro de rede: {e}")
        return False, None
    except Exception as e:
        print(f"🚨 Erro inesperado: {e}")
        return False, None

# === EXECUÇÃO PRINCIPAL ===
if __name__ == "__main__":
    print("🚍 Iniciando coleta de posições SPTrans...")

    if autenticar_api():
        sucesso, arquivo = solicitar_e_salvar_posicoes()
        if sucesso:
            print(f"✅ Processo finalizado. Arquivo: {arquivo}")
        else:
            print("⚠️ Nenhum arquivo foi salvo.")
    else:
        print("❌ Token inválido ou falha de autenticação.")

