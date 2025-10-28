import os

import click


def _format_number(value):
    """
    Formata número para apresentação acessível:
     - sem casas decimais quando for inteiro
     - separador de milhares como '.' (padrão BR)
    """
    try:
        # se é NaN ou infinito, transforma em 0.0 para evitar problemas
        if value is None:
            return "0"
        # valor já é float
        iv = int(round(value))
        s = f"{iv:,}"  # usa separador da localidade (vírgula em python)
        return s.replace(",", ".")
    except Exception:
        return str(value)


def exibir_comparacao(dados: dict):
    """
    Exibe resultado de forma acessível usando click.echo.
    Se houver "erro" no dicionário, exibe a mensagem de erro e retorna.
    Permite desativar emojis definindo MTCLI_NO_EMOJI=1 no ambiente.
    """
    # checa erro vindo do controlador
    if not isinstance(dados, dict):
        click.echo("Erro: dados inválidos retornados pelo controlador.")
        return

    if "erro" in dados:
        click.echo(f"Erro: {dados['erro']}")
        return

    # emoji toggle (útil para leitores que não lidam bem com glyphs)
    no_emoji = os.getenv("MTCLI_NO_EMOJI", "1") == "1"

    def pref(txt):
        return txt if no_emoji else txt

    tipo = "Tick Volume" if dados.get("volume_type") == "tick" else "Volume Real"

    click.echo(pref("\n") + f"Comparativo de Volume - {dados.get('symbol')}")
    click.echo(pref("") + f"Horário atual: {dados.get('hora_atual')}")
    click.echo(pref("") + f"Tipo de volume: {tipo}")
    click.echo(pref("") + f"Média baseada em {dados.get('days')} últimos pregões")
    click.echo(pref("") + f"Último pregão considerado: {dados.get('ultimo_pregao')}\n")

    click.echo(f"Volume de hoje: {_format_number(dados.get('vol_hoje'))}")
    click.echo(
        f"Volume do último pregão até esse horário: {_format_number(dados.get('vol_ontem'))}"
    )
    click.echo(
        f"Volume médio até esse horário: {_format_number(dados.get('vol_medio'))}"
    )

    click.echo("")  # separador
    click.echo(f"Hoje vs Último pregão: {dados.get('perc_ontem', 0.0):+.2f}%")
    click.echo(f"Hoje vs Média: {dados.get('perc_medio', 0.0):+.2f}%\n")
