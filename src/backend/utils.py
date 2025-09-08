def add_technical_features(df):
    # 1. SMA_5: 5-day Simple Moving Average - short-term trend signal
    df["SMA_5"] = df['close'].rolling(5).mean()

    # 2. SMA_20: 20-day Simple Moving Average - long-term trend signal
    df["SMA_20"] = df['close'].rolling(20).mean()

    # 3. Calculate daily price change
    df["diff"] = df["close"].diff()

    # 4. Gain: only positive differences (else 0)
    df["gain"] = df["diff"].where(df["diff"] > 0, 0)

    # 5. Loss: convert negative differences to positive values (else 0)
    df["loss"] = -df["diff"].where(df["diff"] < 0, 0)

    # 6. Calculate average gain and average loss over 14 days (RSI window)
    df["avgGain"] = df["gain"].rolling(14).mean()
    df["avgLoss"] = df["loss"].rolling(14).mean()

    # 7. RSI: Relative Strength Index
    #    Measures momentum by comparing recent gains vs losses
    #    >70 = overbought, <30 = oversold
    df["RSI"] = 100 - (100 / (1 + (df["avgGain"]/df["avgLoss"])))

    # 8. Volume Ratio: compares current volume to 10-day average volume
    #    High ratio indicates high interest or unusual trading behavior
    df["volume_ratio"] = df["volume"] / df["volume"].rolling(10).mean()

    return df
