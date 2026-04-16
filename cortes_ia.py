import streamlit as st
from moviepy.editor import VideoFileClip
import os

# Configuração da página
st.set_page_config(page_title="Gerador de Cortes Virais", layout="centered")

st.title("✂️ Criador de Cortes Virais")
st.subheader("Transforme vídeos longos em Reels/TikTok em segundos")

# Upload do arquivo
uploaded_file = st.file_uploader("Escolha um vídeo de até 5 min", type=["mp4", "mov", "avi"])

if uploaded_file is not None:
    # Salva o arquivo temporariamente
    with open("temp_video.mp4", "wb") as f:
        f.write(uploaded_file.read())
    
    video = VideoFileClip("temp_video.mp4")
    duration = video.duration
    
    st.write(f"Duração original: {duration:.2f} segundos")

    # Seleção do trecho
    st.divider()
    start_time = st.number_input("Início do corte (segundos)", min_value=0.0, max_value=duration, value=0.0)
    end_time = st.number_input("Fim do corte (segundos)", min_value=0.0, max_value=duration, value=min(duration, 60.0))

    if st.button("Gerar Vídeo Viral"):
        with st.spinner("Processando... Isso pode levar um tempinho."):
            # 1. Cortar o tempo
            clip = video.subclip(start_time, end_time)
            
            # 2. Lógica de Redimensionamento para Vertical (9:16)
            w, h = clip.size
            target_ratio = 9/16
            target_w = h * target_ratio
            
            # Centraliza o corte no meio do vídeo
            final_clip = clip.crop(x_center=w/2, width=target_w, height=h)
            
            # 3. Salvar o resultado
            output_path = "corte_viral.mp4"
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
            
            st.success("Corte concluído!")
            st.video(output_path)
            
            # Botão de download
            with open(output_path, "rb") as file:
                st.download_button(
                    label="Baixar Vídeo para o Celular",
                    data=file,
                    file_name="meu_video_viral.mp4",
                    mime="video/mp4"
                )
    
    # Limpeza básica (opcional)
    video.close()
