import pandas as pd
import requests
import json
import unicodedata
from difflib import get_close_matches
from io import StringIO

# --- 1. CONFIGURAÇÕES E CHAVES ---
SUPABASE_URL = "https://mynxlubykylncinttggu.supabase.co"
SUBMIT_URL = "https://mynxlubykylncinttggu.functions.supabase.co/ibge-submit"

# Chave API Pública (Recuperada e corrigida)
API_KEY_PUBLIC = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15bnhsdWJ5a3lsbmNpbnR0Z2d1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUxODg2NzAsImV4cCI6MjA4MDc2NDY3MH0.Z-zqiD6_tjnF2WLU167z7jT5NzZaG72dWH0dpQW1N-Y"

# --- 2. SEUS DADOS DE LOGIN ---
EMAIL_USER = "cruzeirogoleiro@gmail.com"
SENHA_USER = "teste123"  # <--- COLOQUE A SENHA QUE VOCÊ CRIOU NO PASSO ANTERIOR

# --- 3. DADOS DE ENTRADA (input.csv) ---
csv_content = """municipio,populacao
Niteroi,515317
Sao Gonçalo,1091737
Sao Paulo,12396372
Belo Horzionte,2530701
Florianopolis,516524
Santo Andre,723889
Santoo Andre,700000
Rio de Janeiro,6718903
Curitba,1963726
Brasilia,3094325"""

# --- FUNÇÕES UTILITÁRIAS ---

def normalizar(texto):
    """Remove acentos e põe em minúsculas."""
    if not isinstance(texto, str): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto)
                  if unicodedata.category(c) != 'Mn').lower()

def fazer_login():
    """Realiza o login no Supabase e retorna o ACCESS_TOKEN."""
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": API_KEY_PUBLIC, "Content-Type": "application/json"}
    payload = {"email": EMAIL_USER, "password": SENHA_USER}
    
    print("🔑 Fazendo login...")
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        raise Exception(f"Erro no Login: {resp.text}")
    return resp.json()['access_token']

def buscar_ibge():
    """Baixa a lista de todos os municípios do IBGE."""
    print("🌎 Baixando dados do IBGE...")
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    resp = requests.get(url)
    return resp.json()

# --- FLUXO PRINCIPAL ---

def main():
    # Salvar o arquivo input.csv no disco
    with open("input.csv", "w", encoding="utf-8") as f:
        f.write(csv_content)

    # 1. Autenticação
    try:
        token = fazer_login()
    except Exception as e:
        print(f"❌ Falha: {e}")
        return

    # 2. Carregar dados
    df_input = pd.read_csv("input.csv")
    dados_ibge_raw = buscar_ibge()

    # Preparar "mapa" do IBGE
    mapa_ibge = {}
    nomes_para_fuzzy = [] 
    
    print("🛠️ Mapeando cidades (ignorando erros de estrutura)...")
    for cidade in dados_ibge_raw:
        # --- CORREÇÃO AQUI: Bloco try/except para pular dados quebrados ---
        try:
            nome_real = cidade['nome']
            nome_norm = normalizar(nome_real)
            
            # Tenta ler a hierarquia completa. Se falhar, pula para o 'except'.
            info = {
                'municipio_ibge': nome_real,
                'uf': cidade['microrregiao']['mesorregiao']['UF']['sigla'],
                'regiao': cidade['microrregiao']['mesorregiao']['UF']['regiao']['nome'],
                'id_ibge': cidade['id']
            }
            
            mapa_ibge[nome_norm] = info
            nomes_para_fuzzy.append(nome_norm)
            
        except (KeyError, TypeError):
            # Se a cidade vier com dados faltando na API, apenas ignoramos ela
            continue 

    # 3. Processamento
    resultados = []
    
    print("⚙️ Processando municípios do input...")
    for i, row in df_input.iterrows():
        cidade_input = row['municipio']
        pop = row['populacao']
        cidade_norm = normalizar(cidade_input)
        
        status = "NAO_ENCONTRADO"
        match_info = None
        
        if cidade_norm in mapa_ibge:
            match_info = mapa_ibge[cidade_norm]
            status = "OK"
        else:
            matches = get_close_matches(cidade_norm, nomes_para_fuzzy, n=1, cutoff=0.7)
            if matches:
                melhor_match = matches[0]
                match_info = mapa_ibge[melhor_match]
                status = "OK"
        
        linha = {
            "municipio_input": cidade_input,
            "populacao_input": pop,
            "municipio_ibge": match_info['municipio_ibge'] if match_info else None,
            "uf": match_info['uf'] if match_info else None,
            "regiao": match_info['regiao'] if match_info else None,
            "id_ibge": match_info['id_ibge'] if match_info else None,
            "status": status
        }
        resultados.append(linha)

    # 4. CSV Final
    df_resultado = pd.DataFrame(resultados)
    df_resultado.to_csv("resultado.csv", index=False)
    print("✅ Arquivo 'resultado.csv' gerado.")

    # 5. Estatísticas
    df_ok = df_resultado[df_resultado['status'] == 'OK']
    
    if len(df_ok) == 0:
        print("⚠️ ALERTA: Nenhuma cidade foi encontrada. Verifique os dados.")
        return

    stats = {
        "total_municipios": int(len(df_resultado)),
        "total_ok": int(len(df_ok)),
        "total_nao_encontrado": int(len(df_resultado[df_resultado['status'] == 'NAO_ENCONTRADO'])),
        "total_erro_api": 0,
        "pop_total_ok": int(df_ok['populacao_input'].sum()),
        "medias_por_regiao": df_ok.groupby('regiao')['populacao_input'].mean().to_dict()
    }
    
    for regiao in stats["medias_por_regiao"]:
        stats["medias_por_regiao"][regiao] = round(stats["medias_por_regiao"][regiao], 2)

    # 6. Envio
    payload_final = {"stats": stats}
    headers_submit = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("🚀 Enviando resposta para correção...")
    resp_submit = requests.post(SUBMIT_URL, json=payload_final, headers=headers_submit)
    
    print("\n--- RESPOSTA DA PROVA ---")
    print(f"Status: {resp_submit.status_code}")
    try:
        feedback = resp_submit.json()
        print(f"NOTA: {feedback.get('score')}")
        print(f"MENSAGEM: {feedback.get('feedback')}")
    except:
        print("Resposta bruta:", resp_submit.text)

if __name__ == "__main__":
    main()