import brownie
import click
import requests


# keccak tool: https://emn178.github.io/online-tools/keccak_256.html

# keccak("Burn(address,int24,int24,uint128,uint256,uint256)")
BURN_TOPIC = "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"

# keccak("Collect(address,address,int24,int24,uint128,uint128)")
COLLECT_TOPIC = "0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0"

# keccak("Rebalance(int24,uint256,uint256,uint256)")
REBALANCE_TOPIC = "0xc73adb760e747dc4ed7b1c9e0c0cd134b745cd3e73f971c94f1a35ddfe47343c"

DECIMAL0 = 6
DECIMAL1 = 18


@click.command()
@click.option("-k", "--key", required=True, help="Covalent api key")
@click.option("-a", "--address", required=True)
def fetch_fees(key, address):
    brownie.network.connect("mainnet")

    burns = {}
    collects = {}

    for ev in _fetch_events(key, address, brownie.web3.eth.blockNumber):
        if ev["raw_log_topics"][0] == REBALANCE_TOPIC:
            tx = _fetch_tx(key, ev["tx_hash"])
            for ev2 in tx["log_events"]:
                topic = ev2["raw_log_topics"][0]
                data = ev2["raw_log_data"][2:]
                if topic == BURN_TOPIC:
                    assert len(data) == 192
                    amount0 = int(data[64:128], 16) / 10 ** DECIMAL0
                    amount1 = int(data[128:192], 16) / 10 ** DECIMAL1
                    burns[tx["block_signed_at"]] = amount0, amount1

                elif topic == COLLECT_TOPIC:
                    assert len(data) == 192
                    amount0 = int(data[64:128], 16) / 10 ** DECIMAL0
                    amount1 = int(data[128:192], 16) / 10 ** DECIMAL1
                    collects[tx["block_signed_at"]] = amount0, amount1

    for k in burns:
        fee0 = collects[k][0] - burns[k][0]
        fee1 = collects[k][1] - burns[k][1]
        print(f"{k}\t{fee0:.3f} USDC\t{fee1:.6f} ETH")


def _fetch_events(key, address, block_height):
    url = f"https://api.covalenthq.com/v1/1/events/address/{address}/?key={key}&starting-block={block_height-999999}&ending-block={block_height}&page-size=999999"
    resp = requests.get(url)
    data = resp.json()
    assert not data["data"]["pagination"]
    return data["data"]["items"]


def _fetch_tx(key, tx_hash):
    url = f"https://api.covalenthq.com/v1/1/transaction_v2/{tx_hash}/?key={key}"
    resp = requests.get(url)
    data = resp.json()
    assert not data["data"]["pagination"]
    (tx,) = data["data"]["items"]
    return tx


if __name__ == "__main__":
    fetch_fees()
