"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { caseStudies as csApi, type CaseStudyList } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { CaseStudyCard } from "@/components/case-study-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { Plus } from "lucide-react";

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<CaseStudyList[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [user, authLoading, router]);

  useEffect(() => {
    if (user) {
      csApi
        .byUser(user.handle)
        .then(setItems)
        .finally(() => setLoading(false));
    }
  }, [user]);

  if (authLoading || loading) {
    return <div className="space-y-4">{[1, 2].map((i) => <div key={i} className="h-32 rounded-xl border bg-muted animate-pulse" />)}</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">My Case Studies</h1>
        <Button asChild size="sm">
          <Link href="/new">
            <Plus className="h-4 w-4 mr-1" />
            New
          </Link>
        </Button>
      </div>

      {items.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground border rounded-xl">
          <p className="mb-3">You haven&apos;t created any case studies yet.</p>
          <Button asChild size="sm">
            <Link href="/new">Create your first one</Link>
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((cs) => (
            <div key={cs.id} className="relative">
              <div className="absolute top-3 right-3 z-10">
                <Badge variant={cs.visibility === "public" ? "default" : "secondary"}>
                  {cs.visibility}
                </Badge>
              </div>
              <CaseStudyCard cs={cs} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
