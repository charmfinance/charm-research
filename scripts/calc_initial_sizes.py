import click
from scipy.optimize import minimize
import numpy as np


@click.command()
@click.option("--b", type=float)
@click.argument("prices", nargs=-1, type=float)
def calc_initial_sizes(b, prices):
    assert list(prices) == sorted(prices)
    target = np.concatenate([
        [prices[0]],
        np.diff(prices),
        [1.0 - prices[-1]],
    ])

    print("Target gradient:")
    for x in target:
        print(f"{x:.6f}")
    print()

    def lmsr(q):
        mx = q.max()
        a = np.exp((q-mx)/b).sum()
        return mx + b * np.log(a)

    # gradient of lmsr cost function
    def grad(q):
        a = np.exp((q - q.max()) / b)
        return a / a.sum()

    def loss(q):
        return ((grad(q) - target) ** 2).sum()

    initial = np.ones(target.shape)
    res = minimize(loss, initial, tol=1e-9)
    print(res.message)

    q = res.x
    q -= q.min()

    print(f"Cost: {lmsr(q):.6f}")
    print(f"Loss: {loss(q)}")
    print()

    print(f"Quantities:")
    for x in q:
        print(f"{x:.6f}")
    print()

    long = q[:-1].copy()
    short = q[1:].copy()

    mn = np.minimum(long, short)
    long -= mn
    short -= mn

    print(f"Long calls/puts:")
    for x in long:
        print(f"{x:.6f}")
    print()

    print(f"Short calls/puts:")
    for x in short:
        print(f"{x:.6f}")
    print()

    q2 = np.concatenate([[0], np.cumsum(short)])
    q2 += np.concatenate([[0], np.cumsum(long[::-1])])[::-1]
    print(f"Cost of options: {lmsr(q2):.6f}")

    # check equal to target
    # print(grad(q2))


if __name__ == "__main__":
    calc_initial_sizes()
