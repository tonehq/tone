# API Kubernetes Manifest Templates

All placeholders use `{PLACEHOLDER}` syntax. Replace before writing files.

## api/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {RESOURCE_PREFIX}tone-api-deployment
  namespace: {ENV_NAME}
  labels:
    app: {RESOURCE_PREFIX}tone-api
    environment: {ENV_NAME}
spec:
  replicas: {API_REPLICAS}
  selector:
    matchLabels:
      app: {RESOURCE_PREFIX}tone-api
  template:
    metadata:
      labels:
        app: {RESOURCE_PREFIX}tone-api
        environment: {ENV_NAME}
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      containers:
        - name: {RESOURCE_PREFIX}tone-api
          image: {DOCKER_IMAGE}
          imagePullPolicy: Always
          ports:
            - containerPort: 8000
          command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
          resources:
            requests:
              cpu: "{API_CPU_REQUEST}"
              memory: "{API_MEM_REQUEST}"
            limits:
              cpu: "{API_CPU_LIMIT}"
              memory: "{API_MEM_LIMIT}"
          env:
            - name: ENV
              value: "{ENV_NAME}"
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
      imagePullSecrets:
        - name: dockerhub-auth
```

## api/service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {RESOURCE_PREFIX}tone-api-service
  namespace: {ENV_NAME}
  labels:
    app: {RESOURCE_PREFIX}tone-api
    environment: {ENV_NAME}
spec:
  selector:
    app: {RESOURCE_PREFIX}tone-api
  ports:
    - port: 80
      targetPort: 8000
      protocol: TCP
  type: ClusterIP
```

## api/ingress.yaml

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {RESOURCE_PREFIX}tone-api-ingress
  namespace: {ENV_NAME}
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    # CORS Configuration
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "*"
    nginx.ingress.kubernetes.io/cors-allow-methods: "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    nginx.ingress.kubernetes.io/cors-allow-headers: "DNT, Keep-Alive, User-Agent, X-Requested-With, If-Modified-Since, Cache-Control, Content-Type, Range, Authorization, X-Auth-Token, X-Org-Id, X-Tenant-Id, tenant_id, Accept, Origin, Referer"
    nginx.ingress.kubernetes.io/cors-expose-headers: "Content-Length, Content-Range, Content-Type, X-Request-Id"
    nginx.ingress.kubernetes.io/cors-allow-credentials: "true"
    nginx.ingress.kubernetes.io/cors-max-age: "3600"
    # TLS
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - {API_DOMAIN}
    secretName: {RESOURCE_PREFIX}certificate
  rules:
  - host: {API_DOMAIN}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {RESOURCE_PREFIX}tone-api-service
            port:
              number: 80
```

## api/certificate.yaml

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: {RESOURCE_PREFIX}certificate
  namespace: {ENV_NAME}
spec:
  secretName: {RESOURCE_PREFIX}certificate
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  commonName: {API_DOMAIN}
  dnsNames:
  - {API_DOMAIN}
  duration: 2160h # 90 days
  renewBefore: 720h # 30 days
  privateKey:
    algorithm: RSA
    encoding: PKCS1
    size: 2048
```
