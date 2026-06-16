"use client";

import { useEffect, useState } from "react";
import { engagement, type ReactionCounts } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

const REACTIONS = [
  { type: "like", emoji: "❤️", label: "Like" },
  { type: "applause", emoji: "👏", label: "Applause" },
  { type: "aha", emoji: "💡", label: "Aha!" },
] as const;

interface Props {
  caseStudyId: string;
  initialCounts?: ReactionCounts;
}

export function ReactionBar({ caseStudyId, initialCounts }: Props) {
  const { user } = useAuth();
  const router = useRouter();
  const [counts, setCounts] = useState<ReactionCounts>(
    initialCounts ?? {
      likes_count: 0,
      applause_count: 0,
      aha_count: 0,
      user_reactions: [],
    },
  );
  const [loading, setLoading] = useState<string | null>(null);

  useEffect(() => {
    engagement
      .reactions(caseStudyId)
      .then(setCounts)
      .catch(() => {});
  }, [caseStudyId]);

  async function toggle(type: string) {
    if (!user) {
      router.push("/login");
      return;
    }
    setLoading(type);
    const hasIt = counts.user_reactions.includes(type);
    const key = `${type}s_count` as keyof ReactionCounts;

    // Optimistic update
    setCounts((prev) => ({
      ...prev,
      [key]: hasIt
        ? Math.max(0, (prev[key] as number) - 1)
        : (prev[key] as number) + 1,
      user_reactions: hasIt
        ? prev.user_reactions.filter((r) => r !== type)
        : [...prev.user_reactions, type],
    }));

    try {
      if (hasIt) {
        await engagement.removeReaction(caseStudyId, type);
      } else {
        await engagement.addReaction(caseStudyId, type);
      }
    } catch {
      // Revert on error
      setCounts((prev) => ({
        ...prev,
        [key]: hasIt
          ? (prev[key] as number) + 1
          : Math.max(0, (prev[key] as number) - 1),
        user_reactions: hasIt
          ? [...prev.user_reactions, type]
          : prev.user_reactions.filter((r) => r !== type),
      }));
      toast.error("Failed to update reaction");
    } finally {
      setLoading(null);
    }
  }

  const getCount = (type: string) => {
    const key = `${type}s_count` as keyof ReactionCounts;
    return counts[key] as number;
  };

  return (
    <div className="flex items-center gap-2">
      {REACTIONS.map(({ type, emoji, label }) => (
        <Button
          key={type}
          variant={counts.user_reactions.includes(type) ? "default" : "outline"}
          size="sm"
          disabled={loading === type}
          onClick={() => toggle(type)}
          className="gap-1.5"
          title={label}
        >
          <span>{emoji}</span>
          <span className="text-xs">{getCount(type)}</span>
        </Button>
      ))}
    </div>
  );
}
