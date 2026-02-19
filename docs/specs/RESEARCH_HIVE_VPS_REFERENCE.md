# Research Hive: VPS-Claude Reference Guide

**This file supplements the main spec. Read RESEARCH_HIVE_COMPLETE_SPEC.md first.**

---

## Skills to Reference During Build

The [awesome-agent-skills repo](https://github.com/VoltAgent/awesome-agent-skills) has patterns you can reference when implementing specific features. You don't need to copy them - just look at HOW they solve similar problems.

### When Implementing R1 (Ingestion Pipeline)

**Reference: anthropics/pdf**
- Location: `https://github.com/anthropics/skills/tree/main/skills/pdf`
- Why: Shows how to extract text from PDFs cleanly
- What to steal: Error handling for corrupted PDFs, text extraction patterns
- What to ignore: The skill-specific prompt structure (you're building a pipeline, not a skill)

**Reference: anthropics/docx**
- Location: `https://github.com/anthropics/skills/tree/main/skills/docx`
- Why: Word document processing patterns
- What to steal: How to handle .docx structure, text extraction approach
- What to ignore: Editing capabilities (you only need reading)

### When Implementing R2 (Librarian Worker)

**Reference: Technical writing patterns**
- Look at how skills format citations
- See how they structure markdown output
- Note: Your citations need file path + chunk index + similarity score

**Reference: Data analysis patterns**
- How to present search results clearly
- Grouping/clustering approaches
- Table formatting in markdown

### When Implementing R6 (UI Integration)

**Reference: anthropics/doc-coauthoring**
- Location: `https://github.com/anthropics/skills/tree/main/skills/doc-coauthoring`
- Why: Shows a feedback-heavy workflow (similar to your structure approval loop)
- What to steal: How they handle iterative refinement
- What to ignore: The specific doc types (you're doing structure, not documents)

### Testing Reference

Look at test patterns in any of the Anthropic skills to see how they structure pytest tests. They're minimal and clear.

---

## What NOT to Import

**Don't use:**
- Skill prompt structures (your workers use different prompting)
- Tool configurations (your tools are different)
- The skills framework itself (you're not building skills, you're building workers)

**Do use:**
- Code patterns for file processing
- Error handling approaches  
- Output formatting examples
- Testing strategies

---

## Using Gemini API for Workers (Not Claude)

Alex has Gemini API credits. The spec assumes Gemini for workers but doesn't show configuration. Here's how:

### API Key Setup

```bash
# Add to environment (don't commit this)
export GEMINI_API_KEY="your-key-here"

# Or in .env file (add .env to .gitignore)
GEMINI_API_KEY=your-key-here
```

### Configuration Strategy

You need to configure:
1. **Builder model** (Claude Code uses Claude for building the system)
2. **Worker models** (Librarian, Architect, Writer, Critic use Gemini)

**Builder model:** You're already using Claude Code (Claude Opus/Sonnet). This stays.

**Worker models:** These should use Gemini API. Configuration options:

#### Option 1: Config file approach

```yaml
# config/models.yaml
builder:
  provider: "anthropic"  # Claude Code itself
  model: "claude-opus-4-6"
  
workers:
  librarian:
    provider: "google"
    model: "gemini-2.0-flash-exp"  # Fast, cheap
    api_key_env: "GEMINI_API_KEY"
    
  architect:
    provider: "google"
    model: "gemini-2.0-flash-exp"
    api_key_env: "GEMINI_API_KEY"
    
  writer:
    provider: "google"
    model: "gemini-2.5-pro-002"  # Smarter for drafting
    api_key_env: "GEMINI_API_KEY"
    
  critic:
    provider: "google"
    model: "gemini-2.0-flash-exp"  # Simple rule checking
    api_key_env: "GEMINI_API_KEY"
```

#### Option 2: Environment variables

```bash
# .env
LIBRARIAN_MODEL=gemini-2.0-flash-exp
ARCHITECT_MODEL=gemini-2.0-flash-exp
WRITER_MODEL=gemini-2.5-pro-002
CRITIC_MODEL=gemini-2.0-flash-exp
GEMINI_API_KEY=your-key-here
```

#### Option 3: Code-level configuration

```python
# config.py
import os
from google.generativeai import configure, GenerativeModel

configure(api_key=os.getenv("GEMINI_API_KEY"))

MODELS = {
    "librarian": GenerativeModel("gemini-2.0-flash-exp"),
    "architect": GenerativeModel("gemini-2.0-flash-exp"),
    "writer": GenerativeModel("gemini-2.5-pro-002"),
    "critic": GenerativeModel("gemini-2.0-flash-exp"),
}
```

### Gemini Model Selection (Feb 2026)

**Available models:**
- `gemini-2.0-flash-exp`: Fast, cheap, experimental (free tier: 15 RPM, 1M TPM)
- `gemini-2.0-flash-thinking-exp`: Flash with reasoning (free tier: 15 RPM, 32K TPM)
- `gemini-2.5-pro-002`: Smart, expensive (free tier: 2 RPM, 32K TPM)
- `gemini-2.5-flash`: Production Flash (free tier: 10 RPM, 4M TPM)

**My suggested assignments:**
- Librarian: `gemini-2.0-flash-exp` (retrieval is fast, doesn't need smart)
- Architect: `gemini-2.0-flash-thinking-exp` (structure benefits from reasoning)
- Writer: `gemini-2.5-pro-002` (needs quality for Alex's voice)
- Critic: `gemini-2.0-flash-exp` (rule checking is mechanical)

**Cost with free tier:**
- Librarian: 100 calls/day = FREE
- Architect: 50 calls/day = FREE
- Writer: 10 calls/day = FREE (2 RPM limit)
- Critic: 50 calls/day = FREE

**If you hit limits:** Gemini 2.5 Pro is $1.25 per 1M input tokens. Still 4x cheaper than Claude.

### Code Integration Pattern

```python
# workers/base.py
from google.generativeai import GenerativeModel
import os

class BaseWorker:
    def __init__(self, model_name: str):
        self.model = GenerativeModel(model_name)
    
    def generate(self, prompt: str, **kwargs):
        response = self.model.generate_content(
            prompt,
            generation_config={
                "temperature": kwargs.get("temperature", 0.7),
                "max_output_tokens": kwargs.get("max_tokens", 2048),
            }
        )
        return response.text

# workers/librarian.py
class Librarian(BaseWorker):
    def __init__(self):
        super().__init__("gemini-2.0-flash-exp")
    
    def search(self, query: str, chunks: list) -> list:
        prompt = f"Analyze these chunks for: {query}\n\n{chunks}"
        return self.generate(prompt)
```

### API Error Handling

Gemini API can fail. Handle it:

```python
from google.api_core import retry
import google.generativeai as genai

@retry.Retry(predicate=retry.if_transient_error)
def safe_generate(model, prompt):
    try:
        return model.generate_content(prompt)
    except genai.types.StopCandidateException:
        # Safety filter triggered
        return None
    except genai.types.BlockedPromptException:
        # Prompt blocked
        return None
    except Exception as e:
        # Log and re-raise
        print(f"Gemini API error: {e}")
        raise
```

### Testing with Gemini

During development, test each worker's Gemini integration:

```python
# tests/test_gemini_integration.py
def test_librarian_uses_gemini():
    librarian = Librarian()
    assert librarian.model.model_name == "gemini-2.0-flash-exp"

def test_librarian_handles_api_errors():
    # Mock Gemini API failure
    # Verify graceful degradation
    pass
```

---

## Configuration Decision for VPS-Claude

**Choose ONE approach:**

1. **Config file** (cleanest, easiest to change models)
2. **Environment variables** (simplest, no file parsing)
3. **Code-level** (most control, harder to change)

I suggest **Option 1 (config file)** because:
- Alex can switch models without touching code
- Easy to add new workers later
- Can add per-worker parameters (temperature, max_tokens)
- Version controlled (API key stays in .env)

---

## What This Means for the Build

**R0 additions:**
- Install `google-generativeai` Python package
- Set up Gemini API key in .env
- Create config file (if using Option 1)
- Test Gemini connection

**R2-R5 changes:**
- Each worker uses Gemini (not Claude)
- Builder (Claude Code) still uses Claude (that's you)
- Workers call Gemini API via google.generativeai library

**Cost implications:**
- Building the system: Uses Claude Code subscription (already paid)
- Running the system: Uses Gemini API credits (Alex's free tier)
- Total cost during build: $0 extra (within free limits)
- Total cost in production: ~$0.10-0.50/day (if exceeds free tier)

---

## Files to Create in R0

```
research-hive/
├── .env                          # API keys (gitignored)
├── .env.example                  # Template for .env
├── config/
│   └── models.yaml               # Model assignments
├── workers/
│   ├── base.py                   # BaseWorker class
│   ├── librarian.py
│   ├── architect.py
│   ├── writer.py
│   └── critic.py
├── tests/
│   └── test_gemini_integration.py
└── README.md
```

---

## Testing Gemini API Before Building

**Quick test to verify Gemini works:**

```python
# test_gemini.py
import os
from google.generativeai import configure, GenerativeModel

configure(api_key=os.getenv("GEMINI_API_KEY"))

model = GenerativeModel("gemini-2.0-flash-exp")
response = model.generate_content("Say hello")
print(response.text)
```

Run this in R0 to confirm API key works.

---

## Summary

1. **Skills to reference:** Look at anthropics/pdf, anthropics/docx, anthropics/doc-coauthoring for patterns (not to copy wholesale)
2. **Gemini API:** Configure workers to use Gemini, builder uses Claude
3. **Cost:** Free tier covers development, ~$0.50/day in production
4. **Decision needed:** Choose config approach (file/env/code)

**Next step:** Add these considerations to R0 setup in your build plan.
