"""Read-only Solana collectors. No signer or sendTransaction method exists."""
import os
import time
from dataclasses import asdict
from urllib.parse import urlencode
from .models import SOL, USDC, TOKEN_PROGRAM, MAINNET_GENESIS, Snapshot, pubkey, finite
from .transport import HTTP, DataError

class SolanaRPC:
    ALLOWED = {'getGenesisHash','getAccountInfo','getTokenSupply','getTokenLargestAccounts',
               'getSlot','getBalance','getSignaturesForAddress','getRecentPerformanceSamples'}
    def __init__(self,http=None,url=None):
        self.http = http or HTTP()
        self.url = url or os.environ.get('SOLANA_RPC_URL','https://api.mainnet-beta.solana.com')
    def call(self,method,params=None):
        if method not in self.ALLOWED:
            raise DataError('Método RPC não permitido')
        d = self.http.json(self.url,{'jsonrpc':'2.0','id':1,'method':method,'params':params or []})
        if not isinstance(d,dict) or d.get('error') or 'result' not in d:
            raise DataError(f'RPC {method} falhou; detalhes omitidos')
        return d['result']
    def verify(self):
        if self.call('getGenesisHash') != MAINNET_GENESIS:
            raise DataError('RPC não pertence à Solana mainnet')
    def inspect(self,mint):
        pubkey(mint)
        self.verify()
        account = self.call('getAccountInfo',[mint,{'encoding':'jsonParsed','commitment':'finalized'}])
        value = account.get('value')
        if not isinstance(value,dict) or value.get('owner') != TOKEN_PROGRAM:
            raise DataError('Somente mint SPL clássico é suportado; Token-2022 recusado')
        parsed = value.get('data',{}).get('parsed',{})
        info = parsed.get('info',{})
        if parsed.get('type') != 'mint' or info.get('isInitialized') is not True:
            raise DataError('Conta não é um mint inicializado')
        if 'mintAuthority' not in info or 'freezeAuthority' not in info:
            raise DataError('Autoridades não informadas')
        supply = self.call('getTokenSupply',[mint,{'commitment':'finalized'}])
        largest = self.call('getTokenLargestAccounts',[mint,{'commitment':'finalized'}])
        total = int(supply['value']['amount'])
        if total < 0:
            raise DataError('Supply inválido')
        # wSOL supply is not a meaningful holder concentration denominator.
        share = None if mint == SOL or total == 0 else min(1,sum(int(a['amount']) for a in largest['value'][:10])/total)
        return dict(mint=mint,chain='solana',token_program=value['owner'],
                    mint_authority=info['mintAuthority'],freeze_authority=info['freezeAuthority'],
                    decimals=info['decimals'],supply_raw=str(total),top10_account_share=share,
                    account_checked=True,cluster_verified=True,slot=account['context']['slot'],
                    warnings=['Top accounts não equivalem a holders: pools e custodians não classificados.'])
    def wallet(self,address):
        pubkey(address)
        self.verify()
        balance = self.call('getBalance',[address,{'commitment':'finalized'}])
        signatures = self.call('getSignaturesForAddress',[address,{'limit':20,'commitment':'finalized'}])
        return dict(chain='solana',address=address,sol_balance=balance['value']/1e9,
                    signatures=signatures,slot=balance['context']['slot'])

class DexScreener:
    def __init__(self,http=None):
        self.http = http or HTTP()
    def market(self,mint):
        pubkey(mint)
        pairs = self.http.json(f'https://api.dexscreener.com/token-pairs/v1/solana/{mint}')
        if not isinstance(pairs,list):
            raise DataError('Resposta de pools inválida')
        # Keep a USDC quoted Solana pool with the requested BASE mint.
        valid = [p for p in pairs if p.get('chainId') == 'solana'
                 and p.get('baseToken',{}).get('address') == mint
                 and p.get('quoteToken',{}).get('address') == USDC
                 and p.get('priceNative') and (p.get('liquidity') or {}).get('usd')]
        if not valid:
            raise DataError('Nenhuma pool Solana com base solicitada e cotação USDC')
        p = max(valid,key=lambda p:float(p['liquidity']['usd']))
        tx = (p.get('txns') or {}).get('h1',{})
        buys, sells = tx.get('buys',0), tx.get('sells',0)
        return dict(price=float(p['priceNative']),liquidity_usd=float(p['liquidity']['usd']),
                    volume_24h_usd=float((p.get('volume') or {}).get('h24',0)),
                    buy_sell_imbalance=(buys-sells)/(buys+sells) if buys+sells else 0,
                    pair=p.get('pairAddress'),dex=p.get('dexId'),source='dexscreener_pool_usdc')

class JupiterQuotes:
    def __init__(self,http=None):
        self.http = http or HTTP()
    def quote(self,input_mint,output_mint,amount,slippage_bps=50):
        pubkey(input_mint); pubkey(output_mint)
        if {input_mint,output_mint} != {SOL,USDC}:
            raise DataError('Quote v0.2 restrito a SOL/USDC na Solana')
        if type(amount) is not int or amount <= 0 or amount > 10**15:
            raise DataError('amount deve ser inteiro em unidades raw')
        if type(slippage_bps) is not int or not 1 <= slippage_bps <= 100:
            raise DataError('slippage_bps fora do limite')
        key = os.environ.get('JUPITER_API_KEY')
        if not key:
            raise DataError('JUPITER_API_KEY necessária para cotação; não é chave da carteira')
        query = urlencode(dict(inputMint=input_mint,outputMint=output_mint,amount=amount,
                               slippageBps=slippage_bps,swapMode='ExactIn',restrictIntermediateTokens='true'))
        d = self.http.json('https://api.jup.ag/swap/v1/quote?'+query,headers={'x-api-key':key})
        if d.get('inputMint') != input_mint or d.get('outputMint') != output_mint or int(d.get('inAmount',0)) != amount:
            raise DataError('Quote não corresponde à solicitação')
        if not d.get('routePlan') or int(d.get('outAmount',0)) <= 0:
            raise DataError('Rota vazia')
        return d  # quote only; never constructs or broadcasts a transaction

def collect(mint=SOL,rpc=None,dex=None):
    # Timestamp is acquisition completion; source exchange timestamp unavailable.
    r = (rpc or SolanaRPC()).inspect(mint)
    m = (dex or DexScreener()).market(mint)
    return Snapshot(timestamp=int(time.time()),mint=mint,price=m['price'],
                    liquidity_usd=m['liquidity_usd'],volume_24h_usd=m['volume_24h_usd'],
                    buy_sell_imbalance=m['buy_sell_imbalance'],mint_authority=r['mint_authority'],
                    freeze_authority=r['freeze_authority'],top10_account_share=r['top10_account_share'],
                    token_program=r['token_program'],account_checked=True,cluster_verified=True,
                    source=m['source'],slot=r['slot'],warnings=tuple(r['warnings']+[
                        'Preço indexado: frescor da pool não comprovado pelo horário de aquisição.',
                        'Sem oracle/funding de perp: novas posições perp são bloqueadas.']))
