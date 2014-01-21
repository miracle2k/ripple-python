#!/usr/bin/env python
import json

import os
import sys

from ripple import sign_transaction, Client
from ripple.client import transaction_hash, Remote
from ripple.sign import get_ripple_from_secret


LOCAL_SIGNING = int(os.environ.get('LOCAL_SIGNING', 1))


def main(argv):
    if len(argv) <= 1:
        print "Usage: transact.py <secret> payment <destination> <amount>"
        return 1

    secret = argv[1]
    command = argv[2]
    args = argv[3:]

    assert command == 'payment', 'Only payments supported right now'

    #cmd_pay_2(secret, *args)
    #return

    # Connect to rippled
    remote = Client(os.environ.get('RIPPLE_URI', 'wss://s1.ripple.com'))

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

    if not LOCAL_SIGNING:
        print(remote.submit(tx_json=tx, secret=secret))
    else:
        # Signup to the transaction stream so we'll be able to verify
        # the transaction result.
        result, queue = remote.subscribe(streams=['server'])

        # Submit the transaction.
        remote.submit(tx_blob=tx)
        txhash = transaction_hash(tx)

        remote.close()
        # Look for the final disposition.
        # TODO: That would actually involve looking at the values though
        # rather than just printing the first status update.
        while True:
            tx = queue.get(timeout=1)
            if tx['transaction']['hash'] == txhash:
                print('FOUND: %s' % tx)
                break


def cmd_pay_2(secret, destination, amount):
    # Example for payment with high-level API
    remote = Remote(os.environ.get('RIPPLE_URI', 'wss://s1.ripple.com'), secret)
    transaction = remote.send_payment(destination, int(amount))
    print(transaction.wait())


if __name__ == '__main__':
    sys.exit(main(sys.argv) or 0)
