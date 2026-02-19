# Research Hive: Complete Build Plan

**Project:** Content Research Hive - Autonomous research assistant for 8-9 years of teaching/content corpus
**Status:** Pre-build, ready for execution
**Date:** 2026-02-17
**Target completion:** 23-31 working hours (5-7 days)

This document contains the complete build specification for VPS-Claude to execute. All technical decisions are made. All dependencies are specified. Execute sequentially.

---

## Table of Contents

- **PART 1:** Project Overview & Architecture
- **PART 2:** Infrastructure & Dependencies (R0-R1)
- **PART 3:** Core Workers (R2-R5)
- **PART 4:** Integration & UI (R6)
- **PART 5:** Testing & Validation

---

# PART 1: PROJECT OVERVIEW & ARCHITECTURE

## What this is

A conversational research assistant that indexes Alex's 8-9 year corpus of teaching materials (workshops, scripts, notes, transcripts) and enables:

1. **Discovery:** "Show me everything I've written about X"
2. **Rebranding:** "How would I reframe this 2018 content for my current brand?"
3. **Structure discovery:** "What could these fragments become?"
4. **Quote bank:** "Give me 20 usable one-liners on topic X"

The system does NOT write final content. It retrieves, organizes, and critiques. Alex writes.

## Core principles

- **Transparency:** Always show what's being pulled and why
- **Steerability:** Human-in-the-loop at every decision point
- **Privacy:** Corpus never leaves the VPS
- **Modularity:** Can later integrate into main Hive-Office as optional worker set
- **Iteration:** Support versioned outputs (research_packet_v001, v002, etc.)

## Architecture overview

```
┌─────────────────────────────────────────────────────────────┐
│                      RESEARCH HIVE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  INPUT: Syncthing ──> File Watcher ──> Ingestion Pipeline  │
│         (Desktop)     (Monitors)       (Converts, chunks,   │
│                                         embeds, indexes)    │
│                                                             │
│  STORAGE: LanceDB (vectors) + SQLite (metadata)            │
│                                                             │
│  WORKERS:                                                   │
│    • Librarian  - Semantic retrieval with citations        │
│    • Architect  - Thematic organization, gap detection     │
│    • Critic     - Brand principles enforcement             │
│                                                             │
│  INTERFACE: Gradio Chat UI                                 │
│    - Conversational interaction                            │
│    - Multi-panel view (chat, results, sources)            │
│    - Version management                                    │
│                                                             │
│  OUTPUT: Research packets (markdown) ──> Syncthing         │
│                                          (Back to desktop) │
└─────────────────────────────────────────────────────────────┘
```

## Tech stack (specific versions)

| Component | Tool | Version | Why |
|---|---|---|---|
| Vector DB | LanceDB | 0.5+ | Embedded, fast, Python-native |
| Embeddings | sentence-transformers | 2.2+ | Local, no API costs |
| Embedding model | all-MiniLM-L6-v2 | Latest | Fast, good for English |
| LLM (workers) | Gemini Flash via API | 2.0 | Cheap, fast |
| Chat UI | Gradio | 4.0+ | Simple, hot-reloads |
| File sync | Syncthing | Existing | Already in use |
| Transcription | Whisper API | v1 | Cheap, accurate |
| Metadata store | SQLite | 3.40+ | Lightweight, built-in |
| File watching | watchdog | 3.0+ | Cross-platform |
| Doc conversion | pypandoc, PyPDF2 | Latest | Format handling |

## Directory structure (complete)

```
~/research-hive/                    # Project root
│
├── CLAUDE.md                       # Build rules for VPS-Claude
├── STATUS.md                       # Progress tracking
├── README.md                       # User documentation
├── requirements.txt                # Python dependencies
│
├── data/                          # Permanent storage (NOT synced)
│   ├── lancedb/                   # Vector database files
│   ├── metadata.db                # SQLite metadata
│   └── embeddings_cache/          # Cached embeddings
│
├── workspace/                     # Project outputs (synced to desktop)
│   └── projects/
│       ├── workshop_pricing_2026/
│       │   ├── research_packet_v001.md
│       │   ├── structure_v001.md
│       │   └── critique_v001.md
│       └── book_chapter_04/
│
├── workers/                       # Worker scripts
│   ├── librarian.py              # Semantic retrieval
│   ├── architect.py              # Thematic organization
│   └── critic.py                 # Brand enforcement
│
├── core/                         # Core utilities
│   ├── ingestion.py              # File conversion & indexing
│   ├── chunker.py                # Text chunking
│   ├── embedder.py               # Embedding generation
│   ├── search.py                 # LanceDB query wrapper
│   └── metadata.py               # SQLite operations
│
├── ui/                           # Gradio interface
│   └── app.py                    # Main UI application
│
├── config/                       # Configuration
│   ├── config.yaml               # System config
│   ├── BRAND_PRINCIPLES.md       # Alex's brand rules
│   └── BRAND_VOICE_EXAMPLES.md   # Example-based training
│
└── tests/                        # Test suite
    ├── test_ingestion.py
    ├── test_search.py
    └── test_workers.py
```

## External directories (on VPS but outside project)

```
~/content-vault/                   # The corpus (synced from desktop)
│
├── raw_media/                    # Workshop recordings (not indexed)
├── transcripts/                  # Auto-generated (indexed)
├── notes/                        # Markdown notes (indexed)
├── workshops/                    # Workshop materials (indexed)
├── scripts/                      # Video scripts (indexed)
├── client_work/                  # Relevant deliverables (indexed)
└── archive/                      # Old content (indexed)
```

## Data scale estimates

- **Files:** 2,000-5,000 individual pieces
- **Text volume:** 500MB-2GB after transcription
- **Tokens:** 20-50 million when chunked
- **Embeddings storage:** 1-3GB
- **Metadata:** 10-50MB
- **Total VPS usage:** 5-10GB (VPS has 320GB available)

## Interaction modes (four patterns)

The system supports four distinct workflows:

### Mode 1: Discovery
**Query:** "Show me everything I've written about personal branding"
**Output:** 50-100 chunks, grouped by year, duplicates flagged
**Use:** Landscape view before deciding what to build

### Mode 2: Rebranding
**Query:** "Reframe this 2018 script for my current brand"
**Output:** Structure comparison, brand violations flagged, suggestions
**Use:** Salvage good ideas from off-brand old content

### Mode 3: Structure Discovery
**Query:** "What could these 12 fragments become?"
**Output:** 3 suggested structures (workshop, video series, article)
**Use:** Turn scattered pieces into coherent projects

### Mode 4: Quote Bank
**Query:** "Give me 20 one-liners on pricing for social posts"
**Output:** Short, punchy quotes, brand-filtered
**Use:** Quick content creation

## Quality standards

- **Retrieval precision:** Top 30 results must include at least 25 relevant chunks (83%+)
- **Citation accuracy:** Every chunk must include correct source file path
- **Brand alignment:** Critic must flag 100% of clear principle violations
- **Response time:** Queries return in <3 seconds
- **UI responsiveness:** No blocking operations in the main thread

## Commit discipline

- Format: `RX.Y: description` (e.g., "R1.2: implement chunking with overlap")
- Gate commits: `RX GATE: description` at phase boundaries
- One commit per logical change
- Never commit broken code

---

# PART 2: INFRASTRUCTURE & DEPENDENCIES (R0-R1)

## R0: Infrastructure Setup

**Goal:** Directory structure, Syncthing configured, dependencies installed

### R0.1: Directory scaffolding

Create the complete directory structure:

```bash
cd ~
mkdir -p research-hive/{data/{lancedb,embeddings_cache},workspace/projects,workers,core,ui,config,tests}
mkdir -p content-vault/{raw_media,transcripts,notes,workshops,scripts,client_work,archive}
cd research-hive
```

### R0.2: Python environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Create requirements.txt
cat > requirements.txt << 'EOF'
# Vector DB and embeddings
lancedb>=0.5.0
sentence-transformers>=2.2.0
torch>=2.0.0  # For sentence-transformers

# LLM integration
google-generativeai>=0.3.0

# File processing
watchdog>=3.0.0
pypandoc>=1.11
PyPDF2>=3.0.0
python-docx>=0.8.11
beautifulsoup4>=4.12.0
lxml>=4.9.0

# UI
gradio>=4.0.0

