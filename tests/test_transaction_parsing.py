import json
from os import path
from rippletools import Transaction


def open_transaction(name):
    filename = path.join(path.dirname(__file__), 'transactions', name)
    with open(filename) as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            if line.startswith('---'):
                break
        json_text = ''.join(lines[idx+1:])
        return json.loads(json_text)


def test_payment_with_third_party_iou():
    txstr = open_transaction('payment_with_third_party_iou.json')
    tx = Transaction(txstr)

    # Correctly find the currency the recipient receives
    assert tx.currency_received() == ('USD', 'rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B')

    # Currently determine the new balance
    assert tx.recipient_balance() == 28


def test_payment_with_intermediary_lender():
    txstr = open_transaction('payment_with_intermediary_lender.json')
    tx = Transaction(txstr)

    # Correctly find the currency the recipient receives
    assert tx.currency_received() == ('USD', 'rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B')

    # Currently determine the new balance
    assert tx.recipient_balance() == 26
