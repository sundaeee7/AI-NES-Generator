import os
import shutil
import subprocess
import time
import numpy as np
import fluidsynth
from scipy.io import wavfile
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Параметры
SAMPLE_RATE = 44100
OUTPUT_DIR = r"C:\Users\andre\PycharmProjects\chiptune_generator\generated_midis"
STATIC_DIR = r"C:\Users\andre\PycharmProjects\chiptune_generator\static"
GEN_NESMDB_BAT_PATH = r"C:\Users\andre\PycharmProjects\chiptune_generator\gen_nesmdb.bat"
SF2_PATH = r"C:\Users\andre\PycharmProjects\chiptune_generator\soundfont\8bitsf.sf2"

# Инициализация FastAPI
app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="templates")


# Конвертация MIDI в WAV
def midi_to_wav(midi_path, wav_path, sample_rate=SAMPLE_RATE):
    subprocess.run([
        "fluidsynth",
        "-ni",           # Без интерактивного режима
        "-F", wav_path,  # Выходной WAV-файл
        "-r", str(sample_rate),  # Частота дискретизации
        SF2_PATH,  # Путь к SoundFont
        midi_path        # Путь к MIDI
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)


# Генерация MIDI с помощью gen_nesmdb.bat и конвертация в WAV
def generate_midi_and_wav():
    if os.path.exists(OUTPUT_DIR):
        for filename in os.listdir(OUTPUT_DIR):
            file_path = os.path.join(OUTPUT_DIR, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

    if os.path.exists(STATIC_DIR):
        for filename in os.listdir(STATIC_DIR):
            file_path = os.path.join(STATIC_DIR, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    if not os.path.exists(STATIC_DIR):
        os.makedirs(STATIC_DIR)

    # Запускаем gen_nesmdb.bat для генерации нового MIDI
    result = subprocess.run(GEN_NESMDB_BAT_PATH, shell=True, capture_output=True, text=True)

    # Ищем последний сгенерированный MIDI-файл
    midi_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mid')]
    midi_file = f"C:/Users/andre/PycharmProjects/chiptune_generator/generated_midis/" + f"{midi_files[0]}"

    wav_file = os.path.join(STATIC_DIR, "generated.wav")

    # Конвертируем MIDI в WAV
    midi_to_wav(midi_file, wav_file)

    return midi_file, wav_file


# Главная страница
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("test.html", {"request": request, "audio_url": None})


# Генерация трека
@app.get("/generate_track")
async def generate_track_endpoint():
    midi_file, wav_file = generate_midi_and_wav()
    return {"audio_url": "/static/generated.wav"}


# Скачивание WAV
@app.get("/download")
async def download_track():
    wav_file = os.path.join(STATIC_DIR, "generated.wav")
    if os.path.exists(wav_file):
        return FileResponse(
            path=wav_file,
            filename="generated.wav",
            media_type="audio/wav"
        )
    return {"error": "File not found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
