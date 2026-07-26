"""Camada única de emissão e validação de códigos numéricos de uso único.

Confirmação de e-mail e recuperação de senha por código são o MESMO problema
(provar posse temporária de uma caixa de entrada) com dois rótulos diferentes
(`VerificationCode.Purpose`) — por isso um serviço só, em vez de duas cópias
que um dia divergiriam sobre TTL, teto de tentativas ou rate limit.

Este módulo não manda e-mail nenhum (isso é de quem chama, na Fase 2) e não
sabe nada sobre views/templates: só emite, valida e invalida códigos.
"""

import enum
import hashlib
import secrets
import string
from dataclasses import dataclass
from datetime import timedelta

from axes.helpers import get_client_ip_address
from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import VerificationCode

# ── Constantes ───────────────────────────────────────────────────────────────
#
# CODE_TTL e MAX_ATTEMPTS vêm de settings (config/settings/base.py já define o
# default de cada uma via env.int) para dar para ajustar em produção sem
# deploy de código. Os limites de emissão/validação abaixo ficam fixos no
# módulo: são parâmetro de abuso, não de produto, e mexer neles é raro o
# bastante para não valer a pena mais uma variável de ambiente.
CODE_LENGTH = 6
CODE_TTL = settings.VERIFICATION_CODE_TTL
MAX_ATTEMPTS = settings.VERIFICATION_CODE_MAX_ATTEMPTS

ISSUE_LIMIT_PER_IDENTITY = 3   # emissões por (usuário, propósito) na janela
ISSUE_LIMIT_PER_IP = 10        # emissões por IP na janela
CHECK_LIMIT_PER_IP = 20        # validações por IP na janela
THROTTLE_WINDOW = 900          # 15 minutos — mesma janela do balde de reset em views.py


def _hash_key(*parts):
    """Deriva uma chave de cache opaca e de tamanho fixo a partir de dados sensíveis.

    Promovida de apps.accounts.views (mesma implementação, mesmo motivo: a
    chave crua carregaria e-mail/IP/user id em texto puro para dentro do
    backend de cache, que hoje é uma tabela no banco — DatabaseCache). views.py
    importa esta função daqui agora, para não manter duas cópias que um dia
    poderiam divergir.
    """
    return hashlib.sha256('|'.join(parts).encode()).hexdigest()


def _bucket_count(key):
    """Garante o balde (cria com 0 se ausente) e devolve a contagem atual, sem incrementar.

    Separar "ler/criar" de "incrementar" (função seguinte) permite checar
    VÁRIOS baldes antes de decidir se a operação é permitida, sem contar uma
    tentativa contra um balde quando outro, checado depois, acaba barrando.
    """
    return cache.get_or_set(key, 0, THROTTLE_WINDOW)


def _bump_bucket(key):
    """Incrementa um balde já garantido por `_bucket_count`.

    Mesmo padrão de CustomPasswordResetView.form_valid (views.py): entre o
    get_or_set que garantiu a chave e este incr, ela pode expirar — uma
    corrida mínima que o except cobre recriando o balde do zero.
    """
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=THROTTLE_WINDOW)


def throttle(key_parts, limit, prefix):
    """Conta uma tentativa num balde e devolve True quando ela deve ser BARRADA.

    API pública dos baldes, para quem precisa limitar algo que este módulo não
    conhece — o caso concreto é a solicitação de recuperação de senha
    (apps.accounts.code_views): `issue_code` só roda quando a conta existe,
    então sem um balde no nível da view um atacante martelaria o endpoint com
    endereços inexistentes de graça, sem nunca tocar num limite.

    Expor uma função em vez dos três helpers privados evita que cada chamador
    recomponha na mão a sequência get_or_set -> compara -> incr (e esqueça o
    except ValueError da corrida de expiração).
    """
    key = f'{prefix}:{_hash_key(*key_parts)}'
    if _bucket_count(key) >= limit:
        return True
    _bump_bucket(key)
    return False


def _hash_code(user, purpose, raw_code):
    """HMAC do código — nunca o texto puro chega perto do banco ou de um log.

    `salted_hmac` usa SECRET_KEY do processo como pepper, que não mora no
    banco: quem rouba só um dump/backup do banco não tem o que precisa para
    forçar bruta offline os hashes, porque falta o pepper. Por isso NÃO se
    usa aqui um KDF lento (PBKDF2/argon2, como em senha de usuário) — seria
    teatro de segurança: o espaço de busca é 10⁶ (6 dígitos), e nenhum KDF
    lento neutraliza força bruta quando o atacante já tem hash e pepper. A
    defesa real de um segredo tão curto é TTL de minutos + teto de tentativas
    + uso único — exatamente o que CODE_TTL, MAX_ATTEMPTS e `used_at`
    implementam.

    `key_salt` inclui `purpose` e `user.pk` de propósito: sem isso, o mesmo
    código de 6 dígitos gerado por acaso para dois usuários (ou para dois
    propósitos do mesmo usuário) produziria o mesmo hash — um hash vazado
    validaria o código certo no contexto errado.
    """
    key_salt = f'apps.accounts.verification.{purpose}.{user.pk}'
    return salted_hmac(key_salt, raw_code, algorithm='sha256').hexdigest()


