"""Specialist agents return structured evidence assessments, never executable code."""
from copy import deepcopy
from dataclasses import asdict
from .models import Proposal, finite
from .strategies import candidates
from .risk import security_checks,approve,profile_feasibility
from .transport import DataError
from .prompts import PromptLibrary
from .finance import evidence_envelope

REPORT_SCHEMA = {'type':'object','additionalProperties':False,'properties':{
    'stance':{'type':'string','enum':['LONG','SHORT','HOLD','CLOSE']},
    'score':{'type':'number','minimum':0,'maximum':1},
    'summary':{'type':'string'},
    'evidence_keys':{'type':'array','items':{'type':'string'}},
    'concerns':{'type':'array','items':{'type':'string'}}},
    'required':['stance','score','summary','evidence_keys','concerns']}
DECISION_SCHEMA = {'type':'object','additionalProperties':False,'properties':{
    'action':{'type':'string','enum':['LONG','HOLD','CLOSE']},
    'market':{'type':'string','enum':['spot']},
    'confidence':{'type':'number','minimum':0,'maximum':1},
    'stop_fraction':{'type':'number','minimum':.005,'maximum':.1},
    'take_fraction':{'type':'number','minimum':.005,'maximum':.3},
    'horizon_bars':{'type':'integer','minimum':1,'maximum':96},
    'thesis':{'type':'string'},'strategy':{'type':'string'}},
    'required':['action','market','confidence','stop_fraction','take_fraction','horizon_bars','thesis','strategy']}


RISK_FLAGS = ['data_quality','costs','liquidity','concentration','model_uncertainty',
              'contradictory_evidence','unsupported_assumptions']
REPORT_SCHEMA['properties'].update({
    'missing_data':{'type':'array','items':{'type':'string'}},
    'invalidation':{'type':'string'},
    'risk_flags':{'type':'array','items':{'type':'string','enum':RISK_FLAGS}},
    'blocking':{'type':'boolean'},
    'score_is_probability':{'type':'boolean','enum':[False]}})
REPORT_SCHEMA['required']=list(REPORT_SCHEMA['properties'])
PLAN_FIELDS = {'evidence_keys','invalidation','entry_conditions','exit_conditions','counterevidence_keys'}
DECISION_SCHEMA['properties'].update({
    'evidence_keys':{'type':'array','items':{'type':'string'}},
    'invalidation':{'type':'string'},
    'entry_conditions':{'type':'array','items':{'type':'string'}},
    'exit_conditions':{'type':'array','items':{'type':'string','enum':[
        'configured_stop','configured_take','time_exit','signal_reversal','feed_failure']}},
    'counterevidence_keys':{'type':'array','items':{'type':'string'}}})
DECISION_SCHEMA['required']=list(DECISION_SCHEMA['properties'])

def validate_references(refs,allowed,required=False):
    if (not isinstance(refs,list) or len(refs)>20 or any(not isinstance(x,str) or len(x)>200 for x in refs)
            or len(refs)!=len(set(refs)) or set(refs)-set(allowed) or required and not refs):
        raise DataError('Referências de evidência inválidas ou ausentes')


def validate_report(r,allowed_keys):
    if not isinstance(r,dict) or set(r) != set(REPORT_SCHEMA['required']):
        raise DataError('Contrato de relatório inválido')
    if not isinstance(r['stance'],str) or r['stance'] not in {'LONG','SHORT','HOLD','CLOSE'}:
        raise DataError('Stance inválido')
    finite(r['score'],'report.score',0,1)
    if type(r['blocking']) is not bool or r['score_is_probability'] is not False:
        raise DataError('Bloqueio inválido ou score apresentado como probabilidade')
    for name in ['summary','invalidation']:
        if not isinstance(r[name],str) or not 1 <= len(r[name]) <= 2000:
            raise DataError('Resumo/invalidação inválidos')
    for name in ['concerns','missing_data','risk_flags']:
        if not isinstance(r[name],list) or len(r[name])>20 or any(not isinstance(x,str) or len(x)>500 for x in r[name]):
            raise DataError('Lista de relatório inválida')
    if set(r['risk_flags'])-set(RISK_FLAGS):
        raise DataError('Risco desconhecido')
    validate_references(r['evidence_keys'],allowed_keys,required=r['stance']!='HOLD')
    return r


