import flet as ft
import numpy as np
import sqlite3

# Constantes de Antoine para a Água (NIST) - Validação exata de Tsat
A_ANTOINE_AGUA = 5.11564
B_ANTOINE_AGUA = 1687.537
C_ANTOINE_AGUA = 230.17

R_GASES = 8.31446261815324e-5  # bar*m3/(mol*K)

def calcular_tsat_antoine(p_bar):
    """Calcula a temperatura de saturação exata da água em °C via Antoine"""
    return (B_ANTOINE_AGUA / (A_ANTOINE_AGUA - np.log10(p_bar))) - C_ANTOINE_AGUA

def calcular_volume_superaquecido_perry(p_bar, t_celcius):
    """Calcula dinamicamente o volume específico do vapor d'água superaquecido (m³/kg)"""
    t_kelvin = t_celcius + 273.15
    b0 = -0.00115
    b1 = 4.2e-6
    v_ideal = (R_GASES * t_kelvin) / (p_bar * 0.018015)
    z_aprox = 1.0 + (b0 + b1 * t_celcius) * p_bar
    return round(v_ideal * z_aprox, 4)

# TABELA REVISADA: Escopo expandido até 250 °C conforme especificações do projeto
TABELA_SATURACAO_AGUA = {
    "T":    [0.01, 10.0, 20.0, 30.0, 40.0, 50.0, 75.0, 100.0, 125.0, 150.0, 180.0, 200.0, 220.0, 250.0],
    "Psat": [0.611, 1.228, 2.339, 4.247, 7.385, 12.35, 38.59, 101.33, 232.2, 476.2, 1002.2, 1554.9, 2319.6, 3976.2], # kPa
    "vl":   [0.0010, 0.0010, 0.0010, 0.0010, 0.0010, 0.0010, 0.0010, 0.0010, 0.0011, 0.0011, 0.0011, 0.0012, 0.0012, 0.0013], # m3/kg
    "vv":   [206.14, 106.38, 57.79, 32.89, 19.52, 12.03, 4.131, 1.673, 0.770, 0.392, 0.194, 0.127, 0.086, 0.050] # m3/kg
}

def buscar_dados_sqlite(tabela, substancia):
    conn = sqlite3.connect("assets/termodinamica.db")
    cursor = conn.cursor()
    try:
        if tabela == "antoine":
            cursor.execute("SELECT A, B, C FROM antoine WHERE substancia=?", (substancia,))
            row = cursor.fetchone()
            if row: return {"A": float(row[0]), "B": float(row[1]), "C": float(row[2])}
        elif tabela == "criticas":
            cursor.execute("SELECT Tc_K, Pc_bar, omega FROM propriedades_criticas WHERE substancia=?", (substancia,))
            row = cursor.fetchone()
            if row: return {"Tc_K": float(row[0]), "Pc_bar": float(row[1]), "omega": float(row[2])}
        elif tabela == "elv":
            cursor.execute("SELECT A12, A21 FROM parametros_elv WHERE sistema=?", (substancia,))
            row = cursor.fetchone()
            if row: return {"A12": float(row[0]), "A21": float(row[1])}
    except Exception as ex:
        print(f"Erro SQLite interno: {ex}")
        return None
    finally: 
        conn.close()
    return None
