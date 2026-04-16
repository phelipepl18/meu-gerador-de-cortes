import streamlit as st
from moviepy.editor import VideoFileClip
from groq import Groq
import os
import gc

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Cortes Virais (Groq)", layout="wide")

# Estilo para centralizar o player
st.markdown("""
    <style>
    .stVideo { width: 100%; max-width: 400px; margin: auto; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO COM A GROQ (Pegue a chave em console.groq.com)
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("⚠️ Erro: Configure GROQ_API_KEY nos Secrets do Streamlit!")

st.title("🚀 Estrategista de Cortes Virais (Grátis)")
st.write("Usando Inteligência Artificial da Groq para análise instantânea.")

# 3. UPLOAD DO VÍDEO
uploaded_file = st.file_uploader("Suba seu vídeo original", type=["mp4", "mov", "avi"])

if uploaded_file:
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"Vídeo carregado: {uploaded_file.name}")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Análise de Retenção (IA)")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("IA transcrevendo e identificando ganchos..."):
                try:
                    # Extração do áudio para transcrição
                    clip_audio = VideoFileClip(temp_path)
                    clip_audio.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    
                    # Transcrição com Whisper na Groq (Modelo Turbo)
                    with open("audio_temp.mp3", "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            file=("audio_temp.mp3", audio_file.read()),
                            model="whisper-large-v3-turbo",
                            response_format="text"
                        )
                    
                    # Sugestão de cortes com Llama 3.1 (Modelo Atualizado)
                    prompt = (
                        f"Analise a transcrição abaixo e identifique os 3 momentos com maior potencial viral. "
                        f"Para cada momento, forneça: \n"
                        f"1. Título chamativo\n"
                        f"2. Tempo de INÍCIO e FIM (em segundos)\n"
                        f"3. Por que esse trecho é bom para o Reels/TikTok.\n\n"
                        f"Transcrição: {transcription}"
                    )
                    
                    chat_completion = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.1-8b-instant",
                    )
                    
                    st.session_state['analise_viral'] = chat_completion.choices[0].message.content
                    st.session_state['transcricao'] = transcription
                    
                    clip_audio.close()
                    if os.path.exists("audio_temp.mp3"):
                        os.remove("audio_temp.mp3")
                        
                except Exception as e:
                    st.error(f"Erro no processamento da IA: {e}")

        if 'analise_viral' in st.session_state:
            st.success("🎯 Sugestões da IA:")
            st.write(st.session_state['analise_viral'])
            with st.expander("Ver transcrição completa"):
                st.write(st.session_state['transcricao'])

    with col2:
        st.subheader("2. Gerar o Vídeo Vertical")
        st.info("Digite os tempos sugeridos pela IA abaixo:")
        
        start_t = st.number_input("Início (segundos)", min_value=0.0, step=0.5, value=0.0)
        end_t = st.number_input("Fim (segundos)", min_value=0.1, step=0.5, value=15.0)
        
        if st.button("Gerar e Converter para 9:16"):
            with st.spinner("Processando corte e ajustando imagem..."):
                try:
                    # Carrega e corta o vídeo
                    video = VideoFileClip(temp_path).subclip(start_t, end_t)
                    
                    # Lógica 9:16 Vertical (Garante dimensões PARES para evitar Erro 32)
                    w, h = video.size
                    target_w = int(h * (9/16))
                    if target_w % 2 != 0:
                        target_w -= 1
                    
                    if w > target_w:
                        video_vertical = video.crop(x_center=w/2, width=target_w, height=h)
                    else:
                        video_vertical = video

                    output_name = "corte_viral.mp4"
                    video_vertical.write_videofile(
                        output_name,
                        codec="libx264",         
                        audio_codec="aac",       
                        bitrate="3000k",         
                        fps=24,                  
                        preset="ultrafast",      
                        threads=4,               
                        ffmpeg_params=["-pix_fmt", "yuv420p"] # Garante imagem no Mac/iPhone
                    )

                    # Player e Download
                    st.video(output_name)
                    with open(output_name, "rb") as f:
                        st.download_button(
                            label="⬇️ Baixar Vídeo Viral",
                            data=f,
                            file_name="meu_corte_viral.mp4",
                            mime="video/mp4"
                        )
                    
                    # Limpeza
                    video.close()
                    video_vertical.close()
                    gc.collect()

                except Exception as e:
                    st.error(f"Erro ao gerar vídeo: {e}")

st.divider()
st.caption("Dica: Se a IA sugerir tempos fora da duração do vídeo, ajuste manualmente os segundos.")
