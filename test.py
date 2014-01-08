import os
import sys
import json
import websocket
from rippletools import Transaction, PaymentTransaction, TransactionSubscriptionMessage


def main():
    # Provide transaction via stdin
    if not sys.stdin.isatty():
        analyze_transaction(sys.stdin.read())
        return

    # Or file
    if len(sys.argv) > 1:
        analyze_transaction(open(sys.argv[1]).read())
        return

    # Or follow the server stream
    ws = websocket.create_connection(
        os.environ.get('RIPPLE_URI', 'wss://s1.ripple.com'), timeout=20)
    ws.send('{"command":"subscribe","streams":["transactions"]}')
    print(ws.recv())

    while True:
        message = ws.recv()
        try:
            analyze_transaction(message)
            print()
        except:
            print(json.dumps(message, indent=2))
            raise


def analyze_transaction(txstr):
    txdata = json.loads(txstr)
    tx = TransactionSubscriptionMessage(txdata).transaction

    data = [tx.type.__name__]
    if not tx.successful:
        data.append('unsuccessful')
    else:
        if tx.type == PaymentTransaction:
            data.append(tx.hash)
            data.append('{0} {1}/{2}'.format(*tx.amount_received))
            data.append('to: %s' % tx.Destination)
            data.append('new balance: %s' % tx.recipient_balance)
            data.append('of limit: %s' % tx.recipient_trust_limit)
            data.append('path: intermediaries={intermediaries}, offers={offers}'.format(
                **tx.analyze_path()
            ))
        else:
            data.append('TODO: parse')

    # Print the collected info
    print(data[0])
    for line in data[1:]:
        print('    %s' % line)


main()
