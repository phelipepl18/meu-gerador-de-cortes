import streamlit as st
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, ColorClip
from groq import Groq
import os, gc, json, re, random, time
from PIL import Image, ImageDraw, ImageFont

# --- CORREÇÃO PIL ---
import PIL.Image
if not hasattr(PIL.Image, 'Resampling'):
    PIL.Image.LANCZOS = PIL.Image.ANTIALIAS
else:
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    PIL.Image.LANCZOS = PIL.Image.Resampling.LANCZOS

st.set_page_config(page_title="Estrategista de Cortes", layout="wide")

# Estilização CSS para parecer com a imagem
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #2e77d0; color: white; }
    .stVideo { border-radius: 15px; overflow: hidden; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Configure a GROQ_API_KEY nos Secrets!")

def criar_imagem_texto(texto, largura=1080):
    img = Image.new('RGBA', (largura, 450), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 100)
    except:
        font = ImageFont.load_default()
    
    # Texto em caixa alta e quebra de linha simples se for longo
    texto_formatado = texto.upper()
    w_txt, h_txt = draw.textbbox((0, 0), texto_formatado, font=font)[2:4]
    draw.text(((largura - w_txt) / 2, (450 - h_txt) / 2), texto_formatado, font=font, fill="white", align="center")
    
    path = f"txt_{random.randint(0,9999)}.png"
    img.save(path)
    return path

def processar_corte(video_path, bg_path, start, end, tema, output_name, dur_max):
    start, end = max(0, start), min(end, dur_max)
    with VideoFileClip(video_path) as video:
        clip = video.subclip(start, end)
        bg = ImageClip(bg_path).set_duration(clip.duration).resize(height=1920)
        bg = bg.crop(x_center=bg.w/2, y_center=bg.h/2, width=1080, height=1920)
        vid_centro = clip.resize(width=1000)
        
        path_txt = criar_imagem_texto(tema)
        txt_clip = ImageClip(path_txt).set_duration(clip.duration).set_position(('center', 200))
        tarja = ColorClip(size=(1080, 400), color=(0,0,0)).set_opacity(0.7).set_duration(clip.duration).set_position(('center', 220))
        
        final = CompositeVideoClip([bg, tarja, txt_clip, vid_centro.set_position("center")])
        final = final.crop(width=1080, height=1920, x_center=540, y_center=960) # Garante 9:16 exato
        
        final.write_videofile(output_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
    if os.path.exists(path_txt): os.remove(path_txt)
    return output_name

# --- INTERFACE ---
st.title("🎙️ Estrategista de Cortes Profissional")

# Sidebar para configurações e transcrição
with st.sidebar:
    st.header("1. Configuração")
    file = st.file_uploader("Vídeo Original", type=["mp4", "mov"])
    bg_img = st.file_uploader("Imagem de Fundo", type=["jpg", "png"])
    
    if st.button("Analisar Momentos Virais"):
        st.session_state['analisar'] = True

# Área Principal
if file and bg_img:
    temp_path = "orig.mp4"
    bg_path = "bg.png"
    with open(temp_path, "wb") as f: f.write(file.getbuffer())
    with open(bg_path, "wb") as f: f.write(bg_img.getbuffer())

    if st.session_state.get('analisar'):
        with st.spinner("IA processando áudio e criando os 3 vídeos..."):
            try:
                # Extração e Transcrição
                with VideoFileClip(temp_path) as v:
                    dur_tot = v.duration
                    v.audio.write_audiofile("a.mp3", codec='libmp3lame', logger=None)
                
                with open("a.mp3", "rb") as a:
                    trans = client.audio.transcriptions.create(file=("a.mp3", a.read()), model="whisper-large-v3-turbo", response_format="text")
                
                # Pedindo JSON à IA
                prompt = f"Vídeo de {dur_tot}s. Escolha os 3 melhores cortes. Retorne APENAS um JSON: [{{'inicio': seg, 'fim': seg, 'tema': 'titulo'}}] Texto: {trans}"
                res = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.1-8b-instant")
                
                match = re.search(r'\[.*\]', res.choices[0].message.content, re.DOTALL)
                cortes = json.loads(match.group().replace("'", '"'))

                # Geração em Colunas (Dashboard)
                st.header("2. Gerador Automático")
                cols = st.columns(3)
                for i, corte in enumerate(cortes[:3]):
                    # Nome único com timestamp para evitar cache de vídeo preto
                    unique_name = f"corte_{i}_{int(time.time())}.mp4"
                    processar_corte(temp_path, bg_path, corte['inicio'], corte['fim'], corte['tema'], unique_name, dur_tot)
                    
                    with cols[i]:
                        st.video(unique_name)
                        st.write(f"**{corte['tema']}**")
                        with open(unique_name, "rb") as f:
                            st.download_button(f"📥 BAIXAR CORTE {i+1}", f, file_name=f"corte_{i+1}.mp4")
                
                st.sidebar.subheader("Transcrição Completa")
                st.sidebar.text_area("", trans, height=300)
                
                st.session_state['analisar'] = False
                gc.collect()
            except Exception as e:
                st.error(f"Erro: {e}")
else:
    st.info("💡 Suba o vídeo e a imagem de fundo na barra lateral para começar.")