# Utilities
pyyaml>=6.0
pytest>=7.4.0
ruff>=0.1.0

EOF

# Install dependencies
pip install -r requirements.txt

# Download embedding model (one-time, ~80MB)
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### R0.3: Syncthing configuration

**On desktop (Alex does this):**
1. Add `~/Downloads/ContentVault/` to Syncthing
2. Share with VPS device
3. Set to send-only

**On VPS (you do this):**
```bash
# Verify Syncthing is running
systemctl status syncthing@$(whoami)

# Configure folder
# Web UI: http://localhost:8384
# Add folder: ~/content-vault
# Connect to Alex's device
# Set to receive-only
# Save config
```

**Test:**
```bash
# Alex: Create test file on desktop
echo "Test sync" > ~/Downloads/ContentVault/test_sync.txt

# VPS: Wait 30 seconds, then check
ls -la ~/content-vault/test_sync.txt

# Should exist. If yes, Syncthing works.
```

### R0.4: Core configuration files

**config/config.yaml:**
```yaml
# Research Hive Configuration

# Paths
vault_path: ~/content-vault
data_path: ~/research-hive/data
workspace_path: ~/research-hive/workspace

# LanceDB settings
vector_db:
  path: ~/research-hive/data/lancedb
  table_name: content_chunks
  
# Embedding settings
embeddings:
  model: sentence-transformers/all-MiniLM-L6-v2
  cache_path: ~/research-hive/data/embeddings_cache
  chunk_size: 500  # tokens
  chunk_overlap: 100  # tokens
  batch_size: 32

# LLM settings (Gemini Flash)
llm:
  provider: google
  model: gemini-2.0-flash-exp
  api_key_env: GEMINI_API_KEY
  temperature: 0.3
  max_tokens: 2048

# Search settings
search:
  default_top_k: 30
  similarity_threshold: 0.5
  
# File watcher
watcher:
  enabled: true
  scan_interval: 30  # seconds
  supported_extensions:
    - .txt
    - .md
    - .docx
    - .pdf
    - .html
    - .srt
    - .vtt
    - .json
    
# UI settings
ui:
  host: 127.0.0.1
  port: 7860
  share: false  # Set true for ngrok tunnel
  theme: soft
```

**config/BRAND_PRINCIPLES.md:**
```markdown
# Brand Principles

## Core principles (non-negotiable)
- Strategy before tactics. Never give a "how to" without the "why."
- No quick wins. No hacks. No shortcuts framed as solutions.
- Depth over breadth. One thing explained thoroughly beats three things mentioned.
- Show the work. Don't just state conclusions. Show reasoning.

## Voice rules
- Confident without being loud. Observational. State things.
- No hedging ("I think," "maybe," "it seems").
- No apologizing for having done good work.
- Direct observation. Trust the reader to evaluate.

## Red lines (never do this)
- Do not use "hack," "secret," "trick" as positive framing.
- Do not promise outcomes ("this will 10x your revenue").
- Do not treat readers as non-thinkers who need step-by-step without understanding.
- Avoid generic business clichés (game-changer, leverage, synergy, etc.)

## Structural patterns
- Always explain the pattern before the example.
- Always name the trade-off. Never present one approach as universally correct.
- Conclusions come from evidence, not assertion.
- Lists and bullets for organization, not as default writing mode.
```

**config/BRAND_VOICE_EXAMPLES.md:**
```markdown
# Brand Voice Examples

## Good examples (sounds like Alex)

"The pattern is simple. Most businesses overvalue tactics and undervalue strategy. Not because they're stupid. Because tactics are concrete and strategy feels abstract. But abstract work is what scales."

"You don't need more content. You need better thinking. One deep idea beats ten shallow posts. Every time."

"Trust over speed. Never claim success without evidence. If you say you fixed it, prove the fix."

## Bad examples (don't sound like Alex)

"In today's fast-paced world, businesses must leverage cutting-edge strategies to optimize their value propositions and foster meaningful customer relationships."

"Here are 7 secrets to 10x your revenue! (You won't believe #4!)"

"It's important to note that personal branding is a journey, not a destination."
```

### R0.5: Project documentation

**CLAUDE.md:**
```markdown
# Research Hive - Build Rules

## What this is
Conversational research assistant for Alex's 8-9 year content corpus.
Retrieves, organizes, critiques. Does NOT write final content.

## Architecture
- Base: Standalone Python project (later integrates into Hive-Office)
- Vector DB: LanceDB (embedded, no server)
- Embeddings: sentence-transformers (local, no API)
- LLM: Gemini Flash (cheap, fast)
- UI: Gradio (hot-reload, simple)
- Sync: Syncthing (already configured)

## Constraints
- All corpus data stays on VPS (privacy)
- No external vector DB services
- Keep files under 300 lines each
- Support iteration (versioned outputs)
- Human-in-the-loop for all decisions
- Never auto-generate final content

## Testing
- Automated: pytest tests/
- Manual: Alex tests via browser UI
- Never skip tests to save time

## Commit discipline
- Format: "RX.Y: description"
- Gate commits: "RX GATE: description"
- One commit per logical change

## Current step
See STATUS.md for progress.

## Reference materials
- LanceDB docs: https://lancedb.github.io/lancedb/
- sentence-transformers: https://www.sbert.net/
- Gradio docs: https://www.gradio.app/docs/
```

**STATUS.md:**
```markdown
# STATUS.md

## Current step: R0 (Infrastructure setup)
## Last commit: (none yet)

## Completed
- (none yet)

## Blockers
- (none yet)

## Deviations from plan
- (none yet)

## Open questions
- (none yet)
```

**README.md:**
```markdown
# Research Hive

Conversational research assistant for 8-9 years of teaching content.

## Quick start

1. Activate environment: `source venv/bin/activate`
2. Start UI: `python ui/app.py`
3. Open browser: http://localhost:7860

## Adding content

Drop files into `~/Downloads/ContentVault/` on desktop.
Syncthing syncs to VPS. Automatic indexing happens within 60 seconds.

## Supported formats

- Text: .txt, .md, .html
- Documents: .docx, .pdf
- Transcripts: .srt, .vtt
- Structured: .json, .yaml

## Query modes

- Discovery: "Show me everything on [topic]"
- Rebranding: "Reframe this [old content] for current brand"
- Structure: "What could these fragments become?"
- Quotes: "Give me 20 one-liners on [topic]"

## Project structure

- `data/` - Vector DB and metadata (not synced)
- `workspace/` - Research packets (synced to desktop)
- `workers/` - Librarian, Architect, Critic
- `core/` - Ingestion, search, utilities
- `ui/` - Gradio interface
```

### R0.6: Git initialization

```bash
cd ~/research-hive

# Initialize repo
git init

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/
.pytest_cache/

# Data (too large, regenerable)
data/lancedb/
data/embeddings_cache/
data/*.db

# Workspace (synced separately)
workspace/

# Config secrets
config/.env
*.key

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
EOF

# Initial commit
git add .
git commit -m "R0: infrastructure scaffold"
```

**Commit:** `R0 GATE: infrastructure ready, Syncthing verified`

---

## R1: Ingestion Pipeline

**Goal:** Any file format → indexed chunks with metadata

### R1.1: File conversion utilities

