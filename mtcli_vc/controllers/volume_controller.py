from mtcli.logger import setup_logger
from mtcli_vc.models.volume_model import calcular_volume_comparativo

log = setup_logger()


def obter_comparacao(symbol: str, days: int, volume_type: str):
    """
    Controlador que obtém o comparativo de volumes.
    Em caso de erro, retorna um dicionário com a chave "erro" para que a view trate a mensagem.
    """
    try:
        return calcular_volume_comparativo(symbol, days, volume_type)
    except Exception as exc:
        log.exception("Erro ao obter comparacao de volume")
        return {"erro": str(exc)}
