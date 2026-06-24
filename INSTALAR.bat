@echo off
title Mana Food - Instalador
color 0A
echo.
echo  ============================================
echo     MANA FOOD - INSTALADOR v4.0
echo  ============================================
echo.

:: Verifica Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo  [ERRO] Python nao encontrado!
    echo  Baixe em: https://python.org/downloads
    echo  Marque "Add Python to PATH" na instalacao!
    echo.
    pause
    exit
)
echo  [OK] Python encontrado!

:: Verifica Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo  [ERRO] Git nao encontrado!
    echo  Baixe em: https://git-scm.com/download/win
    echo  Instale com as opcoes padrao (Next, Next, Finish)
    echo.
    pause
    exit
)
echo  [OK] Git encontrado!

:: Instala dependencias Python
echo  Instalando dependencias...
python -m pip install pystray pillow --quiet --disable-pip-version-check >nul 2>&1
echo  [OK] Dependencias instaladas!

:: Clona ou atualiza o repositorio
if exist "C:\ManaFood\.git" (
    echo  [OK] Sistema ja instalado, atualizando...
    cd /d "C:\ManaFood"
    git pull >nul 2>&1
) else (
    echo  Baixando sistema do servidor...
    git clone https://github.com/techprimedev-br/manafood.git "C:\ManaFood" >nul 2>&1
)
echo  [OK] Sistema instalado em C:\ManaFood\

:: Cria pastas de dados (nao versionadas)
if not exist "C:\ManaFood\lanchonete\data" mkdir "C:\ManaFood\lanchonete\data"
if not exist "C:\ManaFood\lanchonete\imagens" mkdir "C:\ManaFood\lanchonete\imagens"
if not exist "C:\ManaFood\lanchonete\backups" mkdir "C:\ManaFood\lanchonete\backups"
echo  [OK] Pastas de dados criadas!

:: Cria atalho na area de trabalho
for /f "delims=" %%i in ('where pythonw 2^>nul') do set PYTHONW=%%i
if "%PYTHONW%"=="" (
    for /f "delims=" %%i in ('where python') do set PYTHONW=%%~dpi\pythonw.exe
)

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%temp%\atalho.vbs"
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Mana Food.lnk" >> "%temp%\atalho.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%temp%\atalho.vbs"
echo oLink.TargetPath = "%PYTHONW%" >> "%temp%\atalho.vbs"
echo oLink.Arguments = """C:\ManaFood\mana.py""" >> "%temp%\atalho.vbs"
echo oLink.WorkingDirectory = "C:\ManaFood" >> "%temp%\atalho.vbs"
echo oLink.IconLocation = "C:\ManaFood\logo.ico" >> "%temp%\atalho.vbs"
echo oLink.Description = "Mana Food - PDV" >> "%temp%\atalho.vbs"
echo oLink.Save >> "%temp%\atalho.vbs"
cscript //nologo "%temp%\atalho.vbs"
del "%temp%\atalho.vbs"
echo  [OK] Atalho criado na area de trabalho!

echo.
echo  ============================================
echo     INSTALACAO CONCLUIDA!
echo  ============================================
echo.
echo  Requisitos: Python + Git [OK]
echo  Local: C:\ManaFood\
echo  Atalho: "Mana Food" na area de trabalho
echo.
echo  O sistema recebe atualizacoes automaticas!
echo.
pause
