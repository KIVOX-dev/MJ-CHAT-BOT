@echo off
echo [*] Attempting to start Ollama service...
start /min "" "ollama" serve
echo [+] Service command sent. 
echo [*] Waiting 5 seconds for initialization...
timeout /t 5 /nobreak > nul
ollama list
echo.
echo [+] If models (phi3, etc.) are listed above, Ollama is now RUNNING.
echo [+] You can now close this window and refresh REM AI.
pause
