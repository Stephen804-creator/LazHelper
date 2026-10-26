# Deploy LazHelper to Render

LazHelper uses one **Render Web Service** to serve the FastAPI application, HTML/CSS/JavaScript interface, and API. It does not create a separate static site or a separate API service. The root page is served at `/`, API documentation at `/docs`, and the health endpoint is `/api/health`.

## Create the deployment

1. Push or merge this deployment branch into the branch you intend to deploy.
2. In Render, choose **New → Blueprint Instance**.
3. Connect the `Stephen804-creator/LazHelper` GitHub repository and select the branch containing `render.yaml`.
4. Review the resources. The Blueprint defines one web service (`lazhelper`) and one PostgreSQL database (`lazhelper-db`).
5. Confirm creation and wait for the web service deploy to finish.
6. Open the public URL shown on the **lazhelper Web Service** page. It will be an `onrender.com` URL. Use this web-service URL for the demo, not the database connection string.

The Blueprint connects the web service to PostgreSQL using Render's private connection string exposed as `DATABASE_URL`. Do not paste the database URL into a browser or share it publicly; it contains credentials.

## Configure Gemma 4 through Ollama Cloud

The Blueprint preconfigures these environment variables:

- `LAZHELPER_OLLAMA_URL=https://ollama.com/api`
- `LAZHELPER_OLLAMA_MODEL=gemma4:31b`

When Render creates the Blueprint, enter your Ollama Cloud API key for the secret environment variable `OLLAMA_API_KEY`. If the service already exists, open **Render → lazhelper → Environment**, add `OLLAMA_API_KEY`, paste the key there, and save/redeploy. Do not put the key in GitHub, source code, browser JavaScript, or screenshots.

LazHelper sends the key as an `Authorization: Bearer` header and calls the Ollama chat endpoint. The AI feature uses the model identifier `gemma4:31b`; this is distinct from the previous local default `gemma3:1b`. Ollama Cloud usage is subject to the account's available free allowance, credits, and model availability. If AI recommendations fail, check Render logs and the Ollama dashboard usage/keys pages. The rest of the app can still run when AI is unavailable.

## Database behavior

- Local development must also use a PostgreSQL database; configure `DATABASE_URL` in your local environment.
- All persistent application state uses the same PostgreSQL database; startup fails if no PostgreSQL URL is configured. This includes preferences, operation history, review queue, owner policy/instructions, assistant profile, activity history, project workspaces, and saved workflows.
- PostgreSQL records survive web-service restarts and redeployments. The database is separate from the web service's ephemeral filesystem.
- The default Blueprint uses Render's free PostgreSQL plan. Render currently expires free PostgreSQL databases 30 days after creation. Upgrade the database before expiry if the records must be retained longer. Free web services also sleep when idle and have an ephemeral filesystem.

## Important demo limitations

- The service's workspace is the server-side `workspace/` directory, not a visitor's computer. LazHelper cannot access a visitor's local files through a hosted web page. Files in the server workspace are on Render's ephemeral filesystem and may reset after redeploy or restart; PostgreSQL preserves application records, not file contents.
- LazHelper does not currently provide user authentication. Treat the public deployment as a demonstration using sample/non-sensitive files only. Do not upload or store private documents or credentials in it.

## Troubleshooting

- If the Blueprint cannot create `lazhelper-db`, check whether the selected Render workspace already has an active free PostgreSQL database. Render permits only one active free PostgreSQL database per workspace. A separate workspace can have its own database, subject to Render's current account limits.
- If the web service fails its health check, inspect its deploy logs. Database connection or SQL compatibility errors should be fixed before treating the demo as ready.
- If the web service starts but AI recommendations are unavailable, verify the URL, model identifier, `OLLAMA_API_KEY`, and remaining Ollama Cloud usage. The AI service can fail independently of the web/API deployment.