# =============================================================================
# ALGORITMOS NUMÉRICOS DE CÁLCULO REVISADOS
# =============================================================================
def interpolacao_saturacao_inteligente(t_alvo=None, p_alvo_bar=None):
    t_lista = TABELA_SATURACAO_AGUA["T"]
    p_lista = TABELA_SATURACAO_AGUA["Psat"]
    vl_lista = TABELA_SATURACAO_AGUA["vl"]
    vv_lista = TABELA_SATURACAO_AGUA["vv"]
    
    if t_alvo is not None and p_alvo_bar is None:
        if t_alvo < -273.15:
            return None, "❌ Erro Físico: Temperatura abaixo do Zero Absoluto (-273.15 °C)!"
        if not (t_lista[0] <= t_alvo <= t_lista[-1]):
            return None, f"⚠️ Fora da faixa da tabela ({t_lista[0]} a {t_lista[-1]} °C)"
            
        for i in range(len(t_lista) - 1):
            if t_lista[i] <= t_alvo <= t_lista[i+1]:
                t0, t1 = t_lista[i], t_lista[i+1]
                p0, p1 = p_lista[i], p_lista[i+1]
                vl0, vl1 = vl_lista[i], vl_lista[i+1]
                vv0, vv1 = vv_lista[i], vv_lista[i+1]
                
                fator = (t_alvo - t0) / (t1 - t0)
                p_interp = p0 + (p1 - p0) * fator
                vl_interp = vl0 + (vl1 - vl0) * fator
                vv_interp = vv0 + (vv1 - vv0) * fator
                
                return f"📉 Saturação a {t_alvo}°C:\n• Psat: {p_interp:.2f} kPa\n• vl: {vl_interp:.4f} m³/kg\n• vv: {vv_interp:.4f} m³/kg", None

    elif p_alvo_bar is not None and t_alvo is None:
        if p_alvo_bar <= 0:
            return None, "❌ Erro Físico: Não existem pressões nulas ou negativas!"
        p_alvo_kpa = p_alvo_bar * 100.0
        if not (p_lista[0] <= p_alvo_kpa <= p_lista[-1]):
            return None, f"⚠️ Fora da faixa da tabela ({p_lista[0]/100.0} a {p_lista[-1]/100.0} bar)"
            
        for i in range(len(p_lista) - 1):
            if p_lista[i] <= p_alvo_kpa <= p_lista[i+1]:
                p0, p1 = p_lista[i], p_lista[i+1]
                t0, t1 = t_lista[i], t_lista[i+1]
                vl0, vl1 = vl_lista[i], vl_lista[i+1]
                vv0, vv1 = vv_lista[i], vv_lista[i+1]
                
                fator = (p_alvo_kpa - p0) / (p1 - p0)
                t_interp = t0 + (t1 - t0) * fator
                vl_interp = vl0 + (vl1 - vl0) * fator
                vv_interp = vv0 + (vv1 - vv0) * fator
                
                return f"📉 Saturação a {p_alvo_bar:.1f} bar:\n• Tsat: {t_interp:.1f} °C\n• vl: {vl_interp:.4f} m³/kg\n• vv: {vv_interp:.4f} m³/kg", None

    elif t_alvo is not None and p_alvo_bar is not None:
        return None, "⚠️ Na Região de Saturação, T e P não são independentes.\nPreencha APENAS um campo."
        
    return None, "❌ Digite um valor em pelo menos um dos campos."

def interpolacao_bilinear_superaquecido(p_alvo, t_alvo):
    if p_alvo <= 0: return None, "❌ Erro Físico: Pressão deve ser maior que zero!"
    if t_alvo < -273.15: return None, "❌ Erro Físico: Abaixo do Zero Absoluto!"
    
    p_ajustado = round(p_alvo, 1)
    if not (1.0 <= p_ajustado <= 10.0):
        return None, "⚠️ Pressão fora do escopo. Insira um valor decimal entre 1.0 e 10.0 bar."
    if not (100.0 <= t_alvo <= 250.0):
        return None, "⚠️ Temperatura fora das fronteiras analíticas (100 a 250 °C)."

    t_sat_real = calcular_tsat_antoine(p_ajustado)
    if t_alvo <= t_sat_real:
        return None, f"❌ Erro Físico: Região de Líquido Comprimido!\nPara {p_ajustado:.1f} bar, insira T > {t_sat_real:.1f} °C."

    v_calculado = calcular_volume_superaquecido_perry(p_ajustado, t_alvo)
    return f"📦 Volume Específico para {p_ajustado:.1f} bar:\n{v_calculado} m³/kg", None

