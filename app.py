import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
from io import BytesIO
from streamlit_gsheets import GSheetsConnection

# Bibliotecas para PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CheckList Cloud Pro", page_icon="🚜", layout="wide")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def salvar_no_google(dados):
    try:
        # Lendo a primeira aba disponível (sem especificar nome)
        # ttl=0 é obrigatório para ignorar o cache do Streamlit
        df_existente = conn.read(ttl=0) 
        
        df_novo = pd.DataFrame([dados])

        if df_existente is not None and not df_existente.empty:
            # Garante que não estamos pegando colunas fantasmas
            df_existente = df_existente.dropna(axis=1, how='all').dropna(axis=0, how='all')
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)
        else:
            df_final = df_novo

        # Atualiza a primeira aba disponível
        conn.update(data=df_final)
        return True
    except Exception as e:
        st.error(f"Erro técnico: {e}")
        return False

def gerar_pdf(df):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("RELATÓRIO DE NÃO CONFORMIDADES", styles['Title']))
    elements.append(Paragraph(f"Extraído em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Seleciona apenas colunas existentes para o PDF
    colunas_pdf = [c for c in ['Data', 'Máquina', 'Funcionário', 'Falhas'] if c in df.columns]
    df_pdf = df[colunas_pdf]
    
    data = [df_pdf.columns.to_list()] + df_pdf.values.tolist()
    
    t = Table(data, colWidths=[90, 100, 100, 250])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(t)
    doc.build(elements)
    return output.getvalue()

# --- INTERFACE ---
st.title("🚜 SafeMachine - CheckList")

aba1, aba2 = st.tabs(["📋 Nova Inspeção", "📜 Histórico Cloud"])

with aba1:
    if 'finalizado' not in st.session_state:
        st.session_state.finalizado = False

    if not st.session_state.finalizado:
        with st.form("form_inspecao"):
            col1, col2, col3 = st.columns(3)
            nome = col1.text_input("👤 Funcionário")
            maquina = col2.selectbox("🚜 Máquina", [
                "01 - Travel 75", "02 - Travel 35", "03 - Trator Massey Ferguson", 
                "04 - Trator Valtra 100", "05 - Trator Valtra 100", 
                "06 - Empilhadeira Zenshin", "07 - Plataforma Snocker", "23 - Empilhadeira Liugong"
            ])
            horimetro = col3.number_input("⏲️ Horímetro", min_value=0.0, step=0.1)
            
            st.divider()
            itens = [
                "NÍVEL DE ÓLEO DO CARTER", "ÓLEO HIDRÁULICO", "NÍVEL ÁGUA RADIADOR", "PRESSÃO E ESTADO DOS PNEUS", 
                "FREIO ESTACIONÁRIO", "INSTRUMENTOS DO PAINEL", "VAZAMENTO COMBUSTÍVEL", "SISTEMA DE DIREÇÃO", 
                "FUNCIONAMENTO DO MOTOR", "CORREIA DO VENTILADOR", "BUZINA", "FARÓIS/LANTERNAS", "LIMPEZA GERAL", 
                "PINTURA/AVARIAS", "GARFOS/MACACO", "CINTAS"
            ]
            
            respostas = {}
            c1, c2 = st.columns(2)
            for i, item in enumerate(itens):
                target = c1 if i % 2 == 0 else c2
                respostas[item] = target.radio(item, ["OK", "NÃO OK", "N/A"], horizontal=True, key=f"radio_{i}")

            if st.form_submit_button("🏁 FINALIZAR E SALVAR NA NUVEM"):
                if nome:
                    falhas = [it for it, stt in respostas.items() if stt == "NÃO OK"]
                    status = "🔴 NÃO CONFORMIDADE" if falhas else "🟢 OK"
                    dados = {
                        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Funcionário": nome,
                        "Máquina": maquina,
                        "Horímetro": horimetro,
                        "Status": status,
                        "Falhas": ", ".join(falhas) if falhas else "Nenhuma"
                    }
                    
                    with st.spinner("Conectando ao Google Drive..."):
                        if salvar_no_google(dados):
                            st.session_state.dados_ultima = dados
                            st.session_state.finalizado = True
                            st.rerun()
                else:
                    st.error("Por favor, preencha o nome do funcionário.")
    else:
        res = st.session_state.dados_ultima
        st.success(f"Dados salvos com sucesso na nuvem! Status: {res['Status']}")
        
        c1, c2 = st.columns(2)
        msg_wa = f"📋 *RELATÓRIO: {res['Máquina']}*\nStatus: {res['Status']}\nFunc: {res['Funcionário']}\nFalhas: {res['Falhas']}"
        c1.link_button("📲 WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg_wa)}", use_container_width=True)
        c2.link_button("📧 E-mail", f"mailto:?subject=Inspeção&body={urllib.parse.quote(msg_wa)}", use_container_width=True)
        
        if st.button("➕ NOVA INSPEÇÃO", use_container_width=True):
            st.session_state.finalizado = False
            st.rerun()

with aba2:
    st.header("📊 Histórico Permanente (Google Sheets)")
    
    try:
        # Busca os dados em tempo real
        df_cloud = conn.read(ttl=0)
        
        if df_cloud is not None and not df_cloud.empty:
            # Tratamento de datas para garantir que o filtro funcione
            df_cloud['Data_DT'] = pd.to_datetime(df_cloud['Data'], format='%d/%m/%Y %H:%M', errors='coerce')
            
            # --- ÁREA DE FILTROS ---
            st.subheader("Filtros de Busca")
            f_col1, f_col2 = st.columns(2)
            d_ini = f_col1.date_input("📅 Início", value=datetime.now().replace(day=1), key="hist_ini")
            d_fim = f_col2.date_input("📅 Fim", value=datetime.now(), key="hist_fim")
            
            f_col3, f_col4 = st.columns(2)
            # Filtro de Status
            opcoes_status = ["Todos", "🟢 OK", "🔴 NÃO CONFORMIDADE"]
            filtro_status = f_col3.selectbox("🔍 Filtrar por Status", opcoes_status)
            
            # Filtro de Máquina
            lista_maquinas = ["Todas"] + sorted(df_cloud['Máquina'].unique().tolist())
            filtro_maquina = f_col4.selectbox("🚜 Filtrar por Máquina", lista_maquinas)
            
            # --- APLICAÇÃO DOS FILTROS ---
            mask = (df_cloud['Data_DT'].dt.date >= d_ini) & (df_cloud['Data_DT'].dt.date <= d_fim)
            
            if filtro_status != "Todos":
                mask = mask & (df_cloud['Status'] == filtro_status)
            
            if filtro_maquina != "Todas":
                mask = mask & (df_cloud['Máquina'] == filtro_maquina)
            
            df_filtrado = df_cloud.loc[mask].sort_values(by="Data_DT", ascending=False)
            
            # --- EXIBIÇÃO ---
            if not df_filtrado.empty:
                df_view = df_filtrado.drop(columns=['Data_DT']).copy()
                
                # Métricas
                m1, m2, m3 = st.columns(3)
                m1.metric("Total", len(df_view))
                m2.metric("Falhas", len(df_view[df_view['Status'] == "🔴 NÃO CONFORMIDADE"]))
                m3.metric("Conformes", len(df_view[df_view['Status'] == "🟢 OK"]))
                
                st.divider()
                st.dataframe(df_view, use_container_width=True, hide_index=True)
                
                # --- EXPORTAÇÃO E COMUNICAÇÃO ---
                st.subheader("Exportar e Partilhar")
                c_pdf, c_csv, c_mail = st.columns(3)
                
                # 1. BOTÃO PDF
                pdf_bytes = gerar_pdf(df_view)
                c_pdf.download_button("📄 Gerar PDF", pdf_bytes, "relatorio_inspecoes.pdf", "application/pdf", use_container_width=True)
                
                # 2. BOTÃO CSV (Excel)
                csv_data = df_view.to_csv(index=False).encode('utf-8')
                c_csv.download_button("📥 Baixar CSV", csv_data, "historico_inspecoes.csv", "text/csv", use_container_width=True)
                
                # 3. BOTÃO E-MAIL (Recuperado)
                corpo_email = f"Relatório de Inspeções ({d_ini} a {d_fim}):\n\n"
                for _, r in df_view.iterrows():
                    corpo_email += f"- {r['Data']} | {r['Máquina']} | {r['Status']} | Falhas: {r['Falhas']}\n"
                
                c_mail.link_button("📧 Enviar por E-mail", f"mailto:?subject=Relatorio de Inspecoes&body={urllib.parse.quote(corpo_email)}", use_container_width=True)
            else:
                st.info("Nenhum registro encontrado para estes filtros.")
        else:
            st.info("A planilha está vazia.")
            
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")







