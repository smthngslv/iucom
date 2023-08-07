# Development
You can install dependencies using poetry:
```shell
poetry install
```

Use `.env.example` to setup `.env`
```shell
cp .env.example .env
nano .env
```

Use auto formatting and linting:
```shell
make format lint
```

Start the api locally:
```shell
uvicorn iucom.api.application:application
```

Start jobs locally:
```shell
iucom-moodle-sync
iucom-telegram-sync
```

Start with docker compose:
```shell
docker compose -f docker/docker-compose.yaml up
```

Build, push, pull, prune docker:
```shell
make build
make push
make pull
make prune
```
