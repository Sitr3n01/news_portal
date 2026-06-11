# Documentação Técnica

Índice técnico do projeto. Para entender a arquitetura, comece por `ARQUITETURA_E_MODELOS.md`; para publicar em produção, comece pelo checklist de go-live.

## Canônicos

| Documento | Uso |
|-----------|-----|
| [ARQUITETURA_E_MODELOS.md](ARQUITETURA_E_MODELOS.md) | Visão geral: rotas, Sites Framework, apps e modelos |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | Onboarding de desenvolvimento e padrões de código |
| [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md) | Referência extensa para debugging sensível |
| [SEGURANCA.md](SEGURANCA.md) | Ameaças, proteções ativas e checklist de segurança |
| [FLUXO_NEWSLETTER.md](FLUXO_NEWSLETTER.md) | Fluxo real da newsletter, fila e entregas |
| [APP_HIRING.md](APP_HIRING.md) | Vagas, candidaturas e download protegido de currículos |

## Operação

| Documento | Uso |
|-----------|-----|
| [go-live-checklist.md](go-live-checklist.md) | Checklist operacional antes de publicar |
| [DEPLOY.md](DEPLOY.md) | Guia de deploy em produção |
| [secure-deploy.md](secure-deploy.md) | Fluxo GitHub Actions → tag aprovada → VPS |
| [cloudflare-bots.md](cloudflare-bots.md) | Turnstile, Cloudflare proxy, firewall e real IP |
| [vps-optimization.md](vps-optimization.md) | Rotinas de manutenção e otimização da VPS |

## Recursos Atuais

| Documento | Escopo |
|-----------|--------|
| [REDES_SOCIAIS.md](REDES_SOCIAIS.md) | Contas, posts, seção da home e sync Instagram/TikTok |
| [REDES_SOCIAIS_CREDENCIAIS.md](REDES_SOCIAIS_CREDENCIAIS.md) | Como conectar credenciais oficiais de Instagram/TikTok |

## Nota Sobre Multi-site

Hoje existe um único `Site` ativo (`SITE_ID=1`). A separação Komuniki/Blog da Kelly é por caminho e por Nginx, não por dois registros `Site` em produção. Continue usando `on_site` nas views públicas, porque isso preserva o isolamento quando o multi-site real for ativado.