**core/converters.py:**
```python
"""File format converters - all formats to plain text."""
import os
from pathlib import Path
from typing import Optional
import pypandoc
import PyPDF2
import docx
from bs4 import BeautifulSoup


class FileConverter:
    """Convert various file formats to plain text."""
    
    @staticmethod
    def convert(file_path: str) -> Optional[str]:
        """
        Convert any supported file to plain text.
        
        Returns None if conversion fails.
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        try:
            if extension == '.txt' or extension == '.md':
                return FileConverter._read_text(file_path)
            elif extension == '.docx':
                return FileConverter._convert_docx(file_path)
            elif extension == '.pdf':
                return FileConverter._convert_pdf(file_path)
            elif extension == '.html':
                return FileConverter._convert_html(file_path)
            elif extension in ['.srt', '.vtt']:
                return FileConverter._convert_subtitle(file_path)
            elif extension == '.json':
                return FileConverter._read_text(file_path)  # Keep as-is
            else:
                print(f"Unsupported format: {extension}")
                return None
        except Exception as e:
            print(f"Conversion failed for {file_path}: {e}")
            return None
    
    @staticmethod
    def _read_text(file_path: str) -> str:
        """Read plain text file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    @staticmethod
    def _convert_docx(file_path: str) -> str:
        """Convert DOCX to text."""
        doc = docx.Document(file_path)
        return '\n\n'.join([para.text for para in doc.paragraphs])
    
    @staticmethod
    def _convert_pdf(file_path: str) -> str:
        """Convert PDF to text."""
        text = []
        with open(file_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            for page in pdf.pages:
                text.append(page.extract_text())
        return '\n\n'.join(text)
    
    @staticmethod
    def _convert_html(file_path: str) -> str:
        """Convert HTML to text."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'lxml')
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()
            return soup.get_text(separator='\n', strip=True)
    
    @staticmethod
    def _convert_subtitle(file_path: str) -> str:
        """Convert SRT/VTT subtitle file to text."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Extract only the text lines (skip timestamps and indices)
        text_lines = []
        for line in lines:
            line = line.strip()
            # Skip empty lines, indices, and timestamps
            if line and not line.isdigit() and '-->' not in line:
                text_lines.append(line)
        
        return ' '.join(text_lines)
```

### R1.2: Text chunking

**core/chunker.py:**
```python
"""Text chunking with overlap for semantic coherence."""
from typing import List, Dict
import tiktoken


class TextChunker:
    """Chunk text into overlapping segments."""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target tokens per chunk
            overlap: Overlap tokens between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoder = tiktoken.get_encoding("cl100k_base")
    
    def chunk(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Chunk text with overlap.
        
        Returns list of chunks with metadata:
        {
            'text': str,
            'tokens': int,
            'chunk_index': int,
            'metadata': dict
        }
        """
        if not text or not text.strip():
            return []
        
        # Tokenize
        tokens = self.encoder.encode(text)
        
        # If text is shorter than chunk_size, return as single chunk
        if len(tokens) <= self.chunk_size:
            return [{
                'text': text,
                'tokens': len(tokens),
                'chunk_index': 0,
                'metadata': metadata or {}
            }]
        
        # Chunk with overlap
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoder.decode(chunk_tokens)
            
            chunks.append({
                'text': chunk_text,
                'tokens': len(chunk_tokens),
                'chunk_index': chunk_index,
                'metadata': metadata or {}
            })
            
            chunk_index += 1
            start += self.chunk_size - self.overlap
        
        return chunks
```

### R1.3: Embedding generation

**core/embedder.py:**
```python
"""Embedding generation using sentence-transformers."""
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
import hashlib
import pickle
from pathlib import Path


class Embedder:
    """Generate and cache embeddings."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', cache_dir: str = None):
        """Initialize embedder with caching."""
        self.model = SentenceTransformer(model_name)
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def embed(self, texts: List[str], use_cache: bool = True) -> np.ndarray:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of text strings
            use_cache: Use cached embeddings if available
        
        Returns:
            numpy array of shape (len(texts), 384)
        """
        if not texts:
            return np.array([])
        
        # Check cache
        if use_cache and self.cache_dir:
            cached = self._load_from_cache(texts)
            if cached is not None:
                return cached
        
        # Generate embeddings
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        # Cache results
        if use_cache and self.cache_dir:
            self._save_to_cache(texts, embeddings)
        
        return embeddings
    
    def _cache_key(self, texts: List[str]) -> str:
        """Generate cache key from texts."""
        text_hash = hashlib.md5(''.join(texts).encode()).hexdigest()
        return f"{text_hash}.pkl"
    
    def _load_from_cache(self, texts: List[str]) -> np.ndarray:
        """Load embeddings from cache."""
        cache_file = self.cache_dir / self._cache_key(texts)
        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None
    
    def _save_to_cache(self, texts: List[str], embeddings: np.ndarray):
        """Save embeddings to cache."""
        cache_file = self.cache_dir / self._cache_key(texts)
        with open(cache_file, 'wb') as f:
            pickle.dump(embeddings, f)
```

### R1.4: Metadata database

**core/metadata.py:**
```python
"""SQLite metadata storage for file tracking."""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import hashlib


class MetadataDB:
    """SQLite database for file metadata."""
    
    def __init__(self, db_path: str):
        """Initialize database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    file_hash TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    file_type TEXT,
                    indexed_at TEXT NOT NULL,
                    chunk_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'indexed'
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    token_count INTEGER,
                    FOREIGN KEY (file_hash) REFERENCES files(file_hash)
                )
            ''')
            
            conn.execute('CREATE INDEX IF NOT EXISTS idx_file_path ON files(file_path)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON chunks(file_hash)')
            conn.commit()
    
    def file_hash(self, file_path: str) -> str:
        """Generate hash for file."""
        path = Path(file_path)
        # Hash: path + size + mtime (detects changes)
        stat = path.stat()
        content = f"{path}{stat.st_size}{stat.st_mtime}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_indexed(self, file_path: str) -> bool:
        """Check if file is already indexed."""
        file_hash = self.file_hash(file_path)
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                'SELECT 1 FROM files WHERE file_hash = ?',
                (file_hash,)
            ).fetchone()
            return result is not None
    
    def add_file(self, file_path: str, chunk_count: int):
        """Add file metadata."""
        path = Path(file_path)
        file_hash = self.file_hash(file_path)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO files 
                (file_hash, file_path, file_name, file_size, file_type, indexed_at, chunk_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_hash,
                str(path),
                path.name,
                path.stat().st_size,
                path.suffix,
                datetime.now().isoformat(),
                chunk_count
            ))
            conn.commit()
    
    def add_chunk(self, chunk_id: str, file_hash: str, chunk_index: int, 
                  chunk_text: str, token_count: int):
        """Add chunk metadata."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO chunks
                (chunk_id, file_hash, chunk_index, chunk_text, token_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (chunk_id, file_hash, chunk_index, chunk_text, token_count))
            conn.commit()
    
    def get_file_info(self, file_hash: str) -> Optional[Dict]:
        """Get file metadata."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                'SELECT * FROM files WHERE file_hash = ?',
                (file_hash,)
            ).fetchone()
            return dict(row) if row else None
    
    def list_files(self) -> List[Dict]:
        """List all indexed files."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('SELECT * FROM files ORDER BY indexed_at DESC').fetchall()
            return [dict(row) for row in rows]
    
    def stats(self) -> Dict:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            file_count = conn.execute('SELECT COUNT(*) FROM files').fetchone()[0]
            chunk_count = conn.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]
            total_tokens = conn.execute('SELECT SUM(token_count) FROM chunks').fetchone()[0] or 0
            
            return {
                'files': file_count,
                'chunks': chunk_count,
                'total_tokens': total_tokens
            }
```

### R1.5: LanceDB integration

**core/search.py:**
```python
"""LanceDB vector search wrapper."""
import lancedb
from pathlib import Path
from typing import List, Dict
import pyarrow as pa


class VectorSearch:
    """LanceDB search interface."""
    
    def __init__(self, db_path: str, table_name: str = 'content_chunks'):
        """Initialize LanceDB connection."""
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(str(self.db_path))
        self.table_name = table_name
        self.table = None
        
    def create_table(self):
        """Create table with schema."""
        schema = pa.schema([
            pa.field("chunk_id", pa.string()),
            pa.field("file_hash", pa.string()),
            pa.field("file_path", pa.string()),
            pa.field("chunk_index", pa.int32()),
            pa.field("chunk_text", pa.string()),
            pa.field("token_count", pa.int32()),
            pa.field("vector", pa.list_(pa.float32(), 384))  # all-MiniLM-L6-v2 dim
        ])
        
        # Create empty table
        self.table = self.db.create_table(self.table_name, schema=schema, mode="overwrite")
    
    def open_table(self):
        """Open existing table."""
        if self.table_name in self.db.table_names():
            self.table = self.db.open_table(self.table_name)
        else:
            self.create_table()
    
    def add_chunks(self, chunks: List[Dict]):
        """
        Add chunks to vector DB.
        
        chunks: List of dicts with:
            - chunk_id
            - file_hash
            - file_path
            - chunk_index
            - chunk_text
            - token_count
            - vector (384-dim numpy array)
        """
        if not chunks:
            return
        
        if self.table is None:
            self.open_table()
        
        # Convert to PyArrow format
        data = []
        for chunk in chunks:
            data.append({
                'chunk_id': chunk['chunk_id'],
                'file_hash': chunk['file_hash'],
                'file_path': chunk['file_path'],
                'chunk_index': chunk['chunk_index'],
                'chunk_text': chunk['chunk_text'],
                'token_count': chunk['token_count'],
                'vector': chunk['vector'].tolist()
            })
        
        self.table.add(data)
    
    def search(self, query_vector, top_k: int = 30, 
               filter_expr: str = None) -> List[Dict]:
        """
        Search for similar chunks.
        
        Args:
            query_vector: Query embedding (384-dim)
            top_k: Number of results
            filter_expr: Optional SQL filter
        
        Returns:
            List of results with distance scores
        """
        if self.table is None:
            self.open_table()
        
        query = self.table.search(query_vector.tolist()).limit(top_k)
        
        if filter_expr:
            query = query.where(filter_expr)
        
        results = query.to_list()
        
        # Add distance as similarity score (lower = more similar)
        for result in results:
            result['similarity'] = 1 / (1 + result['_distance'])
        
        return results
    
    def count(self) -> int:
        """Get total chunk count."""
        if self.table is None:
            return 0
        return self.table.count_rows()
```

