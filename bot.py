import requests
import json
import sqlite3
from sqlite3 import Error
import sys
from minterapi import minter
import telegram
import time
import math
#from dotenv import load_dotenv
#import os
#import threading

#load_dotenv()

#PATH_TO_CONFIG_JSON = os.environ['PATH_TO_CONFIG_JSON']

PATH_TO_DB = 'krooxtips.db'
MINT_COST = 0.690777
MINT_COST_WEI = int(MINT_COST * 10**18)
MY_WALLET = ''
NFT_CA = ''
BUYS_ENABLED = True
TG_TOKEN_ID = ''

def notify_arena(username, num_mints, nft_id, link):
    message = 'Thanks @%s for minting a Comfy Kroox! You got # %s<br/>%s' % (username, nft_id, link)
    message = message.replace('Thanks @None for ', 'Thanks Undetected Username for ')
    headers = {}
    headers['Content-Type'] = 'application/json'
    headers['Authorization'] = ''

    payload = {}
    payload['content'] = message
    payload['files'] = []
    imageUrl = 'https://nochill.lol/ck_nft/%s.png' % nft_id
    file = {"url":imageUrl,"isLoading":False, "fileType": "image"}
    payload['files'].append(file)
    payload['privacyType'] = 0
    r = requests.post('https://api.starsarena.com/threads', headers=headers, data=json.dumps(payload))

def notify_dev(message):
    TOKEN=TG_TOKEN_ID
    CHAT_ID=''
    if message != '':
        text = '%s' % (message)
        bot = telegram.Bot(token=TOKEN)
        bot.sendMessage(chat_id=CHAT_ID, text=text)

def notify_tg_group(message):
    TOKEN=TG_TOKEN_ID
    CHAT_ID=''
    if message != '':
        text = '%s' % (message)
        bot = telegram.Bot(token=TOKEN)
        bot.sendMessage(chat_id=CHAT_ID, text=text)

def read_users_json():
    with open('../nochillexchange/users.json', 'r') as openfile:
        # Reading from json file
        json_object = json.load(openfile)

    return json_object

def get_username(conn, address):
    address = address.lower()
    username = get_username_from_db(conn, address)
    if username != None:
        return username
    else:
        username = address
        print(username)
        url = 'https://api.arenabook.xyz/user_info?user_address=eq.%s' % address
        r = requests.get(url)
        if r.status_code == 200:
            if len(r.json()) == 1:
                username = r.json()[0]['twitter_handle']
        print(username)
        if username != None:
            add_username_to_db(conn, address, username)
        else:
            try:
                users = read_users_json()
                if address.lower() in users:
                    username = users[address.lower()]
                else:
                    username = None
            except:
                pass
        return username

def get_username_from_db(conn, address):
    cur = conn.cursor()
    cur.execute("SELECT * FROM wallets WHERE wallet=?", (address,))

    rows = cur.fetchall()

    if len(rows) != 0:
        for row in rows:
            return row[2]
    else:
        return None

def add_username_to_db(conn, address, username):
    cur = conn.cursor()
    cur.execute("INSERT INTO wallets (wallet, username) VALUES(\"%s\",\"%s\");" % (address, username))
    conn.commit()
    return cur.lastrowid

def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
    except Error as e:
        print(e)

    return conn

def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

def check_transaction(conn, txnId):
    cur = conn.cursor()
    cur.execute("SELECT * FROM txn WHERE txnId=\"%s\";" % txnId)
    rows = cur.fetchall()
    if len(rows) > 0:
        return True
    else:
        return False

def add_transaction(conn, txnId, username):
    cur = conn.cursor()
    cur.execute("INSERT INTO txn (txnId, amountIn, tradeTxn, amountOut, transferTxn, username) VALUES(\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\");" % (txnId, 'x', 'x', 'x','x', username))
    conn.commit()
    return cur.lastrowid

def update_transaction_with_buy_data(conn, originTxn, amount, buy_txn):
    task = (amount, buy_txn, originTxn)
    sql = ''' UPDATE txn
              SET amountIn = ? ,
                  tradeTxn = ?
              WHERE txnId = ?'''
    cur = conn.cursor()
    cur.execute(sql, task)
    conn.commit()

