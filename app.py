import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import os

# Configuração da Página
st.set_page_config(page_title="CheckList Pro", page_icon="🚜", layout="wide")

# Arquivo para salvar os dados (Histórico)
DB_FILE = "historico_inspecoes.csv"

def salvar_dados(dados):
    df_novo = pd.DataFrame([dados])
    if not os.path.isfile(DB_FILE):
        df_novo.to_csv(DB_FILE, index=False)
    else:
        df_novo.to_csv(DB_FILE, mode='a', header=False, index=False)

# Interface
st.title("🚜 Sistema de Inspeção de Máquinas")

aba1, aba2 = st.tabs(["📋 Nova Inspeção", "📜 Histórico de Não Conformidades"])

with aba1:
    st.header("Checklist Diário")
    
    with st.form("form_inspecao", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            nome = st.text_input("👤 Funcionário")
        with col2:
            maquina = st.selectbox("🚜 Máquina", [
                "01 - Travel 75", "02 - Travel 35", "03 - Trator Massey Ferguson",
                "04 - Trator Valtra 100", "05 - Trator Valtra 100", 
                "06 - Empilhadeira Zenshin", "07 - Plataforma Snocker", 
                "23 - Empilhadeira Liugong"
            ])
        with col3:
            horimetro = st.number_input("⏲️ Horímetro", min_value=0.0, step=0.1)

        st.divider()
        
        itens = ["NÍVEL DE ÓLEO DO CARTER", "ÓLEO HIDRÁULICO", "NÍVEL DE ÁGUA DO RADIADOR", 
                 "PRESSÃO E ESTADO DOS PNEUS", "FUNCIONAMENTO DO FREIO ESTACIONÁRIO", 
                 "INSTRUMENTOS DO PAINEL", "VAZAMENTO DE COMBUSTÍVEL", "SISTEMA DE DIREÇÃO", 
                 "FUNCIONAMENTO DO MOTOR", "CORREIA DO VENTILADOR", "BUZINA", 
                 "FARÓIS E LANTERNAS", "CARGA EXTINTOR", "LIMPEZA GERAL", 
                 "PINTURA/AVARIAS", "GARRAS E GARFOS", "DESLOCADORES DAS CINTAS"]
        
        respostas = {}
        cols = st.columns(2)
        for i, item in enumerate(itens):
            with cols[i % 2]:
                respostas[item] = st.radio(item, ["OK", "NÃO OK", "N/A"], horizontal=True)

        btn_finalizar = st.form_submit_button("🏁 FINALIZAR INSPEÇÃO")

    if btn_finalizar:
        if not nome:
            st.error("⚠️ Por favor, informe o nome do funcionário.")
        else:
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
            falhas = [item for item, status in respostas.items() if status == "NÃO OK"]
            status_geral = "🔴 NÃO CONFORMIDADE" if falhas else "🟢 OK"
            
            # Preparar dados para salvar
            dados_registro = {
                "Data": data_atual,
                "Funcionário": nome,
                "Máquina": maquina,
                "Horímetro": horimetro,
                "Status": status_geral,
                "Falhas": ", ".join(falhas) if falhas else "Nenhuma"
            }
            salvar_dados(dados_registro)
            
            if falhas:
                st.warning(f"Inspeção Finalizada. Foram encontradas {len(falhas)} não conformidades.")
            else:
                st.success("Inspeção Finalizada. Tudo em ordem!")

            # --- OPÇÕES DE ENVIO ---
            st.write("### 📲 Enviar Relatório")
            
            msg_texto = f"🚨 *ALERTA DE INSPEÇÃO* 🚨\n\n"
            msg_texto += f"*Status:* {status_geral}\n"
            msg_texto += f"*Máquina:* {maquina}\n"
            msg_texto += f"*Funcionário:* {nome}\n"
            msg_texto += f"*Horímetro:* {horimetro}h\n"
            if falhas:
                msg_texto += f"\n*FALHAS DETECTADAS:*\n"
                for f in falhas: msg_texto += f"❌ {f}\n"

            col_zap, col_email = st.columns(2)
            
            # WhatsApp
            texto_zap = urllib.parse.quote(msg_texto)
            url_zap = f"https://api.whatsapp.com/send?text={texto_zap}"
            col_zap.link_button("Compartilhar no WhatsApp", url_zap, use_container_width=True, type="primary")

            # E-mail
            assunto = urllib.parse.quote(f"Relatório de Inspeção - {maquina}")
            corpo_email = urllib.parse.quote(msg_texto)
            url_email = f"mailto:?subject={assunto}&body={corpo_email}"
            col_email.link_button("Enviar por E-mail", url_email, use_container_width=True)

with aba2:
    st.header("Histórico de Não Conformidades")
    
    if os.path.exists(DB_FILE):
        df_hist = pd.read_csv(DB_FILE)
        df_hist['Data'] = pd.to_datetime(df_hist['Data'])
        
        # Filtros
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            data_inicio = st.date_input("De:", value=datetime.now().replace(day=1))
        with col_f2:
            data_fim = st.date_input("Até:", value=datetime.now())
            
        # Aplicar Filtros (Apenas Não Conformidades e por Data)
        mask = (
            (df_hist['Status'] == "🔴 NÃO CONFORMIDADE") & 
            (df_hist['Data'].dt.date >= data_inicio) & 
            (df_hist['Data'].dt.date <= data_fim)
        )
        df_filtrado = df_hist.loc[mask].sort_values(by="Data", ascending=False)
        
        if not df_filtrado.empty:
            st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
            
            # Botão para baixar histórico filtrado
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar Excel (CSV)", csv, "historico_falhas.csv", "text/csv")
        else:
            st.info("Nenhuma não conformidade encontrada no período selecionado.")
    else:
        st.info("Ainda não existem registros de inspeção.")
