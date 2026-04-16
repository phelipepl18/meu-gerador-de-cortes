import streamlit as st
from moviepy.editor import VideoFileClip
from openai import OpenAI
import os
import gc

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Cortes Inteligente", layout="wide")

# Estilo para melhorar o visual do player de vídeo
st.markdown("""
    <style>
    .stVideo {
        width: 100%;
        max-width: 400px;
        margin: auto;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO COM A OPENAI (Secrets do Streamlit)
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error("⚠️ Erro: Chave da OpenAI não encontrada nos Secrets!")

st.title("✂️ Gerador de Cortes Inteligente (Formato 9:16)")
st.write("Suba seu vídeo original (recomendado até 500MB para estabilidade)")

# 3. UPLOAD DO ARQUIVO
uploaded_file = st.file_uploader("Escolha o arquivo", type=["mp4", "mov", "avi"])

if uploaded_file:
    # Salva o vídeo temporário no servidor
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"Vídeo carregado com sucesso: {uploaded_file.name}")

    # Organização em colunas
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Análise da IA")
        if st.button("Transcrever Áudio"):
            with st.spinner("IA extraindo e analisando o áudio..."):
                try:
                    # Extração do áudio para transcrição
                    clip_audio = VideoFileClip(temp_path)
                    clip_audio.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    
                    with open("audio_temp.mp3", "rb") as audio_f:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1", 
                            file=audio_f
                        )
                    st.session_state['transcricao'] = transcript.text
                    st.success("Transcrição concluída!")
                    
                    # Limpeza imediata de arquivos de áudio
                    clip_audio.close()
                    if os.path.exists("audio_temp.mp3"):
                        os.remove("audio_temp.mp3")
                except Exception as e:
                    st.error(f"Erro na transcrição: {e}")

        if 'transcricao' in st.session_state:
            st.text_area("Texto transcrito:", st.session_state['transcricao'], height=250)

    with col2:
        st.subheader("2. Criar o Corte")
        start_t = st.number_input("Início do corte (segundos)", min_value=0.0, step=0.5, value=0.0)
        end_t = st.number_input("Fim do corte (segundos)", min_value=0.1, step=0.5, value=15.0)
        
        if st.button("Gerar Clipe Viral (9:16)"):
            with st.spinner("Processando vídeo... Aguarde a finalização."):
                try:
                    # Carrega e corta o vídeo
                    video = VideoFileClip(temp_path).subclip(start_t, end_t)
                    
                    # LÓGICA PARA FORMATO VERTICAL (9:16)
                    w, h = video.size
                    target_w = h * (9/16)
                    if w > target_w:
                        video_vertical = video.crop(x_center=w/2, width=target_w, height=h)
                    else:
                        video_vertical = video

                    # SALVAMENTO COM MÁXIMA COMPATIBILIDADE (Correção de Imagem/Áudio)
                    output_name = "corte_final.mp4"
                    video_vertical.write_videofile(
                        output_name,
                        codec="libx264",         # Codec de vídeo universal
                        audio_codec="aac",       # Codec de áudio compatível com Apple/Navegadores
                        bitrate="3000k",         # Equilíbrio entre qualidade e peso do arquivo
                        fps=24,                  
                        preset="ultrafast",      # Processamento rápido para evitar queda do servidor
                        threads=4,               
                        ffmpeg_params=["-pix_fmt", "yuv420p"] # GARANTE QUE A IMAGEM APAREÇA NO MAC/IPHONE
                    )

                    # EXIBE O VÍDEO NO PLAYER DO SITE
                    st.video(output_name)
                    
                    # BOTÃO DE DOWNLOAD
                    with open(output_name, "rb") as f:
                        st.download_button(
                            label="⬇️ Baixar Vídeo para o Celular",
                            data=f,
                            file_name="meu_corte_viral.mp4",
                            mime="video/mp4"
                        )
                    
                    # LIMPEZA DE MEMÓRIA DO SERVIDOR
                    video.close()
                    video_vertical.close()
                    gc.collect()

                except Exception as e:
                    st.error(f"Erro ao gerar vídeo: {e}")

# Informações de rodapé
st.divider()
st.info("💡 Lembre-se: Vídeos muito grandes podem demorar para carregar no player do site. Se o player ficar preto, tente baixar o vídeo ou usar um corte mais curto para teste.")
