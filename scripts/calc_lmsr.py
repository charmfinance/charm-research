import click
from scipy.optimize import minimize
import numpy as np


@click.command()
@click.option("--b", type=float)
@click.argument("q", nargs=-1, type=float)
def calc_lmsr(b, q):
    q = np.array(q)

    def lmsr(q):
        mx = q.max()
        a = np.exp((q-mx)/b).sum()
        return mx + b * np.log(a)

    # gradient of lmsr cost function
    def grad(q):
        a = np.exp((q - q.max()) / b)
        return a / a.sum()

    print(f"Cost:    {lmsr(q)}")
    print(f"Prices:  {grad(q)}")


if __name__ == "__main__":
    calc_lmsr()
