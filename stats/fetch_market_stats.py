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
        underlying_price = contract.expiryPrice() * 1e-18
        if underlying_price == 0:
            print("Warning! Not settled yet so using current underlying price")
            oracle = brownie.Contract.from_explorer(contract.oracle())
            underlying_price = oracle.getPrice() * 1e-18

        mult = 1 if is_put else underlying_price

        # fetch trades
        events = _fetch_events(key, addr, EVENT_NAMES, brownie.web3.eth.blockNumber)
        df = pd.DataFrame(events)
        print(events)

        if "isSettled" not in df.columns:
            df["isSettled"] = False
        for col in ["amountIn", "amountOut", "optionsIn", "optionsOut", "sharesIn", "sharesOut"]:
            if col not in df.columns:
                df[col] = 0.0

        df = df[~df["isSettled"].fillna(False)]

        df["is_lp"] = df["event"].isin(["Deposit", "Withdraw"])
        df["is_trade"] = df["event"].isin(["Buy", "Sell"])
        df["strike"] = df["strikeIndex"].map(lambda i: 0 if pd.isnull(i) else strikes[int(i)])

        def to_float(x):
            return x.fillna(0).astype(float) / (10 ** decimals)

        # calculate trade quantities and pnls
        df["qty"] = np.where(df["is_trade"], to_float(df["optionsOut"]) - to_float(df["optionsIn"]), 0)
        df["lp_qty"] = np.where(df["is_lp"], to_float(df["sharesOut"]) - to_float(df["sharesIn"]), 0)
        df["pnl"] = mult * np.where(df["is_trade"], to_float(df["amountOut"]) - to_float(df["amountIn"]), 0)
        df["lp_amount"] = mult * np.where(df["is_lp"], to_float(df["amountIn"]) - to_float(df["amountOut"]), 0)
        df["base_qty"] = df["qty"] * df["strike"] if is_put else df["qty"]

        # calculate option payoffs
        call_payoff = np.maximum(0, underlying_price - df["strike"])
        put_payoff = np.maximum(0, df["strike"] - underlying_price)
        short_payoff = np.minimum(underlying_price, df["strike"])
        long_payoff = put_payoff if is_put else call_payoff
        df["payoff"] = df["qty"] * np.where(df["isLongToken"], long_payoff, short_payoff)

        # calculate lp payoffs
        tvl = mult * (to_float(df["amountIn"]).sum() - to_float(df["amountOut"]).sum())
        lp_payoff = tvl - df["payoff"].sum()
        lp_shares = df["lp_qty"].sum()
        df["lp_payoff"] = df["lp_qty"] * lp_payoff / lp_shares

        dfs.append(df)

        # print stats
        print(addr)
        _print_stats(df)
        print()

    # print total stats
    merged = pd.concat(dfs)
    print("Total")
    _print_stats(merged)
    print()

    # calculate volume and pnl per account
    merged["volume"] = merged["qty"].abs()
    merged["buy_amount"] = np.maximum(-merged["pnl"], 0)
    merged["pnl_payoff"] = merged["pnl"] + merged["payoff"]
    accounts = merged.groupby("account")[["volume", "buy_amount", "lp_amount", "pnl_payoff", "lp_payoff"]].sum()
    accounts["roi"] = accounts["pnl_payoff"] / accounts["buy_amount"]
    accounts["lp_yield"] = accounts["lp_payoff"] / accounts["lp_amount"]

    # print leaderboards
    print(accounts["pnl_payoff"].sort_values(ascending=False).head(21))
    print()
    print(accounts["roi"].sort_values(ascending=False).head(21))
    print()
    print(accounts["lp_yield"][accounts["lp_amount"] != 0].sort_values(ascending=False).head(21))
    print()
    print(accounts["lp_payoff"][accounts["lp_amount"] != 0].sort_values(ascending=False).head(21))
    print()
    print(accounts["lp_amount"][accounts["lp_amount"] != 0].sort_values(ascending=False).head(21))
    print()


def _print_stats(df):
    print("Num buys:           ", (df["event"] == "Buy").sum())
    print("Num sells:          ", (df["event"] == "Sell").sum())
    print("Num trades:         ", (df["event"].isin(["Buy", "Sell"])).sum())
    print("Contracts traded:   ", df["qty"].abs().sum())
    print("Volume traded:      ", df["base_qty"].abs().sum())
    print("Fees earned:        ", df["base_qty"][df["event"] == "Buy"].sum() * 0.01)
    print("Median trade size:  ", df["qty"][df["qty"] != 0].abs().median())


def _fetch_events(key, address, event_names, block_height):
    url = f"https://api.covalenthq.com/v1/1/events/address/{address}/?key={key}&starting-block={block_height-999999}&ending-block={block_height}&page-size=999999"
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
