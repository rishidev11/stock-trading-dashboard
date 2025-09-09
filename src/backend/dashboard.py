import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

def get_currency_symbol(currency):
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£"
    }
    return symbols.get(currency, "$")

# Page configuration
st.set_page_config(
    page_title="Stock Price Predictor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }

    .prediction-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        color: white;
        margin: 1rem 0;
    }

    .sentiment-positive {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }

    .sentiment-negative {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }

    .feature-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e1e5e9;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .sidebar-content {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">📈 AI Stock Price Predictor</h1>', unsafe_allow_html=True)

# Sidebar for controls
with st.sidebar:
    st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
    st.header("🎯 Controls")

    # Stock symbol input
    symbol = st.text_input(
        "Stock Symbol",
        placeholder="Enter ticker (e.g., AAPL, TSLA)",
        help="Enter a valid stock ticker symbol"
    )

    if symbol:
        # Time period selection
        period = st.selectbox(
            '📅 Time Period',
            ('1mo', '3mo', '6mo', '1y', '2y'),
            index=2,  # Default to 6mo
            help="Select historical data timeframe"
        )

        # Prediction window
        window_size = st.slider(
            "🔮 Prediction Window",
            min_value=2,
            max_value=15,
            value=5,
            help="Number of days to use for prediction"
        )

        # Currency toggle
        currency = st.selectbox(
            "💱 Currency",
            options=["USD", "EUR", "GBP"],
            index=0,
            help="Select preferred currency for price display"
        )

        # Analysis options
        st.subheader("📊 Analysis Options")
        show_volume = st.checkbox("Show Volume", value=True)
        show_sma = st.checkbox("Show Moving Averages", value=True)
        show_predictions = st.checkbox("Show Predictions", value=True)

    st.markdown('</div>', unsafe_allow_html=True)

if symbol:
    # Fetch basic stock data
    with st.spinner('Fetching stock data...'):
        response = requests.get(f"http://localhost:8000/api/stock/{symbol}?target_currency={currency}")

    if response.status_code == 200:
        data = response.json()
        currency_symbol = get_currency_symbol(currency)

        # Main content area with columns
        col1, col2, col3, col4 = st.columns(4)

        # Key metrics row - Updated with proper currency symbols
        with col1:
            price_change = data['current_price'] - data['previous_close']
            st.metric(
                "Current Price",
                f"{currency_symbol}{data['current_price']:.2f}",  # Changed from $ to currency_symbol
                delta=f"{price_change:+.2f}",
                delta_color="normal"
            )

        with col2:
            st.metric(
                "Day Change",
                f"{data['day_change_percent']:.2f}%",
                delta=f"{data['day_change_percent']:+.2f}%"
            )

        with col3:
            st.metric(
                "Previous Close",
                f"{currency_symbol}{data['previous_close']:.2f}"  # Changed from $ to currency_symbol
            )

        with col4:
            st.metric(
                "Currency",
                data['currency']
            )

        # Company info
        st.markdown(f"### 🏢 {data['company_name']}")

        # Fetch historical data
        with st.spinner('Loading historical data...'):
            hist_response = requests.get(f"http://localhost:8000/api/stock/{symbol}/history?period={period}&target_currency={currency}")

        if hist_response.status_code == 200:
            df = pd.DataFrame(hist_response.json()["data"])
            df['date'] = pd.to_datetime(df['date'])

            # Create two columns for charts
            chart_col1, chart_col2 = st.columns([3, 1])

            with chart_col1:
                st.subheader("📈 Price Chart")

                # Base price chart
                price_chart = alt.Chart(df).mark_line(
                    color='#667eea',
                    strokeWidth=2
                ).encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("close:Q", title=f"Price ({currency_symbol})", scale=alt.Scale(zero=False)),
                    tooltip=["date:T", "close:Q", "volume:Q"]
                ).properties(
                    height=400
                )

                # Add moving averages if selected
                charts_to_layer = [price_chart]
                if show_sma and len(df) > 20:
                    df['SMA_20'] = df['close'].rolling(20).mean()
                    sma_chart = alt.Chart(df).mark_line(
                        color='orange',
                        strokeDash=[5, 5]
                    ).encode(
                        x="date:T",
                        y="SMA_20:Q",
                        tooltip=["date:T", "SMA_20:Q"]
                    )
                    charts_to_layer.append(sma_chart)

                # Prediction logic
                if show_predictions:
                    with st.spinner('Generating prediction...'):
                        pred_response = requests.get(
                            f"http://localhost:8000/api/stock/{symbol}/predict?windowSize={window_size}&target_currency={currency}")

                    if pred_response.status_code == 200:
                        pred_data = pred_response.json()
                        predicted_price = pred_data['predicted_close_price']
                        last_close = df["close"].iloc[-1]

                        # Prediction marker
                        last_date = df["date"].iloc[-1]
                        next_date = last_date + pd.Timedelta(days=1)
                        prediction_df = pd.DataFrame([{
                            "date": next_date,
                            "close": predicted_price,
                            "type": "Prediction"
                        }])

                        marker_color = "#00ff00" if predicted_price >= last_close else "#ff0000"
                        prediction_marker = alt.Chart(prediction_df).mark_point(
                            shape="triangle-up",
                            size=200,
                            color=marker_color
                        ).encode(
                            x="date:T",
                            y="close:Q",
                            tooltip=["date:T", "close:Q", "type:N"]
                        )
                        charts_to_layer.append(prediction_marker)

                # Combine all charts
                final_chart = alt.layer(*charts_to_layer).resolve_scale(
                    y='independent'
                ).properties(
                    title=f"{symbol.upper()} Stock Analysis"
                )

                st.altair_chart(final_chart, use_container_width=True)

                # Volume chart if selected
                if show_volume:
                    volume_chart = alt.Chart(df).mark_bar(
                        color='lightblue',
                        opacity=0.7
                    ).encode(
                        x="date:T",
                        y=alt.Y("volume:Q", title="Volume"),
                        tooltip=["date:T", "volume:Q"]
                    ).properties(
                        height=150,
                        title="Trading Volume"
                    )
                    st.altair_chart(volume_chart, use_container_width=True)

            with chart_col2:
                # Prediction results
                if show_predictions and 'pred_data' in locals():
                    st.markdown("### 🔮 AI Prediction")

                    # Prediction box
                    prediction_change = ((predicted_price - last_close) / last_close) * 100
                    direction = "📈" if prediction_change > 0 else "📉"

                    st.markdown(f"""
                            <div class="prediction-box">
                                <h2>{direction} Next Close</h2>
                                <h1>{currency_symbol}{predicted_price:.2f}</h1>  # Changed from $ to currency_symbol
                                <h3>{prediction_change:+.2f}%</h3>
                            </div>
                            """, unsafe_allow_html=True)

                    # Model confidence/features
                    st.markdown("#### 🧠 Model Features")
                    features_df = pd.DataFrame(pred_data["last_window"])
                    st.dataframe(features_df.round(4), height=200)

            # News sentiment section
            sentiment_response = requests.get(f"http://localhost:8000/api/stock/{symbol}/sentiment")
            if sentiment_response.status_code == 200:
                sentiment_data = sentiment_response.json()

                st.markdown("---")
                st.subheader("📰 Market Sentiment")

                # Sentiment metrics in columns
                sent_col1, sent_col2, sent_col3 = st.columns(3)

                with sent_col1:
                    sentiment_score = sentiment_data["sentiment_score"]
                    sentiment_emoji = "😊" if sentiment_score > 0.1 else "😐" if sentiment_score > -0.1 else "😟"
                    st.metric(
                        "Sentiment Score",
                        f"{sentiment_score:.3f}",
                        help="Range: -1 (very negative) to +1 (very positive)"
                    )

                with sent_col2:
                    st.metric("Status", f"{sentiment_emoji} {sentiment_data['status']}")

                with sent_col3:
                    st.metric("News Articles", len(sentiment_data["headlines"]))

                # Headlines in expandable section
                with st.expander("📰 Latest Headlines", expanded=False):
                    for i, headline in enumerate(sentiment_data["headlines"][:5], 1):
                        st.markdown(f"**{i}.** {headline}")

        else:
            st.error("❌ Unable to fetch historical data. Please check the stock symbol.")
    else:
        st.error(f"❌ Stock '{symbol}' not found. Please verify the ticker symbol.")

else:
    # Welcome screen when no symbol is entered
    st.markdown("""
    ### 👋 Welcome to AI Stock Predictor!

    **Features:**
    - 📊 Real-time stock data and charts
    - 🤖 AI-powered price predictions
    - 📰 News sentiment analysis  
    - 📈 Technical indicators
    - 🎯 Interactive controls

    **Get Started:**
    Enter a stock symbol in the sidebar to begin your analysis!

    **Popular Stocks:** AAPL, TSLA, GOOGL, MSFT, AMZN, NVDA
    """)

    # Example stocks grid
    st.markdown("### 🔥 Popular Stocks")
    example_cols = st.columns(6)
    popular_stocks = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN", "NVDA"]

    for i, stock in enumerate(popular_stocks):
        with example_cols[i]:
            if st.button(f"📊 {stock}", key=f"stock_{stock}"):

                st.page_link("pages/page2.py", label="Go to Page 2")
                st.rerun()  # This would ideally set the symbol and refresh