def resolver_fator_z_newton(modelo, substancia, temperatura_c, pressao_bar):
    if pressao_bar <= 0: 
        return None, None, "❌ Erro Físico: Pressão deve ser maior que zero!"
    if temperatura_c < -273.15:
        return None, None, "❌ Erro Físico: Temperatura abaixo do Zero Absoluto!"
        
    comp = buscar_dados_sqlite("criticas", substancia)
    if not comp:
        if substancia == "Metano (CH4)":
            comp = {"Tc_K": 190.6, "Pc_bar": 46.1, "omega": 0.012}
        elif substancia == "Dióxido Carbono (CO2)":
            comp = {"Tc_K": 304.2, "Pc_bar": 73.8, "omega": 0.224}
        else:
            return None, None, "❌ Gás não localizado no banco de dados."
            
    T = temperatura_c + 273.15
    limite_k = 0.3 * comp["Tc_K"]
    limite_c = limite_k - 273.15
    
    # VALIDAÇÃO CRÍTICA DINÂMICA REVISADA
    if T < limite_k:
        return None, None, f"⚠️ Temperatura abaixo do limite do modelo para o {substancia} ({limite_c:.1f} °C).\nAbaixo de {limite_k:.1f} K, o componente solidifica ou gera divergência matemática nas forças de coesão."
        
    P = pressao_bar
    Tr = T / comp["Tc_K"]
    
    if modelo == "Peng-Robinson (PR)":
        m = 0.37464 + 1.54226 * comp["omega"] - 0.26992 * comp["omega"]**2
        u, w, omega_a, omega_b = 2, -1, 0.45724, 0.07780
    else:
        m = 0.480 + 1.574 * comp["omega"] - 0.176 * comp["omega"]**2
        u, w, omega_a, omega_b = 1, 0, 0.42748, 0.08664
        
    alpha = (1 + m * (1 - np.sqrt(Tr)))**2
    a = omega_a * (R_GASES**2 * comp["Tc_K"]**2 / comp["Pc_bar"]) * alpha
    b = omega_b * (R_GASES * comp["Tc_K"] / comp["Pc_bar"])
    A, B = (a * P) / (R_GASES**2 * T**2), (b * P) / (R_GASES * T)
    
    alfa_c = (u - 1) * B - 1
    beta_c = A + (w - u - u*B) * B**2 - u * B
    gamma_c = - (A * B + w * B**2 + w * B**3)
    
    Z = 1.0
    for _ in range(100):
        f = Z**3 + alfa_c * Z**2 + beta_c * Z + gamma_c
        df = 3 * Z**2 + 2 * alfa_c * Z + beta_c
        if abs(df) < 1e-12: break
        Z_novo = Z - f / df
        if abs(Z_novo - Z) < 1e-6:
            v_mol = (Z_novo * R_GASES * T) / P
            return round(Z_novo, 4), round(v_mol * 1000, 4), None
        Z = Z_novo
    return None, None, "❌ Limite de iterações do Newton-Raphson atingido."

def calcular_elv_binario(modelo, x1, temperatura_c):
    if temperatura_c < -273.15: 
        return None, None, None, None, "❌ Erro Físico: Temperatura abaixo do Zero Absoluto (-273.15 °C)!"
    if not (0.0 <= x1 <= 1.0): 
        return None, None, None, None, "❌ Erro Físico: Fração molar (x1) deve estar entre 0.0 e 1.0!"

    p_agua = buscar_dados_sqlite("antoine", "Água")
    p_etanol = buscar_dados_sqlite("antoine", "Etanol")
    par_elv = buscar_dados_sqlite("elv", f"Etanol/Água ({modelo})")
    
    if not p_agua or not p_etanol or not par_elv:
        if modelo == "Van Laar": A12, A21 = 1.6113, 0.7972
        else: A12, A21 = 1.545, 0.812
        p_sat1 = np.exp(16.5179 - (3641.58 / (temperatura_c + 225.86))) / 100.0 if temperatura_c > -50 else 0.01
        p_sat2 = np.exp(16.3872 - (3885.70 / (temperatura_c + 230.17))) / 100.0 if temperatura_c > -50 else 0.01
    else:
        A12, A21 = par_elv["A12"], par_elv["A21"]
        p_sat1 = np.exp(p_etanol["A"] - (p_etanol["B"] / (temperatura_c + p_etanol["C"]))) / 100.0
        p_sat2 = np.exp(p_agua["A"] - (p_agua["B"] / (p_agua["C"] + temperatura_c))) / 100.0

    x2 = 1.0 - x1
    if modelo == "Van Laar":
        if (A12 * x1 + A21 * x2) == 0: ln_gamma1, ln_gamma2 = 0, 0
        else:
            ln_gamma1 = A12 / (1.0 + (A12 * x1) / (A21 * x2))**2 if x2 > 0 else 0
            ln_gamma2 = A21 / (1.0 + (A21 * x2) / (A12 * x1))**2 if x1 > 0 else 0
    else: 
        ln_gamma1 = x2**2 * (A12 + 2.0 * (A21 - A12) * x1)
        ln_gamma2 = x1**2 * (A21 + 2.0 * (A12 - A21) * x2)
        
    gamma1, gamma2 = np.exp(ln_gamma1), np.exp(ln_gamma2)
    P_bolha = (x1 * gamma1 * p_sat1) + (x2 * gamma2 * p_sat2)
    
    if P_bolha <= 0: return None, None, None, None, "❌ Erro Físico: Pressão calculada inconsistente."
    
    y1 = (x1 * gamma1 * p_sat1) / P_bolha
    y1 = max(0.0, min(1.0, y1))
    
    return round(P_bolha, 4), round(y1, 4), round(gamma1, 3), round(gamma2, 3), None
