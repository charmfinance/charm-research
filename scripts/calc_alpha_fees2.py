import brownie
import click
import requests


# keccak tool: https://emn178.github.io/online-tools/keccak_256.html

# keccak("CollectFees(uint256,uint256,uint256,uint256)")
COLLECT_FEES_TOPIC = "0x1ac56d7e866e3f5ea9aa92aa11758ead39a0a5f013f3fefb0f47cb9d008edd27"

DECIMAL0 = 18
DECIMAL1 = 6


@click.command()
@click.option("-k", "--key", required=True, help="Covalent api key")
@click.option("-a", "--address", required=True)
def fetch_fees(key, address):
    brownie.network.connect("mainnet")

    for ev in _fetch_events(key, address, brownie.web3.eth.blockNumber):
        if ev["raw_log_topics"][0] == COLLECT_FEES_TOPIC:
            data = ev["raw_log_data"][2:]
            assert len(data) == 256
            fees0 = int(data[:64], 16) / 10 ** DECIMAL0
            fees1 = int(data[64:128], 16) / 10 ** DECIMAL1
            # protocolFees0 = int(data[128:192], 16) / 10 ** DECIMAL0
            # protocolFees1 = int(data[192:], 16) / 10 ** DECIMAL1
            print(f"{ev['block_signed_at']}\t{fees0:.3f} ETH\t{fees1:.6f} USDT")



def _fetch_events(key, address, block_height):
    url = f"https://api.covalenthq.com/v1/1/events/address/{address}/?key={key}&starting-block={block_height-999999}&ending-block={block_height}&page-size=999999"
    resp = requests.get(url)
    data = resp.json()
    assert not data["data"]["pagination"]
    return data["data"]["items"]


if __name__ == "__main__":
    fetch_fees()