def make_snowtrace_link(txn):
    url = 'https://snowtrace.io/tx/%s?chainId=43114' % txn
    return url

def update_transaction_with_transfer_data(conn, originTxn, transferTxn, amount):
    task = (amount, transferTxn, originTxn)
    sql = ''' UPDATE txn
              SET amountOut = ? ,
                  transferTxn = ?
              WHERE txnId = ?'''
    cur = conn.cursor()
    cur.execute(sql, task)
    conn.commit()

def update_transaction_with_user_data(conn, originTxn, username):
    task = (username, originTxn)
    sql = ''' UPDATE txn
              SET username = ?
              WHERE txnId = ?'''
    cur = conn.cursor()
    cur.execute(sql, task)
    conn.commit()

def remove_transaction(conn, txnId):
    sql = 'DELETE FROM txn WHERE txnId=?'
    cur = conn.cursor()
    cur.execute(sql, (txnId,))
    conn.commit()

def get_transfers(address):
    url = 'https://api.routescan.io/v2/network/mainnet/evm/43114/etherscan/api?module=account&action=txlist&address=%s&startblock=0&endblock=99999999&page=1&offset=100&sort=desc&apikey=YourApiKeyToken' % address
    r = requests.get(url)
    print(r.status_code)
    transactions = []
    if r.status_code == 200:
        if r.json()['message'] == 'OK':
            for txn in r.json()['result']:
                # {'blockNumber': '39895801', 'timeStamp': '1704313821', 'hash': '0x23c2de1d272c168c4711a01ce65a229405b227ab4aca064d7d977cf6ec97ea03', 'nonce': '0', 'blockHash': '0x18280b7f315dc0c50d43ed110e4777bd08e6d84b92f875c3e20c87fcdb9d0c39', 'transactionIndex': '9', 'from': '0x9133dd7d4d62b190e4fa03398022dc2fb37ccfec', 'to': '0x167f0c5d8ef61a10b1f5829bd4c21126799737d0', 'value': '58717750000000000', 'gas': '21000', 'gasPrice': '25000000000', 'isError': '0', 'txreceipt_status': '1', 'input': '0x', 'contractAddress': '', 'cumulativeGasUsed': '674251', 'gasUsed': '21000', 'confirmations': '988386', 'methodId': '0x', 'functionName': ''}
                if txn['methodId'] == '0x' and txn['input'] == '0x' and txn['to'].lower() == MY_WALLET.lower():
                    if int(txn['value']) >= MINT_COST_WEI:
                        transactions.append(txn)
                    #print(txn)

    return transactions

def make_link(nft_id):
    url = 'https://avax.hyperspace.xyz/collection/avax/comfykroox?tokenAddress=%s_%s' % (NFT_CA.lower(), nft_id)
    #url = 'https://joepegs.com/item/avalanche/%s/%s' % (NFT_CA, nft_id)
    return url

#m = minter()
#m.refund_remainder('0xAb0fb9ea07CC64703e7954611CF37903bF2Cacdf', 0.001)

