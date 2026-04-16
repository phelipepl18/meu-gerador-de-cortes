import streamlit as st
from moviepy.editor import VideoFileClip
from openai import OpenAI
import os
import gc

# 1. CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira linha de código Streamlit)
st.set_page_config(page_title="Gerador de Cortes Inteligente", layout="wide")

# Estilo para melhorar o visual do player
st.markdown("""
    <style>
    .stVideo {
        width: 100%;
        max-width: 400px;
        margin: auto;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO COM A OPENAI
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error("⚠️ Erro: Chave da OpenAI não encontrada nos Secrets!")

st.title("✂️ Gerador de Cortes Inteligente (Formato 9:16)")
st.write("Suba seu vídeo original (max 500MB recomendados)")

# 3. UPLOAD DO VÍDEO
uploaded_file = st.file_uploader("Escolha o arquivo", type=["mp4", "mov", "avi"])

if uploaded_file:
    # Salva o vídeo temporariamente no servidor
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"Vídeo carregado: {uploaded_file.name} ({uploaded_file.size / 1024 / 1024:.1f} MB)")

    # Divisão da tela em colunas
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Análise da IA")
        if st.button("Transcrever Áudio"):
            with st.spinner("Extraindo áudio e transcrevendo..."):
                try:
                    # Extrai áudio
                    clip_audio = VideoFileClip(temp_path)
                    clip_audio.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    
                    # Manda para OpenAI
                    with open("audio_temp.mp3", "rb") as audio_f:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1", 
                            file=audio_f
                        )
                    st.session_state['transcricao'] = transcript.text
                    st.success("Transcrição concluída!")
                    
                    # Limpeza imediata
                    clip_audio.close()
                    os.remove("audio_temp.mp3")
                except Exception as e:
                    st.error(f"Erro na transcrição: {e}")

        if 'transcricao' in st.session_state:
            st.text_area("Texto transcrito:", st.session_state['transcricao'], height=250)

    with col2:
        st.subheader("2. Criar o Corte")
        start_t = st.number_input("Início (segundos)", min_value=0.0, step=0.5, value=0.0)
        end_t = st.number_input("Fim (segundos)", min_value=0.1, step=0.5, value=15.0)
        
        if st.button("Gerar Clipe Viral (9:16)"):
            with st.spinner("Processando vídeo... Isso pode demorar para arquivos grandes."):
                try:
                    # Carrega o vídeo para corte
                    video = VideoFileClip(temp_path).subclip(start_t, end_t)
                    
                    # AJUSTE PARA FORMATO VERTICAL (Corta as laterais)
                    w, h = video.size
                    target_w = h * (9/16)
                    if w > target_w:
                        video_vertical = video.crop(x_center=w/2, width=target_w, height=h)
                    else:
                        video_vertical = video

                    # SALVAMENTO COM MÁXIMA COMPATIBILIDADE
                    output_name = "corte_final.mp4"
                    video_vertical.write_videofile(
                        output_name,
                        codec="libx264",        # Codec universal
                        audio_codec="aac",      # Codec de áudio padrão Apple
                        bitrate="3000k",        # Reduz o peso para o player do site carregar
                        fps=24,                 # Estabiliza o vídeo
                        preset="ultrafast",     # Evita timeout no servidor
                        threads=4               # Usa mais processamento do servidor
                    )

                    # EXIBE O PLAYER NO SITE
                    st.video(output_name)
                    
                    # BOTÃO DE DOWNLOAD
                    with open(output_name, "rb") as f:
                        st.download_button(
                            label="⬇️ Baixar Vídeo",
                            data=f,
                            file_name="meu_corte_viral.mp4",
                            mime="video/mp4"
                        )
                    
                    # LIMPEZA DE MEMÓRIA (Crucial para não travar o site)
                    video.close()
                    video_vertical.close()
                    gc.collect()

                except Exception as e:
                    st.error(f"Erro ao gerar vídeo: {e}")

# Rodapé informando o limite
st.info("Limite de memória do servidor: 1GB RAM. Tente cortes de no máximo 60 segundos por vez.")
