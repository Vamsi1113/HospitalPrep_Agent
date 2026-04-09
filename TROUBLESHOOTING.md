# Troubleshooting Guide

## Common Issues

### Issue: ModuleNotFoundError: No module named 'agent.orchestrator'

**Cause:** Python cached bytecode (`.pyc` files) from the old orchestrator module.

**Solution:**
```bash
# Clear Python cache
Remove-Item -Recurse -Force agent/__pycache__
Remove-Item -Recurse -Force __pycache__

# Or on Linux/Mac:
rm -rf agent/__pycache__
rm -rf __pycache__
```

### Issue: Import errors after upgrading to LangGraph

**Cause:** Old cached imports or missing dependencies.

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Clear all caches
Remove-Item -Recurse -Force __pycache__
Remove-Item -Recurse -Force agent/__pycache__
Remove-Item -Recurse -Force services/__pycache__
Remove-Item -Recurse -Force tests/__pycache__
```

### Issue: LangGraph not found

**Cause:** Dependencies not installed.

**Solution:**
```bash
pip install langgraph langchain langchain-core langchain-openai
```

### Issue: Agent execution fails with validation errors

**Cause:** Service method signatures changed during LangGraph integration.

**Solution:** This has been fixed. Make sure you have the latest version of `agent/tools.py`.

## Verification Steps

1. **Test imports:**
```bash
python -c "from agent.graph import run_agent; print('Success')"
```

2. **Test app startup:**
```bash
python -c "import app; print('App imports successfully')"
```

3. **Run the app:**
```bash
python app.py
```

4. **Access the UI:**
```
http://localhost:5000
```

## Getting Help

If issues persist:
1. Check the error message carefully
2. Verify all dependencies are installed: `pip list`
3. Clear all Python caches
4. Restart your terminal/IDE
5. Check `LANGGRAPH_UPGRADE_CONTEXT.md` for architecture details
