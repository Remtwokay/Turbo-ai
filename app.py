import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import tempfile, os, textwrap
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip

st.set_page_config(page_title="TURBO AI REAL VIDEO", layout="wide")
st.title("TURBO AI V3 - REAL MP4")
st.caption("This version generates REAL video file")

topic = st.text_input("Topic", "How to make money with AI in 2026")

if st.button("GENERATE REAL MP4 VIDEO NOW", type="primary"):
    try:
        with st.spinner("Creating REAL video... 30 seconds"):
            script = f"Stop scrolling. {topic}. Most people fail because they ignore this one secret. If you start today, {topic} will change your life. Follow Turbo AI."
            
            # 1. VOICE
            audio_path = os.path.join(tempfile.gettempdir(), "voice.mp3")
            gTTS(text=script, lang='en').save(audio_path)
            audio = AudioFileClip(audio_path)
            
            # 2. IMAGE WITH YOUR TOPIC
            w,h = 1080,1920
            img = Image.new('RGB', (w,h), (0,0,0))
            draw = ImageDraw.Draw(img)
            try: f = ImageFont.truetype("DejaVuSans.ttf", 55)
            except: f = ImageFont.load_default()
            wrapped = "\n".join(textwrap.wrap(topic.upper(), 15))
            draw.text((60, 400), wrapped, fill=(255,215,0), font=f)
            draw.text((60, 900), "WATCH TILL END", fill=(255,255,255), font=f)
            img_path = os.path.join(tempfile.gettempdir(), "frame.jpg")
            img.save(img_path)
            
            # 3. MAKE MP4
            clip = ImageClip(img_path, duration=audio.duration).set_audio(audio)
            final_path = os.path.join(tempfile.gettempdir(), "TURBO_REAL.mp4")
            clip.write_videofile(final_path, fps=24, codec='libx264', audio_codec='aac', verbose=False, logger=None)
            
            st.success("REAL VIDEO GENERATED - NOT BUNNY")
            st.video(final_path)
            st.audio(audio_path)
            with open(final_path, "rb") as file:
                st.download_button("⬇️ DOWNLOAD REAL MP4 - THIS IS YOUR VIDEO", file, file_name="TURBO_REAL_VIDEO.mp4", mime="video/mp4", type="primary")
            st.code(script)
    except Exception as e:
        st.error(f"Error: {e}")
        st.info("If gTTS fails, Streamlit blocked Google. Try again in 1 minute, it works second time.")

