from __future__ import unicode_literals
from decimal import Decimal
import json
from os import path
import pytest
from ripple import Transaction, TransactionSubscriptionMessage, SetRegularKeyTransaction

# TODO: I'd like to move the test assertions into the JSON file, and eval them.

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
    assert tx.currencies_received == ('XRP', None)
    assert tx.recipient_balances == [(None, (Decimal('16230.610429')))]
    assert tx.recipient_trust_limits == []
    assert tx.recipient_trust_limit == None

    assert tx.analyze_path() == {'offers': 0, 'intermediaries': 0}


def test_payment_delivered_amount_xrp():
    txstr = open_transaction('payment_delivered_amount_xrp.json')
    tx = Transaction(txstr)
    assert tx.amount_received == (Decimal('0.000955'), 'XRP', None)


def test_payment_to_trusting_party():
    txstr = open_transaction('payment_to_trusting_party.json')
    tx = Transaction(txstr)

    # We identify the correct recipient data
    assert tx.currencies_received == ('USD', ['rhq549rEtUrJowuxQC2WsHNGLjAjBQdAe8'])
    assert tx.recipient_balances == [
        ('rhq549rEtUrJowuxQC2WsHNGLjAjBQdAe8', Decimal('11.38715136504026'))]
    assert tx.recipient_trust_limits == [
        ('rhq549rEtUrJowuxQC2WsHNGLjAjBQdAe8', Decimal('40'))]

    assert tx.analyze_path() == {'offers': 0, 'intermediaries': 0}


def test_payment_with_third_party_iou():
    txstr = open_transaction('payment_with_third_party_iou.json')
    tx = Transaction(txstr)

    # We identify the correct recipient data
    assert tx.currencies_received == ('USD', ['rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B'])
    assert tx.recipient_balances == [
        ('rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B', Decimal('28'))]
    assert tx.recipient_trust_limits == [
        ('rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B', Decimal('500'))]

    assert tx.analyze_path() == {'offers': 0, 'intermediaries': 1}


def test_payment_with_intermediary_lender():
    txstr = open_transaction('payment_with_intermediary_lender.json')
    tx = Transaction(txstr)

    # We identify the correct recipient data
    assert tx.currencies_received == ('USD', ['rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B'])
    assert tx.recipient_balances == [
        ('rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B', Decimal('26'))]
    assert tx.recipient_trust_limits == [
        ('rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B', Decimal('500'))]

    assert tx.analyze_path() == {'offers': 0, 'intermediaries': 2}


def test_payment_with_intermediary_traders():
    msg = open_transaction('payment_with_intermediary_traders.json')
    tx = TransactionSubscriptionMessage(msg).transaction

    # We identify the correct recipient data
    assert tx.currencies_received == ('USD', ['rMwjYedjc7qqtKYVLiAccJSmCwih4LnE2q'])
    assert tx.recipient_balances == [
        ('rMwjYedjc7qqtKYVLiAccJSmCwih4LnE2q', Decimal('369.1796199999879'))]
    assert tx.recipient_trust_limits == [
        ('rMwjYedjc7qqtKYVLiAccJSmCwih4LnE2q', Decimal('4000'))]

    assert tx.analyze_path() == {'offers': 2, 'intermediaries': 2}


@pytest.mark.xfail()
def test_payment_usd_to_xrp_lending_from_payee():
    txstr = open_transaction('payment_usd_to_xrp_lending_from_payee.json')
    tx = Transaction(txstr)

    # We identify the correct recipient data
    assert tx.currencies_received == ('XRP', None)
    assert tx.recipient_balances == [(None, Decimal('16229.610429'))]
    assert tx.recipient_trust_limits == []

    # TODO: This test currently fails because we aren't smart enough to
    # recognize that the guy that *gets payed* is lending the payer
    # something to facilitate the transaction. We filter that change
    # out, thinking it is not an intermediary.
    # A related question is whether we should classify further: we currently
    # count the IOU being traded as an intermediary, an account rippling
    # between two foreign IOUs, as well as an account rippling by issuing
    # their own to a trusting party in exchange for whatever the payment needs.
    assert tx.analyze_path() == {'offers': 1, 'intermediaries': 2}


