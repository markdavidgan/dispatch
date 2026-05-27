const BRAND_MAP: Record<string, string> = {
  vercel: "Vercel",
  google: "Google",
  googleapis: "Google",
  netflix: "Netflix",
  facebook: "Meta",
  meta: "Meta",
  microsoft: "Microsoft",
  apple: "Apple",
  amazon: "Amazon",
  aws: "AWS",
  openai: "OpenAI",
  anthropic: "Anthropic",
  stripe: "Stripe",
  shopify: "Shopify",
  github: "GitHub",
  gitlab: "GitLab",
  "rust-lang": "Rust",
  python: "Python",
  golang: "Go",
  kubernetes: "Kubernetes",
  apache: "Apache",
  hashicorp: "HashiCorp",
  "terraform-providers": "HashiCorp",
  redis: "Redis",
  supabase: "Supabase",
  prisma: "Prisma",
  tailwindlabs: "Tailwind",
  shadcn: "shadcn",
  "radix-ui": "Radix",
  tanstack: "TanStack",
  trpc: "tRPC",
  "drizzle-team": "Drizzle",
  withastro: "Astro",
  sveltejs: "Svelte",
  vuejs: "Vue",
  nuxt: "Nuxt",
  "remix-run": "Remix",
  reactjs: "React",
  mui: "MUI",
  lodash: "Lodash",
  expressjs: "Express",
  nestjs: "NestJS",
  fastify: "Fastify",
  jestjs: "Jest",
  "vitest-dev": "Vitest",
  cypressio: "Cypress",
  playwright: "Playwright",
  storybookjs: "Storybook",
  eslint: "ESLint",
  prettier: "Prettier",
  babel: "Babel",
  webpack: "webpack",
  vitejs: "Vite",
  rollup: "Rollup",
  esbuild: "esbuild",
  turborepo: "Turborepo",
  nx: "Nx",
  docker: "Docker",
  helm: "Helm",
  prometheus: "Prometheus",
  grafana: "Grafana",
  jaegertracing: "Jaeger",
  istio: "Istio",
  envoyproxy: "Envoy",
  traefik: "Traefik",
  caddyserver: "Caddy",
  nginx: "NGINX",
  mongodb: "MongoDB",
  postgres: "PostgreSQL",
  mysql: "MySQL",
  sqlite: "SQLite",
  elastic: "Elastic",
  "opensearch-project": "OpenSearch",
  clickhouse: "ClickHouse",
  cockroachdb: "CockroachDB",
  rabbitmq: "RabbitMQ",
  kafka: "Apache Kafka",
  natsio: "NATS",
  grpc: "gRPC",
  protobuf: "Protocol Buffers",
  swaggerapi: "Swagger",
  postmanlabs: "Postman",
  getsentry: "Sentry",
  datadog: "Datadog",
  launchdarkly: "LaunchDarkly",
  posthog: "PostHog",
  amplitude: "Amplitude",
  mixpanel: "Mixpanel",
  segmentio: "Segment",
  dbtlabs: "dbt",
  airbytehq: "Airbyte",
  dagsterio: "Dagster",
  prefecthq: "Prefect",
  airflow: "Apache Airflow",
  mlflow: "MLflow",
  huggingface: "Hugging Face",
  "langchain-ai": "LangChain",
  llamaindex: "LlamaIndex",
  "chroma-core": "Chroma",
  "pinecone-io": "Pinecone",
  weaviate: "Weaviate",
  qdrant: "Qdrant",
  meilisearch: "Meilisearch",
  algolia: "Algolia",
  mapbox: "Mapbox",
  threejs: "Three.js",
  godotengine: "Godot",
  unrealengine: "Unreal Engine",
  bevyengine: "Bevy",
  flutter: "Flutter",
  expo: "Expo",
  firebase: "Firebase",
  appwrite: "Appwrite",
  pocketbase: "PocketBase",
  serverless: "Serverless",
  temporalio: "Temporal",
  camunda: "Camunda",
  jhipster: "JHipster",
  "spring-projects": "Spring",
  micronaut: "Micronaut",
  quarkusio: "Quarkus",
  ktorio: "Ktor",
  square: "Square",
  okhtt: "OkHttp",
  retrofit: "Retrofit",
  lottie: "Lottie",
  airbnb: "Airbnb",
  "material-components": "Material Design",
  electron: "Electron",
  "tauri-apps": "Tauri",
  wailsapp: "Wails",
  cloudflare: "Cloudflare",
  fastly: "Fastly",
  cloudinary: "Cloudinary",
  netlify: "Netlify",
  heroku: "Heroku",
  renderinc: "Render",
  railwayapp: "Railway",
  fly: "Fly.io",
  digitalocean: "DigitalOcean",
  oracle: "Oracle",
  ibm: "IBM",
  redhat: "Red Hat",
  canonical: "Canonical",
  ubuntu: "Ubuntu",
  debian: "Debian",
  archlinux: "Arch Linux",
  nixos: "NixOS",
  rancher: "Rancher",
  vmware: "VMware",
  openstack: "OpenStack",
  proxmox: "Proxmox",
  ipfs: "IPFS",
  ethereum: "Ethereum",
  bitcoin: "Bitcoin",
  hyperledger: "Hyperledger",
};

