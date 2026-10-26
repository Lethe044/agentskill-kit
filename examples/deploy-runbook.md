# Deploying the billing service

1. Pull the latest main branch and check that CI is green.
2. Run `make test` locally. Do not deploy if anything fails.
3. Build the image with `docker build -t billing:$(git rev-parse --short HEAD) .`.
4. Push the image to the registry and update the tag in `deploy/values.yaml`.
5. Run `kubectl rollout status deployment/billing` and wait for it to finish.
6. Check `/health` returns 200 and that the error rate in the dashboard stays flat for five minutes.
7. If the error rate rises, run `kubectl rollout undo deployment/billing` and post in the incident channel.
