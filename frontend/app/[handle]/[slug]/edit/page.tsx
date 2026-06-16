"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { caseStudies as csApi, type CaseStudy } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { CaseStudyForm } from "@/components/case-study-form";

interface Props {
  params: Promise<{ handle: string; slug: string }>;
}

export default function EditCaseStudyPage({ params }: Props) {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [cs, setCs] = useState<CaseStudy | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [user, authLoading, router]);

  useEffect(() => {
    async function load() {
      const { handle, slug } = await params;
      if (!user) return;
      const list = await csApi.byUser(handle).catch(() => []);
      const item = list.find((c) => c.slug === slug);
      if (!item) { router.replace("/dashboard"); return; }
      const full = await csApi.get(item.id);
      if (full.author.id !== user.id) { router.replace("/dashboard"); return; }
      setCs(full);
      setLoading(false);
    }
    if (user) load();
  }, [user, params]);

  if (authLoading || loading || !cs) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Edit case study</h1>
      <CaseStudyForm existing={cs} />
    </div>
  );
}
