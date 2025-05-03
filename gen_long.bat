@echo off
set TF_CPP_MIN_LOG_LEVEL=2
call C:\Users\andre\PycharmProjects\chiptune_generator\.venv\Scripts\activate
set MAGENTA_DIR=C:\Users\andre\PycharmProjects\chiptune_generator\.venv\Lib\site-packages
set RUN_DIR=C:\Users\andre\PycharmProjects\chiptune_generator
set OUTPUT_DIR=C:\Users\andre\PycharmProjects\chiptune_generator\generated_midis

if not exist %OUTPUT_D    IR% mkdir %OUTPUT_DIR%

python %MAGENTA_DIR%\magenta\models\music_vae\music_vae_generate.py ^
  --config=hier-chiptune_4bar ^
  --checkpoint_file=%RUN_DIR%\train_long\train\model.ckpt-27 ^
  --mode=sample ^
  --num_outputs=1 ^
  --output_dir=%OUTPUT_DIR% ^
  --temperature=1.0

pause