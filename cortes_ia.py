import streamlit as st
from moviepy.editor import VideoFileClip
from groq import Groq
import os
import gc

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Cortes Virais", layout="wide")

# 2. CONEXÃO COM A GROQ
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("⚠️ Erro: Configure GROQ_API_KEY nos Secrets!")

st.title("🚀 Estrategista de Cortes Virais")

# 3. UPLOAD DO VÍDEO
uploaded_file = st.file_uploader("Suba seu vídeo original", type=["mp4", "mov", "avi"])

if uploaded_file:
    # Salva o arquivo fisicamente para o MoviePy não se perder
    temp_path = "video_original_temp.mp4"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Análise da IA")
        if st.button("Analisar Momentos Virais"):
            with st.spinner("IA analisando..."):
                try:
                    clip_audio = VideoFileClip(temp_path)
                    clip_audio.audio.write_audiofile("audio_temp.mp3", codec='libmp3lame')
                    
                    with open("audio_temp.mp3", "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            file=("audio_temp.mp3", audio_file.read()),
                            model="whisper-large-v3-turbo",
                            response_format="text"
                        )
                    
                    prompt = f"Analise o texto e dê 3 sugestões de cortes com tempo de início e fim em segundos: {transcription}"
                    
                    chat_completion = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.1-8b-instant",
                    )
                    
                    st.session_state['analise_viral'] = chat_completion.choices[0].message.content
                    clip_audio.close()
                    os.remove("audio_temp.mp3")
                except Exception as e:
                    st.error(f"Erro na análise: {e}")

        if 'analise_viral' in st.session_state:
            st.success("🎯 Sugestões da IA:")
            st.write(st.session_state['analise_viral'])

    with col2:
        st.subheader("2. Gerar o Corte")
        
        # Usamos chaves (keys) para garantir que o Streamlit capture o valor certo
        t_inicio = st.number_input("Início exato (segundos)", min_value=0.0, step=0.1, key="start_val")
        t_fim = st.number_input("Fim exato (segundos)", min_value=0.1, step=0.1, key="end_val")
        
        if st.button("Cortar Vídeo Agora"):
            if t_fim <= t_inicio:
                st.error("O tempo de fim deve ser maior que o de início!")
            else:
                with st.spinner(f"Cortando de {t_inicio}s até {t_fim}s..."):
                    try:
                        # Forçamos a recarga do clipe para garantir o tempo limpo
                        with VideoFileClip(temp_path) as video_full:
                            # O segredo está aqui: subclip(inicio, fim)
                            video_cut = video_full.subclip(t_inicio, t_fim)
                            
                            # Ajuste 9:16 (Par)
                            w, h = video_cut.size
                            target_w = int(h * (9/16))
                            if target_w % 2 != 0: target_w -= 1
                            
                            final_video = video_cut.crop(x_center=w/2, width=target_w, height=h)
                            
                            output_name = "resultado_corte.mp4"
                            final_video.write_videofile(
                                output_name,
                                codec="libx264",
                                audio_codec="aac",
                                bitrate="3000k",
                                fps=24,
                                preset="ultrafast",
                                ffmpeg_params=["-pix_fmt", "yuv420p"]
                            )

                            st.video(output_name)
                            with open(output_name, "rb") as f:
                                st.download_button("⬇️ Baixar Corte", f, file_name="corte.mp4")
                            
                            # Fechar tudo para liberar o arquivo
                            final_video.close()
                            video_cut.close()
                            gc.collect()

                    except Exception as e:
                        st.error(f"Erro ao processar: {e}")

# Limpeza de segurança
if os.path.exists("resultado_corte.mp4") and not uploaded_file:
    os.remove("resultado_corte.mp4")
