import sqlite3
import os

# Pega o caminho absoluto da pasta onde o script criar_banco.py está salvo
diretorio_atual = os.path.dirname(os.path.abspath(__file__))

# Se o script estiver dentro de assets, a raiz é a pasta de cima. Se estiver na raiz, usa ela mesma.
if os.path.basename(diretorio_atual) == "assets":
    pasta_raiz = os.path.dirname(diretorio_atual)
else:
    pasta_raiz = diretorio_atual

# Garante a criação da pasta assets na raiz correta do TCC2
pasta_assets_correta = os.path.join(pasta_raiz, "assets")
os.makedirs(pasta_assets_correta, exist_ok=True)

# Fixa o caminho do banco de dados na pasta assets principal
caminho_banco = os.path.join(pasta_assets_correta, "termodinamica.db")
conn = sqlite3.connect(caminho_banco)
cursor = conn.cursor()

print(f"🔨 Criando banco de dados oficial em: {caminho_banco}")

cursor.execute("CREATE TABLE IF NOT EXISTS antoine (substancia TEXT PRIMARY KEY, A REAL, B REAL, C REAL)")
cursor.execute("CREATE TABLE IF NOT EXISTS propriedades_criticas (substancia TEXT PRIMARY KEY, Tc_K REAL, Pc_bar REAL, omega REAL)")
cursor.execute("CREATE TABLE IF NOT EXISTS parametros_elv (sistema TEXT PRIMARY KEY, A12 REAL, A21 REAL)")

print("💾 Populando tabelas com parâmetros reais da literatura...")

dados_antoine = [
    ("Água", 5.11564, 1687.537, 230.17),
    ("Etanol", 5.24677, 1598.673, 226.51),
    ("Metano (CH4)", 3.98075, 443.028, 272.74),
    ("Dióxido Carbono (CO2)", 6.81228, 1301.679, 269.61)
]

dados_criticos = [
    ("Metano (CH4)", 190.6, 46.1, 0.012),
    ("Dióxido Carbono (CO2)", 304.2, 73.8, 0.224),
    ("Água", 647.1, 220.6, 0.344),
    ("Etanol", 513.9, 61.4, 0.645)
]

dados_elv = [
    ("Etanol/Água (Van Laar)", 1.6113, 0.7972),
    ("Etanol/Água (Margules)", 1.5450, 0.8120)
]

cursor.executemany("INSERT OR REPLACE INTO antoine VALUES (?, ?, ?, ?)", dados_antoine)
cursor.executemany("INSERT OR REPLACE INTO propriedades_criticas VALUES (?, ?, ?, ?)", dados_criticos)
cursor.executemany("INSERT OR REPLACE INTO parametros_elv VALUES (?, ?, ?)", dados_elv)

conn.commit()
conn.close()

print("\n✅ Sucesso total! Banco gerado no local correto sem duplicidade.")
