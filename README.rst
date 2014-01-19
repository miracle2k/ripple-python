Python utilities to work with the Ripple payment network.

For now, this contains:


ripple.sign
    Offline signing for transactions.
    [very new, but seems to work so far]

ripple.serialize
    Encode data structures transactions to binary.
    [not 100% complete, but most things you'll need for transactions]

ripple.client
    High-level client library. [very much a work in progress]

ripple.datastructures
    Helps extracting information from Ripple transaction data, like
    how balances changed during a payment. [very much a work in progress]
