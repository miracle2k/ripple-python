from decimal import Decimal


class RipplePrimitive(dict):
    """Dict that allows attribute access."""

    def __init__(self, data):
        dict.__init__(self, **data)

    def __getattr__(self, item):
        try:
            value = self[item]
            if isinstance(value, dict) and not isinstance(value, RipplePrimitive):
                value = RipplePrimitive(value)
                self[item] = value
            return value
        except KeyError:
            raise AttributeError(item)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict.__repr__(self))


class RippleStateEntry(RipplePrimitive):
    """Ripple state entries exist when one account sets a credit limit
    to another account in a particular currency or if an account holds
    the IOUs of another account. Each entry is shared between two accounts.
    """

    def affects_account(self, account):
        try:
            if self.counter_party(account):
                return True
        except ValueError:
            return False

    def counter_party(self, account):
        if self.LowLimit.issuer == account:
            return self.HighLimit.issuer
        if self.HighLimit.issuer == account:
            return self.LowLimit.issuer
        raise ValueError('%s is not a party' % account)

    def balance(self, account):
        """Return the balance from the perspective of the given account.
        """
        if self.LowLimit.issuer == account:
            return Decimal(self.Balance.value)
        if self.HighLimit.issuer == account:
            return -Decimal(self.Balance.value)
        raise ValueError('%s is not a party' % account)

    def trust_limit(self, account):
        """Return the trust limit from the perspective of the given account.
        """
        if self.LowLimit.issuer == account:
            return Decimal(self.LowLimit.value)
        if self.HighLimit.issuer == account:
            return Decimal(self.HighLimit.value)
        raise ValueError('%s is not a party' % account)


class AccountRootEntry(RipplePrimitive):
    """An account root entry exists for each account. It holds its XRP
    balance, last transaction sequence number, and related information.
    """

    def affects_account(self, account):
        return self.Account == account


class OfferEntry(RipplePrimitive):
    """A offer entry specifies the terms of exchange between two currencies.
    """

    def affects_account(self, account):
        # Does not return True if the account's IOUs are being traded
        return self.Account == account


class DirectoryNodeEntry(RipplePrimitive):

    def affects_account(self, account):
        return False


LedgerEntries = {
    'AccountRoot': AccountRootEntry,
    'RippleState': RippleStateEntry,
    'Offer': OfferEntry,
    'DirectoryNode': DirectoryNodeEntry,
}


def shadow(front, back):
    # For now this is a hard-merge, but I'd prefer a transient fall-through.
    result = back.copy()
    back.update(front)
    return result


class NodeModification(RipplePrimitive):
    """An entry in the ``AffectedNodes`` key of a processed transaction.
    """

    def __init__(self, data):
        RipplePrimitive.__init__(self, data)
        node_class = LedgerEntries[data['LedgerEntryType']]
        self.new = node_class(data['FinalFields'])
        if 'PreviousFields' in data:
            self.old = node_class(
                # PreviousFields only contains parts, presumably those
                # that changed, so add a fallback to the shared data).
                shadow(data['PreviousFields'], data['FinalFields']))
        else:
            self.old = None
        self.type = type(self.new)

    def __getattr__(self, item):
        return getattr(self.new, item)


class NodeDeletion(NodeModification):
    """An entry in the ``AffectedNodes`` key of a processed transaction.
    """


class Transaction(RipplePrimitive):
    """Makes data from a ripple transaction structure accessible.

    ``meta`` can be given if the transaction data has no ``metaData``
    key. This is because the Ripple server will hand out different
    formats: When querying a ledger, the meta that is in said key.
    When subscribing to the transaction feed, the metadata is given
    separately from the transaction.
    """

    def __init__(self, data, meta=None):
        RipplePrimitive.__init__(self, data)
        self.meta = meta

        # __new__ could also be used for this I suppose
        subclass = {
            'Payment': PaymentTransaction,
            'OfferCreate': OfferCreateTransaction,
            'OfferCancel': OfferCancelTransaction,
            'TrustSet': TrustSetTransaction,
            'AccountSet': AccountSetTransaction,
        }[data['TransactionType']]
        self.__class__ = subclass

    @property
    def type(self):
        return type(self)

    def _get_meta(self):
        return self._meta or self.metaData
    def _set_meta(self, value):
        self._meta = RipplePrimitive(value) if value else value
    meta = property(_get_meta, _set_meta)

    @property
    def successful(self):
        return self.meta.TransactionResult == 'tesSUCCESS'

    @property
    def affected_nodes(self):
        for node in self.meta.AffectedNodes:
            assert len(list(node.keys())) == 1
            change_type = list(node.keys())[0]
            node_class = {
                'ModifiedNode': NodeModification,
                'DeletedNode': NodeDeletion}[change_type]
            yield node_class(list(node.values())[0])

    def _get_node(self, account=None, type=None):
        """Return a affected node matching the filters, and make sure
        there is only one."""
        result = self.affected_nodes
        if account:
            result = filter(lambda n: n.affects_account(account), result)
        if type:
            result = filter(lambda n: n.type == type, result)
        result = list(result)
        assert len(result) == 1, 'One node expected, found %s' % len(result)
        return result[0]


xrp_base = Decimal('1000000')
def xrp(s):
    """XRP is given in the API as a large int, convert to a decimal.
    """
    return Decimal(s) / xrp_base


