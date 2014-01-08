from decimal import Decimal
import json
from os import path
from rippletools import Transaction, TransactionSubscriptionMessage


def open_transaction(name):
    filename = path.join(path.dirname(__file__), 'transactions', name)
    with open(filename) as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            if line.startswith('---'):
                break
        json_text = ''.join(lines[idx+1:])
        return json.loads(json_text)


def test_payment_xrp():
    txstr = open_transaction('payment_xrp.json')
    tx = Transaction(txstr)

    # We identify the correct recipient data
    assert tx.currency_received == ('XRP', None)
    assert tx.recipient_balance == 16230610429
    assert tx.recipient_trust_limit == None

    assert tx.analyze_path() == {'offers': 0, 'intermediaries': 0}


def test_payment_to_trusting_party():
    txstr = open_transaction('payment_to_trusting_party.json')
    tx = Transaction(txstr)

    # We identify the correct recipient data
    assert tx.currency_received == ('USD', 'rhq549rEtUrJowuxQC2WsHNGLjAjBQdAe8')
    assert tx.recipient_balance == Decimal('11.38715136504026')
    assert tx.recipient_trust_limit == Decimal('40')

    assert tx.analyze_path() == {'offers': 0, 'intermediaries': 0}


def test_payment_with_third_party_iou():
    txstr = open_transaction('payment_with_third_party_iou.json')
    tx = Transaction(txstr)

    # We identify the correct recipient data
    assert tx.currency_received == ('USD', 'rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B')
    assert tx.recipient_balance == 28
    assert tx.recipient_trust_limit == 500

    assert tx.analyze_path() == {'offers': 0, 'intermediaries': 1}


def test_payment_with_intermediary_lender():
    txstr = open_transaction('payment_with_intermediary_lender.json')
    tx = Transaction(txstr)

    # We identify the correct recipient data
    assert tx.currency_received == ('USD', 'rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B')
    assert tx.recipient_balance == 26
    assert tx.recipient_trust_limit == 500

    assert tx.analyze_path() == {'offers': 0, 'intermediaries': 2}


def test_payment_with_intermediary_traders():
    msg = open_transaction('payment_with_intermediary_traders.json')
    tx = TransactionSubscriptionMessage(msg).transaction

    # We identify the correct recipient data
    assert tx.currency_received == ('USD', 'rMwjYedjc7qqtKYVLiAccJSmCwih4LnE2q')
    assert tx.recipient_balance == Decimal('369.1796199999879')
    assert tx.recipient_trust_limit == 4000

    assert tx.analyze_path() == {'offers': 2, 'intermediaries': 0}


def test_payment_payment_usd_to_xrp_lending_from_payee():
    txstr = open_transaction('payment_usd_to_xrp_lending_from_payee.json')
    tx = Transaction(txstr)

    # We identify the correct recipient data
    assert tx.currency_received == ('XRP', None)
    assert tx.recipient_balance == 16229610429
    assert tx.recipient_trust_limit == None

    # TODO: This test currently fails because we aren't smart enough to
    # recognize that the guy that *gets payed* is lending the payer
    # something to facilitate the transaction. We filter that change
    # out, thinking it is not an intermediary.
    # A related question is whether we should classify further: we currently
    # count the IOU being traded as an intermediary, an account rippling
    # between two foreign IOUs, as well as an account rippling by issuing
    # their own to a trusting party in exchange for whatever the payment needs.
    assert tx.analyze_path() == {'offers': 1, 'intermediaries': 1}