# =============================================================================
# INTERFACE GRÁFICA MULTIPLATAFORMA (Flet 1.0)
# =============================================================================
def main(page: ft.Page):
    page.title = "TCC2 - Termodinâmica Móvel"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK 

    # --- ABA INTERPOLAÇÃO ---
    drop_tipo_interp = ft.Dropdown(label="Tipo de Interpolação", width=300, value="Saturação (Linear)", options=[ft.dropdown.Option("Saturação (Linear)"), ft.dropdown.Option("Superaquecido (Bilinear)")])
    txt_temp_interp = ft.TextField(label="Temperatura (°C)", width=300, keyboard_type=ft.KeyboardType.NUMBER)
    txt_pres_interp = ft.TextField(label="Pressão (bar)", width=300, keyboard_type=ft.KeyboardType.NUMBER)
    lbl_res_interp = ft.Text(value="Aguardando entrada de dados...", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200, text_align=ft.TextAlign.CENTER)

    def clique_interpola(e):
        try:
            t_val = float(txt_temp_interp.value) if txt_temp_interp.value else None
            p_val = float(txt_pres_interp.value) if txt_pres_interp.value else None
            
            if drop_tipo_interp.value == "Saturação (Linear)":
                res, erro = interpolacao_saturacao_inteligente(t_alvo=t_val, p_alvo_bar=p_val)
                lbl_res_interp.value = erro if erro else res
            elif drop_tipo_interp.value == "Superaquecido (Bilinear)":
                if t_val is None or p_val is None:
                    lbl_res_interp.value = "❌ Erro: No modo Superaquecido você DEVE preencher Temperatura E Pressão juntas."
                else:
                    res, erro = interpolacao_bilinear_superaquecido(p_val, t_val)
                    lbl_res_interp.value = erro if erro else res
        except Exception: 
            lbl_res_interp.value = f"❌ Erro operacional nos dados de entrada."
        page.update()

    # --- ABA EQUAÇÕES CÚBICAS ---
    drop_modelo_cubico = ft.Dropdown(label="Modelo Cúbico", width=300, options=[ft.dropdown.Option("Peng-Robinson (PR)"), ft.dropdown.Option("Soave-Redlich-Kwong (SRK)")])
    drop_gas = ft.Dropdown(label="Gás Real", width=300, options=[ft.dropdown.Option("Metano (CH4)"), ft.dropdown.Option("Dióxido Carbono (CO2)")])
    txt_temp_cubico = ft.TextField(label="Temperatura (°C)", width=300, keyboard_type=ft.KeyboardType.NUMBER)
    txt_pres_cubico = ft.TextField(label="Pressão (bar)", width=300, keyboard_type=ft.KeyboardType.NUMBER)
    lbl_res_cubico = ft.Text(value="Aguardando dados para Newton-Raphson", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200, text_align=ft.TextAlign.CENTER)

    def clique_cubico(e):
        if not drop_modelo_cubico.value or not drop_gas.value or not txt_temp_cubico.value or not txt_pres_cubico.value:
            lbl_res_cubico.value = "❌ Preencha todos os campos da aba."
            page.update()
            return
        try:
            Z, v, erro = resolver_fator_z_newton(drop_modelo_cubico.value, drop_gas.value, float(txt_temp_cubico.value), float(txt_pres_cubico.value))
            lbl_res_cubico.value = erro if erro else f"📊 Fator Z: {Z}\n📦 Volume: {v} L/mol"
        except Exception: 
            lbl_res_cubico.value = f"❌ Dados inválidos."
        page.update()

    # --- ABA EQUILÍBRIO (ELV) ---
    drop_elv_modelo = ft.Dropdown(label="Modelo de Atividade", width=300, value="Van Laar", options=[ft.dropdown.Option("Van Laar"), ft.dropdown.Option("Margules")])
    txt_temp_elv = ft.TextField(label="Temperatura do Sistema (°C)", width=300, keyboard_type=ft.KeyboardType.NUMBER)
    txt_x1_elv = ft.TextField(label="Fração líquida do Etanol (x1)", width=300, keyboard_type=ft.KeyboardType.NUMBER)
    lbl_res_elv = ft.Text(value="Aguardando frações molares", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200, text_align=ft.TextAlign.CENTER)

    def clique_elv(e):
        if not drop_elv_modelo.value or not txt_temp_elv.value or not txt_x1_elv.value: 
            lbl_res_elv.value = "❌ Preencha todos os campos molares."
            page.update()
            return
        try:
            P, y1, g1, g2, erro = calcular_elv_binario(drop_elv_modelo.value, float(txt_x1_elv.value), float(txt_temp_elv.value))
            lbl_res_elv.value = erro if erro else f"🧪 P_bolha: {P} bar\n🔹 y1: {y1} | y2: {round(1-y1, 4)}\n🔬 Atividade: γ1={g1} | γ2={g2}"
        except Exception: 
            lbl_res_elv.value = f"❌ Erro físico ou de leitura."
        page.update()

    # --- NAVEGAÇÃO INTERNA ---
    conteudo_interp = ft.Column([ft.Text("Abordagem 1: Interpolação", size=17, weight=ft.FontWeight.BOLD), drop_tipo_interp, txt_temp_interp, txt_pres_interp, ft.Button(content=ft.Text("Executar Interpolação"), width=300, on_click=clique_interpola), ft.Divider(), lbl_res_interp], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=True)
    conteudo_cubico = ft.Column([ft.Text("Abordagem 2: Newton-Raphson", size=17, weight=ft.FontWeight.BOLD), drop_modelo_cubico, drop_gas, txt_temp_cubico, txt_pres_cubico, ft.Button(content=ft.Text("Resolver"), width=300, on_click=clique_cubico), ft.Divider(), lbl_res_cubico], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)
    conteudo_elv = ft.Column([ft.Text("Módulo 3: ELV Binário", size=17, weight=ft.FontWeight.BOLD), drop_elv_modelo, txt_temp_elv, txt_x1_elv, ft.Button(content=ft.Text("Calcular ELV"), width=300, on_click=clique_elv), ft.Divider(), lbl_res_elv], horizontal_alignment=ft.CrossAxisAlignment.CENTER, visible=False)

    def nav_1(e):
        conteudo_interp.visible, conteudo_cubico.visible, conteudo_elv.visible = True, False, False
        page.update()
    def nav_2(e):
        conteudo_interp.visible, conteudo_cubico.visible, conteudo_elv.visible = False, True, False
        page.update()
    def nav_3(e):
        conteudo_interp.visible, conteudo_cubico.visible, conteudo_elv.visible = False, False, True
        page.update()

    nav_bar = ft.Row([
        ft.Button(content=ft.Text("Interpolação"), on_click=nav_1),
        ft.Button(content=ft.Text("Cúbicas (NR)"), on_click=nav_2),
        ft.Button(content=ft.Text("ELV Binário"), on_click=nav_3),
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)

    page.add(ft.Container(content=ft.Column([ft.Text("Núcleo Computacional - TCC2", size=22, weight=ft.FontWeight.BOLD), nav_bar, ft.Divider(), conteudo_interp, conteudo_cubico, conteudo_elv], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=10))

if __name__ == "__main__":
    ft.run(main)
