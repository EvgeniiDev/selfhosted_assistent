"""
Патч для GigaAM для работы с PyTorch 2.6+
"""

import torch
import omegaconf.dictconfig

# Добавляем безопасные глобальные переменные для PyTorch 2.6+
if hasattr(torch.serialization, 'add_safe_globals'):
    try:
        torch.serialization.add_safe_globals([omegaconf.dictconfig.DictConfig])
        print("✅ Добавлены безопасные глобальные переменные для PyTorch")
    except Exception as e:
        print(f"⚠️ Не удалось добавить безопасные глобальные переменные: {e}")
