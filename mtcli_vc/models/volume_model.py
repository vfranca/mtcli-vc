import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta, UTC
import pytz
from mtcli_vc.conf import TIMEZONE
from mtcli.logger import setup_logger

log = setup_logger()
tz = pytz.timezone(TIMEZONE)


def obter_dados(symbol: str, days: int):
    """
    Obtém candles M1 dos últimos N dias.

    Funciona com:
      - Forex / ActivTrades → usa copy_rates_range()
      - B3 / Clear / XP     → usa fallback copy_rates_from() com paginação (máx. 1000 candles/bloco)

    Compatível com Python 3.13+ (usa datetime.UTC em vez de datetime.utcnow()).
    """
    if days is None or days < 1:
        raise ValueError("Parâmetro 'days' deve ser inteiro positivo.")

    # Horário local e UTC
    agora_local = datetime.now(tz)
    inicio_local = agora_local - timedelta(days=days + 10)

    # Datas UTC naive (sem tzinfo, exigido pelo MetaTrader5)
    agora = datetime.now(UTC).replace(tzinfo=None)
    inicio = inicio_local.astimezone(UTC).replace(tzinfo=None)

    initialized = False
    try:
        initialized = mt5.initialize()
        if not initialized:
            raise RuntimeError("Erro ao conectar ao MetaTrader5")

        log.debug(f"MT5 inicializado. Coletando dados de {symbol} desde {inicio} até {agora} (UTC naive)")

        # Garante que o símbolo esteja visível no Market Watch
        info = mt5.symbol_info(symbol)
        if info is None or not info.visible:
            log.warning(f"Símbolo '{symbol}' não está visível. Tentando selecionar...")
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Não foi possível selecionar o símbolo '{symbol}'. Verifique no MT5 se está ativo.")

        # 1️⃣ Tenta método padrão (funciona no Forex / ActivTrades)
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, inicio, agora)
        if rates is None:
            code, reason = mt5.last_error()
            log.warning(f"Erro copy_rates_range: {code} - {reason}")

            # 2️⃣ Fallback para Clear / B3 (limite de 1000 candles)
            if code == -2:
                log.info("Servidor limita a 1000 candles. Ativando modo de paginação (copy_rates_from).")

                candles_total = []
                total_candles = int((days + 10) * 1440)  # minutos no período
                fetched = 0
                chunk = 1000
                cursor_time = agora

                while fetched < total_candles:
                    rates_chunk = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, cursor_time, chunk)
                    if rates_chunk is None or len(rates_chunk) == 0:
                        log.debug(f"Nenhum dado adicional após {fetched} candles. last_error={mt5.last_error()}")
                        break

                    candles_total.extend(rates_chunk)
                    fetched += len(rates_chunk)

                    # Atualiza o cursor para o candle mais antigo do último bloco
                    oldest_time = rates_chunk[0]["time"]
                    cursor_time = datetime.fromtimestamp(oldest_time, UTC)
                    log.debug(f"Baixados {fetched} candles até {cursor_time.isoformat()}")

                    # Se não conseguiu 1000, significa que acabou o histórico
                    if len(rates_chunk) < chunk:
                        break

                rates = candles_total[::-1]  # inverter para ordem cronológica crescente

        if rates is None or len(rates) == 0:
            raise RuntimeError(f"Nenhum dado retornado para {symbol}. Verifique histórico e horário de pregão.")

        # Cria DataFrame e converte timestamps
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s").dt.tz_localize("UTC").dt.tz_convert(tz)
        return df

    finally:
        if initialized:
            try:
                mt5.shutdown()
                log.debug("MT5 finalizado (shutdown).")
            except Exception:
                log.exception("Falha ao finalizar MT5 (shutdown).")


def encontrar_ultimo_dia_com_volume(df, hoje, col_volume):
    """Retorna o último dia de pregão antes de 'hoje' com volume > 0."""
    if df.empty:
        return None
    for dia in sorted(df["date"].unique(), reverse=True):
        if dia >= hoje:
            continue
        volume = float(df.loc[df["date"] == dia, col_volume].sum())
        if volume > 0:
            return dia
    return None


def calcular_volume_comparativo(symbol: str, days: int, volume_type: str):
    """
    Calcula e compara:
      - volume do dia atual até o momento
      - volume do último pregão válido até o mesmo horário
      - volume médio dos últimos N pregões até o mesmo horário
    """
    if days is None or days < 1:
        raise ValueError("O parâmetro 'days' deve ser inteiro >= 1.")

    df = obter_dados(symbol, days)
    agora = datetime.now(tz)
    hora_atual = agora.time()
    hoje = agora.date()

    df["date"] = df["time"].dt.date
    df["hora"] = df["time"].dt.time

    col_volume = "tick_volume" if volume_type == "tick" else "real_volume"
    if col_volume not in df.columns:
        raise ValueError(f"Coluna '{col_volume}' não encontrada nos dados para {symbol}")

    vol_hoje = float(df.loc[(df["date"] == hoje) & (df["hora"] <= hora_atual), col_volume].sum())

    ontem = encontrar_ultimo_dia_com_volume(df, hoje, col_volume)
    if ontem is None:
        raise RuntimeError("Não foi possível encontrar o último dia de pregão válido antes de hoje.")

    vol_ontem = float(df.loc[(df["date"] == ontem) & (df["hora"] <= hora_atual), col_volume].sum())

    dias_passados = [d for d in sorted(df["date"].unique(), reverse=True) if d < hoje][:days]
    volumes = [
        float(df.loc[(df["date"] == d) & (df["hora"] <= hora_atual), col_volume].sum())
        for d in dias_passados
        if float(df.loc[(df["date"] == d), col_volume].sum()) > 0
    ]
    vol_medio = sum(volumes) / len(volumes) if volumes else 0.0

    perc_ontem = ((vol_hoje - vol_ontem) / vol_ontem * 100.0) if vol_ontem > 0 else 0.0
    perc_medio = ((vol_hoje - vol_medio) / vol_medio * 100.0) if vol_medio > 0 else 0.0

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
