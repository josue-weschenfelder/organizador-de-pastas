@echo off
echo Encerrando instancia em execucao (se houver)...
taskkill /f /im OrganizadorDePastas.exe >nul 2>&1

echo Instalando dependencias...
pip install -r requirements-dev.txt

echo Limpando builds anteriores...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo Gerando executavel...
pyinstaller --onefile --noconsole --name OrganizadorDePastas organizador_pastas.py
if errorlevel 1 (
    echo.
    echo ERRO ao gerar o executavel. Veja "Solucao de problemas" no README.
    pause
    exit /b 1
)

echo.
echo Executavel gerado em dist\OrganizadorDePastas.exe
pause
