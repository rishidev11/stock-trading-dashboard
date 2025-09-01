import pandas as pd
def slidingWindow(prices, windowSize, x_values, y_values):
    i = 0
    while (i+3) < len(prices):
        x_values.append(prices[i:i + windowSize])  # actual values
        y_values.append(prices[i + windowSize])  # actual next-day price
        i += 1

    return x_values, y_values

def add_technical_features(df):
    df["SMA_5"] = df['close'].rolling(5).mean()
    df["SMA_20"] = df['close'].rolling(20).mean()

    df["diff"] = df["close"].diff()

    df["gain"] = df["diff"].where(df["diff"] > 0, 0)

    # make losses positive
    df["loss"] = -df["diff"].where(df["diff"] < 0, 0)

    df["avgGain"] = df["gain"].rolling(14).mean()
    df["avgLoss"] = df["loss"].rolling(14).mean()

    df["RSI"] = 100 - (100 / (1 + (df["avgGain"]/df["avgLoss"])))

    df["volume_ratio"] = df["volume"] / df["volume"].rolling(10).mean()


    return df

