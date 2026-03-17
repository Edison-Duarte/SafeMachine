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
        nome_aba = "Página 1"  # Nome da aba conforme identificado no seu Google Drive
        try:
            # Tenta ler os dados existentes para concatenar
            df_existente = conn.read(worksheet=nome_aba, ttl=0)
        except:
            df_existente = pd.DataFrame()

        df_novo = pd.DataFrame([dados])

        if df_existente is not None and not df_existente.empty:
            # Remove linhas e colunas fantasmamente vazias
            df_existente = df_existente.dropna(how='all').dropna(axis=1, how='all')
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)
        else:
            df_final = df_novo

        # Salva a tabela atualizada na aba correta
        conn.update(worksheet=nome_aba, data=df_final)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na nuvem: {e}")
        return False

def gerar_pdf(df):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("RELATÓRIO DE INSPEÇÃO DE MÁQUINAS", styles['Title']))
    elements.append(Paragraph(f"Extraído em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Seleciona colunas principais para o PDF
    colunas_pdf = ["Data", "Máquina", "Horímetro", "Status", "Falhas"]
    df_pdf = df[colunas_pdf]
    
    data = [df_pdf.columns.to_list()] + df_pdf.values.tolist()
    
    t = Table(data, colWidths=[80, 100, 60, 90, 200])
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
st.title("🚜 CheckList Pro - Gestão de Frota")

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
            horimetro_val = col3.number_input("⏲️ Horímetro Atual", min_value=0.0, step=0.1)
            
            st.divider()
            itens = [
                "NÍVEL DE ÓLEO", "ÓLEO HIDRÁULICO", "ÁGUA RADIADOR", "PNEUS", 
                "FREIO ESTACIONÁRIO", "PAINEL", "VAZAMENTO COMBUSTÍVEL", "DIREÇÃO", 
                "MOTOR", "CORREIA", "BUZINA", "FARÓIS", "EXTINTOR", "LIMPEZA", 
                "AVARIAS", "GARRAS/GARFOS", "CINTAS"
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
                        "Horímetro": horimetro_val,
                        "Status": status,
                        "Falhas": ", ".join(falhas) if falhas else "Nenhuma"
                    }
                    
                    with st.spinner("Gravando na planilha..."):
                        if salvar_no_google(dados):
                            st.session_state.dados_ultima = dados
                            st.session_state.finalizado = True
                            st.rerun()
                else:
                    st.error("Por favor, informe o nome do funcionário.")
    else:
        res = st.session_state.dados_ultima
        st.success(f"Dados salvos! Máquina: {res['Máquina']} | Horímetro: {res['Horímetro']}")
        
        c1, c2 = st.columns(2)
        msg_wa = f"📋 *RELATÓRIO: {res['Máquina']}*\nStatus: {res['Status']}\nHorímetro: {res['Horímetro']}\nFunc: {res['Funcionário']}\nFalhas: {res['Falhas']}"
        c1.link_button("📲 Enviar via WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg_wa)}", use_container_width=True)
        
        if st.button("➕ REALIZAR NOVA INSPEÇÃO", use_container_width=True):
            st.session_state.finalizado = False
            st.rerun()

with aba2:
    st.header("📊 Histórico Permanente")
    try:
        df_cloud = conn.read(worksheet="Página 1", ttl=0)
        
        if df_cloud is not None and not df_cloud.empty:
            df_cloud['Data_DT'] = pd.to_datetime(df_cloud['Data'], format='%d/%m/%Y %H:%M', errors='coerce')
            
            # --- FILTROS ---
            f1, f2, f3, f4 = st.columns(4)
            d_ini = f1.date_input("Início", value=datetime.now().replace(day=1), key="d_i")
            d_fim = f2.date_input("Fim", value=datetime.now(), key="d_f")
            status_f = f3.selectbox("Status", ["Todos", "🟢 OK", "🔴 NÃO CONFORMIDADE"])
            maquina_f = f4.selectbox("Máquina", ["Todas"] + sorted(df_cloud['Máquina'].unique().tolist()))
            
            # --- APLICAÇÃO ---
            mask = (df_cloud['Data_DT'].dt.date >= d_ini) & (df_cloud['Data_DT'].dt.date <= d_fim)
            if status_f != "Todos":
                mask = mask & (df_cloud['Status'] == status_f)
            if maquina_f != "Todas":
                mask = mask & (df_cloud['Máquina'] == maquina_f)
            
            df_filtrado = df_cloud.loc[mask].sort_values(by="Data_DT", ascending=False)
            
            if not df_filtrado.empty:
                df_view = df_filtrado.drop(columns=['Data_DT']).copy()
                st.dataframe(df_view, use_container_width=True, hide_index=True)
                
                st.divider()
                c_pdf, c_csv, c_mail = st.columns(3)
                
                # PDF
                pdf_bytes = gerar_pdf(df_view)
                c_pdf.download_button("📄 Baixar PDF", pdf_bytes, "relatorio.pdf", "application/pdf", use_container_width=True)
                
                # CSV
                csv_data = df_view.to_csv(index=False).encode('utf-8')
                c_csv.download_button("📥 Baixar CSV (Excel)", csv_data, "historico.csv", "text/csv", use_container_width=True)
                
                # E-MAIL
                corpo_email = f"Relatório de Inspeções:\n\n"
                for _, r in df_view.iterrows():
                    corpo_email += f"- {r['Data']} | {r['Máquina']} (H: {r['Horímetro']}) | {r['Status']}\n"
                
                c_mail.link_button("📧 Enviar por E-mail", f"mailto:?subject=Relatorio&body={urllib.parse.quote(corpo_email)}", use_container_width=True)
            else:
                st.info("Nenhum dado encontrado para os filtros aplicados.")
    except Exception as e:
        st.warning("Aguardando conexão com a planilha ou planilha vazia.")
