from web3 import Web3
import time
import random
from decimal import Decimal
from loguru import logger
from tqdm import tqdm
from sys import stderr
from config import *

logger.remove()
logger.add(stderr, format="<lm>{time:YYYY-MM-DD HH:mm:ss}</lm> | <level>{level: <8}</level>| <lw>{message}</lw>")

web3 = Web3(Web3.HTTPProvider('https://rpc.ankr.com/bsc'))
w3 = Web3(Web3.HTTPProvider('https://bscrpc.com'))
panRouterContractAddress = Web3.to_checksum_address('0x10ED43C718714eb63d5aA57B78B54704E256024E') 
ageurContract = Web3.to_checksum_address('0x12f31b73d812c6bb0d735a218c086d44d5fe5f89')
bridgeContract = Web3.to_checksum_address('0xe9f183fc656656f1f17af1f2b0df79b8ff9ad8ed')
ageurProxyContract = Web3.to_checksum_address('0x3e399ae5b4d8bc0021e53b51c8bcdd66dd62c03b')
number_wallets = 0


def pancakeSwap(private_key):
    try:
        address_wallet = web3.eth.account.from_key(private_key).address
        contract = web3.eth.contract(address=panRouterContractAddress, abi=panabi)
        valueRandom = round(random.uniform(minAmount, maxAmount), 7)
        logger.info(f'Swap {valueRandom} BNB to agEUR via PancakeSwap')
        pancakeswap2_txn = contract.functions.swapExactETHForTokens(0, [Web3.to_checksum_address('0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'), Web3.to_checksum_address('0x55d398326f99059ff775485246999027b3197955'), ageurContract], address_wallet, (int(time.time()) + 3000000)).build_transaction({
            'from': address_wallet,
            'value': web3.to_wei(valueRandom,'ether'),
            'gas': 400000,
            'gasPrice': Web3.to_wei(1.1, 'gwei'),
            'nonce': web3.eth.get_transaction_count(address_wallet),
        })
        signed_tx = web3.eth.account.sign_transaction(pancakeswap2_txn, private_key)
        raw_tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hash = web3.to_hex(raw_tx_hash)
        
        tx_receipt = web3.eth.wait_for_transaction_receipt(raw_tx_hash, timeout=900)
        if tx_receipt.status == 1:
            logger.success(f'BNB swap done https://bscscan.com/tx/{tx_hash}')
        else:
            time.sleep(120)
            tx_receipt = web3.eth.get_transaction_receipt(tx_hash)
            status = tx_receipt.status
            if status == 1:
                logger.success(f'BNB swap done https://bscscan.com/tx/{tx_hash}')
            else:
                balance = getBalanceAGEUR(address_wallet)
                if balance > 0:
                    logger.success(f'BNB swap done https://bscscan.com/tx/{tx_hash}')
                else:
                    logger.error(f'Swap {valueRandom} BNB to agEUR failed')
        time.sleep(10)
        balance = getBalanceAGEUR(address_wallet)
        return balance
    
    except Exception as error:
        logger.error(f"Pancakeswap function failed: {error}")
        return 0

def getAGEUR(private_key):
    try:
        address_wallet = web3.eth.account.from_key(private_key).address
        balance = getBalanceAGEUR(address_wallet)
        if balance == 0:
            try:
                balance = pancakeSwap(private_key)
                if balance > 0:
                    return True
                else:
                    time.sleep(60)
                    if getBalanceAGEUR(address_wallet) > 0:
                        return True
                    else:
                        logger.error(f'Balance of agEUR = 0 even though pancakeSwap function called')
                        return False
            except Exception as error:
                logger.error(error)
                return False 
        else:
            balanceGwei = round(web3.from_wei(balance, 'ether'), 4)
            logger.info(f'agEUR balance = {balanceGwei}')
            return True
    
    except Exception as error:
        logger.error(error)
        return False
        
def getBalanceAGEUR(address):
    try:
        ageurToken = web3.eth.contract(address=ageurContract, abi=ageurProxyAbi)
        ageurBalance = ageurToken.functions.balanceOf(address).call()
        return ageurBalance
    
    except Exception as error:
        logger.error(error)
        return 0
        
def getLayerzeroFees(address, dstChainId):
    contract_data = web3.eth.contract(address=bridgeContract, abi=bridgeAbi)
    ageurToken = web3.eth.contract(address=ageurContract, abi=ageurProxyAbi)
    _adapterParams = "0x00010000000000000000000000000000000000000000000000000000000000030d40"
    fees = contract_data.functions.estimateSendFee(dstChainId, address, ageurToken.functions.balanceOf(address).call(), True, _adapterParams).call()
    fee = int(fees[0]) * int(1.02)
    return fee
    
