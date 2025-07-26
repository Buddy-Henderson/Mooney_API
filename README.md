# Mooney_API
API for conducting analysis for Crypto tokens

--Use to pull data if running locally--

curl -X POST -H "Content-Type: application/json" -d "{\"ticker\":\"XBT\"}" http://localhost:5000/analyze

supported Coins/Tokens
COINGECKO_IDS = {
    'BTC': 'bitcoin',
    'XBT': 'xbt',
    'ETH': 'ethereum',
    'ADA': 'cardano',
    'SOL': 'solana',
    'DOGE': 'dogecoin',
    'PENGU': 'pudgy-penguins',
    'DOT': 'Polkadot',
    'XRP': 'XRP',
    'MANYU' 'manyu'
}
