@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  Testare automata website Ocna de Fier
echo ============================================
echo.

echo [1/4] Verific Python...
python --version
if errorlevel 1 (
    echo EROARE: Python nu este instalat sau nu este in PATH.
    pause
    exit /b 1
)

echo.
echo [2/4] Instalez / verific dependinte...
python -m pip install --upgrade pip
python -m pip install pytest requests beautifulsoup4 selenium webdriver-manager pytest-html
if errorlevel 1 (
    echo EROARE: Nu s-au putut instala dependintele.
    pause
    exit /b 1
)

echo.
echo [3/4] Verific daca pytest gaseste testele...
python -m pytest --collect-only -q test_ocna_de_fier.py
if errorlevel 1 (
    echo EROARE: pytest nu poate colecta testele. Verifica daca test_ocna_de_fier.py este in acelasi folder cu acest fisier BAT.
    pause
    exit /b 1
)

echo.
echo [4/4] Rulez testele si generez raport HTML...
python -m pytest test_ocna_de_fier.py --html=raport_ocna_de_fier.html --self-contained-html

echo.
echo ============================================
echo  Gata. Deschide raport_ocna_de_fier.html
echo ============================================
pause
