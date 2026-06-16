import Link from "next/link";
import { type CaseStudyList } from "@/lib/api";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Heart, MessageCircle, Sparkles, Zap } from "lucide-react";
import { formatDistanceToNow } from "@/lib/utils";

interface Props {
  cs: CaseStudyList;
}

export function CaseStudyCard({ cs }: Props) {
  const totalReactions = cs.likes_count + cs.applause_count + cs.aha_count;

  return (
    <article className="flex flex-col gap-3 rounded-xl border bg-card p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-center gap-2">
        <Avatar className="h-7 w-7">
          <AvatarImage src={cs.author.avatar_url ?? undefined} />
          <AvatarFallback className="text-xs">
            {cs.author.name[0]?.toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <Link
          href={`/${cs.author.handle}`}
          className="text-sm font-medium hover:underline"
        >
          {cs.author.name}
        </Link>
        <span className="text-xs text-muted-foreground">·</span>
        <span className="text-xs text-muted-foreground">
          {cs.published_at ? formatDistanceToNow(cs.published_at) : "Draft"}
        </span>
        {cs.ai_model && (
          <>
            <span className="text-xs text-muted-foreground">·</span>
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Sparkles className="h-3 w-3" />
              {cs.ai_model}
            </span>
          </>
        )}
      </div>

      <div>
        <Link
          href={`/${cs.author.handle}/${cs.slug}`}
          className="font-semibold text-base hover:underline leading-snug"
        >
          {cs.title}
        </Link>
        {cs.summary && (
          <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
            {cs.summary}
          </p>
        )}
      </div>

      {cs.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {cs.tags.slice(0, 5).map((tag) => (
            <Badge key={tag.id} variant="secondary" className="text-xs">
              {tag.name}
            </Badge>
          ))}
        </div>
      )}

      <div className="flex items-center gap-4 text-xs text-muted-foreground pt-1">
        <span className="flex items-center gap-1">
          <Heart className="h-3.5 w-3.5" />
          {totalReactions}
        </span>
        <span className="flex items-center gap-1">
          <MessageCircle className="h-3.5 w-3.5" />
          {cs.comments_count}
        </span>
      </div>
    </article>
  );
}
