import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_BASE = "http://localhost:8000"

# Custom CSS
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

    .auth-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .portfolio-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }

    .holding-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e1e5e9;
        margin: 0.5rem 0;
    }

    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }

    .error-message {
        background: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
def initialize_session_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'login'
    if 'selected_stock' not in st.session_state:
        st.session_state.selected_stock = None


initialize_session_state()


# API helper functions
def make_authenticated_request(endpoint, method="GET", data=None):
    headers = {'Authorization': f'Bearer {st.session_state.token}'}
    url = f"{API_BASE}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers)

        if response.status_code == 401:
            st.session_state.authenticated = False
            st.session_state.token = None
            st.rerun()

        return response
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def logout():
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.user_email = None
    st.session_state.current_page = 'login'
    st.rerun()


# Authentication Pages
def login_page():
    st.markdown('<h1 class="main-header">Welcome to Trading Platform</h1>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        st.subheader("Login to Your Account")

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                try:
                    response = requests.post(f"{API_BASE}/auth/login",
                                             json={"email": email, "password": password})

                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.token = data['access_token']
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.session_state.current_page = 'dashboard'
                        st.success("Login successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                except Exception as e:
                    st.error(f"Login error: {e}")

        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        st.subheader("Create New Account")

        with st.form("register_form"):
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_confirm = st.text_input("Confirm Password", type="password")
            reg_submit = st.form_submit_button("Register")

            if reg_submit:
                if reg_password != reg_confirm:
                    st.error("Passwords don't match")
                elif len(reg_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    try:
                        response = requests.post(f"{API_BASE}/auth/register",
                                                 json={"email": reg_email, "password": reg_password})

                        if response.status_code == 200:
                            st.success("Registration successful! Please login.")
                        else:
                            st.error("Registration failed. Email might already exist.")
                    except Exception as e:
                        st.error(f"Registration error: {e}")

        st.markdown('</div>', unsafe_allow_html=True)


# Dashboard Page
def dashboard_page():
    # Header with user info
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown('<h1 class="main-header">Trading Dashboard</h1>', unsafe_allow_html=True)
    with col2:
        st.write(f"Welcome, {st.session_state.user_email}")
    with col3:
        if st.button("Logout"):
            logout()

    # Get portfolio data
    portfolio_response = make_authenticated_request("/portfolio/")

    if portfolio_response and portfolio_response.status_code == 200:
        portfolio_data = portfolio_response.json()

        # Portfolio overview
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Cash Balance", f"${portfolio_data['cash_balance']:.2f}")

        with col2:
            holdings_value = portfolio_data.get('holdings_market_value', 0)
            st.metric("Holdings Value", f"${holdings_value:.2f}")

        with col3:
            total_value = portfolio_data.get('total_portfolio_value', portfolio_data['cash_balance'])
            st.metric("Total Portfolio", f"${total_value:.2f}")

        with col4:
            pnl = portfolio_data.get('total_unrealised_pnl', 0)
            pnl_color = "normal" if pnl >= 0 else "inverse"
            st.metric("P&L", f"${pnl:.2f}", delta=f"{pnl:.2f}", delta_color=pnl_color)

        # Holdings section
        st.subheader("Your Holdings")
        holdings = portfolio_data.get('holdings', [])

        if holdings:
            for holding in holdings:
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])

                with col1:
                    if st.button(f"📊 {holding['symbol']}", key=f"holding_{holding['symbol']}"):
                        st.session_state.selected_stock = holding['symbol']
                        st.session_state.current_page = 'stock_detail'
                        st.rerun()

                with col2:
                    st.write(f"Qty: {holding['quantity']}")

                with col3:
                    st.write(f"Avg: ${holding.get('avg_price', 0):.2f}")

                with col4:
                    current_price = holding.get('current_price', 0)
                    st.write(f"Current: ${current_price:.2f}")

                with col5:
                    pnl = holding.get('unrealised_pnl', 0)
                    pnl_pct = holding.get('pnl_percentage', 0)
                    color = "🟢" if pnl >= 0 else "🔴"
                    st.write(f"{color} ${pnl:.2f} ({pnl_pct:.1f}%)")
        else:
            st.info("No holdings yet. Search for stocks to start trading!")

    # Quick stock search
    st.subheader("Search Stocks")
    search_col1, search_col2 = st.columns([3, 1])

    with search_col1:
        stock_symbol = st.text_input("Enter stock symbol (e.g., AAPL, TSLA)", key="stock_search")

    with search_col2:
        if st.button("View Stock") and stock_symbol:
            st.session_state.selected_stock = stock_symbol.upper()
            st.session_state.current_page = 'stock_detail'
            st.rerun()

    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📈 View All Stocks"):
            st.session_state.current_page = 'stock_search'
            st.rerun()

    with col2:
        if st.button("📋 Transaction History"):
            st.session_state.current_page = 'transactions'
            st.rerun()


# Stock Detail Page
def stock_detail_page():
    if not st.session_state.selected_stock:
        st.error("No stock selected")
        if st.button("Back to Dashboard"):
            st.session_state.current_page = 'dashboard'
            st.rerun()
        return

    symbol = st.session_state.selected_stock

    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title(f"📊 {symbol} Analysis")
    with col2:
        if st.button("🏠 Dashboard"):
            st.session_state.current_page = 'dashboard'
            st.rerun()
    with col3:
        if st.button("Logout"):
            logout()

    # Get stock data
    try:
        response = requests.get(f"{API_BASE}/api/stock/{symbol}")
        if response.status_code == 200:
            stock_data = response.json()

            # Stock metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                price_change = stock_data['current_price'] - stock_data['previous_close']
                st.metric(
                    "Current Price",
                    f"${stock_data['current_price']:.2f}",
                    delta=f"{price_change:+.2f}"
                )

            with col2:
                st.metric(
                    "Day Change",
                    f"{stock_data['day_change_percent']:.2f}%"
                )

            with col3:
                st.metric(
                    "Previous Close",
                    f"${stock_data['previous_close']:.2f}"
                )

            with col4:
                st.write(f"**Company:** {stock_data['company_name']}")

            # Trading section
            st.subheader("Trade")
            trade_col1, trade_col2 = st.columns(2)

            with trade_col1:
                st.markdown("#### Buy")
                with st.form(f"buy_form_{symbol}"):
                    buy_quantity = st.number_input("Quantity", min_value=0.01, step=0.01, key=f"buy_qty_{symbol}")
                    buy_cost = buy_quantity * stock_data['current_price']
                    st.write(f"Total cost: ${buy_cost:.2f}")

                    if st.form_submit_button("Buy"):
                        buy_response = make_authenticated_request(
                            "/portfolio/buy",
                            method="POST",
                            data={"ticker": symbol, "quantity": buy_quantity}
                        )

                        if buy_response and buy_response.status_code == 200:
                            st.success(f"Successfully bought {buy_quantity} shares of {symbol}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            error_msg = buy_response.json().get('detail',
                                                                'Unknown error') if buy_response else 'Request failed'
                            st.error(f"Buy failed: {error_msg}")

            with trade_col2:
                st.markdown("#### Sell")
                with st.form(f"sell_form_{symbol}"):
                    sell_quantity = st.number_input("Quantity", min_value=0.01, step=0.01, key=f"sell_qty_{symbol}")
                    sell_value = sell_quantity * stock_data['current_price']
                    st.write(f"Total value: ${sell_value:.2f}")

                    if st.form_submit_button("Sell"):
                        sell_response = make_authenticated_request(
                            "/portfolio/sell",
                            method="POST",
                            data={"ticker": symbol, "quantity": sell_quantity}
                        )

                        if sell_response and sell_response.status_code == 200:
                            st.success(f"Successfully sold {sell_quantity} shares of {symbol}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            error_msg = sell_response.json().get('detail',
                                                                 'Unknown error') if sell_response else 'Request failed'
                            st.error(f"Sell failed: {error_msg}")

            # Chart section (reusing your existing chart code)
            st.subheader("Price Chart & Analysis")

            # Get historical data
            hist_response = requests.get(f"{API_BASE}/api/stock/{symbol}/history?period=6mo")
            if hist_response.status_code == 200:
                df = pd.DataFrame(hist_response.json()["data"])
                df['date'] = pd.to_datetime(df['date'])

                # Price chart
                price_chart = alt.Chart(df).mark_line(
                    color='#667eea',
                    strokeWidth=2
                ).encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("close:Q", title="Price ($)", scale=alt.Scale(zero=False)),
                    tooltip=["date:T", "close:Q", "volume:Q"]
                ).properties(
                    height=400,
                    title=f"{symbol} Price History"
                )

                st.altair_chart(price_chart, use_container_width=True)

                # Prediction section
                pred_response = requests.get(f"{API_BASE}/api/stock/{symbol}/predict?windowSize=5")
                if pred_response.status_code == 200:
                    pred_data = pred_response.json()
                    predicted_price = pred_data['predicted_close_price']
                    current_price = stock_data['current_price']

                    st.subheader("AI Prediction")
                    prediction_change = ((predicted_price - current_price) / current_price) * 100
                    direction = "📈" if prediction_change > 0 else "📉"

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            "Predicted Next Close",
                            f"${predicted_price:.2f}",
                            delta=f"{prediction_change:+.2f}%"
                        )
                    with col2:
                        st.write(f"{direction} Direction: {'Up' if prediction_change > 0 else 'Down'}")

        else:
            st.error(f"Stock {symbol} not found")

    except Exception as e:
        st.error(f"Error loading stock data: {e}")