const SPECIAL_REPO_NAMES: Record<string, string> = {
  ai: "AI SDK",
  "ai-sdk": "AI SDK",
  "next.js": "Next.js",
  react: "React",
  vue: "Vue",
  svelte: "Svelte",
  angular: "Angular",
  jquery: "jQuery",
  lodash: "Lodash",
  express: "Express",
  fastapi: "FastAPI",
  django: "Django",
  flask: "Flask",
  rails: "Ruby on Rails",
  laravel: "Laravel",
  symfony: "Symfony",
  "spring-boot": "Spring Boot",
  dotnet: ".NET",
  aspnetcore: "ASP.NET Core",
  kubernetes: "Kubernetes",
  docker: "Docker",
  terraform: "Terraform",
  vault: "Vault",
  consul: "Consul",
  nomad: "Nomad",
  packer: "Packer",
  vagrant: "Vagrant",
  opentofu: "OpenTofu",
  pulumi: "Pulumi",
  crossplane: "Crossplane",
  argo: "Argo",
  flux: "Flux",
  "cert-manager": "cert-manager",
  "external-dns": "ExternalDNS",
  "ingress-nginx": "NGINX Ingress Controller",
  karpenter: "Karpenter",
  prometheus: "Prometheus",
  grafana: "Grafana",
  loki: "Loki",
  tempo: "Tempo",
  thanos: "Thanos",
  jaeger: "Jaeger",
  zipkin: "Zipkin",
  opentelemetry: "OpenTelemetry",
  opentracing: "OpenTracing",
  skywalking: "SkyWalking",
  fluentd: "Fluentd",
  "fluent-bit": "Fluent Bit",
  vector: "Vector",
  logstash: "Logstash",
  filebeat: "Filebeat",
  osquery: "osquery",
  falco: "Falco",
  trivy: "Trivy",
  sonarqube: "SonarQube",
  codeql: "CodeQL",
  semgrep: "Semgrep",
  tfsec: "tfsec",
  checkov: "Checkov",
  opa: "Open Policy Agent",
  gatekeeper: "Gatekeeper",
  kyverno: "Kyverno",
  ansible: "Ansible",
  chef: "Chef",
  puppet: "Puppet",
  saltstack: "SaltStack",
  jenkins: "Jenkins",
  "gitlab-ci": "GitLab CI",
  "github-actions": "GitHub Actions",
  circleci: "CircleCI",
  travisci: "Travis CI",
  drone: "Drone CI",
  tektoncd: "Tekton",
  "argo-workflows": "Argo Workflows",
  spinnaker: "Spinnaker",
  helm: "Helm",
  harbor: "Harbor",
  notary: "Notary",
  cosign: "Cosign",
  sigstore: "Sigstore",
  fulcio: "Fulcio",
  rekor: "Rekor",
  theupdateframework: "TUF",
  "in-toto": "in-toto",
  grafeas: "Grafeas",
  clair: "Clair",
  anchore: "Anchore",
  dapr: "Dapr",
  keptn: "Keptn",
  brigade: "Brigade",
  werf: "werf",
  "argo-cd": "Argo CD",
  "sealed-secrets": "Sealed Secrets",
  sops: "SOPS",
  "git-crypt": "git-crypt",
  transcrypt: "Transcrypt",
  "git-secret": "git-secret",
  blackbox: "Blackbox",
  molecule: "Molecule",
  awx: "AWX",
  rundeck: "Rundeck",
  codefresh: "Codefresh",
  harness: "Harness",
  chartmuseum: "ChartMuseum",
  distribution: "Distribution",
  "vault-csi-provider": "Vault CSI Provider",
  "secrets-store-csi-driver": "Secrets Store CSI Driver",
  "external-secrets": "External Secrets Operator",
  "cloud-custodian": "Cloud Custodian",
  cartography: "Cartography",
  "audit2rbac": "audit2rbac",
  "rbac-lookup": "rbac-lookup",
  "rbac-manager": "rbac-manager",
  trafficserver: "Apache Traffic Server",
  apache2: "Apache HTTP Server",
  httpd: "Apache HTTP Server",
  tomcat: "Apache Tomcat",
  jetty: "Eclipse Jetty",
  undertow: "Undertow",
  netty: "Netty",
  mina: "Apache MINA",
  vertx: "Vert.x",
  quarkus: "Quarkus",
  micronaut: "Micronaut",
  springboot: "Spring Boot",
  springcloud: "Spring Cloud",
  springdata: "Spring Data",
  springsecurity: "Spring Security",
  springbatch: "Spring Batch",
  springintegration: "Spring Integration",
  springkafka: "Spring Kafka",
  springldap: "Spring LDAP",
  springws: "Spring Web Services",
  springhateoas: "Spring HATEOAS",
  springtools: "Spring Tools",
  keycloak: "Keycloak",
  authelia: "Authelia",
  authentik: "Authentik",
  dexidp: "Dex",
  ory: "ORY",
  hydra: "Hydra",
  keto: "Keto",
  oathkeeper: "Oathkeeper",
  spiffe: "SPIFFE",
  spire: "SPIRE",
  linkerd: "Linkerd",
  caddy: "Caddy",
  varnish: "Varnish",
  squid: "Squid",
  lighttpd: "Lighttpd",
  haproxy: "HAProxy",
};

