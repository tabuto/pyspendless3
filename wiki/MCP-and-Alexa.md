# MCP server and Alexa+

PySpendless embeds a small [Model Context Protocol](https://modelcontextprotocol.io/) server, so an AI assistant can log an expense for you ("I spent 23.50 at the supermarket") without opening the web UI. There are two endpoints, sharing the same tools:

| Endpoint | Authentication | Intended client |
|---|---|---|
| `POST /mcp` | Personal token (`Authorization: Bearer <token>`) | Claude and any MCP client that accepts a static bearer token |
| `POST /mcp-oauth2` | OAuth 2 access token | Clients that require OAuth, such as Alexa+ |

Both speak stateless JSON-RPC 2.0: `tools/call` can be invoked directly, with no `initialize` handshake.

![Profile page where personal MCP tokens are generated](https://raw.githubusercontent.com/wiki/tabuto/pyspendless3/images/settings-profile-light.png)

## Tools

### `add_movement`

Records an expense or an income.

| Argument | Type | Notes |
|---|---|---|
| `amount` | number | Required. Always positive; `kind` decides whether it is an expense or an income |
| `kind` | `expense` \| `income` | Defaults to `expense` |
| `category` | string | Category **name**, one of the account's categories. Call `list_categories` first if unsure |
| `wallet` | string | Optional wallet name or code. Falls back to the calling user's preferred wallet |
| `date` | `YYYY-MM-DD` | Optional. Defaults to today (Italian time) |
| `note` | string | Optional free text |
| `force` | boolean | Set to `true` to insert a movement identical to the last one |

**Duplicate protection:** if the new movement is identical to the last one the user inserted (same amount, kind, category and note), the call is rejected with `duplicate: true` and the existing movement is returned. The assistant is expected to ask the user for confirmation and retry with `force=true`.

### `list_categories`

Returns the account's categories **and wallets**, so the assistant can pick valid names. Takes an optional `kind` (`expense` / `income`) to filter the categories.

## Using `/mcp` with a personal token

1. Sign in and open **Profile** (`/settings/profile`).
2. In the MCP tokens section, give the token a label (default `Claude`) and generate it.
3. **Copy the token immediately**: it is shown once. Only its hash is stored, and it expires after 365 days.
4. Register `https://<your-host>/mcp` in your MCP client, sending the token as a bearer header.

Tokens can be revoked at any time from the same page (`DELETE /api/mcp-tokens/<hash>`).

A quick manual test:

```bash
curl -s https://<your-host>/mcp \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_categories","arguments":{}}}'
```

## OAuth 2 for Alexa+ (`/mcp-oauth2`)

The OAuth endpoints live in `pyspendless/oauth_server.py`.

- **Grants:** `authorization_code` with PKCE (S256), `refresh_token` and `client_credentials`.
- **Clients:** no dynamic registration. A single client is pre-registered through environment variables (see below).
- **Token lifetimes:** authorization code 60 s, access token 1 h, refresh token 60 days.
- **Consent:** `/oauth/authorize` asks the user to sign in with Google (if needed) and approve the connection. Authorised apps are listed, and can be revoked, on the profile page.
- **`client_credentials` tokens** are service-level: they carry no user and no refresh token.
- **Discovery:** `/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server` (plus path-suffixed variants).

| Variable | Description |
|---|---|
| `OAUTH_ALEXA_CLIENT_ID` | Client ID of the pre-registered client |
| `OAUTH_ALEXA_CLIENT_SECRET` | Its secret |
| `OAUTH_ALEXA_REDIRECT_URIS` | Comma-separated list of allowed redirect URIs |

## Alexa custom skill bridge

`alexa-mcp-lambda/` is a small AWS Lambda function that backs an Alexa custom skill and forwards requests to `/mcp-oauth2`. It is an isolated sub-project with its own virtualenv and `requirements.txt`; the build, deployment and skill-creation steps are in [`alexa-mcp-lambda/README.md`](https://github.com/tabuto/pyspendless3/blob/main/alexa-mcp-lambda/README.md). The interaction model shipped there is in Italian.

## Known limitations

- There is no rate limiting on `/mcp` yet (tracked in the backlog).
- The tool descriptions and error messages are in Italian, matching the application UI.

---

[← Back to the home page](https://github.com/tabuto/pyspendless3/wiki)