### R1.6: Main ingestion orchestrator

**core/ingestion.py:**
```python
"""Main ingestion pipeline - coordinates all components."""
from pathlib import Path
from typing import List, Dict
import hashlib
from .converters import FileConverter
from .chunker import TextChunker
from .embedder import Embedder
from .search import VectorSearch
from .metadata import MetadataDB


class IngestionPipeline:
    """Coordinate file conversion, chunking, embedding, and indexing."""
    
    def __init__(self, config: Dict):
        """Initialize pipeline components."""
        self.config = config
        
        # Initialize components
        self.converter = FileConverter()
        self.chunker = TextChunker(
            chunk_size=config['embeddings']['chunk_size'],
            overlap=config['embeddings']['chunk_overlap']
        )
        self.embedder = Embedder(
            model_name=config['embeddings']['model'],
            cache_dir=config['embeddings']['cache_path']
        )
        self.vector_db = VectorSearch(
            db_path=config['vector_db']['path'],
            table_name=config['vector_db']['table_name']
        )
        self.metadata_db = MetadataDB(
            db_path=f"{config['data_path']}/metadata.db"
        )
    
    def process_file(self, file_path: str) -> bool:
        """
        Process a single file through the full pipeline.
        
        Returns True if successful, False otherwise.
        """
        path = Path(file_path)
        
        # Check if already indexed
        if self.metadata_db.is_indexed(str(path)):
            print(f"Skipping (already indexed): {path.name}")
            return False
        
        print(f"Processing: {path.name}")
        
        # Step 1: Convert to text
        text = self.converter.convert(str(path))
        if not text:
            print(f"  ✗ Conversion failed")
            return False
        
        # Step 2: Chunk
        file_hash = self.metadata_db.file_hash(str(path))
        chunks = self.chunker.chunk(text, metadata={
            'file_path': str(path),
            'file_name': path.name,
            'file_hash': file_hash
        })
        
        if not chunks:
            print(f"  ✗ No chunks generated")
            return False
        
        print(f"  Generated {len(chunks)} chunks")
        
        # Step 3: Generate embeddings
        chunk_texts = [c['text'] for c in chunks]
        embeddings = self.embedder.embed(chunk_texts)
        
        # Step 4: Prepare for vector DB
        vector_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(
                f"{file_hash}_{chunk['chunk_index']}".encode()
            ).hexdigest()
            
            vector_chunks.append({
                'chunk_id': chunk_id,
                'file_hash': file_hash,
                'file_path': str(path),
                'chunk_index': chunk['chunk_index'],
                'chunk_text': chunk['text'],
                'token_count': chunk['tokens'],
                'vector': embeddings[i]
            })
            
            # Add to metadata DB
            self.metadata_db.add_chunk(
                chunk_id=chunk_id,
                file_hash=file_hash,
                chunk_index=chunk['chunk_index'],
                chunk_text=chunk['text'],
                token_count=chunk['tokens']
            )
        
        # Step 5: Add to vector DB
        self.vector_db.add_chunks(vector_chunks)
        
        # Step 6: Update metadata
        self.metadata_db.add_file(str(path), len(chunks))
        
        print(f"  ✓ Indexed successfully")
        return True
    
    def process_directory(self, directory: str) -> Dict:
        """
        Process all files in a directory recursively.
        
        Returns summary statistics.
        """
        vault = Path(directory)
        
        # Get all supported files
        extensions = self.config['watcher']['supported_extensions']
        files = []
        for ext in extensions:
            files.extend(vault.rglob(f"*{ext}"))
        
        print(f"Found {len(files)} files to process")
        
        stats = {
            'total': len(files),
            'processed': 0,
            'skipped': 0,
            'failed': 0
        }
        
        for file_path in files:
            result = self.process_file(str(file_path))
            if result:
                stats['processed'] += 1
            else:
                stats['skipped'] += 1
        
        return stats
```

### R1.7: File watcher

**core/watcher.py:**
```python
"""File system watcher for automatic ingestion."""
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .ingestion import IngestionPipeline


class VaultWatcher(FileSystemEventHandler):
    """Watch vault directory for new files."""
    
    def __init__(self, pipeline: IngestionPipeline, config: Dict):
        """Initialize watcher."""
        self.pipeline = pipeline
        self.config = config
        self.processing = set()  # Track files being processed
    
    def on_created(self, event):
        """Handle new file creation."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Check if supported extension
        if file_path.suffix not in self.config['watcher']['supported_extensions']:
            return
        
        # Ignore temp files
        if file_path.name.startswith('.') or file_path.name.startswith('~'):
            return
        
        # Wait for file to be fully written (Syncthing)
        time.sleep(2)
        
        # Check if file is stable (size not changing)
        if not self._is_stable(file_path):
            return
        
        # Avoid duplicate processing
        if str(file_path) in self.processing:
            return
        
        self.processing.add(str(file_path))
        
        try:
            print(f"\nNew file detected: {file_path.name}")
            self.pipeline.process_file(str(file_path))
        finally:
            self.processing.discard(str(file_path))
    
    def _is_stable(self, file_path: Path, wait_time: int = 3) -> bool:
        """Check if file size is stable (fully synced)."""
        try:
            size1 = file_path.stat().st_size
            time.sleep(wait_time)
            size2 = file_path.stat().st_size
            return size1 == size2
        except:
            return False


def start_watcher(vault_path: str, pipeline: IngestionPipeline, config: Dict):
    """Start file watcher."""
    event_handler = VaultWatcher(pipeline, config)
    observer = Observer()
    observer.schedule(event_handler, vault_path, recursive=True)
    observer.start()
    
    print(f"Watching: {vault_path}")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
```

### R1.8: Testing

**tests/test_ingestion.py:**
```python
"""Test ingestion pipeline."""
import pytest
from pathlib import Path
import tempfile
import shutil
from core.ingestion import IngestionPipeline


@pytest.fixture
def test_config():
    """Create test configuration."""
    temp_dir = tempfile.mkdtemp()
    return {
        'vault_path': temp_dir,
        'data_path': f"{temp_dir}/data",
        'embeddings': {
            'model': 'all-MiniLM-L6-v2',
            'cache_path': f"{temp_dir}/cache",
            'chunk_size': 500,
            'chunk_overlap': 100
        },
        'vector_db': {
            'path': f"{temp_dir}/lancedb",
            'table_name': 'test_chunks'
        },
        'watcher': {
            'supported_extensions': ['.txt', '.md']
        }
    }


def test_process_text_file(test_config):
    """Test processing a simple text file."""
    # Create test file
    test_file = Path(test_config['vault_path']) / 'test.txt'
    test_file.write_text("This is a test file with some content.")
    
    # Process
    pipeline = IngestionPipeline(test_config)
    result = pipeline.process_file(str(test_file))
    
    assert result == True
    
    # Verify in metadata
    assert pipeline.metadata_db.is_indexed(str(test_file))
    
    # Cleanup
    shutil.rmtree(test_config['vault_path'])


def test_skip_duplicate(test_config):
    """Test that duplicate files are skipped."""
    test_file = Path(test_config['vault_path']) / 'test.txt'
    test_file.write_text("This is a test file.")
    
    pipeline = IngestionPipeline(test_config)
    
    # First process
    result1 = pipeline.process_file(str(test_file))
    assert result1 == True
    
    # Second process (should skip)
    result2 = pipeline.process_file(str(test_file))
    assert result2 == False
    
    shutil.rmtree(test_config['vault_path'])
```

