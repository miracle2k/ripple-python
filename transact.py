#!/usr/bin/env python

import os
import sys
import json

from ripple import sign_transaction, Remote
from ripple.sign import get_ripple_from_secret
from ripple.client import transaction_hash


LOCAL_SIGNING = int(os.environ.get('LOCAL_SIGNING', 1))


def main(argv):
    if len(argv) <= 1:
        print "Usage: transact.py <secret> payment <destination> <amount>"
        return 1

    secret = argv[1]
    command = argv[2]
    args = argv[3:]

    assert command == 'payment', 'Only payments supported right now'

    # Connect to rippled
    remote = Remote(os.environ.get('RIPPLE_URI', 'wss://s1.ripple.com'))

    # Execute the command
    cmd_pay(remote, secret, *args)


def cmd_pay(remote, secret, destination, amount):
    sender = get_ripple_from_secret(secret)
    print('Sender: {}'.format(sender))

    # Construct the basic transaction
    tx = {
        "TransactionType" : "Payment",
        "Account" : sender,
        "Destination" : destination,
        "Amount" : "%s" % amount,
    }
    remote.add_fee(tx)

    # We need to determine the sequence number
    sequence = remote.request_account_info(sender)['Sequence']
    tx['Sequence'] = sequence

    # Sign the transaction
    if LOCAL_SIGNING:
        sign_transaction(tx, secret)

    print('I will now submit:')
    print(json.dumps(tx, indent=2))

    if LOCAL_SIGNING:
        remote.submit(tx_blob=tx)
        print(transaction_hash(tx))
    else:
        remote.submit(tx_json=tx, secret=secret)


if __name__ == '__main__':
    sys.exit(main(sys.argv) or 0)
