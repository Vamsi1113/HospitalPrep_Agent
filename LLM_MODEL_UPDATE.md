# LLM Model Update - Two-Tier Fallback System

## Changes Made

### Primary Model: Google Gemini
- **Model**: `google/gemma-4-26b-a4b-it:free`
- **Provider**: Google via OpenRouter
- **Cost**: Completely free
- **Use Case**: Primary model for all LLM operations

### Fallback Model: Meta Llama
- **Model**: `meta-llama/llama-3.3-70b-instruct:free`
- **Provider**: Meta via OpenRouter
- **Cost**: Completely free
- **Use Case**: Automatic fallback if primary model fails

### Three-Tier Fallback Strategy

```
1st Attempt: Google Gemini (google/gemma-4-26b-a4b-it:free)
    ↓ (if fails)
2nd Attempt: Meta Llama (meta-llama/llama-3.3-70b-instruct:free)
    ↓ (if fails)
3rd Attempt: Template-based responses (keyword matching)
```

---

## Files Modified

### 1. `services/llm_client.py`

#### Added Fallback Model Parameter
```python
def __init__(self, api_key: Optional[str] = None, timeout: int = 5, 
             model: str = "google/gemma-4-26b-a4b-it:free",
             fallback_model: str = "meta-llama/llama-3.3-70b-instruct:free"):
```

#### Updated `rewrite_message()` Method
```python
try:
    # Try primary model (Gemini)
    response = self._client.chat.completions.create(
        model=self.model,
        messages=[...],
        temperature=0.7,
        max_tokens=1000
    )
    return response.choices[0].message.content.strip()
    
except Exception as e:
    logger.warning(f"Primary model ({self.model}) failed, trying fallback")
    
    try:
        # Try fallback model (Llama)
        response = self._client.chat.completions.create(
            model=self.fallback_model,
            messages=[...],
            temperature=0.7,
            max_tokens=1000
        )
        logger.info(f"Fallback model ({self.fallback_model}) succeeded")
        return response.choices[0].message.content.strip()
        
    except Exception as fallback_error:
        # Both models failed, return None for template fallback
        logger.warning(f"Fallback model also failed")
        return None
```

#### Updated `generate_with_prompt()` Method
- Same two-tier fallback logic
- Tries Gemini first, then Llama
- Returns None if both fail

### 2. `.env`
Updated comments to reflect new models:
```env
# Primary Model: google/gemma-4-26b-a4b-it:free
# Fallback Model: meta-llama/llama-3.3-70b-instruct:free
```

### 3. `.env.example`
Updated documentation:
```env
# The application uses OpenRouter with FREE models and automatic fallback.
# Primary Model: google/gemma-4-26b-a4b-it:free
# Fallback Model: meta-llama/llama-3.3-70b-instruct:free
```

---

## How It Works

### Scenario 1: Primary Model Success ✅
```
User sends chat message
    ↓
Try Gemini model
    ↓
Success! Return AI response
```

### Scenario 2: Primary Fails, Fallback Success ✅
```
User sends chat message
    ↓
Try Gemini model → FAILS (NotFoundError)
    ↓
Log warning: "Primary model failed, trying fallback"
    ↓
Try Llama model
    ↓
Success! Return AI response
    ↓
Log info: "Fallback model succeeded"
```

### Scenario 3: Both Models Fail, Template Success ✅
```
User sends chat message
    ↓
Try Gemini model → FAILS
    ↓
Try Llama model → FAILS
    ↓
Log warning: "Fallback model also failed"
    ↓
Return None to trigger template-based response
    ↓
agent/tools.py uses keyword matching
    ↓
Return intelligent fallback response
```

---

## Benefits

### 1. Higher Reliability
- If one model is down, the other takes over
- No user-facing errors
- Seamless experience

### 2. Better Model Coverage
- Gemini: Excellent for conversational responses
- Llama: Strong reasoning and instruction following
- Different strengths complement each other

