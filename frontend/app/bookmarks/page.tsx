"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { caseStudies as csApi, type CaseStudyList } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { CaseStudyCard } from "@/components/case-study-card";

export default function BookmarksPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<CaseStudyList[]>([]);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [user, authLoading, router]);

  // Bookmarks endpoint returns case study IDs; full details would need a separate fetch.
  // For v1 we show the user's bookmarked case study IDs (enhancement: batch-fetch details).

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Bookmarks</h1>
      <p className="text-muted-foreground text-sm">Your saved case studies</p>
      {items.length === 0 && (
        <div className="text-center py-12 text-muted-foreground border rounded-xl">
          Bookmark case studies to save them here.
        </div>
      )}
    </div>
  );
}