**Commit:** `R1 GATE: ingestion pipeline complete, watcher working`

---

# PART 3: CORE WORKERS (R2-R5)

## R2: Librarian Worker

**Goal:** Semantic retrieval with citations and multiple query modes

### R2.1: Search interface

**workers/librarian.py:**
```python
"""Librarian worker - semantic retrieval with citations."""
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from core.search import VectorSearch
from core.embedder import Embedder
from core.metadata import MetadataDB


class Librarian:
    """Semantic search and retrieval with citations."""
    
    def __init__(self, config: Dict):
        """Initialize Librarian."""
        self.config = config
        self.embedder = Embedder(
            model_name=config['embeddings']['model'],
            cache_dir=config['embeddings']['cache_path']
        )
        self.vector_db = VectorSearch(
            db_path=config['vector_db']['path'],
            table_name=config['vector_db']['table_name']
        )
        self.vector_db.open_table()
        self.metadata_db = MetadataDB(
            db_path=f"{config['data_path']}/metadata.db"
        )
    
    def search(self, query: str, top_k: int = 30, 
               filters: Dict = None) -> List[Dict]:
        """
        Semantic search with citations.
        
        Args:
            query: Natural language query
            top_k: Number of results
            filters: Optional filters (year, file_type, etc.)
        
        Returns:
            List of chunks with full metadata and citations
        """
        # Generate query embedding
        query_embedding = self.embedder.embed([query])[0]
        
        # Build filter expression
        filter_expr = self._build_filter(filters) if filters else None
        
        # Search
        results = self.vector_db.search(
            query_vector=query_embedding,
            top_k=top_k,
            filter_expr=filter_expr
        )
        
        # Enhance with file metadata
        enhanced = []
        for result in results:
            file_info = self.metadata_db.get_file_info(result['file_hash'])
            enhanced.append({
                **result,
                'file_info': file_info,
                'citation': self._format_citation(result, file_info)
            })
        
        return enhanced
    
    def discovery_search(self, topic: str, top_k: int = 100) -> Dict:
        """
        Discovery mode - broad search organized by year.
        
        Returns:
            {
                'topic': str,
                'total_results': int,
                'by_year': {2018: [chunks], 2019: [chunks], ...},
                'duplicates': [similar chunks]
            }
        """
        results = self.search(topic, top_k=top_k)
        
        # Group by year
        by_year = {}
        for result in results:
            year = self._extract_year(result['file_info'])
            if year not in by_year:
                by_year[year] = []
            by_year[year].append(result)
        
        # Find duplicates (similarity > 0.9)
        duplicates = self._find_duplicates(results)
        
        return {
            'topic': topic,
            'total_results': len(results),
            'by_year': by_year,
            'duplicates': duplicates
        }
    
    def quote_bank(self, topic: str, count: int = 20) -> List[str]:
        """
        Quote bank mode - extract usable one-liners.
        
        Returns list of short, punchy quotes.
        """
        # Search broadly
        results = self.search(topic, top_k=50)
        
        # Filter for short chunks (1-3 sentences)
        quotes = []
        for result in results:
            text = result['chunk_text'].strip()
            sentences = text.split('. ')
            
            # Look for 1-3 sentence chunks
            if 1 <= len(sentences) <= 3:
                # Check if it reads well standalone
                if self._is_quotable(text):
                    quotes.append({
                        'text': text,
                        'citation': result['citation'],
                        'similarity': result['similarity']
                    })
        
        # Return top N by similarity
        quotes.sort(key=lambda x: x['similarity'], reverse=True)
        return quotes[:count]
    
    def save_results(self, results: List[Dict], output_path: str, 
                     format_type: str = 'research_packet'):
        """
        Save results to markdown file.
        
        format_type: 'research_packet', 'discovery', 'quotes'
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            if format_type == 'research_packet':
                self._write_research_packet(f, results)
            elif format_type == 'discovery':
                self._write_discovery(f, results)
            elif format_type == 'quotes':
                self._write_quotes(f, results)
    
    def _write_research_packet(self, file, results: List[Dict]):
        """Write research packet format."""
        file.write(f"# Research Packet\n\n")
        file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        file.write(f"Results: {len(results)}\n\n")
        file.write("---\n\n")
        
        for i, result in enumerate(results, 1):
            file.write(f"## Result {i}\n\n")
            file.write(f"**Source:** {result['citation']}\n\n")
            file.write(f"**Similarity:** {result['similarity']:.3f}\n\n")
            file.write(f"{result['chunk_text']}\n\n")
            file.write("---\n\n")
    
    def _write_discovery(self, file, discovery: Dict):
        """Write discovery format (grouped by year)."""
        file.write(f"# Discovery: {discovery['topic']}\n\n")
        file.write(f"Total results: {discovery['total_results']}\n\n")
        
        # By year
        for year in sorted(discovery['by_year'].keys()):
            chunks = discovery['by_year'][year]
            file.write(f"## {year} ({len(chunks)} results)\n\n")
            for chunk in chunks:
                file.write(f"- {chunk['citation']}\n")
            file.write("\n")
        
        # Duplicates
        if discovery['duplicates']:
            file.write(f"## Duplicates Found\n\n")
            for dup in discovery['duplicates']:
                file.write(f"- {dup}\n")
    
    def _write_quotes(self, file, quotes: List[Dict]):
        """Write quote bank format."""
        file.write("# Quote Bank\n\n")
        file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        
        for i, quote in enumerate(quotes, 1):
            file.write(f"{i}. \"{quote['text']}\"\n")
            file.write(f"   *Source: {quote['citation']}*\n\n")
    
    def _build_filter(self, filters: Dict) -> str:
        """Build SQL filter expression."""
        conditions = []
        
        if 'year' in filters:
            conditions.append(f"file_path LIKE '%{filters['year']}%'")
        
        if 'file_type' in filters:
            conditions.append(f"file_path LIKE '%{filters['file_type']}'")
        
        return ' AND '.join(conditions) if conditions else None
    
    def _format_citation(self, result: Dict, file_info: Dict) -> str:
        """Format citation string."""
        if not file_info:
            return result['file_path']
        
        name = file_info['file_name']
        date = file_info['indexed_at'][:10]  # YYYY-MM-DD
        return f"{name} ({date}), chunk {result['chunk_index']}"
    
    def _extract_year(self, file_info: Dict) -> int:
        """Extract year from file metadata."""
        if not file_info:
            return 0
        
        # Try to parse from filename or path
        import re
        path = file_info['file_path']
        years = re.findall(r'20\d{2}', path)
        return int(years[0]) if years else 0
    
    def _find_duplicates(self, results: List[Dict], 
                         threshold: float = 0.9) -> List[str]:
        """Find near-duplicate content."""
        duplicates = []
        seen = set()
        
        for i, result1 in enumerate(results):
            for result2 in results[i+1:]:
                if result1['chunk_id'] in seen or result2['chunk_id'] in seen:
                    continue
                
                # Compare similarity (simplified - could use embedding distance)
                similarity = self._text_similarity(
                    result1['chunk_text'],
                    result2['chunk_text']
                )
                
                if similarity > threshold:
                    duplicates.append(
                        f"{result1['citation']} ≈ {result2['citation']}"
                    )
                    seen.add(result1['chunk_id'])
                    seen.add(result2['chunk_id'])
        
        return duplicates
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple Jaccard similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0
    
    def _is_quotable(self, text: str) -> bool:
        """Check if text reads well as standalone quote."""
        # Simple heuristics
        if len(text) < 50 or len(text) > 300:
            return False
        
        # Should be complete sentences
        if not text.endswith(('.', '!', '?')):
            return False
        
        # Shouldn't reference unclear context
        unclear_words = ['this', 'that', 'it', 'they', 'them']
        first_word = text.split()[0].lower()
        if first_word in unclear_words:
            return False
        
        return True
```

### R2.2: Testing