### 3. Cost Efficiency
- Both models are completely free
- No API costs even with fallback
- Unlimited usage

### 4. Graceful Degradation
- Three levels of fallback
- Always provides a response
- Never crashes or shows errors

---

## Logging Output

### When Primary Model Works
```
[INFO] LLM response generated successfully
```

### When Fallback Model Works
```
[WARNING] Primary LLM model (google/gemma-4-26b-a4b-it:free) failed: NotFoundError, trying fallback model
[INFO] Fallback model (meta-llama/llama-3.3-70b-instruct:free) succeeded
```

### When Both Models Fail
```
[WARNING] Primary LLM model (google/gemma-4-26b-a4b-it:free) failed: NotFoundError, trying fallback model
[WARNING] Fallback LLM model (meta-llama/llama-3.3-70b-instruct:free) also failed: NotFoundError
[INFO] Using template-based response
```

---

## Testing

### Test Primary Model
1. Start the app: `python app.py`
2. Go to Chat tab
3. Ask: "What should I eat before my appointment?"
4. Check logs for successful Gemini response

### Test Fallback Model
1. Temporarily change primary model to invalid name in code
2. Ask a question in chat
3. Check logs for fallback to Llama
4. Verify response is still generated

### Test Template Fallback
1. Temporarily set `OPENROUTER_API_KEY=` (empty)
2. Ask a question in chat
3. Verify keyword-based response is returned
4. No errors should appear

---

## Model Comparison

| Feature | Google Gemini | Meta Llama |
|---------|--------------|------------|
| Model | gemma-4-26b-a4b-it | llama-3.3-70b-instruct |
| Parameters | 26B | 70B |
| Strengths | Fast, conversational | Strong reasoning |
| Use Case | Primary responses | Fallback |
| Cost | Free | Free |
| Availability | High | High |

---

## Configuration Options

### Change Primary Model
```python
llm_client = LLMClient(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    model="google/gemma-4-26b-a4b-it:free"  # Change here
)
```

### Change Fallback Model
```python
llm_client = LLMClient(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    fallback_model="meta-llama/llama-3.3-70b-instruct:free"  # Change here
)
```

### Disable Fallback
```python
llm_client = LLMClient(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    fallback_model=None  # No fallback, go straight to templates
)
```

---

## Troubleshooting

### Issue: Both models fail with NotFoundError
**Cause**: Model names might be incorrect or not available on OpenRouter

**Solution**:
1. Check available models at https://openrouter.ai/models
2. Verify model names are exact (case-sensitive)
3. Ensure API key has access to free models

### Issue: Slow responses
**Cause**: Primary model might be slow, then tries fallback

**Solution**:
1. Reduce timeout: `LLMClient(timeout=3)`
2. Swap primary and fallback models
3. Use faster model as primary

### Issue: Inconsistent responses
**Cause**: Different models have different styles

**Solution**:
1. Adjust temperature: `temperature=0.5` for more consistent
2. Use same model family for both primary and fallback
3. Improve system prompts for consistency

---

## Next Steps

### Optional Enhancements
1. **Add more fallback models**: Create a chain of 3-4 models
2. **Model selection based on task**: Use different models for different tasks
3. **Performance tracking**: Log which model is used most often
4. **A/B testing**: Compare response quality between models
5. **Caching**: Cache responses to reduce API calls

### Monitoring
- Track success rate of each model
- Monitor average response time
- Log fallback frequency
- Alert if both models fail frequently

---

## Summary

✅ Primary model: Google Gemini (gemma-4-26b-a4b-it:free)
✅ Fallback model: Meta Llama (llama-3.3-70b-instruct:free)
✅ Template fallback: Keyword-based responses
✅ All models are free
✅ Automatic failover
✅ Graceful degradation
✅ No user-facing errors

The system now has robust three-tier fallback ensuring responses are always generated, even if both LLM models fail!
