# Local Agent Developer Setup

To develop and test Agent capabilities (like the Caseworker Agent) locally without affecting the production Jawafdehi.org database, follow these steps to spin up a local instance of the `jawafdehi-api` using SQLite.

## 1. Setup the Local Database and API

Navigate to the API service directory from the root of `jawafdehi-meta`:

```bash
cd services/jawafdehi-api
```

Install the dependencies using Poetry:

```bash
poetry install
```

Configure your local environment to use SQLite (this happens by default if no Postgres URL is provided, but verify by copying the example environment file):

```bash
cp .env.example .env
# Edit .env and ensure database connection defaults to SQLite locally
```

Run the database migrations:

```bash
poetry run python manage.py migrate
```

## 2. Create a Superuser and Generate a Token

To allow the MCP Server to authenticate with your local API, you will need a user account and an API token.

Create the superuser account:

```bash
poetry run python manage.py createsuperuser
```
Follow the prompts to set a username, email, and password.

Next, generate an API token for your newly created user. You can do this by running:

```bash
poetry run python manage.py shell -c "from django.contrib.auth import get_user_model; from rest_framework.authtoken.models import Token; User = get_user_model(); user = User.objects.get(username='<your-superuser-username>'); token, _ = Token.objects.get_or_create(user=user); print('\n--- YOUR TOKEN ---'); print(token.key); print('------------------\n')"
```
*(Replace `<your-superuser-username>` with the username you created)*

Note down the printed token.

Finally, start the local server:

```bash
poetry run python manage.py runserver 127.0.0.1:8000
```

## 3. Configure the MCP Tooling

Whether you are using standard IDE agents (like GitHub Copilot or Cursor), custom runners (like `kiro-cli`), or independent CLIs (like Openclaw or Claude Code), you need to configure your agent's MCP settings to point to your local server.

Edit your agent's `mcp.json` (or the respective IDE settings file):

```json
{
  "mcpServers": {
    "jawafdehi": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Jawafdehi/jawafdehi-mcp.git",
        "jawafdehi-mcp"
      ],
      "env": {
        "JAWAFDEHI_API_TOKEN": "<your-local-token>",
        "JAWAFDEHI_API_BASE_URL": "http://127.0.0.1:8000/api"
      }
    }
  }
}
```

> **Note:** By setting `JAWAFDEHI_API_BASE_URL` to your localhost port `8000`, all MCP commands like "create case" or "patch case" will be routed safely to your local SQLite database instead of production.

### Agent JSON files

If running agents directly via `.agents/caseworker/agents/*.json`, also set the corresponding environment variables in your shell before invoking the agent runner:

```bash
export JAWAFDEHI_API_TOKEN=<your-local-token>
export JAWAFDEHI_API_BASE_URL=http://127.0.0.1:8000/api
```

The agent JSON files use `${env:...}` references so these shell variables will be picked up automatically.

## 4. Work with the Agent!

You can now use any CLI or Agent runner, point them at your local repositories and `.agents/caseworker/INSTRUCTIONS.md`, and observe changes reflecting locally in your `jawafdehi-api` Django admin panel!
