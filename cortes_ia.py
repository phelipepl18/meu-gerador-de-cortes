import streamlit as st
from moviepy.editor import VideoFileClip
from groq import Groq
import os
import gc

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Cortes Virais Grátis (Groq)", layout="wide")

# 2. CONEXÃO COM A GROQ
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("⚠️ Erro: Configure GROQ_API_KEY nos Secrets do Streamlit!")

st.title("🚀 Gerador de Cortes Virais (Versão Grátis)")

# 3. UPLOAD
uploaded_file = st.file_uploader("Suba seu vídeo", type=["mp4", "mov", "avi"])

if uploaded_file:
    temp_path = "video_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Análise de Inteligência")
        if st.button("Analisar Momentos Virais (Grátis)"):
            with st.spinner("Groq transcrevendo e analisando..."):
                try:
                    # Extrair Áudio
                    clip = VideoFileClip(temp_path)
                    clip.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    
                    # Transcrever com Whisper na Groq
                    with open("audio_temp.mp3", "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            file=("audio_temp.mp3", audio_file.read()),
                            model="whisper-large-v3",
                            response_format="text"
                        )
                    
                    # Analisar Momentos com Llama 3 na Groq
                    prompt = f"Analise o texto abaixo e me dê os 3 momentos mais virais. Para cada um, dê o tempo inicial e final em segundos e um motivo. Texto: {transcription}"
                    
                    chat_completion = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama3-8b-8192",
                    )
                    
                    st.session_state['analise'] = chat_completion.choices[0].message.content
                    st.session_state['texto'] = transcription
                    clip.close()
                    os.remove("audio_temp.mp3")
                except Exception as e:
                    st.error(f"Erro no processamento: {e}")

        if 'analise' in st.session_state:
            st.success("🎯 Sugestões da IA:")
            st.write(st.session_state['analise'])

    with col2:
        st.subheader("2. Gerar Vídeo")
        st_t = st.number_input("Início (seg)", value=0.0)
        en_t = st.number_input("Fim (seg)", value=15.0)
        
        if st.button("Cortar e Converter 9:16"):
            with st.spinner("Gerando vídeo vertical..."):
                try:
                    video = VideoFileClip(temp_path).subclip(st_t, en_t)
                    
                    # Ajuste 9:16 Par
                    w, h = video.size
                    target_w = int(h * (9/16))
                    if target_w % 2 != 0: target_w -= 1
                    
                    final = video.crop(x_center=w/2, width=target_w, height=h)
                    
                    out = "corte_final.mp4"
                    final.write_videofile(
                        out, codec="libx264", audio_codec="aac",
                        bitrate="3000k", fps=24, preset="ultrafast",
                        ffmpeg_params=["-pix_fmt", "yuv420p"]
                    )
                    
                    st.video(out)
                    with open(out, "rb") as f:
                        st.download_button("⬇️ Baixar Vídeo", f, file_name="corte.mp4")
                    
                    video.close()
                    final.close()
                    gc.collect()
                except Exception as e:
                    st.error(f"Erro: {e}")

# 4. ATUALIZAR REQUIREMENTS
# Importante: No seu arquivo requirements.txt, adicione a linha: groq
