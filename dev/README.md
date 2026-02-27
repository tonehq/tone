# Development Seed Data

This directory contains the seed script and data for populating the database with service providers, models, and API keys.

## Files

### `seed.py` (195 lines)
**Pure logic file** - Contains only the database seeding logic:
- Loads data from `dev-data.json`
- Creates/updates ServiceProvider records
- Creates/updates Model records
- Creates/updates ApiKey records (from environment variables)
- Handles database transactions and error handling

**Usage:**
```bash
# From project root
python dev/seed.py
# OR
python -m dev.seed
```

### `dev-data.json` (5,267 lines)
**Single source of truth** for all seed data. Organized into three main sections:

#### Structure:
```json
{
  "llm_providers": [
    {
      "name": "provider_name",
      "provider_type": "llm",
      "display_name": "Provider Display Name",
      "description": "Provider description",
      "api_key_env": "ENV_VAR_NAME",
      "models": [
        {
          "name": "model-name",
          "meta_data": {"model": "model-name"}
        }
      ]
    }
  ],
  "stt_providers": [...],
  "tts_providers": [...]
}
```

## Current Inventory

### Service Providers: **55 total**
- **LLM Providers:** 17
  - OpenAI, Groq, Anthropic, Google, OpenRouter, Cerebras, Qwen, DeepSeek, SambaNova, Ollama, Grok, Perplexity, Azure, NVIDIA NIM, Fireworks AI, Together AI, AWS Bedrock

- **STT Providers:** 15
  - Deepgram, OpenAI, Groq, Sarvam, AssemblyAI, Cartesia, Sonioz, ElevenLabs, Gladia, Hathora, SambaNova, NVIDIA, Speechmatics, Google, Azure

- **TTS Providers:** 23
  - Cartesia, PlayHT, Deepgram, Groq, Hathora, MiniMax, Rime, Sarvam, Fish, Inworld, OpenAI, Resemble, NVIDIA, Neuphonic, LMNT, Hume, ElevenLabs, Camb AI, Async AI, AWS Polly, Google, Azure, Speechmatics

### Models: **794 total**
- **LLM Models:** 572
- **STT Models:** 103
- **TTS Models:** 119

## Making Changes

### Adding a New Provider
1. Open `dev-data.json`
2. Find the appropriate section (`llm_providers`, `stt_providers`, or `tts_providers`)
3. Add a new provider object with the required fields:
   ```json
   {
     "name": "provider_name",
     "provider_type": "llm|stt|tts",
     "display_name": "Provider Name",
     "description": "Provider description",
     "api_key_env": "PROVIDER_API_KEY",
     "models": [...]
   }
   ```
4. Run `python dev/seed.py` to apply changes

### Adding a New Model to Existing Provider
1. Open `dev-data.json`
2. Find the provider in the appropriate section
3. Add a new model to the `models` array:
   ```json
   {
     "name": "new-model-name",
     "meta_data": {"model": "new-model-name"}
   }
   ```
4. Run `python dev/seed.py` to apply changes

### Updating Provider Details
1. Open `dev-data.json`
2. Find and update the provider object
3. Run `python dev/seed.py` to apply changes

## API Keys

API keys are read from environment variables specified in the `api_key_env` field. 

**Example:**
If `api_key_env` is `"OPENAI_API_KEY"`, the script will:
1. Look for `OPENAI_API_KEY` in your `.env` file
2. If found, create/update an ApiKey record
3. Link it to all models for that provider

**Missing API Keys:**
If an API key is not found in the environment, the provider and models are still created, but no ApiKey record is created. This is tracked in the seeding stats output.

## Benefits of This Structure

✅ **Separation of Concerns:** Logic and data are completely separated
✅ **Easy Maintenance:** Update data without touching Python code
✅ **Version Control Friendly:** Clear diffs when data changes
✅ **Readable:** JSON is human-readable and easy to edit
✅ **Scalable:** Add hundreds of models without cluttering code
✅ **Single Source of Truth:** All seed data in one place
✅ **Type Safety:** Clear structure makes validation easy

## Migration Notes

The original `seed.py` file contained both logic and data (SERVICE_PROVIDER_CONFIGS). This has been refactored:

- **Before:** 1,545+ lines (logic + data mixed together)
- **After:** 195 lines (pure logic) + 5,267 lines (pure data in JSON)
- **Improvement:** 87% reduction in code file size, much cleaner architecture