def _normalize_code(raw_code):
    """Descarta tudo que não for dígito antes de comparar.

    O usuário vai colar o código do jeito que o e-mail/SMS formatou para
    leitura humana — '482 731' ou '482-731' — e recusar isso por um detalhe
    de formatação, que nada tem a ver com segurança, é só atrito.
    """
    return ''.join(char for char in (raw_code or '') if char.isdigit())


def _latest_code(user, purpose):
    """A linha mais recente do par (user, purpose), usada ou não, expirada ou não.

    Deliberadamente SEM filtrar `used_at__isnull=True`: check_code precisa
    diferenciar "nunca existiu" (NOT_FOUND) de "existiu e estourou o teto de
    tentativas" (TOO_MANY_ATTEMPTS) mesmo depois que este último já foi
    queimado — se a busca escondesse linhas usadas, a MESMA consulta que
    reporta TOO_MANY_ATTEMPTS na 5ª tentativa errada não acharia mais nada na
    6ª, e o chamador veria NOT_FOUND onde deveria ver "você estourou o
    limite". `-pk` como desempate de `-created_at`: dois códigos emitidos no
    mesmo microssegundo (reemissão rápida em teste, por exemplo) não podem
    deixar ambíguo qual é o mais recente.
    """
    return (
        VerificationCode.objects
        .filter(user=user, purpose=purpose)
        .order_by('-created_at', '-pk')
        .first()
    )


def issue_code(user, purpose, request=None):
    """Emite um código novo para (user, purpose) e devolve o texto puro.

    O texto puro só existe neste retorno — nunca é salvo (só o hash) nem
    logado. Quem chama manda por e-mail (Fase 2) e descarta a variável.
    Devolve None quando algum balde de rate limit recusa a emissão; quem
    chama decide o que mostrar (mensagem genérica, no mesmo espírito de
    CustomPasswordResetView.form_valid, que também finge sucesso quando
    bloqueia).

    `request=None` pula o balde por IP: chamadas de management command ou
    shell não têm requisição HTTP para tirar um IP, e quem dispara essas
    chamadas já é código de confiança (staff/CLI), não um formulário público
    exposto a qualquer origem — só o balde por identidade continua valendo.
    """
    identity_key = f'verify:issue:identity:{_hash_key(str(user.pk), purpose)}'
    ip_key = None
    if request is not None:
        ip = get_client_ip_address(request) or 'unknown_ip'
        ip_key = f'verify:issue:ip:{_hash_key(ip)}'

    # Checa OS DOIS baldes antes de incrementar QUALQUER um: se o de IP barrar,
    # o de identidade não pode ter sido contado à toa por uma emissão que não
    # vai acontecer.
    if _bucket_count(identity_key) >= ISSUE_LIMIT_PER_IDENTITY:
        return None
    if ip_key is not None and _bucket_count(ip_key) >= ISSUE_LIMIT_PER_IP:
        return None

    _bump_bucket(identity_key)
    if ip_key is not None:
        _bump_bucket(ip_key)

    # "O usuário pediu vários códigos": só o último deve valer. Sem isto, um
    # e-mail de confirmação antigo (ainda na caixa de entrada de quem pediu
    # reenvio) continuaria funcionando ao lado do mais novo — dois segredos
    # válidos ao mesmo tempo para o mesmo par (user, purpose).
    VerificationCode.objects.filter(
        user=user, purpose=purpose, used_at__isnull=True,
    ).update(used_at=timezone.now())

    # Limpeza oportunista: link de segurança para instalações que nunca
    # rodam `clear_expired_verification_codes` agendado. O comando continua
    # sendo o mecanismo principal (pensado para rodar em cron); isto aqui é só
    # uma rede, então o alcance é a tabela inteira, não só este usuário.
    VerificationCode.objects.filter(created_at__lt=timezone.now() - timedelta(hours=24)).delete()

    # secrets.choice (CSPRNG do SO), nunca random.choice: random usa Mersenne
    # Twister, reprodutível a partir de amostras da própria saída — errado
    # para qualquer coisa que vire segredo, mesmo um de 6 dígitos.
    raw_code = ''.join(secrets.choice(string.digits) for _ in range(CODE_LENGTH))

    VerificationCode.objects.create(
        user=user,
        email=(user.email or '').strip().lower(),
        purpose=purpose,
        code_hash=_hash_code(user, purpose, raw_code),
        expires_at=timezone.now() + timedelta(seconds=CODE_TTL),
    )
    return raw_code


