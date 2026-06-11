# Credenciais das APIs (Instagram + TikTok)

Guia para conectar a sincronização automática. Enquanto não houver credenciais, o sistema continua funcionando no modo manual: contas e posts podem ser cadastrados pelo admin.

## Onde os Valores Entram

- **Admin → Contas de Redes Sociais:** `external_user_id`, `access_token`, `refresh_token`, `token_expires_at`.
- **`.env.prod`:** `TIKTOK_CLIENT_KEY` e `TIKTOK_CLIENT_SECRET`.

Nunca versione tokens ou segredos.

## Instagram

Pré-requisito: conta profissional Business ou Creator vinculada a uma Página do Facebook.

1. Acesse `developers.facebook.com` e crie um app Business.
2. Adicione Instagram Graph API.
3. Vincule a Página do Facebook e a conta Instagram.
4. Gere token de longa duração com `instagram_basic` e `instagram_graph_user_media`.
5. Obtenha o Instagram User ID.
6. No admin, abra a conta Instagram e preencha:
   - **ID da conta na API**;
   - **Token de acesso**;
   - **Token expira em**.
7. Faça App Review da Meta antes de produção ampla.

O comando renova token do Instagram quando faltam até 7 dias para expirar.

## TikTok

1. Acesse `developers.tiktok.com` e crie um app.
2. Adicione Login Kit e Display API.
3. Configure Redirect URI.
4. Solicite escopos `user.info.basic` e `video.list`.
5. Anote Client Key e Client Secret.
6. Faça OAuth da conta para obter `access_token` e `refresh_token`.
7. No servidor, configure:

```env
TIKTOK_CLIENT_KEY=seu_client_key
TIKTOK_CLIENT_SECRET=seu_client_secret
```

8. No admin, preencha token de acesso, refresh token e data de expiração.

O comando renova token TikTok quando falta até 1 hora para expirar.

## Teste

```bash
python manage.py sync_social_posts --dry-run --verbose
python manage.py sync_social_posts
```

Depois confira **Posts de Redes Sociais** no admin.

## Segurança

- Tokens e segredos não entram no repositório.
- Campos sensíveis no admin não reexibem valor preenchido.
- Falha de uma rede não impede a outra.
- A home continua no ar com posts já salvos.