def setApprove(private_key):
    address_wallet = web3.eth.account.from_key(private_key).address
    amount = getBalanceAGEUR(address_wallet)
    if amount > 0:
        try:
            ageurTokenContract = web3.eth.contract(address=ageurContract, abi=ageurProxyAbi)
            allowance = ageurTokenContract.functions.allowance(Web3.to_checksum_address(address_wallet), bridgeContract).call()
            if allowance < amount:
                approveTX = ageurTokenContract.functions.approve(bridgeContract, amount).build_transaction({
                    'chainId': 56,
                    'value': 0,
                    'from': address_wallet,
                    'gas': 200000,
                    'gasPrice': Web3.to_wei(1.1, 'gwei'),
                    'nonce': web3.eth.get_transaction_count(address_wallet)
                    })
                signed_tx = web3.eth.account.sign_transaction(approveTX, private_key)
                raw_tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                tx_hash = web3.to_hex(raw_tx_hash)
                
                tx_receipt = web3.eth.wait_for_transaction_receipt(raw_tx_hash, timeout=900)
                if tx_receipt.status == 1:
                    logger.success(f'Approved agEUR to bridge - https://bscscan.com/tx/{tx_hash}')
                else:
                    time.sleep(120)
                    tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
                    status = tx_receipt.status
                    if status == 1:
                        logger.success(f'Approved agEUR to bridge - https://bscscan.com/tx/{tx_hash}')
                    else:
                        logger.error(f'Approve agEUR for bridge failed: tx https://bscscan.com/tx/{tx_hash}\n')
        except Exception as error:
            logger.error(error)
    else:
        logger.error(f'agEUR amount = 0 Nothing to approve')

def ageurBridge(private_key, amount, dstChainId, chainName):
    try:
        address_wallet = web3.eth.account.from_key(private_key).address
        valueLZ0 = getLayerzeroFees(address_wallet, dstChainId)
        _zroPaymentAddress = '0x0000000000000000000000000000000000000000'
        _adapterParams = "0x00010000000000000000000000000000000000000000000000000000000000030d40"
        contract_data = web3.eth.contract(address=bridgeContract, abi=bridgeAbi)

        bridge_txn = contract_data.functions.send(dstChainId, address_wallet, amount, address_wallet, _zroPaymentAddress, _adapterParams).build_transaction({
            'chainId': 56,
            'value': valueLZ0,
            'from': address_wallet,
            'gas': 400000,
            'gasPrice': Web3.to_wei(1.1, 'gwei'),
            'nonce': web3.eth.get_transaction_count(address_wallet)
        })
        
        signed_tx = web3.eth.account.sign_transaction(bridge_txn, private_key)
        raw_tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hash = web3.to_hex(raw_tx_hash)
        
        tx_receipt = web3.eth.wait_for_transaction_receipt(raw_tx_hash, timeout=900)
        agEURgwei = round(web3.from_wei(amount, 'ether'), 4)
        if tx_receipt.status == 1:
            logger.success(f'Bridge {agEURgwei} agEUR to {chainName} chain success - https://bscscan.com/tx/{tx_hash}')
            return 1
        else:
            time.sleep(120)
            tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
            status = tx_receipt.status
            if status == 1:
                logger.success(f'Bridge {agEURgwei} agEUR to {chainName} chain success - https://bscscan.com/tx/{tx_hash}')
                return 1
            else:
                logger.error(f'Bridge {agEURgwei} agEUR failed: tx {tx_receipt.status}')
                return 0

    except Exception as error:
        logger.error(error)
        return 0


if __name__ == '__main__':
    print()
    print('This script will buy agEUR worth ~0.1$ and bridge it to Gnosis and Celo chains:')
    print()

    with open("private_key.txt", "r") as f:
        keys_list = [row.strip() for row in f]
        
    count_wallets = len(keys_list)

    while keys_list:
        key = keys_list.pop(0)
        address_wallet = web3.eth.account.from_key(key).address
        number_wallets += 1
        print(f'{number_wallets}/{count_wallets} - {address_wallet}\n')
        if getAGEUR(key):
            time.sleep(10)
            setApprove(key)
            time.sleep(10)
            amount = int(getBalanceAGEUR(address_wallet) / 2)
            txnumber = web3.eth.get_transaction_count(address_wallet)
            if ageurBridge(key, amount, 125, 'Celo') == 1 and web3.eth.get_transaction_count(address_wallet) == txnumber:
                time.sleep(60) # prevent errors like {'code': -32000, 'message': 'nonce too low'}
            else:
                time.sleep(30)
            amount = getBalanceAGEUR(address_wallet)
            ageurBridge(key, amount, 145, 'Gnosis')
        else:
            logger.error(f'Failed to get balance or swap. Skiped this account.')
        sleepDelay = random.randint(time_delay_min, time_delay_max)
        for i in tqdm(range(sleepDelay), desc='sleep ', bar_format='{desc}: {n_fmt}/{total_fmt}'):
            time.sleep(1)
        print()
    print('Done!')