function titleCase(str: string): string {
  return str
    .split(/[-_.]/)
    .map((word) => {
      if (!word) return "";
      const lower = word.toLowerCase();
      if (lower === "js") return "JS";
      if (lower === "ai") return "AI";
      if (lower === "api") return "API";
      if (lower === "sdk") return "SDK";
      if (lower === "ui") return "UI";
      if (lower === "cli") return "CLI";
      if (lower === "css") return "CSS";
      if (lower === "html") return "HTML";
      if (lower === "sql") return "SQL";
      if (lower === "io") return "IO";
      if (lower === "cd") return "CD";
      if (lower === "ci") return "CI";
      if (lower === "dns") return "DNS";
      if (lower === "cdn") return "CDN";
      if (lower === "os") return "OS";
      if (lower === "db") return "DB";
      if (lower === "orm") return "ORM";
      if (lower === "gui") return "GUI";
      if (lower === "uuid") return "UUID";
      if (lower === "jwt") return "JWT";
      if (lower === "oauth") return "OAuth";
      if (lower === "oidc") return "OIDC";
      if (lower === "saml") return "SAML";
      if (lower === "ldap") return "LDAP";
      if (lower === "http") return "HTTP";
      if (lower === "https") return "HTTPS";
      if (lower === "tcp") return "TCP";
      if (lower === "udp") return "UDP";
      if (lower === "grpc") return "gRPC";
      if (lower === "rpc") return "RPC";
      if (lower === "rest") return "REST";
      if (lower === "graphql") return "GraphQL";
      if (lower === "json") return "JSON";
      if (lower === "xml") return "XML";
      if (lower === "yaml") return "YAML";
      if (lower === "toml") return "TOML";
      if (lower === "ini") return "INI";
      if (lower === "csv") return "CSV";
      if (lower === "pdf") return "PDF";
      if (lower === "png") return "PNG";
      if (lower === "jpg") return "JPG";
      if (lower === "jpeg") return "JPEG";
      if (lower === "gif") return "GIF";
      if (lower === "svg") return "SVG";
      if (lower === "webp") return "WebP";
      if (lower === "mp3") return "MP3";
      if (lower === "mp4") return "MP4";
      if (lower === "wav") return "WAV";
      if (lower === "ogg") return "OGG";
      if (lower === "flac") return "FLAC";
      if (lower === "aac") return "AAC";
      if (lower === "mov") return "MOV";
      if (lower === "avi") return "AVI";
      if (lower === "mkv") return "MKV";
      if (lower === "webm") return "WebM";
      if (lower === "hls") return "HLS";
      if (lower === "webrtc") return "WebRTC";
      if (lower === "websocket") return "WebSocket";
      if (lower === "socket") return "Socket";
      if (lower === "ip") return "IP";
      if (lower === "ipv4") return "IPv4";
      if (lower === "ipv6") return "IPv6";
      if (lower === "vpn") return "VPN";
      if (lower === "tls") return "TLS";
      if (lower === "ssl") return "SSL";
      if (lower === "ssh") return "SSH";
      if (lower === "ftp") return "FTP";
      if (lower === "sftp") return "SFTP";
      if (lower === "scp") return "SCP";
      if (lower === "rsync") return "rsync";
      if (lower === "nfs") return "NFS";
      if (lower === "smb") return "SMB";
      if (lower === "cifs") return "CIFS";
      if (lower === "ceph") return "Ceph";
      if (lower === "minio") return "MinIO";
      if (lower === "arrow") return "Arrow";
      if (lower === "parquet") return "Parquet";
      if (lower === "orc") return "ORC";
      if (lower === "avro") return "Avro";
      if (lower === "thrift") return "Thrift";
      if (lower === "protobuf") return "Protobuf";
      if (lower === "capnproto") return "Cap'n Proto";
      if (lower === "flatbuffers") return "FlatBuffers";
      if (lower === "msgpack") return "MessagePack";
      if (lower === "bson") return "BSON";
      if (lower === "cbor") return "CBOR";
      if (lower === "rdf") return "RDF";
      if (lower === "sparql") return "SPARQL";
      if (lower === "jsonld") return "JSON-LD";
      if (lower === "microdata") return "Microdata";
      if (lower === "rdfa") return "RDFa";
      if (lower === "openid") return "OpenID";
      if (lower === "webauthn") return "WebAuthn";
      if (lower === "fido") return "FIDO";
      if (lower === "u2f") return "U2F";
      if (lower === "totp") return "TOTP";
      if (lower === "hotp") return "HOTP";
      if (lower === "otp") return "OTP";
      if (lower === "2fa") return "2FA";
      if (lower === "mfa") return "MFA";
      if (lower === "sso") return "SSO";
      if (lower === "scim") return "SCIM";
      if (lower === "ad") return "AD";
      if (lower === "kerberos") return "Kerberos";
      if (lower === "cas") return "CAS";
      if (lower === "shibboleth") return "Shibboleth";
      if (lower === "kronos") return "Kronos";
      if (lower === "ats") return "ATS";
      return word.charAt(0).toUpperCase() + word.slice(1);
    })
    .join(" ");
}

export function suggestDisplayName(githubRepo: string): string | null {
  const trimmed = githubRepo.trim();
  if (!trimmed) return null;

  const parts = trimmed.split("/");
  if (parts.length !== 2) return null;

  const [owner, repo] = parts;
  if (!owner || !repo) return null;

  const brand = BRAND_MAP[owner.toLowerCase()] ?? titleCase(owner);
  const repoDisplay = SPECIAL_REPO_NAMES[repo.toLowerCase()] ?? titleCase(repo);

  return `${brand} ${repoDisplay}`;
}
