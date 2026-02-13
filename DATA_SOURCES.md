# QBot Data Sources and Handling

This document provides a comprehensive explanation of how QBot sources, downloads, stores, and handles all data types.

---

## 📊 Data Overview

QBot uses several types of data, each with different sources, storage locations, and handling strategies:

| Data Type           | Source            | Storage                 | Download Strategy | Missing Data Handling |
| ------------------- | ----------------- | ----------------------- | ----------------- | --------------------- |
| **Quran Metadata**  | Bundled (JSON)    | `data/metadata/`        | Pre-included      | Error on startup      |
| **Quran Text**      | Bundled (TXT)     | `data/text/`            | Pre-included      | Error on startup      |
| **Audio Files**     | EveryAyah.com     | `data/audio/{reciter}/` | On-demand         | Download on request   |
| **Tafsir**          | AlQuran.cloud API | In-memory cache         | On-demand         | Return None           |
| **User Data**       | User input        | SQLite database         | N/A               | Auto-create           |
| **Generated Audio** | FFmpeg concat     | `output/`               | On-demand         | Generate on request   |

---

## 1️⃣ Quran Metadata

### Source

**Bundled with the repository** - Static JSON file

### Location

```
data/metadata/quran-data.json
```

### Structure

```json
{
  "Sura": [
    [],  // Index 0 is empty
    [0, 7, 5, 1, "الفاتحة", "Al-Faatiha", ...],  // Surah 1
    [7, 286, 87, 2, "البقرة", "Al-Baqara", ...],  // Surah 2
    ...
  ],
  "Page": [...],
  "Juz": [...],
  "Hizb": [...],
  "Manzil": [...],
  "Sajda": [...]
}
```

### Fields (per Surah)

- `[0]`: Starting verse index (global)
- `[1]`: Number of verses
- `[2]`: Revelation order
- `[3]`: Revelation type (1=Meccan, 2=Medinan)
- `[4]`: Arabic name
- `[5]`: English name

### Loading

