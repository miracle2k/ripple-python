from decimal import Decimal


class RipplePrimitive(dict):

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
        """It would appear that if IOUs are transferred, the recipient
        is always listed as HighLimit.
        """
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


class AccountRootEntry(RipplePrimitive):
    """An account root entry exists for each account. It holds its XRP
    balance, last transaction sequence number, and related information.
    """

    def affects_account(self, account):
        return self.Account == account


class NodeModification(RipplePrimitive):
    """An entry in the ``AffectedNodes`` key of a processed transaction.
    """

    def __init__(self, data):
        RipplePrimitive.__init__(self, data)
        node_class = {
            'AccountRoot': AccountRootEntry,
            'RippleState': RippleStateEntry
        }[data['LedgerEntryType']]
        self.new = node_class(data['FinalFields'])
        self.old = node_class(data['PreviousFields'])
        self.type = type(self.new)

    def __getattr__(self, item):
        return getattr(self.new, item)


class Transaction(RipplePrimitive):
    """Makes data from a ripple transaction structure accessible.
    """

    @property
    def affected_nodes(self):
        for node in self.metaData.AffectedNodes:
            yield NodeModification(node['ModifiedNode'])

    def _get_node(self, account=None, type=None):
        """Return a affected node matching the filters, and make sure
        there is only one."""
        result = self.affected_nodes
        if account:
            result = filter(lambda n: n.affects_account(account), result)
        if type:
            result = filter(lambda n: n.type == type, result)
        result = list(result)
        assert len(result) == 1, 'Only one such node expected'
        return result[0]

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
        node = self._get_node(account=self.Destination, type=RippleStateEntry)
        if isinstance(self.Amount, dict):
            return (self.Amount.currency, node.counter_party(self.Destination))
        else:
            return (self.Amount, None)


    def recipient_balance(self):
        node = self._get_node(account=self.Destination, type=RippleStateEntry)
        return node.new.balance(self.Destination)

