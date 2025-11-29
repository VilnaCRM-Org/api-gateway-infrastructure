# PyCharm Autocomplete with the Docker Workspace

This repository already includes a Docker environment that carries the Pulumi
CLI, Poetry, and the AWS CLI. You can point PyCharm at the running container to
get type hints and completions without installing anything on your host. The
steps below describe both the Docker-backed flow (recommended) and a local
virtual-environment fallback.

## 1. Build the workspace image and start the container

1. Install the latest versions of Docker Desktop (or Docker Engine) and Docker
   Compose.
2. From the repository root, build the container and start it in the background:

   ```bash
   docker compose up --build -d
   ```

   The compose file defines a single service named `app`. It mounts the
   `pulumi/` directory into `/home/<your-username>/project` inside the
   container so PyCharm can reuse the same sources.

3. Install the Python dependencies inside the container so that the interpreter
   already knows about Pulumi and the AWS provider:

   ```bash
   docker compose exec app bash -lc "cd /home/${USER}/project && poetry install --no-root"
   ```

   The command above creates a `.venv` folder inside `pulumi/` (thanks to
   `poetry config virtualenvs.in-project true` in the Dockerfile).

4. (Optional) To verify the toolchain in the container, drop into a shell:

   ```bash
   docker compose exec app bash
   ```

   Inside the shell you can run `pulumi version`, `python --version`, or `aws
   --version`.

## 2. Attach PyCharm to the Docker Compose interpreter

1. Launch PyCharm and open the project.
2. Go to **Settings → Project: api-gateway-infrastructure → Python Interpreter**.
3. Click the gear icon → **Add…** → select **Docker Compose**.
4. In the dialog:
   - Choose the repo’s `docker-compose.yml`.
   - Set **Service** to `app`.
   - Leave the default Python path or explicitly point it to the Poetry
     environment created earlier:
     `/home/<your-username>/project/.venv/bin/python`.
     <br>To confirm the `<your-username>` part, run
     `docker compose exec app bash -lc 'echo $USER'`.
5. Confirm the interpreter. PyCharm will connect to the running container,
   index the site-packages inside `.venv`, and autocomplete should start working
   immediately inside `pulumi/__main__.py` and other modules.

PyCharm remembers the interpreter selection. If it shows as “not connected”,
start the container again (`docker compose up -d`) and PyCharm will reconnect.

## 3. Optional: local virtual-environment fallback

If you cannot use Docker on your machine, you can still create a local virtual
environment mirroring the container dependencies. Choose where you want it to
live:

- `pulumi/.venv` keeps the interpreter alongside the Pulumi program.
- `.venv` at the repository root works equally well.

Run the commands below from the repository root (replace `pulumi/.venv` with
`.venv` if you choose the root location).

```bash
python -m venv pulumi/.venv
# Activate the environment (run the line that matches your shell):
#   macOS/Linux:        source pulumi/.venv/bin/activate
#   Windows PowerShell: pulumi\.venv\Scripts\Activate
#   Windows cmd:        pulumi\.venv\Scripts\activate.bat
pip install --upgrade pip
pip install "pulumi>=3.138,<4" "pulumi-aws>=6.0,<7" black flake8 pre-commit
deactivate
```

Add the interpreter in PyCharm by pointing to `pulumi/.venv/bin/python` (or the
Windows equivalent). This gives you the same completions without needing Docker.

## 4. Verify autocomplete inside PyCharm

Open (or create) any Pulumi module such as `pulumi/__main__.py` and type
`pulumi.` or `pulumi_aws.`. You should see resource suggestions. If completions
do not appear:

- Confirm the interpreter status in the PyCharm status bar.
- Rebuild the Docker image if dependencies changed:

  ```bash
  docker compose build app
  ```

- Use **File → Invalidate Caches / Restart…** in PyCharm to trigger re-indexing.

## 5. Stop the workspace

When you are done, you can stop the container:

```bash
docker compose down
```

This removes the running container but keeps the built image for the next
session. Use `docker compose down --rmi all` if you also want to remove the
image.
