import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import os
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Configuração da Página
st.set_page_config(page_title="CheckList Pro", page_icon="🚜", layout="wide")

DB_FILE = "historico_inspecoes.csv"

def salvar_dados(dados):
    df_novo = pd.DataFrame([dados])
    if not os.path.isfile(DB_FILE):
        df_novo.to_csv(DB_FILE, index=False)
    else:
        df_novo.to_csv(DB_FILE, mode='a', header=False, index=False)

def gerar_pdf(df):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título do PDF
    elements.append(Paragraph(f"Relatório de Não Conformidades - {datetime.now().strftime('%d/%m/%Y')}", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Preparar Dados da Tabela
    data = [df.columns.to_list()] + df.values.tolist()
    
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    doc.build(elements)
    return output.getvalue()

# Interface Principal
st.title("🚜 Sistema de Inspeção de Máquinas")

aba1, aba2 = st.tabs(["📋 Nova Inspeção", "📜 Histórico de Não Conformidades"])

with aba1:
    st.header("Checklist Diário")
    with st.form("form_inspecao", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1: nome = st.text_input("👤 Funcionário")
        with col2: maquina = st.selectbox("🚜 Máquina", ["01 - Travel 75", "02 - Travel 35", "03 - Trator Massey Ferguson", "04 - Trator Valtra 100", "05 - Trator Valtra 100", "06 - Empilhadeira Zenshin", "07 - Plataforma Snocker", "23 - Empilhadeira Liugong"])
        with col3: horimetro = st.number_input("⏲️ Horímetro", min_value=0.0, step=0.1)

        st.divider()
        itens = ["NÍVEL DE ÓLEO DO CARTER", "ÓLEO HIDRÁULICO", "NÍVEL DE ÁGUA DO RADIADOR", "PRESSÃO E ESTADO DOS PNEUS", "FUNCIONAMENTO DO FREIO ESTACIONÁRIO", "INSTRUMENTOS DO PAINEL", "VAZAMENTO DE COMBUSTÍVEL", "SISTEMA DE DIREÇÃO", "FUNCIONAMENTO DO MOTOR", "CORREIA DO VENTILADOR", "BUZINA", "FARÓIS E LANTERNAS", "CARGA EXTINTOR", "LIMPEZA GERAL", "PINTURA/AVARIAS", "GARRAS E GARFOS", "DESLOCADORES DAS CINTAS"]
        
        respostas = {}
        cols = st.columns(2)
        for i, item in enumerate(itens):
            with cols[i % 2]: respostas[item] = st.radio(item, ["OK", "NÃO OK", "N/A"], horizontal=True)

        btn_finalizar = st.form_submit_button("🏁 FINALIZAR INSPEÇÃO")

    if btn_finalizar:
        if not nome:
            st.error("⚠️ Por favor, informe o nome do funcionário.")
        else:
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
            falhas = [item for item, status in respostas.items() if status == "NÃO OK"]
            status_geral = "🔴 NÃO CONFORMIDADE" if falhas else "🟢 OK"
            
            dados_registro = {"Data": data_atual, "Funcionário": nome, "Máquina": maquina, "Horímetro": horimetro, "Status": status_geral, "Falhas": ", ".join(falhas) if falhas else "Nenhuma"}
            salvar_dados(dados_registro)
            
            st.info("Inspeção Processada!")
            
            # Opções de Envio Imediato
            msg_texto = f"🚨 *INSPEÇÃO FINALIZADA* 🚨\n\nStatus: {status_geral}\nMáquina: {maquina}\nFuncionário: {nome}\nHorímetro: {horimetro}h"
            if falhas:
                msg_texto += f"\n\n*FALHAS:* " + ", ".join(falhas)

            c1, c2 = st.columns(2)
            c1.link_button("📲 WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg_texto)}", use_container_width=True)
            c2.link_button("📧 E-mail", f"mailto:?subject=Inspeção {maquina}&body={urllib.parse.quote(msg_texto)}", use_container_width=True)

with aba2:
    st.header("Relatório de Ocorrências")
    if os.path.exists(DB_FILE):
        df_hist = pd.read_csv(DB_FILE)
        df_hist['Data'] = pd.to_datetime(df_hist['Data'])
        
        col_f1, col_f2 = st.columns(2)
        data_inicio = col_f1.date_input("Início:", value=datetime.now().replace(day=1))
        data_fim = col_f2.date_input("Fim:", value=datetime.now())
            
        mask = (df_hist['Status'] == "🔴 NÃO CONFORMIDADE") & (df_hist['Data'].dt.date >= data_inicio) & (df_hist['Data'].dt.date <= data_fim)
        df_filtrado = df_hist.loc[mask].sort_values(by="Data", ascending=False)
        
        if not df_filtrado.empty:
            # Formata data para exibição
            df_display = df_filtrado.copy()
            df_display['Data'] = df_display['Data'].dt.strftime('%d/%m/%Y %H:%M')
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            st.divider()
            col_down, col_mail = st.columns(2)
            
            # Botão PDF
            pdf_data = gerar_pdf(df_display)
            col_down.download_button("📄 Gerar PDF do Histórico", pdf_data, f"historico_falhas_{data_inicio}.pdf", "application/pdf", use_container_width=True)
            
            # Botão E-mail do Histórico
            texto_email_hist = f"Resumo de Não Conformidades ({data_inicio} a {data_fim}):\n\n"
            for _, row in df_display.iterrows():
                texto_email_hist += f"- {row['Data']} | {row['Máquina']} | Falhas: {row['Falhas']}\n"
            
            url_email_hist = f"mailto:?subject=Relatorio de Falhas Periodo {data_inicio}&body={urllib.parse.quote(texto_email_hist)}"
            col_mail.link_button("📧 Enviar Histórico por E-mail", url_email_hist, use_container_width=True)
        else:
            st.info("Nenhuma falha registrada neste período.")
    else:
        st.info("Sem histórico disponível.")
