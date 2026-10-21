# amazon-auth

`amazon-auth` will be the sign-in and session layer for Amazon (sign-in, OTP and MFA, challenges, and cookie
persistence), extracted from [`amazon-orders`](https://github.com/alexdlaird/amazon-orders) so other packages can build
on it without the rest of `amazon-orders`.

> **Note:** This package is a placeholder and isn't usable yet. Until it is, use
> [`amazon-orders`](https://pypi.org/project/amazon-orders/), whose
> [`AmazonSession`](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession) provides the same
> sign-in and session handling today.
