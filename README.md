# 🎧 AI Audiobook Converter

Convert any text document into high-quality audiobooks using **your own custom voice** with RVC (Retrieval-based Voice Conversion) technology. Transform books, PDFs, EPUBs, and more into personalized audiobooks with any voice or vocal tone you want.

## ✨ Features

- 🎤 **Custom Voice Cloning**: Use any RVC model to create audiobooks with your preferred voice
- 📚 **Multiple Format Support**: TXT, PDF, EPUB, DOCX, DOC files
- 🔄 **Intelligent Text Processing**: Smart chunking and sentence boundary detection
- ⚡ **Parallel Processing**: Concurrent chunk processing for faster conversion
- 💾 **Smart Caching**: Avoid re-processing identical chunks
- 🎵 **High-Quality Audio**: Configurable bitrate and format options
- 🔄 **Retry Logic**: Robust error handling with automatic retries
- 📊 **Progress Tracking**: Real-time conversion progress monitoring

## 🚀 Quick Start

### Prerequisites

1. **Applio** - Download and install [Applio](https://github.com/IAHispano/Applio) for TTS and RVC processing
2. **Python 3.8+** with pip
3. **RVC Model Files** - Your trained .pth and .index files

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/ai-audiobook-converter.git
   cd ai-audiobook-converter
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **⚠️ IMPORTANT: Replace Applio's app.py with API-enabled version**:
   - Download the modified `app.py` from this repository 
   - Navigate to your Applio installation directory
   - **Backup the original**: `cp app.py app.py.backup`
   - Replace with our version: Copy our `app.py` over the original
   - This adds REST API endpoints needed for the audiobook converter

4. **Start Applio** with the new API-enabled version:
   ```bash
   cd /path/to/your/applio
   python app.py
   ```
   - Applio will now run on port 6969 (normal UI) AND port 6970 (API)

5. **Configure the audiobook converter**:
   Edit the configuration section in `audiobook_converter.py`:
   ```python
   PTH_FILE = r"C:/path/to/your/model.pth"
   INDEX_FILE = r"C:/path/to/your/model.index"
   TTS_VOICE = "en-US-AvaNeural"  # Choose your preferred Edge-TTS voice
   ```

5. **Add your books**:
   Place your text files in the `books_to_convert/` folder

6. **Run the converter**:
   ```bash
   python audiobook_converter.py
   ```

## 📋 Requirements

Create a `requirements.txt` file with these dependencies:

```txt
requests>=2.28.0
PyPDF2>=3.0.0
ebooklib>=0.18
pydub>=0.25.1
python-docx>=0.8.11
docx2txt>=0.8
beautifulsoup4>=4.11.0
pathlib
```

**Optional dependencies** (install as needed):
- `python-docx` - For DOCX support
- `docx2txt` - For DOC support  
- `beautifulsoup4` - For better HTML cleaning in EPUBs

## ⚙️ Configuration

### Core Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `PTH_FILE` | Path to your RVC model (.pth) | **REQUIRED** |
| `INDEX_FILE` | Path to your RVC index (.index) | **REQUIRED** |
| `TTS_VOICE` | Edge-TTS voice to use | `en-US-AvaNeural` |
| `API_BASE_URL` | Applio API endpoint | `http://127.0.0.1:6970` |
| `CHUNK_SIZE_WORDS` | Words per processing chunk | `1200` |
| `AUDIO_FORMAT` | Output audio format | `mp3` |
| `AUDIO_BITRATE` | Audio quality | `128k` |
| `RVC_PITCH_SHIFT` | Pitch adjustment (-12 to +12) | `0` |
| `MAX_WORKERS` | Concurrent processing threads | `1` |

### Edge-TTS Voice Options

Popular English voices:
- `en-US-AvaNeural` - Female, clear and natural
- `en-US-BrianNeural` - Male, professional
- `en-US-EmmaNeural` - Female, friendly
- `en-US-GuyNeural` - Male, warm
- `en-GB-SoniaNeural` - British Female
- `en-AU-NatashaNeural` - Australian Female

[See full list of Edge-TTS voices](https://speech.microsoft.com/portal/voicegallery)

## 🔧 Applio Configuration

### Setting up Applio with API Support

**IMPORTANT**: This converter requires a modified version of Applio's `app.py` that includes REST API endpoints.

#### Step 1: Install Applio
1. Download and install [Applio](https://github.com/IAHispano/Applio) following their documentation
2. Ensure Applio runs correctly with the standard interface

#### Step 2: Enable API Support
1. **Download our modified `app.py`** from this repository
2. **Navigate to your Applio installation directory**:
   ```bash
   cd /path/to/your/applio/installation
   ```
3. **Backup the original app.py**:
   ```bash
   cp app.py app.py.backup
   ```
4. **Replace with our API-enabled version**:
   - Copy our `app.py` file over the original `app.py`
   - This adds REST API endpoints without breaking existing functionality

#### Step 3: Start Applio with API
```bash
python app.py
```

After starting, you'll have:
- **Gradio UI**: `http://127.0.0.1:6969` (normal Applio interface)
- **REST API**: `http://127.0.0.1:6970` (for audiobook converter)

#### Verify API is Working
Check if the API is accessible:
```bash
curl http://127.0.0.1:6970/
```

You should see API information and available endpoints.

### What the Modified app.py Adds

The enhanced `app.py` includes these new API endpoints:
- `POST /generate_audiobook` - Submit text for processing
- `GET /status/{job_id}` - Check processing status
- `GET /download/{job_id}` - Download completed audio
- `DELETE /jobs/{job_id}` - Clean up resources

**No existing functionality is removed** - all original Applio features remain intact.

## 📖 Supported File Formats

| Format | Extension | Requirements |
|--------|-----------|--------------|
| Plain Text | `.txt` | Built-in support |
| PDF | `.pdf` | PyPDF2 |
| EPUB | `.epub` | ebooklib |
| Word Document | `.docx` | python-docx |
| Legacy Word | `.doc` | docx2txt |

## 🎯 Usage Examples

### Basic Conversion
```bash
# Place your book files in books_to_convert/
cp "my_book.pdf" books_to_convert/

# Run the converter
python audiobook_converter.py
```

### Batch Processing
```bash
# Add multiple books
cp *.epub books_to_convert/
cp *.pdf books_to_convert/

# Convert all at once
python audiobook_converter.py
```

### Custom Voice Settings
```python
# Edit configuration for different voices/settings
PTH_FILE = r"C:/models/celebrity_voice.pth"
INDEX_FILE = r"C:/models/celebrity_voice.index"
TTS_VOICE = "en-US-EmmaNeural"
RVC_PITCH_SHIFT = -2  # Lower pitch
AUDIO_BITRATE = "192k"  # Higher quality
```

## 📁 Directory Structure

```
ai-audiobook-converter/
├── audiobook_converter.py          # Main conversion script
├── applio_app_modified.py          # Modified Applio app.py (for replacement)
├── config_example.py               # Configuration template
├── requirements.txt                # Python dependencies
├── README.md                       # This documentation
├── LICENSE                         # MIT license
├── .gitignore                      # Git exclusions
├── books_to_convert/               # 📚 Input books folder
│   └── sample.txt                  # Sample book for testing
├── audiobooks/                     # 🎧 Generated audiobooks output
├── chunks/                         # ⚡ Temporary processing files  
├── cache/                          # 💾 Cached audio chunks
│   └── audio_chunks/
└── logs/                           # 📊 Processing logs
    └── audiobook_YYYYMMDD.log
```

## ⚡ Quick Installation Guide

**For users who want to get started immediately:**

1. **Download Applio** and ensure it works
2. **Clone this repository**:
   ```bash
   git clone https://github.com/WhiskeyCoder/ai-audiobook-converter.git
   cd ai-audiobook-converter
   ```
3. **Install Python packages**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Replace Applio's app.py**:
   ```bash
   # Backup original
   cp /path/to/applio/app.py /path/to/applio/app.py.backup
   
   # Copy our version
   cp applio_app_modified.py /path/to/applio/app.py
   ```
5. **Start Applio**:
   ```bash
   cd /path/to/applio
   python app.py
   ```
6. **Configure paths** in `audiobook_converter.py`:
   ```python
   PTH_FILE = r"C:/path/to/your/model.pth"
   INDEX_FILE = r"C:/path/to/your/model.index"
   ```
7. **Add books** to `books_to_convert/` folder
8. **Run converter**:
   ```bash
   python audiobook_converter.py
   ```

**Done!** Your audiobooks will appear in the `audiobooks/` folder.

## 🔍 How It Works

1. **Text Extraction**: Extracts text from various document formats
2. **Intelligent Chunking**: Splits text into optimal chunks for processing
3. **TTS Generation**: Converts text to speech using Edge-TTS
4. **Voice Conversion**: Applies RVC model to transform voice characteristics
5. **Audio Assembly**: Combines processed chunks into final audiobook
6. **Quality Control**: Validates and optimizes output audio

## 🛠️ Troubleshooting

### Common Issues

**API Connection Failed**
```
❌ Cannot connect to Applio API!
```
- Ensure you replaced Applio's `app.py` with our API-enabled version
- Restart Applio after replacing the file
- Check if port 6970 is available and not blocked by firewall
- Verify API endpoint: `curl http://127.0.0.1:6970/`

**Original Applio Functionality Lost**
```
❌ Applio interface not working after app.py replacement
```
- Restore from backup: `cp app.py.backup app.py`
- Re-download our modified `app.py` and try again
- Ensure you're using compatible Applio version

**RVC Model Not Found**
```
❌ RVC model file not found: path/to/model.pth
```
- Check file paths in configuration
- Ensure .pth and .index files exist
- Use absolute paths for clarity

**No Text Extracted**
```
❌ No text extracted from document
```
- Verify file isn't corrupted
- Check if document contains selectable text
- Try converting PDF to text first

**Memory Issues**
```
❌ Failed to process large chunks
```
- Reduce `CHUNK_SIZE_WORDS` to 800-1000
- Lower `MAX_WORKERS` to 1
- Process smaller documents first

### Performance Optimization

**Speed up processing:**
- Use SSD storage for cache directory
- Increase `MAX_WORKERS` (but watch for rate limits)
- Use lower quality TTS voice for faster generation

**Improve quality:**
- Increase `AUDIO_BITRATE` to 192k or 256k
- Use higher quality RVC models
- Fine-tune `RVC_PITCH_SHIFT` for your voice

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/WhiskeyCoder/ai-audiobook-converter.git

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Applio](https://github.com/IAHispano/Applio) - For the amazing RVC and TTS integration
- [Microsoft Edge-TTS](https://github.com/rany2/edge-tts) - For high-quality text-to-speech
- [RVC Project](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) - For voice conversion technology

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/WhiskeyCoder/ai-audiobook-converter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/WhiskeyCoder/ai-audiobook-converter/discussions)
- **Documentation**: [Wiki](https://github.com/WhiskeyCoder/ai-audiobook-converter/wiki)

## 🔮 Roadmap

- [ ] GUI interface for easier configuration
- [ ] Batch voice model switching
- [ ] SSML support for advanced speech control
- [ ] Chapter detection and splitting
- [ ] Multiple output formats (M4B, OGG)
- [ ] Cloud API integration options
- [ ] Real-time preview functionality

---

⭐ **Star this repo** if you found it helpful! 

🐛 **Found a bug?** [Report it here](https://github.com/yourusername/ai-audiobook-converter/issues)

💡 **Have an idea?** [Share it with us](https://github.com/yourusername/ai-audiobook-converter/discussions)
