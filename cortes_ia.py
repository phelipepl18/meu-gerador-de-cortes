import streamlit as st
from moviepy.editor import VideoFileClip
from openai import OpenAI
import os
import gc  # Para limpeza de memória

# Configuração da página
st.set_page_config(page_title="Corte Viral IA", layout="centered")

# 1. Configuração da IA
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error("Configure sua OPENAI_API_KEY nos Secrets do Streamlit.")

st.title("✂️ Gerador de Cortes Viral (9:16)")

# 2. Upload do arquivo
uploaded_file = st.file_uploader("Suba seu vídeo original", type=["mp4", "mov", "avi"])

if uploaded_file:
    # Salva temporário
    with open("temp_video.mp4", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.info("💡 Dica: Para vídeos grandes, aguarde o processamento sem fechar a página.")

    # Colunas para organizar a tela
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Transcrição")
        if st.button("Analisar Áudio"):
            with st.spinner("IA ouvindo..."):
                try:
                    video = VideoFileClip("temp_video.mp4")
                    video.audio.write_audiofile("temp_audio.mp3", codec='libmp3lame')
                    
                    with open("temp_audio.mp3", "rb") as audio_file:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1", 
                            file=audio_file
                        )
                    st.session_state['texto_final'] = transcript.text
                    video.close() # Libera o arquivo
                except Exception as e:
                    st.error(f"Erro: {e}")

        if 'texto_final' in st.session_state:
            st.text_area("Transcrição:", st.session_state['texto_final'], height=200)

    with col2:
        st.subheader("2. Criar o Corte")
        start_t = st.number_input("Início (seg)", min_value=0.0, value=0.0)
        end_t = st.number_input("Fim (seg)", min_value=0.1, value=10.0)
        
        if st.button("Gerar Vídeo Vertical"):
            with st.spinner("Cortando e Convertendo..."):
                try:
                    # Carrega o vídeo
                    clip = VideoFileClip("temp_video.mp4").subclip(start_t, end_t)
                    
                    # Lógica 9:16 (Vertical)
                    w, h = clip.size
                    target_w = h * (9/16)
                    
                    if w > target_w:
                        final_clip = clip.crop(x_center=w/2, width=target_w, height=h)
                    else:
                        final_clip = clip
                    
                    # CONFIGURAÇÃO DE ALTA COMPATIBILIDADE (Apple/QuickTime)
                    output_path = "corte_final_compativel.mp4"
                    final_clip.write_videofile(
                        output_path, 
                        codec="libx264", 
                        audio_codec="aac", 
                        temp_audiofile='temp-audio.m4a', 
                        remove_temp=True,
                        fps=24, # FPS fixo ajuda na compatibilidade
                        preset="ultrafast" # Processa mais rápido para não travar o servidor
                    )
                    
                    # Exibe no site
                    st.video(output_path)
                    
                    # Botão de Download
                    with open(output_path, "rb") as file:
                        st.download_button(
                            label="⬇️ Baixar Vídeo",
                            data=file,
                            file_name="corte_viral.mp4",
                            mime="video/mp4"
                        )
                    
                    # Limpeza de memória
                    clip.close()
                    final_clip.close()
                    gc.collect() 

                except Exception as e:
                    st.error(f"Erro no processamento: {e}")

# Limpeza de arquivos ao recarregar (opcional)
if os.path.exists("temp_audio.mp3"):
    try: os.remove("temp_audio.mp3")
    except: pass
