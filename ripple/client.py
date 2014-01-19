import json
import websocket
import logging
from .serialize import serialize_object
from .sign import hash_transaction, HASH_TX_ID


__all__ = ('Remote',)


log = logging.Logger('ripple.client')
log.addHandler(logging.StreamHandler())
log.addHandler(logging.NullHandler())


class ResponseError(Exception):
    pass


# TODO: Support calculating a fee based on the server, see:
# ripple-lib:server.js:feeTxUnit()
FEE_DEFAULT = 10


def transaction_hash(tx_json):
    """To identify a transaction, we can use the signing-hash algorithm
    with a special prefix; the result should match the transaction id
    that the server will use.

    In particular because we do not have a blob serializer, we'll have to
    use the dict structure to calculate the hash.
    """
    return hash_transaction(tx_json, HASH_TX_ID)


class Remote(object):
    """Connection to Ripple network.
    """

    def __init__(self, url):
        self.conn = websocket.create_connection(url, timeout=10)
        self.queue = []

    def _mkid(self):
        setattr(self, '_id', getattr(self, '_id', 0) + 1)
        return self._id

    def add_fee(self, tx, amount=None):
        """Add a fee to the given transaction dict.
        """
        tx['Fee'] = amount or FEE_DEFAULT

    def execute(self, cmd, **data):
        # Prepare the command to send
        data['command'] = cmd
        data['id'] = self._mkid()
        data = {k:v for k, v in data.items() if v is not None}

        log.debug(json.dumps(data, indent=2))
        self.conn.send(json.dumps(data))

        response = self.wait(data['id'])
        log.debug(response)
        if not response['status'] == 'success':
            raise ResponseError(response)
        return response['result']

    def wait(self, id):
        msg = self.conn.recv()
        msg = json.loads(msg)
        if msg['id'] == id:
            return msg
        # At some point I'd like to support subscribes/threads, and other
        # out-of-order response types.
        raise ValueError('response has id %s, expected %s' % (msg['id'], id))

    def request_account_info(self, account):
        return self.execute("account_info", account=account)['account_data']

    def submit(self, tx_blob=None, tx_json=None, secret=None):
        """Submit the transaction.

        You may either send a signed transaction (as a serialized
        tx_blob or unserialized dict, both as ``tx_blob``), or you
        may pass a secret and a ``tx_json`` dict to let the server
        do the signing.
        """
        assert not (tx_blob and tx_json)
        if isinstance(tx_blob, dict):
            tx_blob = serialize_object(tx_blob)

        result = self.execute(
            "submit", tx_blob=tx_blob, tx_json=tx_json, secret=secret)
        print(result)


