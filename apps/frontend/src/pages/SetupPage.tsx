import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { bulkUpdateSettings, createAdminProject } from "@/lib/api";
import Seo from "@/components/Seo";
import { suggestDisplayName } from "@/lib/projectNames";

const STEPS = [
  { key: "storage", label: "Storage" },
  { key: "ai", label: "AI" },
  { key: "tts", label: "TTS" },
  { key: "github", label: "GitHub" },
  { key: "project", label: "First Project" },
];

export default function SetupPage() {
  const seo = <Seo title="Setup" noindex canonicalPath="/setup" />;
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [storage, setStorage] = useState({
    provider: "local",
    bucket: "",
    region: "",
    access_key: "",
    secret_key: "",
    endpoint: "",
  });

  const [ai, setAi] = useState({
    provider: "openai",
    api_key: "",
    model: "gpt-4o",
  });

  const [tts, setTts] = useState({
    provider: "openai",
    api_key: "",
    voice: "alloy",
  });

  const [github, setGithub] = useState({
    token: "",
  });

  const [project, setProject] = useState({
    slug: "",
    display_name: "",
    github_repo: "",
    status: "active",
    kind: "app",
  });

  const totalSteps = STEPS.length;
  const current = STEPS[step];
  const isLast = step === totalSteps - 1;

  async function handleFinish() {
    setSaving(true);
    setError("");
    try {
      const settings: Record<string, string> = {};

      if (storage.provider) settings["storage.provider"] = storage.provider;
      if (storage.bucket) settings["storage.bucket"] = storage.bucket;
      if (storage.region) settings["storage.region"] = storage.region;
      if (storage.access_key)
        settings["storage.access_key"] = storage.access_key;
      if (storage.secret_key)
        settings["storage.secret_key"] = storage.secret_key;
      if (storage.endpoint) settings["storage.endpoint"] = storage.endpoint;

      if (ai.provider) settings["ai.provider"] = ai.provider;
      if (ai.api_key) settings["ai.api_key"] = ai.api_key;
      if (ai.model) settings["ai.model"] = ai.model;

      if (tts.provider) settings["tts.provider"] = tts.provider;
      if (tts.api_key) settings["tts.api_key"] = tts.api_key;
      if (tts.voice) settings["tts.voice"] = tts.voice;

      if (github.token) settings["github.token"] = github.token;

      await bulkUpdateSettings(settings);

      if (project.slug && project.display_name) {
        await createAdminProject(project);
      }

      navigate("/admin");
    } catch (e: any) {
      setError(e.message || "Setup failed.");
      setSaving(false);
    }
  }

  function handleSkip() {
    if (isLast) {
      handleFinish();
    } else {
      setStep((s) => s + 1);
    }
  }

  function handleNext() {
    if (isLast) {
      handleFinish();
    } else {
      setStep((s) => s + 1);
    }
  }

  return (
    <>
      {seo}
      <main className="max-w-[720px] mx-auto px-4 sm:px-8 py-16">
      <div className="mb-10">
        <h1 className="font-disp text-3xl font-bold tracking-[-0.02em] text-ink mb-2">
          Setup
        </h1>
        <p className="font-disp text-sm text-ink-mute">
          Configure Dispatch to get started.
        </p>
      </div>

      {/* Progress */}
      <div className="flex gap-0 border border-ink mb-10">
        {STEPS.map((s, i) => (
          <div
            key={s.key}
            className={`flex-1 px-2 py-2.5 text-center border-r border-ink last:border-r-0 transition-colors ${
              i === step
                ? "bg-ink text-paper"
                : i < step
                  ? "bg-paper-deep text-ink"
                  : "bg-paper text-ink-mute"
            }`}
          >
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] font-semibold">
              {i + 1}. {s.label}
            </span>
          </div>
        ))}
      </div>

      {error && (
        <div className="mb-6 px-4 py-3 border border-signal text-signal font-mono text-[11px]">
          {error}
        </div>
      )}

      {/* Step content */}
      <div className="border border-ink p-6 mb-8">
        {current.key === "storage" && (
          <StepStorage values={storage} onChange={setStorage} />
        )}
        {current.key === "ai" && <StepAi values={ai} onChange={setAi} />}
        {current.key === "tts" && <StepTts values={tts} onChange={setTts} />}
        {current.key === "github" && (
          <StepGithub values={github} onChange={setGithub} />
        )}
        {current.key === "project" && (
          <StepProject values={project} onChange={setProject} />
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={handleSkip}
          disabled={saving}
          className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 border border-ink text-ink hover:bg-paper-deep transition-colors disabled:opacity-50"
        >
          {isLast ? "Skip & Finish" : "Skip for now"}
        </button>
        <div className="flex gap-3">
          {step > 0 && (
            <button
              onClick={() => setStep((s) => s - 1)}
              disabled={saving}
              className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 border border-ink text-ink hover:bg-paper-deep transition-colors disabled:opacity-50"
            >
              Back
            </button>
          )}
          <button
            onClick={handleNext}
            disabled={saving}
            className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-6 py-2.5 bg-signal text-paper hover:bg-ink transition-colors disabled:opacity-50"
          >
            {saving
              ? "Saving…"
              : isLast
                ? "Finish"
                : `Next: ${STEPS[step + 1].label}`}
          </button>
        </div>
      </div>
    </main>
    </>
  );
}

/* ---------- Sub-components ---------- */

function StepStorage({
  values,
  onChange,
}: {
  values: Record<string, string>;
  onChange: (v: any) => void;
}) {
  return (
    <div className="space-y-4">
      <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink font-semibold mb-4">
        Storage Provider
      </h2>
      <SelectRow
        label="Provider"
        value={values.provider}
        options={["local", "s3", "r2"]}
        onChange={(v) => onChange({ ...values, provider: v })}
      />
      {values.provider !== "local" && (
        <>
          <InputRow
            label="Bucket"
            value={values.bucket}
            onChange={(v) => onChange({ ...values, bucket: v })}
          />
          <InputRow
            label="Region"
            value={values.region}
            onChange={(v) => onChange({ ...values, region: v })}
          />
          <InputRow
            label="Access Key"
            value={values.access_key}
            onChange={(v) => onChange({ ...values, access_key: v })}
          />
          <InputRow
            label="Secret Key"
            value={values.secret_key}
            type="password"
            onChange={(v) => onChange({ ...values, secret_key: v })}
          />
          <InputRow
            label="Endpoint"
            value={values.endpoint}
            onChange={(v) => onChange({ ...values, endpoint: v })}
            placeholder="https://..."
          />
        </>
      )}
    </div>
  );
}

function StepAi({
  values,
  onChange,
}: {
  values: Record<string, string>;
  onChange: (v: any) => void;
}) {
  return (
    <div className="space-y-4">
      <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink font-semibold mb-4">
        AI Provider
      </h2>
      <SelectRow
        label="Provider"
        value={values.provider}
        options={["openai", "anthropic"]}
        onChange={(v) => onChange({ ...values, provider: v })}
      />
      <InputRow
        label="API Key"
        value={values.api_key}
        type="password"
        onChange={(v) => onChange({ ...values, api_key: v })}
      />
      <InputRow
        label="Model"
        value={values.model}
        onChange={(v) => onChange({ ...values, model: v })}
        placeholder="gpt-4o, claude-3-5-sonnet..."
      />
    </div>
  );
}

function StepTts({
  values,
  onChange,
}: {
  values: Record<string, string>;
  onChange: (v: any) => void;
}) {
  return (
    <div className="space-y-4">
      <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink font-semibold mb-4">
        TTS Provider
      </h2>
      <SelectRow
        label="Provider"
        value={values.provider}
        options={["openai", "elevenlabs", "kokoro"]}
        onChange={(v) => onChange({ ...values, provider: v })}
      />
      <InputRow
        label="API Key"
        value={values.api_key}
        type="password"
        onChange={(v) => onChange({ ...values, api_key: v })}
      />
      <InputRow
        label="Voice"
        value={values.voice}
        onChange={(v) => onChange({ ...values, voice: v })}
        placeholder="alloy, onyx, nova..."
      />
    </div>
  );
}

function StepGithub({
  values,
  onChange,
}: {
  values: Record<string, string>;
  onChange: (v: any) => void;
}) {
  return (
    <div className="space-y-4">
      <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink font-semibold mb-4">
        GitHub
      </h2>
      <InputRow
        label="Personal Access Token"
        value={values.token}
        type="password"
        onChange={(v) => onChange({ ...values, token: v })}
      />
    </div>
  );
}

function StepProject({
  values,
  onChange,
}: {
  values: Record<string, string>;
  onChange: (v: any) => void;
}) {
  return (
    <div className="space-y-4">
      <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink font-semibold mb-4">
        First Project
      </h2>
      <InputRow
        label="Slug"
        value={values.slug}
        onChange={(v) => onChange({ ...values, slug: v })}
        placeholder="my-project"
      />
      <InputRow
        label="Display Name"
        value={values.display_name}
        onChange={(v) => onChange({ ...values, display_name: v })}
        placeholder="My Project"
      />
      <InputRow
        label="GitHub Repo"
        value={values.github_repo}
        onChange={(v) => {
          const suggested = suggestDisplayName(v);
          onChange({
            ...values,
            github_repo: v,
            display_name: values.display_name || suggested || values.display_name,
          });
        }}
        placeholder="owner/repo"
      />
      <SelectRow
        label="Status"
        value={values.status}
        options={["active", "held", "archived"]}
        onChange={(v) => onChange({ ...values, status: v })}
      />
      <SelectRow
        label="Kind"
        value={values.kind}
        options={["app", "lib", "infra", "other"]}
        onChange={(v) => onChange({ ...values, kind: v })}
      />
    </div>
  );
}

/* ---------- Field helpers ---------- */

function InputRow({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-[140px_1fr] gap-2 items-center">
      <label className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold">
        {label}
      </label>
      <input
        type={type}
        className="w-full px-2.5 py-2 border border-ink bg-paper font-disp text-sm text-ink focus:outline-none focus:border-signal placeholder:text-ink-mute/40"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

function SelectRow({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-[140px_1fr] gap-2 items-center">
      <label className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold">
        {label}
      </label>
      <select
        className="w-full px-2.5 py-2 border border-ink bg-paper font-mono text-[11px] text-ink focus:outline-none focus:border-signal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}
