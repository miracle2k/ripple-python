"""I want this to be a straightforward and easy to understand
implementation of the signing procedure that can be ripped from this
library and used on its own.
"""

from hashlib import sha256, sha512
from ecdsa import curves, SigningKey
from ecdsa.util import sigencode_der


__all__ = ('sign_transaction', 'signature_for_transaction')


def sign_transaction(transaction, secret):
    """Adds a signature (``TxnSignature``) field to the transaction object.
    """
    sig = signature_for_transaction(transaction, secret)
    transaction['TxnSignature'] = sig
    return transaction


def signature_for_transaction(transaction, secret):
    """Calculate the signature of the transaction.

    Will set the ``SigningPubKey`` as appropriate before signing.

    ``transaction`` is a Python object. The result value is what you
    can insert into as ``TxSignature`` into the transaction structure
    you submit.
    """
    seed = parse_seed(secret)
    key = root_key_from_seed(seed)

    # Apparently the pub key is required to be there.
    transaction['SigningPubKey'] = '%X' % from_bytes(
        ecc_point_to_bytes_compressed(key.privkey.public_key.point))

    # Convert the transaction to a binary representation
    signing_hash = tx_to_binary(transaction)

    # Create a hex-formatted signature.
    return '%X' % ecdsa_sign(key, signing_hash)


def parse_seed(secret):
    """Your Ripple secret is a seed from which the true private key can
    be derived.

    The ``Seed.parse_json()`` method of ripple-lib supports different
    ways of specifying the seed, including a 32-byte hex value. We just
    support the regular base-encoded secret format given to you by the
    client when creating an account.
    """
    assert secret[0] == 's'
    return RippleBaseDecoder.decode(secret)


def root_key_from_seed(seed):
    """This derives your master key the given seed.

    Implemented in ripple-lib as ``Seed.prototype.get_key``, and further
    is described here:
    https://ripple.com/wiki/Account_Family#Root_Key_.28GenerateRootDeterministicKey.29
    """
    seq = 0
    while True:
        private_gen = from_bytes(first_half_of_sha512(
            '{}{}'.format(seed, to_bytes(seq, 4))))
        seq += 1
        if curves.SECP256k1.order >= private_gen:
            break

    public_gen = curves.SECP256k1.generator * private_gen

    # Now that we have the private and public generators, we apparently
    # have to calculate a secret from them that can be used as a ECDSA
    # signing key.
    secret = i = 0
    public_gen_compressed = ecc_point_to_bytes_compressed(public_gen)
    while True:
        secret = from_bytes(first_half_of_sha512(
            "{}{}{}".format(
                public_gen_compressed, to_bytes(0, 4), to_bytes(i, 4))))
        i += 1
        if curves.SECP256k1.order >= secret:
            break
    secret = secret + private_gen % curves.SECP256k1.order

    # The ECDSA signing key object will, given this secret, then expose
    # the actual private and public key we are supposed to work with.
    return SigningKey.from_secret_exponent(secret, curves.SECP256k1)


def ecdsa_sign(key, bytes):
    """Sign the given data. The key is the secret returned by
    :func:`root_key_from_seed`.

    The data will be a binary coded transaction.
    """
    r, s = key.sign_number(from_bytes(bytes))
    # Encode signature in DER format, as in.
    # As in ``sjcl.ecc.ecdsa.secretKey.prototype.encodeDER``
    der_coded = sigencode_der(r, s, None)
    # Return as uppercase hex
    return from_bytes(der_coded)


def tx_to_binary(transaction):
    # 'HASH_TX_SIGN_TESTNET' : 'HASH_TX_SIGN' -> to binary
    # sha512(prefix + binaryObject)
    return 'DCB1705AC616BA2FA2F0BCC21277192A24A726B4900636496E166816B4EE11D9'



class RippleBaseDecoder(object):
    """Decodes Ripple's base58 alphabet.

    This is what ripple-lib does in ``base.js``.
    """

    alphabet = 'rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz'

    @classmethod
    def decode(cls, *a, **kw):
        """Apply base58 decode, verify checksum, return payload.
        """
        decoded = cls.decode_base(*a, **kw)
        assert cls.verify_checksum(decoded)
        payload = decoded[:-4] # remove the checksum
        payload = payload[1:]  # remove first byte, a version number
        return payload

    @classmethod
    def decode_base(cls, encoded, pad_length=None):
        """Decode a base encoded string with the Ripple alphabet."""
        n = 0
        base = len(cls.alphabet)
        for char in encoded:
            n = n * base + cls.alphabet.index(char)
        return to_bytes(n, pad_length, 'big')

    @classmethod
    def verify_checksum(cls, bytes):
        """These ripple byte sequences have a checksum builtin.
        """
        valid = bytes[-4:] == sha256(sha256(bytes[:-4]).digest()).digest()[:4]
        return valid

    @staticmethod
    def as_ints(bytes):
        return list([ord(c) for c in bytes])


def first_half_of_sha512(bytes):
    """As per spec, this is the hashing function used."""
    return sha512(bytes).digest()[:256/8]


def to_bytes(number, pad_length=None, endianess='big'):
    """Will take an integer and serialize it to a string of bytes.
    Python 3 has this, this is a backport to Python 2.
    # http://stackoverflow.com/a/16022710/15677
    """
    h = '%x' % number
    s = ('0'*(len(h) % 2) + h)
    if pad_length:
        s = s.zfill(pad_length*2)
    s = s.decode('hex')
    return s if endianess == 'big' else s[::-1]


def from_bytes(bytes):
    """Reverse of to_bytes()."""
    return int(bytes.encode('hex'), 16)


def ecc_point_to_bytes_compressed(point):
    """
    In ripple-lib, implemented as a prototype extension
    ``sjcl.ecc.point.prototype.toBytesCompressed`` in ``sjcl-custom``.

    Also implemented as ``KeyPair.prototype._pub_bits``, though in
    that case it seems to explicitly try to pad to the bit length of
    the curve prime order value.
    """
    header = '\x02' if point.y() % 2 == 0 else '\x03'
    return "{}{}".format(header, to_bytes(point.x()))


import json
print json.dumps(sign_transaction({}, 'ssq55ueDob4yV3kPVnNQLHB6icwpC'), indent=3)



class Test:
    def test_seed(self):
        parsed = parse_seed('ssq55ueDob4yV3kPVnNQLHB6icwpC')
        assert RippleBaseDecoder.as_ints(parsed) == [
            33,
            82,
            50,
            144,
            230,
            54,
            214,
            205,
            65,
            69,
            243,
            240,
            63,
            133,
            73,
            87,
            122,
            127,
            146,
            238,
            172 ]
