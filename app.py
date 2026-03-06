import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import os
from io import BytesIO

# Bibliotecas para geração de PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CheckList Pro Máquinas", page_icon="🚜", layout="wide")

DB_FILE = "historico_inspecoes.csv"

# --- FUNÇÕES DE APOIO ---
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
    
    elements.append(Paragraph("RELATÓRIO DE NÃO CONFORMIDADES", styles['Title']))
    elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    df_pdf = df[['Data', 'Máquina', 'Funcionário', 'Falhas']]
    data = [df_pdf.columns.to_list()] + df_pdf.values.tolist()
    
    t = Table(data, colWidths=[90, 100, 100, 250])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(t)
    doc.build(elements)
    return output.getvalue()

# --- INTERFACE PRINCIPAL ---
st.title("🚜 CheckList de Máquinas Pro")

aba1, aba2 = st.tabs(["📋 Nova Inspeção", "📜 Histórico de Falhas"])

# --- ABA 1: NOVA INSPEÇÃO ---
with aba1:
    st.header("Formulário de Inspeção Diária")
    
    # Usamos o state para controlar se a inspeção foi finalizada e mostrar os botões de envio
    if 'finalizado' not in st.session_state:
        st.session_state.finalizado = False

    if not st.session_state.finalizado:
        with st.form("form_inspecao", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                nome = st.text_input("👤 Funcionário", placeholder="Nome completo")
            with col2:
                maquina = st.selectbox("🚜 Máquina", [
                    "01 - Travel 75", "02 - Travel 35", "03 - Trator Massey Ferguson",
                    "04 - Trator Valtra 100", "05 - Trator Valtra 100", 
                    "06 - Empilhadeira Zenshin", "07 - Plataforma Snocker", 
                    "23 - Empilhadeira Liugong"
                ])
            with col3:
                horimetro = st.number_input("⏲️ Horímetro Atual", min_value=0.0, step=0.1)

            st.divider()
            itens = ["NÍVEL DE ÓLEO DO CARTER", "ÓLEO HIDRÁULICO", "NÍVEL DE ÁGUA DO RADIADOR", 
                     "PRESSÃO E ESTADO DOS PNEUS", "FUNCIONAMENTO DO FREIO ESTACIONÁRIO", 
                     "INSTRUMENTOS DO PAINEL", "VAZAMENTO DE COMBUSTÍVEL", "SISTEMA DE DIREÇÃO", 
                     "FUNCIONAMENTO DO MOTOR", "CORREIA DO VENTILADOR", "BUZINA", 
                     "FARÓIS E LANTERNAS", "CARGA EXTINTOR", "LIMPEZA GERAL", 
                     "PINTURA/AVARIAS", "GARRAS E GARFOS", "DESLOCADORES DAS CINTAS"]
            
            respostas = {}
            c_itens1, c_itens2 = st.columns(2)
            for i, item in enumerate(itens):
                target_col = c_itens1 if i % 2 == 0 else c_itens2
                respostas[item] = target_col.radio(item, ["OK", "NÃO OK", "N/A"], horizontal=True, key=f"inspec_{i}")

            btn_finalizar = st.form_submit_button("🏁 FINALIZAR INSPEÇÃO")

            if btn_finalizar:
                if not nome:
                    st.error("⚠️ Digite o nome do funcionário.")
                else:
                    data_inspecao = datetime.now().strftime("%Y-%m-%d %H:%M")
                    falhas_lista = [item for item, status in respostas.items() if status == "NÃO OK"]
                    status_txt = "🔴 NÃO CONFORMIDADE" if falhas_lista else "🟢 OK"
                    
                    dados_final = {
                        "Data": data_inspecao, "Funcionário": nome, "Máquina": maquina,
                        "Horímetro": horimetro, "Status": status_txt,
                        "Falhas": ", ".join(falhas_lista) if falhas_lista else "Nenhuma"
                    }
                    salvar_dados(dados_final)
                    
                    # Armazena dados no session_state para exibir após o submit
                    st.session_state.dados_ultima = dados_final
                    st.session_state.msg_wa = f"📋 *RELATÓRIO: {maquina}*\nStatus: {status_txt}\nFunc: {nome}\nHor: {horimetro}h" + (f"\n❌ Falhas: {', '.join(falhas_lista)}" if falhas_lista else "")
                    st.session_state.finalizado = True
                    st.rerun()

    else:
        # TELA DE PÓS-FINALIZAÇÃO
        res = st.session_state.dados_ultima
        if "🔴" in res['Status']:
            st.warning(f"### ⚠️ Inspeção Finalizada: {res['Status']}")
            st.write(f"**Falhas:** {res['Falhas']}")
        else:
            st.success(f"### ✅ Inspeção Finalizada: {res['Status']}")

        st.write("---")
        st.subheader("📤 Compartilhar Relatório")
        c1, c2 = st.columns(2)
        c1.link_button("📲 WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(st.session_state.msg_wa)}", use_container_width=True, type="primary")
        c2.link_button("📧 E-mail", f"mailto:?subject=Inspeção {res['Máquina']}&body={urllib.parse.quote(st.session_state.msg_wa)}", use_container_width=True)
        
        st.write("---")
        if st.button("➕ INICIAR NOVA INSPEÇÃO", use_container_width=True):
            st.session_state.finalizado = False
            st.rerun()

# --- ABA 2: HISTÓRICO ---
with aba2:
    st.header("Histórico de Não Conformidades")
    if os.path.exists(DB_FILE):
        df_hist = pd.read_csv(DB_FILE)
        df_hist['Data'] = pd.to_datetime(df_hist['Data'])
        
        col_data1, col_data2 = st.columns(2)
        data_ini = col_data1.date_input("Data Inicial", value=datetime.now().replace(day=1))
        data_fim = col_data2.date_input("Data Final", value=datetime.now())
        
        mask = (df_hist['Status'] == "🔴 NÃO CONFORMIDADE") & (df_hist['Data'].dt.date >= data_ini) & (df_hist['Data'].dt.date <= data_fim)
        df_filtrado = df_hist.loc[mask].sort_values(by="Data", ascending=False)
        
        if not df_filtrado.empty:
            df_view = df_filtrado.copy()
            df_view['Data'] = df_view['Data'].dt.strftime('%d/%m/%Y %H:%M')
            st.dataframe(df_view, use_container_width=True, hide_index=True)
            
            st.divider()
            c_pdf, c_mail = st.columns(2)
            pdf_bytes = gerar_pdf(df_view)
            c_pdf.download_button("📄 GERAR PDF", pdf_bytes, "historico.pdf", "application/pdf", use_container_width=True)
            
            corpo_mail = f"Resumo de Falhas ({data_ini} a {data_fim}):\n" + "\n".join([f"- {r['Data']}: {r['Máquina']} ({r['Falhas']})" for _, r in df_view.iterrows()])
            c_mail.link_button("📧 Enviar por E-mail", f"mailto:?subject=Relatorio de Falhas&body={urllib.parse.quote(corpo_mail)}", use_container_width=True)
    else:
        st.info("Nenhum registro encontrado.")