# Transaction History Page
def transactions_page():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📋 Transaction History")
    with col2:
        if st.button("🏠 Back to Dashboard"):
            st.session_state.current_page = 'dashboard'
            st.rerun()

    # Get transactions
    response = make_authenticated_request("/portfolio/transactions")

    if response and response.status_code == 200:
        transactions = response.json().get('transactions', [])

        if transactions:
            # Convert to DataFrame for better display
            df = pd.DataFrame(transactions)
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')

            # Display as interactive table
            st.dataframe(
                df[['timestamp', 'symbol', 'trade_type', 'quantity', 'price', 'amount']],
                use_container_width=True,
                column_config={
                    "timestamp": "Date & Time",
                    "symbol": "Stock",
                    "trade_type": "Type",
                    "quantity": "Quantity",
                    "price": st.column_config.NumberColumn("Price", format="$%.2f"),
                    "amount": st.column_config.NumberColumn("Total", format="$%.2f")
                }
            )

            # Summary stats
            st.subheader("Summary")
            col1, col2, col3 = st.columns(3)

            with col1:
                total_trades = len(transactions)
                st.metric("Total Trades", total_trades)

            with col2:
                buy_count = len([t for t in transactions if t['trade_type'] == 'BUY'])
                st.metric("Buys", buy_count)

            with col3:
                sell_count = len([t for t in transactions if t['trade_type'] == 'SELL'])
                st.metric("Sells", sell_count)
        else:
            st.info("No transactions yet. Start trading to see your history!")
    else:
        st.error("Could not load transaction history")


# Main app navigation
def main():
    if not st.session_state.authenticated:
        login_page()
    else:
        # Sidebar navigation for authenticated users
        with st.sidebar:
            st.write(f"**Logged in as:** {st.session_state.user_email}")

            if st.button("🏠 Dashboard"):
                st.session_state.current_page = 'dashboard'
                st.rerun()

            if st.button("📋 Transactions"):
                st.session_state.current_page = 'transactions'
                st.rerun()

            st.markdown("---")
            if st.button("🚪 Logout"):
                logout()

        # Route to appropriate page
        if st.session_state.current_page == 'dashboard':
            dashboard_page()
        elif st.session_state.current_page == 'stock_detail':
            stock_detail_page()
        elif st.session_state.current_page == 'transactions':
            transactions_page()


if __name__ == "__main__":
    main()