#!/usr/bin/env python
from __future__ import print_function
import json
import os
import sys
import argparse

from ripple.client import Remote
from ripple.sign import get_ripple_from_secret


LOCAL_SIGNING = int(os.environ.get('LOCAL_SIGNING', 1))


def main(argv):
    parser = argparse.ArgumentParser(argv[0])
    parser.add_argument('secret')
    parser.add_argument('--server')
    # Add a subparser for every command defined
    cmd_parsers = parser.add_subparsers(help='command help', dest='command')
    commands = {}
    for _, value in globals().items():
        if isinstance(value, type) and issubclass(value, Command) \
                and not value is Command:
            commands[value.name] = value
            subparser = cmd_parsers.add_parser(value.name)
            value.add_args(subparser)

    # Parse and resolve
    ns = parser.parse_args(argv[1:])

    # Do some manual validation
    secret = ns.secret or os.environ.get('RIPPLE_SECRET')
    if not secret:
        print('You need to provide --secret or RIPPLE_SECRET')
        return 1

    # Run the command
    cmd_klass = commands[ns.command]
    cmd = cmd_klass(
        ns.server or os.environ.get('RIPPLE_URI') or 'wss://s-east.ripple.com',
        secret)
    return cmd.run(ns)


class Command(object):

    def __init__(self, ripple_uri, secret):
        self.ripple_uri = ripple_uri
        self.secret = secret

    @classmethod
    def add_args(cls, parser):
        pass

    @property
    def remote(self):
        if not hasattr(self, '_remote'):
            self._remote = Remote(self.ripple_uri, self.secret)
        return self._remote

    def handle(self, result):
        print('TxHash: %s' % result.hash)
        result = result.wait()
        print(result['engine_result_message'])

    @property
    def account(self):
        return get_ripple_from_secret(self.secret)


class GetAddress(Command):
    """Get ripple address for a secret.
    """
    name = 'get-address'
    def run(self, ns):
        print(get_ripple_from_secret(self.secret))


class RawCommand(Command):
    """Submit JSON as specified by the user."""

    name = 'raw'

    @classmethod
    def add_args(self, parser):
        parser.add_argument('json', help='Custom JSON transaction')

    def run(self, ns):
        tx = json.loads(ns.json)
        result = self.remote.submit(tx['Account'], tx)
        self.handle(result)


def yesno(v):
    try:
        return {'yes': True, 'no': False}[v]
    except KeyError:
        raise argparse.ArgumentTypeError('%s: want yes or no' % v)


class AccountSet(Command):
    """Set account properties."""

    # TODO: I don't quite understand the flag setting yet. The account
    # value afterwards is always a single flag, not a set of them.

    name = 'account-set'

    tfRequireDestTag = 0x00010000
    tfOptionalDestTag = 0x00020000
    tfRequireAuth = 0x00040000
    tfOptionalAuth = 0x00080000
    tfDisallowXRP = 0x00100000
    tfAllowXRP = 0x00200000

    @classmethod
    def add_args(self, parser):
        parser.add_argument(
            '--allow-xrp', nargs='?', type=yesno, const='yes',
            help='Account may receive XRP')
        parser.add_argument(
            '--require-dest', nargs='?', type=yesno, const='yes',
            help='Payments require a destination tag')
        parser.add_argument(
            '--domain', help='Associate a domain with this account')

    def run(self, ns):
        flags = 0
        if ns.allow_xrp is not None:
            flags |= self.tfAllowXRP if ns.allow_xrp else self.tfDisallowXRP
        if ns.require_dest is not None:
            flags |= self.tfRequireDestTag if ns.require_dest else self.tfOptionalDestTag

        tx = {
            "TransactionType": "AccountSet",
            "Account": self.account
        }
        if flags:
            tx['Flags'] = flags

        if ns.domain:
            tx['Domain'] = ns.domain.lower().encode('hex').upper()

        result = self.remote.submit(tx['Account'], tx)
        self.handle(result)



class PaymentCommand(Command):
    """Send a payment."""

    name = 'payment'

    tfPartialPayment = 0x00020000

    @classmethod
    def add_args(self, parser):
        parser.add_argument('destination', help='Destination account')
        parser.add_argument('amount', help='Amount to send')
        parser.add_argument('--partial', action='store_true',
                            help='recipient will pay any fees')

    def run(self, ns):
        amount = ns.amount
        if '/' in amount:
            value, currency = ns.amount.split('/', 2)
            amount = {'value': value, 'currency': currency}

        flags = 0
        if ns.partial:
            flags |= self.tfPartialPayment

        result = self.remote.send_payment(
            ns.destination, amount, flags=flags)
        self.handle(result)


if __name__ == '__main__':
    sys.exit(main(sys.argv) or 0)

