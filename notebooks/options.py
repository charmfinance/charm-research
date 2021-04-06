import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import seaborn as sns

sns.set_style("white")
plt.rcParams['figure.dpi'] = 200
plt.rc("font", size=8)


# lmsr cost function
def lmsr(q, b):
    mx = q.max()
    a = np.exp((q-mx)/b).sum()
    return mx + b * np.log(a)


# grad of lmsr cost wrt q
def gradq(q, b):
    a = np.exp((q - q.max()) / b)
    return a / a.sum()


# partial derivative of lmsr cost wrt b
def db(q, b, eps=1e-9):
    return (lmsr(q, b+eps) - lmsr(q, b)) / eps


def calc_call_payoffs(underlying_price, strike_prices):
    lo = np.concatenate([[0], strike_prices])
    hi = np.concatenate([strike_prices, [np.inf]])
    return np.maximum(0, np.minimum(hi, underlying_price) - lo) / underlying_price


def calc_put_payoffs(underlying_price, strike_prices):
    lo = np.concatenate([[1e-9], strike_prices])
    hi = np.concatenate([strike_prices, [1e9]])
    a = np.maximum(0, lo - underlying_price) / lo
    b = np.maximum(0, hi - underlying_price) / hi
    return b - a


def calc_call_lp_payoff(underlying_price, strike_prices, b):
    payoff = calc_call_payoffs(underlying_price, strike_prices)
    q = calc_q(payoff, b)
    return lmsr(q, b) - (payoff * q).sum()


def calc_put_lp_payoff(underlying_price, strike_prices, b):
    payoff = calc_put_payoffs(underlying_price, strike_prices)
    q = calc_q(payoff, b)
    return lmsr(q, b) - (payoff * q).sum()


# calculate what q would be at expiry assuming market is efficient and no arbs exist at expiry
def calc_q(payoff, b):
    def loss(q):
        return ((gradq(q, b) - payoff) ** 2).sum()

    initial = np.ones(payoff.shape)
    q = minimize(loss, initial, tol=1e-9).x

    # normalize since LMSR is translation invariant
    return q - q.min()


# make plots look nice
def format_ax(ax):
    sns.despine(top=True, right=True, left=False, bottom=False)
    ax.grid(False)
    ax.spines['left'].set_color('#999999')
    ax.spines['bottom'].set_color('#999999')
    ax.xaxis.label.set_color('#666666')
    ax.yaxis.label.set_color('#666666')
    ax.tick_params(axis='x', colors='#666666', which='both')
    ax.tick_params(axis='y', colors='#666666', which='both')

