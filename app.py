from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import requests
import os

app = Flask(__name__)
CSV_FILE = 'TRADING_JOURNELS_v4.csv'
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwI289q3hpAnXO5GRPeNOfZbMycgZmFmMdluHUo0vWBNXHjE8L-EO6UYgbtdyoLF3yA/exec"
STARTING_BALANCE = 5021.00

def get_trade_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df['Profit/Loss'] = pd.to_numeric(df['Profit/Loss'], errors='coerce').fillna(0)
        df['Balance'] = STARTING_BALANCE + df['Profit/Loss'].cumsum()
        return df
    return pd.DataFrame()

@app.route('/')
def index():
    df = get_trade_data()
    trades = df.to_dict('records') if not df.empty else []
    return render_template('index.html', trades=trades[::-1])

@app.route('/dashboard')
def dashboard():
    df = get_trade_data()
    if not df.empty:
        current_balance = df['Balance'].iloc[-1]
        
        # Setup Success Data (Now tracking 'Entry On')
        df['Result'] = df['Profit/Loss'].apply(lambda x: 'Win' if x > 0 else 'Loss')
        setup_stats = df.groupby(['Entry On', 'Result']).size().unstack(fill_value=0).reset_index()
        
        setup_labels = setup_stats['Entry On'].tolist() if 'Entry On' in setup_stats else []
        setup_wins = setup_stats['Win'].tolist() if 'Win' in setup_stats else []
        setup_losses = setup_stats['Loss'].tolist() if 'Loss' in setup_stats else []
        
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        chart_dates = df['Date'].tolist()
        chart_balances = df['Balance'].tolist()
    else:
        current_balance = STARTING_BALANCE
        setup_labels, setup_wins, setup_losses, chart_dates, chart_balances = [], [], [], [], []

    return render_template('dashboard.html', 
                           current_balance=current_balance,
                           setup_labels=setup_labels, setup_wins=setup_wins, setup_losses=setup_losses,
                           chart_dates=chart_dates, chart_balances=chart_balances)

@app.route('/add', methods=['POST'])
def add_trade():
    new_trade = {
        'date': request.form['date'],
        'entry_on': request.form['entry_on'],
        'fvg_target': request.form['fvg_target'],
        'pair': request.form['pair'],
        'rr': request.form['rr'],
        'trend_1h': request.form['trend_1h'],
        'trend_3m': request.form['trend_3m'],
        'direction': request.form['direction'],
        'entry': request.form.get('entry', ''),
        'target': request.form.get('target', ''),
        'exit': request.form.get('exit', ''),
        'pnl': request.form.get('pnl', 0),
        'notes': request.form.get('notes', '')
    }
    
    # 1. Sync to Google Sheets
    try:
        requests.post(APPS_SCRIPT_URL, json=new_trade)
    except Exception as e:
        print(f"Failed to sync: {e}")
    
    # 2. Save locally
    csv_trade = {
        'Date': new_trade['date'], 
        'Entry On': new_trade['entry_on'], 
        'Targeted FVG': new_trade['fvg_target'],
        'Pair': new_trade['pair'], 
        'RR': new_trade['rr'], 
        '1H Trend': new_trade['trend_1h'], 
        '3M Trend': new_trade['trend_3m'], 
        'Direction': new_trade['direction'],
        'Entry Price': new_trade['entry'], 
        'Target Price': new_trade['target'], 
        'Exit Price': new_trade['exit'], 
        'Profit/Loss': new_trade['pnl'],
        'Notes': new_trade['notes']
    }
    
    df = pd.DataFrame([csv_trade])
    df.to_csv(CSV_FILE, mode='a', header=not os.path.exists(CSV_FILE), index=False)
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)