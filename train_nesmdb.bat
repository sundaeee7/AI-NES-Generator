@echo off
set TF_CPP_MIN_LOG_LEVEL=2
call C:\Users\andre\PycharmProjects\chiptune_generator\.venv\Scripts\activate
set MAGENTA_DIR=C:\Users\andre\PycharmProjects\chiptune_generator\.venv\Lib\site-packages
set DATASET_DIR=C:\Users\andre\PycharmProjects\chiptune_generator\tfrecord
set RUN_DIR=C:\Users\andre\PycharmProjects\chiptune_generator\run_dir

python %MAGENTA_DIR%\magenta\models\music_vae\music_vae_train.py ^
  --config=nesmdb ^
  --run_dir=%RUN_DIR% ^
  --mode=train ^
  --examples_path=%DATASET_DIR%\nes_mdb_4chan.tfrecord ^
  --hparams=batch_size=32,learning_rate=0.0005 ^
  --num_steps=100 ^
  --log=DEBUG

pause