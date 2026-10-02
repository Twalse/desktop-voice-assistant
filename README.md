# Desktop Voice Assistant (Голосовой Ассистент для Windows)

Модульный головой ассистент для Windows с поддержкой индексации приложений, управления системой, офлайн-распознавания речи (faster-whisper), двух режимов работы (Команды / Диалог с ИИ) и современным графическим интерфейсом на CustomTkinter.

---

## 🛠 Установка и запуск на Windows

### 1. Создание виртуального окружения
Откройте PowerShell или Командную строку (CMD) в папке проекта и выполните:

```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 2. Установка зависимостей
Установите требуемые библиотеки:

```powershell
pip install -r requirements.txt
```

### 3. GPU Ускорение (CUDA / cuBLAS для faster-whisper)
Для наибыстрейшей офлайн-транскрипции речи с помощью GPU NVIDIA:
1. Убедитесь, что установлены драйверы NVIDIA и [CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-downloads).
2. Установите PyTorch с поддержкой CUDA:
   ```powershell
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```
3. При отсутствии библиотеки `cublas64_12.dll` скачайте соответствующие DLL cuBLAS/cuDNN или добавьте путь к CUDA в системный `PATH`.
*При отсутствии GPU ассистент автоматически переключится на высокопроизводительный режим CPU (int8).*

---

## 🚀 Запуск приложения

Запустите главного ассистента:

```powershell
python main.py
```

---

## ⚙️ Настройка ИИ в Режиме Диалога (LLM)

Ассистент поддерживает два источника ИИ для ответов в режиме "Диалог":

1. **Google Gemini Flash API** (Рекомендуется):
   Задайте переменную окружения `GEMINI_API_KEY`:
   ```powershell
   $env:GEMINI_API_KEY="ваш_ключ_gemini"
   ```
2. **Локальный Ollama**:
   Запустите [Ollama](https://ollama.com) локально. По умолчанию ассистент будет обращаться к `http://localhost:11434`. При необходимости переопределите URL:
   ```powershell
   $env:OLLAMA_URL="http://localhost:11434"
   ```

---

## ⌨️ Горячие клавиши
- `Ctrl + Shift + Space` — Быстрое переключение активности микрофона (ВКЛ / ВЫКЛ).
