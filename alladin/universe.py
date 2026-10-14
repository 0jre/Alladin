"""Research mint funnel: observe, classify, admit. Does not submit orders."""
import struct
from .models import SOL, TOKEN_PROGRAM, TOKEN_2022

# spl-token-2022 ExtensionType, repr(u16), ordem do enum oficial.
EXTENSIONS = {
    1: 'transfer_fee',
    6: 'default_account_state',
    9: 'non_transferable',
    12: 'permanent_delegate',
    14: 'transfer_hook',
    26: 'pausable',
}
DANGEROUS = {'non_transferable', 'permanent_delegate', 'pausable', 'default_frozen'}
ACCOUNT_TYPE_INDEX = 165
TLV_START = 166
MINT_ACCOUNT_TYPE = 1
FROZEN_STATE = 2

def seed_primary(mint):
    return dict(mint=mint, status='negotiable', reasons=[], program='anchor',
                extensions=[], updated_at=0)

def decode_mint_account(data):
    """Decode a historical SPL/Token-2022 mint; unknown extensions fail explicitly."""
    if not isinstance(data, (bytes, bytearray)) or len(data) < 82:
        raise ValueError('Mint account is too short')
    if data[45] != 1:
        raise ValueError('Mint is not initialized')
    decimals = data[44]
    if not 0 <= decimals <= 18:
        raise ValueError('Invalid decimals')
    mint_authority = data[4:36] if int.from_bytes(data[0:4], 'little') else None
    freeze_authority = data[50:82] if int.from_bytes(data[46:50], 'little') else None
    if len(data) == 82:
        return dict(decimals=decimals, mint_authority=mint_authority, freeze_authority=freeze_authority,
                    extensions=(), extensions_decoded=True, transfer_fee_bps=None)
    if len(data) < TLV_START or data[ACCOUNT_TYPE_INDEX] != MINT_ACCOUNT_TYPE:
        raise ValueError('Token-2022 mint AccountType is missing at offset 165')
    if any(data[82:ACCOUNT_TYPE_INDEX]):
        raise ValueError('Token-2022 mint padding is nonzero')
    extensions = []
    transfer_fee_bps = None
    start = TLV_START
    raw = bytes(data)
    while start + 4 <= len(raw):
        typ, length = struct.unpack_from('<HH', raw, start)
        value_end = start + 4 + length
        if typ == 0 or value_end > len(raw):
            break
        value = raw[start + 4:value_end]
        name = EXTENSIONS.get(typ)
        if name is None:
            raise ValueError(f'Undecoded Token-2022 extension: {typ}')
        if name == 'default_account_state' and value and value[0] == FROZEN_STATE:
            name = 'default_frozen'
        if name == 'transfer_fee' and len(value) >= 2:
            transfer_fee_bps = int.from_bytes(value[:2], 'little')
        extensions.append(name)
        start = value_end
    return dict(decimals=decimals, mint_authority=mint_authority, freeze_authority=freeze_authority,
                extensions=tuple(extensions), extensions_decoded=True, transfer_fee_bps=transfer_fee_bps)

def admission_reasons(s, cfg):
    reasons = []
    if s.chain != 'solana':
        reasons.append('wrong_chain')
    if not s.account_checked or not s.cluster_verified:
        reasons.append('unverified_onchain_data')
    if s.token_program not in {TOKEN_PROGRAM, TOKEN_2022}:
        reasons.append('unsupported_token_program')
    if s.token_program == TOKEN_2022 and not s.extensions_decoded:
        reasons.append('token2022_extensions_not_decoded')
    names = set(s.extensions)
    if names & DANGEROUS:
        reasons.append('dangerous_token2022_extension')
    if 'transfer_hook' in names:
        reasons.append('unknown_transfer_hook')
    if 'transfer_fee' in names and not cfg.allow_transfer_fee:
        reasons.append('transfer_fee_blocked')
    if s.mint not in cfg.authority_exceptions and s.mint != SOL:
        if s.mint_authority is not None or s.freeze_authority is not None:
            reasons.append('active_token_authority')
    if s.mint != SOL and (s.top10_account_share is None or s.top10_account_share > cfg.max_top10_account_share):
        reasons.append('holder_concentration_unknown_or_high')
    if s.liquidity_usd < cfg.min_liquidity_usd:
        reasons.append('insufficient_liquidity')
    if s.volume_24h_usd < cfg.min_volume_24h_usd:
        reasons.append('insufficient_volume')
    if s.mint != SOL and not (s.sell_simulated and s.route_buy and s.route_sell):
        reasons.append('exit_route_not_proven')
    return reasons

def classify_snapshot(s, cfg):
    reasons = admission_reasons(s, cfg)
    if not s.account_checked or not s.cluster_verified:
        status = 'observed'
    elif reasons:
        status = 'classified'
    else:
        status = 'eligible'
    return dict(mint=s.mint, status=status, reasons=reasons, program=s.token_program,
                extensions=list(s.extensions), updated_at=s.timestamp)
