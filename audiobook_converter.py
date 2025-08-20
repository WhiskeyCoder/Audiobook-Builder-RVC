#!/usr/bin/env python3
"""
API-Based Audiobook Converter - Uses Applio REST API for chunk processing
Converts books by sending chunks to the API and assembling the results

Author: Your Name
License: MIT
"""

import os
import shutil
import logging
import hashlib
import requests
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import sys
import zipfile
import xml.etree.ElementTree as ET
from html import unescape
import re
from datetime import datetime
import PyPDF2
import ebooklib
from ebooklib import epub
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

# CONFIGURATION - EDIT THESE PATHS AND SETTINGS
BOOKS_FOLDER = "books_to_convert"
PTH_FILE = r"ADD_YOUR_RVC_MODEL_PATH_HERE.pth"  # Path to your RVC model file
INDEX_FILE = r"ADD_YOUR_RVC_INDEX_PATH_HERE.index"  # Path to your RVC index file
TTS_VOICE = "en-US-AvaNeural"  # Edge-TTS voice (see documentation for options)

# API Configuration
API_BASE_URL = "http://127.0.0.1:6970"  # Default Applio API endpoint
API_TIMEOUT = 300  # 5 minutes per chunk
MAX_RETRIES = 3

# Processing settings
CHUNK_SIZE_WORDS = 1200  # Words per chunk (adjust based on your needs)
MAX_WORKERS = 1  # Concurrent chunks (keep at 1 to avoid rate limiting)
AUDIO_FORMAT = "mp3"  # Output format: mp3, wav, etc.
AUDIO_BITRATE = "128k"  # Audio quality
RVC_PITCH_SHIFT = 0  # Pitch adjustment (-12 to +12 semitones)
TTS_RATE = 0  # Speech rate adjustment (-100 to +100)
MIN_DELAY_BETWEEN_CHUNKS = 3  # Seconds delay between API calls

# Optional imports with fallbacks
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import docx2txt
    DOC_AVAILABLE = True
except ImportError:
    DOC_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