def test_payment_two_receiving_issuers():
    txstr = open_transaction('payment_two_receiving_issuers.json')
    tx = Transaction(txstr)

    # We identify the correct recipient data
    assert tx.currencies_received == (
        'CAD', ['rLju3NgFJn9jZuiyibyJM7asTVeVoueWWF',
                'rhKJE9kFPz6DuK4KyL2o8NkCCNPKnSQGRL'])
    assert tx.amounts_received == [
        (Decimal('14.43'), 'CAD', 'rLju3NgFJn9jZuiyibyJM7asTVeVoueWWF'),
        (Decimal('0.5700000000000'), 'CAD', 'rhKJE9kFPz6DuK4KyL2o8NkCCNPKnSQGRL')
    ]

    assert tx.recipient_balances == [
        ('rLju3NgFJn9jZuiyibyJM7asTVeVoueWWF', Decimal('1700')),
        ('rhKJE9kFPz6DuK4KyL2o8NkCCNPKnSQGRL', Decimal('527.5647752464243'))]
    assert tx.recipient_trust_limits == [
        ('rLju3NgFJn9jZuiyibyJM7asTVeVoueWWF', Decimal('1700')),
        ('rhKJE9kFPz6DuK4KyL2o8NkCCNPKnSQGRL', Decimal('900'))]

    assert tx.analyze_path() == {'offers': 0, 'intermediaries': 1}

    # The simplified single-accessor fail in this case
    with pytest.raises(ValueError):
        tx.recipient_balance
    with pytest.raises(ValueError):
        tx.recipient_previous_balance
    with pytest.raises(ValueError):
        tx.recipient_trust_limit


def test_payment_receiving_own_senders_thirdparty_ious():
    txstr = open_transaction('payment_receiving_own_senders_thirdparty_ious.json')
    tx = Transaction(txstr)

    # We identify the correct recipient data
    assert tx.currencies_received == (
        'CAD', ['rLju3NgFJn9jZuiyibyJM7asTVeVoueWWF',
                'rnziParaNb8nsU4aruQdwYE3j5jUcqjzFm',
                'rhKJE9kFPz6DuK4KyL2o8NkCCNPKnSQGRL'])
    assert tx.amounts_received == [
        (Decimal('5.088436765502'), 'CAD', 'rLju3NgFJn9jZuiyibyJM7asTVeVoueWWF'),
        (Decimal('10.15156323449716'), 'CAD', 'rnziParaNb8nsU4aruQdwYE3j5jUcqjzFm'),
        (Decimal('9.7600000000000'), 'CAD', 'rhKJE9kFPz6DuK4KyL2o8NkCCNPKnSQGRL')
    ]

    assert tx.sender_trust_limits == [
        ('r3ADD8kXSUKHd6zTCKfnKT3zV9EZHjzp1S', Decimal('1000')),
        ('rnziParaNb8nsU4aruQdwYE3j5jUcqjzFm', Decimal('20')),
        ('rhKJE9kFPz6DuK4KyL2o8NkCCNPKnSQGRL', Decimal('200'))
    ]

    assert tx.analyze_path() == {'offers': 0, 'intermediaries': 2}

    # The simplified single-accessor fail in this case
    with pytest.raises(ValueError):
        tx.sender_trust_limit


def test_payment_account_creation():
    txstr = open_transaction('payment_account_creation.json')
    tx = Transaction(txstr)

    assert tx.amount_received == (Decimal('35'), 'XRP', None)


@pytest.mark.xfail()
def test_payment_unknown():
    txstr = open_transaction('payment_unknown.json')
    tx = Transaction(txstr)

    # Returns intermediaries=4; I'm letting this fail because its a good
    # example of why we need to analyze the path better, because presumably
    # the 4th intermediary is the IOU issuer, and this really needs to be
    # reported separately.
    assert tx.analyze_path() == {'offers': 3, 'intermediaries': 3}


def test_account_root_node_without_fields():
    txstr = open_transaction('account_root_node_without_fields.json')
    tx = Transaction(txstr)

    # It we can do this to all nodes w/o exception, we are good
    for node in tx.affected_nodes:
        node.affects_account('foo')


def test_set_regular_key():
    """[Regression] Make sure we can handle SetRegularKey transactions."""
    txstr = open_transaction('set_regular_key.json')
    tx = Transaction(txstr)

    assert type(tx) == SetRegularKeyTransaction
