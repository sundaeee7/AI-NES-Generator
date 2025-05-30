@echo off
set TF_CPP_MIN_LOG_LEVEL=2
call C:\Users\andre\PycharmProjects\chiptune_generator\.venv\Scripts\activate
set MAGENTA_DIR=C:\Users\andre\PycharmProjects\chiptune_generator\.venv\Lib\site-packages
set DATASET_DIR=C:\Users\andre\PycharmProjects\chiptune_generator\tfrecord
set RUN_DIR=C:\Users\andre\PycharmProjects\chiptune_generator\run_dir

python %MAGENTA_DIR%\magenta\models\music_vae\scripts\create_dataset.py ^
    --config=hier-trio_16bar ^
    --mode=train ^
    --input_dir=%MIDI_DIR% ^
    --output_dir=%DATASET_DIR% ^
    --num_threads=1 ^
    --log=INFO


pause