class CodeCheckStatus(enum.Enum):
    """Valores estáveis — usados em template/log/teste; não renomeie sem migrar os três."""

    OK = 'ok'
    INVALID = 'invalid'
    EXPIRED = 'expired'
    TOO_MANY_ATTEMPTS = 'too_many_attempts'
    NOT_FOUND = 'not_found'
    THROTTLED = 'throttled'


@dataclass(frozen=True)
class CodeCheck:
    """Resultado tipado de `check_code` — nunca um bool solto ou uma exceção.

    `code` vem preenchido sempre que uma linha foi de fato localizada e
    inspecionada (todo status menos NOT_FOUND por ausência de linha e
    THROTTLED), para quem chama decidir o que exibir — ex.: quantas
    tentativas restam — sem uma segunda consulta ao banco.
    """

    status: CodeCheckStatus
    code: VerificationCode | None = None

    @property
    def ok(self):
        return self.status is CodeCheckStatus.OK


def check_code(user, purpose, raw_code, request=None):
    """Valida `raw_code` contra o código pendente de (user, purpose).

    `request=None` pula o balde de validação por IP, pelo mesmo motivo de
    `issue_code`: sem requisição HTTP não há IP, e quem valida sem request já
    é chamada de confiança.

    A ordem das checagens importa e não é a leitura mais óbvia do requisito —
    ver a docstring de `_latest_code` para o porquê de checar o teto de
    tentativas ANTES de "já foi usado": é o que permite a 6ª tentativa,
    depois do código já ter sido queimado na 5ª, continuar reportando
    TOO_MANY_ATTEMPTS em vez de NOT_FOUND.
    """
    if request is not None:
        ip = get_client_ip_address(request) or 'unknown_ip'
        ip_key = f'verify:check:ip:{_hash_key(ip)}'
        if _bucket_count(ip_key) >= CHECK_LIMIT_PER_IP:
            return CodeCheck(status=CodeCheckStatus.THROTTLED)
        _bump_bucket(ip_key)

    code = _latest_code(user, purpose)
    if code is None:
        return CodeCheck(status=CodeCheckStatus.NOT_FOUND)

    if code.attempts >= MAX_ATTEMPTS:
        if code.used_at is None:
            code.used_at = timezone.now()
            code.save(update_fields=['used_at'])
        return CodeCheck(status=CodeCheckStatus.TOO_MANY_ATTEMPTS, code=code)

    if code.is_used:
        # Já foi validado com sucesso antes, ou foi invalidado por uma
        # reemissão — dos dois jeitos, não há nada pendente para este par.
        return CodeCheck(status=CodeCheckStatus.NOT_FOUND, code=code)

    if code.is_expired:
        return CodeCheck(status=CodeCheckStatus.EXPIRED, code=code)

    normalized = _normalize_code(raw_code)
    given_hash = _hash_code(user, purpose, normalized)

    # compare_digest, nunca `==`: comparação de string comum retorna assim
    # que encontra o primeiro byte diferente, e essa diferença de tempo dá
    # para medir em rede — um oráculo de tempo que deixaria adivinhar o hash
    # (não o código) byte a byte. Comparamos os HASHES, não os códigos: o
    # texto puro do lado do servidor nunca existe fora do retorno de
    # issue_code, então não haveria nem o que comparar diretamente.
    if not secrets.compare_digest(given_hash, code.code_hash):
        new_attempts = code.attempts + 1
        reached_ceiling = new_attempts >= MAX_ATTEMPTS
        updates = {'attempts': F('attempts') + 1}
        if reached_ceiling:
            updates['used_at'] = timezone.now()
        VerificationCode.objects.filter(pk=code.pk).update(**updates)

        # Reflete no objeto em memória (já persistido acima via F()) para o
        # chamador ler o estado pós-tentativa sem uma segunda consulta.
        code.attempts = new_attempts
        if reached_ceiling:
            code.used_at = updates['used_at']
        return CodeCheck(status=CodeCheckStatus.INVALID, code=code)

    code.used_at = timezone.now()
    code.save(update_fields=['used_at'])
    return CodeCheck(status=CodeCheckStatus.OK, code=code)


def invalidate_all(user, purpose=None):
    """Carimba `used_at` em todo código ainda pendente do usuário.

    Chamado ao trocar a senha (fluxo de outra Fase): se um código de reset
    ainda pendente chegou a vazar (caixa de entrada comprometida, e-mail
    encaminhado por engano), a troca de senha por qualquer outro caminho deve
    fechar essa porta em vez de deixar o código antigo utilizável até expirar
    sozinho. `purpose=None` invalida todos os propósitos de uma vez; passar
    um `VerificationCode.Purpose` específico restringe a um só.
    """
    queryset = VerificationCode.objects.filter(user=user, used_at__isnull=True)
    if purpose is not None:
        queryset = queryset.filter(purpose=purpose)
    queryset.update(used_at=timezone.now())
