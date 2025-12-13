import streamlit as st
import io, os, re, sys, tempfile, urllib.request, json
from datetime import datetime
import spacy
import dateparser
import PyPDF2
from docx import Document
from pydub import AudioSegment
from moviepy.editor import VideoFileClip
import speech_recognition as sr

@st.cache_resource
def load_nlp():
    try:
        return spacy.load("en_core_web_sm")
    except:
        os.system("python -m spacy download en_core_web_sm")
        return spacy.load("en_core_web_sm")

nlp = load_nlp()

def clean_text(t):
    return re.sub(r"\s+", " ", t.replace("\r"," ").replace("\n"," ")).strip()

def text_from_pdf(data):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        return clean_text(" ".join([page.extract_text() for page in reader.pages if page.extract_text()]))
    except:
        return ""

def text_from_docx(data):
    try:
        doc = Document(io.BytesIO(data))
        return clean_text(" ".join([p.text for p in doc.paragraphs]))
    except:
        return ""

def text_from_txt(data):
    for enc in ["utf-8","latin-1","cp1252"]:
        try:
            return data.decode(enc)
        except:
            continue
    return ""

def text_from_audio(data, ext):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix="."+ext)
    tmp.write(data)
    tmp.close()
    sound = AudioSegment.from_file(tmp.name)
    wav = tmp.name + ".wav"
    sound.export(wav, format="wav")
    r = sr.Recognizer()
    with sr.AudioFile(wav) as src:
        audio = r.record(src)
        try:
            text = r.recognize_google(audio)
        except:
            text = ""
    os.unlink(tmp.name)
    os.unlink(wav)
    return text

def text_from_video(data, ext):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix="."+ext)
    tmp.write(data)
    tmp.close()
    video = VideoFileClip(tmp.name)
    audio_path = tmp.name + ".wav"
    video.audio.write_audiofile(audio_path, verbose=False, logger=None)
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    text = text_from_audio(audio_data, "wav")
    os.unlink(tmp.name)
    os.unlink(audio_path)
    return text

def local_summarize(text, max_sentences=8):
    doc = nlp(text)
    sents = [sent.text.strip() for sent in doc.sents]
    return "\n".join(sents[:max_sentences])

def detect_deadline(text):
    doc = nlp(text)
    dates = []
    for ent in doc.ents:
        if ent.label_ == "DATE":
            try:
                dt = dateparser.parse(ent.text)
                if dt:
                    dates.append(dt)
            except:
                pass
    if not dates:
        return "No deadline found"
    soonest = min(dates)
    return soonest.strftime("%d %B %Y")

def extract_tasks(text):
    tasks = re.findall(r"(?:Task|Do|Complete|Finish|Submit|Prepare)[^\n\.]{5,120}", text, flags=re.I)
    if not tasks:
        return ["No explicit tasks found"]
    return ["- " + clean_text(t) for t in tasks]

def extract_important_points(text):
    points = re.findall(r"Important[:\- ](.+?)(?=[\.\n])", text, flags=re.I)
    if not points:
        return ["No important points found"]
    return ["- " + clean_text(p) for p in points]

st.title("📌 Zoom Meeting Summary & Task Analyzer (Local Server Version)")
st.write("Upload any PDF, DOCX, TXT, Audio, or Video file.")

uploaded = st.file_uploader("Upload File", type=["pdf","docx","txt","mp3","wav","m4a","mp4","mkv","mov"])

if uploaded:
    ext = uploaded.name.split(".")[-1].lower()
    data = uploaded.read()
    st.info("Processing...")
    if ext == "pdf":
        text = text_from_pdf(data)
    elif ext == "docx":
        text = text_from_docx(data)
    elif ext == "txt":
        text = text_from_txt(data)
    elif ext in ["mp3","wav","m4a"]:
        text = text_from_audio(data, ext)
    elif ext in ["mp4","mkv","mov"]:
        text = text_from_video(data, ext)
    else:
        st.error("Unsupported format")
        st.stop()
    st.subheader("Extracted Text")
    st.write(text[:4000] + "...")
    st.subheader("Summary")
    st.write(local_summarize(text))
    st.subheader("Deadline")
    st.write(detect_deadline(text))
    st.subheader("Tasks")
    for t in extract_tasks(text):
        st.write(t)
    st.subheader("Important Points")
    for p in extract_important_points(text):
        st.write(p)
