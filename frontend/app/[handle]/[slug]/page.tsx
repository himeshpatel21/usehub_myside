import { notFound } from "next/navigation";
import Link from "next/link";
import { caseStudies as csApi } from "@/lib/api";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ReactionBar } from "@/components/reaction-bar";
import { Comments } from "@/components/comments";
import { formatDistanceToNow } from "@/lib/utils";
import { Sparkles } from "lucide-react";

interface Props {
  params: Promise<{ handle: string; slug: string }>;
}

// Note: We look up by handle/slug by listing user's case studies.
// In production we'd add a GET /users/{handle}/case-studies/{slug} endpoint.
export default async function CaseStudyPage({ params }: Props) {
  const { handle, slug } = await params;

  const list = await csApi.byUser(handle).catch(() => []);
  const listItem = list.find((cs) => cs.slug === slug);
  if (!listItem) notFound();

  const cs = await csApi.get(listItem.id).catch(() => null);
  if (!cs) notFound();

  const content = cs.content;

  return (
    <div className="max-w-3xl space-y-8">
      {/* Header */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link
            href={`/${cs.author.handle}`}
            className="flex items-center gap-2 hover:text-foreground transition-colors"
          >
            <Avatar className="h-6 w-6">
              <AvatarImage src={cs.author.avatar_url ?? undefined} />
              <AvatarFallback className="text-xs">
                {cs.author.name[0]?.toUpperCase()}
              </AvatarFallback>
            </Avatar>
            {cs.author.name}
          </Link>
          <span>·</span>
          <span>
            {cs.published_at
              ? formatDistanceToNow(cs.published_at)
              : "Draft"}
          </span>
          {cs.ai_model && (
            <>
              <span>·</span>
              <span className="flex items-center gap-1">
                <Sparkles className="h-3.5 w-3.5" />
                {cs.ai_model}
                {cs.ai_platform && ` · ${cs.ai_platform}`}
              </span>
            </>
          )}
        </div>

        <h1 className="text-3xl font-bold leading-tight">{cs.title}</h1>

        {cs.summary && (
          <p className="text-muted-foreground text-lg leading-relaxed">
            {cs.summary}
          </p>
        )}

        {cs.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {cs.tags.map((tag) => (
              <Badge key={tag.id} variant="secondary">
                {tag.name}
              </Badge>
            ))}
          </div>
        )}
      </div>

      <Separator />

      {/* Content */}
      {content && (
        <div className="space-y-8">
          <section className="space-y-3">
            <h2 className="text-lg font-semibold">Prompt</h2>
            <div className="rounded-lg bg-muted p-4 font-mono text-sm whitespace-pre-wrap leading-relaxed">
              {content.prompt}
            </div>
          </section>

          {content.iterations.length > 0 && (
            <section className="space-y-4">
              <h2 className="text-lg font-semibold">
                Iterations ({content.iterations.length})
              </h2>
              <div className="space-y-4">
                {content.iterations.map((iter, idx) => (
                  <div
                    key={idx}
                    className="border rounded-lg overflow-hidden"
                  >
                    <div className="bg-muted/50 px-4 py-2 text-xs font-medium text-muted-foreground border-b">
                      Iteration {idx + 1}
                    </div>
                    <div className="divide-y">
                      <div className="p-4 space-y-1">
                        <p className="text-xs font-medium text-muted-foreground">Input</p>
                        <p className="text-sm whitespace-pre-wrap leading-relaxed">
                          {iter.input}
                        </p>
                      </div>
                      <div className="p-4 space-y-1 bg-muted/20">
                        <p className="text-xs font-medium text-muted-foreground">Output</p>
                        <p className="text-sm whitespace-pre-wrap leading-relaxed">
                          {iter.output}
                        </p>
                      </div>
                      {iter.notes && (
                        <div className="p-4 space-y-1">
                          <p className="text-xs font-medium text-muted-foreground">Notes</p>
                          <p className="text-sm text-muted-foreground">
                            {iter.notes}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="space-y-3">
            <h2 className="text-lg font-semibold">Final Output</h2>
            <div className="rounded-lg border p-4 text-sm whitespace-pre-wrap leading-relaxed">
              {content.final_output}
            </div>
          </section>
        </div>
      )}

      <Separator />

      {/* Reactions */}
      <div className="space-y-2">
        <p className="text-sm text-muted-foreground">React to this case study</p>
        <ReactionBar caseStudyId={cs.id} />
      </div>

      <Separator />

      {/* Comments */}
      <Comments caseStudyId={cs.id} />
    </div>
  );
}