**tests/test_librarian.py:**
```python
"""Test Librarian worker."""
import pytest
from workers.librarian import Librarian


def test_search(test_config, indexed_vault):
    """Test basic search."""
    librarian = Librarian(test_config)
    results = librarian.search("pricing strategy", top_k=10)
    
    assert len(results) > 0
    assert 'citation' in results[0]
    assert 'similarity' in results[0]


def test_quote_bank(test_config, indexed_vault):
    """Test quote extraction."""
    librarian = Librarian(test_config)
    quotes = librarian.quote_bank("business strategy", count=5)
    
    assert len(quotes) <= 5
    for quote in quotes:
        assert 'text' in quote
        assert 'citation' in quote
```

**Commit:** `R2 GATE: Librarian working, all search modes tested`

---

## R3: Chat UI (Basic)

**Goal:** Gradio interface for conversational interaction with Librarian

### R3.1: Basic UI

**ui/app.py:**
```python
"""Gradio chat interface for Research Hive."""
import gradio as gr
from pathlib import Path
import yaml
from workers.librarian import Librarian


# Load config
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize Librarian
librarian = Librarian(config)

# Project management
current_project = None
workspace_path = Path(config['workspace_path']) / 'projects'
workspace_path.mkdir(parents=True, exist_ok=True)


def chat(message, history):
    """Handle chat interaction."""
    # Simple command parsing
    if message.startswith('/'):
        return handle_command(message)
    
    # Default: treat as search query
    results = librarian.search(message, top_k=30)
    
    # Format response
    response = f"Found {len(results)} results:\n\n"
    for i, result in enumerate(results[:5], 1):
        response += f"{i}. {result['citation']}\n"
        response += f"   Similarity: {result['similarity']:.3f}\n"
        response += f"   Preview: {result['chunk_text'][:150]}...\n\n"
    
    if len(results) > 5:
        response += f"\n... and {len(results) - 5} more results."
    
    return response


def handle_command(command):
    """Handle slash commands."""
    parts = command.split()
    cmd = parts[0].lower()
    
    if cmd == '/search':
        query = ' '.join(parts[1:])
        results = librarian.search(query)
        return f"Search: {query}\nResults: {len(results)}"
    
    elif cmd == '/discovery':
        topic = ' '.join(parts[1:])
        discovery = librarian.discovery_search(topic)
        return format_discovery(discovery)
    
    elif cmd == '/quotes':
        topic = ' '.join(parts[1:])
        quotes = librarian.quote_bank(topic, count=20)
        return format_quotes(quotes)
    
    elif cmd == '/stats':
        stats = librarian.metadata_db.stats()
        return (f"Database Statistics:\n"
                f"Files: {stats['files']}\n"
                f"Chunks: {stats['chunks']}\n"
                f"Total tokens: {stats['total_tokens']:,}")
    
    else:
        return f"Unknown command: {cmd}"


def format_discovery(discovery):
    """Format discovery results."""
    output = f"# Discovery: {discovery['topic']}\n\n"
    output += f"Total results: {discovery['total_results']}\n\n"
    
    for year in sorted(discovery['by_year'].keys(), reverse=True):
        chunks = discovery['by_year'][year]
        output += f"**{year}:** {len(chunks)} results\n"
    
    return output


def format_quotes(quotes):
    """Format quote bank."""
    output = "# Quote Bank\n\n"
    for i, quote in enumerate(quotes, 1):
        output += f"{i}. \"{quote['text']}\"\n"
        output += f"   *{quote['citation']}*\n\n"
    return output


# Build UI
with gr.Blocks(title="Research Hive", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Research Hive")
    gr.Markdown("Conversational research assistant for your content corpus")
    
    with gr.Row():
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(height=600)
            msg = gr.Textbox(
                placeholder="Ask a question or use a command (/search, /discovery, /quotes, /stats)",
                container=False
            )
            
        with gr.Column(scale=1):
            gr.Markdown("### Commands")
            gr.Markdown("""
            - `/search [query]` - Semantic search
            - `/discovery [topic]` - Broad search by year
            - `/quotes [topic]` - Extract usable quotes
            - `/stats` - Database statistics
            
            Or just type naturally and I'll search for you.
            """)
    
    msg.submit(chat, [msg, chatbot], [chatbot])


if __name__ == "__main__":
    demo.launch(
        server_name=config['ui']['host'],
        server_port=config['ui']['port'],
        share=config['ui'].get('share', False)
    )
```

**Commit:** `R3 GATE: Basic chat UI working`

---

## R4: Architect Worker

**Goal:** Thematic organization and structural suggestions

**workers/architect.py:**
```python
"""Architect worker - organize and structure research."""
from typing import List, Dict
import google.generativeai as genai
from pathlib import Path


class Architect:
    """Thematic organization and gap detection."""
    
    def __init__(self, config: Dict):
        """Initialize Architect."""
        self.config = config
        genai.configure(api_key=config['llm']['api_key'])
        self.model = genai.GenerativeModel(config['llm']['model'])
    
    def organize_by_theme(self, chunks: List[Dict]) -> Dict:
        """
        Organize chunks into themes.
        
        Returns:
            {
                'themes': {
                    'theme_name': [chunks],
                    ...
                },
                'gaps': [identified gaps]
            }
        """
        # Prepare chunks for LLM
        chunk_texts = [
            f"[{i}] {c['chunk_text']}"
            for i, c in enumerate(chunks)
        ]
        
        prompt = f"""Analyze these text chunks and organize them into themes.

CHUNKS:
{chr(10).join(chunk_texts[:30])}  # Limit for context

Identify 3-5 major themes.
For each theme, list which chunk numbers belong to it.
Also identify gaps - themes that are mentioned but underdeveloped.

Format:
THEMES:
- Theme name: [chunk numbers]

GAPS:
- Gap description
"""
        
        response = self.model.generate_content(prompt)
        
        # Parse response (simplified - production would use structured output)
        return self._parse_themes(response.text, chunks)
    
    def suggest_structures(self, chunks: List[Dict]) -> List[Dict]:
        """
        Suggest possible structures for the content.
        
        Returns list of structure options:
        [
            {
                'type': 'workshop',
                'title': '...',
                'structure': [...],
                'gaps': [...]
            },
            ...
        ]
        """
        # Summarize content
        summaries = [c['chunk_text'][:200] for c in chunks[:20]]
        
        prompt = f"""Given these content fragments, suggest 3 different ways to structure them:

CONTENT FRAGMENTS:
{chr(10).join(summaries)}

Suggest:
1. A workshop structure (3-5 sections, beginner to advanced)
2. A video series structure (5-7 episodes)
3. A long-form article structure (introduction, body sections, conclusion)

For each, identify what additional content would be needed to fill gaps.
"""
        
        response = self.model.generate_content(prompt)
        
        # Parse suggestions
        return self._parse_structures(response.text)
    
    def _parse_themes(self, text: str, chunks: List[Dict]) -> Dict:
        """Parse LLM output into structured themes."""
        # Simplified parsing - production would be more robust
        themes = {}
        gaps = []
        
        # This would parse the LLM's response
        # For now, return structure
        return {
            'themes': themes,
            'gaps': gaps,
            'raw_analysis': text
        }
    
    def _parse_structures(self, text: str) -> List[Dict]:
        """Parse structure suggestions."""
        # Simplified - return raw for now
        return [{
            'raw_suggestions': text
        }]
```

**Commit:** `R4 GATE: Architect worker complete`

---

## R5: Critic Worker

**Goal:** Brand principles enforcement

