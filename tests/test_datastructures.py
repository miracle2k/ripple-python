from decimal import Decimal
from pytest import raises
from ripple.datastructures import Amount


def test_amount():
    # Parse different XRP input types
    assert Amount(10).currency == 'XRP'
    assert Amount(10).issuer == None
    assert Amount(10).value == Decimal('0.00001')
    assert Amount(Decimal('10')).value == Decimal('10')
    assert Amount('10.0').value == Decimal('10')
    assert Amount('10').value == Decimal('0.00001')
    # Ensure that high level input types are serialized properly
    assert Amount('10.0').__json__() == 10000000

    # The Amount.value can be modified
    a = Amount(15)
    a.value = 10
    assert a.data == 10000000
    # Same for IOUsa = Amount(15)
    a = Amount({'value': '10', 'currency': 'USD'})
    a.value = 15
    assert a.data['value'] == '15'

    # Make sure we can do math
    assert (Amount(10) + Amount(15)).value == Decimal('0.000025')
    assert (Amount({'value': '10', 'currency': 'USD'}) - '2').value == 8

    # If Amount represents an IOU, then it can also be used as a dict
    amount = Amount({'value': '10', 'currency': 'USD'})
    assert not ('issuer' in amount)
    amount['issuer'] = 'foo'
    assert amount.issuer == 'foo'