payables = get_transfers(MY_WALLET)
#print(payables)
retry_mints = []
if len(payables) != 0:
    conn = create_connection(PATH_TO_DB)
    m = minter()
    sql_create_txn_table = """ CREATE TABLE IF NOT EXISTS txn (
                                        id integer PRIMARY KEY,
                                        txnId text NOT NULL,
                                        amountIn text NOT NULL,
                                        tradeTxn text NOT NULL,
                                        amountOut text NOT NULL,
                                        transferTxn text NOT NULL,
                                        username text NOT NULL
                                    ); """

    sql_create_wallet_table = """ CREATE TABLE IF NOT EXISTS wallets (
                                        id integer PRIMARY KEY,
                                        wallet text NOT NULL,
                                        username text NOT NULL
                                    ); """

    sql_timestamp_table = """ CREATE TABLE IF NOT EXISTS timestamps (
                                        id integer PRIMARY KEY,
                                        txnId text NOT NULL,
                                        ts text NOT NULL
                                    ); """
    # create tables
    if conn is not None:
        # create tweets table
        create_table(conn, sql_create_txn_table)
        create_table(conn, sql_create_wallet_table)
        create_table(conn, sql_timestamp_table)
    else:
        print("Error! cannot create the database connection.")
        #notifySlack('Error! Cannot create the database connection!')
        #notifyDiscord('Error! Cannot create the database connection!')
        sys.exit(1)

    print('payables count: ',len(payables))
    for payable in payables:
        print('***************************************')
        if not check_transaction(conn, payable['hash']):
            # p is already in 10**18 format
            payable_value_readable = int(payable['value'])/10**18
            p = int(payable['value'])
            p = int(p)
            minted = []
            # get the username
            username = get_username(conn, payable['from'])
            notify_dev('[kroox] 1/2 got a transaction from %s - %s avax - hash: %s' % (username, int(payable['value'])/10**18, make_snowtrace_link(payable['hash'])))
            add_transaction(conn, payable['hash'], username)
            if BUYS_ENABLED == True:
                nft_id = -1
                num_mints = math.floor(int(payable['value']) / MINT_COST_WEI)
                remainder = int(payable['value']) - (num_mints * MINT_COST_WEI)
                print(int(payable['value'])/10**18, num_mints, remainder)
                print(remainder/10**18)
                for i in range(0, num_mints):
                    try:
                        nft_id = m.mint(payable['from'])
                        #nft_id = i
                    except:
                        print('ay mint failed bro')
                        notify_dev('[kroox] 1 mint failed for %s! added to retry list.' % (username))
                        fm = {}
                        fm['from'] = payable['from']
                        fm['hash'] = payable['hash']
                        fm['payable_readable'] = payable_value_readable
                        fm['minted'] = minted
                        retry_mints.append(fm)

                    if nft_id != -1:
                        link = make_link(nft_id)
                        print('ey you minted a nft # ', nft_id)
                        minted.append(str(nft_id))
                        print(link)
                        print('minted successfully! %s of %s' % (i+1, num_mints))
                        notify_dev('[kroox] 2/2 minted # %s - total expected %s - link: %s' % (nft_id, num_mints, link))
                        update_transaction_with_buy_data(conn, payable['hash'], payable_value_readable, ','.join(minted))
                        notify_arena(username, num_mints, nft_id, link)
                        #notify_tg_group('%s tipped %s to comfykroox' % (username, payable_value_readable))
                    else:
                        print('ay mint failed bro')
                        notify_dev('[kroox] 1 mint failed for %s!' % (username))
                        remainder += MINT_COST_WEI

                    time.sleep(5)
                if remainder > 0.01*10**18:
                    print('refunding %s' % (remainder/10**18))
                    #notify_dev('Surplus received: %s AVAX' % (remainder))

        else:
            print('skipped for %s - %s' % (get_username(conn, payable['from']), payable['hash']))
            #update_transaction_with_user_data(conn, payable['hash'], get_username(payable['from']))

time.sleep(10)
if len(retry_mints) != 0:
    for failed_mint in retry_mints:
        nft_id = -1
        username = get_username(conn, failed_mint['from'])
        minted = failed_mint['minted']
        num_mints = 1
        try:
            nft_id = m.mint(failed_mint['from'])
            #nft_id = i
        except:
            print('ay mint failed bro')
            notify_dev('[kroox][retry] 1 mint failed for %s! ' % (username))

        if nft_id != -1:
            link = make_link(nft_id)
            print('ey you minted a nft # ', nft_id)
            minted.append(str(nft_id))
            print(link)
            #print('minted successfully! %s of %s' % (i+1, num_mints))
            notify_dev('[kroox][retry] 2/2 minted # %s - link: %s' % (nft_id, link))
            update_transaction_with_buy_data(conn, failed_mint['hash'], failed_mint['payable_readable'], ','.join(minted))
            notify_arena(username, num_mints, nft_id, link)
            #notify_tg_group('%s tipped %s to comfykroox' % (username, payable_value_readable))
        else:
            print('ay mint failed bro')
            notify_dev('[kroox][retry] 1 mint failed for %s!' % (username))
