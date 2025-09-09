import requests


def get_conversion_rate(from_currency, to_currency):
    """Get conversion rate without converting a specific amount"""
    if from_currency == to_currency:
        return 1.0
    try:
        key = "9c963643d7d186655a968060"
        url = f"https://v6.exchangerate-api.com/v6/{key}/pair/{from_currency}/{to_currency}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if 'conversion_rate' in data:
            return data['conversion_rate']
        else:
            print(f"Rate fetch failed: {data}")
            return 1.0

    except Exception as e:
        print(f"Rate fetch error: {e}")
        return 1.0

def convert_currency(amount, from_currency, to_currency):
    if from_currency == to_currency:
        # no conversion needed
        return amount
    try:
        key = "9c963643d7d186655a968060"
        url = f"https://v6.exchangerate-api.com/v6/{key}/pair/{from_currency}/{to_currency}/{amount}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # Raises exception for bad status codes
        data = response.json()

        # The exchangerate-host API returns the converted amount directly in 'result'
        if 'conversion_result' in data:
            return round(data['conversion_result'], 2)
        else:
            print(f"Currency conversion failed: {data}")
            return amount

    except Exception as e:
        print(f"Currency conversion error: {e}")
        # fallback to original value
        return amount

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


from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

key = "53746e59369d4b3db63904264741f5a3"
def fetch_news_headlines(symbol):
    url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey={key}"
    response = requests.get(url)
    return [article['title'] for article in response.json().get('articles', [])[:10]]

def analyze_sentiment(headlines):
    analyzer = SentimentIntensityAnalyzer()
    scores = [analyzer.polarity_scores(headline)['compound'] for headline in headlines]
    return sum(scores) / len(scores) if scores else 0



