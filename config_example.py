#!/usr/bin/env python3
"""
Configuration Example for AI Audiobook Converter
Copy this file and modify the paths for your setup
"""

# =============================================================================
# REQUIRED CONFIGURATION - EDIT THESE PATHS
# =============================================================================

# RVC Model Files (REQUIRED)
PTH_FILE = r"C:/path/to/your/rvc_model.pth"
INDEX_FILE = r"C:/path/to/your/rvc_model.index"

# Example paths for different operating systems:
# Windows: r"C:/Applio/models/my_voice/my_voice.pth"
# Linux/Mac: "/home/user/applio/models/my_voice/my_voice.pth"

# =============================================================================
# TTS AND VOICE SETTINGS
# =============================================================================

# Edge-TTS Voice Selection
TTS_VOICE = "en-US-AvaNeural"

# Popular voice options:
# English (US): en-US-AvaNeural, en-US-BrianNeural, en-US-EmmaNeural
# English (UK): en-GB-SoniaNeural, en-GB-RyanNeural
# English (AU): en-AU-NatashaNeural, en-AU-WilliamNeural

# Voice modification settings
RVC_PITCH_SHIFT = 0     # Range: -12 to +12 semitones
TTS_RATE = 0           # Speech rate: -100 to +100

# =============================================================================
# API CONFIGURATION
# =============================================================================

API_BASE_URL = "http://127.0.0.1:6970"  # Default Applio API endpoint
API_TIMEOUT = 300                        # 5 minutes per chunk
MAX_RETRIES = 3                         # Retry failed chunks

# =============================================================================
# PROCESSING SETTINGS
# =============================================================================

# Text processing
CHUNK_SIZE_WORDS = 1200                 # Words per chunk (adjust for performance)
MIN_DELAY_BETWEEN_CHUNKS = 3           # Seconds between API calls

# Parallel processing
MAX_WORKERS = 1                         # Concurrent chunks (keep low for rate limiting)

# =============================================================================
# AUDIO OUTPUT SETTINGS
# =============================================================================

AUDIO_FORMAT = "mp3"                    # Format: mp3, wav, m4a
AUDIO_BITRATE = "128k"                  # Quality: 64k, 128k, 192k, 256k, 320k

# =============================================================================
# DIRECTORY CONFIGURATION
# =============================================================================

BOOKS_FOLDER = "books_to_convert"       # Input folder for books
AUDIOBOOKS_FOLDER = "audiobooks"        # Output folder for audiobooks
CACHE_FOLDER = "cache"                  # Cache folder for processed chunks
LOGS_FOLDER = "logs"                    # Logs folder

# =============================================================================
# ADVANCED SETTINGS (Usually don't need to change)
# =============================================================================

# Supported file extensions
SUPPORTED_FORMATS = ['.txt', '.pdf', '.epub', '.docx', '.doc']

# Text cleaning options
CLEAN_PAGE_NUMBERS = True               # Remove standalone numbers
NORMALIZE_WHITESPACE = True             # Clean up spacing
SENTENCE_BOUNDARY_DETECTION = True      # Smart sentence splitting

# Cache settings
ENABLE_CACHING = True                   # Cache processed chunks
CACHE_CLEANUP_DAYS = 30                # Remove cache older than X days

# Logging settings
LOG_LEVEL = "INFO"                      # DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE = True                      # Save logs to file
LOG_TO_CONSOLE = True                   # Display logs in terminal