**workers/critic.py:**
```python
"""Critic worker - enforce brand principles."""
from typing import List, Dict
import google.generativeai as genai
from pathlib import Path


class Critic:
    """Brand principles enforcement and contradiction detection."""
    
    def __init__(self, config: Dict):
        """Initialize Critic."""
        self.config = config
        genai.configure(api_key=config['llm']['api_key'])
        self.model = genai.GenerativeModel(config['llm']['model'])
        
        # Load brand principles
        principles_path = Path('config/BRAND_PRINCIPLES.md')
        with open(principles_path) as f:
            self.principles = f.read()
        
        # Load voice examples
        examples_path = Path('config/BRAND_VOICE_EXAMPLES.md')
        if examples_path.exists():
            with open(examples_path) as f:
                self.voice_examples = f.read()
        else:
            self.voice_examples = ""
    
    def critique(self, structure: str, context: str = "") -> Dict:
        """
        Critique structure against brand principles.
        
        Args:
            structure: The structure to critique
            context: Additional context (e.g., target audience)
        
        Returns:
            {
                'violations': [list of violations],
                'suggestions': [improvement suggestions],
                'score': float (0-1)
            }
        """
        prompt = f"""Review this content structure against these brand principles.

BRAND PRINCIPLES:
{self.principles}

STRUCTURE TO REVIEW:
{structure}

{f"CONTEXT: {context}" if context else ""}

Identify:
1. Any violations of the stated principles
2. Suggestions for improvement
3. Overall alignment score (0-1)

Be specific about which principle is violated and how.
"""
        
        response = self.model.generate_content(prompt)
        
        return {
            'raw_critique': response.text,
            'violations': self._extract_violations(response.text),
            'suggestions': self._extract_suggestions(response.text)
        }
    
    def check_contradictions(self, chunks: List[Dict]) -> List[Dict]:
        """
        Find contradictions across chunks (different years).
        
        Returns list of contradictions with sources.
        """
        # Group by year
        by_year = {}
        for chunk in chunks:
            year = chunk.get('file_info', {}).get('indexed_at', '')[:4]
            if year not in by_year:
                by_year[year] = []
            by_year[year].append(chunk)
        
        # Compare statements across years
        contradictions = []
        years = sorted(by_year.keys())
        
        for i, year1 in enumerate(years):
            for year2 in years[i+1:]:
                # Sample chunks from each year
                sample1 = by_year[year1][:5]
                sample2 = by_year[year2][:5]
                
                prompt = f"""Compare these statements from {year1} vs {year2}.
                
{year1}:
{chr(10).join([c['chunk_text'][:200] for c in sample1])}

{year2}:
{chr(10).join([c['chunk_text'][:200] for c in sample2])}

Do any statements contradict each other?
If yes, list the contradictions.
If no, say "No contradictions found."
"""
                
                response = self.model.generate_content(prompt)
                
                if "contradict" in response.text.lower():
                    contradictions.append({
                        'years': f"{year1} vs {year2}",
                        'description': response.text
                    })
        
        return contradictions
    
    def _extract_violations(self, text: str) -> List[str]:
        """Extract violations from critique."""
        # Simplified extraction
        violations = []
        if "violation" in text.lower():
            # Parse violations
            lines = text.split('\n')
            for line in lines:
                if 'violation' in line.lower():
                    violations.append(line.strip())
        return violations
    
    def _extract_suggestions(self, text: str) -> List[str]:
        """Extract suggestions from critique."""
        suggestions = []
        if "suggest" in text.lower():
            lines = text.split('\n')
            for line in lines:
                if 'suggest' in line.lower() or line.strip().startswith('-'):
                    suggestions.append(line.strip())
        return suggestions
```

**Commit:** `R5 GATE: Critic worker complete`

---

# PART 4: INTEGRATION & UI (R6)

## R6: Full Integration

**Goal:** Complete workflow via enhanced UI

### R6.1: Enhanced UI with all workers

**ui/app.py** (updated - replace previous version):
```python
"""Full Research Hive interface."""
import gradio as gr
from pathlib import Path
import yaml
from datetime import datetime
from workers.librarian import Librarian
from workers.architect import Architect
from workers.critic import Critic


# Load config
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize workers
librarian = Librarian(config)
architect = Architect(config)
critic = Critic(config)

# State management
workspace_path = Path(config['workspace_path']) / 'projects'
workspace_path.mkdir(parents=True, exist_ok=True)

current_project = None
current_results = []


def create_project(project_name):
    """Create new project directory."""
    global current_project
    
    if not project_name:
        return "Please provide a project name"
    
    current_project = workspace_path / project_name
    current_project.mkdir(exist_ok=True)
    
    return f"Project created: {project_name}"


def handle_query(message, mode):
    """Handle different query modes."""
    global current_results
    
    if mode == "Search":
        current_results = librarian.search(message, top_k=30)
        return format_search_results(current_results)
    
    elif mode == "Discovery":
        discovery = librarian.discovery_search(message, top_k=100)
        return format_discovery(discovery)
    
    elif mode == "Quotes":
        quotes = librarian.quote_bank(message, count=20)
        return format_quotes(quotes)
    
    elif mode == "Stats":
        stats = librarian.metadata_db.stats()
        return format_stats(stats)


def organize_results():
    """Organize current results by theme."""
    global current_results
    
    if not current_results:
        return "No results to organize. Run a search first."
    
    organized = architect.organize_by_theme(current_results)
    return format_organization(organized)


def critique_structure(structure_text):
    """Critique structure against brand principles."""
    critique = critic.critique(structure_text)
    return format_critique(critique)


def save_output(content, filename):
    """Save output to current project."""
    if not current_project:
        return "No project selected. Create a project first."
    
    if not filename:
        filename = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    output_path = current_project / filename
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    return f"Saved to: {output_path}"


def format_search_results(results):
    """Format search results."""
    output = f"# Search Results ({len(results)} found)\n\n"
    
    for i, r in enumerate(results[:30], 1):
        output += f"## Result {i}\n\n"
        output += f"**Source:** {r['citation']}\n"
        output += f"**Similarity:** {r['similarity']:.3f}\n\n"
        output += f"{r['chunk_text']}\n\n"
        output += "---\n\n"
    
    return output


def format_discovery(discovery):
    """Format discovery results."""
    output = f"# Discovery: {discovery['topic']}\n\n"
    output += f"**Total results:** {discovery['total_results']}\n\n"
    
    output += "## By Year\n\n"
    for year in sorted(discovery['by_year'].keys(), reverse=True):
        chunks = discovery['by_year'][year]
        output += f"### {year} ({len(chunks)} results)\n\n"
        for chunk in chunks[:5]:
            output += f"- {chunk['citation']}\n"
        if len(chunks) > 5:
            output += f"- ... and {len(chunks) - 5} more\n"
        output += "\n"
    
    if discovery['duplicates']:
        output += "## Duplicates Found\n\n"
        for dup in discovery['duplicates']:
            output += f"- {dup}\n"
    
    return output


def format_quotes(quotes):
    """Format quote bank."""
    output = "# Quote Bank\n\n"
    for i, quote in enumerate(quotes, 1):
        output += f"{i}. \"{quote['text']}\"\n"
        output += f"   *{quote['citation']}*\n\n"
    return output


def format_stats(stats):
    """Format database stats."""
    return f"""# Database Statistics

**Files indexed:** {stats['files']:,}
**Total chunks:** {stats['chunks']:,}
**Total tokens:** {stats['total_tokens']:,}
"""


def format_organization(organized):
    """Format thematic organization."""
    return f"""# Thematic Organization

{organized.get('raw_analysis', 'No analysis available')}
"""


def format_critique(critique):
    """Format critique."""
    output = "# Critique\n\n"
    
    if critique.get('violations'):
        output += "## Violations Found\n\n"
        for v in critique['violations']:
            output += f"- {v}\n"
        output += "\n"
    
    if critique.get('suggestions'):
        output += "## Suggestions\n\n"
        for s in critique['suggestions']:
            output += f"- {s}\n"
        output += "\n"
    
    output += "\n## Full Critique\n\n"
    output += critique.get('raw_critique', '')
    
    return output


# Build UI
with gr.Blocks(title="Research Hive", theme=gr.themes.Soft()) as app:
    gr.Markdown("# Research Hive")
    gr.Markdown("Conversational research assistant for your content corpus")
    
    with gr.Tab("Query"):
        with gr.Row():
            project_name_input = gr.Textbox(label="Project Name", placeholder="workshop_2026_pricing")
            create_proj_btn = gr.Button("Create Project")
        
        project_status = gr.Textbox(label="Project Status", interactive=False)
        create_proj_btn.click(create_project, inputs=[project_name_input], outputs=[project_status])
        
        gr.Markdown("---")
        
        with gr.Row():
            query_input = gr.Textbox(
                label="Query",
                placeholder="What are you researching?",
                lines=2
            )
            mode_select = gr.Radio(
                choices=["Search", "Discovery", "Quotes", "Stats"],
                value="Search",
                label="Mode"
            )
        
        search_btn = gr.Button("Search", variant="primary")
        
        results_output = gr.Markdown(label="Results", height=600)
        
        search_btn.click(
            handle_query,
            inputs=[query_input, mode_select],
            outputs=[results_output]
        )
    
    with gr.Tab("Organize"):
        gr.Markdown("Organize search results by theme")
        
        organize_btn = gr.Button("Organize Current Results")
        organized_output = gr.Markdown(label="Organized Results")
        
        organize_btn.click(
            organize_results,
            outputs=[organized_output]
        )
    
    with gr.Tab("Critique"):
        gr.Markdown("Critique structure against brand principles")
        
        structure_input = gr.Textbox(
            label="Structure to Critique",
            placeholder="Paste your structure here...",
            lines=10
        )
        
        critique_btn = gr.Button("Critique")
        critique_output = gr.Markdown(label="Critique Results")
        
        critique_btn.click(
            critique_structure,
            inputs=[structure_input],
            outputs=[critique_output]
        )
    
    with gr.Tab("Save"):
        gr.Markdown("Save outputs to project")
        
        content_input = gr.Textbox(
            label="Content to Save",
            placeholder="Paste content here...",
            lines=15
        )
        
        filename_input = gr.Textbox(
            label="Filename",
            placeholder="research_packet_v001.md"
        )
        
        save_btn = gr.Button("Save")
        save_status = gr.Textbox(label="Save Status", interactive=False)
        
        save_btn.click(
            save_output,
            inputs=[content_input, filename_input],
            outputs=[save_status]
        )


if __name__ == "__main__":
    app.launch(
        server_name=config['ui']['host'],
        server_port=config['ui']['port'],
        share=config['ui'].get('share', False)
    )
```

