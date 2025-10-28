from datetime import datetime, timedelta

import MetaTrader5 as mt5
import pandas as pd
import pytz

from mtcli.logger import setup_logger
from mtcli_vc.conf import TIMEZONE

log = setup_logger()
tz = pytz.timezone(TIMEZONE)


def obter_dados(symbol: str, days: int):
    """
    Obtém candles M1 dos últimos N dias, com margem extra para cobrir fins de semana/feriados.
    Garante que a conexão com o MetaTrader5 seja finalizada mesmo em erro.
    """
    if days is None or days < 1:
        raise ValueError("Parâmetro 'days' deve ser inteiro positivo.")

    agora = datetime.now(tz)
    inicio = agora - timedelta(
        days=days + 10
    )  # margem para cobrir fins de semana/feriados

    initialized = False
    try:
        initialized = mt5.initialize()
        if not initialized:
            raise RuntimeError("Erro ao conectar ao MetaTrader5")
        log.debug(
            f"MT5 inicializado. Coletando dados de {symbol} desde {inicio.isoformat()} até {agora.isoformat()}"
        )

        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, inicio, agora)
        if rates is None:
            raise RuntimeError(f"Erro ao obter dados para {symbol} (rates is None)")

        df = pd.DataFrame(rates)
        if df.empty:
            raise RuntimeError(
                f"Nenhum dado retornado para {symbol}. Verifique se o símbolo está correto e se há pregão."
            )

        # converte timestamp em timezone configurado
        df["time"] = (
            pd.to_datetime(df["time"], unit="s").dt.tz_localize("UTC").dt.tz_convert(tz)
        )
        return df

    finally:
        if initialized:
            try:
                mt5.shutdown()
                log.debug("MT5 finalizado (shutdown).")
            except Exception:
                # Não propaga erros de shutdown para não mascarar a exceção principal
                log.exception("Falha ao finalizar MT5 (shutdown).")


def encontrar_ultimo_dia_com_volume(df, hoje, col_volume):
    """
    Retorna o último dia de pregão antes de 'hoje' com volume > 0.
    Percorre as datas de forma decrescente e ignora dias >= hoje.
    """
    if df.empty:
        return None

    # usamos unique ordenado decrescente
    for dia in sorted(df["date"].unique(), reverse=True):
        if dia >= hoje:
            continue
        # soma direta; pode retornar numpy types -> convert later
        volume = df.loc[df["date"] == dia, col_volume].sum()
        try:
            if float(volume) > 0.0:
                return dia
        except Exception:
            # se não for conversível, ignora esse dia
            continue
    return None


def calcular_volume_comparativo(symbol: str, days: int, volume_type: str):
    """
    Calcula volumes:
      - vol_hoje: volume do dia atual até hora atual
      - vol_ontem: volume do último pregão válido até mesma hora
      - vol_medio: média dos últimos `days` pregões válidos (excluindo hoje) até a mesma hora

    Retorna dicionário com valores float e percentuais.
    """
    if days is None or days < 1:
        raise ValueError("O parâmetro 'days' deve ser inteiro >= 1.")

    df = obter_dados(symbol, days)
    agora = datetime.now(tz)
    hora_atual = agora.time()
    hoje = agora.date()

    # segurança: se df for None ou vazio, obter_dados já levantou RuntimeError.
    df["date"] = df["time"].dt.date
    df["hora"] = df["time"].dt.time

    # Define coluna de volume
    col_volume = "tick_volume" if volume_type == "tick" else "real_volume"
    if col_volume not in df.columns:
        raise ValueError(
            f"Coluna de volume '{col_volume}' não encontrada nos dados para o símbolo {symbol}"
        )

    # Volume de hoje
    vol_hoje = float(
        df.loc[(df["date"] == hoje) & (df["hora"] <= hora_atual), col_volume].sum()
    )

    # Último pregão válido (pula domingos/feriados)
    ontem = encontrar_ultimo_dia_com_volume(df, hoje, col_volume)
    if ontem is None:
        # não encontrou pregão anterior; pode ocorrer em ativos recém listados
        raise RuntimeError(
            "Não foi possível encontrar o último dia de pregão válido antes de hoje."
        )

    vol_ontem = float(
        df.loc[(df["date"] == ontem) & (df["hora"] <= hora_atual), col_volume].sum()
    )

    # Média dos últimos N dias de pregão (excluindo hoje)
    dias_passados = [d for d in sorted(df["date"].unique(), reverse=True) if d < hoje]
    dias_passados = dias_passados[:days]

    volumes = []
    for d in dias_passados:
        v = float(
            df.loc[(df["date"] == d) & (df["hora"] <= hora_atual), col_volume].sum()
        )
        if v > 0:
            volumes.append(v)

    vol_medio = float(sum(volumes) / len(volumes)) if volumes else 0.0

    # Comparações percentuais (float evita overflow)
    perc_ontem = (
        ((vol_hoje - vol_ontem) / vol_ontem * 100.0) if vol_ontem > 0.0 else 0.0
    )
    perc_medio = (
        ((vol_hoje - vol_medio) / vol_medio * 100.0) if vol_medio > 0.0 else 0.0
    )

    return {
        "symbol": symbol,
        "hora_atual": agora.strftime("%H:%M"),
        "vol_hoje": vol_hoje,
        "vol_ontem": vol_ontem,
        "vol_medio": vol_medio,
        "perc_ontem": perc_ontem,
        "perc_medio": perc_medio,
        "volume_type": volume_type,
        "days": days,
        "ultimo_pregao": ontem.strftime("%Y-%m-%d"),
    }
