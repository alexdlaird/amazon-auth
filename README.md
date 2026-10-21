# amazon-auth

`amazon-auth` signs in to Amazon's consumer website (amazon.com and other Amazon sites) and reuses the session from
Python: sign-in, OTP and MFA, challenges, browser sign-in, and cookie persistence. It's being carved out of
[`amazon-orders`](https://github.com/alexdlaird/amazon-orders) so other packages can build on Amazon sign-in without the
rest of `amazon-orders`.

> **Note:** The refactor is under active development, and its first pieces land here in the near future. Until
> sign-in moves over, you can use [`amazon-orders`](https://pypi.org/project/amazon-orders/), whose
> [`AmazonSession`](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession) provides the same
> sign-in and session handling today. `amazon-orders` will build on `amazon-auth` as each piece moves, so code using
> `AmazonSession` today keeps working.
