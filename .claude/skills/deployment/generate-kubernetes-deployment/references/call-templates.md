# Call Worker Kubernetes Manifest Templates

All placeholders use `{PLACEHOLDER}` syntax. Replace before writing files.

## call/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {RESOURCE_PREFIX}tone-call-worker
  namespace: {ENV_NAME}
  labels:
    app: {RESOURCE_PREFIX}tone-call-worker
    environment: {ENV_NAME}
    component: call
spec:
  replicas: {CALL_REPLICAS}
  selector:
    matchLabels:
      app: {RESOURCE_PREFIX}tone-call-worker
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: {RESOURCE_PREFIX}tone-call-worker
        environment: {ENV_NAME}
        component: call
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      terminationGracePeriodSeconds: 20
      containers:
        - name: {RESOURCE_PREFIX}tone-call-worker
          image: {DOCKER_IMAGE}
          imagePullPolicy: Always
          command:
            - uvicorn
            - "main:app"
            - "--host"
            - "0.0.0.0"
            - "--port"
            - "8080"
            - "--workers"
            - "1"
            - "--timeout-keep-alive"
            - "3600"
            - "--log-level"
            - "info"
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: "{CALL_CPU_REQUEST}"
              memory: "{CALL_MEM_REQUEST}"
            limits:
              cpu: "{CALL_CPU_LIMIT}"
              memory: "{CALL_MEM_LIMIT}"
          env:
            - name: ENV
              value: "{ENV_NAME}"
            - name: WORKER_MODE
              value: "voice"
            - name: MAX_CONCURRENT_CALLS
              value: "{MAX_CONCURRENT_CALLS}"
            - name: INFISICAL_TOKEN
              valueFrom:
                secretKeyRef:
                  name: infisical-credentials
                  key: token
            - name: INFISICAL_PROJECT_ID
              valueFrom:
                secretKeyRef:
                  name: infisical-credentials
                  key: project_id
            - name: INFISICAL_HOST
              value: "https://secrets.trytone.ai"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 2
          lifecycle:
            preStop:
              exec:
                command:
                  - /bin/sh
                  - -c
                  - "curl -sf http://localhost:8080/drain || true && sleep 280"
      imagePullSecrets:
        - name: dockerhub-auth
```

## call/service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {RESOURCE_PREFIX}tone-call-service
  namespace: {ENV_NAME}
  labels:
    app: {RESOURCE_PREFIX}tone-call-worker
    component: call
spec:
  selector:
    app: {RESOURCE_PREFIX}tone-call-worker
  ports:
    - port: 80
      targetPort: 8080
      protocol: TCP
  type: ClusterIP
```

## call/ingress.yaml

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {RESOURCE_PREFIX}tone-call-ingress
  namespace: {ENV_NAME}
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "10"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "*"
    nginx.ingress.kubernetes.io/cors-allow-methods: "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    nginx.ingress.kubernetes.io/cors-allow-headers: "DNT, Keep-Alive, User-Agent, X-Requested-With, If-Modified-Since, Cache-Control, Content-Type, Range, Authorization, X-Auth-Token, X-Org-Id, X-Tenant-Id, tenant_id, Accept, Origin, Referer, Sec-WebSocket-Extensions, Sec-WebSocket-Key, Sec-WebSocket-Protocol, Sec-WebSocket-Version"
    nginx.ingress.kubernetes.io/cors-expose-headers: "Content-Length, Content-Range, Content-Type, X-Request-Id"
    nginx.ingress.kubernetes.io/cors-allow-credentials: "true"
    nginx.ingress.kubernetes.io/cors-max-age: "3600"
    nginx.ingress.kubernetes.io/websocket-services: "{RESOURCE_PREFIX}tone-call-service"
    nginx.ingress.kubernetes.io/proxy-http-version: "1.1"
    nginx.ingress.kubernetes.io/upstream-hash-by: "$request_uri"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - {CALL_DOMAIN}
      secretName: {RESOURCE_PREFIX}tone-call-certificate
  rules:
    - host: {CALL_DOMAIN}
      http:
        paths:
          - path: /ws
            pathType: Prefix
            backend:
              service:
                name: {RESOURCE_PREFIX}tone-call-service
                port:
                  number: 80
          - path: /health
            pathType: Exact
            backend:
              service:
                name: {RESOURCE_PREFIX}tone-call-service
                port:
                  number: 80
          - path: /ready
            pathType: Exact
            backend:
              service:
                name: {RESOURCE_PREFIX}tone-call-service
                port:
                  number: 80
```

## call/certificate.yaml

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: {RESOURCE_PREFIX}tone-call-certificate
  namespace: {ENV_NAME}
spec:
  secretName: {RESOURCE_PREFIX}tone-call-certificate
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  commonName: {CALL_DOMAIN}
  dnsNames:
  - {CALL_DOMAIN}
  duration: 2160h # 90 days
  renewBefore: 720h # 30 days
  privateKey:
    algorithm: RSA
    encoding: PKCS1
    size: 2048
```

## call/pdb.yaml

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {RESOURCE_PREFIX}tone-call-worker-pdb
  namespace: {ENV_NAME}
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: {RESOURCE_PREFIX}tone-call-worker
```

## letsencrypt-prod.yaml (shared, at environment root)

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: {LETSENCRYPT_EMAIL}
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```
