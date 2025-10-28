@echo off
SET CMD=%1

IF /i "%CMD%"=="test" (
	echo Executando testes...
	poetry run pytest --cov=mtcli_vc --cov-report=html
	goto :EOF
)

IF "%CMD%"=="format" (
	echo Formatando o codigo com ruff...
	poetry run ruff format .
    goto :EOF
)

IF /i "%CMD%"=="check" (
	echo Verificando o codigo com ruff...
	poetry run ruff check .
	goto :EOF
)

IF /i "%CMD%"=="lint" (
	echo executando linter com ruff...
	poetry run ruff check . --fix
	goto :EOF
)

echo Comando invalido: %CMD%
echo Uso: make [test] [format] [check] [lint]
