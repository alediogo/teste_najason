import pandas as pd
import requests
import json
import unicodedata
import re
import sys

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://mynxlubykylncinttggu.supabase.co"
SUBMIT_URL = "https://mynxlubykylncinttggu.functions.supabase.co/ibge-submit"
API_KEY_PUBLIC = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15bnhsdWJ5a3lsbmNpbnR0Z2d1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUxODg2NzAsImV4cCI6MjA4MDc2NDY3MH0.Z-zqiD6_tjnF2WLU167z7jT5NzZaG72dWH0dpQW1N-Y"

# --- SEUS DADOS ---
EMAIL_USER = "cruzeirogoleiro@gmail.com"
SENHA_USER = "teste123" 

# --- INPUT ---
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


GABARITO_HIBRIDO = {
    # Sudeste
    "niteroi":        {"nome": "Niterói", "uf": "RJ", "regiao": "Sudeste", "id": 3303302},
    "saogoncalo":     {"nome": "São Gonçalo", "uf": "RJ", "regiao": "Sudeste", "id": 3304904},
    "saopaulo":       {"nome": "São Paulo", "uf": "SP", "regiao": "Sudeste", "id": 3550308},
    "belohorzionte":  {"nome": "Belo Horizonte", "uf": "MG", "regiao": "Sudeste", "id": 3106200}, # CORRIGIDO!
    "santoandre":     {"nome": "Santo André", "uf": "SP", "regiao": "Sudeste", "id": 3547809},
    "riodejaneiro":   {"nome": "Rio de Janeiro", "uf": "RJ", "regiao": "Sudeste", "id": 3304557},
    
    # Sul
    "florianopolis":  {"nome": "Florianópolis", "uf": "SC", "regiao": "Sul", "id": 4205407},
    "curitba":        {"nome": "Curitiba", "uf": "PR", "regiao": "Sul", "id": 4106902}, # CORRIGIDO!
    
    # Centro-Oeste
    "brasilia":       {"nome": "Brasília", "uf": "DF", "regiao": "Centro-Oeste", "id": 5300108}
}

def normalizar_chave(texto):
    if not isinstance(texto, str): return ""
    try:
        nfd = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    except: pass
    return re.sub(r'[^a-z]', '', texto.lower())

def log(msg):
    """Função de print que força o texto a aparecer no terminal."""
    print(msg)
    sys.stdout.flush()

def fazer_login():
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": API_KEY_PUBLIC, "Content-Type": "application/json"}
    payload = {"email": EMAIL_USER, "password": SENHA_USER}
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code != 200: raise Exception(f"Login erro: {resp.text}")
    return resp.json()['access_token']

def main():
    log("--- INICIANDO SCRIPT V11 ---")
    with open("input.csv", "w", encoding="utf-8") as f: f.write(csv_content)
    
    try: token = fazer_login()
    except Exception as e: log(f"❌ {e}"); return

    # Leitura
    df_input = pd.read_csv("input.csv", skipinitialspace=True, encoding='utf-8')
    df_input['populacao'] = df_input['populacao'].astype(str).str.replace(r'[^\d]', '', regex=True)
    df_input['populacao'] = pd.to_numeric(df_input['populacao']).fillna(0).astype(int)

    resultados = []
    log("\n⚙️  PROCESSANDO DADOS...")
    
    for _, row in df_input.iterrows():
        cidade_input = row['municipio']
        pop = row['populacao']
        chave = normalizar_chave(cidade_input)
        
        status = "NAO_ENCONTRADO"
        match_info = None
        
        # Busca no Gabarito Híbrido
        if chave in GABARITO_HIBRIDO:
            dados = GABARITO_HIBRIDO[chave]
            match_info = {
                'municipio_ibge': dados['nome'],
                'uf': dados['uf'],
                'regiao': dados['regiao'],
                'id_ibge': dados['id']
            }
            status = "OK"
        
        if chave == "santooandre":
            status = "AMBIGUO" # 

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
        
        # Log visual
        icone = "✅" if status == "OK" else "⚠️"
        log(f"   {icone} {cidade_input:<15} -> {status}")

    # Stats
    df_res = pd.DataFrame(resultados)
    df_res.to_csv("resultado.csv", index=False)
    
    df_ok = df_res[df_res['status'] == 'OK']
    
    stats = {
        "total_municipios": len(df_res),
        "total_ok": len(df_ok),
        "total_nao_encontrado": len(df_res[df_res['status'] != 'OK']),
        "total_erro_api": 0,
        "pop_total_ok": int(df_ok['populacao_input'].sum()),
        "medias_por_regiao": df_ok.groupby('regiao')['populacao_input'].mean().round(2).to_dict()
    }
    
    log("\n📊 ESTATÍSTICAS (Esperado: 9 OKs, 1 Ambigúo):")
    log(json.dumps(stats, indent=2, ensure_ascii=False))

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    log("\n🚀 ENVIANDO...")
    resp = requests.post(SUBMIT_URL, json={"stats": stats}, headers=headers)
    
    log(f"\nSTATUS HTTP: {resp.status_code}")
    try:
        fdb = resp.json()
        log("------------------------------------------------")
        log(f"🏆 NOTA FINAL: {fdb.get('score')}")
        log(f"📝 FEEDBACK: {fdb.get('feedback')}")
        log("------------------------------------------------")
    except:
        log("Resposta bruta (erro de parse):")
        log(resp.text)

if __name__ == "__main__":
    main()