class PaymentTransaction(Transaction):

    @property
    def currency_received(self):
        """Returns a 2-tuple (code, issuer) indicating the currency
        that was received. In case of XRP, ``('XRP', None)`` is returned.

        What it does:

        The currency itself is readily available in ``Amount.currency``
        (or in case of XRP, ``Amount`` will be an integer). The issuer
        of that currency is a bit more complicated. Here are some places
        where we do not find it:

        - ``Amount.issuer`` - always seems to be the account of the recipient.
        - The last element of ``Paths``. Frequently, multiple paths are
          listed, and it's  not clear which one the transaction took.

        All in all, it it seems as if that part of the transaction is verbatim
        what the client submitted. Instead, we look into ``metaData``.

        There, we find a list of AffectedNodes, and we just find the one
        that relates to the account of the recipient.
        """
        if self.is_xrp_received:
            # This means XRP was received.
            return ('XRP', None)
        else:
            node = self._get_node(account=self.Destination, type=RippleStateEntry)
            return (self.Amount.currency, node.counter_party(self.Destination))


    @property
    def amount_received(self):
        """3-tuple of (amount, currency, issuer).
        """
        amount = self.Amount.value if isinstance(self.Amount, dict) else xrp(self.Amount)
        return tuple(
            [amount] +
            list(self.currency_received)
        )

    @property
    def is_xrp_received(self):
        # Looking at this field is the only way. It should be reliable.
        # In complex routings, in don't thing AffectedNodes can conclusively
        # tell us; or, it's really hard.
        return not isinstance(self.Amount, dict)

    @property
    def is_xrp_sent(self):
        return not isinstance(self.SendMax, dict)

    def get_balance(self, who, previous=False):
        """Returns the previous balance *with the issuer*.
        """
        where = 'old' if previous else 'new'
        if self.is_xrp_received:
            # If it is a XRP payment, there should be one AccountRoot change
            node = self._get_node(account=who, type=AccountRootEntry)
            return xrp(getattr(node, where).Balance)
        else:
            # Otherwise, there should be one RippleState entry
            node = self._get_node(account=who, type=RippleStateEntry)
            return getattr(node, where).balance(who)

    @property
    def recipient_balance(self):
        return self.get_balance(self.Destination)

    @property
    def recipient_previous_balance(self):
        return self.get_balance(self.Destination, previous=True)

    @property
    def recipient_trust_limit(self):
        if self.is_xrp_received:
            return None
        else:
            node = self._get_node(account=self.Destination, type=RippleStateEntry)
            return node.new.trust_limit(self.Destination)

    @property
    def sender_trust_limit(self):
        if self.is_xrp_sent:
            return None
        else:
            node = self._get_node(account=self.Acount, type=RippleStateEntry)
            return node.new.trust_limit(self.Account)

    def analyze_path(self):
        """This will give you some information about how the payment was
        routed.

        Specifically, the return value is a dict that looks like this::

            {'intermediaries': 2, 'offers': 1}

        If intermediaries is 0, there was a trust set between the two parties
        (or its a direct XRP payment).
        If intermediaries is 1, both parties trust the same third party.
        If intermediaries is 2, one additional user helped.
        And so on.

        ``offers`` specifies the number of market offers that were fully
        or partially executed during payment routing. This is always included
        in ``intermediaries``.

        So the following may be true:

            intermediaries - offers - 1 = ripples involved

        ----

        How is this done? Drawing automated conclusions from the set of
        unlinked node changes can be a bit of a challenge. For example, an
        AccountRoot node may be modified when someone pays in XRP, when
        a fee is claimed during an IOU payment, or when your offer gets
        resolved during a third party's payment.
        Presumably, this can be vastly improved.
        """

        # list() used once exhausts the generator, it's tiring..
        filter = lambda f, d: list(__builtins__['filter'](f, d))

        # Ignore all DirectoryNodes, not sure what they do, it seems
        # like upkeep.
        nodes = filter(lambda n: n.type != DirectoryNodeEntry, self.affected_nodes)

        # Ignore all XRP acounting nodes. These either indicate a fee,
        # or a direct payment, which would mean no intermediaries.
        nodes = filter(lambda n: n.type != AccountRootEntry, nodes)

        # Ignore all nodes involving the recipient. If its a direct payment,
        # it will delete the sender's state node as well. If we are dealing
        # with a third party IOUs, the sender's balance node will be left to
        # be counted as our "one" hop (transferring Bitstamp IOUs between
        # two accounts generates two RippleState node changes, both party's
        # balance with Bitstamp).
        nodes = filter(lambda n: not n.new.affects_account(self.Destination), nodes)

        # Count the offer nodes. These are easy, each such node indicates
        # one offer that was involved.
        offers = filter(lambda n: n.type == OfferEntry, nodes)

        # Each offer comes with AccountRoot and RippleStateEntry nodes
        # for the accounts of the offerer, so we need to filter those
        # out as well.
        for offer in offers:
            nodes = filter(lambda n: not n.affects_account(offer.Account), nodes)

        # What is left is the payee RippleState + one RippleState for each
        # true intermediary that was involved.
        # For validation, make sure all the nodes left are RippleState entries
        assert len(filter(lambda n: n.type != RippleStateEntry, nodes)) == 0

        return {
            'intermediaries': len(nodes) + len(offers),
            'offers': len(offers)
        }


class OfferCreateTransaction(Transaction):
    pass


class OfferCancelTransaction(Transaction):
    pass


class TrustSetTransaction(Transaction):
    pass


class AccountSetTransaction(Transaction):
    pass


class TransactionSubscriptionMessage(RipplePrimitive):
    """The data structure returned by the server when subscribing to
    transaction updates.
    """

    @property
    def transaction(self):
        return Transaction(self['transaction'], meta=self['meta'])