**File**: [`data.py`](file:///home/neuraknight/Workplace/QBot/data.py)

```python
def load_quran_data(data_dir: Path) -> Dict[str, Any]:
    json_path = data_dir / "metadata" / "quran-data.json"
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    raise FileNotFoundError("No quran-data.json found")
```

### Missing Data Handling

- **Critical**: Bot cannot function without this file
- **Action**: Raises `FileNotFoundError` on startup
- **User Impact**: Bot fails to start

---

## 2️⃣ Quran Text

### Source

**Bundled with the repository** - Static text files

### Location

```
data/text/quran-uthmani.txt  (Primary - Uthmanic script)
data/text/quran-tajweed.txt  (Optional - with Tajweed marks)
data/text/quran-warsh.txt    (Optional - Warsh reading)
```

### Format

- One verse per line
- 6236 lines total (all verses)
- UTF-8 encoding
- No line numbers or metadata

### Loading

**File**: [`data.py`](file:///home/neuraknight/Workplace/QBot/data.py)

```python
def load_quran_text(data_dir: Path, source: str = "hafs") -> List[str]:
    text_sources = {
        "hafs": "quran-uthmani.txt",
        "tajweed": "quran-tajweed.txt",
        "warsh": "quran-warsh.txt"
    }
    filename = text_sources.get(source, f"quran-{source}.txt")
    path = data_dir / "text" / filename

    if path.exists():
        return path.read_text(encoding="utf-8").splitlines()
    return []  # Empty list if not found
```

### Missing Data Handling

- **Critical**: Required for text display and search
- **Action**: Returns empty list `[]`
- **User Impact**: Text features won't work, but bot continues

---

## 3️⃣ Audio Files

### Source

**EveryAyah.com** - On-demand download

### API Endpoint

```
https://everyayah.com/data/{reciter}/{surah}/{surah:03d}{verse:03d}.mp3
```

**Example**:

```
https://everyayah.com/data/Alafasy_64kbps/1/001001.mp3
```

→ Al-Fatiha (Surah 1), Verse 1, by Alafasy

### Storage Structure

```
data/audio/
└── .gitkeep
```

### Reciters List

Stored in `config.py` in the `VOICES` dictionary.

````

### Download Logic

**File**: [`downloader.py`](file:///home/neuraknight/Workplace/QBot/downloader.py)

```python
def download_sura(quran_data, voice, sura):
    """Downloads all verses for a Surah if not already cached."""
    base_url = f"{AUDIO_API}/{voice}/{sura}"
    aya_count = get_sura_aya_count(quran_data, sura)

    output_dir = DATA_DIR / "audio" / voice / str(sura)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for aya in range(1, aya_count + 1):
        filename = f"{sura:03d}{aya:03d}.mp3"
        filepath = output_dir / filename

        if filepath.exists():
            files.append(filepath)  # Use cached file
            continue

        url = f"{base_url}/{filename}"
        try:
            urllib.request.urlretrieve(url, filepath)
            files.append(filepath)
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return None  # Abort on failure

    return files
````

### Download Strategy

1. **Check cache first**: If file exists locally, skip download
2. **Download missing files**: Fetch from EveryAyah.com
3. **Abort on error**: If any verse fails, return `None`

### Missing Data Handling

- **Non-critical**: Audio is optional
- **Action**: Download on first request, cache for future
- **User Impact**: First request slower, subsequent requests instant
- **Error Handling**: If download fails, user sees error message

---

## 4️⃣ Generated Audio (Concatenated MP3)

### Source

**Generated by FFmpeg** - Concatenates individual verse files

### Location

```
output/
├── Alafasy_64kbps-001001001007.mp3  (Surah 1, Verse 1-7)
├── Alafasy_64kbps-002001002005.mp3  (Surah 2, Verse 1-5)
└── .gitkeep
```

### Filename Format

```
{start_surah:03d}{start_verse:03d}{end_surah:03d}{end_verse:03d}.mp3
```

_(Reciter name suffix was removed for better compatibility)_

### Generation Logic

**File**: [`audio.py`](file:///home/neuraknight/Workplace/QBot/audio.py)

```python
def gen_mp3(audio_dir, output_dir, quran_data, voice,
            start_sura, start_aya, end_sura, end_aya,
            title="Quran", artist="Reciter"):
    """Generates a concatenated MP3 with metadata."""

    # 1. Check cache
    range_id = f"{start_sura:03d}{start_aya:03d}{end_sura:03d}{end_aya:03d}"
    filename = f"{voice}-{range_id}.mp3"
    output_path = output_dir / filename

    if output_path.exists():
        return output_path  # Use cached file

    # 2. Collect individual verse files
    files = []
    for sura in range(start_sura, end_sura + 1):
        max_aya = int(quran_data["Sura"][sura][1])
        aya_start = start_aya if sura == start_sura else 1
        aya_end = end_aya if sura == end_sura else max_aya

        for aya in range(aya_start, aya_end + 1):
            path = audio_dir / voice / str(sura) / f"{sura:03d}{aya:03d}.mp3"
            if not path.exists():
                raise FileNotFoundError(f"Missing: {path}")
            files.append(path)

    # 3. Concatenate with FFmpeg
    inputs = [ffmpeg.input(str(f)) for f in files]
    temp = output_dir / f"temp_{filename}"

    (
        ffmpeg
        .concat(*inputs, v=0, a=1)  # v=0: no video/album art
        .output(
            str(temp),
            **{
                'metadata:g:title': title,      # Set title
                'metadata:g:artist': artist,    # Set artist
                'id3v2_version': 3              # ID3v2.3 tags
            }
        )
        .overwrite_output()
        .run(quiet=True)
    )

    temp.rename(output_path)
    return output_path
```

### FFmpeg Process

1. **Input**: Individual verse MP3 files
2. **Concat**: Merge audio streams (`v=0, a=1` = audio only, no video/art)
3. **Metadata**: Set Title and Artist tags
4. **Output**: Single MP3 file with clean metadata

### Missing Data Handling

- **Dependency**: Requires individual verse files
- **Action**: Raises `FileNotFoundError` if verse missing
- **User Impact**: Error message, prompts re-download

---

## 5️⃣ Tafsir (Interpretation)

### Source

**AlQuran.cloud API** - On-demand fetch

### API Endpoint

```
https://api.alquran.cloud/v1/ayah/{surah}:{verse}/editions/quran-uthmani,{edition}
```

**Example**:

```
https://api.alquran.cloud/v1/ayah/2:255/editions/quran-uthmani,ar.muyassar
```

→ Ayatul Kursi (2:255) with Tafsir Al-Muyassar

### Storage

**In-memory cache** (Python dictionary)

```python
cache = {}  # Global cache in tafsir.py
```

### Fetch Logic

**File**: [`tafsir.py`](file:///home/neuraknight/Workplace/QBot/tafsir.py)

```python
def get_tafsir(sura, aya, edition="ar.muyassar"):
    key = f"{edition}:{sura}:{aya}"

    # Check cache
    if key in cache:
        return cache[key]

    # Fetch from API
    url = f"{QURAN_API}/ayah/{sura}:{aya}/editions/quran-uthmani,{edition}"

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            if data.get("data") and len(data["data"]) > 1:
                text = data["data"][1].get("text", "")
                cache[key] = text  # Cache for session
                return text
    except:
        pass

    return None  # Return None on failure
```

### Missing Data Handling

- **Non-critical**: Tafsir is optional
- **Action**: Return `None` on API failure
- **User Impact**: Error message shown to user
- **Cache**: Only persists during bot session (not saved to disk)

---

## 6️⃣ User Data

### Source

**User input** - Telegram interactions

### Storage

**SQLite database**: `data/qbot.db`

### Schema

**File**: [`database.py`](file:///home/neuraknight/Workplace/QBot/database.py)

```python
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    language = Column(String, default='ar')
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Auto-Creation

**File**: [`bot.py`](file:///home/neuraknight/Workplace/QBot/bot.py)

```python
def get_db_user(telegram_user):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_user.id).first()

    if not user:
        # Auto-create new user with default language
        user = User(telegram_id=telegram_user.id, language="ar")
        session.add(user)
        session.commit()

    session.close()
    return user
```

### Missing Data Handling

- **Auto-create**: New users automatically created on first `/start`
- **Default language**: Arabic (`ar`)
- **No migration needed**: SQLAlchemy handles schema

---

## 🔄 Data Flow Summary

### User Requests Verse Range (e.g., "Baqarah 1-5")

1. **NLU** ([`nlu.py`](file:///home/neuraknight/Workplace/QBot/nlu.py)): Parse query → `{type: "range", sura: 2, from_aya: 1, to_aya: 5}`
2. **Metadata** ([`data.py`](file:///home/neuraknight/Workplace/QBot/data.py)): Load Surah info from `quran-data.json`
3. **Text** ([`data.py`](file:///home/neuraknight/Workplace/QBot/data.py)): Load verses from `quran-uthmani.txt`
4. **Display**: Send formatted text to user
5. **Audio Button**: User clicks "🎧 Audio"
6. **Download** ([`downloader.py`](file:///home/neuraknight/Workplace/QBot/downloader.py)): Check `data/audio/Alafasy_64kbps/2/`, download missing files from EveryAyah.com
7. **Generate** ([`audio.py`](file:///home/neuraknight/Workplace/QBot/audio.py)): Concatenate verses 1-5, add metadata, save to `output/`
8. **Send**: Upload MP3 to Telegram

---

## 📁 Directory Structure

```
QBot/
├── data/                          # All Quran data
│   ├── metadata/
│   │   └── quran-data.json       ✅ Bundled (required)
│   ├── text/
│   │   ├── quran-uthmani.txt     ✅ Bundled (required)
│   │   ├── quran-tajweed.txt     ⚪ Bundled (optional)
│   │   └── quran-warsh.txt       ⚪ Bundled (optional)
│   ├── audio/                    🔽 Downloaded on-demand
│   │   └── .gitkeep
│   └── qbot.db                   💾 SQLite database (auto-created)
├── output/                        🎵 Generated MP3 files (cached)
│   └── .gitkeep
└── cache/                         🗂️ Temporary cache (future)
    └── .gitkeep
```

**Legend**:

- ✅ = Bundled, required
- ⚪ = Bundled, optional
- 🔽 = Downloaded on-demand
- 💾 = Auto-generated
- 🎵 = Generated and cached

---

## ⚠️ Error Handling Summary

| Scenario                    | Handling                         | User Impact                    |
| --------------------------- | -------------------------------- | ------------------------------ |
| Missing `quran-data.json`   | Raise error, bot fails to start  | Bot doesn't start              |
| Missing `quran-uthmani.txt` | Return empty list                | Text features broken           |
| Audio download fails        | Return `None`, show error        | User sees error message        |
| Tafsir API fails            | Return `None`                    | User sees "Tafsir unavailable" |
| Missing verse file          | Raise `FileNotFoundError`        | User sees error, can retry     |
| Database missing            | Auto-create on startup           | Seamless                       |
| User not in DB              | Auto-create on first interaction | Seamless                       |

---

## 🚀 Performance Optimizations

1. **Caching**:
   - Audio files cached in `data/audio/`
   - Generated MP3s cached in `output/`
   - Tafsir cached in memory (session-only)

2. **Lazy Loading**:
   - Audio downloaded only when requested
   - Tafsir fetched only when user clicks button

3. **Reuse**:
   - Cached files checked before download/generation
   - Database queries use SQLAlchemy session pooling

---

## 📝 Configuration

**File**: [`config.py`](file:///home/neuraknight/Workplace/QBot/config.py)

```python
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

AUDIO_API = "https://everyayah.com/data"
QURAN_API = "https://api.alquran.cloud/v1"

VOICES = {
    "Alafasy_64kbps": "مشاري العفاسي",
    "Husary_64kbps": "محمود الحصري",
    # ...
}
```

---

## 🔗 External Dependencies

1. **EveryAyah.com**: Audio files (no API key required)
2. **AlQuran.cloud**: Tafsir API (no API key required)
3. **FFmpeg**: Audio processing (system dependency)

All APIs are free and do not require authentication.
