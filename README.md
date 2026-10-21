# amazon-auth

`amazon-auth` is the session layer for Amazon (sign-in, OTP and MFA, challenges, and cookie persistence), being carved
out of [`amazon-orders`](https://github.com/alexdlaird/amazon-orders) so other packages can build on Amazon sign-in
without the rest of `amazon-orders`.

> **Note:** The refactor is under active development, and its first pieces land here in the near future. Until
> sign-in moves over, you can use [`amazon-orders`](https://pypi.org/project/amazon-orders/), whose
> [`AmazonSession`](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession) provides the same
> sign-in and session handling today. `amazon-orders` will build on `amazon-auth` as each piece moves, so code using
> `AmazonSession` today keeps working.
