import click

from mtcli_vc.conf import DAYS_AVERAGE, SYMBOL, TIMEZONE, VOLUME
from mtcli_vc.controllers.volume_controller import obter_comparacao
from mtcli_vc.views.volume_view import exibir_comparacao


@click.command()
@click.version_option(package_name="mtcli-vc")
@click.option(
    "--symbol",
    "-s",
    default=SYMBOL,
    show_default=True,
    help="Símbolo do ativo (ex: WIN$)",
)
@click.option(
    "--days",
    default=DAYS_AVERAGE,
    show_default=True,
    help="Número de dias para cálculo da média",
    type=int,
)
@click.option(
    "--volume",
    type=click.Choice(["tick", "real"], case_sensitive=False),
    default=VOLUME,
    show_default=True,
    help="Tipo de volume (tick ou real)",
)
@click.option("--show-tz", is_flag=True, help="Mostra o timezone configurado e sai.")
def volume(symbol, days, volume, show_tz):
    """Exibe comparação de volume atual com o último pregão e a média."""
    if show_tz:
        click.echo(f"Timezone configurado: {TIMEZONE}")
        return

    # validações simples
    if days is None or days < 1:
        raise click.BadParameter(
            "O número de dias (--days) deve ser inteiro maior ou igual a 1."
        )

    dados = obter_comparacao(symbol, days, volume)
    exibir_comparacao(dados)
