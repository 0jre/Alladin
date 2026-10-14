"""External session protocol. No provider SDK, credentials or inference requests."""
import hashlib
from .storage import canonical

BINDING_VERSION = 2


def context_hash(state):
    """Bind account authority, not observations produced by the market worker.

    Stops, peak equity and marks are rechecked against the current account at
    execution. Updating those observations must not replace a pending analysis.
    Cash, position identity/size, fills, configuration and permissions do.
    """
    portfolio=state.get('portfolio',{})
    position_fields=('id','market','side','qty','entry','opened_at','expires_at','strategy','mint')
    material={key:state.get(key) for key in (
        'config_hash','agent_mode','input_mode','universe','blocked_mints',
        'pending','pending_book','execution_check')}
    material['portfolio']={key:portfolio.get(key) for key in (
        'cash','initial','halted','halt_reason','cooldown_until','total_closed','fees_paid')}
    material['portfolio']['positions']=[{key:p.get(key) for key in position_fields}
                                        for p in portfolio.get('positions',[])]
    return hashlib.sha256(canonical(material).encode()).hexdigest()


def task_is_current(task,state,now):
    return bool(task and task.get('protocol')=='external-session-v2'
                and task.get('binding_version')==BINDING_VERSION
                and task.get('status')=='prepared'
                and task['created_at']-5<=now<=task['expires_at']
                and task['context_sha256']==context_hash(state))
