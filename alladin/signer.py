"""Assinatura fora do contexto do modelo. Sem seed, sem reenvio."""

FORBIDDEN = {'private_key', 'secret', 'seed', 'keypair', 'mnemonic'}

class IsolatedSigner:
    def __init__(self, submit):
        if not callable(submit):
            raise ValueError('Signer exige função de submissão injetada')
        self.submit = submit
        self.calls = 0
    def execute(self, intent):
        if not isinstance(intent, dict):
            raise ValueError('Intenção inválida')
        keys = {k.lower() for k in intent}
        if keys & FORBIDDEN:
            raise ValueError('Intenção não pode carregar segredo')
        if intent.get('simulated') is not True:
            raise ValueError('Simulação obrigatória antes da submissão')
        allowed = {'mint', 'side', 'notional', 'price', 'simulated', 'market'}
        if set(intent) - allowed:
            raise ValueError('Intenção tem campo fora do contrato')
        self.calls += 1
        result = self.submit(dict(intent))
        if not isinstance(result, dict) or result.get('status') not in {'confirmed', 'rejected', 'unknown'}:
            return dict(status='unknown')
        if result['status'] == 'confirmed' and not result.get('signature'):
            return dict(status='unknown')
        return dict(status=result['status'], signature=result.get('signature'), price=result.get('price'))
