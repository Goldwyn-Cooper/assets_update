import os
import ast
import requests
from dotenv import load_dotenv
import pandas as pd
import yfinance as yf

def get_data():
    base_id = os.getenv('AIRTABLE_BASE_ID')
    table_name = os.getenv('AIRTABLE_TABLE_ID')
    URL = f'https://api.airtable.com/v0/{base_id}/{table_name}'
    token = os.getenv('AIRTABLE_API_TOKEN')
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(URL, headers=headers)
    response.raise_for_status()
    records = response.json().get('records')
    ids = [record.get('id') for record in records]
    fields = [record.get('fields') for record in records]
    df = pd.DataFrame(fields)
    df['ID'] = ids
    df.set_index('ID', inplace=True)
    return df.dropna()

def put_data(ids, data):
    base_id = os.getenv('AIRTABLE_BASE_ID')
    table_name = os.getenv('AIRTABLE_TABLE_ID')
    URL = f'https://api.airtable.com/v0/{base_id}/{table_name}'
    token = os.getenv('AIRTABLE_API_TOKEN')
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    records = []
    for id in ids:
        record = {
            'id': id,
            'fields': data,
        }
        records.append(record)
    # print(records)
    response = requests.patch(URL, headers=headers, json={'records': records})
    response.raise_for_status()

def update_currency():
    URL = 'https://quotation-api-cdn.dunamu.com/v1/forex/recent?codes=FRX.KRWUSD'
    response = requests.get(URL)
    response.raise_for_status()
    data = response.json()
    currency = data[0].get('basePrice')
    return currency

def update_krx(symbol):
    URL = 'https://m.stock.naver.com/front-api/external/chart/domestic/info'
    sd = pd.Timestamp.utcnow() - pd.Timedelta('6D')
    ed = pd.Timestamp.utcnow() + pd.Timedelta('24h')
    params = {
        'symbol': symbol,
        'requestType': 1,
        'startTime': sd.strftime('%Y%m%d'),
        'endTime': ed.strftime('%Y%m%d'),
        'timeframe': 'day',
    }
    response = requests.get(URL, params=params)
    response.raise_for_status()
    data = ast.literal_eval(response.text.replace('\n', ''))
    df = pd.DataFrame(data[1:], columns=data[0])
    return df.loc[:, '종가'].iloc[-1]

def update_fund(symbol):
    URL = f'https://www.samsungfund.com/api/v1/fund/product/{symbol}.do'
    response = requests.get(URL)
    response.raise_for_status()
    data = response.json()
    return data.get('suik').get('calculateResult').get('resultPer')[0].get('currentPrice')

def update_coin(symbol):
    URL = f'https://api.upbit.com/v1/ticker'
    params = {'markets': f'KRW-{symbol}'}
    response = requests.get(URL, params=params)
    response.raise_for_status()
    data = response.json()
    return data[0].get('trade_price')

def update_us(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period='1d')
    return data['Close'].iloc[-1]

if __name__ == '__main__':
    load_dotenv()
    print('🪴 Load Data')
    data = get_data()
    print('🪴 Update Currency')
    currency = update_currency()
    # put_data(data.query('Currency != 1').index, {'Currency': currency})
    for id, rows in data.iterrows():
        if rows['Currency'] != 1:
            put_data([id], {'Currency': currency})
    print('🪴 Update KRX')
    krx = data.query('Category == "한국증권"')
    for id, rows in krx.iterrows():
        price = update_krx(rows['Symbol'])
        put_data([id], {'Price': int(price)})
    print('🪴 Update Fund')
    fund = data.query('Category == "한국펀드"')
    put_data(fund.index, {'Price': update_fund('K55105BU1120')})
    print('🪴 Update Coin')
    coin = data.query('Category == "가상자산"')
    for id, rows in coin.iterrows():
        price = update_coin(rows['Symbol'])
        put_data([id], {'Price': int(price)})
    print('🪴 Update US')
    us = data.query('Category == "미국증권"')
    for id, rows in us.iterrows():
        price = update_us(rows['Symbol'])
        put_data([id], {'Price': int(price)})
    print('🪴 Done')
