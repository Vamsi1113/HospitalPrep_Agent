# OpenRouter Setup Guide (FREE AI Model)

## What Changed?

The system now uses **OpenRouter** instead of OpenAI, with a **completely FREE** Google Gemini model!

### Benefits

✅ **100% FREE** - No costs, no credit card needed  
✅ **Unlimited usage** - No rate limits on free tier  
✅ **Same quality** - Google Gemini 2 9B model  
✅ **Easy setup** - Get API key in 2 minutes  
✅ **No billing** - Never pay anything  

## Quick Setup (Optional)

The system works perfectly **without** an API key (uses templates). But if you want FREE AI enhancement:

### Step 1: Get FREE API Key

1. Go to https://openrouter.ai/keys
2. Sign up with email or GitHub (no credit card!)
3. Click "Create Key"
4. Copy your key (starts with `sk-or-v1-`)

### Step 2: Add to .env File

Open `.env` and add your key:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### Step 3: Restart App

```bash
# Stop the app (Ctrl+C)
# Start it again
python app.py
```

That's it! You now have FREE AI-enhanced messages.

## What Model is Used?

**Model**: `google/gemma-2-9b-it:free`

- **Provider**: Google
- **Size**: 9 billion parameters
- **Cost**: FREE (unlimited)
- **Quality**: Excellent for message rewriting
- **Speed**: Fast responses

## How It Works

### Without API Key (Current Setup)
```
User Input → Template Engine → Professional Message
```

### With FREE OpenRouter Key
```
User Input → Template Engine → OpenRouter (Gemini) → Enhanced Message
```

The AI makes messages more friendly and natural while keeping all medical instructions intact.

## Example Comparison

### Template Mode (No API Key)
```
APPOINTMENT PREPARATION GUIDE

Patient: John Doe
Appointment: Surgery - Knee Surgery

WHAT TO BRING:
  • Photo ID
  • Insurance Card
  • List of current medications

ARRIVAL:
Arrive at 8:00 AM (60 minutes before your appointment)

FASTING:
Do not eat or drink anything after 12:00 AM on April 15 (8 hours before appointment)
```

### AI-Enhanced Mode (With FREE OpenRouter Key)
```
Hi John,

Here's everything you need to know for your knee surgery appointment:

What to Bring:
- Your photo ID and insurance card
- A list of your current medications

When to Arrive:
Please arrive at 8:00 AM - that's one hour before your procedure starts.

Important Fasting Instructions:
Don't eat or drink anything after midnight on April 15th. This is really important for your safety during surgery.

If you have any questions, just give us a call!
```

Both contain the same medical information, but the AI version is more conversational.

## Checking Your Setup

When you start the app, look for this message:

**Without API Key:**
```
[LLMClient] Using template mode (no API key)
```

**With OpenRouter Key:**
```
[LLMClient] Connected to OpenRouter (google/gemma-2-9b-it:free)
```

## Cost Comparison

| Provider | Model | Cost | Setup |
|----------|-------|------|-------|
| OpenAI | GPT-3.5 | $0.002/message | Credit card required |
| OpenAI | GPT-4 | $0.03/message | Credit card required |
| **OpenRouter** | **Gemini Free** | **$0.00** | **No credit card** |

## Troubleshooting

### "Invalid API key" error

1. Check your key starts with `sk-or-v1-`
2. Make sure there are no spaces before/after the key
3. Verify the key is active at https://openrouter.ai/keys

### "Rate limit exceeded"

The free model has no rate limits! If you see this, check your API key.

### Still using templates

1. Check `.env` file has `OPENROUTER_API_KEY=sk-or-v1-...`
2. Restart the Flask app
3. Look for connection message in console

## Security Notes

- ✅ `.env` is in `.gitignore` (won't be committed)
- ✅ API key is free, but keep it private
- ✅ No billing information stored
- ✅ No credit card ever needed

## Advanced: Using Different Models

Want to try other models? Edit `services/llm_client.py`:

```python
# Current (free)
llm_client = LLMClient(api_key=api_key, model="google/gemma-2-9b-it:free")

# Other free options
llm_client = LLMClient(api_key=api_key, model="meta-llama/llama-3.2-3b-instruct:free")
llm_client = LLMClient(api_key=api_key, model="microsoft/phi-3-mini-128k-instruct:free")
```

See all free models at: https://openrouter.ai/models?order=newest&supported_parameters=tools&max_price=0

## Summary

✅ **Changed from**: OpenAI (paid) → OpenRouter (free)  
✅ **Model**: Google Gemini 2 9B (free tier)  
✅ **Cost**: $0.00 forever  
✅ **Setup**: 2 minutes, no credit card  
✅ **Quality**: Excellent for message enhancement  

**Get your FREE key**: https://openrouter.ai/keys

**Current status**: System works in template mode (no key needed). Add key for FREE AI enhancement!
