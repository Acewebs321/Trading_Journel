from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import requests
import os
import uuid

app = Flask(__name__)
CSV_FILE = 'TRADING_JOURNELS_v4.csv'
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwI289q3hpAnXO5GRPeNOfZbMycgZmFmMdluHUo0vWBNXHjE8L-EO6UYgbtdyoLF3yA/exec"
STARTING_BALANCE = 5021.00

def get_trade_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        
        # Retroactively add unique IDs to old trades if missing
        if 'ID' not in df.columns:
            df.insert(0, 'ID', [str(uuid.uuid4()) for _ in range(len(df))])
            df.to_csv(CSV_FILE, index=False)

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
    trade_id = str(uuid.uuid4())
    new_trade = {
        'id': trade_id,
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
    
    try:
        requests.post(APPS_SCRIPT_URL, json=new_trade)
    except Exception as e:
        print(f"Failed to sync: {e}")
    
    csv_trade = {
        'ID': trade_id,
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

@app.route('/edit/<trade_id>', methods=['GET', 'POST'])
def edit_trade(trade_id):
    df = get_trade_data()
    if df.empty:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        idx = df.index[df['ID'] == trade_id].tolist()
        if idx:
            i = idx[0]
            df.at[i, 'Date'] = request.form['date']
            df.at[i, 'Entry On'] = request.form['entry_on']
            df.at[i, 'Targeted FVG'] = request.form['fvg_target']
            df.at[i, 'Pair'] = request.form['pair']
            df.at[i, 'RR'] = request.form['rr']
            df.at[i, '1H Trend'] = request.form['trend_1h']
            df.at[i, '3M Trend'] = request.form['trend_3m']
            df.at[i, 'Direction'] = request.form['direction']
            df.at[i, 'Entry Price'] = request.form.get('entry', '')
            df.at[i, 'Target Price'] = request.form.get('target', '')
            df.at[i, 'Exit Price'] = request.form.get('exit', '')
            df.at[i, 'Profit/Loss'] = request.form.get('pnl', 0)
            df.at[i, 'Notes'] = request.form.get('notes', '')
            
            # Drop the calculated 'Balance' column before saving so it recalculates cleanly next time
            if 'Balance' in df.columns:
                df = df.drop(columns=['Balance'])
            
            df.to_csv(CSV_FILE, index=False)
        return redirect(url_for('index'))

    # Render the edit page if it's a GET request
    trade = df[df['ID'] == trade_id].to_dict('records')
    if not trade:
        return redirect(url_for('index'))
        
    return render_template('edit.html', trade=trade[0])

if __name__ == '__main__':
    app.run(debug=True)