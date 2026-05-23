import { fetchSnapshot, type SnapshotProject } from "@/lib/snapshot";
import { fetchProjects } from "@/lib/projects";
import { notFound } from "next/navigation";
import Link from "next/link";
import FromTheDesk from "@/components/FromTheDesk";
import MentionedInBriefings from "@/components/MentionedInBriefings";
import EventStream from "@/components/EventStream";

interface Props {
  params: Promise<{ slug: string }>;
}

export const revalidate = 300;

export default async function ProjectPage({ params }: Props) {
  const { slug } = await params;
  const snapshot = await fetchSnapshot();
  const registry = await fetchProjects();
  let project: SnapshotProject | undefined = snapshot?.projects.find((p) => p.slug === slug);
  const registryProject = registry?.find((p) => p.slug === slug);
  if (!project) {
    if (registryProject) {
      project = {
        slug: registryProject.slug,
        name: registryProject.display_name,
        status: registryProject.status,
        kind: registryProject.kind,
        color_hint: registryProject.color_hint,
        from_the_desk: null,
        from_the_desk_generated_at: null,
        mentioned_in_briefings: [],
      };
    }
  }
  if (!project) notFound();

  const events = (snapshot?.recent_events ?? []).filter((e) => e.project_slug === slug);
  const mentions = project.mentioned_in_briefings ?? [];

  return (
    <main className="lg:pl-24">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-8">
        <section className="pt-10 pb-8 border-b border-ink grid grid-cols-[1fr_auto] gap-8 items-end">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute mb-3.5">
              <Link href="/projects" className="hover:text-signal">
                Projects
              </Link>{" "}
              · {project.name}
            </div>
            <div className="flex flex-col sm:flex-row sm:items-baseline gap-2 sm:gap-4.5">
              <h1 className="font-disp text-[42px] sm:text-[84px] font-extrabold leading-[0.95] tracking-[-0.04em] break-words">{project.name}</h1>
              {project.status === "active" && (
                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-paper bg-signal px-2.5 py-1.5 font-semibold">
                  Active
                </span>
              )}
              {project.status === "held" && (
                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-paper bg-ink-mute px-2.5 py-1.5 font-semibold">
                  Held
                </span>
              )}
              {project.status === "archived" && (
                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute border border-ink-mute px-2.5 py-1.5">
                  Archived
                </span>
              )}
            </div>
            <div className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-soft mt-4.5 flex gap-6 flex-wrap">
              {project.kind && (
                <span>
                  <span className="text-ink-mute mr-1">Kind</span>
                  <span className="text-ink font-semibold">{project.kind}</span>
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2.5">
            {registryProject?.github_repo && (
              <a
                href={`https://github.com/${registryProject.github_repo}`}
                target="_blank"
                rel="noreferrer"
                className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink border border-ink hover:bg-ink hover:text-paper px-3.5 py-2.5 font-medium"
              >
                GitHub ↗
              </a>
            )}
          </div>
        </section>

        <div className="pt-12 pb-24 grid grid-cols-1 lg:grid-cols-[minmax(0,8fr)_minmax(0,3fr)] gap-16">
          <article>
            <FromTheDesk body={project.from_the_desk ?? null} generatedAt={project.from_the_desk_generated_at ?? null} />
            <MentionedInBriefings mentions={mentions} />
            <EventStream events={events} limit={20} />
          </article>
          <aside className="font-disp text-sm">
            <section className="mb-10">
              <h3 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3 border-b border-ink mb-4.5 font-semibold">
                Project brief
              </h3>
              <p className="text-base leading-[1.55] text-ink-soft italic">{project.summary ?? "—"}</p>
            </section>
          </aside>
        </div>
      </div>
    </main>
  );
}
