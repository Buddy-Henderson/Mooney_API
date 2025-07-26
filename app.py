from flask import Flask, request, jsonify
import ccxt
import requests
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands
from datetime import datetime
import logging
import numpy as np
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CoinGecko API base URL
COINGECKO_API = "https://api.coingecko.com/api/v3"

# Ticker to CoinGecko ID mapping
COINGECKO_IDS = {
    'BTC': 'bitcoin',
    'XBT': 'bitcoin',
    'ETH': 'ethereum',
    'ADA': 'cardano',
    'SOL': 'solana',
    'DOGE': 'dogecoin',
    'PENGU': 'pudgy-penguins',
    'DOT': 'Polkadot',
    'XRP': 'XRP',
    'MANYU' 'manyu'
}

# Add root route for browser testing
@app.route('/')
def home():
    return 'Crypto Analysis API is running! Use POST /analyze with {"ticker": "BTC"}'

def calculate_score(rsi, price_change, volatility, macd_diff, bb_position, vol_to_mcap, market_cap, circ_supply_percent):
    score = 0
    
    # RSI (20%)
    if rsi < 30:
        score += 20
    elif rsi > 70:
        score += 0
    else:
        score += (100 - rsi) / 100 * 20
    
    # Price Change (20%)
    if price_change > 5:
        score += 20
    elif price_change < -5:
        score += 0
    else:
        score += (price_change + 5) / 10 * 20
    
    # Volatility (10%, lower is better)
    vol_max = 0.1  # Assume 10% daily volatility as max
    vol_score = max(0, (vol_max - volatility) / vol_max * 10)
    score += vol_score
    
    # MACD (15%)
    if macd_diff > 0:
        score += 15
    
    # Bollinger Bands (10%)
    if bb_position < 0:
        score += 10
    elif bb_position > 1:
        score += 0
    else:
        score += (1 - bb_position) * 10
    
    # Volume-to-Market-Cap Ratio (15%)
    if vol_to_mcap > 0.05:
        score += 15
    elif vol_to_mcap < 0.01:
        score += 0
    else:
        score += (vol_to_mcap - 0.01) / 0.04 * 15
    
    # Market Cap (10%, higher is better)
    mcap_max = 1e12  # 1 trillion USD
    score += min(market_cap / mcap_max, 1) * 10
    
    # Circulating Supply (10%)
    if circ_supply_percent > 80:
        score += 10
    elif circ_supply_percent < 20:
        score += 0
    else:
        score += (circ_supply_percent - 20) / 60 * 10
    
    return round(score, 2)

def get_recommendation(score):
    if score > 60:
        return "buy"
    elif score < 40:
        return "sell"
    else:
        return "hold"

@app.route('/analyze', methods=['POST'])
def analyze_crypto():
    try:
        # Get JSON payload
        data = request.get_json()
        ticker = data.get('ticker')
        if not ticker:
            logger.error("No ticker provided in request")
            return jsonify({'error': 'Ticker is required'}), 400

        logger.info(f"Processing analysis for ticker: {ticker}")

        # Map ticker to CoinGecko ID
        coingecko_id = COINGECKO_IDS.get(ticker.upper(), ticker.lower())
        
        # Initialize exchange (Kraken)
        exchange = ccxt.kraken()
        symbol = f"{ticker}/USD"  # Kraken uses USD
        
        # Fetch 30 days of daily OHLCV data with retries
        retries = 3
        for attempt in range(retries):
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=30)
                break
            except ccxt.NetworkError as e:
                if attempt < retries - 1:
                    logger.warning(f"Network error, retrying... ({attempt + 1}/{retries}): {str(e)}")
                    time.sleep(2)
                    continue
                raise e
        if not ohlcv:
            logger.error(f"No price data found for {symbol}")
            return jsonify({'error': f"No price data for {symbol}"}), 404

        # Extract closing prices
        closing_prices = [candle[4] for candle in ohlcv]
        prices_df = pd.DataFrame(closing_prices, columns=['close'])

        # Price-based metrics
        latest_price = closing_prices[-1]
        avg_price = sum(closing_prices) / len(closing_prices)
        price_change = ((latest_price - closing_prices[0]) / closing_prices[0]) * 100
        returns = prices_df['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(365) * 100  # Annualized volatility

        # Technical indicators
        rsi = RSIIndicator(prices_df['close'], window=14).rsi().iloc[-1]
        sma_30 = prices_df['close'].rolling(window=30).mean().iloc[-1]
        macd = MACD(prices_df['close']).macd_diff().iloc[-1]
        bb = BollingerBands(prices_df['close'], window=20)
        bb_upper = bb.bollinger_hband().iloc[-1]
        bb_lower = bb.bollinger_lband().iloc[-1]
        bb_position = (latest_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0

        # Fetch CoinGecko data with retries
        coingecko_data = None
        for attempt in range(retries):
            try:
                coingecko_response = requests.get(f"{COINGECKO_API}/coins/markets", 
                                               params={'vs_currency': 'usd', 'ids': coingecko_id})
                coingecko_response.raise_for_status()  # Raise exception for HTTP errors
                coingecko_data = coingecko_response.json()
                logger.info(f"CoinGecko response for {ticker}: {coingecko_data}")
                break
            except requests.RequestException as e:
                if attempt < retries - 1:
                    logger.warning(f"CoinGecko request failed, retrying... ({attempt + 1}/{retries}): {str(e)}")
                    time.sleep(2)
                    continue
                logger.error(f"CoinGecko request failed after {retries} attempts: {str(e)}")
                return jsonify({'error': f"CoinGecko request failed: {str(e)}"}), 503

        if not coingecko_data:
            logger.error(f"No CoinGecko data for {ticker} (ID: {coingecko_id})")
            return jsonify({'error': f"No market data for {ticker}"}), 404

        market_cap = coingecko_data[0].get('market_cap', 0)
        volume_24h = coingecko_data[0].get('total_volume', 0)
        vol_to_mcap = volume_24h / market_cap if market_cap > 0 else 0
        circ_supply = coingecko_data[0].get('circulating_supply', 0)
        total_supply = coingecko_data[0].get('total_supply', 1)
        circ_supply_percent = (circ_supply / total_supply * 100) if total_supply > 0 else 0

        # Calculate score and recommendation
        score = calculate_score(rsi, price_change, volatility, macd, bb_position, vol_to_mcap, market_cap, circ_supply_percent)
        recommendation = get_recommendation(score)

        # Prepare response
        result = {
            'ticker': ticker,
            'latest_price': round(latest_price, 2),
            '30d_avg_price': round(avg_price, 2),
            '30d_price_change_percent': round(price_change, 2),
            'volatility_percent': round(volatility, 2),
            'rsi': round(rsi, 2),
            'sma_30': round(sma_30, 2),
            'macd_diff': round(macd, 2),
            'bollinger_position': round(bb_position, 2),
            'market_cap_usd': market_cap,
            'volume_24h_usd': volume_24h,
            'volume_to_market_cap': round(vol_to_mcap, 4),
            'circulating_supply_percent': round(circ_supply_percent, 2),
            'score': score,
            'recommendation': recommendation,
            'timestamp': datetime.utcnow().isoformat()
        }

        logger.info(f"Analysis completed for {ticker}: {result}")
        return jsonify(result), 200

    except ccxt.NetworkError as e:
        logger.error(f"Exchange network error: {str(e)}")
        return jsonify({'error': 'Exchange network error'}), 503
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {str(e)}")
        return jsonify({'error': f"Exchange error: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
