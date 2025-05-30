import os
import shutil
import subprocess
import time
import uuid
import numpy as np
import fluidsynth
from datetime import datetime
from pydub import AudioSegment
from scipy.io import wavfile
from fastapi import FastAPI, Request, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import mido
import firebase_admin
from firebase_admin import credentials, firestore, auth as firebase_auth
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SAMPLE_RATE = 44100
OUTPUT_DIR = r"C:/Users/andre/PycharmProjects/chiptune_generator/generated_midis"
STATIC_DIR = r"C:/Users/andre/PycharmProjects/chiptune_generator/static"
MIDIS_DIR = os.path.join(STATIC_DIR, "midis")
WAVS_DIR = os.path.join(STATIC_DIR, "wavs")
GEN_NESMDB_BAT_PATH = r"C:/Users/andre/PycharmProjects/chiptune_generator/gen_long.bat"
SF2_PATH = r"C:/Users/andre/PycharmProjects/chiptune_generator/soundfont/Famicom.sf2"
CHECKPOINT_FILE = r"C:/Users/andre/PycharmProjects/chiptune_generator/run_dir/train/model.ckpt-74"

cred = credentials.Certificate("front/chipgen-9465b-firebase-adminsdk-fbsvc-83d2f2c92e.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="front")

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token['uid']
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


def midi_to_wav(midi_path, wav_path, track_index=None, sample_rate=SAMPLE_RATE):
    if track_index is not None:
        original_midi = mido.MidiFile(midi_path)
        new_midi = mido.MidiFile(ticks_per_beat=original_midi.ticks_per_beat)
        if track_index < len(original_midi.tracks):
            new_midi.tracks.append(original_midi.tracks[track_index])
        temp_midi_path = midi_path.replace('.mid', '_single_track.mid')
        new_midi.save(temp_midi_path)
        midi_path_to_use = temp_midi_path
    else:
        midi_path_to_use = midi_path

    result = subprocess.run([
        "fluidsynth", "-ni", "-F", wav_path, "-r", str(sample_rate), SF2_PATH, midi_path_to_use
    ], check=True, capture_output=True, text=True)

    if track_index is not None and os.path.exists(midi_path_to_use):
        os.remove(midi_path_to_use)

    print(f"Fluidsynth STDOUT: {result.stdout}")
    print(f"Fluidsynth STDERR: {result.stderr}")


def check_midi_content(midi_path):
    midi = mido.MidiFile(midi_path)
    note_count = 0
    for track in midi.tracks:
        for msg in track:
            if msg.type == 'note_on':
                note_count += 1
    print(f"MIDI {midi_path} contains {note_count} note_on events")
    return note_count > 0


def trim_wav_to_segment(wav_path, segment_duration=8):
    sample_rate, data = wavfile.read(wav_path)
    target_samples = int(segment_duration * sample_rate)
    if len(data) > target_samples:
        data = data[:target_samples]
    wavfile.write(wav_path, sample_rate, data)
    print(f"Trimmed WAV {wav_path} to {segment_duration} seconds")
    return data


def append_wav(existing_wav, new_wav_segment, output_wav, sample_rate=44100):
    _, existing_data = wavfile.read(existing_wav)
    new_data = trim_wav_to_segment(new_wav_segment, segment_duration=8)
    combined_data = np.concatenate((existing_data, new_data))
    wavfile.write(output_wav, sample_rate, combined_data)
    print(f"Appended WAV, new duration: {len(combined_data) / sample_rate:.2f} seconds")


async def save_track_to_firestore(user_id, track_id, wav_filename):
    track_ref = db.collection('users').document(user_id).collection('tracks').document(track_id)
    print(f"Saving track {track_id} for user {user_id}")
    await track_ref.set({
        'trackCode': track_id,
        'title': track_id,
        'createdAt': firestore.SERVER_TIMESTAMP,
        'audioUrl': f"/static/wavs/{wav_filename}"
    })
    print(f"Track {track_id} saved successfully")


async def generate_midi_and_wav(user_id, save_to_history=True):
    track_id = str(uuid.uuid4())
    midi_filename = f"{track_id}.mid"
    wav_filename = f"{track_id}.wav"

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    result = subprocess.run(GEN_NESMDB_BAT_PATH, shell=True, capture_output=True, text=True)
    midi_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mid')]
    if not midi_files:
        raise RuntimeError("No MIDI files generated")

    source_midi = os.path.join(OUTPUT_DIR, midi_files[0])
    if not check_midi_content(source_midi):
        raise RuntimeError(f"Generated MIDI {source_midi} is empty")

    target_midi = os.path.join(MIDIS_DIR, midi_filename)
    target_wav = os.path.join(WAVS_DIR, wav_filename)

    midi_to_wav(source_midi, target_wav)
    trim_wav_to_segment(target_wav, segment_duration=8)
    shutil.copy(source_midi, target_midi)

    if save_to_history:
        await save_track_to_firestore(user_id, track_id, wav_filename)

    return track_id, target_midi, target_wav


async def continue_midi_and_wav(current_track_id, user_id, save_to_history):
    current_midi_path = os.path.join(MIDIS_DIR, f"{current_track_id}.mid")
    if not current_track_id or not os.path.exists(current_midi_path):
        print("No valid current track ID provided or file not found, generating new track")
        return await generate_midi_and_wav(user_id)

    new_track_id = str(uuid.uuid4())
    new_midi_filename = f"{new_track_id}.mid"
    new_wav_filename = f"{new_track_id}.wav"

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    result = subprocess.run([
        "python",
        r"C:/Users/andre/PycharmProjects/chiptune_generator/.venv/Lib/site-packages/magenta/models"
        r"/music_vae/music_vae_generate.py",
        "--config=hier-chiptune_4bar",
        "--checkpoint_file=" + CHECKPOINT_FILE,
        "--mode=sample",
        "--num_outputs=1",
        "--output_dir=" + OUTPUT_DIR,
        "--temperature=1.0",
        "--primer_midi=" + current_midi_path
    ], shell=True, capture_output=True, text=True)

    print("Generate STDOUT:", result.stdout)
    print("Generate STDERR:", result.stderr)

    midi_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mid')]
    if not midi_files:
        raise RuntimeError(f"No MIDI files generated in continue_midi_and_wav. Command output: {result.stderr}")

    new_midi_file = os.path.join(OUTPUT_DIR, midi_files[0])
    if not check_midi_content(new_midi_file):
        raise RuntimeError(f"New MIDI {new_midi_file} is empty")

    prev_midi = mido.MidiFile(current_midi_path)
    new_midi = mido.MidiFile(new_midi_file)
    combined_midi = mido.MidiFile(ticks_per_beat=prev_midi.ticks_per_beat)

    for i in range(max(len(prev_midi.tracks), len(new_midi.tracks))):
        combined_track = mido.MidiTrack()
        if i < len(prev_midi.tracks):
            for msg in prev_midi.tracks[i]:
                combined_track.append(msg)
        if i < len(new_midi.tracks):
            prev_duration = sum(msg.time for msg in prev_midi.tracks[i]) if i < len(prev_midi.tracks) else 0
            for msg in new_midi.tracks[i]:
                new_msg = msg.copy()
                if not new_msg.is_meta:
                    new_msg.time += prev_duration
                combined_track.append(new_msg)
        combined_midi.tracks.append(combined_track)

    combined_midi_path = os.path.join(MIDIS_DIR, new_midi_filename)
    combined_midi.save(combined_midi_path)

    temp_wav = os.path.join(WAVS_DIR, "temp.wav")
    target_wav = os.path.join(WAVS_DIR, new_wav_filename)
    current_wav = os.path.join(WAVS_DIR, f"{current_track_id}.wav")

    midi_to_wav(new_midi_file, temp_wav)
    if os.path.exists(current_wav):
        append_wav(current_wav, temp_wav, target_wav)
        os.remove(temp_wav)
    else:
        trim_wav_to_segment(temp_wav, segment_duration=8)
        shutil.move(temp_wav, target_wav)

    if save_to_history:
        await save_track_to_firestore(user_id, new_track_id, new_wav_filename)

    return new_track_id, combined_midi_path, target_wav


async def generate_single_track_wav(user_id, save_to_history):
    track_id = str(uuid.uuid4())
    midi_filename = f"{track_id}.mid"
    wav_filename = f"{track_id}.wav"

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    result = subprocess.run(GEN_NESMDB_BAT_PATH, shell=True, capture_output=True, text=True)
    print("Generate STDOUT:", result.stdout)
    print("Generate STDERR:", result.stderr)

    midi_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mid')]
    if not midi_files:
        raise RuntimeError("No MIDI files generated in generate_single_track_wav")

    midi_file = os.path.join(OUTPUT_DIR, midi_files[0])
    if not check_midi_content(midi_file):
        raise RuntimeError(f"Generated MIDI {midi_file} is empty")

    target_midi = os.path.join(MIDIS_DIR, midi_filename)
    shutil.copy(midi_file, target_midi)

    target_wav = os.path.join(WAVS_DIR, wav_filename)
    midi_to_wav(midi_file, target_wav, track_index=1)
    trim_wav_to_segment(target_wav, segment_duration=8)

    if save_to_history:
        await save_track_to_firestore(user_id, track_id, wav_filename)

    return track_id, target_midi, target_wav


async def convert_uploaded_midi_to_chiptune(midi_file: UploadFile, user_id: str, save_to_history):
    track_id = str(uuid.uuid4())
    midi_filename = f"{track_id}.mid"
    wav_filename = f"{track_id}.wav"

    target_midi = os.path.join(MIDIS_DIR, midi_filename)
    target_wav = os.path.join(WAVS_DIR, wav_filename)

    with open(target_midi, "wb") as f:
        content = await midi_file.read()
        f.write(content)

    if not check_midi_content(target_midi):
        os.remove(target_midi)
        raise RuntimeError("Uploaded MIDI file is empty or invalid")

    midi_to_wav(target_midi, target_wav)
    trim_wav_to_segment(target_wav, segment_duration=8)

    if save_to_history:
        await save_track_to_firestore(user_id, track_id, wav_filename)

    return track_id, target_midi, target_wav


@app.get("/generate_single_track")
async def generate_single_track_endpoint(user_id: str = Depends(get_current_user), saveToHistory: bool = Query(default=True)):
    try:
        track_id, midi_file, wav_file = await generate_single_track_wav(user_id, save_to_history=saveToHistory)
        return {"audio_url": f"/static/wavs/{track_id}.wav", "track_id": track_id}
    except Exception as e:
        print(f"Full error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating single track: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, track_id: str = None):
    if track_id:
        wav_path = os.path.join(WAVS_DIR, f"{track_id}.wav")
        if os.path.exists(wav_path):
            audio_url = f"/static/wavs/{track_id}.wav"
            return templates.TemplateResponse("main.html", {"request": request, "audio_url": audio_url, "track_id": track_id})
        else:
            return templates.TemplateResponse("main.html", {"request": request, "audio_url": None, "error": "Track not found"})
    return templates.TemplateResponse("main.html", {"request": request, "audio_url": None})


@app.get("/generate_track")
async def generate_track_endpoint(user_id: str = Depends(get_current_user), saveToHistory: bool = Query(default=True)):
    try:
        track_id, midi_file, wav_file = await generate_midi_and_wav(user_id, save_to_history=saveToHistory)
        return {"audio_url": f"/static/wavs/{track_id}.wav", "track_id": track_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating track: {str(e)}")


@app.get("/continue_track")
async def continue_track_endpoint(track_id: str = None, user_id: str = Depends(get_current_user), saveToHistory: bool = Query(default=True)):
    try:
        new_track_id, midi_file, wav_file = await continue_midi_and_wav(track_id, user_id, save_to_history=saveToHistory)
        return {"audio_url": f"/static/wavs/{new_track_id}.wav", "track_id": new_track_id}
    except Exception as e:
        print(f"Full error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error continuing track: {str(e)}")


@app.get("/download")
async def download_track(track_id: str, volume: float = 1.0):
    wav_file = os.path.join(WAVS_DIR, f"{track_id}.wav")
    if not os.path.exists(wav_file):
        return {"error": "File not found"}
    audio = AudioSegment.from_wav(wav_file)
    gain = (volume - 1) * 20
    adjusted_audio = audio + gain
    temp_wav = os.path.join(WAVS_DIR, f"{track_id}_adjusted.wav")
    adjusted_audio.export(temp_wav, format="wav")
    response = FileResponse(path=temp_wav, filename=f"{track_id}.wav", media_type="audio/wav")
    return response


@app.get("/download_midi")
async def download_midi_track(track_id: str):
    midi_file = os.path.join(MIDIS_DIR, f"{track_id}.mid")
    if not os.path.exists(midi_file):
        return {"error": "MIDI file not found"}
    response = FileResponse(path=midi_file, filename=f"{track_id}.mid", media_type="audio/midi")
    return response


@app.post("/upload_midi")
async def upload_midi_endpoint(midi: UploadFile = File(...), user_id: str = Depends(get_current_user), saveToHistory: bool = Query(default=True)):
    try:
        if not midi.filename.endswith(('.mid', '.midi')):
            raise HTTPException(status_code=400, detail="File must be a MIDI file (.mid or .midi)")
        track_id, midi_file, wav_file = await convert_uploaded_midi_to_chiptune(midi, user_id, save_to_history=saveToHistory)
        return {"audio_url": f"/static/wavs/{track_id}.wav", "track_id": track_id}
    except Exception as e:
        print(f"Full error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error converting MIDI to chiptune: {str(e)}")


@app.delete("/tracks/{track_id}")
async def delete_track(track_id: str, user_id: str = Depends(get_current_user)):
    try:
        track_ref = db.collection('users').document(user_id).collection('tracks').document(track_id)
        track_doc = track_ref.get()
        if not track_doc.exists:
            raise HTTPException(status_code=404, detail="Track not found")

        midi_file = os.path.join(MIDIS_DIR, f"{track_id}.mid")
        wav_file = os.path.join(WAVS_DIR, f"{track_id}.wav")

        if os.path.exists(midi_file):
            os.remove(midi_file)

        if os.path.exists(wav_file):
            os.remove(wav_file)

        track_ref.delete()
        print(f"Track {track_id} deleted from Firestore for user {user_id}")

        return {"message": "Track deleted successfully"}
    except Exception as e:
        print(f"Error deleting track: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting track: {str(e)}")


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})


@app.get("/auth", response_class=HTMLResponse)
async def auth(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})


@app.delete("/delete_user")
async def delete_user(user_id: str = Depends(get_current_user)):
    try:
        tracks_ref = db.collection('users').document(user_id).collection('tracks')
        for track in tracks_ref.stream():
            track.reference.delete()

        db.collection('users').document(user_id).delete()

        firebase_auth.delete_user(user_id)

        return {"message": "Пользователь успешно удалён"}
    except Exception as e:
        print(f"Ошибка при удалении пользователя: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при удалении аккаунта")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
