import json, uuid, asyncio, requests, streamlit as st, random
from pathlib import Path
from loguru import logger
import edge_tts
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    concatenate_videoclips, ColorClip, CompositeAudioClip
)

# --- Directories ---
ROOT_DIR = Path(__file__).parent.resolve()
STORAGE_DIR = ROOT_DIR / "storage"
TEMP_DIR = STORAGE_DIR / "temp"
OUTPUT_DIR = STORAGE_DIR / "output"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Streamlit UI ---
st.set_page_config(page_title="Turbo AI - Automated Video Generator", page_icon="🔥", layout="wide")

# --- Custom Theme (Red & White) ---
st.markdown("""
<style>
.stApp { background-color: #FFFFFF; }
section[data-testid="stSidebar"] { background-color: #DC2626!important; }
section[data-testid="stSidebar"] * { color: #FFFFFF!important; }
.stButton>button { background-color: #DC2626!important; color: white!important; border-radius: 8px!important; font-weight: 600!important; }
.stProgress > div > div { background-color: #DC2626!important; }
h1, h2, h3, h4, h5, h6 { color: #DC2626!important; }
</style>
""", unsafe_allow_html=True)

st.title("🔥 Turbo AI")

# --- Sidebar Config ---
with st.sidebar:
    st.header("⚙️ Core Configuration")
    llm_provider = st.selectbox("LLM Script Engine", ["OpenAI", "Built-In Template"])
    llm_key = st.text_input("OpenAI Key", type="password")
    tts_voice = st.selectbox("TTS Voice", ["en-US-JennyNeural", "en-US-GuyNeural", "en-GB-SoniaNeural"])
    pexels_key = st.text_input("Pexels API Key", type="password")
    bg_music = st.checkbox("Add Background Music")

topic = st.text_input("Video Subject / Topic", placeholder="e.g., Space Exploration")
subtitle_pos = st.selectbox("Subtitle Position", ["Bottom", "Top"])
subtitle_color = st.color_picker("Subtitle Color", "#DC2626")
custom_script = st.text_area("Custom Script (Optional)")
aspect_ratio = st.selectbox("Aspect Ratio", ["Vertical (1080x1920)", "Horizontal (1920x1080)", "Square (1080x1080)"])

# --- Functions ---
def generate_script_llm(topic: str, provider: str, api_key: str) -> dict:
    if provider == "OpenAI" and api_key.strip():
        try:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            prompt = f"Create short video script about '{topic}'. Return JSON with 'script' and 'keywords' (3 terms)."
            payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                return json.loads(resp.json()["choices"][0]["message"]["content"])
            else:
                st.error("Script generation failed. Using fallback template.")
        except Exception as e:
            st.error(f"LLM Error: {e}")
            logger.error(e)
    return {"script": f"Welcome to Turbo AI. Today we explore {topic}. Technology is advancing fast.", "keywords": [topic, "technology", "future"]}

async def generate_speech_edge(text: str, voice: str, output_path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def run_tts_safe(text, voice, path):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(generate_speech_edge(text, voice, path))
    finally:
        loop.close()

def fetch_pexels_videos(keywords: list, pexels_key: str, task_id: str, count: int = 3) -> list:
    files = []
    if not pexels_key.strip(): return files
    headers = {"Authorization": pexels_key}
    for kw in keywords[:3]:
        try:
            r = requests.get(f"https://api.pexels.com/videos/search?query={kw}&per_page=5&orientation=portrait", headers=headers, timeout=10)
            if r.status_code == 200 and r.json().get("videos"):
                videos = r.json()["videos"]
                for v in random.sample(videos, min(len(videos), 2)):
                    link = v["video_files"][0]["link"]
                    data = requests.get(link, timeout=20).content
                    fp = TEMP_DIR / f"{task_id}_{uuid.uuid4().hex[:6]}.mp4"
                    fp.write_bytes(data)
                    files.append(str(fp))
        except Exception as e:
            st.warning(f"Clip fetch failed for {kw}")
            logger.error(e)
    return files

def render_video_pipeline(script_text, audio_path, video_clips, output_path, subtitle_pos, subtitle_color, aspect_ratio, bg_music):
    audio_clip = AudioFileClip(audio_path)
    total_duration = audio_clip.duration
    loaded = [VideoFileClip(p).without_audio() for p in video_clips if Path(p).exists()]

    # Aspect ratio handling
    if aspect_ratio == "Vertical (1080x1920)":
        size = (1080, 1920)
    elif aspect_ratio == "Horizontal (1920x1080)":
        size = (1920, 1080)
    else:
        size = (1080, 1080)

    if not loaded:
        base = ColorClip(size=size, color=(220, 38, 38), duration=total_duration)  # Red background
    else:
        concat = concatenate_videoclips(loaded, method="compose")
        if concat.duration < total_duration:
            base = concatenate_videoclips([concat] * (int(total_duration // concat.duration) + 1)).subclip(0, total_duration)
        else:
            base = concat.subclip(0, total_duration)

    base = base.resize(size)

    txt = TextClip(
        text=script_text,
        fontsize=48,
        color=subtitle_color,
        stroke_color="black",
        stroke_width=2,
        method="caption",
        size=(size[0]-200, None),
        duration=total_duration
    ).set_position(('center', size[1]-200 if subtitle_pos == "Bottom" else 200))

    clips = [base, txt]
    final_audio = audio_clip
    if bg_music:
        music = AudioFileClip("assets/background.mp3").volumex(0.3)
        final_audio = CompositeAudioClip([audio_clip, music])

    final = CompositeVideoClip(clips).set_audio(final_audio)
    final.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast')

    # Cleanup
    audio_clip.close(); final.close(); base.close(); txt.close()
    for c in loaded: c.close()
    if 'concat' in locals(): concat.close()

# --- Workflow ---
if st.button("🚀 Start Video Render", use_container_width=True):
    if not topic and not custom_script: 
        st.warning("Provide topic or script")
    else:
        task_id = str(uuid.uuid4())[:8]
        bar = st.progress(0, text="Generating script...")
        script_data = {"script": custom_script, "keywords": [topic]} if custom_script.strip() else generate_script_llm(topic, llm_provider, llm_key)
        st.info(script_data['script'])

        bar.progress(40, text="Synthesizing voice...")
        audio_file = str(TEMP_DIR / f"{task_id}.mp3")
        run_tts_safe(script_data['script'], tts_voice, audio_file)

        bar.progress(60, text="Fetching clips...")
        vids = fetch_pexels_videos(script_data.get('keywords', []), pexels_key, task_id)

        bar.progress(80, text="Rendering...")
        out = str(OUTPUT_DIR / f"TURBO_{task_id}.mp4")
        render_video_pipeline(script_data['script'], audio_file, vids, out, subtitle_pos, subtitle_color, aspect_ratio, bg_music)

        bar.progress(100, text="Done!")
        st.success("Video ready!"); st.video(out)
        st.download_button("⬇️ Download Video", data=open(out, "rb").read(), file_name=f"TURBO_{task_id}.mp4")