class Council:
    def __init__(self,mode='external',prompts=None):
        if mode not in {'rules','external'}:
            raise ValueError('agent_mode deve ser external ou rules')
        self.mode=mode
        self.prompts=prompts or PromptLibrary()
        self.memory=[]

    def decide(self,f,s,book,cfg,now,submission=None):
        ideas=[]
        for p in candidates(f,s,cfg):
            existing=next((x for x in book.positions if x.market==p.market and x.mint==s.mint),None)
            side=1 if p.action=='LONG' else -1
            if existing is None:
                ideas.append(Proposal(**{**asdict(p),'mint':s.mint}))
            elif existing.side!=side:
                ideas.append(Proposal('CLOSE',p.market,p.confidence,p.stop_fraction,p.take_fraction,
                    p.horizon_bars,'Sinal quantitativo contrário à posição','signal_reversal',mint=s.mint))
        guard_reasons=security_checks(s,cfg,now)
        baseline=ideas[0] if ideas else Proposal(thesis='Sem confluência suficiente',mint=s.mint)
        audit=dict(mode=self.mode,protocol='external-session-v2' if self.mode=='external' else 'deterministic-rules',
                   candidates=[asdict(p) for p in ideas],security_reasons=guard_reasons,reports={})
        if not f.get('ready') or guard_reasons or book.halted:
            audit['gate']='precheck_abstention'
            return Proposal(thesis='Dados insuficientes ou bloqueio de segurança',mint=s.mint),audit
        if self.mode=='rules':
            audit['reports']={
                'market':{'regime':f['regime'],'score':baseline.confidence},
                'quality':{'warnings':list(s.warnings),'checks_passed':True},
                'flow':{'organic_score':s.organic_score,'imbalance':s.buy_sell_imbalance},
                'challenger':{'concerns':['Scores não calibrados','Alladin aceita somente Solana spot paper']},
                'manager':asdict(baseline)}
            return baseline,audit
        def abstain(reason,gate):
            audit['gate']=gate
            return Proposal(thesis=reason,mint=s.mint),audit
        try:
            audit['prompt_pack']=self.prompts.metadata(f.get('regime'))
            evidence=evidence_envelope(f,s,book,cfg,ideas,now,self.memory)
            audit['evidence_sha256']=evidence['evidence_sha256']
            audit['candidate_economics']=evidence['candidate_economics']
            held=any(pos.mint==s.mint and pos.market=='spot' for pos in book.positions)
            admissible=[row for row in evidence['candidate_economics'] if row['approval']['approved']]
            if not held and not ideas:
                return abstain('Sem sinal quantitativo; permanecer em caixa','signal_abstention')
            if not held and not admissible:
                audit['profile_feasibility']=profile_feasibility(cfg)
                return abstain('Nenhum candidato aprovado por risco e custos','economic_abstention')
            allowed=set(evidence['evidence_registry'])
            if submission is None:
                audit['task'] = dict(evidence=evidence,report_schema=deepcopy(REPORT_SCHEMA),
                    decision_schema=deepcopy(DECISION_SCHEMA),
                    instructions={role:self.prompts.render(role,f.get('regime'))
                                  for role in sorted(PromptLibrary.ROLES)},
                    stages=[['market','quality','flow'],['challenger'],['manager']])
                return abstain('Aguardando decisão dos agentes da sessão externa','awaiting_external_agents')
            if not isinstance(submission,dict) or set(submission)!={'reports','decision'}:
                raise DataError('Submissão exige reports e decision')
            reports=submission['reports']
            if not isinstance(reports,dict) or set(reports)!={'market','quality','flow','challenger'}:
                raise DataError('Quatro pareceres externos obrigatórios')
            for name in ['market','quality','flow','challenger']:
                audit['reports'][name]=validate_report(deepcopy(reports[name]),allowed)
            vetoes=[name for name,r in audit['reports'].items() if r['blocking']]
            audit['vetoes']=vetoes
            if vetoes and not held:
                return abstain('Analista bloqueou a entrada: '+','.join(vetoes),'analyst_veto')
            decision=deepcopy(submission['decision'])
            if not isinstance(decision,dict) or set(decision)!=set(DECISION_SCHEMA['required']):
                raise DataError('Contrato de decisão inválido')
            p=Proposal(**{k:v for k,v in decision.items() if k not in PLAN_FIELDS},mint=s.mint)
            directional=p.action in {'LONG','CLOSE'}
            validate_references(decision['evidence_keys'],allowed,required=directional)
            validate_references(decision['entry_conditions'],allowed,required=p.action=='LONG')
            validate_references(decision['counterevidence_keys'],allowed)
            if not isinstance(decision['invalidation'],str) or not 1<=len(decision['invalidation'])<=2000:
                raise DataError('Invalidação de tese obrigatória')
            exits=decision['exit_conditions']
            allowed_exits=set(DECISION_SCHEMA['properties']['exit_conditions']['items']['enum'])
            if not isinstance(exits,list) or any(not isinstance(x,str) or x not in allowed_exits for x in exits) or len(exits)>10:
                raise DataError('Condições de saída inválidas')
            audit['reports']['manager']=decision
            if p.action=='CLOSE' and not held:
                raise DataError('Não há posição para encerrar')
            if p.action=='LONG':
                if 'configured_stop' not in exits:
                    raise DataError('Entrada sem stop obrigatório')
                if not any(k.startswith('features.') for k in decision['evidence_keys']) or not any(k.startswith('snapshot.') for k in decision['evidence_keys']):
                    raise DataError('Entrada exige evidência de mercado fechado e snapshot')
                if not any(p.action==x['action'] and p.market==x['market'] and p.strategy==x['strategy'] for x in admissible):
                    raise DataError('Decisão de entrada sem candidato econômico aprovado')
                contrary=[name for name,r in audit['reports'].items() if name!='manager' and r['stance'] in {'SHORT','CLOSE'}]
                supports=sum(audit['reports'][name]['stance']=='LONG' and audit['reports'][name]['score']>=cfg.min_confidence for name in ['market','quality','flow'])
                if vetoes or contrary or supports<2:
                    return abstain('Conselho sem consenso independente para entrada','consensus_abstention')
                check=approve(p,f,s,book,cfg,now,s.price)
                audit['risk_recheck']=asdict(check)
                if not check.approved:
                    return abstain('Gestor alterou o plano além do risco permitido','manager_risk_veto')
            return p,audit
        except (DataError,ValueError,KeyError,TypeError) as exc:
            audit['error']=str(exc)[:200]
            return Proposal(thesis='Submissão externa inválida: abstenção',mint=s.mint),audit