class AudiobookConverter:
    """Converter that uses Applio API for processing chunks"""

    def __init__(self):
        self.setup_logging()
        self.setup_directories()
        self.validate_configuration()
        self.validate_api()

    def setup_logging(self):
        """Setup logging configuration"""
        Path("logs").mkdir(exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"logs/audiobook_{datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_directories(self):
        """Create necessary directories"""
        directories = [BOOKS_FOLDER, "audiobooks", "chunks", "cache/audio_chunks", "logs"]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def validate_configuration(self):
        """Validate configuration and file paths"""
        if "ADD_YOUR" in PTH_FILE or "ADD_YOUR" in INDEX_FILE:
            print("❌ Configuration Error!")
            print("Please edit the configuration section at the top of the script:")
            print(f"- PTH_FILE: Set path to your RVC model (.pth file)")
            print(f"- INDEX_FILE: Set path to your RVC index (.index file)")
            print("\nExample:")
            print('PTH_FILE = r"C:/path/to/your/model.pth"')
            print('INDEX_FILE = r"C:/path/to/your/model.index"')
            sys.exit(1)

        if not Path(PTH_FILE).exists():
            print(f"❌ RVC model file not found: {PTH_FILE}")
            print("Please check the PTH_FILE path in the configuration")
            sys.exit(1)

        if not Path(INDEX_FILE).exists():
            print(f"❌ RVC index file not found: {INDEX_FILE}")
            print("Please check the INDEX_FILE path in the configuration")
            sys.exit(1)

    def validate_api(self):
        """Check if Applio API is accessible"""
        try:
            response = requests.get(f"{API_BASE_URL}/", timeout=10)
            if response.status_code == 200:
                self.logger.info("✅ API server is accessible")
            else:
                raise Exception(f"API returned status {response.status_code}")
        except Exception as e:
            print("❌ Cannot connect to Applio API!")
            print(f"API endpoint: {API_BASE_URL}")
            print("Make sure:")
            print("1. Applio is running")
            print("2. The API server is enabled")
            print("3. The endpoint URL is correct")
            print(f"Error: {e}")
            sys.exit(1)

    def generate_chunk_via_api(self, text: str, chunk_num: int) -> Optional[str]:
        """Send chunk to API and get back audio file path"""
        try:
            # Check cache first
            cache_path = self.get_cache_path(text)
            if cache_path.exists():
                output_path = Path("chunks") / f"chunk_{chunk_num:04d}.wav"
                shutil.copy2(cache_path, output_path)
                return str(output_path)

            # Prepare API request
            request_data = {
                "text": text,
                "tts_voice": TTS_VOICE,
                "tts_rate": TTS_RATE,
                "rvc_model_path": PTH_FILE,
                "rvc_index_path": INDEX_FILE,
                "embedder_model": "contentvec",
                "pitch_shift": RVC_PITCH_SHIFT,
                "filename": f"chunk_{chunk_num:04d}.wav"
            }

            # Submit job to API
            self.logger.debug(f"Submitting chunk {chunk_num} to API")
            response = requests.post(
                f"{API_BASE_URL}/generate_audiobook",
                json=request_data,
                timeout=30
            )

            if response.status_code != 200:
                raise Exception(f"API request failed: {response.status_code}")

            job_id = response.json()["job_id"]
            self.logger.debug(f"Chunk {chunk_num} job ID: {job_id}")

            # Poll for completion
            max_wait = API_TIMEOUT
            poll_interval = 2
            waited = 0

            while waited < max_wait:
                status_response = requests.get(f"{API_BASE_URL}/status/{job_id}", timeout=10)
                if status_response.status_code == 200:
                    status = status_response.json()

                    if status["status"] == "completed":
                        # Download the result
                        download_response = requests.get(f"{API_BASE_URL}/download/{job_id}", timeout=30)
                        if download_response.status_code == 200:
                            output_path = Path("chunks") / f"chunk_{chunk_num:04d}.wav"
                            with open(output_path, 'wb') as f:
                                f.write(download_response.content)

                            # Cache the result
                            shutil.copy2(output_path, cache_path)

                            # Cleanup API job
                            requests.delete(f"{API_BASE_URL}/jobs/{job_id}")

                            self.logger.debug(f"Chunk {chunk_num} completed")
                            return str(output_path)

                    elif status["status"] == "failed":
                        error_msg = status.get("error", "Unknown error")
                        raise Exception(f"API job failed: {error_msg}")

                time.sleep(poll_interval)
                waited += poll_interval

            raise Exception(f"API job timed out after {max_wait} seconds")

        except Exception as e:
            self.logger.error(f"API chunk processing failed for chunk {chunk_num}: {e}")
            return None

    def process_chunk_with_retry(self, args: Tuple[int, str]) -> bool:
        """Process chunk with retry logic and rate limiting"""
        chunk_num, text = args

        # Stagger requests to avoid rate limiting
        delay = (chunk_num - 1) * MIN_DELAY_BETWEEN_CHUNKS
        if delay > 0:
            time.sleep(delay)

        for attempt in range(MAX_RETRIES):
            try:
                result = self.generate_chunk_via_api(text, chunk_num)
                if result and Path(result).exists():
                    return True
                else:
                    self.logger.warning(f"Chunk {chunk_num} attempt {attempt + 1} failed")
            except Exception as e:
                self.logger.warning(f"Chunk {chunk_num} attempt {attempt + 1} error: {e}")

            if attempt < MAX_RETRIES - 1:
                sleep_time = 5 + (2 ** attempt)
                self.logger.info(f"Waiting {sleep_time}s before retry...")
                time.sleep(sleep_time)

        self.logger.error(f"Chunk {chunk_num} failed after {MAX_RETRIES} attempts")
        return False

    def get_cache_path(self, text: str) -> Path:
        """Get cache path for text chunk"""
        content = f"{text}_{TTS_VOICE}_{PTH_FILE}_{RVC_PITCH_SHIFT}"
        hash_obj = hashlib.md5(content.encode())
        return Path("cache/audio_chunks") / f"{hash_obj.hexdigest()}.wav"

    def extract_text_from_epub(self, file_path: Path) -> str:
        """Extract text from EPUB with fallback methods"""
        methods = [
            self._extract_epub_ebooklib,
            self._extract_epub_zipfile,
            self._extract_epub_manual
        ]

        for method in methods:
            try:
                text = method(file_path)
                if text and text.strip():
                    self.logger.info(f"EPUB extraction successful: {len(text)} characters")
                    return text
            except Exception as e:
                self.logger.warning(f"EPUB method failed: {e}")
                continue

        raise RuntimeError("All EPUB extraction methods failed")

    def _extract_epub_ebooklib(self, file_path: Path) -> str:
        """Extract using ebooklib"""
        book = epub.read_epub(str(file_path))
        text_parts = []

        for item_id, linear in book.spine:
            try:
                item = book.get_item_by_id(item_id)
                if item and isinstance(item, ebooklib.ITEM_DOCUMENT):
                    content = item.get_body_content()
                    if content:
                        if isinstance(content, bytes):
                            content = content.decode('utf-8', errors='ignore')
                        clean_text = self._clean_html(str(content))
                        if clean_text.strip():
                            text_parts.append(clean_text)
            except Exception:
                continue

        return '\n\n'.join(text_parts)

    def _extract_epub_zipfile(self, file_path: Path) -> str:
        """Extract using zipfile parsing"""
        text_parts = []
        with zipfile.ZipFile(file_path, 'r') as epub_zip:
            for file_name in epub_zip.namelist():
                if file_name.lower().endswith(('.html', '.xhtml', '.htm')):
                    try:
                        content = epub_zip.read(file_name).decode('utf-8', errors='ignore')
                        clean_text = self._clean_html(content)
                        if clean_text.strip():
                            text_parts.append(clean_text)
                    except Exception:
                        continue
        return '\n\n'.join(text_parts)

    def _extract_epub_manual(self, file_path: Path) -> str:
        """Manual extraction fallback"""
        text_parts = []
        with zipfile.ZipFile(file_path, 'r') as epub_zip:
            for file_name in epub_zip.namelist():
                if not any(file_name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.css', '.js']):
                    try:
                        content = epub_zip.read(file_name).decode('utf-8', errors='ignore')
                        if '<' in content and len(content.strip()) > 100:
                            clean_text = self._clean_html(content)
                            if clean_text:
                                text_parts.append(clean_text)
                    except Exception:
                        continue
        return '\n\n'.join(text_parts)

    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content"""
        if not html_content:
            return ""

        if BS4_AVAILABLE:
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                return ' '.join(chunk for chunk in chunks if chunk)
            except Exception:
                pass

        # Fallback regex cleaning
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<[^>]+>', ' ', html_content)
        html_content = unescape(html_content)
        html_content = re.sub(r'\s+', ' ', html_content)
        return html_content.strip()

    def extract_text_from_file(self, file_path: Path) -> str:
        """Extract text from various file formats"""
        extension = file_path.suffix.lower()

        if extension == '.txt':
            return self._extract_txt(file_path)
        elif extension == '.pdf':
            return self._extract_pdf(file_path)
        elif extension == '.epub':
            return self.extract_text_from_epub(file_path)
        elif extension == '.docx' and DOCX_AVAILABLE:
            return self._extract_docx(file_path)
        elif extension == '.doc' and DOC_AVAILABLE:
            return self._extract_doc(file_path)
        else:
            raise ValueError(f"Unsupported file format: {extension}")

    def _extract_txt(self, file_path: Path) -> str:
        """Extract from TXT with encoding detection"""
        for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return self._clean_text(f.read())
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode text file")

    def _extract_pdf(self, file_path: Path) -> str:
        """Extract from PDF"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text += f"\n\n{page_text}"
                except Exception:
                    continue
        return self._clean_text(text)

    def _extract_docx(self, file_path: Path) -> str:
        """Extract from DOCX"""
        doc = Document(file_path)
        text = '\n\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
        return self._clean_text(text)

    def _extract_doc(self, file_path: Path) -> str:
        """Extract from DOC"""
        text = docx2txt.process(str(file_path))
        return self._clean_text(text) if text else ""

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\n', ' ')
        text = re.sub(r'\b\d{1,3}\b(?=\s|$)', '', text)
        return text.strip()

    def split_into_chunks(self, text: str) -> List[str]:
        """Split text into manageable chunks"""
        if not text.strip():
            return []

        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        current_words = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())

            if sentence_words > CHUNK_SIZE_WORDS:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                    current_words = 0

                # Split long sentences
                parts = re.split(r'[,;:]', sentence)
                for part in parts:
                    part_words = len(part.split())
                    if current_words + part_words <= CHUNK_SIZE_WORDS:
                        current_chunk += part + " "
                        current_words += part_words
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = part + " "
                        current_words = part_words
            else:
                if current_words + sentence_words <= CHUNK_SIZE_WORDS:
                    current_chunk += sentence + " "
                    current_words += sentence_words
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + " "
                    current_words = sentence_words

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return [chunk for chunk in chunks if chunk.strip()]

    def combine_chunks(self, total_chunks: int, output_path: Path) -> bool:
        """Combine audio chunks into final audiobook"""
        try:
            combined = AudioSegment.empty()
            successful = 0

            for i in range(1, total_chunks + 1):
                chunk_file = Path("chunks") / f"chunk_{i:04d}.wav"
                if chunk_file.exists():
                    try:
                        chunk_audio = AudioSegment.from_wav(str(chunk_file))
                        combined += chunk_audio
                        successful += 1
                        if successful % 10 == 0:
                            self.logger.info(f"Combined {successful}/{total_chunks} chunks")
                    except Exception as e:
                        self.logger.warning(f"Failed to load chunk {i}: {e}")

            if successful == 0:
                raise RuntimeError("No valid chunks found")

            combined.export(str(output_path), format=AUDIO_FORMAT, bitrate=AUDIO_BITRATE)
            self.logger.info(f"Audiobook saved: {output_path} ({successful}/{total_chunks} chunks)")
            return True

        except Exception as e:
            self.logger.error(f"Failed to combine chunks: {e}")
            return False

    def cleanup_chunks(self):
        """Remove temporary chunk files"""
        try:
            for chunk_file in Path("chunks").glob("chunk_*.wav"):
                chunk_file.unlink()
            self.logger.info("Cleaned up temporary files")
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")

    def convert_book(self, file_path: Path) -> bool:
        """Convert a single book to audiobook using API"""
        self.logger.info(f"Converting: {file_path.name}")
        start_time = time.time()

        try:
            # Extract text
            self.logger.info("Extracting text...")
            text = self.extract_text_from_file(file_path)
            if not text.strip():
                self.logger.error("No text extracted")
                return False

            self.logger.info(f"Extracted {len(text)} characters")

            # Split into chunks
            chunks = self.split_into_chunks(text)
            total_chunks = len(chunks)
            if total_chunks == 0:
                self.logger.error("No chunks created")
                return False

            self.logger.info(f"Processing {total_chunks} chunks via API...")

            # Process chunks in parallel via API
            chunk_args = [(i + 1, chunk) for i, chunk in enumerate(chunks)]

            print(f"\n{'=' * 50}")
            print(f"PROCESSING {total_chunks} CHUNKS")
            print(f"{'=' * 50}")

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_chunk = {
                    executor.submit(self.process_chunk_with_retry, args): args[0]
                    for args in chunk_args
                }

                results = []
                completed = 0

                for future in as_completed(future_to_chunk):
                    chunk_num = future_to_chunk[future]
                    try:
                        result = future.result()
                        results.append(result)
                        completed += 1

                        if result:
                            print(f"✅ Chunk {chunk_num:3d}/{total_chunks} completed ({completed}/{total_chunks} total)")
                            self.logger.info(f"+ Chunk {chunk_num}/{total_chunks} completed")
                        else:
                            print(f"❌ Chunk {chunk_num:3d}/{total_chunks} FAILED    ({completed}/{total_chunks} total)")
                            self.logger.error(f"- Chunk {chunk_num}/{total_chunks} failed")

                    except Exception as e:
                        results.append(False)
                        completed += 1
                        print(f"❌ Chunk {chunk_num:3d}/{total_chunks} ERROR     ({completed}/{total_chunks} total)")
                        self.logger.error(f"- Chunk {chunk_num}/{total_chunks} error: {e}")

            successful_chunks = sum(results)
            print(f"\n{'=' * 50}")
            print(f"CHUNK PROCESSING COMPLETE")
            print(f"Successful: {successful_chunks}/{total_chunks}")
            print(f"{'=' * 50}")
            self.logger.info(f"API processing completed: {successful_chunks}/{total_chunks} chunks")

            if successful_chunks == 0:
                self.logger.error("No chunks were successfully processed")
                return False

            # Combine chunks
            output_path = Path("audiobooks") / f"{file_path.stem}.{AUDIO_FORMAT}"
            success = self.combine_chunks(total_chunks, output_path)

            if success:
                duration = time.time() - start_time
                self.logger.info(f"Conversion completed in {duration:.1f}s: {output_path}")

            # Cleanup
            self.cleanup_chunks()
            return success

        except Exception as e:
            self.logger.error(f"Conversion failed: {e}")
            return False

    def run(self):
        """Main conversion process"""
        print("=" * 70)
        print("🎧 API-BASED AUDIOBOOK CONVERTER")
        print("=" * 70)
        print(f"📚 Books folder: {BOOKS_FOLDER}")
        print(f"🌐 API endpoint: {API_BASE_URL}")
        print(f"🎤 RVC model: {Path(PTH_FILE).name}")
        print(f"🗣️  TTS voice: {TTS_VOICE}")
        print(f"🎵 Output format: {AUDIO_FORMAT}")
        print(f"⚡ Max workers: {MAX_WORKERS}")
        print("=" * 70)

        # Check for books
        books_dir = Path(BOOKS_FOLDER)
        supported_formats = ['.txt', '.pdf', '.epub']
        if DOCX_AVAILABLE:
            supported_formats.append('.docx')
        if DOC_AVAILABLE:
            supported_formats.append('.doc')

        book_files = [f for f in books_dir.iterdir()
                      if f.is_file() and f.suffix.lower() in supported_formats]

        if not book_files:
            print(f"📂 No supported files found in {BOOKS_FOLDER}")
            print(f"📋 Supported formats: {', '.join(supported_formats)}")

            # Create sample file
            sample_file = books_dir / "sample.txt"
            with open(sample_file, 'w') as f:
                f.write("This is a sample audiobook for testing the API-based converter. "
                        "The system will send this text to the Applio API for TTS and RVC processing. "
                        "You can replace this file with your own books to convert.")
            print(f"📝 Created sample file: {sample_file}")
            return

        print(f"📚 Found {len(book_files)} books to convert")

        # Convert each book
        results = {}
        for book_file in book_files:
            try:
                success = self.convert_book(book_file)
                results[book_file.name] = success
            except KeyboardInterrupt:
                print("\n⚠️ Conversion interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                results[book_file.name] = False

        # Print summary
        successful = sum(results.values())
        total = len(results)

        print("\n" + "=" * 70)
        print("📊 CONVERSION SUMMARY")
        print("=" * 70)
        print(f"📈 Total: {total} | Success: {successful} | Failed: {total - successful}")
        print("=" * 70)

        for filename, success in results.items():
            status = "✅" if success else "❌"
            print(f"{status} {filename}")

        if successful > 0:
            print(f"\n🎧 Audiobooks saved to: audiobooks/")


def main():
    """Entry point"""
    try:
        converter = AudiobookConverter()
        converter.run()
    except KeyboardInterrupt:
        print("\n⚠️ Shutdown requested by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
