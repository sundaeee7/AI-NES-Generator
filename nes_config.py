from magenta.models.music_vae import configs

CONFIG = configs.CONFIG_MAP['hierdec-trio_16bar']
CONFIG.data_converter.max_tensors_per_item = 4  # 4 канала: P1, P2, Tr, No
CONFIG.hparams.z_size = 512  # Размер скрытого пространства
configs.CONFIG_MAP['hierdec-nes_16bar'] = CONFIG