### R6.2: CLI tools

**cli.py** (for command-line usage):
```python
"""CLI interface for Research Hive."""
import click
import yaml
from pathlib import Path
from core.ingestion import IngestionPipeline
from workers.librarian import Librarian


@click.group()
def cli():
    """Research Hive CLI."""
    pass


@cli.command()
@click.argument('directory')
def index(directory):
    """Index all files in a directory."""
    with open('config/config.yaml') as f:
        config = yaml.safe_load(f)
    
    pipeline = IngestionPipeline(config)
    stats = pipeline.process_directory(directory)
    
    click.echo(f"Indexed: {stats['processed']} files")
    click.echo(f"Skipped: {stats['skipped']} files")


@cli.command()
@click.argument('query')
@click.option('--top-k', default=30, help='Number of results')
@click.option('--output', help='Save to file')
def search(query, top_k, output):
    """Search the corpus."""
    with open('config/config.yaml') as f:
        config = yaml.safe_load(f)
    
    librarian = Librarian(config)
    results = librarian.search(query, top_k=top_k)
    
    if output:
        librarian.save_results(results, output, format_type='research_packet')
        click.echo(f"Saved to: {output}")
    else:
        for i, r in enumerate(results, 1):
            click.echo(f"\n{i}. {r['citation']}")
            click.echo(f"   {r['chunk_text'][:150]}...")


@cli.command()
def stats():
    """Show database statistics."""
    with open('config/config.yaml') as f:
        config = yaml.safe_load(f)
    
    librarian = Librarian(config)
    stats = librarian.metadata_db.stats()
    
    click.echo(f"Files: {stats['files']:,}")
    click.echo(f"Chunks: {stats['chunks']:,}")
    click.echo(f"Tokens: {stats['total_tokens']:,}")


if __name__ == '__main__':
    cli()
```

**Commit:** `R6 GATE: Full integration complete, UI working`

---

# PART 5: TESTING & VALIDATION

## Final Testing Protocol

### Integration Tests

**tests/test_integration.py:**
```python
"""Integration tests - full workflow."""
import pytest
from pathlib import Path
import tempfile
import shutil


def test_full_workflow(test_config):
    """Test complete workflow: index -> search -> organize -> critique."""
    # Setup
    from core.ingestion import IngestionPipeline
    from workers.librarian import Librarian
    from workers.architect import Architect
    from workers.critic import Critic
    
    # Create test corpus
    vault = Path(test_config['vault_path'])
    test_file = vault / 'test_content.md'
    test_file.write_text("""
# Pricing Strategy

Pricing is about value perception, not cost calculation.

Strategy before tactics. Always explain the why before the how.

Most businesses price based on cost-plus. This is a mistake.
    """)
    
    # Step 1: Index
    pipeline = IngestionPipeline(test_config)
    pipeline.process_file(str(test_file))
    
    # Step 2: Search
    librarian = Librarian(test_config)
    results = librarian.search("pricing strategy", top_k=10)
    
    assert len(results) > 0
    
    # Step 3: Organize
    architect = Architect(test_config)
    organized = architect.organize_by_theme(results)
    
    assert 'themes' in organized or 'raw_analysis' in organized
    
    # Step 4: Critique
    critic = Critic(test_config)
    structure = "## Pricing Tactics\n\nHere are 7 quick wins..."
    critique = critic.critique(structure)
    
    # Should flag "tactics before strategy" violation
    assert 'violation' in critique['raw_critique'].lower() or \
           len(critique.get('violations', [])) > 0
    
    # Cleanup
    shutil.rmtree(test_config['vault_path'])
```

### Manual Test Cases

**After R6 completion, Alex should test:**

1. **Project Creation**
   - Create project "test_workshop"
   - Verify directory appears in workspace/projects/

2. **Search Mode**
   - Query: "pricing psychology"
   - Verify: 20+ results, citations included
   - Save results to project

3. **Discovery Mode**
   - Query: "brand positioning"
   - Verify: Results grouped by year
   - Check for duplicate detection

4. **Quote Bank**
   - Query: "business strategy"
   - Verify: 20 short quotes returned
   - Check quotes are standalone readable

5. **Organization**
   - Run search first
   - Click "Organize"
   - Verify: Themes identified, gaps marked

6. **Critique**
   - Paste structure with "tactics before strategy"
   - Click "Critique"
   - Verify: Violation flagged

7. **Save Output**
   - Save research packet
   - Check file in workspace/projects/test_workshop/

8. **Stats**
   - Check database statistics
   - Verify counts are accurate

### Validation Checklist

Before marking complete:

- [ ] All R0-R6 steps committed
- [ ] pytest tests pass (run `pytest tests/`)
- [ ] Gradio UI launches without errors
- [ ] Search returns relevant results
- [ ] Results include proper citations
- [ ] Project creation works
- [ ] Save functionality works
- [ ] Files sync to workspace directory
- [ ] File watcher detects new files
- [ ] Manual test cases pass

---

## Deployment Notes

### Starting the System

```bash
# Activate environment
source venv/bin/activate

# Start file watcher (background)
python -m core.watcher &

# Start UI
python ui/app.py
```

### Accessing the UI

- Local: http://localhost:7860
- Remote (if share=true): Gradio provides public URL

### Syncthing Setup

Desktop → VPS sync:
- Desktop: `~/Downloads/ContentVault/` (send-only)
- VPS: `~/content-vault/` (receive-only)

VPS → Desktop sync:
- VPS: `~/research-hive/workspace/` (send-only)
- Desktop: `~/Obsidian/ResearchHive/` (receive-only)

---

## Maintenance

### Re-indexing

If you need to re-index everything:
```bash
# Clear existing index
rm -rf data/lancedb
rm data/metadata.db

# Re-index
python cli.py index ~/content-vault
```

### Updating Brand Principles

Edit `config/BRAND_PRINCIPLES.md` - changes take effect immediately.

### Monitoring

Check file watcher logs:
```bash
tail -f logs/watcher.log
```

---

## Future Extensions

After R6 is stable:

1. **Journalism Hive** (fact-checking, quote verification)
2. **Book Drafter** (chapter-by-chapter organization)
3. **Rebranding Assistant** (semi-automated content updates)
4. **Integration into main Hive-Office** (as optional Consorts)

---

## References

- LanceDB docs: https://lancedb.github.io/lancedb/
- sentence-transformers: https://www.sbert.net/
- Gradio docs: https://www.gradio.app/docs/
- Gemini API: https://ai.google.dev/docs

---

## End of Build Plan

This document contains everything needed to build the Research Hive. Execute steps R0-R6 sequentially. Report progress in STATUS.md. Commit at each gate.

**First task:** Start with R0 (infrastructure setup).
