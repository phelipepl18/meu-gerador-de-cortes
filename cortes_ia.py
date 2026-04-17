import streamlit as st
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, ColorClip
from groq import Groq
import os, gc, json, re, random, time
from PIL import Image, ImageDraw, ImageFont

# --- CORREÇÃO DE COMPATIBILIDADE PILLOW ---
import PIL.Image
if not hasattr(PIL.Image, 'Resampling'):
    PIL.Image.LANCZOS = PIL.Image.ANTIALIAS
else:
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    PIL.Image.LANCZOS = PIL.Image.Resampling.LANCZOS

# 1. CONFIGURAÇÃO DA PÁGINA (DEVE SER A PRIMEIRA COISA)
st.set_page_config(page_title="Estrategista de Cortes", layout="wide")

# Inicializa variáveis de estado para não dar erro de "variable not defined"
if 'analisar' not in st.session_state:
    st.session_state['analisar'] = False

# Estilização para o layout profissional
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child {
        background-color: #2e77d0;
        color: white;
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }
    .stVideo { border-radius: 15px; border: 1px solid #444; }
    </style>
    """, unsafe_allow_html=True)

# Conexão Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("⚠️ Erro nas Credenciais: Configure a GROQ_API_KEY nos Secrets.")

def criar_imagem_texto(texto, largura=1080):
    img = Image.new('RGBA', (largura, 450), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 100)
    except:
        font = ImageFont.load_default()
    
    texto_formatado = texto.upper()
    w_txt, h_txt = draw.textbbox((0, 0), texto_formatado, font=font)[2:4]
    draw.text(((largura - w_txt) / 2, (450 - h_txt) / 2), texto_formatado, font=font, fill="white", align="center")
    
    path = f"txt_{random.randint(0,9999)}.png"
    img.save(path)
    return path

def processar_corte(video_path, bg_path, start, end, tema, output_name, dur_max):
    # Garante que os tempos são válidos para o MoviePy
    start_v = max(0, float(start))
    end_v = min(float(end), float(dur_max))
    
    with VideoFileClip(video_path) as video:
        clip = video.subclip(start_v, end_v)
        bg = ImageClip(bg_path).set_duration(clip.duration).resize(height=1920)
        bg = bg.crop(x_center=bg.w/2, y_center=bg.h/2, width=1080, height=1920)
        
        vid_centro = clip.resize(width=1000)
        path_txt = criar_imagem_texto(tema)
        
        txt_clip = ImageClip(path_txt).set_duration(clip.duration).set_position(('center', 200))
        tarja = ColorClip(size=(1080, 400), color=(0,0,0)).set_opacity(0.7).set_duration(clip.duration).set_position(('center', 220))
        
        final = CompositeVideoClip([bg, tarja, txt_clip, vid_centro.set_position("center")])
        
        # Força dimensões pares (importante para o player do navegador)
        final = final.crop(width=1080, height=1920, x_center=540, y_center=960)
        
        final.write_videofile(output_name, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
    
    if os.path.exists(path_txt): os.remove(path_txt)
    return output_name

# --- INTERFACE ---
st.title("🎙️ Estrategista de Cortes Profissional")

with st.sidebar:
    st.header("1. Upload de Arquivos")
    file = st.file_uploader("Vídeo Original", type=["mp4", "mov"])
    bg_img = st.file_uploader("Imagem de Fundo (9:16)", type=["jpg", "png"])
    
    if st.button("🚀 GERAR 3 VÍDEOS AUTOMÁTICOS"):
        if file and bg_img:
            st.session_state['analisar'] = True
        else:
            st.warning("Envie o vídeo e o fundo primeiro!")

if file and bg_img:
    temp_path = "orig_file.mp4"
    bg_path = "bg_file.png"
    
    with open(temp_path, "wb") as f: f.write(file.getbuffer())
    with open(bg_path, "wb") as f: f.write(bg_img.getbuffer())

    if st.session_state['analisar']:
        with st.spinner("IA analisando e editando os vídeos..."):
            try:
                with VideoFileClip(temp_path) as v:
                    dur_tot = v.duration
                    v.audio.write_audiofile("temp_audio.mp3", codec='libmp3lame', logger=None)
                
                with open("temp_audio.mp3", "rb") as a:
                    trans = client.audio.transcriptions.create(file=("temp_audio.mp3", a.read()), model="whisper-large-v3-turbo", response_format="text")
                
                prompt = f"Vídeo de {dur_tot}s. Escolha 3 cortes virais. Retorne APENAS JSON: [{{'inicio': seg, 'fim': seg, 'tema': 'titulo'}}] Texto: {trans}"
                res = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.1-8b-instant")
                
                match = re.search(r'\[.*\]', res.choices[0].message.content, re.DOTALL)
                cortes = json.loads(match.group().replace("'", '"'))

                st.header("2. Seus Cortes Gerados")
                cols = st.columns(3)
                
                for i, corte in enumerate(cortes[:3]):
                    out_name = f"final_{i}_{int(time.time())}.mp4"
                    processar_corte(temp_path, bg_path, corte['inicio'], corte['fim'], corte['tema'], out_name, dur_tot)
                    
                    with cols[i]:
                        st.video(out_name)
                        st.caption(f"📌 {corte['tema']}")
                        with open(out_name, "rb") as f:
                            st.download_button(f"Baixar Vídeo {i+1}", f, file_name=f"corte_{i+1}.mp4")
                
                st.sidebar.success("Concluído!")
                st.session_state['analisar'] = False
                gc.collect()
            except Exception as e:
                st.error(f"Erro no processamento: {e}")
else:
    st.info("Aguardando arquivos para iniciar...")
