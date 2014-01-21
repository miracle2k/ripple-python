from decimal import Decimal
from pytest import raises
from ripple.datastructures import Amount


def test_amount():
    # Parse input
    assert Amount(10).currency == 'XRP'
    assert Amount(10).issuer == None
    assert Amount(10).value == Decimal('0.00001')
    assert Amount(Decimal('10')).value == Decimal('10')
    assert Amount('10.0').value == Decimal('10')
    with raises(ValueError):
        assert Amount('10').value == Decimal('10')

    # Generate output
    assert u'%s' % Amount('10.0').__json__ == 10000000







