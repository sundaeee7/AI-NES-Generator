@echo off

python C:\Users\andre\PycharmProjects\chiptune_generator\.venv\Lib\site-packages\magenta\models\music_vae\music_vae_train.py ^
  --config=hier-chiptune_4bar ^
  --run_dir=C:\Users\andre\PycharmProjects\chiptune_generator\train_long ^
  --hparams="batch_size=128,learning_rate=0.001" ^
  --examples_path=C:\Users\andre\PycharmProjects\chiptune_generator\tfrecord\nes_mdb_4chan.tfrecord ^
  --mode=train ^
  --num_steps=20000 ^
  --log=INFO