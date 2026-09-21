# Mini Agent 01 배포

모든 명령은 프로젝트 루트 `C:\mini_agent_st\mini_agent_01_llm`에서 실행합니다.

## 설정 검사

```powershell
docker compose --env-file .env -f deploy/compose.yml config --quiet
```

## 이미지 빌드와 실행

```powershell
docker compose --env-file .env -f deploy/compose.yml up -d --build
docker compose --env-file .env -f deploy/compose.yml ps
```

## 접속 주소

- Frontend: `http://127.0.0.1:8501`
- Backend Health: `http://127.0.0.1:8000/health`

## 로그와 종료

```powershell
docker compose --env-file .env -f deploy/compose.yml logs --tail=100 backend frontend
docker compose --env-file .env -f deploy/compose.yml down
```

실제 API 키가 들어 있는 `.env`는 Git과 Docker 이미지에 포함하지 않습니다.

## GitHub Actions 자동 배포 준비

EC2에는 Docker와 Docker Compose가 설치되어 있어야 하며 다음 파일을 최초 한 번 직접
준비해야 합니다.

```text
~/mini_agent_01_llm/.env
```

GitHub 저장소의 `production` Environment에 다음 Secret을 등록합니다.

```text
AWS_HOST
AWS_USER
AWS_SSH_PRIVATE_KEY
AWS_SSH_KNOWN_HOSTS
```

Repository variable `ENABLE_EC2_DEPLOY`를 `true`로 설정하면 `main` Push의 CI가 성공한 뒤
EC2 배포가 실행됩니다. 이 값을 설정하기 전에는 CI만 실행되고 EC2 배포는 건너뜁니다.
