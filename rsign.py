#!/usr/bin/env python
from __future__ import print_function
import json
import sys
from ripple import sign_transaction
from ripple.sign import create_signing_hash
from ripple.serialize import serialize_object


def main(argv):
    if len(argv) <= 1:
        print("Usage: rsign.py <secret> <json>")
        print()
        print('Example: rsign.py ssq55ueDob4yV3kPVnNQLHB6icwpC \'{"TransactionType":"Payment","Account":"r3P9vH81KBayazSTrQj6S25jW6kDb779Gi","Destination":"r3kmLJN5D28dHuH8vZNUZpMC43pEHpaocV","Amount":"200000000","Fee":"10","Sequence":1}\'')
        return 1

    secret = argv[1]
    tx = json.loads(argv[2])
    signed_tx = sign_transaction(tx.copy(), secret)

    # For compatibility with rsign.js, comparing the output is
    # otherwise quite confusing.
    tx['SigningPubKey'] = signed_tx['SigningPubKey']

    output = {
        'tx_json': signed_tx,
        'tx_blob': serialize_object(signed_tx),
        'tx_signing_hash': create_signing_hash(tx),
        'tx_unsigned': serialize_object(tx)
    }
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    sys.exit(main(sys.argv) or 0)
