@echo off
cd /d "%~dp0"

REM Запуск через py (обычно есть в Windows вместе с Python)
py update_pack.py
IF ERRORLEVEL 1 (
  echo.
  echo ❌ Ошибка при обновлении. Окно не закрываю.
  pause
  exit /b 1
)

echo.
echo ✅ Обновление завершено. Теперь открой GitHub Desktop и сделай Commit + Push.
pause