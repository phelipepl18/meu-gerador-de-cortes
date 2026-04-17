import streamlit as st
from moviepy.editor import VideoFileClip, clips_array, ImageClip, CompositeVideoClip, ColorClip
from groq import Groq
import os
import gc
import json
from PIL import Image, ImageDraw, ImageFont

# --- CORREÇÃO PARA ERRO DE REDIMENSIONAMENTO (ANTIALIAS) ---
import PIL.Image
if not hasattr(PIL.Image, 'Resampling'):
    PIL.Image.LANCZOS = PIL.Image.ANTIALIAS
else:
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    PIL.Image.LANCZOS = PIL.Image.Resampling.LANCZOS

st.set_page_config(page_title="Gerador Automático de Cortes Virais", layout="wide")

# Conexão Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Configure a GROQ_API_KEY nos Secrets do Streamlit!")

def criar_imagem_texto(texto, largura=1080):
    img = Image.new('RGBA', (largura, 250), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()
    
    w_txt, h_txt = draw.textbbox((0, 0), texto.upper(), font=font)[2:4]
    draw.text(((largura - w_txt) / 2, (250 - h_txt) / 2), texto.upper(), font=font, fill="white")
    path = f"titulo_{hash(texto)}.png"
    img.save(path)
    return path

def processar_corte(video_path, bg_path, start, end, tema, output_name):
    with VideoFileClip(video_path) as video:
        clip = video.subclip(start, min(end, video.duration))
        
        # 1. Preparar Fundo (9:16)
        bg = ImageClip(bg_path).set_duration(clip.duration).resize(height=1920)
        bg = bg.crop(x_center=bg.w/2, y_center=bg.h/2, width=1080, height=1920)
        
        # 2. Vídeo no Centro
        vid_centro = clip.resize(width=1000)
        
        # 3. Tema Forte e Tarja
        path_txt = criar_imagem_texto(tema)
        txt_clip = ImageClip(path_txt).set_duration(clip.duration).set_position(('center', 400))
        tarja = ColorClip(size=(1080, 200), color=(0,0,0)).set_opacity(0.6).set_duration(clip.duration).set_position(('center', 430))
        
        final = CompositeVideoClip([bg, tarja, txt_clip, vid_centro.set_position("center")])
        
        # Garantir dimensões pares
        if final.w % 2 != 0: final = final.margin(right=1)
        if final.h % 2 != 0: final = final.margin(bottom=1)
        
        final.write_videofile(output_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
    return output_name

st.title("🎙️ Gerador Automático de 3 Cortes Virais")

file = st.file_uploader("1. Suba seu vídeo original", type=["mp4", "mov", "avi"])
bg_image = st.file_uploader("2. Suba a imagem de fundo para os cortes", type=["jpg", "jpeg", "png"])

if file and bg_image:
    temp_path = "video_orig.mp4"
    bg_path = "fundo_orig.png"
    
    with open(temp_path, "wb") as f: f.write(file.getbuffer())
    with open(bg_path, "wb") as f: f.write(bg_image.getbuffer())

    if st.button("🚀 Gerar 3 Vídeos Virais Automaticamente"):
        with st.spinner("IA analisando e criando os vídeos... isso pode levar alguns minutos."):
            try:
                # Transcrição
                with VideoFileClip(temp_path) as v_full:
                    v_full.audio.write_audiofile("audio.mp3", codec='libmp3lame', logger=None)
                
                with open("audio.mp3", "rb") as a:
                    trans = client.audio.transcriptions.create(file=("audio.mp3", a.read()), model="whisper-large-v3-turbo", response_format="text")
                
                # IA escolhe os 3 cortes e temas (Pedindo JSON para facilitar o código)
                prompt = (
                    f"Com base neste texto, escolha os 3 momentos mais virais. "
                    f"Retorne APENAS um JSON no formato: "
                    f"[{{\"inicio\": segundos, \"fim\": segundos, \"tema\": \"titulo\"}}, ...]. "
                    f"Texto: {trans}"
                )
                
                res = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.1-8b-instant")
                
                # Tenta extrair o JSON da resposta
                cortes = json.loads(res.choices[0].message.content)
                
                # Gerar os vídeos
                cols = st.columns(3)
                for i, corte in enumerate(cortes[:3]):
                    out_name = f"corte_viral_{i+1}.mp4"
                    processar_corte(temp_path, bg_path, corte['inicio'], corte['fim'], corte['tema'], out_name)
                    
                    with cols[i]:
                        st.success(f"Vídeo {i+1}: {corte['tema']}")
                        st.video(out_name)
                        with open(out_name, "rb") as f:
                            st.download_button(f"Baixar Vídeo {i+1}", f, out_name)
                
                gc.collect()
            except Exception as e:
                st.error(f"Ocorreu um erro: {e}. Certifique-se de que a IA retornou o formato correto.")
