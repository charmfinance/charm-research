import brownie
import click
import numpy as np
import pandas as pd
import requests


EVENT_NAMES = {
    "Buy",
    "Sell",
    "Deposit",
    "Withdraw",
}


@click.command()
@click.option("-k", "--key", required=True, help="Covalent api key")
@click.option("-a", "--address", required=True, multiple=True)
def fetch_market(key, address):
    brownie.network.connect("mainnet")

    dfs = []
    for addr in address:

        # fetch contract variables
        contract = brownie.Contract.from_explorer(addr)
        is_put = contract.isPut()
        decimals = contract.decimals()
        strikes = [contract.strikePrices(i) * 1e-18 for i in range(contract.numStrikes())]
        expiry_price = contract.expiryPrice() * 1e-18
        assert expiry_price > 0

        # fetch trades
        events = _fetch_events(key, addr, EVENT_NAMES)
        df = pd.DataFrame(events)
        df = df[df["event"].isin(["Buy", "Sell"])]
        df = df[~df["isSettled"].fillna(False)]
        df["strike"] = df["strikeIndex"].map(lambda i: strikes[int(i)])

        def to_float(x):
            return x.fillna(0).astype(float) / (10 ** decimals)

        # calculate trade quantities and pnls
        df["qty"] = to_float(df["optionsOut"]) - to_float(df["optionsIn"])
        df["pnl"] = to_float(df["amountOut"]) - to_float(df["amountIn"])
        if not is_put:
            df["pnl"] *= expiry_price

        # calculate option payoffs
        call_payoff = np.maximum(0, expiry_price - df["strike"])
        put_payoff = np.maximum(0, df["strike"] - expiry_price)
        short_payoff = np.minimum(expiry_price, df["strike"])
        long_payoff = put_payoff if is_put else call_payoff
        df["payoff"] = df["qty"] * np.where(df["isLongToken"], long_payoff, short_payoff)

        dfs.append(df)

        # print stats
        print(addr)
        print("Num buys:         ", (df["event"] == "Buy").sum())
        print("Num sells:        ", (df["event"] == "Sell").sum())
        print("Num trades:       ", len(df))
        print("Traded volume:    ", df["qty"].abs().sum())
        print()

    # print total stats
    merged = pd.concat(dfs)
    print("Total")
    print("Num buys:         ", (merged["event"] == "Buy").sum())
    print("Num sells:        ", (merged["event"] == "Sell").sum())
    print("Num trades:       ", len(merged))
    print("Traded volume:    ", merged["qty"].abs().sum())
    print()

    # calculate volume and pnl per account
    merged["volume"] = merged["qty"].abs()
    merged["buy_amount"] = np.maximum(-merged["pnl"], 0)
    merged["pnl_payoff"] = merged["pnl"] + merged["payoff"]
    accounts = merged.groupby("account")[["volume", "buy_amount", "pnl_payoff"]].sum()
    accounts["roi"] = accounts["pnl_payoff"] / accounts["buy_amount"]

    print(accounts["pnl_payoff"].sort_values(ascending=False).head(10))
    print()
    print(accounts["roi"].sort_values(ascending=False).head(10))
    print()


def _fetch_events(key, address, event_names):
    url = f"https://api.covalenthq.com/v1/1/events/address/{address}/?key={key}&starting-block=0&ending-block=99999999&page-size=1000000"
    resp = requests.get(url)
    data = resp.json()
    assert not data["data"]["pagination"]

    events = []
    for event in data["data"]["items"]:
        name = event["decoded"]["name"]
        if name in event_names:
            events.append({"event": name, "tx": event["tx_hash"], **{d["name"]: d["value"] for d in event["decoded"]["params"]}})
    return events


if __name__ == "__main__":
    fetch_market()
